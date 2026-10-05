"""Deterministic, explainable document classifier.

Heuristic, not a calibrated probability model: `confidence_score` and `score`
reflect relative weighted keyword evidence, not measured accuracy. Weights
are hand-assigned by signal strength:

  TITLE      -- the document's own printed title (near-unambiguous)
  IDENTIFIER -- a label that is characteristic of the type but can appear
                elsewhere (e.g. a business registration number label also
                appears on an SME confirmation certificate)
  SUPPORT    -- a label commonly present on the type but not distinctive
  GENERIC    -- a bare word that alone proves very little

No LLM. See docs/domains/classification.md.
"""

import logging
import re
from dataclasses import dataclass, field

from app.core.domain import DocumentType

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


def _squash(text: str) -> str:
    """Collapse whitespace so an OCR line-wrap inside a label (e.g.
    "사업자\\n등록증") still matches -- conservative (no character-level
    fuzziness), applied identically to signal text and haystack."""
    return _WHITESPACE_RE.sub("", text)


CLASSIFIER_VERSION = "heuristic-v4-abstain"

TITLE = 5.0
IDENTIFIER = 3.0
SUPPORT = 1.0
GENERIC = 0.25

# A type is only ever predicted (rather than UNKNOWN) once its weighted score
# clears this floor AND at least one IDENTIFIER-or-stronger signal
# contributed to it (see MIN_STRONG_SIGNAL_WEIGHT below) -- SUPPORT/GENERIC
# labels alone, no matter how many, must never be enough. Evidence
# (P1.5 baseline, evaluation/reports/baseline_2026-09-09.md): with only the
# score floor, an unrelated document containing just "대학교"+"학과" (e.g. an
# enrollment certificate, not a graduation certificate) or just "회사명"
# scored above the floor and was confidently misclassified with no review
# flag in 6/85 dev samples (see AMBIGUOUS_DOCUMENT / real UNKNOWN cases in
# that report).
MIN_SCORE_FOR_CONFIDENT_TYPE = SUPPORT
MIN_STRONG_SIGNAL_WEIGHT = IDENTIFIER
# If the top two candidates' scores are within this margin, the winner is
# still returned but flagged for human review rather than asserted plainly.
AMBIGUITY_MARGIN = 1.0


@dataclass(frozen=True)
class Signal:
    text: str
    weight: float


SIGNALS: dict[DocumentType, list[Signal]] = {
    DocumentType.GRADUATION_CERTIFICATE: [
        Signal("졸업증명서", TITLE),
        # Real, official alternate title for graduate-level degree
        # conferment certificates -- confirmed by 정부24 (CappBizCD=
        # 13404000031) and two independent university registrar pages
        # (see evaluation/sources/source_registry.json src_graduation_02/
        # 03/04). Same underlying credential this document type targets.
        Signal("학위수여증명서", TITLE),
        Signal("졸업일자", IDENTIFIER),
        Signal("학위", SUPPORT),
        Signal("학과", SUPPORT),
        Signal("대학교", SUPPORT),
        Signal("대학", GENERIC),
        Signal("졸업", GENERIC),
    ],
    DocumentType.CAREER_CERTIFICATE: [
        Signal("경력증명서", TITLE),
        Signal("재직기간", IDENTIFIER),
        Signal("근무기간", IDENTIFIER),
        Signal("담당업무", SUPPORT),
        Signal("회사명", SUPPORT),
        Signal("직위", SUPPORT),
        Signal("경력", GENERIC),
        Signal("근무", GENERIC),
    ],
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: [
        Signal("사업자등록증", TITLE),
        Signal("사업자등록번호", IDENTIFIER),
        Signal("상호", SUPPORT),
        Signal("대표자", SUPPORT),
        Signal("사업장 소재지", SUPPORT),
        Signal("업태", SUPPORT),
        Signal("종목", SUPPORT),
        Signal("개업연월일", SUPPORT),
    ],
    DocumentType.SME_CONFIRMATION_CERTIFICATE: [
        Signal("중소기업확인서", TITLE),
        Signal("유효기간", IDENTIFIER),
        Signal("중소기업", SUPPORT),
        Signal("기업명", SUPPORT),
        Signal("사업자등록번호", SUPPORT),
        Signal("확인서", GENERIC),
    ],
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: [
        Signal("국세납세증명서", TITLE),
        Signal("납세증명서", TITLE),
        Signal("납세자명", IDENTIFIER),
        Signal("유효기한", SUPPORT),
        Signal("사업자등록번호", SUPPORT),
    ],
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: [
        Signal("4대사회보험료완납증명서", TITLE),
        Signal("사회보험료완납증명서", TITLE),
        # 고용·산재보험료 완납증명원 is the 근로복지공단 title form (원, not 서);
        # its title is printed on its own line, apart from the 보험료 words.
        Signal("완납증명원", TITLE),
        Signal("고용보험료", SUPPORT),
        Signal("산재보험료", SUPPORT),
        Signal("사업장명", IDENTIFIER),
        Signal("사업자등록번호", SUPPORT),
        Signal("유효기한", SUPPORT),
    ],
    DocumentType.ENROLLMENT_CERTIFICATE: [
        Signal("재학증명서", TITLE),
        Signal("재학여부", IDENTIFIER),
        Signal("학번", SUPPORT),
        Signal("학과", SUPPORT),
        Signal("대학교", SUPPORT),
    ],
    DocumentType.TRANSCRIPT: [
        Signal("성적증명서", TITLE),
        Signal("평점평균", IDENTIFIER),
        Signal("총평점", IDENTIFIER),
        Signal("학번", SUPPORT),
        Signal("GPA", SUPPORT),
    ],
}

