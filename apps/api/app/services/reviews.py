from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.domain import (
    REVIEWABLE_FIELDS,
    DocumentType,
    ProcessingStatus,
    RuleType,
)
from app.document_intelligence.evidence_sufficiency import (
    EVIDENCE_POLICY_VERSION,
    EffectiveValueSource,
    EvidenceAssessment,
    EvidenceAssessmentReason,
    EvidenceAssessmentState,
    EvidenceSufficiencyPolicy,
    FieldReviewDecision,
)
from app.document_intelligence.normalization.field_normalizer import (
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_text_field,
)
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    ExtractedField,
    FieldReview,
    Project,
    Submission,
)
from app.services.consistency import lock_project
from app.services.requirements import required_fields


class ReviewValidationError(ValueError):
    pass


class StaleReviewError(ReviewValidationError):
    pass


def _evidence_fingerprint(evidence: list[dict[str, Any]] | None) -> str | None:
    if not evidence:
        return None
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EffectiveFieldValue:
    normalized_value: str | None
    source: EffectiveValueSource
    assessment: EvidenceAssessment
    review: FieldReview | None


@dataclass(frozen=True)
class ReviewTarget:
    project: Project
    document: Document
    field_name: str
    field: ExtractedField | None


def invalidate_document_reviews(db: Session, document_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    db.execute(
        update(FieldReview)
        .where(FieldReview.document_id == document_id, FieldReview.is_current.is_(True))
        .values(is_current=False, stale_at=now, updated_at=now)
    )


class EffectiveFieldResolver:
    def __init__(self, policy: EvidenceSufficiencyPolicy | None = None) -> None:
        self.policy = policy or EvidenceSufficiencyPolicy()

    def resolve(
        self,
        field: ExtractedField | None,
        review: FieldReview | None,
        processing_version: int,
    ) -> EffectiveFieldValue:
        machine = self.policy.assess(
            normalized_value=field.normalized_value if field else None,
            needs_review=field.needs_review if field else True,
            evidence=field.evidence if field else None,
            field_confidence=field.confidence if field else None,
            extraction_method=field.extraction_method if field else None,
        )
        current = (
            review
            if review is not None
            and review.is_current
            and review.stale_at is None
            and review.processing_version == processing_version
            else None
        )
        if current is None:
            return EffectiveFieldValue(
                field.normalized_value
                if field and machine.state == EvidenceAssessmentState.SUFFICIENT
                else None,
                EffectiveValueSource.MACHINE
                if field and machine.state == EvidenceAssessmentState.SUFFICIENT
                else EffectiveValueSource.UNAVAILABLE,
                machine,
                None,
            )
        decision = FieldReviewDecision(current.decision)
        if decision == FieldReviewDecision.CONFIRMED:
            assessment = EvidenceAssessment(EvidenceAssessmentState.SUFFICIENT, (), None)
            return EffectiveFieldValue(
                current.original_normalized_value,
                EffectiveValueSource.HUMAN_CONFIRMED,
                assessment,
                current,
            )
        if decision == FieldReviewDecision.CORRECTED:
            assessment = EvidenceAssessment(EvidenceAssessmentState.SUFFICIENT, (), None)
            return EffectiveFieldValue(
                current.reviewed_normalized_value,
                EffectiveValueSource.HUMAN_CORRECTED,
                assessment,
                current,
            )
        assessment = EvidenceAssessment(
            EvidenceAssessmentState.UNAVAILABLE,
            (
                EvidenceAssessmentReason.HUMAN_REJECTED
                if decision == FieldReviewDecision.REJECTED
                else EvidenceAssessmentReason.HUMAN_CANNOT_DETERMINE,
            ),
            None,
        )
        return EffectiveFieldValue(None, EffectiveValueSource.UNAVAILABLE, assessment, current)


class FieldReviewService:
    def __init__(self) -> None:
        self.resolver = EffectiveFieldResolver()

    def target(
        self, db: Session, project_id: uuid.UUID, document_id: uuid.UUID, field_name: str
    ) -> ReviewTarget | None:
        lock_project(db, project_id)
        document = db.scalar(
            select(Document)
            .join(Submission)
            .options(selectinload(Document.extracted_fields))
            .where(Document.id == document_id, Submission.project_id == project_id)
            .execution_options(populate_existing=True)
        )
        if document is None:
            return None
        if ProcessingStatus(document.processing_status) != ProcessingStatus.COMPLETED:
            raise StaleReviewError("Document processing is not completed; reload current evidence")
        try:
            document_type = DocumentType(document.document_type)
        except ValueError:
            return None
        if field_name not in REVIEWABLE_FIELDS[document_type]:
            raise ReviewValidationError("Unknown canonical field for document type")
        project = db.get(Project, project_id)
        if project is None:
            return None
        field = next(
            (item for item in document.extracted_fields if item.field_name == field_name), None
        )
        return ReviewTarget(project, document, field_name, field)

    def current(self, db: Session, document_id: uuid.UUID, field_name: str) -> FieldReview | None:
        return db.scalar(
            select(FieldReview).where(
                FieldReview.document_id == document_id,
                FieldReview.field_name == field_name,
                FieldReview.is_current.is_(True),
            )
        )

    def submit(
        self,
        db: Session,
        target: ReviewTarget,
        *,
        decision: FieldReviewDecision,
        corrected_value: str | None,
        reviewer_label: str | None,
        note: str | None,
        expected_processing_version: int,
    ) -> FieldReview:
        # Re-read under the same project transaction lock even for service callers
        # that constructed their target before another processing attempt.
        fresh = self.target(db, target.project.id, target.document.id, target.field_name)
        if fresh is None:
            raise StaleReviewError("Review target no longer exists")
        target = fresh
        if target.document.processing_version != expected_processing_version:
            raise StaleReviewError("Processing version changed; reload current evidence")
        field = target.field
        if decision == FieldReviewDecision.CONFIRMED:
            if corrected_value is not None:
                raise ReviewValidationError("CONFIRMED does not accept a corrected value")
            if field is None or field.normalized_value is None:
                raise ReviewValidationError("A missing machine value cannot be confirmed")
            reviewed_normalized = None
        elif decision == FieldReviewDecision.CORRECTED:
            if corrected_value is None or not corrected_value.strip():
                raise ReviewValidationError("CORRECTED requires a corrected value")
            reviewed_normalized = self._normalize(target.field_name, corrected_value)
            if reviewed_normalized is None:
                raise ReviewValidationError("Corrected value is invalid for this field")
        else:
            if corrected_value is not None:
                raise ReviewValidationError(f"{decision.value} does not accept a corrected value")
            reviewed_normalized = None

        current = self.current(db, target.document.id, target.field_name)
        field_name = target.field_name
        logical = (
            current is not None
            and current.processing_version == target.document.processing_version
            and current.decision == decision.value
            and current.reviewed_raw_value == corrected_value
            and current.reviewed_normalized_value == reviewed_normalized
            and current.reviewer_label == reviewer_label
            and current.note == note
        )
        if logical:
            assert current is not None
            return current
        now = datetime.now(UTC)
        if current is not None:
            current.is_current = False
            current.superseded_at = now
            db.flush()
        review = FieldReview(
            project_id=target.project.id,
            document_id=target.document.id,
            extracted_field_id=field.id if field else None,
            field_name=field_name,
            decision=decision.value,
            original_raw_value=field.raw_value if field else None,
            original_normalized_value=field.normalized_value if field else None,
            original_evidence_fingerprint=_evidence_fingerprint(field.evidence if field else None),
            reviewed_raw_value=corrected_value,
            reviewed_normalized_value=reviewed_normalized,
            reviewer_label=reviewer_label,
            note=note,
            processing_version=target.document.processing_version,
            policy_version=EVIDENCE_POLICY_VERSION,
            is_current=True,
            reviewed_at=now,
        )
        db.add(review)
        from app.services.verification import invalidate_submission_verification

        invalidate_submission_verification(db, target.project.id)
        db.commit()
        db.refresh(review)
        return review

    def _normalize(self, field_name: str, raw_value: str) -> str | None:
        if field_name == "business_registration_number":
            return normalize_business_number(raw_value)
        if field_name.endswith("_date") or field_name in {"valid_from", "valid_until"}:
            return normalize_date(raw_value)
        if field_name == "gpa":
            return normalize_gpa(raw_value)
        if field_name == "gpa_scale":
            return normalize_gpa_scale(raw_value)
        return normalize_text_field(raw_value)

    def review_dependencies(self, project: Project) -> set[tuple[DocumentType, str]]:
        dependencies: set[tuple[DocumentType, str]] = set()
        checklist = project.checklist
        if checklist is None:
            return dependencies
        for requirement in checklist.requirements:
            dependencies.update(
                (DocumentType(requirement.document_type), name)
                for name in required_fields(requirement)
            )
            for rule in requirement.rules:
                params: dict[str, Any] = rule.params or {}
                rule_type = RuleType(rule.rule_type)
                if rule_type == RuleType.FIELD_COMPARISON:
                    dependencies.add(
                        (DocumentType(params["source_document_type"]), str(params["source_field"]))
                    )
                    dependencies.add(
                        (DocumentType(params["target_document_type"]), str(params["target_field"]))
                    )
                elif rule_type in {RuleType.DATE_COMPARISON, RuleType.NUMERIC_COMPARISON}:
                    dependencies.add((DocumentType(params["document_type"]), str(params["field"])))
                elif rule_type in {RuleType.DATE_NOT_EXPIRED, RuleType.ISSUE_DATE_MAX_AGE}:
                    dependencies.add(
                        (
                            DocumentType(requirement.document_type),
                            str(
                                params.get(
                                    "field",
                                    "valid_until"
                                    if rule_type == RuleType.DATE_NOT_EXPIRED
                                    else "issue_date",
                                )
                            ),
                        )
                    )
        return dependencies

    def project_with_rules(self, db: Session, project_id: uuid.UUID) -> Project | None:
        return db.scalar(
            select(Project)
            .options(
                selectinload(Project.checklist)
                .selectinload(Checklist.requirements)
                .selectinload(DocumentRequirement.rules)
            )
            .where(Project.id == project_id)
        )

    def list_reviews(
        self, db: Session, project_id: uuid.UUID, *, include_history: bool
    ) -> list[FieldReview]:
        statement = select(FieldReview).where(FieldReview.project_id == project_id)
        if not include_history:
            statement = statement.where(FieldReview.is_current.is_(True))
        return list(
            db.scalars(statement.order_by(FieldReview.reviewed_at.desc(), FieldReview.id)).all()
        )

    def review_items(self, db: Session, project_id: uuid.UUID) -> list[dict[str, Any]] | None:
        project = self.project_with_rules(db, project_id)
        if project is None:
            return None
        dependencies = self.review_dependencies(project)
        documents = db.scalars(
            select(Document)
            .join(Submission)
            .options(selectinload(Document.extracted_fields))
            .where(
                Submission.project_id == project_id,
                Document.processing_status == ProcessingStatus.COMPLETED.value,
            )
            .order_by(Document.created_at, Document.id)
        ).all()
        reviews = self.list_reviews(db, project_id, include_history=True)
        current = {(item.document_id, item.field_name): item for item in reviews if item.is_current}
        stale_targets = {
            (item.document_id, item.field_name) for item in reviews if item.stale_at is not None
        }
        items: list[dict[str, Any]] = []
        for document in documents:
            document_type = DocumentType(document.document_type)
            fields = {item.field_name: item for item in document.extracted_fields}
            for dependency_type, field_name in sorted(
                dependencies, key=lambda item: (item[0].value, item[1])
            ):
                if dependency_type != document_type:
                    continue
                field = fields.get(field_name)
                review = current.get((document.id, field_name))
                effective = self.resolver.resolve(field, review, document.processing_version)
                if effective.assessment.state == EvidenceAssessmentState.SUFFICIENT:
                    continue
                queue_status = (
                    (
                        "REJECTED"
                        if effective.review.decision == FieldReviewDecision.REJECTED
                        else "CANNOT_DETERMINE"
                    )
                    if effective.review is not None
                    else "STALE"
                    if (document.id, field_name) in stale_targets
                    else "PENDING"
                )
                items.append(
                    {
                        "document_id": document.id,
                        "processing_version": document.processing_version,
                        "document_type": document_type,
                        "field_id": field.id if field else None,
                        "field_name": field_name,
                        "machine_raw_value": field.raw_value if field else None,
                        "machine_normalized_value": field.normalized_value if field else None,
                        "confidence": field.confidence if field else None,
                        "evidence": field.evidence if field else None,
                        "assessment_state": effective.assessment.state,
                        "assessment_reasons": list(effective.assessment.reasons),
                        "policy_version": effective.assessment.policy_version,
                        "issue_code": (
                            "OCR_UNCERTAIN"
                            if effective.assessment.state == EvidenceAssessmentState.REVIEW_REQUIRED
                            else "REQUIRED_FIELD_UNRESOLVED"
                        ),
                        "affects_verification": True,
                        "queue_status": queue_status,
                        "current_review_id": effective.review.id if effective.review else None,
                        "current_review_decision": (
                            effective.review.decision if effective.review else None
                        ),
                        "effective_value": effective.normalized_value,
                        "effective_source": effective.source,
                    }
                )
        return items
