# Isolated OCR-vs-VLM experiment (PaddleOCR-VL 1.6)

Nothing here is part of the product. No file under `apps/` imports this folder, no lockfile of the app lists
PaddleOCR-VL, and the environment below lives in `research/vlm_poc/.venv` (git-ignored). The analysis scripts
*read* the app's code (extractors, dataclasses) through `PYTHONPATH`, never the other way round.
Fictional documents only. The seven archived real documents are not used and never leave the machine.

## What was measured

| Method | What it is |
|---|---|
| A | the production reading: embedded PDF text for digital files, PaddleOCR (PP-OCRv5 Korean, paddleocr 3.2.0) for scans and photos |
| B | PaddleOCR-VL parses each page; its blocks are flattened to text lines by `analysis/adapter.py`; the same production extractors map text to fields |
| D | the VLM re-reads only field crops (the system's review fields and the high-risk fields: business number, validity and issue dates, GPA, student number), using the production second-pass crop geometry; it confirms or disputes A's value, it never supplies a new one |

The results and the recommendation are in `COMPARISON.md`.

## Environment (as run)

- Hardware: MacBook Pro, Apple M3 Pro (11 cores: 5 performance + 6 efficiency), 18 GB unified memory, macOS 26.6.2. No NVIDIA GPU.
- Python 3.12.14 venv with `paddlepaddle 3.3.1` (CPU), `paddleocr 3.7.0` (`[doc-parser]`), `paddlex 3.7.2`, `transformers 5.19.0`, `pymupdf`, `pillow`, `httpx`, `gguf`.
- Model: `PaddlePaddle/PaddleOCR-VL-1.6` (Apache-2.0, 0.9 B parameters, revision `c5630abae1d940eafe0697512a0325494b02ab42`, 2026-08-08).
  The Korean language is not named on the 1.6 model card (it lists English, Chinese, multilingual; the 1.0 card names Korean among 109 languages), so Korean support was checked by running it, see `COMPARISON.md`.
- Inference route used for the full run: the official GGUF build `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` (revision `511b09642bb324401f15f97cc23bc67e8f0a291d`, BF16 weights, no quantisation; sha256 in `models/SHA256SUMS`) served by `llama.cpp` 0.6.0 (build 11429, Metal), driven through the official `PaddleOCRVL(vl_rec_backend="llama-cpp-server")` pipeline (layout model `PP-DocLayoutV3` on CPU).
  The native Paddle CPU route (the card's primary route) reproduced the same text on the page it was compared on but needs about 114 s per page on this machine, which made a full run impractical. See `COMPARISON.md` for the cross-check.
- Official docs say macOS users should use Docker for the Paddle route; that was not needed for the llama.cpp route.

## Reproduce

```bash
cd research/vlm_poc
python3.12 -m venv .venv && .venv/bin/pip install "paddlepaddle>=3.2.1" "paddleocr[doc-parser]>=3.6.0" "transformers>=5.0.0" pillow pymupdf numpy huggingface_hub httpx gguf
brew install llama.cpp
# download the two GGUF files + chat_template.jinja at the revision above into models/
llama-server -m models/PaddleOCR-VL-1.6-GGUF.gguf --mmproj models/PaddleOCR-VL-1.6-GGUF-mmproj.gguf \
  --jinja --chat-template-file models/chat_template.jinja --port 8111 -ngl 99 -c 8192 --temp 0 &
scripts/run_dev_pages.sh                      # B on the development data
# then, with the app interpreter: analysis/compare_fields.py, analysis/plan_crops.py, scripts/vlm_crops.py, analysis/report.py
```

`config_frozen.json` records every setting; its hash is written to `results/frozen.json` before the single hold-out 3 run.
