# Ablation Results

| Candidate | Documents | Label/value observation quality | Field quality | False READY | Latency | Verdict |
|---|---:|---|---|---|---|---|
| Current OCR + current source-aware rendering/preparation | 7 | Not independently scored; text/line output reproduced on 7/7 | Full production-path rerun pending | Baseline 0/7 historically | Fresh page median 12.716 s; max 39.331 s | Retain as baseline |
| Current OCR + 200 DPI | not run | not measured | not measured | not measured | not measured | Not selected |
| Current OCR + 300 DPI | not run | not measured | not measured | not measured | not measured | Not selected |
| Current OCR + grayscale/contrast/upscale | not run | not measured | not measured | not measured | not measured | Not selected |
| Server detector + current Korean recognizer | not run | not measured | not measured | not measured | not measured | Deferred pending box-level evidence |
| Alternative Korean recognizer | none justified by official current docs | not measured | not measured | not measured | not measured | No candidate selected |

Candidate selection requires equal inputs/gold/evaluator and must include wrong
non-null, safety, and performance. No change is warranted from output volume or
confidence alone.
