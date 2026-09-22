from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.domain import (
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    RuleOutcome,
    RuleType,
    Severity,
)
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    RuleConfigurationError,
    RuleEvaluationResult,
    SubmissionRule,
    SubmissionVerificationEngine,
    SubmissionVerificationResult,
    VerificationContext,
    VerificationIssue,
)
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    Project,
    Submission,
    ValidationResult,
)

SUBMISSION_SCOPE = "SUBMISSION"


@dataclass(frozen=True)
class StoredSubmissionVerification:
    result: SubmissionVerificationResult | None
    evaluated_at: datetime | None
    is_current: bool


def invalidate_submission_verification(db: Session, project_id: uuid.UUID) -> None:
    """Invalidate the latest submission decision after any input mutation."""
    db.execute(
        delete(ValidationResult).where(
            ValidationResult.project_id == project_id,
            ValidationResult.scope == SUBMISSION_SCOPE,
        )
    )
    project = db.get(Project, project_id)
    if project is not None:
        project.status = OverallStatus.REVIEW_REQUIRED.value


def invalidate_document_project_verification(db: Session, document: Document) -> None:
    project_id = db.scalar(
        select(Submission.project_id).where(Submission.id == document.submission_id)
    )
    if project_id is not None:
        invalidate_submission_verification(db, project_id)


