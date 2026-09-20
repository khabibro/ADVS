import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.domain import DocumentType
from app.document_intelligence.normalization.field_normalizer import (
    BUSINESS_NUMBER_RE,
    DATE_RE,
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_text_field,
)

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
    "대학명",
    "학교명",
    "학과",
    "전공",
    "학위",
    "졸업일자",
    "졸업 연월일",
    "발급일자",
    "발행일자",
    "회사명",
    "상호",
    "상호명",
    "기업명",
    "법인명",
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


def after_label(text: str, labels: list[str]) -> str | None:
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
    normalized_text = _normalize_extraction_text(text)
    lines = [line for line in normalized_text.splitlines() if line.strip()]
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
                return value.strip()
            if not value and idx + 1 < len(lines) and _next_line_value_allowed(lines[idx + 1]):
                return _strip_trailing_labels(lines[idx + 1], labels)
    return None


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
    def extract(self, text: str) -> list[ExtractedValue]:
        raise NotImplementedError

    def missing(self, field_name: str) -> ExtractedValue:
        return ExtractedValue(field_name, None, None, None, True)

    def text_field(self, text: str, field_name: str, labels: list[str]) -> ExtractedValue:
        raw = after_label(text, labels)
        normalized = normalize_text_field(raw)
        if normalized is None or self._reject_text_candidate(field_name, normalized):
            return self.missing(field_name)
        return ExtractedValue(field_name, raw, normalized, 0.7, False, "label_match", raw)

    def date_field(self, text: str, field_name: str, labels: list[str]) -> ExtractedValue:
        raw = after_label(text, labels)
        normalized = normalize_date(raw)
        if normalized is None:
            return self.missing(field_name)
        return ExtractedValue(field_name, raw, normalized, 0.55, False, "regex_date", raw)

    def business_number_field(
        self, text: str, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        raw_context = after_label(text, labels)
        match = BUSINESS_NUMBER_RE.search(raw_context) if raw_context else None
        raw_value = match.group(0) if match else None
        normalized = normalize_business_number(raw_value)
        if normalized is None:
            return self.missing(field_name)
        return ExtractedValue(
            field_name, raw_value, normalized, 0.9, False, "regex_business_number", raw_value
        )

    def valid_until_field(self, text: str, labels: list[str]) -> ExtractedValue:
        raw = after_label(text, labels)
        _, end_raw = split_range(raw)
        candidate = end_raw or raw
        normalized = normalize_date(candidate)
        if normalized is None:
            return self.missing("valid_until")
        return ExtractedValue(
            "valid_until", candidate, normalized, 0.55, False, "regex_date", candidate
        )

    def gpa_field(self, text: str, field_name: str, labels: list[str]) -> ExtractedValue:
        raw = after_label(text, labels)
        normalized = normalize_gpa(raw)
        if normalized is None:
            return self.missing(field_name)
        return ExtractedValue(field_name, raw, normalized, 0.7, False, "regex_gpa", raw)

    def gpa_scale_field(self, text: str, field_name: str, labels: list[str]) -> ExtractedValue:
        raw = after_label(text, labels)
        normalized = normalize_gpa_scale(raw)
        if normalized is None:
            return self.missing(field_name)
        return ExtractedValue(field_name, raw, normalized, 0.7, False, "regex_gpa", raw)

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
