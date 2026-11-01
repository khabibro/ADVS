"""Who may do what, until accounts exist.

Admin / reviewer endpoints are switched off (404, as if absent) unless ADMIN_ENABLED is set, so the
applicant deployment cannot reach them. The check date is decided by the server: an applicant-sent
date is ignored unless the test-harness flag is on.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import api_error
from app.db.session import get_db
from app.models.entities import Document, Project, Submission

SOURCE_CLIENT_TEST_MODE = "client_supplied_test_mode"
SOURCE_SUBMISSION_DATE = "server_submission_date"
SOURCE_FIXED_POLICY = "admin_fixed_date"
SOURCE_ADMIN_RECHECK = "admin_recheck"
SOURCE_DRAFT_PREVIEW = "draft_preview"
SOURCE_FINALISED = "applicant_finalised"


def require_admin() -> None:
    if not get_settings().admin_enabled:
        raise api_error("RESOURCE_NOT_FOUND", "Not found", status.HTTP_404_NOT_FOUND)


@dataclass(frozen=True)
class CheckDate:
    value: date
    source: str


def resolve_check_date(requested: date | None, project: Project | None = None) -> CheckDate:
    """Client date (test mode only), else the pinned checklist version's policy, else the server."""
    settings = get_settings()
    if requested is not None and settings.allow_client_evaluation_date:
        return CheckDate(requested, SOURCE_CLIENT_TEST_MODE)
    version = project.checklist_version if project is not None else None
    if version is not None:
        policy = (version.document or {}).get("check_date", {})
        if policy.get("policy") == "FIXED" and policy.get("fixed_date"):
            return CheckDate(date.fromisoformat(str(policy["fixed_date"])), SOURCE_FIXED_POLICY)
        return CheckDate(date.today(), SOURCE_SUBMISSION_DATE)
    if settings.check_date_mode == "fixed" and settings.check_date_fixed is not None:
        return CheckDate(settings.check_date_fixed, SOURCE_FIXED_POLICY)
    return CheckDate(date.today(), SOURCE_SUBMISSION_DATE)


def check_date_for_project(db: Session, project: Project, requested: date | None) -> CheckDate:
    """The check date of a submission.

    Test mode (client date allowed) uses the requested date. A finalised (or admin re-checked)
    submission reuses its stored date. A draft is checked as a preview with the policy date
    (today, or the fixed admin date) and nothing is stored, so a later upload is never judged
    against a date from before it."""
    if requested is not None and get_settings().allow_client_evaluation_date:
        return CheckDate(requested, SOURCE_CLIENT_TEST_MODE)
    if project.check_date is not None:
        return CheckDate(project.check_date, project.check_date_source or SOURCE_FINALISED)
    return CheckDate(resolve_check_date(None, project).value, SOURCE_DRAFT_PREVIEW)


def finalise_check_date(db: Session, project: Project) -> CheckDate:
    """Freeze the check date at the applicant's explicit submission (idempotent)."""
    if project.check_date is not None:
        return CheckDate(project.check_date, project.check_date_source or SOURCE_FINALISED)
    chosen = resolve_check_date(None, project)
    project.check_date, project.check_date_source = chosen.value, SOURCE_FINALISED
    project.finalised_at = datetime.now(UTC)
    db.flush()
    return CheckDate(chosen.value, SOURCE_FINALISED)


def _supplied_token(request: Request) -> str | None:
    return request.headers.get("x-submission-token") or request.query_params.get("token")


def applicant_access(request: Request, db: Session = Depends(get_db)) -> None:
    """Every route that names a project (or a document of one) needs that submission's token.

    Wrong, missing or unknown -> 404, so existence is not revealed. With ADMIN_ENABLED the
    admin / reviewer deployment is not asked for a token (it has no accounts yet)."""
    if get_settings().admin_enabled:
        return
    params = request.path_params
    project_id: uuid.UUID | None = None
    try:
        if "project_id" in params:
            project_id = uuid.UUID(str(params["project_id"]))
        elif "document_id" in params:
            document_id = uuid.UUID(str(params["document_id"]))
            project_id = db.scalar(
                select(Submission.project_id)
                .join(Document, Document.submission_id == Submission.id)
                .where(Document.id == document_id)
            )
    except ValueError:
        project_id = None
    if "project_id" not in params and "document_id" not in params:
        return
    token = _supplied_token(request)
    stored = (
        db.scalar(select(Project.access_token).where(Project.id == project_id))
        if project_id
        else None
    )
    if not token or stored is None or not secrets.compare_digest(token, stored):
        raise api_error("RESOURCE_NOT_FOUND", "Not found", status.HTTP_404_NOT_FOUND)
