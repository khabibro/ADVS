"""P2.1 observation matrix, pipeline trace and failure classification.

Joins, and reads nothing beyond, these private artifacts:

1. ``observations_private.json``      raw OCR observations from the unmodified
   production PaddleOCR path, with geometry, confidence and provenance.
2. ``observation_gold_private.json``  human visual annotation of label/value
   visibility, readability and region, recorded before any OCR geometry was
   shown.
3. the frozen P1 gold ``ground_truth_v2.json``, read-only and unmodified.

Measurement rules
-----------------
*Comparison is format-insensitive.* A printed business number may use hyphens
or en dashes, a date may use particles, and a form may letter-space a name.
None of those is a recognition error, so the comparison key removes exactly
those differences and nothing else.

*Detection is scored page-wide.* The annotation coordinates were refined
against the observation stream, so region containment cannot by itself prove
that the detector found anything. Detection is judged by whether the value a
human read is recoverable from the page's observations at all, using a
per-character containment measure as well as an exact one, so a value whose
glyphs were partly dropped is separated from one whose glyphs were all
detected but misread.

Writes only to the gitignored runtime directory.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path("apps/api").resolve()))

from app.document_intelligence.classification.classifier import (
    DocumentClassifier,
)
from app.document_intelligence.extraction.base import (
    _KNOWN_LABELS,
    _row_candidates,
    _source_observations,
    rank_candidates,
)
from app.document_intelligence.extraction.fields import (
    is_valid_value,
    looks_like_boilerplate,
)
from app.document_intelligence.extraction.registry import (
    ExtractorRegistry,
)
from app.document_intelligence.normalization.field_normalizer import (
    canonicalize_numeric_text,
)
from app.document_intelligence.ocr.models import (
    BoundingBox,
    OCRDocumentResult,
    OCRLine,
    OCRPage,
)

RUNTIME = Path("evaluation/private_runtime/p2_1")
FROZEN_GOLD = Path("evaluation/backend_round2/work/ground_truth_v2.json")

#: Region-coverage fraction at which a human-annotated region counts as
#: covered by OCR geometry. Reported alongside the raw figure.
COVERAGE_THRESHOLD = 0.25
#: Fraction of the gold value's characters that must be recoverable from the
#: page's observations before a field is called observed-but-misread rather
#: than not observed at all.
CHAR_RECALL_THRESHOLD = 0.6

_WS = re.compile(r"\s+")
_ISSUER_RE = re.compile(
    r"대학교|대학|학교|청|공단|기관|협회|기업부|총장|교장|서장|국장|과장|팀장|부장|"
    r"校長|處長|주무관|담당자"
)
_DATE_ONLY_RE = re.compile(
    r"\s*(20\d{2}\s*[.\-/년\s]\s*\d{1,2}\s*[.\-/월\s]\s*\d{1,2}\s*일?)\s*"
)

_DIGIT_FIELDS = {
    "issue_date",
    "valid_from",
    "valid_until",
    "business_registration_number",
    "gpa",
    "gpa_scale",
}


def compact(text: str) -> str:
    return _WS.sub("", unicodedata.normalize("NFC", text or ""))


def signature(field_name: str, text: str | None) -> str:
    """Format-insensitive comparison key for one field."""
    if text is None:
        return ""
    if field_name in _DIGIT_FIELDS:
        return re.sub(r"[^0-9.]", "", text)
    return compact(text)


def norm_box(box, width, height):
    return (box[0] * width, box[1] * height, box[2] * width, box[3] * height)


def coverage_of(box, lines) -> float:
    bx0, by0, bx1, by1 = box
    area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    if area <= 0:
        return 0.0
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    covered = 0.0
    for line in lines:
        ob = line.get("bbox")
        if not ob:
            continue
        ox0, oy0 = ob["x"], ob["y"]
        ox1, oy1 = ox0 + ob["width"], oy0 + ob["height"]
        iw = min(bx1, ox1) - max(bx0, ox0)
        ih = min(by1, oy1) - max(by0, oy0)
        if iw <= 0 or ih <= 0:
            if ox0 <= cx <= ox1 and oy0 <= cy <= oy1:
                covered += area
            continue
        covered += iw * ih
    return min(1.0, covered / area)


def observations_in(lines, box):
    bx0, by0, bx1, by1 = box
    hits = []
    for line in lines:
        ob = line.get("bbox")
        if not ob:
            continue
        ox0, oy0 = ob["x"], ob["y"]
        ox1, oy1 = ox0 + ob["width"], oy0 + ob["height"]
        if min(bx1, ox1) - max(bx0, ox0) > 0 and min(by1, oy1) - max(by0, oy0) > 0:
            hits.append(line)
    hits.sort(
        key=lambda item: (
            round((item["bbox"]["y"] + item["bbox"]["height"] / 2) / 12),
            item["bbox"]["x"],
        )
    )
    return hits


def char_recall(gold_sig: str, haystack_sig: str) -> float:
    """Fraction of the gold signature's characters present in the haystack.

    Separates a value whose glyphs the detector dropped from one whose glyphs
    were all detected but transcribed wrongly.
    """
    if not gold_sig:
        return 0.0
    remaining = Counter(haystack_sig)
    hits = 0
    for character in gold_sig:
        if remaining.get(character, 0) > 0:
            remaining[character] -= 1
            hits += 1
    return hits / len(gold_sig)


def build_result(document) -> OCRDocumentResult:
    pages = []
    for page in document["pages"]:
        lines = [
            OCRLine(
                text=line["text"],
                confidence=line["confidence"],
                bounding_box=None if not line["bbox"] else BoundingBox(**line["bbox"]),
                polygon=None
                if not line["polygon"]
                else tuple(tuple(point) for point in line["polygon"]),
                detection_confidence=line["detection_confidence"],
            )
            for line in page["lines"]
        ]
        pages.append(
            OCRPage(
                page_number=page["page_number"],
                text=page["text"],
                lines=lines,
                confidence=page["page_confidence"],
                duration_ms=page["duration_ms"],
                metadata=page["metadata"],
            )
        )
    return OCRDocumentResult(
        provider="paddle",
        pages=pages,
        assembled_text="\n\n".join(p.text for p in pages),
    )


ALIASES = {
    "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE": {
        "workplace_name": ["사업장명", "사업장 명칭"],
        "business_registration_number": ["사업자등록번호", "등록번호"],
        "issue_date": ["발급일", "발급일자", "발행일자"],
        "valid_until": ["증명서유효기간", "유효기한", "유효기간"],
    },
    "BUSINESS_REGISTRATION_CERTIFICATE": {
        "company_name": ["법인명(단체명)", "법인명칭", "상호", "상호명"],
        "representative_name": ["대표자 성명", "대표자", "대표자명"],
        "business_registration_number": ["사업자등록번호", "등록번호"],
        "business_address": ["사업장 소재지", "소재지"],
        "issue_date": ["발급일자", "발급일", "발행일자"],
    },
    "SME_CONFIRMATION_CERTIFICATE": {
        "company_name": ["기업명", "회사명", "상호"],
        "representative_name": ["대표자", "대표자명"],
        "business_registration_number": ["사업자등록번호", "등록번호"],
        "certificate_number": ["발급번호", "확인번호", "증명서번호", "일련번호"],
        "issue_date": ["발급일", "발급일자", "발행일자"],
        "valid_from": ["유효기간"],
        "valid_until": ["유효기간"],
    },
    "ENROLLMENT_CERTIFICATE": {
        "student_name": ["학생명", "성명", "이름"],
        "university_name": ["대학교", "대학명", "학교명", "대학"],
        "department": ["학과", "전공"],
        "student_id": ["학번"],
        "issue_date": ["발급일", "발급일자", "발행일자"],
    },
    "TRANSCRIPT": {
        "student_name": ["학생명", "성명", "이름"],
        "university_name": ["대학교", "대학명", "학교명", "대학"],
        "student_id": ["학번"],
        "issue_date": ["발급일", "발급일자", "발행일자"],
        "gpa": ["GPA", "총평점", "평점평균", "평점"],
        "gpa_scale": ["GPA", "총평점", "평점평균", "평점"],
    },
}


def alias_status(label_form, aliases, page_sig: str) -> tuple[str, bool, bool]:
    """Return (status, label_in_alias_set, label_recovered_in_ocr).

    The two booleans are independent facts and must not be collapsed: a label
    can be printed and perfectly recognized yet absent from the extractor's
    vocabulary (an extraction defect), or present in the vocabulary yet absent
    from the OCR text (a recognition defect). Reporting only the worse of the
    two would hide whichever one is actionable.
    """
    if not aliases:
        return "NO_EXTRACTOR_FOR_FIELD", False, False
    if not label_form:
        return "NO_LABEL_ON_DOCUMENT", False, False
    whole = compact(label_form)
    head = compact(re.split(r"[/(]", label_form)[0])
    alias_set = {compact(alias) for alias in aliases}
    in_alias = (
        whole in alias_set
        or head in alias_set
        or any(alias in head for alias in alias_set if len(alias) >= 2)
    )
    recovered = bool(head) and head in page_sig
    if in_alias and recovered:
        return "IN_ALIAS_SET", True, True
    if in_alias:
        return "IN_ALIAS_SET_LABEL_NOT_IN_OCR", True, False
    if recovered:
        return "PRINTED_LABEL_NOT_IN_ALIAS_SET", False, True
    return "PRINTED_LABEL_NOT_IN_ALIAS_SET_AND_NOT_IN_OCR", False, False


@dataclass
class Row:
    sample_id: str
    document_type: str
    field: str
    gold_evaluated: bool
    gold_category: str | None
    gt_state: str
    label_visible: bool
    value_visible: bool
    human_readable: bool
    label_coverage: float
    value_coverage: float
    label_text_recognized: str
    value_detected: str
    value_char_recall: float
    ocr_text_correct: str
    produced_value: str | None
    produced_correct: str
    extraction_method: str | None
    needs_review: bool
    distinct_candidates: int
    valid_candidates: int
    diagnosis: str
    rationale: str
    label_alias_status: str
    label_in_alias_set: bool
    label_recovered: bool
    gold_disagreement: str | None
    trace: dict = field(default_factory=dict)


def trace_field(observations, field_name, labels) -> dict:
    """Stage-by-stage record of where a field's information stops."""
    trace: dict = {"label_rows": [], "candidates": []}
    for row_index, observation in enumerate(observations):
        if any(compact(label) in compact(observation.row.text) for label in labels):
            trace["label_rows"].append(
                {
                    "row_index": row_index,
                    "segments": [segment.text for segment in observation.row.segments],
                    "row_text": observation.row.text,
                }
            )
        if len(trace["candidates"]) < 14:
            for candidate in _row_candidates(observation, labels, row_index):
                trace["candidates"].append(
                    {
                        "row_index": row_index,
                        "relation": candidate.relation,
                        "raw_value": candidate.value,
                        "explicit_separator": candidate.has_explicit_separator,
                        "shape_valid": is_valid_value(field_name, candidate.value),
                        "boilerplate": looks_like_boilerplate(candidate.value),
                    }
                )
                break
    return trace