# Real Korean administrative documents this system does not model, each
# named here because its own title is a superstring or close variant of a
# TITLE-weight signal above and so could otherwise win that type's score by
# plain substring containment (audit F-003: 지방세납세증명서 contains
# "납세증명서", the national-tax TITLE signal, and classified as
# NATIONAL_TAX_PAYMENT_CERTIFICATE at confidence 0.9 with no review flag).
# DECISION_2 (UNDECIDED -> default applied): checked before scoring: any
# match aborts classification to UNKNOWN with needs_review=True
# unconditionally, regardless of what else matches. No new DocumentType is
# added for these -- the system correctly has no opinion about them.
UNSUPPORTED_LOOK_ALIKE_TITLES: tuple[str, ...] = (
    "지방세납세증명서",  # looks like 국세 납세증명서 (NATIONAL_TAX_PAYMENT_CERTIFICATE)
    "휴학증명서",  # looks like 재학증명서 (ENROLLMENT_CERTIFICATE)
    "졸업예정증명서",  # looks like 졸업증명서 (GRADUATION_CERTIFICATE)
)


@dataclass
class ClassificationAlternative:
    document_type: DocumentType
    score: float


@dataclass
class ClassificationResult:
    predicted_type: DocumentType
    confidence_score: float
    score: float
    evidence: list[str]
    needs_review: bool
    classifier_version: str = CLASSIFIER_VERSION
    alternatives: list[ClassificationAlternative] = field(default_factory=list)


def _unknown(
    scores: dict[DocumentType, float], evidence: dict[DocumentType, list[str]]
) -> ClassificationResult:
    alternatives = _alternatives(scores)
    return ClassificationResult(
        predicted_type=DocumentType.UNKNOWN,
        confidence_score=0.0,
        score=0.0,
        evidence=[],
        needs_review=True,
        alternatives=alternatives,
    )


def _alternatives(scores: dict[DocumentType, float]) -> list[ClassificationAlternative]:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [ClassificationAlternative(doc_type, s) for doc_type, s in ranked if s > 0]


class DocumentClassifier:
    def classify(self, text: str, filename: str = "") -> ClassificationResult:
        """Classify from document content only.

        ``filename`` is accepted for call-site compatibility but is
        deliberately *not* part of the haystack. A filename is metadata the
        uploader controls, so feeding it to the classifier lets a document
        be classified by what it is called rather than what it contains, and
        it silently inflates benchmark accuracy for any sample whose
        directory encodes its document type. It is recorded in the log for
        diagnostics instead.
        """
        if filename:
            logger.info(
                "classification_filename_ignored",
                extra={"filename_length": len(filename)},
            )
        haystack = _squash(text)
        if any(marker in haystack for marker in UNSUPPORTED_LOOK_ALIKE_TITLES):
            return _unknown({}, {})
        scores: dict[DocumentType, float] = {}
        evidence: dict[DocumentType, list[str]] = {}
        has_strong_signal: dict[DocumentType, bool] = {}
        for doc_type, signals in SIGNALS.items():
            hits = [signal for signal in signals if _squash(signal.text) in haystack]
            scores[doc_type] = sum(signal.weight for signal in hits)
            evidence[doc_type] = [signal.text for signal in hits]
            has_strong_signal[doc_type] = any(
                signal.weight >= MIN_STRONG_SIGNAL_WEIGHT for signal in hits
            )

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        winner_type, winner_score = ranked[0]
        runner_score = ranked[1][1] if len(ranked) > 1 else 0.0

        if winner_score < MIN_SCORE_FOR_CONFIDENT_TYPE or not has_strong_signal[winner_type]:
            return _unknown(scores, evidence)

        denom = winner_score + runner_score
        confidence = min(winner_score / denom, 0.99) if denom > 0 else 0.0
        ambiguous = runner_score > 0 and (winner_score - runner_score) <= AMBIGUITY_MARGIN
        if ambiguous:
            return _unknown(scores, evidence)

        return ClassificationResult(
            predicted_type=winner_type,
            confidence_score=confidence,
            score=winner_score,
            evidence=evidence[winner_type],
            needs_review=ambiguous,
            alternatives=_alternatives(scores),
        )
