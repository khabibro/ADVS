"""Method D, step 1: the field crops the current system would hand to a person or flags, cut from
the same raster the production OCR read (PDF page at the cached render scale, EXIF-corrected image),
with the production second-pass preprocessing (margin, autocontrast, x1.6, white border).

  PYTHONPATH=<app checkout>/apps/api python analysis/plan_crops.py --corpus dev --synth ... --harness ... \
      --a-cache ... --fields results/fields_dev.json --out results/crops_dev
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HIGH_RISK, guard, sha256  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--synth", type=Path, required=True)
    ap.add_argument("--harness", type=Path, required=True)
    ap.add_argument("--a-cache", type=Path, required=True)
    ap.add_argument("--fields", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    guard(args.corpus)
    sys.path.insert(0, str(args.harness))
    import fitz
    from harness_core import page_from_dict  # type: ignore[import-not-found]
    from PIL import Image, ImageOps

    from app.core.domain import DocumentType
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.ocr.models import OCRDocumentResult
    from app.document_intelligence.ocr.text_assembly import assemble_document_text, assemble_page_text
    from app.document_intelligence.preprocessing.processor import ImagePreprocessor, PdfProcessor
    from app.services.processing import _value_evidence

    rows = json.loads(args.fields.read_text(encoding="utf-8"))["rows"]
    root = args.synth / {"dev": "test_variants"}.get(args.corpus, args.corpus)
    args.out.mkdir(parents=True, exist_ok=True)
    wanted: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r["state"] == "KNOWN_VALUE" and r["a_value"] is not None and (r["field"] in HIGH_RISK or r["a_decision"] == "NEEDS_HUMAN"):
            wanted.setdefault(r["file"], {})[r["field"]] = r
    registry = ExtractorRegistry()
    crops: list[dict] = []
    for rel, fields in sorted(wanted.items()):
        path = root / rel
        sample = next(iter(fields.values()))
        if sample["input"] == "digital":
            pages = PdfProcessor().extract_text(path).pages
        else:
            cached = json.loads((args.a_cache / f"{sha256(path)}.json").read_text(encoding="utf-8"))
            pages = [page_from_dict(p) for p in cached["pages"]]
            for p in pages:
                p.metadata.setdefault("source", "ocr")
                if p.lines:
                    p.text = assemble_page_text(p.lines)
        source = OCRDocumentResult("replay", pages, assemble_document_text(pages))
        values = {v.field_name: v for v in registry.extract(DocumentType(sample["doc_type"]), source)}
        # rasters per page, same as the production reader
        rasters: dict[int, tuple[Image.Image, float]] = {}
        if path.suffix.lower() == ".pdf":
            with fitz.open(path) as doc:
                for idx, page in enumerate(doc, start=1):
                    meta = pages[idx - 1].metadata if idx - 1 < len(pages) else {}
                    scale = float((meta.get("transform") or {}).get("render_scale", 4.0))
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
                    point_scale = scale if meta.get("coordinate_space") == "pdf_point" else 1.0
                    rasters[idx] = (img, point_scale)
        else:
            with Image.open(path) as im:
                prepared = ImageOps.exif_transpose(im).convert("L")
            rasters[1] = (prepared, 1.0)
        for name, row in fields.items():
            value = values.get(name)
            if value is None or not value.evidence or value.normalized_value != row["a_value"]:
                continue
            ev = _value_evidence(value)  # the box of the value itself, as the production second pass does
            if ev is None or ev.bounding_box is None or ev.page_number not in rasters:
                continue
            img, k = rasters[ev.page_number]
            b = ev.bounding_box
            x, y, w, h = b.x * k, b.y * k, b.width * k, b.height * k
            mx, my = max(6.0, h * 0.4), max(4.0, h * 0.3)
            box = (max(0, int(x - mx)), max(0, int(y - my)), min(img.width, int(x + w + mx)), min(img.height, int(y + h + my)))
            if box[2] - box[0] < 4 or box[3] - box[1] < 4:
                continue
            crop = ImageOps.autocontrast(img.crop(box), cutoff=2)
            crop = crop.resize((int(crop.width * 1.6), int(crop.height * 1.6)), Image.Resampling.LANCZOS)
            crop = ImageOps.expand(crop, border=12, fill=255)
            cid = f"{len(crops):05d}"
            crop.save(args.out / f"{cid}.png")
            crops.append({"id": cid, "file": rel, "field": name, "input": row["input"], "doc_type": row["doc_type"],
                          "a_value": row["a_value"], "expected": row["expected"], "a_decision": row["a_decision"]})
    (args.out / "crops.json").write_text(json.dumps(crops, ensure_ascii=False), encoding="utf-8")
    print("crops", len(crops))


if __name__ == "__main__":
    main()
