"""Admin-editable check criteria (점검 기준): mentor request "점검 기준 관리".

Covers: round trip of the editing model, saving as a new version with history, validation that rejects
configurations the verification engine cannot run (nothing is written), optimistic concurrency, restore,
invalidation of stored results of projects that use the workflow, applicant-facing hints, and the
optional admin token.
"""

import uuid

import pytest

from app.core.config import get_settings
from app.models.entities import ChecklistRevision, ValidationRule

BUSINESS_CRITERIA = {
    "documents": [
        {"document_type": "BUSINESS_REGISTRATION_CERTIFICATE", "required": True},
        {
            "document_type": "NATIONAL_TAX_PAYMENT_CERTIFICATE",
            "required": True,
            "check_validity": True,
        },
        {
            "document_type": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
            "required": False,
            "check_validity": True,
        },
    ],
    "comparisons": [
        {
            "source_document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
            "source_field": "business_registration_number",
            "target_document_type": "NATIONAL_TAX_PAYMENT_CERTIFICATE",
            "target_field": "business_registration_number",
            "value_type": "identifier",
        },
        {
            "source_document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
            "source_field": "company_name",
            "target_document_type": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
            "target_field": "workplace_name",
        },
    ],
}

STUDENT_CRITERIA = {
    "documents": [
        {
            "document_type": "ENROLLMENT_CERTIFICATE",
            "required": True,
            "issue_date_max_age_days": 90,
        },
        {
            "document_type": "TRANSCRIPT",
            "required": False,
            "value_rules": [{"field": "gpa", "operator": "GREATER_THAN_OR_EQUAL", "value": "3.0"}],
        },
    ],
    "comparisons": [
        {
            "source_document_type": "ENROLLMENT_CERTIFICATE",
            "source_field": "student_name",
            "target_document_type": "TRANSCRIPT",
            "target_field": "student_name",
        }
    ],
}