def trace_dates(observations) -> dict:
    """Why the bare-date issue-date path did or did not fire."""
    trace: dict = {
        "date_only_rows": [],
        "blocked_by_preceding_label": [],
        "issuer_lookahead": [],
    }
    known = [
        label
        for label in _KNOWN_LABELS
        if not label.endswith(("증명서", "확인서", "등록증"))
    ]
    for index, observation in enumerate(observations):
        canonical = canonicalize_numeric_text(observation.row.text).strip()
        if not _DATE_ONLY_RE.fullmatch(canonical):
            continue
        trace["date_only_rows"].append(canonical)
        if index:
            prior = compact(observations[index - 1].row.text)
            matched = [label for label in known if compact(label) in prior]
            if matched:
                trace["blocked_by_preceding_label"].append(
                    {"date": canonical, "blocked_by": matched}
                )
        window = observations[index + 1 : index + 4]
        trace["issuer_lookahead"].append(
            {
                "date": canonical,
                "issuer_rows_within_3": [
                    item.row.text
                    for item in window
                    if _ISSUER_RE.search(compact(item.row.text))
                ],
            }
        )
    return trace


def diagnose(
    *,
    gold_evaluated,
    gold_category,
    gt_state,
    label_visible,
    value_visible,
    human_readable,
    label_region_hit,
    label_in_alias_set,
    label_recovered,
    value_observed,
    char_recall,
    ocr_text_correct,
    produced_correct,
    distinct_candidates,
    field_is_bare_date=False,
) -> tuple[str, str]:
    """One primary diagnosis per field, first matching rule wins."""
    if not gold_evaluated or gold_category in {"AMBIGUOUS", "NOT_EVIDENCED"}:
        return (
            "NOT_EVALUATED",
            f"the frozen scorer does not evaluate gold category {gold_category}",
        )
    if (
        gt_state in {"ABSENT_BY_DESIGN", "NOT_PRESENT"}
        or gold_category == "VERIFIED_ABSENT"
    ):
        return (
            "SOURCE_ABSENT",
            "the document does not carry this value; absence is the truth",
        )
    if not value_visible:
        return "SOURCE_ABSENT", "no value is visible on the page for this field"
    if not human_readable:
        return (
            "SOURCE_UNREADABLE",
            "a human cannot read the value at source resolution, so no correct reading exists",
        )
    if not value_observed or char_recall < CHAR_RECALL_THRESHOLD:
        return (
            "DETECTION_FAILURE",
            (
                "a human read this value on the page, but its characters are not recoverable "
                f"from the page's observations (character recall {char_recall:.2f})"
            ),
        )
    if ocr_text_correct == "YES" and produced_correct == "YES":
        return "NONE", "OCR correct and extraction correct"
    if (
        ocr_text_correct in {"YES", "PARTIAL", "NEAR"}
        and produced_correct == "NO_VALUE"
    ):
        if label_visible and not label_region_hit:
            return (
                "DETECTION_FAILURE",
                "the value was read correctly but no OCR observation covers the printed label",
            )
        if label_visible and not label_in_alias_set:
            return (
                "EXTRACTION_FAILURE",
                (
                    "the value was read correctly, but the extractor's alias set for this field "
                    "does not contain the label this document prints"
                ),
            )
        if label_visible and not label_recovered:
            return (
                "RECOGNITION_FAILURE",
                (
                    "the value was read correctly but the printed label is not recoverable from "
                    "the OCR text, so the alias match cannot succeed"
                ),
            )
        if distinct_candidates > 1:
            return (
                "STRUCTURAL_INTERPRETATION_FAILURE",
                (
                    f"OCR read {distinct_candidates} competing values for this field and choosing "
                    "the right one requires the document's row/section structure"
                ),
            )
        if field_is_bare_date:
            return (
                "EXTRACTION_FAILURE",
                (
                    "the date is printed without a label and the issuance-block date inference "
                    "refused it"
                ),
            )
        if not label_visible:
            return (
                "STRUCTURAL_INTERPRETATION_FAILURE",
                (
                    "the value was recognized but the document prints no label for this field, so "
                    "resolving it depends on block structure"
                ),
            )
        return (
            "EXTRACTION_FAILURE",
            "OCR observed the value correctly but the production extractor produced no field",
        )
    if ocr_text_correct in {"YES", "PARTIAL", "NEAR"}:
        if produced_correct == "YES":
            return (
                "AMBIGUOUS",
                (
                    "the field resolved correctly although the co-located observation does not "
                    "match; the value must have come from a different observation"
                ),
            )
        return (
            "ASSOCIATION_FAILURE",
            "OCR read the value correctly at its position but a different value was produced",
        )
    if produced_correct == "NO_VALUE":
        return (
            "RECOGNITION_FAILURE",
            "the value was observed but not transcribed correctly where it is printed",
        )
    if produced_correct == "YES":
        return (
            "AMBIGUOUS",
            (
                "the field resolved correctly even though the co-located observation is wrong; "
                "the value came from a different observation"
            ),
        )
    return (
        "RECOGNITION_FAILURE",
        (
            "OCR misread the value where it is printed, and the wrong text became a confident "
            "non-null field value"
        ),
    )


