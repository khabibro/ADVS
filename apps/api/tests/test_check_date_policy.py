"""The check date of a submission comes from the check-date policy of its checklist version (server side)."""

from datetime import date

from fastapi.testclient import TestClient
from test_phase_e2_overview import _both_valid, _overview
from test_submission_verification_api import _business_project

from app.models.entities import ChecklistRevision


def _set_policy(client: TestClient, workflow_id, policy: dict) -> dict:
    detail = client.get(f"/api/v1/admin/workflows/{workflow_id}").json()
    criteria = {**detail["criteria"], "evaluation_date_policy": policy}
    response = client.put(
        f"/api/v1/admin/workflows/{workflow_id}/criteria",
        json={
            "criteria": criteria,
            "editor": "관리자",
            "note": "점검일 정책",
            "expected_version": detail["version"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_a_fixed_policy_decides_the_suggested_and_the_used_check_date(
    client: TestClient, db_session
) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission, valid_until="2026-12-31")
    assert _overview(client, project.id)["suggested_evaluation_date"] == date.today().isoformat()

    _set_policy(client, project.checklist_id, {"mode": "FIXED", "date": "2026-10-30"})
    assert _overview(client, project.id)["suggested_evaluation_date"] == "2026-10-30"

    # The browser asks for a check without naming a date: the policy's date is used.
    response = client.post(f"/api/v1/projects/{project.id}/verify", json={})
    assert response.status_code == 200, response.text
    overview = _overview(client, project.id)
    assert overview["evaluation_date"] == "2026-10-30"
    assert overview["check_state"] == "CURRENT"


def test_a_policy_change_is_a_new_version_and_old_versions_stay_as_they_were(
    client: TestClient, db_session
) -> None:
    project, _, _ = _business_project(db_session)
    before = client.get(f"/api/v1/admin/workflows/{project.checklist_id}").json()
    assert before["criteria"]["evaluation_date_policy"] == {"mode": "TODAY", "date": None}
    changed = _set_policy(client, project.checklist_id, {"mode": "FIXED", "date": "2023-10-07"})
    assert changed["version"] == before["version"] + 1
    assert changed["criteria"]["evaluation_date_policy"] == {"mode": "FIXED", "date": "2023-10-07"}
    snapshots = {
        r.version: r.snapshot["criteria"].get("evaluation_date_policy")
        for r in db_session.query(ChecklistRevision).filter_by(checklist_id=project.checklist_id)
    }
    assert snapshots[changed["version"]] == {"mode": "FIXED", "date": "2023-10-07"}
    assert snapshots[before["version"]] in (None, {"mode": "TODAY", "date": None})


def test_a_fixed_policy_without_a_date_is_refused(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    detail = client.get(f"/api/v1/admin/workflows/{project.checklist_id}").json()
    criteria = {**detail["criteria"], "evaluation_date_policy": {"mode": "FIXED"}}
    response = client.put(
        f"/api/v1/admin/workflows/{project.checklist_id}/criteria",
        json={"criteria": criteria, "expected_version": detail["version"]},
    )
    assert response.status_code == 422


def test_a_save_without_a_policy_keeps_the_fixed_date(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    fixed = _set_policy(client, project.checklist_id, {"mode": "FIXED", "date": "2026-10-30"})
    criteria = {k: v for k, v in fixed["criteria"].items() if k != "evaluation_date_policy"}
    response = client.put(
        f"/api/v1/admin/workflows/{project.checklist_id}/criteria",
        json={"criteria": criteria, "expected_version": fixed["version"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["criteria"]["evaluation_date_policy"] == {
        "mode": "FIXED",
        "date": "2026-10-30",
    }
