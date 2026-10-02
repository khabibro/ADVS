import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from app.core.domain import DocumentType
from app.document_intelligence.evidence import CoordinateSpace, EvidenceRef, EvidenceSourceKind
from app.document_intelligence.extraction.fields import (
    is_valid_value,
    looks_like_boilerplate,
    score_candidate,
)
from app.document_intelligence.normalization.field_normalizer import (
    BUSINESS_NUMBER_RE,
    canonicalize_numeric_text,
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_lexical_text,
    normalize_text_field,
    split_date_range,
)
from app.document_intelligence.ocr.layout import TextRow, build_rows
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.ocr.text_assembly import order_lines

EXTRACTOR_VERSION = "evidence-v5"

_COLON_RE = re.compile(r"[：﹕꞉︓]")
_WHITESPACE_RE = re.compile(r"[ \t]+")
# A row whose entire content is one date and nothing else. Korean official
# certificates print the issue date as a bare line inside the issuance block
# (above the signing officer's name and stamp) far more often than they label
# it, so "a label must exist" is not a complete model of the layout.
_DATE_ONLY_RE = re.compile(r"^\s*(20\d{2}\s*[.\-/년\s]\s*\d{1,2}\s*[.\-/월\s]\s*\d{1,2}\s*일?)\s*$")
# What makes a bare date an *issue* date rather than any other date: the
# issuance block names its issuer -- either the institution, or the officer
# who signs for it. Matched against whitespace-compacted row text because
# these rows are heavily letter-spaced ("경 북 대 학 교 총", "총 괄 세 무 서 장").
#
# Two closed categories, both drawn from issuers actually observed on the
# certificate types in scope: institution nouns (universities and schools, tax
# and local-government offices, the social-insurance agency, industry
# associations, the SME ministry) and Korean officer-title suffixes
# (장/서장/국장/과장/팀장/부장). Adding an issuer means adding it here; that is
# the maintenance point.
_ISSUANCE_ANCHOR_RE = re.compile(
    r"대학교|대학|학교|청|공단|기관|협회|기업부"
    r"|총장|교장|서장|국장|과장|팀장|부장|校長|處長"
    r"|주무관|담당자"
)
# How far below the date the issuer may appear and still be the same block.
# Issuance blocks are short -- a date, then the signatory and stamp -- so a
# small window is enough to catch them without reaching into the body, where
# unrelated dates and institution names also occur.
_ISSUANCE_ANCHOR_LOOKAHEAD = 3
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
    score: float = 0.0
    has_explicit_separator: bool = False
    value_from_other_segment: bool = False
    """True only for a separately boxed value with verified right-side geometry."""
    relation: str = "label_match"


@dataclass(frozen=True)
class _RowObservation:
    """A visual row plus the per-segment evidence that produced it."""

    row: TextRow
    evidence: tuple[EvidenceRef | None, ...]


def _evidence_for(
    page: OCRPage, line: OCRLine, source_kind: EvidenceSourceKind, coordinate_space: CoordinateSpace
) -> EvidenceRef:
    return EvidenceRef(
        page_number=page.page_number,
        source_text=line.text,
        bounding_box=line.bounding_box,
        confidence=line.confidence,
        source_kind=source_kind,
        coordinate_space=coordinate_space,
        polygon=line.polygon,
        detection_confidence=line.detection_confidence,
        transform=page.metadata.get("transform"),
    )


def _source_observations(source: ExtractionInput) -> list[_RowObservation]:
    """Group the source into page-scoped visual rows.

    Plain-text input becomes one single-segment row per line, so the
    geometry and non-geometry paths share a single extraction
    implementation. Rows never span pages, which is what prevents a label
    at the bottom of page 1 from being paired with a value at the top of
    page 2.
    """
    if isinstance(source, str):
        return [
            _RowObservation(TextRow(1, (OCRLine(text=line),)), (None,))
            for line in source.splitlines()
            if line.strip()
        ]

    observations: list[_RowObservation] = []
    for page in source.pages:
        source_kind: EvidenceSourceKind = (
            "embedded_pdf_text"
            if page.metadata.get("source", source.provider) == "direct_pdf_text"
            else "ocr"
        )
        coordinate_space: CoordinateSpace = (
            "pdf_point" if source_kind == "embedded_pdf_text" else "pixel"
        )
        ordered = order_lines(page.lines) or [
            OCRLine(text=line) for line in page.text.splitlines() if line.strip()
        ]
        if not ordered:
            continue
        # Rebuild the page so row grouping sees lines in reading order.
        ordered_page = OCRPage(
            page_number=page.page_number,
            text=page.text,
            lines=ordered,
            confidence=page.confidence,
            duration_ms=page.duration_ms,
            metadata=page.metadata,
        )
        for row in build_rows(ordered_page):
            evidence = tuple(
                _evidence_for(ordered_page, segment, source_kind, coordinate_space)
                for segment in row.segments
            )
            observations.append(_RowObservation(row, evidence))
    return observations