def main() -> int:
    from PIL import Image

    observations = json.loads(
        (RUNTIME / "observations_private.json").read_text(encoding="utf-8")
    )
    gold_obs = json.loads(
        (RUNTIME / "observation_gold_private.json").read_text(encoding="utf-8")
    )
    id_map = json.loads((RUNTIME / "id_map_private.json").read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN_GOLD.read_text(encoding="utf-8"))
    real_to_r2 = {real: r2 for r2, real in id_map["r2_to_real"].items()}

    classifier = DocumentClassifier()
    registry = ExtractorRegistry()
    docs = {doc["sample_id"]: doc for doc in observations["documents"]}
    rows: list[Row] = []

    for sample_id, annotation in gold_obs["samples"].items():
        document = docs[sample_id]
        result = build_result(document)
        classification = classifier.classify(result.assembled_text)
        predicted = classification.predicted_type.value
        values = {
            item.field_name: item
            for item in registry.extract(classification.predicted_type, result)
        }
        page = document["pages"][0]
        lines = page["lines"]
        page_text = page["text"]
        page_sig_all = compact(page_text)
        with Image.open(document["captured_input_images"][0]["image_path"]) as probe:
            width, height = probe.size

        gold_fields = frozen["samples"][real_to_r2[sample_id]]["fields"]
        row_observations = _source_observations(result)
        date_trace = trace_dates(row_observations)

        for name, entry in annotation["fields"].items():
            gold_entry = gold_fields.get(name)
            gold_category = (gold_entry or {}).get("gt")
            gold_value = None if gold_entry is None else gold_entry.get("value")
            label_box = (
                norm_box(entry["label_bbox"], width, height)
                if entry.get("label_bbox")
                else None
            )
            value_box = (
                norm_box(entry["value_bbox"], width, height)
                if entry.get("value_bbox")
                else None
            )
            label_hits = observations_in(lines, label_box) if label_box else []
            value_hits = observations_in(lines, value_box) if value_box else []
            label_cov = coverage_of(label_box, lines) if label_box else 0.0
            value_cov = coverage_of(value_box, lines) if value_box else 0.0
            region_text = " ".join(item["text"] for item in value_hits)

            label_form = entry.get("label_form")
            label_status, label_in_alias, label_rec = alias_status(
                label_form, ALIASES.get(predicted, {}).get(name, []), page_sig_all
            )

            gold_sig = (
                signature(name, str(gold_value)) if gold_value is not None else ""
            )
            region_sig = signature(name, region_text)
            page_sig = signature(name, page_text)
            matched_observations = [
                line["text"]
                for line in lines
                if gold_sig and gold_sig in signature(name, line["text"])
            ]
            recall = char_recall(gold_sig, region_sig) if gold_sig else 0.0
            if gold_sig and (gold_sig in region_sig or gold_sig in page_sig):
                recall = 1.0
            value_observed = recall >= CHAR_RECALL_THRESHOLD or bool(
                matched_observations
            )

            if gold_value is None:
                ocr_correct, detected = "N_A", "N_A"
            elif gold_sig in region_sig:
                ocr_correct, detected = "YES", "OBSERVED_IN_REGION"
            elif gold_sig in page_sig:
                ocr_correct, detected = "PARTIAL", "OBSERVED_ELSEWHERE_ON_PAGE"
            elif recall >= 1.0:
                ocr_correct, detected = "NEAR", "TEXT_NEAR_CORRECT"
            elif recall >= CHAR_RECALL_THRESHOLD:
                ocr_correct, detected = "NO", "MISRECOGNIZED"
            else:
                ocr_correct, detected = "NO_OBSERVATION", "NOT_OBSERVED"

            produced = values.get(name)
            produced_value = produced.normalized_value if produced else None
            if produced_value is None:
                produced_correct = "NO_VALUE"
            elif gold_value is not None and compact(produced_value) == compact(
                str(gold_value)
            ):
                produced_correct = "YES"
            else:
                produced_correct = "NO"

            field_labels = ALIASES.get(predicted, {}).get(name, [])
            raw_values = {
                compact(candidate.value)
                for observation in row_observations
                for candidate in _row_candidates(observation, field_labels, 0)
            }
            distinct = len(raw_values)
            valid_count = len(rank_candidates(result, field_labels, name))

            disagreement = None
            if gold_value is not None and gold_sig and gold_sig not in page_sig:
                disagreement = (
                    "gold value is not recoverable from any OCR observation on the page"
                )

            diagnosis, rationale = diagnose(
                gold_evaluated=gold_entry is not None,
                gold_category=gold_category,
                gt_state=entry["gt_state"],
                label_visible=entry["label_visible"],
                value_visible=entry["value_visible"],
                human_readable=entry["human_readable"],
                label_region_hit=bool(label_hits),
                label_in_alias_set=label_in_alias,
                label_recovered=label_rec,
                value_observed=value_observed,
                char_recall=recall,
                ocr_text_correct=ocr_correct,
                produced_correct=produced_correct,
                distinct_candidates=distinct,
                field_is_bare_date=name == "issue_date",
            )
            rows.append(
                Row(
                    sample_id=sample_id,
                    document_type=predicted,
                    field=name,
                    gold_evaluated=gold_entry is not None,
                    gold_category=gold_category,
                    gt_state=entry["gt_state"],
                    label_visible=entry["label_visible"],
                    value_visible=entry["value_visible"],
                    human_readable=entry["human_readable"],
                    label_coverage=round(label_cov, 3),
                    value_coverage=round(value_cov, 3),
                    label_text_recognized="Y" if label_rec else "N",
                    value_detected=detected,
                    value_char_recall=round(recall, 3),
                    ocr_text_correct=ocr_correct,
                    produced_value=produced_value,
                    produced_correct=produced_correct,
                    extraction_method=produced.extraction_method if produced else None,
                    needs_review=bool(produced.needs_review) if produced else False,
                    distinct_candidates=distinct,
                    valid_candidates=valid_count,
                    diagnosis=diagnosis,
                    rationale=rationale,
                    label_alias_status=label_status,
                    label_in_alias_set=label_in_alias,
                    label_recovered=label_rec,
                    gold_disagreement=disagreement,
                    trace={
                        **trace_field(row_observations, name, field_labels),
                        "dates": date_trace,
                    },
                )
            )

    (RUNTIME / "observation_matrix_private.json").write_text(
        json.dumps(
            {
                "schema_version": "p2-1-observation-matrix-private-v3",
                "warning": "CONTAINS OCR TEXT AND EXTRACTED VALUES FROM PRIVATE DOCUMENTS.",
                "coverage_threshold": COVERAGE_THRESHOLD,
                "char_recall_threshold": CHAR_RECALL_THRESHOLD,
                "rows": [asdict(row) for row in rows],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    summarize(rows)
    return 0


def summarize(rows: list[Row]) -> None:
    evaluated = [row for row in rows if row.diagnosis != "NOT_EVALUATED"]
    observed_states = {"OBSERVED_IN_REGION", "OBSERVED_ELSEWHERE_ON_PAGE"}
    payload = {
        "schema_version": "p2-1-failure-taxonomy-private-v3",
        "coverage_threshold": COVERAGE_THRESHOLD,
        "char_recall_threshold": CHAR_RECALL_THRESHOLD,
        "rows_total": len(rows),
        "rows_evaluated": len(evaluated),
        "diagnosis_all_rows": dict(Counter(row.diagnosis for row in rows)),
        "diagnosis_evaluated": dict(Counter(row.diagnosis for row in evaluated)),
        "detection_evaluated": dict(
            Counter(
                "observed"
                if row.value_detected in observed_states
                else row.value_detected
                for row in evaluated
            )
        ),
        "ocr_text_correct_evaluated": dict(
            Counter(row.ocr_text_correct for row in evaluated)
        ),
        "gold_disagreements": [
            {
                "sample_id": row.sample_id,
                "field": row.field,
                "note": row.gold_disagreement,
            }
            for row in rows
            if row.gold_disagreement
        ],
    }
    (RUNTIME / "failure_taxonomy_private.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print(
        f"{'DOC':9s} {'FIELD':26s} {'GOLDCAT':15s} {'VIS':3s} {'RD':3s} {'LBL':4s} "
        f"{'DET':22s} {'OCR':14s} {'PROD':9s} {'#CAND':5s} {'#VAL':4s} DIAGNOSIS"
    )
    for row in sorted(rows, key=lambda item: (item.sample_id, item.field)):
        print(
            f"{row.sample_id:9s} {row.field:26s} {row.gold_category!s:15s} "
            f"{('Y' if row.value_visible else 'N'):3s} "
            f"{('Y' if row.human_readable else 'N'):3s} "
            f"{row.label_text_recognized:4s} {row.value_detected:22s} "
            f"{row.ocr_text_correct:14s} {row.produced_correct:9s} "
            f"{row.distinct_candidates:5d} {row.valid_candidates:4d} {row.diagnosis}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
