"""Phase 0: an applicant can neither choose the check date nor confirm values, and the admin
endpoints are unreachable unless ADMIN_ENABLED is set. Invented data only."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.config import get_settings
from app.core.domain import DocumentType, OverallStatus
from app.models.entities import Checklist, DocumentRequirement


@pytest.fixture
def applicant_mode(monkeypatch):
    """Both switches off, as in the applicant deployment."""
    monkeypatch.setenv("ADMIN_ENABLED", "false")
    monkeypatch.setenv("ALLOW_CLIENT_EVALUATION_DATE", "false")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _workflow(db_session) -> Checklist:
    checklist = Checklist(name="가상 점검 기준", is_active=True)
    db_session.add(checklist)
    db_session.flush()
    db_session.add(
        DocumentRequirement(
            checklist_id=checklist.id,
            document_type=DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
            required=True,
        )
    )
    db_session.commit()
    return checklist


def _project(client, db_session) -> str:
    workflow = {"id": str(_workflow(db_session).id)}
    created = client.post(
        "/api/v1/projects",
        json={"workflow_id": workflow["id"], "name": "p", "applicant_name": "가상 신청자"},
    )
    assert created.status_code == 201
    return created.json()["id"]


def _verify(client, project_id: str, requested: str | None):
    body = {} if requested is None else {"evaluation_date": requested}
    return client.post(f"/api/v1/projects/{project_id}/verify", json=body)


def test_client_date_is_ignored_when_flag_is_off(client, db_session, applicant_mode):
    project_id = _project(client, db_session)
    response = _verify(client, project_id, "2001-01-01")
    assert response.status_code == 200
    assert response.json()["evaluation_date"] == date.today().isoformat()


def test_client_date_is_used_and_recorded_in_test_mode(client, monkeypatch, db_session):
    monkeypatch.setenv("ALLOW_CLIENT_EVALUATION_DATE", "true")
    get_settings.cache_clear()
    try:
        project_id = _project(client, db_session)
        response = _verify(client, project_id, "2026-08-03")
        assert response.status_code == 200
        assert response.json()["evaluation_date"] == "2026-08-03"
        from sqlalchemy import select

        from app.models.entities import ValidationResult

        rows = db_session.scalars(
            select(ValidationResult).where(ValidationResult.project_id == uuid.UUID(project_id))
        ).all()
        assert rows and all(
            (row.details or {}).get("evaluation_date_source") == "client_supplied_test_mode"
            for row in rows
        )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_admin_fixed_date_policy_overrides_a_client_date(client, db_session, monkeypatch):
    monkeypatch.setenv("ALLOW_CLIENT_EVALUATION_DATE", "false")
    monkeypatch.setenv("CHECK_DATE_MODE", "fixed")
    monkeypatch.setenv("CHECK_DATE_FIXED", "2026-10-05")
    get_settings.cache_clear()
    try:
        project_id = _project(client, db_session)
        response = _verify(client, project_id, "2001-01-01")
        assert response.json()["evaluation_date"] == "2026-10-05"
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_fixed_mode_without_a_date_refuses_to_start(monkeypatch):
    monkeypatch.setenv("CHECK_DATE_MODE", "fixed")
    monkeypatch.delenv("CHECK_DATE_FIXED", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError):
            get_settings()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_admin_endpoints_are_unreachable_when_admin_is_off(client, db_session, applicant_mode):
    project_id = _project(client, db_session)
    workflow_id = str(_workflow(db_session).id)
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 404
    assert client.post("/api/v1/checklists", json={"name": "x"}).status_code == 404
    assert (
        client.patch(f"/api/v1/checklists/{workflow_id}", json={"name": "x"}).status_code == 404
    )
    review = client.post(
        f"/api/v1/projects/{project_id}/documents/{uuid.uuid4()}/fields/gpa/review",
        json={"decision": "CONFIRMED", "reviewer_label": "applicant"},
    )
    assert review.status_code == 404
    # the project still exists
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 200


def test_applicant_cannot_reach_ready_through_date_or_confirmation(client, db_session, applicant_mode):
    """Nothing uploaded, so the submission cannot be READY, whatever date or confirmation is sent."""
    project_id = _project(client, db_session)
    for requested in ("1999-01-01", "2999-12-31", None):
        response = _verify(client, project_id, requested)
        assert response.status_code == 200
        assert response.json()["status"] != OverallStatus.READY.value
    client.post(
        f"/api/v1/projects/{project_id}/documents/{uuid.uuid4()}/fields/gpa/review",
        json={"decision": "CONFIRMED", "reviewer_label": "applicant"},
    )
    final = client.get(f"/api/v1/projects/{project_id}/verification").json()
    assert final["status"] != OverallStatus.READY.value
