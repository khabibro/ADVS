"""Method D, step 2: read each crop with PaddleOCR-VL (prompt "OCR:") through the llama.cpp server.
Runs in the research venv. Only the HTTP API of the local server is used.

  .venv/bin/python scripts/vlm_crops.py --crops results/crops_dev --out results/crop_readings_dev.json
"""
import argparse, base64, json, os, time
from pathlib import Path

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--crops", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
args = ap.parse_args()
cfg = json.loads((Path(__file__).resolve().parents[1] / "config_frozen.json").read_text())
prompt = cfg["method_D"]["prompt"]
crops = json.loads((args.crops / "crops.json").read_text(encoding="utf-8"))
done = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
client = httpx.Client(base_url="http://127.0.0.1:8111", timeout=120)
for index, crop in enumerate(crops):
    if crop["id"] in done:
        continue
    image = base64.b64encode((args.crops / f"{crop['id']}.png").read_bytes()).decode()
    body = {"model": "PaddleOCR-VL-1.6-GGUF", "temperature": 0, "max_tokens": cfg["method_D"]["max_new_tokens"],
            "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}, {"type": "text", "text": prompt}]}]}
    t0 = time.perf_counter()
    try:
        text = client.post("/v1/chat/completions", json=body).json()["choices"][0]["message"]["content"]
        error = None
    except Exception as exc:
        text, error = None, f"{type(exc).__name__}: {exc}"[:200]
    done[crop["id"]] = {"text": text, "seconds": round(time.perf_counter() - t0, 2), "error": error}
    if index % 25 == 0:
        args.out.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
args.out.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
print("read", len(done), "crops")
