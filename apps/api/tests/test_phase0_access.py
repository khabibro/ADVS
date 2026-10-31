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


TOKENS: dict[str, str] = {}


def _project(client, db_session) -> str:
    workflow = {"id": str(_workflow(db_session).id)}
    created = client.post(
        "/api/v1/projects",
        json={"workflow_id": workflow["id"], "name": "p", "applicant_name": "가상 신청자"},
    )
    assert created.status_code == 201
    TOKENS[created.json()["id"]] = created.json()["access_token"]
    return created.json()["id"]


def _h(project_id: str) -> dict[str, str]:
    return {"X-Submission-Token": TOKENS[project_id]}


def _verify(client, project_id: str, requested: str | None):
    body = {} if requested is None else {"evaluation_date": requested}
    return client.post(f"/api/v1/projects/{project_id}/verify", json=body, headers=_h(project_id))


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
    assert (
        client.delete(f"/api/v1/projects/{project_id}", headers=_h(project_id)).status_code == 404
    )
    assert client.post("/api/v1/checklists", json={"name": "x"}).status_code == 404
    assert client.patch(f"/api/v1/checklists/{workflow_id}", json={"name": "x"}).status_code == 404
    review = client.post(
        f"/api/v1/projects/{project_id}/documents/{uuid.uuid4()}/fields/gpa/review",
        json={"decision": "CONFIRMED", "reviewer_label": "applicant"},
        headers=_h(project_id),
    )
    assert review.status_code == 404
    # the project still exists
    assert client.get(f"/api/v1/projects/{project_id}", headers=_h(project_id)).status_code == 200


def test_applicant_cannot_reach_ready_through_date_or_confirmation(
    client, db_session, applicant_mode
):
    """Nothing uploaded, so the submission cannot be READY, whatever date or confirmation is sent."""
    project_id = _project(client, db_session)
    for requested in ("1999-01-01", "2999-12-31", None):
        response = _verify(client, project_id, requested)
        assert response.status_code == 200
        assert response.json()["status"] != OverallStatus.READY.value
    client.post(
        f"/api/v1/projects/{project_id}/documents/{uuid.uuid4()}/fields/gpa/review",
        json={"decision": "CONFIRMED", "reviewer_label": "applicant"},
        headers=_h(project_id),
    )
    final = client.get(f"/api/v1/projects/{project_id}/verification", headers=_h(project_id)).json()
    assert final["status"] != OverallStatus.READY.value


# ---- per-submission link -------------------------------------------------------------------


def test_a_submission_needs_its_own_token(client, db_session, applicant_mode):
    first, second = _project(client, db_session), _project(client, db_session)
    url = f"/api/v1/projects/{first}"
    assert client.get(url).status_code == 404  # no token
    assert client.get(url, headers={"X-Submission-Token": "wrong"}).status_code == 404
    assert client.get(url, headers=_h(second)).status_code == 404  # another submission's token
    assert client.get(url, headers=_h(first)).status_code == 200
    assert client.get(f"{url}?token={TOKENS[first]}").status_code == 200  # for <img> requests


def test_listing_all_submissions_is_not_public(client, db_session, applicant_mode):
    _project(client, db_session)
    assert client.get("/api/v1/projects").status_code == 404
    assert client.get("/api/v1/project-summaries").status_code == 404


def test_document_routes_are_covered_by_the_project_token(client, db_session, applicant_mode):
    import fitz

    pdf = fitz.open()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    project_id = _project(client, db_session)
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("blank.pdf", data, "application/pdf")},
        headers=_h(project_id),
    )
    document_id = upload.json()["id"]
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/pages").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}", headers=_h(project_id)).status_code == 200
    other = _project(client, db_session)
    assert client.get(f"/api/v1/documents/{document_id}", headers=_h(other)).status_code == 404


# ---- check date stored once ----------------------------------------------------------------


class _FakeDate(date):
    current = date(2026, 10, 5)

    @classmethod
    def today(cls):
        return cls.current


def test_check_date_is_stored_once_and_reused_a_week_later(
    client, db_session, applicant_mode, monkeypatch
):
    monkeypatch.setattr("app.core.access.date", _FakeDate)
    _FakeDate.current = date(2026, 10, 5)
    project_id = _project(client, db_session)
    first = _verify(client, project_id, None).json()["evaluation_date"]
    _FakeDate.current = date(2026, 10, 12)
    again = _verify(client, project_id, None).json()["evaluation_date"]
    assert first == again == "2026-10-05"
    # a new submission made a week later gets its own date
    other = _project(client, db_session)
    assert _verify(client, other, None).json()["evaluation_date"] == "2026-10-12"


def test_admin_recheck_changes_the_date_with_a_logged_reason(client, db_session, monkeypatch):
    project_id = _project(client, db_session)
    monkeypatch.setenv("ALLOW_CLIENT_EVALUATION_DATE", "false")
    get_settings.cache_clear()
    try:
        _verify(client, project_id, None)
        too_short = client.post(f"/api/v1/projects/{project_id}/recheck", json={"reason": "x"})
        assert too_short.status_code == 422
        done = client.post(
            f"/api/v1/projects/{project_id}/recheck",
            json={"reason": "late upload accepted by staff", "check_date": "2026-10-20"},
        )
        assert done.status_code == 200
        assert done.json()["evaluation_date"] == "2026-10-20"
        from sqlalchemy import select

        from app.models.entities import AuditLog

        log = db_session.scalars(
            select(AuditLog).where(AuditLog.project_id == uuid.UUID(project_id))
        ).all()
        assert [row.event_name for row in log] == ["check_date_changed"]
        assert log[0].metadata_json["reason"] == "late upload accepted by staff"
        assert log[0].metadata_json["new"] == "2026-10-20"
        # later checks keep the new date
        assert _verify(client, project_id, None).json()["evaluation_date"] == "2026-10-20"
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_recheck_is_unreachable_when_admin_is_off(client, db_session, applicant_mode):
    project_id = _project(client, db_session)
    response = client.post(
        f"/api/v1/projects/{project_id}/recheck",
        json={"reason": "applicant tries it"},
        headers=_h(project_id),
    )
    assert response.status_code == 404


# ---- core flow with default settings (both flags off) ---------------------------------------


def test_core_flow_with_default_settings(client, db_session, applicant_mode):
    """create submission -> upload -> verify -> status, as an applicant with only the link."""
    import fitz

    pdf = fitz.open()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    project_id = _project(client, db_session)
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("blank.pdf", data, "application/pdf")},
        headers=_h(project_id),
    )
    assert upload.status_code == 201
    verify = _verify(client, project_id, "1999-01-01")
    assert verify.status_code == 200
    assert verify.json()["evaluation_date"] == date.today().isoformat()
    assert verify.json()["status"] != OverallStatus.READY.value
    status_ = client.get(f"/api/v1/projects/{project_id}/overview", headers=_h(project_id))
    assert status_.status_code == 200