class SubmissionVerificationService:
    """Authoritative project-verification orchestration over persisted fields."""

    def __init__(self) -> None:
        self.engine = SubmissionVerificationEngine()

    def verify(
        self, db: Session, project_id: uuid.UUID, evaluation_date: date
    ) -> StoredSubmissionVerification:
        project = self._load_project(db, project_id)
        if project is None:
            raise LookupError("project not found")
        if project.checklist_id is None or project.checklist is None:
            raise ValueError("project has no workflow")
        requirements = self._requirements(project.checklist)
        documents = self._documents(db, project_id)
        result = self.engine.verify(
            project_id=project.id,
            workflow_id=project.checklist_id,
            requirements=requirements,
            documents=documents,
            context=VerificationContext(evaluation_date=evaluation_date),
        )
        evaluated_at = datetime.now(UTC)
        self._persist(db, project, result, evaluated_at)
        return StoredSubmissionVerification(result, evaluated_at, True)

    def get_latest(self, db: Session, project_id: uuid.UUID) -> StoredSubmissionVerification:
        project = self._load_project(db, project_id)
        if project is None:
            raise LookupError("project not found")
        rows = list(
            db.scalars(
                select(ValidationResult)
                .where(
                    ValidationResult.project_id == project_id,
                    ValidationResult.scope == SUBMISSION_SCOPE,
                )
                .order_by(ValidationResult.created_at, ValidationResult.id)
            ).all()
        )
        rows.sort(key=lambda row: int((row.details or {}).get("result_index", 0)))
        if not rows or project.checklist_id is None:
            return StoredSubmissionVerification(None, None, False)
        evaluation_date_value = rows[0].details.get("evaluation_date") if rows[0].details else None
        if not evaluation_date_value:
            return StoredSubmissionVerification(None, None, False)
        rule_results = tuple(self._row_to_rule_result(row) for row in rows)
        issues = tuple(item.issue for item in rule_results if item.issue is not None)
        result = SubmissionVerificationResult(
            project_id=project.id,
            workflow_id=project.checklist_id,
            status=OverallStatus(project.status),
            evaluation_date=date.fromisoformat(str(evaluation_date_value)),
            issues=issues,
            rule_results=rule_results,
        )
        evaluated_at = rows[0].created_at
        return StoredSubmissionVerification(result, evaluated_at, True)

    def _load_project(self, db: Session, project_id: uuid.UUID) -> Project | None:
        return db.scalar(
            select(Project)
            .options(
                selectinload(Project.checklist)
                .selectinload(Checklist.requirements)
                .selectinload(DocumentRequirement.rules)
            )
            .where(Project.id == project_id)
        )

    def _requirements(self, checklist: Checklist) -> list[RequirementSnapshot]:
        submission_types = {
            RuleType.FIELD_COMPARISON,
            RuleType.DATE_COMPARISON,
            RuleType.NUMERIC_COMPARISON,
        }
        snapshots = []
        for requirement in checklist.requirements:
            rules = []
            for row in requirement.rules:
                try:
                    rule_type = RuleType(row.rule_type)
                except ValueError as exc:
                    raise RuleConfigurationError(
                        f"Unsupported persisted rule type: {row.rule_type}"
                    ) from exc
                if rule_type in submission_types:
                    try:
                        severity = Severity(row.severity)
                    except ValueError as exc:
                        raise RuleConfigurationError(
                            f"Unsupported persisted rule severity: {row.severity}"
                        ) from exc
                    rules.append(
                        SubmissionRule(
                            id=row.id,
                            rule_type=rule_type,
                            severity=severity,
                            params=row.params or {},
                        )
                    )
            snapshots.append(
                RequirementSnapshot(
                    id=requirement.id,
                    document_type=DocumentType(requirement.document_type),
                    required=requirement.required,
                    rules=tuple(rules),
                )
            )
        return snapshots

    def _documents(self, db: Session, project_id: uuid.UUID) -> list[DocumentSnapshot]:
        rows = db.scalars(
            select(Document)
            .join(Submission)
            .options(selectinload(Document.extracted_fields))
            .where(Submission.project_id == project_id)
            .order_by(Document.created_at, Document.id)
        ).all()
        return [
            DocumentSnapshot(
                id=row.id,
                document_type=DocumentType(row.document_type),
                processing_status=ProcessingStatus(row.processing_status),
                checksum_sha256=row.checksum_sha256,
                fields={
                    item.field_name: FieldSnapshot(
                        id=item.id,
                        field_name=item.field_name,
                        normalized_value=item.normalized_value,
                        needs_review=item.needs_review,
                        evidence_available=bool(item.evidence),
                    )
                    for item in row.extracted_fields
                },
            )
            for row in rows
        ]

    def _persist(
        self,
        db: Session,
        project: Project,
        result: SubmissionVerificationResult,
        evaluated_at: datetime,
    ) -> None:
        invalidate_submission_verification(db, project.id)
        for result_index, item in enumerate(result.rule_results):
            issue = item.issue
            details = {
                "evaluation_date": result.evaluation_date.isoformat(),
                "engine_version": self.engine.version,
                "rule_id": str(item.rule_id) if item.rule_id else None,
                "document_id": str(item.document_id) if item.document_id else None,
                "document_type": item.document_type.value if item.document_type else None,
                "field_name": item.field_name,
                "related_document_id": (
                    str(item.related_document_id) if item.related_document_id else None
                ),
                "related_document_type": (
                    item.related_document_type.value if item.related_document_type else None
                ),
                "related_field_name": item.related_field_name,
                "field_id": str(issue.field_id) if issue and issue.field_id else None,
                "related_field_id": (
                    str(issue.related_field_id) if issue and issue.related_field_id else None
                ),
                "status_effect": issue.status_effect.value if issue else None,
                "result_index": result_index,
            }
            db.add(
                ValidationResult(
                    document_id=item.document_id,
                    project_id=project.id,
                    rule_type=item.rule_type.value,
                    passed=item.outcome in {RuleOutcome.PASS, RuleOutcome.NOT_APPLICABLE},
                    severity=(
                        Severity.ERROR.value
                        if issue and issue.status_effect == OverallStatus.NEEDS_CORRECTION
                        else Severity.WARNING.value
                        if issue
                        else Severity.INFO.value
                    ),
                    expected_value=None,
                    actual_value=None,
                    message=issue.message if issue else "규칙 평가가 완료되었습니다.",
                    code=(
                        issue.code
                        if issue
                        else "RULE_PASSED"
                        if item.outcome == RuleOutcome.PASS
                        else "RULE_NOT_APPLICABLE"
                    ),
                    scope=SUBMISSION_SCOPE,
                    outcome=item.outcome.value,
                    details=details,
                    created_at=evaluated_at,
                    updated_at=evaluated_at,
                )
            )
        project.status = result.status.value
        db.commit()

    def _row_to_rule_result(self, row: ValidationResult) -> RuleEvaluationResult:
        details = row.details or {}
        outcome = RuleOutcome(row.outcome or ("PASS" if row.passed else "FAIL"))
        document_id = self._uuid(details.get("document_id"))
        document_type = self._document_type(details.get("document_type"))
        related_document_id = self._uuid(details.get("related_document_id"))
        related_document_type = self._document_type(details.get("related_document_type"))
        rule_id = self._uuid(details.get("rule_id"))
        issue = None
        if outcome in {RuleOutcome.FAIL, RuleOutcome.UNRESOLVED}:
            issue = VerificationIssue(
                code=row.code,
                status_effect=OverallStatus(
                    details.get("status_effect") or OverallStatus.REVIEW_REQUIRED
                ),
                message=row.message,
                document_id=document_id,
                document_type=document_type,
                field_name=details.get("field_name"),
                related_document_id=related_document_id,
                related_document_type=related_document_type,
                related_field_name=details.get("related_field_name"),
                rule_id=rule_id,
                field_id=self._uuid(details.get("field_id")),
                related_field_id=self._uuid(details.get("related_field_id")),
            )
        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_type=RuleType(row.rule_type),
            outcome=outcome,
            issue=issue,
            document_id=document_id,
            document_type=document_type,
            field_name=details.get("field_name"),
            related_document_id=related_document_id,
            related_document_type=related_document_type,
            related_field_name=details.get("related_field_name"),
        )

    @staticmethod
    def _uuid(value: object) -> uuid.UUID | None:
        return uuid.UUID(str(value)) if value else None

    @staticmethod
    def _document_type(value: object) -> DocumentType | None:
        return DocumentType(str(value)) if value else None
