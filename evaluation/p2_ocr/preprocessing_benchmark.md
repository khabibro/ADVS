# Preprocessing Benchmark

No new preprocessing was applied in P2. The current provider performs required
format conversion and EXIF orientation normalization when an image must be
prepared. It does not currently apply a general contrast, sharpening,
thresholding, denoising, or upscale pass.

| Candidate | Evidence for testing | Quality result | Wrong non-null | Latency | Decision |
|---|---|---|---|---|---|
| Current preparation | Baseline | Repeatable output on 7/7 pages; correctness unscored | Not re-evaluated yet | Baseline median 12.716 s/page | Retain as baseline |
| Grayscale/contrast | No measured failure category yet | Not run | Not measured | Not measured | Defer |
| Sharpening/thresholding | No measured failure category yet | Not run | Not measured | Not measured | Defer |
| Upscale for small source | Two source images are low pixel dimensions | Not run | Not measured | Not measured | Candidate after annotation; avoid choosing by recall alone |
| Denoise/orientation correction | No independent annotation demonstrates noise/rotation as a dominant cause | Not run | Not measured | Not measured | Defer |

No preprocessing method is selected. A controlled comparison needs the same
pages, reviewed visible-text regions, equal field gold, and page-level latency.
