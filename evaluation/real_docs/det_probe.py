"""Probe PaddleOCR detection settings on a crop of a document page (no content stored in the repo).

    python det_probe.py --pdf X.pdf --crop x0,y0,x1,y1 (fractions) --out private.json
"""
import argparse, json, os, sys
from pathlib import Path

import fitz
import numpy as np

REPO = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--pdf", required=True); ap.add_argument("--crop", required=True); ap.add_argument("--out", required=True); ap.add_argument("--dpi", type=int, default=288)
a = ap.parse_args()
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(REPO / "apps/api/storage/paddleocr-cache"))
from paddleocr import PaddleOCR

d = fitz.open(a.pdf); pm = d[0].get_pixmap(dpi=a.dpi)
img = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
x0, y0, x1, y1 = [float(v) for v in a.crop.split(",")]
img = np.ascontiguousarray(img[int(y0 * pm.height):int(y1 * pm.height), int(x0 * pm.width):int(x1 * pm.width)])
cache = REPO / "apps/api/storage/paddleocr-cache/official_models"
res = {}
for name, kw in {"default": {}, "unclip1.0": {"text_det_unclip_ratio": 1.0}, "unclip1.2": {"text_det_unclip_ratio": 1.2},
                 "thresh0.2": {"text_det_thresh": 0.2}, "box0.7": {"text_det_box_thresh": 0.7}, "unclip1.0+limit1280": {"text_det_unclip_ratio": 1.0, "text_det_limit_side_len": 1280, "text_det_limit_type": "max"}}.items():
    ocr = PaddleOCR(lang="korean", device="cpu", text_recognition_model_name="korean_PP-OCRv5_mobile_rec", text_recognition_model_dir=str(cache / "korean_PP-OCRv5_mobile_rec"),
                    text_detection_model_name="PP-OCRv5_mobile_det", text_detection_model_dir=str(cache / "PP-OCRv5_mobile_det"),
                    use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, **kw)
    out = ocr.predict(img)
    r = out[0]
    res[name] = [{"text": t, "score": round(float(s), 3), "box": [int(v) for v in b]} for t, s, b in zip(r["rec_texts"], r["rec_scores"], r["rec_boxes"])]
    print(name, len(res[name]), [x["text"] for x in res[name]][:12], flush=True)
json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
