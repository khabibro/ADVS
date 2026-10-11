"""Phase G / G-1 gate: manipulated copies of every development digital PDF.

For each digital PDF of test_variants, hold-out 1 and hold-out 2 four manipulated copies are made, each
adding a date and a number that are NOT on the visible page:
  hidden_mode3   invisible text (render mode 3)         white_on_white   white text on the white page
  tiny           0.5 pt text                             off_page         text placed outside the page
The check: the added tokens never appear in the text the pipeline reads, and the page is marked
untrusted (so it is read by OCR and the document gets TEXT_LAYER_MISMATCH when the page does not show them).
Hold-out 3 is not touched.

  cd apps/api && PYTHONPATH=. python ../../evaluation/phase_g/scripts/pdf_manipulation_suite.py <synthetic dir>
"""
import math
import sys
import tempfile
from pathlib import Path

import fitz

from app.document_intelligence.preprocessing.processor import PdfProcessor

HIDDEN = "유효기간 2099-12-31 사업자등록번호 999-88-77777"
MODES = {
    "hidden_mode3": lambda page: page.insert_text((60, 60), HIDDEN, fontname="korea", fontsize=11, render_mode=3),
    "white_on_white": lambda page: page.insert_text((60, 90), HIDDEN, fontname="korea", fontsize=11, color=(1, 1, 1)),
    "tiny": lambda page: page.insert_text((60, 120), HIDDEN, fontname="korea", fontsize=0.5),
    "off_page": lambda page: page.insert_text((page.rect.width + 200, 150), HIDDEN, fontname="korea", fontsize=11),
}


def main() -> None:
    synth = Path(sys.argv[1])
    files = []
    for corpus in ("test_variants", "holdout", "holdout2"):
        files += [p for p in (synth / corpus).rglob("*.pdf") if "/digital/" in str(p) or "/formats/F01" in str(p)]
    results = {mode: {"made": 0, "cases": 0, "leaked": 0, "trusted": 0} for mode in MODES}
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(files):
            for mode, apply in MODES.items():
                try:
                    with fitz.open(path) as doc:
                        apply(doc[0])
                        target = Path(tmp) / "m.pdf"
                        doc.save(target)
                except Exception:
                    continue
                r = results[mode]
                r["made"] += 1
                with fitz.open(target) as check:  # what a plain text extractor (the old behaviour) would read
                    naive = check[0].get_text()
                if "2099-12-31" not in naive:
                    continue  # the manipulation left nothing a naive reader could pick up
                pages = PdfProcessor().extract_text(target).pages
                text = "\n".join(p.text for p in pages)
                r["cases"] += 1
                r["leaked"] += ("2099-12-31" in text) or ("999-88-77777" in text)
                r["trusted"] += bool(pages[0].metadata["text_layer"]["trusted"])
    print("| manipulation | copies made | effective against a plain extractor |  hidden tokens found in the text the pipeline reads | page still trusted | 95% upper bound for a miss (rule of three) |")
    print("|---|---|---|---|---|---|")
    bad = 0
    for mode, r in results.items():
        bound = f"{3 / r['cases']:.2%}" if r["cases"] and r["leaked"] + r["trusted"] == 0 else "—"
        print(f"| {mode} | {r['made']} | {r['cases']} | {r['leaked']} | {r['trusted']} | {bound} |")
        bad += r["leaked"] + r["trusted"]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