def _unique_evidence(items: tuple[EvidenceRef | None, ...]) -> list[EvidenceRef]:
    """Deduplicate while preserving order, keeping the first occurrence."""
    seen: set[int] = set()
    unique: list[EvidenceRef] = []
    for item in items:
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        unique.append(item)
    return unique


def _source_lines(source: ExtractionInput) -> list[tuple[str, EvidenceRef | None]]:
    """Flattened (text, evidence) view, retained for the line-pattern helpers."""
    flattened: list[tuple[str, EvidenceRef | None]] = []
    for observation in _source_observations(source):
        for segment, evidence in zip(observation.row.segments, observation.evidence, strict=True):
            if segment.text.strip():
                flattened.append((segment.text, evidence))
    return flattened


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
    normalized = normalize_lexical_text(text)
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
    if label in {"대학교", "대학명", "학교명", "대학"}:
        return compact.endswith(("대학교", "대학")) and len(compact) > len(label)
    return len(label) >= 3 and not _looks_like_label_or_title(compact)


def _next_line_value_allowed(value: str) -> bool:
    normalized = normalize_text_field(value)
    if normalized is None:
        return False
    if _looks_like_label_or_title(normalized):
        return False
    return len(normalized) <= 80


# Longest run of consecutive row segments that may together form one
# label. Three covers the widest observed real case (a letter-spaced
# "재 학 증 명 서" title) without letting the matcher wander across a whole
# row and bolt unrelated words onto a label.
_MAX_LABEL_SEGMENTS = 5


def _right_associated(label: OCRLine, value: OCRLine) -> bool:
    """Same row, to the right, bounded by text height (source-unit independent)."""
    a, b = label.bounding_box, value.bounding_box
    if a is None or b is None or min(a.height, b.height) <= 0:
        return False
    overlap = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
    gap = b.x - (a.x + a.width)
    return overlap >= max(a.height, b.height) * 0.5 and 0 <= gap <= 12 * min(a.height, b.height)


def _row_candidates(
    observation: _RowObservation, labels: list[str], row_index: int
) -> list[ExtractionCandidate]:
    """Generate every label/value candidate found on one visual row.

    A label may be split across adjacent segments ("성" + "명:홍길동"), so
    the matcher walks consecutive segment runs rather than assuming one
    segment holds one label. Only the segments that actually produced the
    label and the value are attached as evidence.
    """
    row = observation.row
    segments = row.segments
    candidates: list[ExtractionCandidate] = []

    for start in range(len(segments)):
        for span in range(1, _MAX_LABEL_SEGMENTS + 1):
            end = start + span
            if end > len(segments):
                break
            if span > 1 and not all(
                _right_associated(left, right)
                for left, right in zip(
                    segments[start : end - 1], segments[start + 1 : end], strict=True
                )
            ):
                break
            label_run_text = " ".join(segment.text for segment in segments[start:end])
            normalized_run = _normalize_extraction_text(label_run_text)
            for label in labels:
                match = re.search(rf"(?:^|[ \t]){_label_pattern(label)}", normalized_run)
                if not match:
                    continue
                # Separator flags must be read from the *raw* tail: text
                # normalization strips leading whitespace, which is exactly
                # the signal that the value was separated from the label.
                raw_tail = normalized_run[match.end() :]
                space_separated = bool(raw_tail[:1].isspace())
                stripped_tail = raw_tail.lstrip()
                colon_separated = stripped_tail.startswith(":")
                explicit = colon_separated
                separated = colon_separated or space_separated
                from_other_segment = False

                if colon_separated:
                    # Value is the remainder of the segment that closed the label.
                    value = stripped_tail[1:].strip()
                    value_evidence = observation.evidence[end - 1 : end]
                elif stripped_tail:
                    # Label and value share one segment ("상호 한국테크").
                    value = stripped_tail
                    value_evidence = observation.evidence[end - 1 : end]
                elif end < len(segments):
                    # Label ends mid-segment: value is a later segment on the
                    # same visual row, so the two are geometrically separated.
                    if not _right_associated(segments[end - 1], segments[end]):
                        break
                    value = _normalize_extraction_text(segments[end].text)
                    value_evidence = observation.evidence[end : end + 1]
                    separated = True
                    from_other_segment = True
                else:
                    value = ""
                    value_evidence = ()

                if not value and end < len(segments):
                    # A label box that *ends* on its colon ("기업명:") with the
                    # value in the next box on the same row. Tables and ruled
                    # layouts put the label and the value in separate cells far
                    # more often than in the same box, and treating this as "no
                    # value here" abandoned the row: a real SME confirmation
                    # certificate lost its company name, its representative and
                    # its entire validity range to it. The value is
                    # geometrically separated, exactly like the case above.
                    if not _right_associated(segments[end - 1], segments[end]):
                        break
                    value = _normalize_extraction_text(segments[end].text)
                    value_evidence = observation.evidence[end : end + 1]
                    separated = True
                    from_other_segment = True

                value = _strip_trailing_labels(value, labels)
                if not value:
                    break
                if not separated and not _adjacent_value_allowed(label, value):
                    break

                # A value that lives inside the label's last box appears in
                # both slices; evidence must reference each box once.
                evidence = _unique_evidence((*observation.evidence[start:end], *value_evidence))
                candidates.append(
                    ExtractionCandidate(
                        value=value.strip(),
                        evidence=evidence,
                        score=score_candidate(
                            field_name="",
                            value=value,
                            has_explicit_separator=explicit,
                            label_is_exact=colon_separated,
                            row_index=row_index,
                        ).total,
                        has_explicit_separator=explicit,
                        value_from_other_segment=from_other_segment,
                        relation="spatial_right_of_label" if from_other_segment else "label_match",
                    )
                )
                break
            else:
                continue
            break
    return candidates


