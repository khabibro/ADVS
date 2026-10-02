from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

EVIDENCE_POLICY_VERSION = "evidence-policy-v2"


class EvidenceAssessmentState(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceAssessmentReason(StrEnum):
    FIELD_MISSING = "FIELD_MISSING"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    OCR_CONFIDENCE_UNAVAILABLE = "OCR_CONFIDENCE_UNAVAILABLE"
    OCR_CONFIDENCE_BELOW_POLICY = "OCR_CONFIDENCE_BELOW_POLICY"
    EXTRACTION_MARKED_FOR_REVIEW = "EXTRACTION_MARKED_FOR_REVIEW"
    OCR_REQUIRES_CONFIRMATION = "OCR_REQUIRES_CONFIRMATION"
    SEMANTIC_INFERENCE = "SEMANTIC_INFERENCE"
    SOURCE_PROVENANCE_INCOMPLETE = "SOURCE_PROVENANCE_INCOMPLETE"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    HUMAN_CANNOT_DETERMINE = "HUMAN_CANNOT_DETERMINE"


class EffectiveValueSource(StrEnum):
    MACHINE = "MACHINE"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    UNAVAILABLE = "UNAVAILABLE"


class FieldReviewDecision(StrEnum):
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    CANNOT_DETERMINE = "CANNOT_DETERMINE"


@dataclass(frozen=True)
class EvidenceAssessment:
    state: EvidenceAssessmentState
    reasons: tuple[EvidenceAssessmentReason, ...]
    confidence: float | None
    policy_version: str = EVIDENCE_POLICY_VERSION


class EvidenceSufficiencyPolicy:
    """Operational trust policy; OCR confidence is not correctness probability."""

    version = EVIDENCE_POLICY_VERSION
    minimum_ocr_field_confidence = 0.90

    def assess(
        self,
        *,
        normalized_value: str | None,
        needs_review: bool,
        evidence: list[dict[str, Any]] | None,
        field_confidence: float | None,
        extraction_method: str | None = None,
    ) -> EvidenceAssessment:
        if normalized_value is None:
            return EvidenceAssessment(
                EvidenceAssessmentState.UNAVAILABLE,
                (EvidenceAssessmentReason.FIELD_MISSING,),
                field_confidence,
            )
        if not evidence:
            return EvidenceAssessment(
                EvidenceAssessmentState.REVIEW_REQUIRED,
                (EvidenceAssessmentReason.EVIDENCE_MISSING,),
                field_confidence,
            )

        reasons: list[EvidenceAssessmentReason] = []
        if needs_review:
            reasons.append(EvidenceAssessmentReason.EXTRACTION_MARKED_FOR_REVIEW)
        if extraction_method and "semantic" in extraction_method:
            reasons.append(EvidenceAssessmentReason.SEMANTIC_INFERENCE)
        if any(item.get("source_kind") not in {"ocr", "embedded_pdf_text"} for item in evidence):
            reasons.append(EvidenceAssessmentReason.SOURCE_PROVENANCE_INCOMPLETE)
        ocr_evidence = [item for item in evidence if item.get("source_kind", "ocr") == "ocr"]
        if ocr_evidence:
            # Recognition confidence is only a diagnostic. No calibrated field
            # correctness estimator exists; OCR-only values need independent human
            # confirmation before deterministic rules consume them.
            reasons.append(EvidenceAssessmentReason.OCR_REQUIRES_CONFIRMATION)
            confidences = [
                float(item["confidence"])
                for item in ocr_evidence
                if item.get("confidence") is not None
            ]
            effective_confidence = min(confidences) if confidences else field_confidence
            if effective_confidence is None:
                reasons.append(EvidenceAssessmentReason.OCR_CONFIDENCE_UNAVAILABLE)
            elif effective_confidence < self.minimum_ocr_field_confidence:
                reasons.append(EvidenceAssessmentReason.OCR_CONFIDENCE_BELOW_POLICY)
        if reasons:
            return EvidenceAssessment(
                EvidenceAssessmentState.REVIEW_REQUIRED,
                tuple(dict.fromkeys(reasons)),
                field_confidence,
            )
        return EvidenceAssessment(
            EvidenceAssessmentState.SUFFICIENT,
            (),
            field_confidence,
        )
