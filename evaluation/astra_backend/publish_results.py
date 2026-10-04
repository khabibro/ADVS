"""Emit sanitized evaluation artifacts from local private measurements.

This is an explicit allowlist exporter: document text, values, source paths,
student/company identifiers, and image data never enter the published files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api/scripts"))
from eval_lib.safety import SCORER_VERSION, score_run


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    private = args.private_dir
    output = Path(__file__).resolve().parent
    inventory = json.loads((private / "inventory.private.json").read_text())
    gold = json.loads((private / "gold-v1.2.private.json").read_text())
    old_inventory = json.loads(
        (ROOT / "evaluation/backend_round2/dataset_summary.json").read_text()
    )
    old_hashes = {x["file"]["sha256_12"] for x in old_inventory["samples"]}
    safe_inventory = []
    for item in inventory:
        sid = item["sample_id"]
        annotation = gold["samples"][sid]
        safe = {
            k: item.get(k)
            for k in (
                "sample_id",
                "extension",
                "mime",
                "size",
                "page_count",
                "source_kind",
                "width",
                "height",
                "dpi",
            )
        }
        safe.update(
            document_type=annotation["document_type"],
            layout_family=annotation["layout_family"],
            table_presence=sid in {"ASTRA-R01", "ASTRA-R03", "ASTRA-R04"},
            seal_presence=True,
            rotation="upright",
            skew="not quantitatively measured",
            quality="low native resolution"
            if sid in {"ASTRA-R02", "ASTRA-R03", "ASTRA-R06"}
            else "legible scan; stamp interference",
            ground_truth_exists=True,
            safe_for_local_testing=True,
            cloud_authorized=False,
            matched_prior_round2_hash=item["sha256"][:12] in old_hashes,
        )
        if item["source_kind"] == "scanned_pdf":
            safe["page_dimensions_points"] = [
                {k: p[k] for k in ("width_points", "height_points")}
                for p in item["pages"]
            ]
        safe_inventory.append(safe)
    dump(
        output / "inventory.json",
        {
            "dataset_version": gold["dataset_version"],
            "total_files": len(inventory),
            "unique_byte_files": len({p["sha256"] for p in inventory}),
            "probable_visual_duplicates": 0,
            "visual_duplicate_method": "All seven rendered originals visually inspected; distinct identities/layouts, no re-encoded copy found.",
            "prior_round2_matches": sum(
                p["matched_prior_round2_hash"] for p in safe_inventory
            ),
            "independent_new_coverage": 0,
            "holdout": "NO RELIABLE HOLDOUT POSSIBLE",
            "types": dict(Counter(p["document_type"] for p in safe_inventory)),
            "layout_families": dict(
                Counter(p["layout_family"] for p in safe_inventory)
            ),
            "samples": safe_inventory,
        },
    )
    dump(
        output / "gold_manifest.json",
        {
            "gold_version": gold["gold_version"],
            "dataset_version": gold["dataset_version"],
            "annotation_date": gold["annotation_date"],
            "annotation_source": gold["annotation_source"],
            "private_gold_sha256": hashlib.sha256(
                (private / "gold-v1.2.private.json").read_bytes()
            ).hexdigest(),
            "correction_history": gold["correction_history"],
            "sample_fields": {
                sid: {
                    name: {
                        "state": field["state"],
                        "required": field.get("required", False),
                    }
                    for name, field in sample["fields"].items()
                }
                for sid, sample in gold["samples"].items()
            },
            "required_profile_note": "Evaluation study profile, explicitly frozen; compare readiness policy separately from old seed configuration.",
            "sensitive_values": "Only in private artifact directory; never exported.",
        },
    )
    scores = {}
    for phase in ("before", "after"):
        path = private / f"{phase}.private.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text())
        # Preserve raw historical run; append measurement corrections to derived metadata.
        run["metadata"]["scored_gold_version"] = gold["gold_version"]
        run["metadata"]["scorer_sha256"] = hashlib.sha256(
            (ROOT / "apps/api/scripts/eval_lib/safety.py").read_bytes()
        ).hexdigest()
        run["metadata"]["observed_page_render_dpi"] = sorted(
            {
                p["metadata"]["render_dpi"]
                for d in run["samples"]
                for p in d.get("ocr_pages", [])
                if p.get("metadata", {}).get("render_dpi")
            }
        )
        if phase == "before":
            run["metadata"]["configuration_correction"] = (
                "Initial harness metadata said 250 DPI; actual persisted page metadata and settings show 288 DPI. No pixels or backend outputs changed."
            )
        scores[phase] = score_run(run, gold)
        dump(output / f"realistic_{phase}.json", scores[phase])
    for name in (
        "synthetic_before",
        "synthetic_before_dev",
        "synthetic_before_held",
        "synthetic_after",
        "synthetic_after_dev",
        "synthetic_after_held",
    ):
        source = private / f"{name}.json"
        if source.exists():
            dump(output / f"{name}.json", json.loads(source.read_text()))
    if "before" in scores and "after" in scores:
        dump(
            output / "comparison.json",
            {
                "scorer_version": SCORER_VERSION,
                "gold_version": gold["gold_version"],
                "dataset_version": gold["dataset_version"],
                "metrics": {
                    key: {
                        "before": value,
                        "after": scores["after"]["metrics"][key],
                        "delta": scores["after"]["metrics"][key] - value
                        if value is not None
                        and scores["after"]["metrics"][key] is not None
                        else None,
                    }
                    for key, value in scores["before"]["metrics"].items()
                },
            },
        )
    print(
        json.dumps(
            {
                "exported_phases": list(scores),
                "gold_version": gold["gold_version"],
                "inventory_count": len(safe_inventory),
            }
        )
    )


if __name__ == "__main__":
    main()
