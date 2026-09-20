import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.domain import DocumentType
from app.document_intelligence.evidence import CoordinateSpace, EvidenceRef, EvidenceSourceKind
from app.document_intelligence.normalization.field_normalizer import (
    BUSINESS_NUMBER_RE,
    DATE_RE,
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_text_field,
)
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRLine
from app.document_intelligence.ocr.text_assembly import order_lines

EXTRACTOR_VERSION = "heuristic-v2"

_COLON_RE = re.compile(r"[：﹕꞉︓]")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_KNOWN_LABELS = [
    "졸업증명서",
    "경력증명서",
    "사업자등록증",
    "중소기업확인서",
    "국세 납세증명서",
    "납세증명서",
    "4대 사회보험료 완납증명서",
    "재학증명서",
    "성적증명서",
    "성명",
    "이름",
    "신청인",
    "대학교",
    "대학",
    "대학명",
    "학교명",
    "학과",
    "전공",
    "학위",
    "졸업일자",
    "졸업 연월일",
    "발급일자",
    "발급일",
    "발행일자",
    "회사명",
    "상호",
    "상호명",
    "기업명",
    "법인명",
    "법인명(단체명)",
    "업체명",
    "납세자명",
    "직위",
    "직급",
    "담당업무",
    "입사일",
    "퇴사일",
    "근무 시작일",
    "근무 종료일",
    "재직기간",
    "근무기간",
    "법인명칭",
    "대표자 성명",
    "대표자",
    "대표자명",
    "사업자등록번호",
    "등록번호",
    "사업장 소재지",
    "소재지",
    "업태",
    "종목",
    "개업연월일",
    "확인번호",
    "발급번호",
    "증명서번호",
    "일련번호",
    "유효기간",
    "유효기한",
    "사업장명",
    "사업장 명칭",
    "학생명",
    "학번",
    "평점",
    "총평점",
    "평점평균",
    "GPA",
]
_DOCUMENT_TITLE_RE = re.compile(r"(증명서|확인서|등록증)$")
_DEGREE_RE = re.compile(r"^(전문학사|학사|석사|박사)$")


@dataclass
class ExtractedValue:
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float | None = None
    needs_review: bool = False
    extraction_method: str | None = None
    source_text: str | None = None
    evidence: list[EvidenceRef] | None = None


type ExtractionInput = str | OCRDocumentResult


@dataclass(frozen=True)
class ExtractionCandidate:
    value: str
    evidence: list[EvidenceRef]


def _source_lines(source: ExtractionInput) -> list[tuple[str, EvidenceRef | None]]:
    if isinstance(source, str):
        return [(line, None) for line in source.splitlines() if line.strip()]
    source_kind: EvidenceSourceKind = (
        "embedded_pdf_text" if source.provider == "direct_pdf_text" else "ocr"
    )
    coordinate_space: CoordinateSpace = (
        "pdf_point" if source_kind == "embedded_pdf_text" else "pixel"
    )
    observations: list[tuple[str, EvidenceRef | None]] = []
    for page in source.pages:
        lines = order_lines(page.lines) or [OCRLine(text=line) for line in page.text.splitlines()]
        for line in lines:
            if not line.text.strip():
                continue
            observations.append(
                (
                    line.text,
                    EvidenceRef(
                        page_number=page.page_number,
                        source_text=line.text,
                        bounding_box=line.bounding_box,
                        confidence=line.confidence,
                        source_kind=source_kind,
                        coordinate_space=coordinate_space,
                    ),
                )
            )
    return observations


def source_text(source: ExtractionInput) -> str:
    return source if isinstance(source, str) else source.assembled_text


def _label_pattern(label: str) -> str:
    """Builds a regex matching `label` tolerant of incidental spaces/tabs
    *within* it (e.g. OCR rendering "사업자등록번호" as "사업자 등록번호"),
    mirroring the whitespace tolerance the classifier already applies.
    Deliberately restricted to space/tab, not newline, so this does not
    also match a label split across two lines -- that is a separate,
    documented layout limitation (see docs/domains/extraction.md), not a
    whitespace-variant OCR artifact."""
    return r"[ \t]*".join(re.escape(ch) for ch in label)


