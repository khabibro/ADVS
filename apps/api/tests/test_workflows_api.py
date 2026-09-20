import uuid

from fastapi.testclient import TestClient

from app.core.domain import DocumentType
from app.models.entities import Checklist, DocumentRequirement


def _workflow(db_session, *, is_active: bool = True) -> Checklist:
    checklist = Checklist(
        name="MVP administrative workflow",
        description="Four-document MVP workflow.",
        is_active=is_active,
    )
    db_session.add(checklist)
    db_session.flush()
    db_session.add_all(
        [
            DocumentRequirement(
                checklist_id=checklist.id,
                document_type=DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
                required=True,
            ),
            DocumentRequirement(
                checklist_id=checklist.id,
                document_type=DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
                required=True,
            ),
            DocumentRequirement(
                checklist_id=checklist.id,
                document_type=DocumentType.CAREER_CERTIFICATE.value,
                required=False,
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(checklist)
    return checklist


def test_list_workflows_exposes_document_requirements(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session)

    response = client.get("/api/v1/workflows")

    assert response.status_code == 200
    payload = response.json()
    item = next(item for item in payload if item["id"] == str(workflow.id))
    assert item["name"] == "MVP administrative workflow"
    requirements = {req["document_type"]: req for req in item["document_requirements"]}
    assert requirements["BUSINESS_REGISTRATION_CERTIFICATE"] == {
        "document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
        "display_name": "사업자등록증",
        "required": True,
    }
    assert requirements["CAREER_CERTIFICATE"]["required"] is False


def test_get_workflow_exposes_required_and_optional_documents(
    client: TestClient, db_session
) -> None:
    workflow = _workflow(db_session)

    response = client.get(f"/api/v1/workflows/{workflow.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(workflow.id)
    assert payload["is_active"] is True
    requirements = {item["document_type"]: item for item in payload["document_requirements"]}
    assert requirements["BUSINESS_REGISTRATION_CERTIFICATE"]["required"] is True
    assert requirements["CAREER_CERTIFICATE"]["required"] is False


def test_inactive_workflows_are_not_listed(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session, is_active=False)

    response = client.get("/api/v1/workflows")

    assert response.status_code == 200
    assert str(workflow.id) not in {item["id"] for item in response.json()}


def test_inactive_workflow_detail_is_rejected(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session, is_active=False)

    response = client.get(f"/api/v1/workflows/{workflow.id}")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_FAILED"


def test_create_project_requires_valid_workflow(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session)

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Workflow-backed project",
            "workflow_id": str(workflow.id),
            "applicant_name": "홍길동",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["workflow_id"] == str(workflow.id)
    assert payload["workflow"]["name"] == workflow.name
    assert payload["status"] == "REVIEW_REQUIRED"
    assert {doc["document_type"] for doc in payload["expected_documents"]} == {
        "BUSINESS_REGISTRATION_CERTIFICATE",
        "SME_CONFIRMATION_CERTIFICATE",
        "CAREER_CERTIFICATE",
    }


def test_project_read_exposes_workflow_context(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session)
    created = client.post(
        "/api/v1/projects",
        json={"name": "Read workflow context", "workflow_id": str(workflow.id)},
    ).json()

    response = client.get(f"/api/v1/projects/{created['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == str(workflow.id)
    assert payload["workflow"]["description"] == "Four-document MVP workflow."
    assert payload["expected_documents"][0]["display_name"]


def test_missing_workflow_id_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json={"name": "Missing workflow"})

    assert response.status_code == 422


def test_unknown_workflow_id_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Bad workflow", "workflow_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_inactive_workflow_id_is_rejected(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session, is_active=False)

    response = client.post(
        "/api/v1/projects",
        json={"name": "Inactive workflow", "workflow_id": str(workflow.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_FAILED"


def test_legacy_project_without_workflow_remains_readable(client: TestClient, db_session) -> None:
    from app.models.entities import Project, User

    user = User(email="legacy@advs.local", display_name="Legacy User")
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="Legacy project", status="PASS")
    db_session.add(project)
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] is None
    assert payload["workflow"] is None
    assert payload["expected_documents"] == []
    assert payload["status"] == "READY"
