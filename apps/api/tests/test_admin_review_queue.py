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