def _below_row_candidates(
    observations: list[_RowObservation], labels: list[str], row_index: int
) -> list[ExtractionCandidate]:
    """Candidates where a label ends a row and its value is on the next row
    of the *same page*."""
    candidates: list[ExtractionCandidate] = []
    for index, observation in enumerate(observations[:-1]):
        following = observations[index + 1]
        if following.row.page_number != observation.row.page_number:
            continue
        if len(following.row.segments) != 1:
            continue
        next_value = _normalize_extraction_text(following.row.text)
        if not _next_line_value_allowed(next_value):
            continue
        for label in labels:
            if not re.search(
                rf"(?:^|[ \t]){_label_pattern(label)}\s*[:：]?\s*$", observation.row.text
            ):
                continue
            value = _strip_trailing_labels(next_value, labels)
            if not value:
                continue
            evidence = [
                item for item in (*observation.evidence, *following.evidence) if item is not None
            ]
            candidates.append(
                ExtractionCandidate(
                    value=value,
                    evidence=evidence,
                    score=score_candidate(
                        field_name="",
                        value=value,
                        has_explicit_separator=False,
                        label_is_exact=True,
                        row_index=row_index,
                    ).total
                    - 10.0,
                    has_explicit_separator=False,
                    relation="label_next_row",
                )
            )
    return candidates


def rank_candidates(
    source: ExtractionInput, labels: list[str], field_name: str
) -> list[ExtractionCandidate]:
    """All plausible candidates for a field, best first.

    Candidates that cannot be a value of this field are dropped outright, so
    an impossible capture becomes an unresolved field rather than a
    confident wrong one.
    """
    observations = _source_observations(source)
    ranked: list[ExtractionCandidate] = []
    for row_index, observation in enumerate(observations):
        for candidate in _row_candidates(observation, labels, row_index):
            if not is_valid_value(field_name, candidate.value):
                continue
            if looks_like_boilerplate(candidate.value):
                continue
            ranked.append(
                ExtractionCandidate(
                    value=candidate.value,
                    evidence=candidate.evidence,
                    score=score_candidate(
                        field_name=field_name,
                        value=candidate.value,
                        has_explicit_separator=candidate.has_explicit_separator,
                        label_is_exact=candidate.has_explicit_separator,
                        row_index=row_index,
                    ).total,
                    has_explicit_separator=candidate.has_explicit_separator,
                    value_from_other_segment=candidate.value_from_other_segment,
                    relation=candidate.relation,
                )
            )
    ranked.extend(
        candidate
        for candidate in _below_row_candidates(observations, labels, len(observations))
        if is_valid_value(field_name, candidate.value)
        and not looks_like_boilerplate(candidate.value)
    )
    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    return ranked


