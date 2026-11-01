"""The admin checklist API: catalogue, draft/publish over HTTP, history, diff, rollback, audit."""

from __future__ import annotations

import copy
import uuid

import pytest

from app.checklists.service import ChecklistService, load_template

service = ChecklistService()


@pytest.fixture
def workflow(db_session):
    document = load_template("student")
    document["key"] = f"t-{uuid.uuid4().hex[:8]}"
    document["name_ko"] = f"API 테스트 {document['key']}"
    return service.create(db_session, document, "tester")


def base(client, workflow) -> dict:
    return client.get(f"/api/v1/admin/workflows/{workflow.id}").json()


def test_catalogue_serves_the_editor_options(client):
    catalog = client.get("/api/v1/admin/catalog").json()
    types = {d["type"]: d for d in catalog["documents"]}
    assert "UNKNOWN" not in types
    assert types["TRANSCRIPT"]["numeric_fields"] == ["gpa"]
    assert types["SME_CONFIRMATION_CERTIFICATE"]["has_valid_until"] is True
    assert {s["value"] for s in catalog["severities"]} == {"ERROR", "WARNING"}
    assert catalog["limits"]["max_age_days"] == {"min": 1, "max": 365}
    assert catalog["fixed_policies_ko"]


def test_workflow_read_has_a_sentence_for_every_rule(client, workflow):
    read = base(client, workflow)
    sentences = read["published"]["sentences"]
    assert read["draft"] is None and read["published"]["number"] == 1
    assert "90일 이내" in " ".join(
        s["text"] for s in sentences["documents"]["ENROLLMENT_CERTIFICATE"]
    )
    assert set(sentences["comparisons"]) == {"stu-id", "stu-name", "stu-birth", "stu-univ"}
    assert "3.0" in sentences["thresholds"]["gpa-min"]
    assert "바꿀 수 없습니다" in sentences["check_date"]


def test_edit_publish_history_diff_rollback_over_http(client, workflow):
    url = f"/api/v1/admin/workflows/{workflow.id}"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][0]["issue_date"]["max_age_days"] = 60
    saved = client.put(f"{url}/draft", json={"document": document}).json()
    assert saved["saved"] and saved["draft"]["revision"] == 1
    assert "60일 이내" in " ".join(
        s["text"] for s in saved["draft"]["sentences"]["documents"]["ENROLLMENT_CERTIFICATE"]
    )

    diff = client.get(f"{url}/diff").json()
    assert [c["kind"] for c in diff["changes"]] == ["CHANGED"]
    assert "90일" in diff["changes"][0]["before"] and "60일" in diff["changes"][0]["after"]

    published = client.post(f"{url}/publish", json={"change_note": "발급일 90→60일"}).json()
    assert published["number"] == 2
    history = client.get(f"{url}/versions").json()
    assert [v["number"] for v in history] == [2, 1]
    assert history[0]["change_note"] == "발급일 90→60일"

    assert client.get(f"{url}/diff", params={"from": 1, "to": 2}).json()["changes"]
    rolled = client.post(f"{url}/rollback", json={"to_version": 1, "change_note": "되돌림"}).json()
    assert rolled["number"] == 3 and rolled["rolled_back_to_number"] == 1
    assert client.get(f"{url}/versions/1").json()["status"] == "SUPERSEDED"

    audit = client.get("/api/v1/admin/audit", params={"checklist_id": str(workflow.id)}).json()
    assert [a["event"] for a in audit][:3] == [
        "checklist_rolled_back",
        "checklist_published",
        "checklist_draft_created",
    ]
    assert audit[0]["detail"]["rolled_back_to"] == 1 and audit[0]["version_number"] == 3


def test_invalid_draft_returns_korean_problems_with_paths(client, workflow):
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][0]["issue_date"]["max_age_days"] = 500
    response = client.put(
        f"/api/v1/admin/workflows/{workflow.id}/draft", json={"document": document}
    )
    assert response.status_code == 422
    problem = response.json()["detail"]["problems"][0]
    assert problem["path"] == "documents.0.issue_date.max_age_days"
    assert problem["code"] == "MAX_AGE_RANGE" and "365" in problem["message_ko"]


def test_stale_editor_gets_a_conflict(client, workflow):
    url = f"/api/v1/admin/workflows/{workflow.id}/draft"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][0]["issue_date"]["max_age_days"] = 80
    assert client.put(url, json={"document": document}).status_code == 200
    document["documents"][0]["issue_date"]["max_age_days"] = 70
    stale = client.put(url, json={"document": document, "expected_revision": 9})
    assert stale.status_code == 409 and "다른 관리자" in stale.json()["detail"]["message"]


