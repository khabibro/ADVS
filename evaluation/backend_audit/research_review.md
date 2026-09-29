# Research review — document intelligence options for ADVS

Research date 2026-09-29. Primary sources preferred throughout (official docs,
official repositories, official pricing pages, arXiv). Anything not verifiable
from a primary source is marked **UNVERIFIED**. Vendor marketing claims are
labelled as such and are not used as evidence for any decision.

Constraint set: Korean administrative certificates, on-premises, CPU-only,
must produce field-level evidence (page, bbox, source text, confidence), must
be deterministic where it matters, and must not be able to fabricate a value.

---

## 1. Local OCR engines

### PaddleOCR — **ADOPTED (already in use; configuration corrected)**

| Property | Finding | Source |
|---|---|---|
| Current version | v3.7.0 (2026-06-11); repo actively maintained | [releases](https://github.com/PaddlePaddle/PaddleOCR/releases) |
| Licence | Apache-2.0 (code and Korean weights) | [LICENSE](https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE) |
| Korean model | `korean_PP-OCRv5_mobile_rec`, **88.0%** accuracy, 14 MB | [PP-OCRv5 multi-language docs](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html) |
| Korean support | Dedicated Korean model. **Caveat: 88.0% is PaddleOCR's own in-house dataset, not a public benchmark** | same |
| Layout | PP-StructureV3 (PP-DocLayout, table, reading order, seal). **Not used by ADVS today** | [PP-StructureV3](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html) |
| CPU latency | `korean_PP-OCRv5_mobile_rec` 5.32 ms, `PP-OCRv5_mobile_det` 28.15 ms (high-perf, Xeon 6271C) | [OCR module tables](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html) |

**Two findings that changed our configuration:**

1. **`lang="korean"` silently pins you to PP-OCRv5, not PP-OCRv6.** PP-OCRv6's
   50-language list excludes Korean
   ([docs](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv6/PP-OCRv6.html);
   verified in `paddleocr/_pipelines/ocr.py`). ADVS's existing config is
   therefore correct, and this was worth confirming rather than assuming.
2. **PaddleOCR's own PDF render default is 2.0× = 144 DPI**
   (`paddlex/utils/flags.py::PDF_RENDER_SCALE`). ADVS was using this default.
   Measured evidence (below) shows it is too low for this corpus.

### PaddleOCR-VL — **NOT ADOPTED**

Strongest measured Korean edit distance of anything surveyed (**0.052** on
PaddleOCR's 107k-sample multilingual eval, vs Latin 0.013 and Japanese 0.086;
[arXiv:2510.14528v4](https://arxiv.org/html/2510.14528v4v4) §4.2.1 Table 6a).
Apache-2.0, actively maintained (v1.6, 2026-05-28).

Rejected for production on three measured grounds:
- **CPU cost.** A 0.9 B autoregressive VLM. PaddleOCR publishes **no CPU
  latency figure**; the nearest published CPU number for a comparable VLM
  class is Surya 2 at **p50 59 s / page** on Apple Silicon
  ([surya#throughput](https://github.com/datalab-to/surya#throughput)). That is
  ~2 orders of magnitude wrong for a certificate pipeline.
- **Coordinate granularity.** PaddleOCR's README states PP-StructureV3
  *"provides more fine-grained coordinate information, including table cell
  coordinates, text coordinates"* **unlike** the PaddleOCR-VL series, which
  emits block-level coordinates plus HTML. ADVS's evidence contract needs
  line-level boxes.
- Requires a separate inference service (`llama-server`/vLLM) — new
  infrastructure with no ADVS requirement.

### Surya — **REJECTED on licence**

Code is Apache-2.0, but **model weights are a modified OpenRAIL-M capped at
$5 M funding/revenue** ([surya#commercial-usage](https://github.com/datalab-to/surya#commercial-usage)).
Apache-2.0 code does not launder a separately-licensed weight file. Korean
`ko` pass rate 86.7% (internal benchmark, vendor-run) would otherwise have been
competitive. Also minute-per-page on CPU.

### docTR — **REJECTED for Korean**

Excellent engineering (best layout/reading-order/table API surveyed, native
per-word geometry, Apache-2.0, v1.1.0 2026-08-21). But every shipped
pretrained recogniser defaults to `VOCABS["french"]`; the Korean vocab exists
only for training/whitelisting, and a whitelist **cannot add characters a
model never saw** ([docs](https://mindee.github.io/doctr/latest/using_doctr/using_models.html)).
Adopting it means training a Korean recogniser — a research project, not an
integration. Korean accuracy: **UNVERIFIED, no benchmark exists.**

### Tesseract — **REJECTED as primary, retained conceptually as a fallback**

- **Korean is materially worse.** On KORIE (774 Korean receipts, peer-reviewed
  [MDPI Mathematics 14(1):187](https://www.mdpi.com/2227-7390/14/1/187)):
  Tesseract CER 25.43 % / WER 35.26 % vs PaddleOCR 15.84 % / 26.73 %.
- **Known Korean-specific defect:** the LSTM decoder inserts spurious
  inter-character spaces in CJK, with Korean named explicitly
  ([tesseract#1009](https://github.com/tesseract-ocr/tesseract/issues/1009),
  closed 2021; root cause in `recodebeam.cpp` per
  [tesseract#991](https://github.com/tesseract-ocr/tesseract/issues/991)).
  This would corrupt word-level matching.
- **No layout, no tables** — official docs state Tesseract has a known problem
  recognising table data ([ImproveQuality](https://github.com/tesseract-ocr/tessdoc/blob/main/ImproveQuality.md)).
- Requires ≥300 DPI input per the same doc — a constraint, not a feature, for us.

### EasyOCR — **REJECTED**

Last release v1.7.2 (2024-09-24); last commit 2025-12-05 and it touched only
the README. Korean model `korean_g2` inherited from a 2020-era tag. Beaten by
PaddleOCR on KORIE (17.36 % vs 15.84 % CER). No layout, no tables.

### Independent Korean accuracy evidence

| Engine | CER | WER | Source |
|---|---|---|---|
| PaddleOCR | **15.84 %** | **26.73 %** | KORIE |
| EasyOCR | 17.36 % | 31.43 % | KORIE |
| Tesseract | 25.43 % | 35.26 % | KORIE |

**Honest limitation:** KORIE is *receipts* (thermal fading, glare, creases),
which is harder than a clean printed certificate. It is the only independent
Korean number available, and it is an upper bound on difficulty. There is **no
public benchmark for Korean business/government certificates at all.** Every
certificate-specific performance claim in this report is extrapolation from our
own measurements, and is labelled as such.

Structural reason Korean trails Latin: Hangul is an alphabet-of-blocks with
11,172 precomposed syllables, giving a naive classifier a ~430× larger output
space ([arXiv:2208.06079](https://arxiv.org/pdf/2208.06079)).

---

## 2. Rasterization DPI — evidence

Tesseract's own docs: *"Tesseract works best on images which have a DPI of at
least 300 dpi"*
([ImproveQuality](https://github.com/tesseract-ocr/tessdoc/blob/main/ImproveQuality.md)).

IBM's production OCR guidance is more specific and more relevant:
*"Optimal DPI for recognition is generally 200 or 300 DPI… Higher DPIs can be
used for better recognition with small fonts or when recognizing languages
containing intricate characters."*
([IBM Baidu OCR best practices](https://www.ibm.com/docs/en/bacaoc?topic=solutions-best-practices-ocr-content-analyzer))
— that describes Hangul in certificate fine print exactly.

Counter-evidence exists and is not ignored: a peer-reviewed 2026 study reports
accuracy **peaking at 300 dpi and declining at 600**
([Boubehziz et al.](https://hal.science/hal-05620753), read only via search
index — full text **UNVERIFIED**), and another reports that 300→150→300
bicubic *improved* Tesseract ([arXiv:2105.04515](https://arxiv.org/pdf/2105.04515)).
The US GPO white paper argues no single enhancement reliably helps
([GPO](https://www.govinfo.gov/media/WhitePaper-OptimizingOCRAccuracy.pdf)).

**Conclusion: the curve is task-dependent and non-monotonic, so it must be
measured on our own documents.** We did (see `experiment_plan.md`); 288 DPI
measured best on our sample, and the setting is now a clamped, adjustable knob
rather than a hard-coded constant.

---

## 3. Cloud document AI

**No live calls were made.** No credentials exist in this project, and the owner
did not grant explicit authorization to transmit documents to third parties.
All rows below are **research-only, not live-benchmarked**.

### NAVER CLOVA OCR — strongest fit, not adopted

| Property | Finding | Source |
|---|---|---|
| Korean | Native; `lang` ∈ {`ko`,`ja`,`zh-TW`}; handwriting KO/JA | [General OCR API](https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocr) |
| Geometry | `boundingPoly.vertices[]` polygons; **per-word only inside tables**; no per-field page number | same |
| Confidence | `inferConfidence` / `confidenceScore` 0–1. **Documented as only "the higher the value the more accurate"** — no calibration, no probability semantics | same |
| **사업자등록증** | Dedicated `POST /biz-license` model returning exactly our schema (`registerNumber`, `companyName`, `corpRegisterNum`, `repName`, `openDate`, …) **with per-field polygons and confidence** | [biz-license API](https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocrdocumentocr-bizlicense) |
| Tables | `enableTableDetection` → `tables[].cells[]` with row/col span, polygons, nested words | General OCR API |
| Privacy | **"별도로 저장하거나 활용하지 않습니다"** — does not store submitted images or results; only minimal billing logs. Regions: **KR-1/KR-2 only** (good for Korean PII residency) | [CLOVA OCR FAQ](https://guide.ncloud-docs.com/docs/en/clovaocr-faq) |
| Price | General text 3원/call; text+table 25원/call. Document OCR Basic 18,000원/mo (300 calls), Standard 180,000원 (3,000), Advanced 580,000원 (15,000) → **~60원/doc at 300–3,000 docs/mo** | [product page](https://www.ncloud.com/product/aiService/ocr) |
| Throughput | **1 TPS recommended per service account** | [prerequisites](https://guide.ncloud-docs.com/docs/en/clovaocr-spec) |
| Friction | Needs NCP account + API Gateway (**billed separately**) + **sales-gated approval for 특화 모델**; no English-only mode; table extraction doubles billing; image long edge must be <8,000 px | [scenario](https://guide.ncloud-docs.com/docs/en/clovaocr-procedure) |

Not adopted because: (a) every document would leave the premises, including
ID-like documents; (b) the `verified` confidence semantics are undocumented and
uncalibrated, and its example responses show `confidenceScore: 0.0`, so we
could not calibrate our `0.90` floor against it; (c) 1 TPS; (d) NAVER states a
**consent-gated** path exists where submitted data may be analysed internally
— the opt-out must be contractual, not assumed.

### Azure AI Document Intelligence — viable alternative, not adopted

- **Korean: YES, verified.** `ko` is listed for Read (printed *and* handwritten —
  the handwritten table is exactly 10 languages including `ko`) and Layout
  ([language support](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/language-support/ocr?view=doc-intel-4.0.0)).
- **Best-documented confidence semantics of the four:**
  *"Field confidence indicates an estimated probability between 0 and 1 that
  the prediction is correct… a confidence value of 0.95 indicates the
  prediction is likely correct 19 out of 20 times"*
  ([accuracy & confidence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence?view=doc-intel-4.0.0)).
  Still "estimated", and MS tells customers to pilot it themselves.
- **v4.0 gotcha:** `prebuilt-document` no longer exists in v4.0 — it is folded
  into Layout, which must be called with `features=keyValuePairs`.
- **Omits `locale` deliberately** — *"Don't provide the language code…
  otherwise the service may return incomplete and incorrect text."*
- **Stores your data 24 h** on shared regional infrastructure
  ([data privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security));
  not used for training (VSTAFF-confirmed).
- **Korea region availability: UNVERIFIED.** If Korea is not an available
  region, Korean PII leaves the country — a blocking question.
- Price: Read $1.50/1k pages, Layout $10/1k, custom extraction $30/1k
  ([pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)).
- Per **page** = per transaction; 2,000 pages max per analysis (S0), 15 TPS.

### Google Document AI — viable, not adopted

- **Korean: YES, verified** across Enterprise Document OCR, Custom Extractor,
  Form Parser and Layout Parser (all four language tables list `ko`/`Kore`).
  The "Layout Parser dropped language support" rumour is **false** for GA.
- **Material catch:** *"If using generative AI for extraction, then: Only the
  English language is officially supported"*
  ([processors](https://docs.cloud.google.com/document-ai/docs/processors-list)).
  The table above it lists Korean, but the GenAI extraction layer is
  English-only. **UNVERIFIED** whether Korean merely lacks an SLA or actually
  fails.
- **Data-residency escape hatch:** newer Gemini-backed processor versions
  *"use the Vertex AI Gemini global endpoint and are not compliant with Data
  Residency (DMZ) standards."* Layout Parser also has **no APAC single
  regions**; single-region throughput is **6 requests/minute**.
- **No documented confidence semantics** — a real gap versus Azure.
- **Human-in-the-loop is deprecated** (unavailable after 2025-01-16).
- Price: Enterprise OCR free to 1k pages then $1.50/1k; Layout $10/1k; Form
  Parser $30/1k ([pricing](https://cloud.google.com/document-ai/pricing)).
- Explicitly states it never trains on customer data — the clearest no-training
  commitment of the three.

### AWS Textract — **DISQUALIFIED**

Official quotas page, verbatim:
*"Amazon Textract supports English, French, German, Italian, Portuguese, and
Spanish text detection"*, and the supported character list contains **"No Hangul
syllables"*
([limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.md)).
It also *"will not return the language detected in its output"*, so Korean input
cannot even be detected and rejected. No workaround. Excluded on evidence, not
on omission.

---

## 4. LLM / VLM — where they help, where they are dangerous

**Not adopted anywhere in the pipeline.** Reasoning:

**Genuinely useful (not implemented; candidates for a future semantic fallback):**
- disambiguating a corrupted label ("유효기간" vs "유효기한" vs "유효년월일")
- choosing between competing label interpretations on unseen layouts
- ranking candidates whose shape is valid for several fields
- a second opinion when deterministic extraction finds nothing

**Dangerous — must never be on the critical path:**
- any number that will be compared for equality (사업자등록번호, 납세번호, 학번)
- date parsing and expiry comparison
- required-document presence
- any final legal/official determination

Evidence for the danger: VLMs are known to *repair* imperfect text toward more
plausible forms, which is invisible on clean benchmarks and catastrophic for
identifier equality. Neither OmniDocBench nor OCRBench v2 includes **Korean** at
all ([OmniDocBench](https://arxiv.org/abs/2412.07626) enumerates
`english`/`simplified_chinese`/`en_ch_mixed`/`traditional_chinese`/`other`),
so **headline "SOTA document OCR" numbers say nothing about Korean.** Benchmarks
that do cover Korean exist (FaithC4, MDPBench) but are young and small.

**Privacy:** any such call transmits a document containing a real person's name
and identifiers to a third party. **Cost:** per-image fees on top of the
existing pipeline. **Reproducibility:** a model update silently changes
extraction output, which conflicts with ADVS's determinism requirement.
**Evidence:** a VLM cannot supply bounding-box provenance comparable to what the
evidence policy requires.

ADVS's existing conservative design — *unknown or ambiguous values must be
`null` or review, never hallucinated* — is the correct posture and is strictly
better served by deterministic abstention than by a model that guesses.

---

## 5. Architecture comparison and selection

| | A: current (Paddle + heuristic) | B: improved OCR + geometry | C: cloud doc AI + deterministic | D: OCR/layout + semantic fallback | E: VLM-first |
|---|---|---|---|---|---|
| Korean accuracy | model is fine; **input is destroyed** | **measured improvement** | likely good; unverified here | unverified | unverified for KO |
| Real-layout robustness | **poor (proven)** | **good for observed cases** | good | good | good |
| Explainability | good | **good (kept)** | good | degraded | poor |
| Determinism | **yes** | **yes** | yes | **no** | **no** |
| Privacy | **local** | **local** | **external transfer** | mixed | external |
| CPU feasibility | **yes** | **yes** | n/a | yes | **no** |
| Latency | ~14 s/page | ~14 s/page | ~1 s + network | +LLM latency | minutes |
| Monetary cost | **0** | **0** | ₩60/doc or $1.50–30/1k | 0 + LLM tokens | per-image |
| Dev complexity | — | **low (done)** | high (gateway, approval) | high | very high |
| Hallucination risk | **none** | **none** | low | **high** | **high** |
| Review compatibility | **yes** | **yes** | yes | yes | poor |

**Selected: Architecture B** — improved rasterization + layout-preserving
representation + shape-validated candidate ranking, with the existing
deterministic verification untouched.

It is the only option that (a) fixes a failure we *measured*, (b) keeps
determinism, (c) keeps documents on-premises, (d) costs nothing per document,
and (e) does not regress anything. C is a credible future escalation path
(CLOVA's 사업자등록증 model is genuinely the best-matched offering found) but
requires an explicit privacy decision that the owner has not made.