def candidate_after_label(
    source: ExtractionInput, labels: list[str], field_name: str | None = None
) -> ExtractionCandidate | None:
    """Best label/value candidate for `field_name`, or None.

    When `field_name` is given the candidate must be a shape-valid value for
    that field and is chosen by score rather than by document order. Without
    it the behaviour is the unranked, shape-agnostic legacy path used by the
    date/number helpers.
    """
    if field_name is None:
        observations = _source_observations(source)
        found = []
        for row_index, observation in enumerate(observations):
            found.extend(_row_candidates(observation, labels, row_index))
        ranked = found or _below_row_candidates(observations, labels, len(observations))
    else:
        ranked = rank_candidates(source, labels, field_name)
    if not ranked:
        return None
    # Evidence class decides priority first. Within that class, a unique top
    # score can pick the primary field printed earlier on a form; exact ties
    # remain unresolved instead of guessing.
    explicit = [candidate for candidate in ranked if candidate.has_explicit_separator]
    strongest = explicit or [c for c in ranked if c.relation != "label_next_row"] or ranked
    values = {_compact(normalize_lexical_text(candidate.value)) for candidate in strongest}
    if len(values) == 1:
        return strongest[0]
    if not any(
        evidence is not None and evidence.bounding_box is not None
        for candidate in strongest
        for evidence in candidate.evidence
    ):
        return None
    top_score = strongest[0].score
    tied_top = [candidate for candidate in strongest if abs(candidate.score - top_score) < 0.000001]
    return strongest[0] if len(tied_top) == 1 else None


def candidate_right_of_label(
    source: ExtractionInput, labels: list[str]
) -> ExtractionCandidate | None:
    """Return the nearest observation on the same visual row as an empty label.

    This is deliberately unavailable for flattened string input. It requires
    source geometry, a value to the right of the label, substantial vertical
    overlap, and a bounded horizontal gap. Both observations remain attached
    as evidence. The helper does not decide field semantics; the caller still
    validates the returned text for its particular field.
    """
    if isinstance(source, str):
        return None
    observations = _source_lines(source)
    normalized_labels = {_compact(_normalize_extraction_text(label)) for label in labels}
    for label_text, label_evidence in observations:
        if label_evidence is None or label_evidence.bounding_box is None:
            continue
        if (
            _compact(_normalize_extraction_text(label_text).rstrip(":").strip())
            not in normalized_labels
        ):
            continue
        label_box = label_evidence.bounding_box
        candidates: list[tuple[float, float, str, EvidenceRef]] = []
        for value_text, value_evidence in observations:
            if (
                value_evidence is None
                or value_evidence is label_evidence
                or value_evidence.page_number != label_evidence.page_number
                or value_evidence.bounding_box is None
                or not _next_line_value_allowed(value_text)
            ):
                continue
            value_box = value_evidence.bounding_box
            horizontal_gap = value_box.x - (label_box.x + label_box.width)
            if not _right_associated(
                OCRLine(label_text, bounding_box=label_box),
                OCRLine(value_text, bounding_box=value_box),
            ):
                continue
            label_center = label_box.y + label_box.height / 2
            value_center = value_box.y + value_box.height / 2
            candidates.append(
                (abs(value_center - label_center), horizontal_gap, value_text, value_evidence)
            )
        if candidates:
            _, _, value, evidence = min(candidates, key=lambda item: (item[0], item[1]))
            return ExtractionCandidate(
                _strip_trailing_labels(_normalize_extraction_text(value), labels),
                [label_evidence, evidence],
                value_from_other_segment=True,
                relation="spatial_right_of_label",
            )
    return None


def candidate_matching_line(
    source: ExtractionInput, pattern: re.Pattern[str]
) -> ExtractionCandidate | None:
    """Return the first full-line semantic pattern match with source evidence."""
    for line, evidence in _source_lines(source):
        normalized = _normalize_extraction_text(line)
        if pattern.fullmatch(normalized) and not _looks_like_label_or_title(normalized):
            return ExtractionCandidate(normalized, [evidence] if evidence is not None else [])
    return None


def after_label(source: ExtractionInput, labels: list[str]) -> str | None:
    candidate = candidate_after_label(source, labels)
    return candidate.value if candidate else None


