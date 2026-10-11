"""Makes the demo's tampered PDF: a copy of a fictional digital 납세증명서 that carries an extra, invisible
date and number in its text layer (render mode 3). Usage: make_tampered_pdf.py <test_variants dir> <output.pdf>"""
import sys
from pathlib import Path

import fitz

src = Path(sys.argv[1]) / "business/B01_all_valid/digital/B01-3_납세증명서.pdf"
with fitz.open(src) as doc:
    doc[0].insert_text((60, 60), "유효기간 2099-12-31 사업자등록번호 999-88-77777", fontname="korea", fontsize=11, render_mode=3)
    doc.save(sys.argv[2])
print(sys.argv[2])
