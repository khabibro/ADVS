"""Step 0: what data exists for dev and hold-outs 1-3 (read-only).

    ADVS_FINAL_JUDGEMENT=1 python3 step0_inventory.py     # hold-out 3 is only touched with the switch (logged)
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "evaluation" / "harness"))
import harness_core as hc  # noqa: E402
import inject_errors as ie  # noqa: E402
import inject_errors_d2 as d2  # noqa: E402
import inject_errors_d3 as d3  # noqa: E402

CACHES = {
    "dev": REPO / "evaluation" / "phase_d" / "ocr_cache",
    "holdout": REPO / "evaluation" / "phase_d" / "ocr_cache_holdout",
    "holdout2": REPO / "evaluation" / "phase_d2" / "ocr_cache_holdout2",
    "holdout3": REPO / "evaluation" / "phase_d3" / "ocr_cache_holdout3",
}
RECORDED = {
    "dev": "evaluation/phase_g/results/dev_final/F_dev.json (+ F_inj_dev.md)",
    "holdout": "evaluation/phase_g/results/dev_final/F_holdout.json (+ F_inj_holdout.md)",
    "holdout2": "evaluation/phase_g/results/dev_final/F_holdout2.json (+ F_inj_holdout2.md)",
    "holdout3": "evaluation/phase_g/final/H3_integrated.json, H3_integrated_inj.md (+ H3_main.json)",
}


def main() -> int:
    rows = []
    for corpus, cache in CACHES.items():
        if corpus == "holdout3" and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
            print("skipping holdout3 (switch not set)")
            continue
        root = hc.guard_corpus(corpus)
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        docs = [p for p in cache.glob("*.json")]
        n_pages = n_lines = n_conf = n_err = 0
        confs: list[float] = []
        engines = set()
        for p in docs:
            data = json.loads(p.read_text(encoding="utf-8"))
            if "error" in data:
                n_err += 1
                continue
            for page in data["pages"]:
                n_pages += 1
                md = page.get("metadata", {})
                engines.add((md.get("provider"), md.get("provider_version"), md.get("det_model_name"), md.get("rec_model_name")))
                for line in page["lines"]:
                    n_lines += 1
                    if line.get("confidence") is not None:
                        n_conf += 1
                        confs.append(line["confidence"])
        sp = {d.name: len(list(d.glob("*.json"))) for d in cache.iterdir() if d.is_dir()}
        by_version = {v: sum(len(s["files"].get(v, [])) for s in manifest["business_sets"] + manifest["student_sets"]) for v in ("digital", "scanned", "images")}
        known = sum(1 for e in manifest["files"] for f in (e.get("expected_fields") or {}).values() if f.get("state") == "KNOWN_VALUE")
        absent = sum(1 for e in manifest["files"] for f in (e.get("expected_fields") or {}).values() if f.get("state") == "VERIFIED_ABSENT")
        planner3 = d3.Planner3(manifest, root, cache)
        cases = ie.Planner(manifest, root, cache).plan() + d2.plan_boundary(manifest, root, cache) + planner3.plan()
        q = statistics.quantiles(confs, n=100) if confs else [None] * 99
        rows.append({
            "corpus": corpus, "ocr_cache_documents": len(docs), "ocr_documents_with_error": n_err, "ocr_pages": n_pages, "ocr_lines": n_lines,
            "lines_with_paddleocr_confidence": n_conf, "line_conf_p1": round(q[0], 4), "line_conf_p50": round(q[49], 4), "line_conf_p99": round(q[98], 4),
            "ocr_engine(provider,version,det,rec)": "; ".join(str(e) for e in sorted(engines, key=str)),
            "second_pass_cache_dirs": json.dumps(sp), "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:16],
            "submissions_digital/scanned/images(files)": json.dumps(by_version), "ground_truth_known_value_fields": known, "ground_truth_verified_absent_fields": absent,
            "injection_cases_planned_E1-E15_E18(+E10,E16,E17 at run time)": len(cases),
            "recorded_predictions_and_scores": RECORDED[corpus],
        })
        print(rows[-1])
    with (HERE / "tables").joinpath("step0_data_inventory.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    (HERE / "tables").mkdir(exist_ok=True)
    raise SystemExit(main())
