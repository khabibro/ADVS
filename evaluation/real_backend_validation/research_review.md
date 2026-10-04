# Research Review — options considered after the failures were known

Research was performed *after* the baseline, and scoped to the measured failures:
all 3 wrong values originate in **OCR recognition**; the largest capability gap is **layout/table
structure**; the blocking functional defect is the **per-document OCR timeout**.

---

## The decisive fact about the current recogniser

`korean_PP-OCRv5_mobile_rec`, the model ADVS already uses, has a published Korean benchmark accuracy
of **88.0 %**, and the benchmark is **line-level**: *if any character (including punctuation) in a line
is incorrect, the entire line is marked wrong*. Per-character accuracy is therefore materially lower
than 88 %.

This is precisely the observed failure mode: single-syllable substitutions on personal and legal
entity names (`글→굴`, `세→시`, `엠→엔`), all with line confidence above 0.90. **No amount of
downstream extraction logic can fix this**, and no amount of confidence thresholding will detect it,
because the recogniser is confidently wrong.

## OCR options

| Option | Korean | Tables | Provenance | Local | Verdict |
|---|---|---|---|---|---|
| **Current: PP-OCRv5 det + `korean_PP-OCRv5_mobile_rec`** | native Korean rec model | **table structure lost** (independently confirmed in vendor comparisons) | line bbox + polygon + rec score | ✅ CPU, already cached | keep, but add a structure layer |
| PP-OCRv6 | ❌ **Korean is not in the language set** (Chinese/English/Japanese + 46 Latin-script). Despite "+5.1 % recognition over v5", it is **not a Korean upgrade** | — | — | ✅ | **reject for Korean** — do not adopt on the headline number |
| PP-StructureV3 | ✅ for `lang="korean"` it selects `korean_PP-OCRv5_mobile_rec` + `PP-OCRv5_server_det` | ✅ layout detection + table structure (SLANet / SLANet_plus / **SLANeXt**, with **dedicated wired-table weights**), reading-order restoration, Markdown/JSON | ✅ *"more fine-grained coordinate information, including table cell coordinates, text coordinates"* | ✅ CPU pipeline | **adopt** — same recogniser, adds exactly the missing layer |
| PP-StructureV3 seal recognition (`use_seal_recognition`) | ✅ | — | — | ✅ | **adopt (P2)** — Korean certificates are seal-heavy and seal artefacts currently pollute rows (F-08) |
| PaddleOCR-VL-1.6 (0.9B) | ✅ 109 languages incl. Korean | ✅ 96.3 % OmniDocBench v1.6 | ⚠️ **less** fine-grained coordinate info than PP-StructureV3 by Paddle's own README | ⚠️ local CPU possible; the high-performance serving path requires an NVIDIA GPU (CC ≥ 8.0) | **experiment only** — attractive as a *proposal* generator feeding the existing gate, never as an authority |
| Tesseract | ✅ but the well-known Korean intra-word spacing problem; 3 char errors on the reference invoice vs 0 for Paddle | partial | ✅ | ✅ tiny | reject |
| EasyOCR | weak Korean | — | — | ✅ | reject |
| Surya / docTR | strong on Latin | ✅ (Surya has table recognition + reading order) | ✅ | ✅ | **worth a spike as a second opinion on tables**, not a replacement |
| NAVER CLOVA OCR | ✅ Korean-first | ✅ General OCR emits "plain text and table extraction" | per-region boxes | ❌ cloud, **KR region** | see below |

### Layout / table conclusion
Korean government certificates are **ruled (wired) tables**. Paddle's `SLANeXt` family trains
separate weights for wired and wireless tables and is documented as substantially better on wired
tables and less sensitive to table-positioning error. That is the model to evaluate.

### Why PP-StructureV3 and not a VLM
1. It reuses the recogniser already validated in production here, so recognition quality does not
   move — only structure improves. A VLM changes *both*, which destroys the ability to attribute a
   regression.
2. It returns **cell-level coordinates**, which ADVS's evidence model can consume directly.
3. It runs on CPU in the existing pipeline shape.
4. Paddle's own README positions PP-StructureV3 as the fine-geometry option and the VL models as the
   read-it-all option. ADVS needs the former.

---

## Semantic / LLM / VLM options for Korean key-value extraction