def test_publish_without_acknowledging_a_loosening_is_refused(client, workflow):
    url = f"/api/v1/admin/workflows/{workflow.id}"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["comparisons"] = document["comparisons"][1:]
    client.put(f"{url}/draft", json={"document": document})
    refused = client.post(f"{url}/publish", json={"change_note": "비교 삭제"})
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "ACKNOWLEDGEMENT_REQUIRED"
    keys = sorted(p["code"] for p in refused.json()["detail"]["problems"])
    assert any(k.startswith("COMPARISON_REMOVED:") for k in keys)
    assert (
        client.post(
            f"{url}/publish", json={"change_note": "비교 삭제", "acknowledged_warnings": keys}
        ).status_code
        == 200
    )


def test_new_submissions_list_the_documents_of_their_version(client, workflow):
    url = f"/api/v1/admin/workflows/{workflow.id}"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][1]["requirement"] = "REQUIRED"
    client.put(f"{url}/draft", json={"document": document})
    client.post(
        f"{url}/publish", json={"change_note": "성적증명서 필수", "acknowledged_warnings": []}
    )
    first = client.post(
        "/api/v1/projects", json={"name": "a", "workflow_id": str(workflow.id)}
    ).json()
    assert {d["document_type"]: d["required"] for d in first["expected_documents"]}["TRANSCRIPT"]
    # rolling back does not change the submission that was already created
    client.post(f"{url}/rollback", json={"to_version": 1, "change_note": "되돌림"})
    after = client.get(f"/api/v1/projects/{first['id']}").json()
    assert {d["document_type"]: d["required"] for d in after["expected_documents"]}["TRANSCRIPT"]
    second = client.post(
        "/api/v1/projects", json={"name": "b", "workflow_id": str(workflow.id)}
    ).json()
    assert not {d["document_type"]: d["required"] for d in second["expected_documents"]}[
        "TRANSCRIPT"
    ]


# --- impact preview ------------------------------------------------------------------------------


def _draft_age(client, workflow, days: int) -> str:
    url = f"/api/v1/admin/workflows/{workflow.id}"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][0]["issue_date"]["max_age_days"] = days
    assert client.put(f"{url}/draft", json={"document": document}).status_code == 200
    return url


def test_tightening_changes_only_the_cases_between_the_old_and_new_limit(client, workflow):
    url = _draft_age(client, workflow, 60)
    scenarios = client.post(f"{url}/draft/preview").json()["scenarios"]
    assert scenarios["total"] > 20 and scenarios["errors"] == 0
    assert scenarios["transitions"] == [{"from": "READY", "to": "NEEDS_CORRECTION", "count": 3}]
    assert scenarios["newly_ready"] == 0
    assert {c["label"] for c in scenarios["cases"]} == {
        "재학증명서 발급 61일 전",
        "재학증명서 발급 89일 전",
        "재학증명서 발급 90일 전",
    }


def test_loosening_shows_newly_ready_cases_and_publish_needs_a_second_acknowledgement(
    client, workflow
):
    url = _draft_age(client, workflow, 200)
    scenarios = client.post(f"{url}/draft/preview").json()["scenarios"]
    assert scenarios["newly_ready"] > 0
    assert all(c["current"] != "READY" and c["draft"] == "READY" for c in scenarios["cases"])
    refused = client.post(f"{url}/publish", json={"change_note": "기간을 늘림"}).json()["detail"]
    keys = {p["code"] for p in refused["problems"]}
    assert "PREVIEW_NEWLY_READY:preview" in keys
    assert any(k.startswith("ISSUE_AGE_RAISED:") for k in keys)
    ok = client.post(
        f"{url}/publish", json={"change_note": "기간을 늘림", "acknowledged_warnings": sorted(keys)}
    )
    assert ok.status_code == 200


def test_preview_counts_stored_submissions(client, workflow):
    from tests.test_checklist_versions import _submit

    _submit(client, workflow.id, "2026년 08월 10일")  # 56 days before the 2026-10-05 check
    url = _draft_age(client, workflow, 30)
    submissions = client.post(f"{url}/draft/preview").json()["submissions"]
    assert submissions["total"] == 1


def test_validate_is_stateless_and_returns_problems_sentences_and_warnings(client, workflow):
    url = f"/api/v1/admin/workflows/{workflow.id}/validate"
    document = copy.deepcopy(base(client, workflow)["published"]["document"])
    document["documents"][0]["issue_date"]["max_age_days"] = 200
    ok = client.post(url, json={"document": document}).json()
    assert ok["problems"] == [] and "200일 이내" in " ".join(
        s["text"] for s in ok["sentences"]["documents"]["ENROLLMENT_CERTIFICATE"]
    )
    assert {w["key"] for w in ok["warnings"]} >= {
        "LONG_ISSUE_AGE:documents.0.issue_date",
        "ISSUE_AGE_RAISED:documents.ENROLLMENT_CERTIFICATE.issue_date",
    }
    document["documents"][0]["issue_date"]["max_age_days"] = 999
    bad = client.post(url, json={"document": document}).json()
    assert bad["problems"][0]["code"] == "MAX_AGE_RANGE" and bad["sentences"] == {}
    assert base(client, workflow)["draft"] is None  # nothing was saved
