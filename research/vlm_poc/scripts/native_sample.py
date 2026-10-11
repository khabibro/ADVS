"""GGUF-vs-native cross-check: the same files through the native Paddle CPU route (the model card's primary
route). Writes the same block JSON as vlm_pages.py. Research venv."""
import hashlib, json, sys, time
from pathlib import Path
from paddleocr import PaddleOCRVL

S = Path("/Users/admin/Documents/ADVS/evaluation/datasets/synthetic/test_variants")
sample = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
pipe = PaddleOCRVL(pipeline_version="v1.6", device="cpu")
for rel in sample:
    path = S / rel
    t0 = time.perf_counter()
    pages = []
    for index, res in enumerate(pipe.predict(str(path)), start=1):
        body = res.json["res"] if "res" in res.json else res.json
        pages.append({"page_number": index, "width": body.get("width"), "height": body.get("height"),
                      "blocks": [{k: b.get(k) for k in ("block_label", "block_content", "block_bbox")} for b in body.get("parsing_res_list", [])]})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / f"{digest}.json").write_text(json.dumps({"file": rel, "pages": pages, "seconds": round(time.perf_counter() - t0, 1)}, ensure_ascii=False))
    print(rel, round(time.perf_counter() - t0, 1), flush=True)