- **PP-ChatOCRv4** (ERNIE-integrated, 109 languages) is the in-family option.
- **Structured cloud extractors** (Azure `prebuilt-layout` + custom extraction; Google Form Parser
  Custom Extractor) exist and support Korean, and Google publishes quality benchmarks including
  Korean for key-value internationalisation.
- **Assessment for ADVS:** a semantic layer is the *wrong* tool for the failures actually measured.
  All 3 wrong values are single-glyph recogniser errors inside a correctly-located row — a semantic
  model asked "what is the company name here?" would confidently return the same wrong string, or
  worse, a plausible one. It cannot corroborate a value whose only evidence is a mis-read glyph.
  A semantic layer helps when the *structure* is missing, not when a *character* is wrong. **Keep it
  out of the authoritative path.** If added at all, add it as a proposal generator whose output enters
  the existing `REVIEW_REQUIRED` gate and carries explicit low-trust provenance.

---

## Cloud Document-AI options (privacy-constrained, therefore evaluated but not adopted)

**Hard constraint for this project: realistic documents must remain local.** Any cloud option violates
that by construction, so these are documented as a contingency, not a plan.

| Provider | Korean | Structure | 2026 price / 1k pages | Notes |
|---|---|---|---|---|
| **NAVER CLOVA OCR** | ✅ Korean-first; regions KR-1/KR-2 | ✅ General OCR: text **and tables** | consumption pricing; free tier exists | **Has a purpose-built Korean "Business Registration Certificate (KR)" specialised model** covering business registration certificates and business-operation licences. Document domains require prior application review for sensitive-document handling — which is a governance control, not an obstacle. States it does not store user images/results beyond minimal billing logs. **This is the single most targeted capability on the market for ADVS's worst-performing document type (F-06).** |
| Azure Document Intelligence | ✅ `prebuilt-layout` + custom extraction | ✅ tables, structure, key-value pairs | Read $1.50 · Layout $10 · Custom extraction $30 · Classifier $3 | Free tier (F0) **limits analysis to the first 2 pages and 4 MB** — unusable for real packs |
| Google Document AI | ✅ (KR benchmarked for KV) | ✅ Form Parser, Layout parser | Layout $10 · Custom Extractor $30 · Classifier $5 | Legacy processors discontinued 2026-06-30; the Gemini-3-Flash layout parser "is not compliant with Data Residency" |
| AWS Textract | ✅ | ✅ Tables/Queries | Detect $1.50 · Tables $15 · Forms $50 | Forms+Tables+Queries priced higher than alternatives |

**Note on plain OCR pricing:** all three international clouds charge the same $1.50/1k pages for plain
OCR. Price is not a differentiator; structure, Korean quality, latency and privacy are.

**Contingency recommendation:** if `사업자등록증` extraction must be materially better than 72-DPI
local OCR can deliver, CLOVA OCR's Korean business-registration specialised model is the targeted
option — Korean-first, KR data residency, purpose-built for exactly that document. It would remain a
*proposal* source feeding the existing gate.

---

## Cross-referencing with the measured failures

| Failure | Does a better OCR fix it? | Does a structure layer fix it? | Does a semantic layer fix it? |
|---|---|---|---|
| F-14 timeout | ❌ | ❌ | ❌ — needs a queue |
| F-03 issue_date null | ❌ | ❌ | ⚠️ — a footer-aware semantic rule would, which is why the *guard*, not the fallback, must be fixed |
| F-04 label shadowing | ❌ | ❌ | ❌ — pure code |
| F-05 zero fields on the clean transcript | ⚠️ partially | ✅ **yes** | ⚠️ |
| F-06 company_name null (72 DPI) | ✅ **yes** (resolution/quality) | ⚠️ | ✅ |
| F-07 GPA table | ❌ | ✅ **yes** | ✅ |
| F-10/F-11 wrong glyphs | ✅ **yes** (better recogniser) | ❌ | ❌ — semantic models inherit the error |
| F-12 address | ❌ | ❌ | ⚠️ (an address model would, but that is a new capability) |

**Conclusion:** the single highest-leverage *research-backed* change is **PP-StructureV3 layout +
wired-table structure recognition**. It addresses the largest measured gap, reuses the validated
recogniser, preserves determinism, preserves the evidence model, and runs locally on CPU.