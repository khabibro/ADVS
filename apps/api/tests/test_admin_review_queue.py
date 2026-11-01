"""Reviewer queue API: list, filters, sort, detail and decision log (made-up values)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.domain import DocumentType
from app.models.entities import Project
from tests.test_field_reviews import _document, _project, _review


def finalised(db_session, project: Project, days_ago: int) -> None:
    project.finalised_at = datetime.now(UTC) - timedelta(days=days_ago)
    db_session.commit()


def make(db_session, days_ago: int, name: str):
    project, submission = _project(db_session, transcript=True)
    project.name = name
    project.applicant_name = name
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.85", 0.80)}
    )
    finalised(db_session, project, days_ago)
    return project, document


def test_queue_lists_open_items_oldest_first_with_facets(client: TestClient, db_session):
    older, _ = make(db_session, 5, "큐테스트오래됨")
    newer, _ = make(db_session, 1, "큐테스트최근")
    body = client.get("/api/v1/admin/review-queue", params={"q": "큐테스트"}).json()
    assert [i["project_id"] for i in body["items"]] == [str(older.id), str(newer.id)]
    first = body["items"][0]
    assert (first["field_name"], first["field_label"], first["queue_status"]) == (
        "gpa",
        "평점",
        "PENDING",
    )
    assert body["facets"]["fields"][0]["value"] == "gpa"
    newest = client.get(
        "/api/v1/admin/review-queue", params={"q": "큐테스트", "sort": "NEWEST"}
    ).json()
    assert newest["items"][0]["project_id"] == str(newer.id)


def test_queue_filters_and_drafts(client: TestClient, db_session):
    project, document = make(db_session, 2, "큐필터")
    wrong = client.get(
        "/api/v1/admin/review-queue", params={"q": "큐필터", "field_name": "student_name"}
    ).json()
    assert wrong["total"] == 0
    project.finalised_at = None
    db_session.commit()
    hidden = client.get("/api/v1/admin/review-queue", params={"q": "큐필터"}).json()
    shown = client.get(
        "/api/v1/admin/review-queue", params={"q": "큐필터", "include_drafts": True}
    ).json()
    assert (hidden["total"], shown["total"]) == (0, 1)
    assert client.get("/api/v1/admin/review-queue", params={"sort": "RANDOM"}).status_code == 400


def test_decided_items_leave_the_open_list_and_show_in_the_log(client: TestClient, db_session):
    project, document = make(db_session, 2, "큐결정")
    assert _review(client, project.id, document.id, "gpa", "CANNOT_DETERMINE").status_code == 201
    opened = client.get("/api/v1/admin/review-queue", params={"q": "큐결정"}).json()
    decided = client.get(
        "/api/v1/admin/review-queue", params={"q": "큐결정", "status": "DECIDED"}
    ).json()
    assert (opened["total"], decided["total"]) == (0, 1)
    log = client.get("/api/v1/admin/review-log", params={"project_id": str(project.id)}).json()
    assert log["total"] == 1
    entry = log["items"][0]
    assert (entry["decision"], entry["reviewer_label"], entry["field_label"]) == (
        "CANNOT_DETERMINE",
        "reviewer-1",
        "평점",
    )
    assert client.get("/api/v1/admin/review-log", params={"decision": "BOGUS"}).status_code == 422


def test_detail_has_item_siblings_and_history(client: TestClient, db_session):
    project, document = make(db_session, 2, "큐상세")
    url = f"/api/v1/admin/review-queue/{project.id}/{document.id}/gpa"
    detail = client.get(url).json()
    assert detail["open"] is True
    assert detail["item"]["machine_normalized_value"] == "3.85"
    assert detail["field_label"] == "평점"
    assert detail["history"] == []
    _review(client, project.id, document.id, "gpa", "CONFIRMED")
    after = client.get(url).json()
    assert after["open"] is False and after["item"] is None
    assert [h["decision"] for h in after["history"]] == ["CONFIRMED"]
    missing = client.get(f"/api/v1/admin/review-queue/{project.id}/{project.id}/gpa")
    assert missing.status_code == 404


def test_one_click_fields_are_marked_and_filterable(client: TestClient, db_session):
    project, document = make(db_session, 2, "큐원클릭")
    body = client.get("/api/v1/admin/review-queue", params={"q": "큐원클릭"}).json()
    assert [(i["field_name"], i["one_click"]) for i in body["items"]] == [("gpa", True)]
    only = client.get(
        "/api/v1/admin/review-queue", params={"q": "큐원클릭", "one_click": True}
    ).json()
    assert only["total"] == 1
    detail = client.get(f"/api/v1/admin/review-queue/{project.id}/{document.id}/gpa").json()
    assert detail["one_click"] is True
    assert detail["project_open_items"] == 1 and detail["project_only_one_click"] is True


def test_decision_robust_values_are_listed_apart_and_can_be_confirmed(
    client: TestClient, db_session, monkeypatch
):
    from app.document_intelligence.auto_acceptance import AutoDecision
    from app.services import review_queue

    project, submission = _project(db_session, transcript=True)
    project.name = project.applicant_name = "큐로버스트"
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.61", 0.99)}
    )
    finalised(db_session, project, 1)
    robust = AutoDecision(accepted=True, strategy="S5", robust=True, rule_id="gpa:DECISION_ROBUST")
    monkeypatch.setattr(
        review_queue, "decisions_for_project", lambda db, p: {(document.id, "gpa"): robust}
    )
    params = {"q": "큐로버스트"}
    assert client.get("/api/v1/admin/review-queue", params=params).json()["total"] == 0
    listed = client.get("/api/v1/admin/review-queue", params={**params, "status": "ROBUST"}).json()
    (row,) = listed["items"]
    assert (row["queue_status"], row["confirmation"], row["one_click"]) == (
        "AUTO_ROBUST",
        "DECISION_ROBUST",
        True,
    )
    url = f"/api/v1/admin/review-queue/{project.id}/{document.id}/gpa"
    detail = client.get(url).json()
    assert detail["open"] is True and detail["item"]["auto_acceptance"]["confirmation"] == (
        "DECISION_ROBUST"
    )
    assert _review(client, project.id, document.id, "gpa", "CONFIRMED").status_code == 201
    after = client.get("/api/v1/admin/review-queue", params={**params, "status": "ROBUST"}).json()
    assert after["total"] == 0  # a person confirmed it: no longer "value not confirmed"
