"""D3-11 on development data: confidence thresholds suggested by split-conformal risk control.

Records = OCR-read (scanned + images) field values of scored runs with an evaluated outcome
(correct = effective_outcome / outcome CORRECT). Suggestions only; production keeps its floors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import conformal  # noqa: E402

D = Path(__file__).resolve().parents[1] / "phase_d3"


def records(label: str) -> list[dict]:
    out = []
    for corpus in ("dev", "holdout", "holdout2"):
        d = json.loads((D / f"{label}_{corpus}.json").read_text(encoding="utf-8"))
        for sid, sset in d["scored"]["sets"].items():
            for version in ("scanned", "images"):
                vres = sset["versions"].get(version)
                if not vres:
                    continue
                raw = {f["file"]: f for f in d["raw"]["sets"][sid]["versions"][version]["files"]}
                for f in vres["files"]:
                    for name, fs in f["fields"].items():
                        if fs.get("category") != "EVALUATED" or fs.get("outcome") not in ("CORRECT", "WRONG"):
                            continue
                        info = raw[f["file"]]["fields"].get(name, {})
                        out.append({"field_name": name, "confidence": info.get("confidence"), "correct": fs["outcome"] == "CORRECT"})
    return out


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "C4"
    recs = records(label)
    floors = {"company_name": 0.90, "business_registration_number": 0.90}
    parts = [f"# D3-11 conformal threshold suggestions on development data ({label}; {len(recs)} OCR field values)\n",
             "Calibration data = development sets only; synthetic, so for comparison until real reviewed data exist. "
             "The hand-picked floors stay in production.\n"]
    for alpha in (0.05, 0.01):
        parts.append(conformal.render(conformal.suggest(recs, alpha), floors, alpha))
    (D / f"conformal_{label}.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts)[:3000])