def _normalize_extraction_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _COLON_RE.sub(":", normalized)
    return "\n".join(_WHITESPACE_RE.sub(" ", line).strip() for line in normalized.splitlines())


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _looks_like_label_or_title(value: str) -> bool:
    compact = _compact(value)
    if not compact:
        return True
    if _DOCUMENT_TITLE_RE.search(compact):
        return True
    return any(compact == _compact(label) for label in _KNOWN_LABELS)


def _strip_trailing_labels(value: str, active_labels: list[str]) -> str:
    earliest: int | None = None
    labels = sorted(
        {label for label in _KNOWN_LABELS if label not in active_labels},
        key=len,
        reverse=True,
    )
    for label in labels:
        pattern = rf"(?:^|[ \t]){_label_pattern(label)}(?:[ \t]*[:：]|[ \t]+|(?=\d|[A-Za-z가-힣]))"
        match = re.search(pattern, value)
        if match and match.start() > 0:
            earliest = match.start() if earliest is None else min(earliest, match.start())
    return value[:earliest].strip() if earliest is not None else value.strip()


def _adjacent_value_allowed(label: str, value: str) -> bool:
    compact = _compact(value)
    if not compact:
        return False
    if normalize_date(compact):
        return True
    if normalize_business_number(compact):
        return True
    if label in {"학위"} and _DEGREE_RE.match(compact):
        return True
    return len(label) >= 3 and not _looks_like_label_or_title(compact)


def _next_line_value_allowed(value: str) -> bool:
    normalized = normalize_text_field(value)
    if normalized is None:
        return False
    if _looks_like_label_or_title(normalized):
        return False
    return len(normalized) <= 80


def candidate_after_label(source: ExtractionInput, labels: list[str]) -> ExtractionCandidate | None:
    """Returns the text following the first matching label on the same
    line. Tolerant of a colon separator, surrounding whitespace, and an
    internal whitespace variant within the label itself; does not
    fuzzy-match across unrelated labels.

    Requires an actual separator (whitespace or a colon) between the label
    and the captured value -- a label with *no* separator at all is not
    accepted as a match. Without this, a short label that happens to be a
    literal prefix of a longer, unrelated word (e.g. "학위" is a prefix of
    the real document title "학위수여증명서") would match with zero
    separator and hallucinate the rest of that word as the field's value
    (evaluation/reports/baseline_2026-09-09b.md: 'degree' field on a
    recreated 학위수여증명서 sample was extracted as "수여증명서")."""
    observations = _source_lines(source)
    lines = [_normalize_extraction_text(line) for line, _ in observations]
    for idx, line in enumerate(lines):
        for label in labels:
            label_re = _label_pattern(label)
            match = re.search(
                rf"(?:^|[ \t]){label_re}(?P<sep>[ \t]*:[ \t]*|[ \t]+)?(?P<value>.*)$", line
            )
            if not match:
                continue
            sep = match.group("sep")
            value = _strip_trailing_labels(match.group("value"), labels)
            if value and (sep or _adjacent_value_allowed(label, value)):
                evidence: list[EvidenceRef] = []
                observation = observations[idx][1]
                if observation is not None:
                    evidence.append(observation)
                return ExtractionCandidate(value.strip(), evidence)
            if not value and idx + 1 < len(lines) and _next_line_value_allowed(lines[idx + 1]):
                evidence = []
                for item in (observations[idx][1], observations[idx + 1][1]):
                    if item is not None:
                        evidence.append(item)
                return ExtractionCandidate(_strip_trailing_labels(lines[idx + 1], labels), evidence)
    return None


