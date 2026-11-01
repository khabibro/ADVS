"""The reviewer queue across submissions: open items to look at, and the log of decisions.

Built on FieldReviewService.review_items (the same per-submission list the applicant flow uses), so
what is open here is exactly what keeps a submission out of 제출 가능. Nothing here decides a value;
decisions go through the existing review endpoint.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.checklists.catalog import document_label, field_label
from app.models.entities import Checklist, FieldReview, Project
from app.services.reviews import FieldReviewService

MAX_PROJECTS = 400
OPEN = ("PENDING", "STALE")
DECIDED = ("REJECTED", "CANNOT_DETERMINE")
STATUS_FILTERS = {"OPEN": OPEN, "DECIDED": DECIDED, "ALL": OPEN + DECIDED}
SORTS = ("OLDEST", "NEWEST", "WORKFLOW", "DOCUMENT")


@dataclass(frozen=True)
class QueueFilter:
    status: str = "OPEN"
    workflow: str | None = None
    document_type: str | None = None
    field_name: str | None = None
    query: str | None = None
    sort: str = "OLDEST"
    include_drafts: bool = False


def _waiting_since(project: Project) -> datetime:
    return project.finalised_at or project.created_at


def _row(project: Project, item: dict[str, Any]) -> dict[str, Any]:
    checklist: Checklist | None = project.checklist
    version = project.checklist_version
    return {
        "project_id": project.id,
        "project_name": project.name,
        "applicant_name": project.applicant_name,
        "company_name": project.company_name,
        "workflow_key": checklist.key if checklist else None,
        "workflow_name": checklist.name if checklist else None,
        "version_number": version.number if version else None,
        "document_id": item["document_id"],
        "document_type": item["document_type"].value,
        "document_label": document_label(item["document_type"]),
        "field_name": item["field_name"],
        "field_label": field_label(item["field_name"]),
        "machine_value": item["machine_normalized_value"],
        "confidence": item["confidence"],
        "queue_status": item["queue_status"],
        "issue_code": item["issue_code"],
        "waiting_since": _waiting_since(project),
        "finalised": project.finalised_at is not None,
    }


def _sort_key(sort: str):
    if sort == "WORKFLOW":
        return lambda r: (r["workflow_name"] or "", r["waiting_since"], str(r["project_id"]))
    if sort == "DOCUMENT":
        return lambda r: (r["document_label"], r["field_label"], r["waiting_since"])
    return lambda r: (
        r["waiting_since"],
        str(r["project_id"]),
        r["document_label"],
        r["field_name"],
    )


class ReviewQueueService:
    def __init__(self, reviews: FieldReviewService | None = None) -> None:
        self.reviews = reviews or FieldReviewService()

    def _projects(self, db: Session, include_drafts: bool) -> list[Project]:
        statement = (
            select(Project)
            .options(joinedload(Project.checklist), joinedload(Project.checklist_version))
            .order_by(Project.created_at.desc())
            .limit(MAX_PROJECTS)
        )
        if not include_drafts:
            statement = statement.where(Project.finalised_at.is_not(None))
        return list(db.scalars(statement).unique().all())

    def rows(self, db: Session, flt: QueueFilter) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        everything: list[dict[str, Any]] = []
        for project in self._projects(db, flt.include_drafts):
            for item in self.reviews.review_items(db, project.id) or []:
                everything.append(_row(project, item))
        wanted = STATUS_FILTERS.get(flt.status, OPEN)
        needle = (flt.query or "").strip().lower()

        def match(row: dict[str, Any], skip: str | None = None) -> bool:
            if row["queue_status"] not in wanted:
                return False
            checks = (
                ("workflow", flt.workflow, row["workflow_key"]),
                ("document", flt.document_type, row["document_type"]),
                ("field", flt.field_name, row["field_name"]),
            )
            if any(name != skip and value and value != got for name, value, got in checks):
                return False
            if needle:
                text = " ".join(
                    str(row[k] or "") for k in ("project_name", "applicant_name", "company_name")
                ).lower()
                return needle in text
            return True

        selected = sorted(
            (r for r in everything if match(r)),
            key=_sort_key(flt.sort),
            reverse=flt.sort == "NEWEST",
        )

        def facet(name: str, key: str, label: str) -> list[dict[str, Any]]:
            counts = Counter((r[key], r[label]) for r in everything if match(r, skip=name))
            return [
                {"value": value, "label": text or str(value), "count": count}
                for (value, text), count in sorted(counts.items(), key=lambda kv: str(kv[0][1]))
                if value
            ]

        facets = {
            "workflows": facet("workflow", "workflow_key", "workflow_name"),
            "documents": facet("document", "document_type", "document_label"),
            "fields": facet("field", "field_name", "field_label"),
            "status": dict(Counter(r["queue_status"] for r in everything)),
        }
        return selected, facets

    def log(
        self,
        db: Session,
        *,
        decision: str | None,
        project_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        base = select(FieldReview)
        if decision:
            base = base.where(FieldReview.decision == decision)
        if project_id:
            base = base.where(FieldReview.project_id == project_id)
        reviews = list(
            db.scalars(base.order_by(FieldReview.reviewed_at.desc(), FieldReview.id)).all()
        )
        page = reviews[offset : offset + limit]
        projects = {
            p.id: p
            for p in db.scalars(
                select(Project).where(Project.id.in_({r.project_id for r in page}))
            ).all()
        }
        out = []
        for r in page:
            project = projects.get(r.project_id)
            out.append(
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "project_name": project.name if project else None,
                    "document_id": r.document_id,
                    "document_label": _document_label_of(db, r),
                    "field_name": r.field_name,
                    "field_label": field_label(r.field_name),
                    "decision": r.decision,
                    "machine_value": r.original_normalized_value,
                    "reviewed_value": r.reviewed_normalized_value,
                    "reviewer_label": r.reviewer_label,
                    "note": r.note,
                    "reviewed_at": r.reviewed_at,
                    "is_current": r.is_current,
                    "stale": r.stale_at is not None,
                    "superseded": r.superseded_at is not None,
                }
            )
        return len(reviews), out


def _document_label_of(db: Session, review: FieldReview) -> str:
    document = review.document
    return document_label(document.document_type) if document else "삭제된 서류"
