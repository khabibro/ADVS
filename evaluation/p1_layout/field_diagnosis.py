"""Per-field structural failure diagnosis.

Replays cached observations through the *production* candidate functions and
records, for every field the pipeline attempted, exactly which stage lost the
value. Emits a per-field verdict plus a taxonomy category drawn from the
categories defined in failure_taxonomy.md.

No production code is modified. No authoritative path is exercised.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "p1_layout"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from observation_cache import DEFAULT_DUMP, load  # noqa: E402

from app.core.domain import DocumentType  # noqa: E402
from app.document_intelligence.classification.classifier import DocumentClassifier  # noqa: E402
from app.document_intelligence.extraction.base import (  # noqa: E402
    _label_pattern,
    _row_candidates,
    _source_observations,
    rank_candidates,
)
from app.document_intelligence.extraction.fields import is_valid_value  # noqa: E402
from app.document_intelligence.extraction.registry import _EXTRACTORS  # noqa: E402
from app.document_intelligence.normalization.field_normalizer import (  # noqa: E402
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_text_field,
)

# field -> (labels, shape kind) taken from the production extractors.
FIELD_LABELS: dict[str, list[str]] = {
    "student_name": ["학생명", "성명", "이름"],
    "applicant_name": ["성명", "이름", "신청인"],
    "university_name": ["대학교", "대학명", "학교명", "대학"],
    "department": ["학과", "전공"],
    "degree": ["학위"],
    "student_id": ["학번"],
    "graduation_date": ["졸업일자", "졸업 연월일"],
    "company_name": ["법인명(단체명)", "법인명칭", "상호", "상호명"],
    "representative_name": ["대표자 성명", "대표자", "대표자명"],
    "business_registration_number": ["사업자등록번호", "등록번호"],
    "business_address": ["사업장 소재지", "소재지"],
    "business_type": ["업태"],
    "business_item": ["종목"],
    "certificate_number": ["발급번호", "확인번호", "증명서번호", "일련번호"],
    "workplace_name": ["사업장명", "사업장 명칭"],
    "position": ["직위", "직급"],
    "employment_start_date": ["입사일", "근무 시작일"],
    "employment_end_date": ["퇴사일", "근무 종료일"],
    "gpa": ["GPA", "총평점", "평점평균", "평점"],
    "gpa_scale": ["GPA", "총평점", "평점평균", "평점"],
    "issue_date": ["발급일", "발급일자", "발행일자"],
}

FIELD_ROLE: dict[str, str] = {
    "student_name": "label_value",
    "applicant_name": "label_value",
    "university_name": "institution",
    "department": "label_value",
    "degree": "label_value",
    "student_id": "label_value",
    "graduation_date": "label_value",
    "company_name": "label_value",
    "representative_name": "label_value",
    "business_registration_number": "identifier",
    "business_address": "label_value",
    "business_type": "label_value",
    "business_item": "label_value",
    "certificate_number": "identifier",
    "workplace_name": "label_value",
    "position": "label_value",
    "employment_start_date": "label_value",
    "employment_end_date": "label_value",
    "gpa": "measurement",
    "gpa_scale": "measurement",
    "issue_date": "date",
}

FOOTER_MARKERS = ("www.", "certpia", "원본대조", "발급일로부터", "원본대조코드", "특허", "인터넷발급")

# These helpers call candidate_after_label() WITHOUT a field name, i.e. the
# unranked, shape-agnostic path. Diagnosing them through rank_candidates()
# would measure a path production never takes.
UNRANKED_PATH_FIELDS = {
    "gpa", "gpa_scale", "issue_date", "graduation_date",
    "employment_start_date", "employment_end_date",
    "business_registration_number", "certificate_number",
    "valid_from", "valid_until",
}


def label_occurrences(observations, labels: list[str]) -> list[dict[str, Any]]:
    """Every place any alias occurs, with the text that follows it."""
    hits: list[dict[str, Any]] = []
    for index, observation in enumerate(observations):
        row_text = observation.row.text
        normalized = re.sub(r"[ \t]+", " ", row_text).strip()
        for label in sorted(labels, key=len, reverse=True):
            match = re.search(rf"(?:^|[ \t]){_label_pattern(label)}", normalized)
            if match:
                tail = normalized[match.end() :]
                stripped = tail.lstrip()
                value = stripped[1:].strip() if stripped.startswith(":") else stripped
                hits.append(
                    {
                        "row_index": index,
                        "alias": label,
                        "raw_tail": tail,
                        "inline_value": value,
                        "segments": len(observation.row.segments),
                        "in_footer": any(
                            marker in row_text.replace(" ", "") for marker in FOOTER_MARKERS
                        ),
                    }
                )
                break
    return hits


def normalize_alternate(field: str, ranked) -> str | None:
    return _apply_normalizer(field, ranked)


def _apply_normalizer(field: str, ranked) -> str | None:
    """What the production normaliser does with the top ranked candidate."""
    if not ranked:
        return None
    raw = ranked[0].value
    if field == "gpa":
        return normalize_gpa(raw)
    if field == "gpa_scale":
        return normalize_gpa_scale(raw)
    if field in {"issue_date", "graduation_date", "employment_start_date", "employment_end_date"}:
        return normalize_date(raw)
    if field == "business_registration_number":
        return normalize_business_number(raw)
    return normalize_text_field(raw)


def diagnose_field(result, field: str) -> dict[str, Any]:
    labels = FIELD_LABELS.get(field)
    if labels is None:
        return {"field": field, "diagnosis": "FIELD_NOT_PROBED"}
    observations = _source_observations(result)
    hits = label_occurrences(observations, labels)

    row_candidates: list[dict[str, Any]] = []
    for index, observation in enumerate(observations):
        for candidate in _row_candidates(observation, labels, index):
            row_candidates.append(
                {
                    "row_index": index,
                    "value": candidate.value,
                    "score": round(candidate.score, 3),
                    "relation": candidate.relation,
                    "explicit_separator": candidate.has_explicit_separator,
                    "from_other_segment": candidate.value_from_other_segment,
                    "shape_valid": is_valid_value(field, candidate.value),
                }
            )
    ranked = rank_candidates(result, labels, field)
    # The selection production actually performs for this field.
    from app.document_intelligence.extraction.base import candidate_after_label

    if field in UNRANKED_PATH_FIELDS:
        actual_selection = candidate_after_label(result, labels)
        actual_path = "unranked_label_path"
    else:
        actual_selection = candidate_after_label(result, labels, field)
        actual_path = "ranked_shape_gated_path"
    ranked_view = [
        {
            "value": c.value,
            "score": round(c.score, 3),
            "relation": c.relation,
            "explicit_separator": c.has_explicit_separator,
        }
        for c in ranked
    ]

    distinct_values = {c["value"] for c in row_candidates}
    footer_only = bool(hits) and all(hit["in_footer"] for hit in hits)
    contaminated = [
        c for c in row_candidates if len(c["value"]) > 24 and re.search(r"[가-힣]{2,}", c["value"][10:])
    ]

    normalized = _apply_normalizer(field, [actual_selection] if actual_selection else [])
    production_resolved = actual_selection is not None and normalized is not None
    if production_resolved:
        entry_extra = {
            "production_path": actual_path,
            "production_selected_value": actual_selection.value,
        }
    else:
        entry_extra = {
            "production_path": actual_path,
            "production_selected_value": None,
        }
    if production_resolved:
        verdict = "RESOLVED_BY_CURRENT_MODEL"
        category = "NONE"
    elif actual_selection is not None and normalized is None:
        verdict = "NORMALIZER_REJECTED_PRODUCTION_SELECTION"
        category = "NORMALIZATION"
    elif ranked and normalize_alternate(field, ranked) is not None:
        verdict = "RANKED_PATH_WOULD_RESOLVE_BUT_PRODUCTION_USES_OTHER_PATH"
        category = "PATH_MISMATCH"
    elif ranked:
        verdict = "NORMALIZER_REJECTED_CANDIDATE"
        category = "NORMALIZATION"
    elif not hits:
        verdict = "NO_LABEL_OBSERVED"
        category = "LABEL_DETECTION"
    elif footer_only:
        verdict = "LABEL_ONLY_IN_FOOTER_BOILERPLATE"
        category = "LABEL_DETECTION"
    elif not row_candidates:
        verdict = "LABEL_FOUND_BUT_NO_VALUE_CANDIDATE"
        category = "LABEL_VALUE_ASSOCIATION"
    elif not any(c["shape_valid"] for c in row_candidates):
        verdict = "CANDIDATES_REJECTED_BY_SHAPE"
        category = "CANDIDATE_SELECTION"
    elif len(distinct_values) > 1:
        verdict = "MULTIPLE_DISTINCT_CANDIDATES_AMBIGUOUS"
        category = "REPEATED_LABEL_AMBIGUITY"
    else:
        verdict = "AMBIGUOUS_OR_SCORE_TIE"
        category = "CANDIDATE_SELECTION"

    if contaminated and verdict != "RESOLVED_BY_CURRENT_MODEL":
        category = "COLUMN_STRUCTURE"
        verdict = "VALUE_CONTAMINATED_BY_ADJACENT_COLUMN"

    return {
        **entry_extra,
        "field": field,
        "role": FIELD_ROLE.get(field, "other"),
        "diagnosis": verdict,
        "taxonomy": category,
        "label_occurrences": len(hits),
        "footer_only_occurrences": footer_only,
        "distinct_candidate_values": len(distinct_values),
        "row_candidates": row_candidates[:12],
        "ranked": ranked_view[:12],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", default=str(DEFAULT_DUMP))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    results = load(Path(args.dump))
    classifier = DocumentClassifier()

    report: dict[str, Any] = {}
    category_counts: Counter[str] = Counter()

    for sample_id, result in results.items():
        classification = classifier.classify(result.assembled_text)
        extractor = _EXTRACTORS.get(classification.predicted_type)
        if extractor is None:
            report[sample_id] = {
                "classification": classification.predicted_type.value,
                "fields": {},
            }
            continue
        extracted = extractor.extract(result)
        produced = {value.field_name for value in extracted}
        resolved = {value.field_name for value in extracted if value.normalized_value is not None}
        fields: dict[str, Any] = {}
        for field in sorted(produced):
            entry = diagnose_field(result, field)
            if "taxonomy" not in entry:
                continue
            entry["produced_by_extractor"] = field in produced
            entry["resolved_by_production"] = field in resolved
            fields[field] = entry
            category_counts[entry["taxonomy"]] += 1
        report[sample_id] = {
            "classification": classification.predicted_type.value,
            "classification_confidence": classification.confidence_score,
            "fields": fields,
        }

    out = Path(args.out) if args.out else Path(
        "/var/folders/yb/qd_ktv9s0m37gmwmskgmzh5m0000gn/T/opencode/advs/p1_field_diagnosis.json"
    )
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'sample':9} {'field':28} {'diagnosis':44} taxonomy")
    for sample_id, entry in report.items():
        for field, item in entry["fields"].items():
            print(
                f"{sample_id:9} {field:28} {item['diagnosis']:44} {item['taxonomy']}"
            )
    print()
    print("taxonomy counts:")
    for category, count in category_counts.most_common():
        print(f"  {category:32} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())