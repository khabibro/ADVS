"""Project-level auto-acceptance decisions over persisted fields (see
document_intelligence/auto_acceptance.py for the rules)."""

from __future__ import annotations

import re
import unicodedata
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
from app.document_intelligence.decision_robust import RuleSpec
from app.document_intelligence.internal_evidence import extract_facts
from app.models.entities import (
    Document,
    DocumentRequirement,
    FieldReview,
    Project,
    Submission,
    ValidationResult,
    ValidationRule,
)
from app.services.requirements import required_fields

Decisions = dict[tuple[uuid.UUID, str], AutoDecision]


def configured_strategy(project: Project | None) -> Strategy:
    settings = get_settings()
    if project is not None and (
        str(project.checklist_id) in settings.auto_accept_disabled_workflow_ids
    ):
        return Strategy.S0
    return parse_strategy(settings.auto_accept_strategy)


_SEMESTER_GPA_RE = re.compile(r"평점평균\s*[:：]?\s*(\d(?:\.\d{1,3})?)\s*/")


def semester_gpas(document: Document) -> tuple[float, ...]:
    values: list[float] = []
    for result in document.ocr_results:
        for line in result.lines or []:
            text = unicodedata.normalize("NFKC", str(line.get("text", "")))
            values.extend(float(match) for match in _SEMESTER_GPA_RE.findall(text))
    return tuple(values)


def latest_evaluation_date(db: Session, project_id: uuid.UUID) -> date | None:
    """The evaluation date of the project's stored verification, if any: the date every
    date-dependent decision was made against."""
    row = db.scalar(
        select(ValidationResult)
        .where(ValidationResult.project_id == project_id, ValidationResult.scope == "SUBMISSION")
        .limit(1)
    )
    value = (row.details or {}).get("evaluation_date") if row is not None else None
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


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


def _rule_specs(db: Session, project: Project) -> tuple[RuleSpec, ...]:
    """The workflow's active rules on decision-driving fields, as outcome specifications (used to
    decide whether a misreading could change any verification outcome)."""
    if project.checklist_id is None:
        return ()
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.rules))
        .where(DocumentRequirement.checklist_id == project.checklist_id)
    ).all()
    specs: list[RuleSpec] = []
    for requirement in requirements:
        try:
            document_type = DocumentType(requirement.document_type)
        except ValueError:
            continue
        if requirement.required and "valid_until" in required_fields(requirement):
            specs.append(RuleSpec(document_type, "valid_until", "on_or_after_ref"))
        for rule in requirement.rules:
            params = rule.params or {}
            field = str(params.get("field", ""))
            if rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE.value:
                specs.append(
                    RuleSpec(
                        document_type,
                        "issue_date",
                        "max_age",
                        days=int(params.get("max_age_days", 90)),
                    )
                )
            elif rule.rule_type == RuleType.DATE_NOT_EXPIRED.value:
                specs.append(
                    RuleSpec(
                        document_type, str(params.get("field", "valid_until")), "on_or_after_ref"
                    )
                )
            elif rule.rule_type == RuleType.DATE_COMPARISON.value and field:
                operator = params.get("operator")
                bound = params.get("expected_value")
                if (
                    params.get("comparison_source") == "EVALUATION_DATE"
                    and operator == "ON_OR_AFTER"
                ):
                    specs.append(RuleSpec(document_type, field, "on_or_after_ref"))
                elif bound and operator in ("ON_OR_BEFORE", "ON_OR_AFTER"):
                    try:
                        parsed = date.fromisoformat(str(bound))
                    except ValueError:
                        continue
                    specs.append(
                        RuleSpec(
                            document_type,
                            field,
                            "on_or_before" if operator == "ON_OR_BEFORE" else "on_or_after",
                            bound_date=parsed,
                        )
                    )
            elif rule.rule_type == RuleType.NUMERIC_COMPARISON.value and field:
                operator = params.get("operator")
                try:
                    number = float(str(params.get("expected_value")))
                except ValueError:
                    continue
                specs.append(
                    RuleSpec(
                        document_type,
                        field,
                        "at_least" if operator == "GREATER_THAN_OR_EQUAL" else "at_most",
                        bound_number=number,
                    )
                )
    return tuple(specs)


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
        reference_date = latest_evaluation_date(db, project.id)
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
        facts = (
            extract_facts(
                [
                    {
                        "page_number": r.page_number,
                        "lines": r.lines or [],
                        "metadata": r.metadata_json or {},
                    }
                    for r in document.ocr_results
                ]
            )
            if any(
                "ocr" in {entry.get("source_kind") for entry in (f.evidence or [])}
                for f in document.extracted_fields
            )
            else None
        )
        gpas = semester_gpas(document) if document_type == DocumentType.TRANSCRIPT else ()
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
                    peer_values=gpas if item.field_name == "gpa" else (),
                    facts=facts,
                )
            )
    max_age, gpa_threshold = _workflow_boundaries(db, project)
    context = ProjectContext(
        company_name=project.company_name,
        applicant_name=project.applicant_name,
        reference_date=reference_date,
        issue_max_age_days=max_age,
        gpa_threshold=gpa_threshold,
        rules=_rule_specs(db, project),
    )
    return decide(inputs, context, strategy)
