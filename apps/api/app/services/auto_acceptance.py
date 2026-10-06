"""Project-level auto-acceptance decisions over persisted fields (see
document_intelligence/auto_acceptance.py for the rules)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.domain import DocumentType, ProcessingStatus, RuleType
from app.document_intelligence.auto_acceptance import (
    AutoDecision,
    FieldInput,
    ProjectContext,
    SecondPassInput,
    Strategy,
    decide,
    parse_strategy,
)
from app.models.entities import (
    Document,
    DocumentRequirement,
    FieldReview,
    Project,
    Submission,
    ValidationRule,
)

Decisions = dict[tuple[uuid.UUID, str], AutoDecision]


def configured_strategy(project: Project | None) -> Strategy:
    settings = get_settings()
    if project is not None and (
        str(project.checklist_id) in settings.auto_accept_disabled_workflow_ids
    ):
        return Strategy.S0
    return parse_strategy(settings.auto_accept_strategy)


def second_pass_by_field(document: Document) -> dict[str, SecondPassInput]:
    found: dict[str, SecondPassInput] = {}
    for result in document.ocr_results:
        stored = (result.metadata_json or {}).get("second_pass") or {}
        for name, item in stored.items():
            found[name] = SecondPassInput(
                text=item.get("text"),
                normalized=item.get("normalized"),
                confidence=item.get("confidence"),
                preprocess=item.get("preprocess", ""),
            )
    return found


def _workflow_boundaries(db: Session, project: Project) -> tuple[int | None, float | None]:
    """The workflow's issue-date age limit and GPA threshold (the decision boundaries a
    second-pass-only value must stay clear of)."""
    if project.checklist_id is None:
        return None, None
    rules = db.scalars(
        select(ValidationRule)
        .join(DocumentRequirement, ValidationRule.requirement_id == DocumentRequirement.id)
        .where(DocumentRequirement.checklist_id == project.checklist_id)
    ).all()
    max_age: int | None = None
    threshold: float | None = None
    for rule in rules:
        params = rule.params or {}
        if rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE.value:
            max_age = int(params.get("max_age_days", 90))
        elif rule.rule_type == RuleType.NUMERIC_COMPARISON.value and params.get("field") == "gpa":
            try:
                threshold = float(str(params.get("expected_value")))
            except (TypeError, ValueError):
                continue
    return max_age, threshold


def decisions_for_project(
    db: Session, project: Project | None, reference_date: date | None = None
) -> Decisions:
    if project is None:
        return {}
    strategy = configured_strategy(project)
    if strategy == Strategy.S0:
        return {}
    documents = db.scalars(
        select(Document)
        .join(Submission)
        .options(selectinload(Document.extracted_fields), selectinload(Document.ocr_results))
        .where(
            Submission.project_id == project.id,
            Document.processing_status == ProcessingStatus.COMPLETED.value,
        )
        .execution_options(populate_existing=True)
    ).all()
    if reference_date is None:
        from app.services.document_validation import submission_reference_date

        submission = db.scalar(
            select(Submission).where(Submission.project_id == project.id).limit(1)
        )
        reference_date = submission_reference_date(submission)
    reviews = (
        {
            (item.document_id, item.field_name)
            for item in db.scalars(
                select(FieldReview).where(
                    FieldReview.project_id == project.id, FieldReview.is_current.is_(True)
                )
            ).all()
        }
        if documents
        else set()
    )
    inputs: list[FieldInput] = []
    for document in documents:
        try:
            document_type = DocumentType(document.document_type)
        except ValueError:
            continue
        if document_type == DocumentType.UNKNOWN or (document.classification_meta or {}).get(
            "needs_review"
        ):
            continue
        second = second_pass_by_field(document)
        for item in document.extracted_fields:
            kinds = {entry.get("source_kind") for entry in (item.evidence or [])}
            inputs.append(
                FieldInput(
                    document_id=document.id,
                    checksum=document.checksum_sha256,
                    document_type=document_type,
                    field_name=item.field_name,
                    value=item.normalized_value,
                    confidence=item.confidence,
                    ocr="ocr" in kinds,
                    needs_review=item.needs_review,
                    extraction_method=item.extraction_method,
                    second_pass=second.get(item.field_name),
                    has_current_review=(document.id, item.field_name) in reviews,
                )
            )
    max_age, gpa_threshold = _workflow_boundaries(db, project)
    context = ProjectContext(
        company_name=project.company_name,
        applicant_name=project.applicant_name,
        reference_date=reference_date,
        issue_max_age_days=max_age,
        gpa_threshold=gpa_threshold,
    )
    return decide(inputs, context, strategy)