def after_label(source: ExtractionInput, labels: list[str]) -> str | None:
    candidate = candidate_after_label(source, labels)
    return candidate.value if candidate else None


def split_range(raw: str | None) -> tuple[str | None, str | None]:
    """Splits a 'start ~ end' style range. Returns (None, None) when no
    range separator is present -- callers decide whether to treat the whole
    string as a single value instead."""
    if not raw:
        return None, None
    normalized = _normalize_extraction_text(raw)
    if not re.search(r"~|–|—|부터|에서", normalized):
        return None, None
    matches = list(DATE_RE.finditer(normalized))
    if len(matches) >= 2:
        return matches[0].group(0).strip(), matches[1].group(0).strip()
    return None, None


class BaseDocumentExtractor(ABC):
    document_type: DocumentType
    extractor_version: str = EXTRACTOR_VERSION

    @abstractmethod
    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        raise NotImplementedError

    def missing(self, field_name: str) -> ExtractedValue:
        return ExtractedValue(field_name, None, None, None, True)

    def _value(
        self,
        field_name: str,
        raw: str,
        normalized: str,
        method: str,
        candidate: ExtractionCandidate,
    ) -> ExtractedValue:
        confidences = [
            item.confidence for item in candidate.evidence if item.confidence is not None
        ]
        confidence = min(confidences) if confidences else None
        supporting_text = "\n".join(item.source_text for item in candidate.evidence) or raw
        return ExtractedValue(
            field_name,
            raw,
            normalized,
            confidence,
            False,
            method,
            supporting_text,
            candidate.evidence or None,
        )

    def text_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw = candidate.value if candidate else None
        normalized = normalize_text_field(raw)
        if (
            candidate is None
            or normalized is None
            or self._reject_text_candidate(field_name, normalized)
        ):
            return self.missing(field_name)
        assert raw is not None
        return self._value(field_name, raw, normalized, "label_match", candidate)

    def date_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw = candidate.value if candidate else None
        normalized = normalize_date(raw)
        if candidate is None or normalized is None:
            return self.missing(field_name)
        assert raw is not None
        return self._value(field_name, raw, normalized, "regex_date", candidate)

    def business_number_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw_context = candidate.value if candidate else None
        match = BUSINESS_NUMBER_RE.search(raw_context) if raw_context else None
        raw_value = match.group(0) if match else None
        normalized = normalize_business_number(raw_value)
        if candidate is None or normalized is None:
            return self.missing(field_name)
        assert raw_value is not None
        return self._value(field_name, raw_value, normalized, "regex_business_number", candidate)

    def valid_until_field(self, text: ExtractionInput, labels: list[str]) -> ExtractedValue:
        candidate_match = candidate_after_label(text, labels)
        raw = candidate_match.value if candidate_match else None
        _, end_raw = split_range(raw)
        candidate = end_raw or raw
        normalized = normalize_date(candidate)
        if candidate_match is None or normalized is None:
            return self.missing("valid_until")
        assert candidate is not None
        return self._value("valid_until", candidate, normalized, "regex_date", candidate_match)

    def gpa_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw = candidate.value if candidate else None
        normalized = normalize_gpa(raw)
        if candidate is None or normalized is None:
            return self.missing(field_name)
        assert raw is not None
        return self._value(field_name, raw, normalized, "regex_gpa", candidate)

    def gpa_scale_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw = candidate.value if candidate else None
        normalized = normalize_gpa_scale(raw)
        if candidate is None or normalized is None:
            return self.missing(field_name)
        assert raw is not None
        return self._value(field_name, raw, normalized, "regex_gpa", candidate)

    def _reject_text_candidate(self, field_name: str, value: str) -> bool:
        if _looks_like_label_or_title(value):
            return True
        if field_name in {"applicant_name", "representative_name", "student_name"}:
            return bool(
                normalize_date(value) or normalize_business_number(value) or len(value) > 20
            )
        if field_name == "degree":
            return _DEGREE_RE.match(_compact(value)) is None
        return False
