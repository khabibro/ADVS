"""Method B (page parse) for one corpus. Runs in the research venv (PaddleOCR-VL pipeline + llama-server).

Writes one JSON per file, keyed by the file's sha256, in the same shape as the production OCR cache
({"pages": [...]}) so the evaluation harness can replay it. The adapter (analysis/adapter.py) turns
the block list into OCR lines; here only the raw blocks are stored.

  .venv/bin/python scripts/vlm_pages.py --manifest <corpus>/manifest.json --root <corpus> --out results/pages_<corpus>
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--manifest", type=Path, required=True)
ap.add_argument("--root", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--limit", type=int, default=0)
args = ap.parse_args()
if "holdout3" in str(args.root) and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
    raise SystemExit("hold-out 3 is for the single final run only (ADVS_FINAL_JUDGEMENT=1)")

from paddleocr import PaddleOCRVL  # noqa: E402

cfg = json.loads((Path(__file__).resolve().parents[1] / "config_frozen.json").read_text())["pipeline"]
pipe = PaddleOCRVL(pipeline_version=cfg["pipeline_version"], device=cfg["device"], vl_rec_backend=cfg["vl_rec_backend"],
                   vl_rec_server_url=cfg["vl_rec_server_url"], vl_rec_api_model_name=cfg["vl_rec_api_model_name"])
args.out.mkdir(parents=True, exist_ok=True)
manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
files = [f["file"] for f in manifest["files"] if f["file"].lower().rsplit(".", 1)[-1] in {"pdf", "jpg", "jpeg", "png", "webp"} and f.get("expected_fields")]
if args.limit:
    files = files[: args.limit]
log = args.out / "_timing.jsonl"
done = 0
for rel in files:
    path = args.root / rel
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    target = args.out / f"{digest}.json"
    if target.exists():
        continue
    t0 = time.perf_counter()
    try:
        results = list(pipe.predict(str(path)))
        pages = []
        for index, res in enumerate(results, start=1):
            body = res.json["res"] if "res" in res.json else res.json
            pages.append({
                "page_number": index,
                "width": body.get("width"), "height": body.get("height"),
                "blocks": [{k: b.get(k) for k in ("block_label", "block_content", "block_bbox")} for b in body.get("parsing_res_list", [])],
            })
        payload = {"file": rel, "pages": pages, "seconds": round(time.perf_counter() - t0, 2)}
    except Exception as exc:  # recorded, never hidden
        payload = {"file": rel, "error": f"{type(exc).__name__}: {exc}"[:300], "seconds": round(time.perf_counter() - t0, 2)}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with log.open("a") as handle:
        handle.write(json.dumps({"file": rel, "seconds": payload["seconds"], "pages": len(payload.get("pages", []))}, ensure_ascii=False) + "\n")
    done += 1
    if done % 20 == 0:
        print(done, "/", len(files), flush=True)
print("finished", done, "new files of", len(files))