def standalone_date_candidate(source: ExtractionInput) -> ExtractionCandidate | None:
    """The one unambiguous issue date in an otherwise unlabelled issuance block.

    Certificates in this domain print their issue date as a bare line above the
    signing officer's name and stamp, with no issue-date label at all. Requiring
    a label therefore loses the field on most real documents.

    Two conditions must both hold, and both exist to refuse rather than to
    gain coverage:

    * **Ambiguity is fatal.** Every bare date on the document must normalize
      to the same value. Several different bare dates -- a birth date printed
      alone, a validity start printed alone -- mean the document is not telling
      us which one issued it, and the field stays unresolved.
    * **The date must be in an issuance block.** The rows just below it must
      name an issuer (an institution or a signing officer). A lone date sitting
      in a transcript body next to grades is not an issue date, however unique
      it is.

    Both failures leave the field unresolved, which routes to human review.
    That is the correct outcome: a guessed issue date silently satisfies every
    downstream date rule.
    """
    observations = _source_observations(source)
    values: dict[str, ExtractionCandidate] = {}
    for observation in observations:
        text = canonicalize_numeric_text(observation.row.text).strip()
        if not _DATE_ONLY_RE.match(text):
            continue
        normalized = normalize_date(text)
        if normalized is None:
            continue
        evidence = next((item for item in observation.evidence if item is not None), None)
        values.setdefault(
            normalized,
            ExtractionCandidate(
                text,
                [evidence] if evidence is not None else [],
                score=0.0,
                has_explicit_separator=False,
                value_from_other_segment=False,
            ),
        )
    if len(values) != 1:
        return None
    candidate = next(iter(values.values()))
    for index, observation in enumerate(observations):
        if canonicalize_numeric_text(observation.row.text).strip() != candidate.value:
            continue
        # A label immediately preceding a bare date owns that date. It is
        # not an unlabelled issuance block (e.g. graduation or employment).
        if index and any(
            _compact(observations[index - 1].row.text).rstrip(":") == _compact(label)
            for label in _KNOWN_LABELS
            if not _DOCUMENT_TITLE_RE.search(_compact(label))
        ):
            continue
        if _followed_by_issuer(observations, index):
            return candidate
    return None


def _followed_by_issuer(observations: list[_RowObservation], index: int) -> bool:
    """True when the next few rows name an issuer, i.e. this date sits in the
    issuance block rather than in the document body."""
    following = observations[index + 1 : index + 1 + _ISSUANCE_ANCHOR_LOOKAHEAD]
    if not following:
        return False
    # Never look past a page boundary: an issuance block does not continue on
    # the next page, so a cross-page match would be a coincidence.
    page_number = observations[index].row.page_number
    for observation in following:
        if observation.row.page_number != page_number:
            return False
        if _ISSUANCE_ANCHOR_RE.search(_compact(observation.row.text)):
            return True
    return False


def split_range(raw: str | None) -> tuple[str | None, str | None]:
    """Splits a 'start ~ end' style range. Returns (None, None) when no
    range separator is present -- callers decide whether to treat the whole
    string as a single value instead."""
    return split_date_range(raw)


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
        self,
        text: ExtractionInput,
        field_name: str,
        labels: list[str],
        *,
        allow_spatial_right: bool = False,
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels, field_name)
        used_spatial_candidate = False
        if candidate is None and allow_spatial_right:
            spatial = candidate_right_of_label(text, labels)
            if spatial is not None and is_valid_value(field_name, spatial.value):
                candidate = spatial
                used_spatial_candidate = True
        raw = candidate.value if candidate else None
        normalized = normalize_text_field(raw)
        if (
            candidate is None
            or normalized is None
            or self._reject_text_candidate(field_name, normalized)
        ):
            return self.missing(field_name)
        assert raw is not None
        method = "spatial_right_of_label" if used_spatial_candidate else candidate.relation
        return self._value(field_name, raw, normalized, method, candidate)

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

    def issue_date_field(self, text: ExtractionInput, labels: list[str]) -> ExtractedValue:
        """Explicit opt-in for issuance-block inference; never used by other dates."""
        labelled = self.date_field(text, "issue_date", labels)
        if labelled.normalized_value is not None:
            return labelled
        if any(re.search(_label_pattern(label), source_text(text)) for label in labels):
            return labelled
        candidate = standalone_date_candidate(text)
        normalized = normalize_date(candidate.value) if candidate else None
        if candidate is None or normalized is None:
            return labelled
        return replace(
            self._value(
                "issue_date", candidate.value, normalized, "document_semantic_issue_date", candidate
            ),
            needs_review=True,
        )

    def business_number_field(
        self, text: ExtractionInput, field_name: str, labels: list[str]
    ) -> ExtractedValue:
        candidate = candidate_after_label(text, labels)
        raw_context = candidate.value if candidate else None
        match = (
            BUSINESS_NUMBER_RE.search(canonicalize_numeric_text(raw_context))
            if raw_context
            else None
        )
        raw_value = raw_context[match.start() : match.end()] if match and raw_context else None
        if normalize_business_number(raw_context) is None:
            return self.missing(field_name)
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
