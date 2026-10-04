"""Document diagnostics computed from current effective, policy-gated values."""

from dataclasses import replace
from datetime import UTC, date
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.evidence_sufficiency import (
    EvidenceAssessmentState,
    EvidenceSufficiencyPolicy,
)
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import (
    ConfiguredRule,
    ValidationEngine,
    ValidationIssue,
)
from app.models.entities import Document, DocumentRequirement, Project, Submission
from app.services.requirements import required_fields

_KST = ZoneInfo("Asia/Seoul")


def submission_reference_date(submission: Submission | None) -> date | None:
    """The submission's own calendar date in Asia/Seoul -- what "valid at
    submission time" actually means (audit: validity/issue-date-age was
    measured against the server's local `date.today()` instead, so
    re-checking the same submission on a later day, or on a server in a
    different timezone, could flip the result).

    `Submission.created_at` is the submission's own timestamp (set once,
    at creation, by the database -- see TimestampMixin); no new column or
    migration is needed. A naive timestamp (should not occur given the
    column is `DateTime(timezone=True)`, but SQLite does not always
    enforce that) is treated as UTC rather than guessed at. Returns None,
    never a guess, only if no submission is resolvable at all."""
    if submission is None or submission.created_at is None:
        return None
    timestamp = submission.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(_KST).date()


def policy_gated_fields(fields: list[ExtractedValue]) -> list[ExtractedValue]:
    policy = EvidenceSufficiencyPolicy()
    result = []
    for field in fields:
        assessment = policy.assess(
            normalized_value=field.normalized_value,
            needs_review=field.needs_review,
            evidence=[item.to_dict() for item in field.evidence] if field.evidence else None,
            field_confidence=field.confidence,
            extraction_method=field.extraction_method,
        )
        result.append(
            field
            if assessment.state == EvidenceAssessmentState.SUFFICIENT
            else replace(field, normalized_value=None, needs_review=True)
        )
    return result


def configured_document_rules(
    db: Session, project: Project | None, document_type: DocumentType
) -> list[ConfiguredRule] | None:
    if project is None or project.checklist_id is None:
        return None
    requirement = db.scalar(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.rules))
        .where(
            DocumentRequirement.checklist_id == project.checklist_id,
            DocumentRequirement.document_type == document_type.value,
        )
    )
    if requirement is None:
        return None
    configured = [
        ConfiguredRule(RuleType(row.rule_type), Severity(row.severity), row.params or {})
        for row in requirement.rules
    ]
    # Explicit REQUIRED_FIELD rules ADD to this requirement's default
    # fields; they do not replace the check for a default field they don't
    # name (audit F-001). A bare rule (no `field` param) already names
    # every field in the document type's own schema -- see
    # _explicit_required_fields in validation/engine.py, which this
    # mirrors -- so it alone still covers everything without an auto-fill.
    explicitly_named = {
        rule.params.get("field")
        for rule in configured
        if rule.rule_type == RuleType.REQUIRED_FIELD and rule.params.get("field")
    }
    has_blanket_rule = any(
        rule.rule_type == RuleType.REQUIRED_FIELD and not rule.params.get("field")
        for rule in configured
    )
    if not has_blanket_rule:
        configured.extend(
            ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": name})
            for name in required_fields(requirement)
            if name not in explicitly_named
        )
    return configured


def validate_effective_document(
    db: Session, document: Document, document_type: DocumentType, fields: list[ExtractedValue]
) -> tuple[list[ValidationIssue], Project | None]:
    submission = db.get(Submission, document.submission_id)
    project = db.get(Project, submission.project_id) if submission else None
    duplicate = bool(
        db.scalar(
            select(Document.id)
            .where(
                Document.submission_id == document.submission_id,
                Document.checksum_sha256 == document.checksum_sha256,
                Document.id != document.id,
            )
            .limit(1)
        )
    )
    issues = ValidationEngine().validate_document(
        None,
        document_type,
        fields,
        project.applicant_name if project else None,
        project.company_name if project else None,
        duplicate,
        configured_document_rules(db, project, document_type),
        submission_reference_date(submission),
    )
    return issues, project
