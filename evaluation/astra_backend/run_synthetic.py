"""Score every emitted field against frozen generated gold (no OCR involved)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("dev", "held_out", "all"), default="all")
    args = parser.parse_args()
    root = args.code_root.resolve()
    sys.path.insert(0, str(root / "apps/api"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/api/scripts"))
    from app.core.domain import DocumentType
    from app.document_intelligence.classification.classifier import DocumentClassifier
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.validation.engine import ValidationEngine
    from eval_lib.safety import score_run

    manifest = json.loads((root / "evaluation/manifest.json").read_text())
    classifier, registry, validator = (
        DocumentClassifier(),
        ExtractorRegistry(),
        ValidationEngine(),
    )
    groups = {}
    for entry in manifest["entries"]:
        if args.split != "all" and entry["split"] != args.split:
            continue
        annotation = json.loads((root / entry["gold_label_path"]).read_text())
        if not annotation.get("verified") or not entry.get("gold_text_path"):
            continue
        group = annotation.get("source_class", "SYNTHETIC_REALISTIC")
        gold, records = groups.setdefault(
            group,
            (
                {
                    "dataset_version": "generated-manifest-v1",
                    "gold_version": "existing-generated-gold-v1.1",
                    "samples": {},
                },
                [],
            ),
        )
        sid = entry["sample_id"]
        gold["samples"][sid] = {
            "document_type": annotation["document_type"],
            "fields": {
                name: {
                    "state": "PRESENT" if data["value"] is not None else "ABSENT",
                    "value": data["value"],
                    "required": data.get("required", True),
                }
                for name, data in annotation["fields"].items()
            },
        }
        text = (root / entry["gold_text_path"]).read_text()
        start = time.perf_counter()
        classification = classifier.classify(text)
        document_type = DocumentType(classification.predicted_type)
        extracted = registry.extract(document_type, text)
        issues = validator.validate_document(
            None, document_type, extracted, None, None, False, None
        )
        fields = {
            f.field_name: {
                "value": f.normalized_value,
                "evidence_count": len(f.evidence or []),
                "needs_review": f.normalized_value is None,
                "extraction_method": f.extraction_method,
            }
            for f in extracted
        }
        records.append(
            {
                "sample_id": sid,
                "processing_status": "COMPLETED",
                "predicted_document_type": str(document_type),
                "overall_status": str(validator.overall_status(issues)),
                "fields": fields,
                "process_ms": (time.perf_counter() - start) * 1000,
            }
        )
    digest = hashlib.sha256()
    for path in sorted((root / "apps/api/app").rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    outputs = {}
    for group, (gold, records) in groups.items():
        fingerprint = hashlib.sha256(
            json.dumps(gold, sort_keys=True).encode()
        ).hexdigest()
        outputs[group] = score_run(
            {
                "samples": records,
                "metadata": {
                    "mode": "gold_text_no_OCR",
                    "backend_tree_sha256": digest.hexdigest(),
                    "gold_sha256": fingerprint,
                },
            },
            gold,
        )
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2))
    print(json.dumps({k: v["metrics"] for k, v in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
