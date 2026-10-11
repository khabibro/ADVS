"""Phase G / G-1 gate, pipeline level: manipulated PDFs through the real API (real OCR for the pages
that are no longer trusted). One document of a consistent digital submission (B01, four documents) is
replaced by a copy that carries a hidden date and number; the submission must never be 제출 가능.

  ADVS_API_URL=http://localhost:8000/api/v1 python evaluation/phase_g/scripts/pdf_manipulation_pipeline.py <synthetic dir>
Needs a running API (scripts/demo start). Only fictional files; the projects are deleted afterwards.
"""
import json
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

import fitz
import httpx

API = os.environ.get("ADVS_API_URL", "http://localhost:8000/api/v1")
HIDDEN = "유효기간 2099-12-31 사업자등록번호 999-88-77777"
MODES = {
    "hidden_mode3": lambda p: p.insert_text((60, 60), HIDDEN, fontname="korea", fontsize=11, render_mode=3),
    "white_on_white": lambda p: p.insert_text((60, 90), HIDDEN, fontname="korea", fontsize=11, color=(1, 1, 1)),
    "tiny": lambda p: p.insert_text((60, 120), HIDDEN, fontname="korea", fontsize=0.5),
}


def main() -> None:
    synth = Path(sys.argv[1])
    manifest = json.loads((synth / "test_variants/manifest.json").read_text(encoding="utf-8"))
    entry = next(s for s in manifest["business_sets"] if s["set_id"] == "B01")
    files = [synth / "test_variants" / rel for rel in entry["files"]["digital"]]
    http = httpx.Client(base_url=API, timeout=600)
    workflow = next(w["id"] for w in http.get("/workflows").json() if w["name"] == "기업 제출서류 점검")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        cases = [("control", None, None)] + [(mode, i, fn) for mode, fn in MODES.items() for i in range(len(files))]
        for mode, index, apply in cases:
            project = http.post("/projects", json={"name": f"[G1] {mode} {index}", "workflow_id": workflow}).json()
            for i, path in enumerate(files):
                data = path.read_bytes()
                if apply is not None and i == index:
                    with fitz.open(path) as doc:
                        apply(doc[0])
                        target = Path(tmp) / "m.pdf"
                        doc.save(target)
                    data = target.read_bytes()
                name = unicodedata.normalize("NFC", path.name)
                doc = http.post(f"/projects/{project['id']}/documents", files={"file": (name, data, "application/pdf")}).json()
                http.post(f"/documents/{doc['id']}/process").raise_for_status()
            result = http.post(f"/projects/{project['id']}/verify", json={"evaluation_date": "2026-10-05"}).json()
            codes = sorted({i["code"] for i in result["issues"]})
            rows.append((mode, index, result["status"], codes))
            http.delete(f"/projects/{project['id']}")
    print("| manipulation | manipulated document | submission status | issue codes |")
    print("|---|---|---|---|")
    for mode, index, status, codes in rows:
        print(f"| {mode} | {'-' if index is None else files[index].name} | {status} | {', '.join(codes)} |")
    manipulated = [r for r in rows if r[0] != "control"]
    ready = [r for r in manipulated if r[2] == "READY"]
    flagged = [r for r in manipulated if "TEXT_LAYER_MISMATCH" in r[3]]
    print(f"\ncontrol: {rows[0][2]}; manipulated submissions: {len(manipulated)}; reached 제출 가능 (READY): {len(ready)}; "
          f"with TEXT_LAYER_MISMATCH: {len(flagged)}; 95% upper bound for READY: {3 / len(manipulated):.1%}")
    sys.exit(1 if ready or rows[0][2] != "READY" else 0)


if __name__ == "__main__":
    main()
