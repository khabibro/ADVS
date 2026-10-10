"""Phase F: does the PDF text-layer path trust hidden text? (read-only probe, no production change)

Builds a scratch PDF whose VISIBLE page is an image saying 유효기간 2025-01-31 (expired) and whose
invisible text layer (render mode 3) says 2027-12-31, then asks the existing PdfProcessor what it
would trust. Needs the API virtualenv:

  cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/phase_f/scripts/text_layer_probe.py
"""

import tempfile
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from app.document_intelligence.preprocessing.processor import PdfProcessor

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"  # macOS; any Korean font works


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        visible = Path(tmp) / "visible.png"
        font = ImageFont.truetype(FONT, 28)
        image = Image.new("RGB", (900, 160), "white")
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "납세증명서  TEST SAMPLE 테스트용 견본", font=font, fill="black")
        draw.text((10, 60), "유효기간 2025-01-31   사업자등록번호 220-81-12341", font=font, fill="black")
        image.save(visible)
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_font(fontname="kr", fontfile=FONT)
        page.insert_image(fitz.Rect(40, 60, 540, 150), filename=str(visible))
        page.insert_text((50, 100), "납세증명서 TEST SAMPLE 테스트용 견본 유효기간 2027-12-31 사업자등록번호 220-81-12341 주식회사 테스트상사",
                         fontname="kr", fontsize=10, render_mode=3)
        target = Path(tmp) / "probe.pdf"
        pdf.save(target)
        result = PdfProcessor().extract_text(target)
    print("visible page says : 유효기간 2025-01-31 (expired)")
    print("page source       :", result.pages[0].metadata["source"])
    print("meaningful text   :", result.has_meaningful_text)
    print("text the pipeline would trust:", result.text)


if __name__ == "__main__":
    main()
