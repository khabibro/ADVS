"""A document's own check uses the submission's current check date (점검 기준일).

Before: the document page measured validity against the submission's creation date, while the
submission result used the chosen check date, so a document could show 보완 필요 inside a
submission that was 제출 가능.
"""

import uuid
from datetime import date

from app.models.entities import ValidationResult
from app.services.document_validation import current_check_date


def _project(client):
    workflows = client.get("/api/v1/workflows").json()
    if not workflows:
        created = client.post(
            "/api/v1/admin/workflows",
            json={
                "name": "검사일 테스트 업무",
                "criteria": {"documents": [{"document_type": "BUSINESS_REGISTRATION_CERTIFICATE"}]},
            },
        ).json()
        workflow_id = created["id"]
    else:
        workflow_id = workflows[0]["id"]
    return client.post(
        "/api/v1/projects", json={"name": "점검 기준일", "workflow_id": workflow_id}
    ).json()


def test_no_current_result_means_no_check_date(client, db_session):
    project = _project(client)
    assert current_check_date(db_session, uuid.UUID(project["id"])) is None


def test_current_result_provides_its_check_date(client, db_session):
    project = _project(client)
    db_session.add(
        ValidationResult(
            project_id=uuid.UUID(project["id"]),
            rule_type="REQUIRED_DOCUMENT",
            passed=True,
            severity="INFO",
            message="",
            code="TEST",
            scope="SUBMISSION",
            details={"evaluation_date": "2026-10-05"},
        )
    )
    db_session.commit()
    assert current_check_date(db_session, uuid.UUID(project["id"])) == date(2026, 10, 5)


def test_verified_project_reports_the_chosen_date(client, db_session):
    project = _project(client)
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/verify", json={"evaluation_date": "2026-10-05"}
        ).status_code
        == 200
    )
    assert current_check_date(db_session, uuid.UUID(project["id"])) == date(2026, 10, 5)
