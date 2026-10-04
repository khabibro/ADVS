"""P2.1 experiment: does the dormant structural layer resolve fields?

Runs the *unmodified*, currently-unreferenced structural layer
(`document_intelligence.layout` plus `extraction.structural`) against the
frozen OCR observations and reports, per unresolved field, whether it yields a
candidate that the production extractor did not already produce.

This is EVALUATION_ONLY. It imports the layer; it does not wire it into any
production path, and nothing it produces can change production behaviour. The
comparison is deliberately restricted to fields OCR already read correctly, so
the only variable is structural interpretation.

Writes only to the gitignored runtime directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("apps/api").resolve()))

from app.document_intelligence.classification.classifier import (
    DocumentClassifier,
)
from app.document_intelligence.extraction import structural
from app.document_intelligence.extraction.base import _source_observations
from app.document_intelligence.extraction.registry import (
    ExtractorRegistry,
)
from app.document_intelligence.layout import build_page_structure

RUNTIME = Path("evaluation/private_runtime/p2_1")

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
        "issue_date": ["발급일자", "발급일", "발행일자"],
    },
    "SME_CONFIRMATION_CERTIFICATE": {
        "company_name": ["기업명", "회사명", "상호"],
        "representative_name": ["대표자", "대표자명"],
        "business_registration_number": ["사업자등록번호", "등록번호"],
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


def build_result(document):
    from app.document_intelligence.ocr.models import (
        BoundingBox,
        OCRDocumentResult,
        OCRLine,
        OCRPage,
    )

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


def main() -> int:
    observations = json.loads(
        (RUNTIME / "observations_private.json").read_text(encoding="utf-8")
    )
    matrix = json.loads(
        (RUNTIME / "observation_matrix_private.json").read_text(encoding="utf-8")
    )
    classifier = DocumentClassifier()
    registry = ExtractorRegistry()

    unresolved = [
        row
        for row in matrix["rows"]
        if row["diagnosis"]
        in {"EXTRACTION_FAILURE", "STRUCTURAL_INTERPRETATION_FAILURE"}
    ]
    by_document = {}
    for row in unresolved:
        by_document.setdefault(row["sample_id"], []).append(row)

    report = []
    for document in observations["documents"]:
        sample_id = document["sample_id"]
        targets = by_document.get(sample_id, [])
        if not targets:
            continue
        result = build_result(document)
        predicted = classifier.classify(result.assembled_text).predicted_type.value
        produced = {
            item.field_name: item for item in registry.extract(predicted, result)
        }
        context = structural.build_context(result)
        observations_rows = _source_observations(result)
        structures = {
            page: build_page_structure(
                tuple(
                    observation.row
                    for observation in observations_rows
                    if observation.row.page_number == page
                )
            )
            for page in {
                observation.row.page_number for observation in observations_rows
            }
        }

        for row in targets:
            field = row["field"]
            labels = ALIASES.get(predicted, {}).get(field, [])
            findings: dict[str, object] = {}
            if context is not None:

                def probe(fn, *args):
                    try:
                        return repr(fn(*args))
                    except Exception as error:  # noqa: BLE001 - the probe records failure
                        return f"raised {type(error).__name__}: {error}"

                for name, fn, args in (
                    (
                        "header_value_candidate",
                        structural.header_value_candidate,
                        (context, labels, field),
                    ),
                    (
                        "section_scoped_values",
                        structural.section_scoped_values,
                        (context, labels),
                    ),
                    (
                        "issuer_block_candidate",
                        structural.issuer_block_candidate,
                        (context, field),
                    ),
                ):
                    findings[name] = probe(fn, *args)
                summary = {
                    "columns": sum(
                        len(item.columns.columns) for item in structures.values()
                    ),
                    "sections": sum(
                        len(item.sections.sections) for item in structures.values()
                    ),
                    "header_value_pairs": sum(
                        len(item.headers.pairs) for item in structures.values()
                    ),
                }
            else:
                summary = {}
            report.append(
                {
                    "sample_id": sample_id,
                    "document_type": predicted,
                    "field": field,
                    "production_value": (
                        produced[field].normalized_value if field in produced else None
                    ),
                    "production_method": (
                        produced[field].extraction_method if field in produced else None
                    ),
                    "ocr_already_correct": row["ocr_text_correct"]
                    in {"YES", "PARTIAL", "NEAR"},
                    "structure_summary": summary,
                    "structural_layer_output": findings,
                }
            )

    payload = {
        "schema_version": "p2-1-structural-layer-probe-private-v1",
        "mode": "EVALUATION_ONLY",
        "production_behavior_modified": False,
        "note": (
            "Candidate reprs may contain private text and stay in this ignored file. "
            "No structural method is activated and none can affect production."
        ),
        "probes": report,
    }
    (RUNTIME / "structural_probe_private.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    resolved = [
        item
        for item in report
        if item["structural_layer_output"].get("header_value_candidate")
        not in (None, "None")
    ]
    payload["fields_resolved_by_structural_layer"] = len(resolved)
    (RUNTIME / "structural_probe_private.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"\nfields where the structural layer produced a candidate: {len(resolved)} of {len(report)}"
    )
    for item in report:
        print(
            f"{item['sample_id']} {item['field']:28s} ocr_ok={item['ocr_already_correct']!s:5s} "
            f"prod={item['production_value']!r} struct={item['structure_summary']}"
        )
        for key, value in item["structural_layer_output"].items():
            print(f"      {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