def _create(client, criteria=STUDENT_CRITERIA, name=None):
    response = client.post(
        "/api/v1/admin/workflows",
        json={
            "name": name or f"테스트 업무 {uuid.uuid4().hex[:6]}",
            "criteria": criteria,
            "editor": "관리자",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _normalized(criteria):
    """Compare criteria regardless of default values the API fills in."""
    docs = []
    for item in criteria["documents"]:
        docs.append(
            {
                "document_type": item["document_type"],
                "required": item.get("required", True),
                "issue_date_max_age_days": item.get("issue_date_max_age_days"),
                "check_validity": item.get("check_validity", False),
                "value_rules": item.get("value_rules", []),
                "required_fields": item.get("required_fields", []),
            }
        )
    comps = [{"value_type": "string", **item} for item in criteria["comparisons"]]

    def key(c):
        return (
            c["source_document_type"],
            c["source_field"],
            c["target_document_type"],
            c["target_field"],
        )

    return sorted(docs, key=lambda d: d["document_type"]), sorted(comps, key=key)


@pytest.mark.parametrize("criteria", [BUSINESS_CRITERIA, STUDENT_CRITERIA])
def test_criteria_round_trip(client, criteria):
    created = _create(client, criteria)
    assert created["version"] == 1
    fetched = client.get(f"/api/v1/admin/workflows/{created['id']}").json()
    assert _normalized(fetched["criteria"]) == _normalized(criteria)


def test_catalog_lists_document_types_with_korean_field_names(client):
    catalog = client.get("/api/v1/admin/catalog").json()["document_types"]
    by_type = {item["document_type"]: item for item in catalog}
    assert "UNKNOWN" not in by_type
    tax = by_type["NATIONAL_TAX_PAYMENT_CERTIFICATE"]
    assert tax["display_name"] == "국세 납세증명서"
    assert tax["supports_validity"] is True
    assert {"name": "valid_until", "display_name": "유효기간 종료일", "kind": "date"} in tax[
        "fields"
    ]
    assert by_type["BUSINESS_REGISTRATION_CERTIFICATE"]["supports_validity"] is False


def test_save_creates_a_new_version_and_changes_the_stored_rule(client, db_session):
    created = _create(client)
    changed = {
        **STUDENT_CRITERIA,
        "documents": [
            dict(STUDENT_CRITERIA["documents"][0], issue_date_max_age_days=30),
            STUDENT_CRITERIA["documents"][1],
        ],
    }
    response = client.put(
        f"/api/v1/admin/workflows/{created['id']}/criteria",
        json={
            "criteria": changed,
            "expected_version": 1,
            "editor": "관리자",
            "note": "30일로 변경",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2
    assert body["criteria"]["documents"][0]["issue_date_max_age_days"] == 30
    rules = db_session.query(ValidationRule).filter_by(rule_type="ISSUE_DATE_MAX_AGE").all()
    assert any(rule.params == {"max_age_days": 30} for rule in rules)
    history = client.get(f"/api/v1/admin/workflows/{created['id']}/revisions").json()
    assert [item["version"] for item in history] == [2, 1]
    assert history[0]["note"] == "30일로 변경" and history[0]["editor_label"] == "관리자"
    assert history[1]["criteria"]["documents"][0]["issue_date_max_age_days"] == 90


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (
            lambda c: c["documents"][0].update(issue_date_max_age_days=0),
            "documents.0.issue_date_max_age_days",
        ),
        (lambda c: c["documents"][0].update(check_validity=True), "documents.0.check_validity"),
        (
            lambda c: c["documents"][1]["value_rules"][0].update(value="abc"),
            "documents.1.value_rules.0",
        ),
        (
            lambda c: c["documents"][1]["value_rules"][0].update(field="student_name"),
            "documents.1.value_rules.0",
        ),
        (lambda c: c["comparisons"][0].update(target_field="gpa_scale_x"), "comparisons.0"),
        (lambda c: c["documents"].append({"document_type": "TRANSCRIPT"}), "documents.2"),
        (lambda c: [d.update(required=False) for d in c["documents"]], "documents"),
        (lambda c: c["comparisons"].append(dict(c["comparisons"][0])), "comparisons.1"),
    ],
)
def test_invalid_criteria_are_rejected_without_writing(client, mutate, field):
    created = _create(client)
    criteria = {
        "documents": [
            dict(item, value_rules=[dict(r) for r in item.get("value_rules", [])])
            for item in STUDENT_CRITERIA["documents"]
        ],
        "comparisons": [dict(item) for item in STUDENT_CRITERIA["comparisons"]],
    }
    mutate(criteria)
    response = client.put(
        f"/api/v1/admin/workflows/{created['id']}/criteria", json={"criteria": criteria}
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["field"] == field
    after = client.get(f"/api/v1/admin/workflows/{created['id']}").json()
    assert after["version"] == 1
    assert _normalized(after["criteria"]) == _normalized(STUDENT_CRITERIA)


def test_comparison_with_a_document_outside_the_workflow_is_rejected(client):
    created = _create(client)
    criteria = {
        "documents": STUDENT_CRITERIA["documents"],
        "comparisons": [
            {
                "source_document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
                "source_field": "company_name",
                "target_document_type": "TRANSCRIPT",
                "target_field": "student_name",
            }
        ],
    }
    response = client.put(
        f"/api/v1/admin/workflows/{created['id']}/criteria", json={"criteria": criteria}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "comparisons.0"


def test_stale_version_is_a_conflict(client):
    created = _create(client)
    url = f"/api/v1/admin/workflows/{created['id']}/criteria"
    assert (
        client.put(url, json={"criteria": STUDENT_CRITERIA, "expected_version": 1}).status_code
        == 200
    )
    response = client.put(url, json={"criteria": STUDENT_CRITERIA, "expected_version": 1})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "VERSION_CONFLICT"


def test_restore_brings_back_an_older_version_as_a_new_version(client):
    created = _create(client)
    url = f"/api/v1/admin/workflows/{created['id']}"
    changed = {
        **STUDENT_CRITERIA,
        "documents": [
            dict(STUDENT_CRITERIA["documents"][0], issue_date_max_age_days=10),
            STUDENT_CRITERIA["documents"][1],
        ],
    }
    client.put(f"{url}/criteria", json={"criteria": changed})
    restored = client.post(f"{url}/revisions/1/restore", json={"editor": "관리자"}).json()
    assert restored["version"] == 3
    assert restored["criteria"]["documents"][0]["issue_date_max_age_days"] == 90
    history = client.get(f"{url}/revisions").json()
    assert history[0]["note"] == "버전 1의 기준으로 되돌림"
    assert client.post(f"{url}/revisions/99/restore", json={}).status_code == 422


def test_saving_invalidates_stored_results_of_projects_using_the_workflow(client):
    created = _create(client)
    project = client.post(
        "/api/v1/projects", json={"name": "기준 변경 확인", "workflow_id": created["id"]}
    ).json()
    verified = client.post(
        f"/api/v1/projects/{project['id']}/verify", json={"evaluation_date": "2026-10-05"}
    )
    assert verified.status_code == 200, verified.text
    assert client.get(f"/api/v1/projects/{project['id']}/verification").json()["is_current"] is True
    client.put(
        f"/api/v1/admin/workflows/{created['id']}/criteria", json={"criteria": STUDENT_CRITERIA}
    )
    assert (
        client.get(f"/api/v1/projects/{project['id']}/verification").json()["is_current"] is False
    )


def test_workflow_read_shows_the_checks_to_applicants(client):
    created = _create(client)
    workflow = client.get(f"/api/v1/workflows/{created['id']}").json()
    by_type = {item["document_type"]: item for item in workflow["document_requirements"]}
    assert by_type["ENROLLMENT_CERTIFICATE"]["checks"] == ["발급일로부터 90일 이내"]
    assert by_type["TRANSCRIPT"]["checks"] == ["평점평균 3.0 이상"]


def test_copy_creates_an_independent_workflow(client):
    source = _create(client, BUSINESS_CRITERIA)
    response = client.post(
        "/api/v1/admin/workflows",
        json={"name": f"복사본 {uuid.uuid4().hex[:6]}", "copy_from_id": source["id"]},
    )
    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != source["id"]
    assert _normalized(copy["criteria"]) == _normalized(BUSINESS_CRITERIA)
    duplicate = client.post(
        "/api/v1/admin/workflows", json={"name": copy["name"], "copy_from_id": source["id"]}
    )
    assert duplicate.status_code == 422 and duplicate.json()["detail"]["field"] == "name"


def test_deactivated_workflow_is_hidden_from_applicants(client):
    created = _create(client)
    client.patch(f"/api/v1/admin/workflows/{created['id']}", json={"is_active": False})
    ids = {item["id"] for item in client.get("/api/v1/workflows").json()}
    assert created["id"] not in ids


def test_first_save_of_a_seeded_workflow_keeps_the_original_as_version_1(client, db_session):
    created = _create(client)
    db_session.query(ChecklistRevision).filter_by(checklist_id=uuid.UUID(created["id"])).delete()
    db_session.commit()
    client.put(
        f"/api/v1/admin/workflows/{created['id']}/criteria", json={"criteria": STUDENT_CRITERIA}
    )
    history = client.get(f"/api/v1/admin/workflows/{created['id']}/revisions").json()
    assert [item["version"] for item in history] == [2, 1]
    assert history[1]["note"] == "최초 기준 (변경 전 상태)"


def test_admin_token_is_enforced_when_configured(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_api_token", "secret-token")
    assert client.get("/api/v1/admin/workflows").status_code == 401
    assert (
        client.get("/api/v1/admin/workflows", headers={"X-ADVS-Admin-Token": "wrong"}).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/admin/workflows", headers={"X-ADVS-Admin-Token": "secret-token"}
        ).status_code
        == 200
    )
    # the applicant-facing API is unaffected
    assert client.get("/api/v1/workflows").status_code == 200
