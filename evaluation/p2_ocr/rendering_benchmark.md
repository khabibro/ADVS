# Rendering Benchmark

## Current path

The production provider uses a configured PDF target of 288 DPI, represented by
a scale of 4 px per PDF point, clamped to 1.5–6.0. A page is rendered at that
scale unless it exceeds either the configured maximum dimension or maximum
pixel budget. For embedded raster pages, the provider estimates source scale
from image dimensions and placement and avoids rendering below source detail.
Image inputs retain source pixel dimensions; only required format/EXIF
normalization is applied.

## Baseline observations

All seven originals are single page. The frozen P1 manifest reports zero
embedded text for the PDFs. Source raster dimensions include 400×566 and
595×842 images, while other image pages are larger. A fresh run through the
current production Paddle adapter reproduced page and line text on all 7/7
samples. This demonstrates repeatability, not that the rendering preserved all
visible content.

| Configuration | Documents/pages | OCR text match | Detection/recognition quality | Latency |
|---|---:|---:|---|---|
| Current source-aware 288 DPI setting | 7/7 | Exact page/line text match vs P1 cache: 7/7 | Not scored; observation gold is absent | Median 12.716 s/page; max 39.331 s/page |
| 200 DPI | 3 PDFs/pages | Exact page/line text match: 0/3 | Not scored; 257 OCR lines total, versus 289 at 288 DPI | 25.513 s, 32.515 s, 10.132 s |
| 288 DPI | 3 PDFs/pages | Exact page/line text match: 3/3 | Not scored; 289 OCR lines total | 14.404 s, 38.431 s, 11.781 s |
| 300 DPI | 3 PDFs/pages | Exact page/line text match: 1/3 | Not scored; 305 OCR lines total; two documents changed text and gained lines | 14.512 s, 41.446 s, 15.068 s |
| Native/source resolution | not run separately | not measured | not measured | not measured |

## Interpretation

The fresh 288-DPI results reproduce the P1 cache. At 200 DPI, all three PDFs
change OCR text and line counts fall on two; at 300 DPI, two PDFs change text
and line counts rise. Increased line count is not evidence of improved
detection: the new boxes could be fragmentation or boilerplate. Keep the
source-aware 288-DPI baseline until rendered pixel dimensions and reviewed
label/value regions can score these alternatives. Source-native image
documents need preprocessing ablation separately from PDF rasterization.
