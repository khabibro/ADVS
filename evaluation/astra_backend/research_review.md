# ADVS current document-AI research review

Research date: 2026-09-29; local comparison scored on 2026-09-30. Scope: Korean administrative/business certificates and student documents; evidence-preserving extraction; local processing. This review records current official documentation and papers, not an independent ranking. No Desktop document was submitted to a cloud OCR, LLM, VLM, demo, or hosted inference endpoint. Model download requests contained no document data.

## Evidence categories and limits

- **Official capability** means the linked upstream documentation describes the feature. It does not mean ADVS measured its accuracy.
- **Paper result** means authors measured a particular benchmark and configuration. Such scores do not establish field correctness on Korean certificates.
- **Local measurement** means a run identified in the local-experiment section. Unmeasured services have no ADVS accuracy, cost-per-success, or latency claim.
- **Engineering assessment** is the proposed ADVS implication; it is explicitly distinct from a provider guarantee.

The observed transcript segmentation and glyph-substitution failures are different problems. A recognizer change can improve glyphs while preserving a wrong label/value relationship; a parser can recover cells while still misreading a person's name. Neither model confidence nor well-formed JSON proves identity, semantic association, or readiness.

## Local OCR and parsing options

| Option | Verified capability relevant to ADVS | Deployment, maintenance, licensing | ADVS implication |
|---|---|---|---|
| PaddleOCR / PP-OCRv5 | Dedicated multilingual recognition includes Korean; default multilingual-family labels do not imply one universal recognizer. | Existing local Python 3.12.14 environment has PaddleOCR 3.2.0, PaddlePaddle 3.1.1, PaddleX 3.2.1. | Keep explicit Korean model identity and model hashes. Do not treat generic model upgrades as proven Korean improvements. |
| PP-StructureV3 | Layout, tables, reading order, optional seal/formula components; returns table-cell coordinates and HTML. | Same ecosystem; more models/configuration than plain OCR. | Credible controlled parser experiment for transcript summaries. Do not force cells through a line-only adapter. |
| PaddleOCR-VL | Current documentation includes VL-1.6; local CPU and accelerator paths exist. | Autoregressive model stack; hardware-specific setup and weights. | CPU is supported, not proven fast enough. Requires an independent ADVS benchmark and evidence-coordinate audit. |
| Surya | Current upstream v2 provides OCR, layout, reading order, and table geometry. | CPU/Apple Silicon via llama.cpp; NVIDIA via vLLM; code and weights have different licenses. | Older reviews of v1 deployment/license do not describe current v2. Larger integration change than adding polygons. |
| docTR | OCR hierarchy, geometry, rotation support, selectable recognizers; Korean vocabulary exists in source. | Current project says Python 3.11+ and ongoing t2k maintenance. | Vocabulary availability is not proof that the chosen pretrained recognizer learned Hangul. |
| Tesseract | Korean traineddata, CPU CLI, TSV/hOCR geometry; page segmentation modes. | Local Tesseract 5.5.2 exists; isolated official Korean weights downloaded. | Credible low-cost comparison, not a table parser or presumptive production replacement. |
| EasyOCR | Korean model, quadrilateral coordinates, recognized text and confidence; CPU mode. | PyTorch stack; Apache-2.0 code; language models download by default. | Another recognizer/detector alternative; cell semantics remain an ADVS responsibility. |

### Paddle: versions, language coverage, and geometry

Upstream currently advertises PP-OCRv6 and PaddleOCR-VL-1.6, and distinguishes PP-StructureV3's finer text/table-cell coordinates from VL outputs. PP-OCRv6's advertised unified language set is Chinese, English, Japanese, and Latin-script languages; that list does not establish Korean coverage. The project code is Apache-2.0. These are upstream statements, not ADVS measurements. [Official repository](https://github.com/PaddlePaddle/PaddleOCR)

The separate PP-OCRv5 multilingual documentation explicitly includes Korean. Its benchmark percentages are vendor evaluations and are not interchangeable with ADVS supported-field precision. [PP-OCRv5 multilingual documentation](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html)

The OCR output exposes detection polygons, recognition-filtered polygons, recognition scores, page metadata, and textline orientation. Preserve those original polygons; derive an axis-aligned box as a convenience. A recognition score describes recognized text, not field association or document truth. [OCR result schema](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

PP-StructureV3 exposes `table_res_list`, `cell_box_list`, table HTML, and table OCR outputs. This justifies an optional parser capability alongside ordinary OCR, without requiring every provider to construct cells. Its Korean recognition configuration must be explicitly checked; table support does not itself certify Hangul recognition. [PP-StructureV3 schema](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html)

Current PaddleOCR-VL documentation explicitly lists x64 CPU support, Apple Silicon options, NVIDIA paths, and hardware-specific accelerator requirements. It gives local and service deployment modes. Therefore a blanket statement that VL has no CPU support is contradicted; practical ADVS CPU latency remains unmeasured. [PaddleOCR-VL deployment documentation](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html)

The PaddleOCR 3.0 report separates OCR, hierarchical parsing, and key-information extraction. VL-1.5 studies degraded documents, while newer upstream VL releases exist. Their public benchmark results motivate experiments, not automatic replacement. [PaddleOCR 3.0 paper](https://arxiv.org/abs/2507.05595), [PaddleOCR-VL paper](https://arxiv.org/abs/2510.14528), [VL-1.5 paper](https://arxiv.org/abs/2601.21957)

### Surya

Current Surya upstream describes v2 with a shared VLM inference backend. CPU/Apple Silicon uses llama.cpp; NVIDIA uses vLLM. OCR blocks expose polygon, box, HTML, and mean token-probability confidence. Table output distinguishes simple row/column intersections from full HTML with spanning cells. Code is Apache-2.0; weights use a modified AI Pubs Open Rail-M license with commercial conditions. A token-probability mean is not a calibrated field-correctness score. [Official Surya repository](https://github.com/datalab-to/surya)

The current package permits Python 3.10 through 3.x, but depends on a substantial PyTorch/Transformers stack and a restricted Pillow range. This establishes declared compatibility, not a tested install in ADVS's pinned environment. Use an isolated environment for any experiment. [Surya package metadata](https://github.com/datalab-to/surya/blob/master/pyproject.toml)

### docTR

The official repository states Python 3.11+ and ongoing maintenance by t2k. It supports structured OCR output and geometry. [Official docTR repository](https://github.com/mindee/doctr)

Korean vocabulary is present, but documentation says most supplied recognition models were trained on a French vocabulary and warns that a whitelist cannot add unseen characters. The correct conclusion is **pretrained Hangul capability must be established per checkpoint**, not that docTR categorically cannot represent Korean. No such ADVS checkpoint was evaluated. [Vocabulary source](https://github.com/mindee/doctr/blob/main/doctr/datasets/vocabs.py), [Model selection documentation](https://mindee.github.io/doctr/latest/using_doctr/using_models.html)

### Tesseract and EasyOCR

Tesseract supplies Korean and vertical-Korean language data; the fast and best model families have different accuracy/compute tradeoffs. The engine is Apache-2.0. Its official quality guide cautions that skew and table recognition can require additional processing. [Language models](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html), [Engine repository](https://github.com/tesseract-ocr/tesseract), [Quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)

EasyOCR documents CPU mode and automatic or manual model downloads. Its Korean model configuration includes mixed Hangul, Latin letters, digits, and punctuation. It returns text geometry and confidence; the documented output is not a row/column/cell model. Python 3.12 compatibility needs an isolated install test with selected torch/OpenCV versions before adoption. [Official EasyOCR repository](https://github.com/JaidedAI/EasyOCR), [Korean model configuration](https://github.com/JaidedAI/EasyOCR/blob/master/easyocr/config.py), [Package metadata](https://github.com/JaidedAI/EasyOCR/blob/master/setup.py)

## Cloud document AI: researched, not called

| Provider | Korean / forms / tables / provenance | Local/privacy/cost implication | Disposition |
|---|---|---|---|
| NAVER CLOVA | Explicit Korean general OCR, optional table extraction, field polygons/confidence; dedicated business-registration endpoint. | Cloud API plus domain configuration; document transfer requires separate authorization. | Plausible Korean-form comparison after permission and governance; not measured. |
| Azure Document Intelligence | Korean Read/Layout support; words, tables, selection marks, structure and polygons. | Cloud service; some separately licensed container/disconnected offerings. | Good structural candidate; endpoint/model/version compatibility must be checked. |
| Google Document AI | Korean OCR and Form Parser support; distinct Layout Parser; rich document schema. | Hosted service, regional processor versions, page/feature charges. | Candidate for an authorized comparison; not interchangeable with Gemini API. |
| AWS Textract | Tables/cells/merged-cell relationships and geometry; documented OCR languages exclude Korean. | Hosted service and page/feature costs. | Do not select for primary Hangul extraction under current documented language support. |

CLOVA General OCR explicitly accepts `ko`, supports table extraction when enabled in the domain, and returns polygon/text confidence with converted-page dimensions. Its API declares page/file limits which must not become ADVS's unbounded upload limits. [General OCR API](https://api.ncloud-docs.com/docs/ai-application-service-ocr-ocr)

The dedicated business-registration endpoint returns organization, business-number, representative, issue-date and other fields, with common confidence/geometry objects. That endpoint's existence is meaningful domain support; it proves neither coverage of every Korean certificate nor superiority on these samples. [Business-registration API](https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocrdocumentocr-bizlicense), [API overview](https://api.ncloud-docs.com/docs/en/ai-application-service-ocr)

Azure's v4 layout model documents OCR, tables, selection marks, paragraphs/roles, and polygons. Its language matrix includes Korean, with support varying by model/version and print/handwriting. [Layout documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout?view=doc-intel-4.0.0), [Language matrix](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/language-support/ocr?view=doc-intel-4.0.0)

Azure documents disconnected containers with commitment/licensing requirements. This is not evidence that any ADVS user can run any current cloud model offline without commercial setup. [Disconnected deployment](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/containers/disconnected)

Google lists Korean for OCR and Form Parser; processor versions and limits differ. Layout Parser is separately described for content structure/chunking. Its document schema includes pages, layout, text anchors, bounding polygons, tables, entities and quality-defect signals. [Processor/language/version list](https://docs.cloud.google.com/document-ai/docs/processors-list), [Document schema](https://docs.cloud.google.com/document-ai/docs/reference/rest/v1/Document)

Google states customer data is not used to train Document AI models. This does not override the user's explicit prohibition on external transfer. [Document AI data policy](https://docs.cloud.google.com/document-ai/docs/security?hl=en)

Textract's current listed text-detection languages are English, French, German, Italian, Portuguese, and Spanish. Korean-language documentation is not Korean OCR support. Its rich table blocks and polygons do not remove that mismatch. [Language limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html), [Table schema](https://docs.aws.amazon.com/textract/latest/dg/how-it-works-tables.html), [Geometry schema](https://docs.aws.amazon.com/textract/latest/APIReference/API_Geometry.html)

Costs must be estimated from the selected region, model, feature, pages, retries, and review rate. Published pricing units differ; no cloud request was made, so this review has no measured per-document cloud cost or latency. Consult [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/), [Google Document AI pricing](https://cloud.google.com/products/document-ai/pricing), [Textract pricing](https://aws.amazon.com/textract/pricing/), and [CLOVA product/pricing](https://www.ncloud.com/product/aiService/ocr). The Google and CLOVA pricing-page retrievals were incomplete; no exact quote is asserted.

## Layout models and academic evidence

| Family | Primary evidence | ADVS assessment |
|---|---|---|
| LayoutLM / LayoutLMv3 | Text, spatial information, and visual features are jointly modeled; v3 uses text/image masking and word-patch alignment. [LayoutLM](https://arxiv.org/abs/1912.13318), [LayoutLMv3](https://arxiv.org/abs/2204.08387) | These are representations/task models, not an off-the-shelf schema for ADVS certificates. Need annotated Korean data, OCR boxes, and supervised evaluation. |
| LayoutXLM | Multilingual pretraining and XFUND form benchmark. XFUND's seven reported languages exclude Korean. [Paper](https://arxiv.org/abs/2104.08836) | Cross-lingual capability is a hypothesis for Korean transfer, not Korean benchmark evidence. |
| Donut | OCR-free document-to-sequence learning; upstream pretraining includes synthetic Korean. [Paper](https://arxiv.org/abs/2111.15664), [Official repository](https://github.com/clovaai/donut) | Requires task/schema adaptation; native token generation lacks ordinary OCR word-box provenance. No ADVS training dataset currently justifies replacing extraction with it. |
| DocFormer | Combines text, visual, and spatial features for document understanding. [Paper](https://arxiv.org/abs/2106.11539) | Conceptually relevant to relationships; maintained deployable Korean checkpoint and Python 3.12 stack not established in this review. |

LayoutLMv3's own project directory declares CC BY-NC-SA 4.0; do not infer a permissive model license from a parent repository or library wrapper. Transformers still documents integration. [Project/license](https://github.com/microsoft/unilm/tree/master/layoutlmv3), [Maintained library integration](https://huggingface.co/docs/transformers/model_doc/layoutlmv3)

Donut's official code is MIT, but its documented original test stack is old and upstream notes dependency-configuration difficulties. Current Transformers integration is preferable to assuming the old installation recipe works on Python 3.12. No runtime test was performed. [Official Donut deployment notes](https://github.com/clovaai/donut)

Other maintained structural approaches directly relevant here are PP-DocLayout/PP-StructureV3, Surya's table/layout capabilities, and Google's current Layout Parser. Their inclusion above does not imply that RAG-oriented Markdown/chunk output preserves enough evidence for deterministic verification.

## Modern multimodal and semantic extraction

Qwen3-VL offers document parsing/grounding examples, local checkpoints from small dense models to large mixtures of experts, and vendor claims of 32-language OCR with degradation robustness. The project is Apache-2.0. The reviewed README does not individually prove Korean field accuracy. CPU feasibility depends on the chosen runtime/quantization; GPU memory and latency require an actual checkpoint experiment. [Official Qwen3-VL](https://github.com/QwenLM/Qwen3-VL)

The current Qwen3.5 repository redirects to Qwen3.8 and describes the 3.5/3.6/3.8 series. This verifies active evolution, not that the newest general model supersedes Qwen3-VL for ADVS document evidence. [Current Qwen family repository](https://github.com/QwenLM/Qwen3.8)

Gemini documents native PDF visual processing, structured extraction, and tables; its current PDF limit is up to 50 MB or 1,000 pages, subject to context and model behavior. Those provider limits are not recommendations for ADVS ingestion. [Document processing](https://ai.google.dev/gemini-api/docs/document-processing), [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)

Gemini API price/data-use tables distinguish free from paid tiers. Never use a free demo as a substitute for a reviewed privacy arrangement. Exact latency and field reliability on this dataset are unmeasured. [Pricing and data-use columns](https://ai.google.dev/gemini-api/docs/pricing)

OpenAI's file-input documentation supports document analysis through multimodal input, and Structured Outputs constrains the output schema. It explicitly warns that schema-conforming outputs can still be wrong and that incompatible input can induce invented content. [File inputs](https://developers.openai.com/api/docs/guides/file-inputs), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

OpenAI's vision documentation explicitly notes limitations for non-Latin scripts including Korean, small text, rotation, and precise spatial localization. Therefore a VLM-produced coordinate is not automatically equivalent to a detector's observed polygon. [Vision limitations](https://developers.openai.com/api/docs/guides/images-vision)

API data retention depends on endpoint and configuration; no-training settings are not synonymous with no retention. Pricing depends on model/input/output/image processing. Both require explicit governance before any future authorized document experiment. [Data controls](https://developers.openai.com/api/docs/guides/your-data), [Pricing](https://developers.openai.com/api/docs/pricing)

**Engineering assessment:** if a semantic fallback is later justified, its input should be a type hypothesis, field schema, OCR/layout candidates, and immutable evidence IDs. Output should permit `null`, cite existing evidence IDs, distinguish inference, and include structured uncertainty. Deterministic code must validate schema, evidence membership, value shape, and normalization. A model may suggest candidates; it must never decide identity equality, expiry arithmetic, required-document satisfaction, or READY. Prompt instructions cannot establish these guarantees alone.

## Capability and deployment gaps that remain unmeasured

No researched vendor has established ADVS accuracy on government/business forms, stamp interference, mixed Korean/digits, low-resolution text, or GPA summaries. Marketing language such as broad language coverage, benchmark leadership, or form understanding is insufficient. Each condition needs a stratified, independently annotated sample set.

Python 3.12 verification is concrete only for ADVS's installed Paddle stack and the Python subprocess experiment using Tesseract. A package's Python version declaration is weaker than tested platform wheels, compatible transitive dependencies, model loading, and inference. Large GPU/VLM dependencies were not installed in production. Model binaries remain outside Git; production dependency files are unchanged by this research.

Offline capability requires preloaded pinned weights, disabled unexpected model downloads/telemetry, bounded local inference, and documented licensing. Local execution avoids cloud transfer but does not itself protect raw OCR logs, temp images, cache permissions, or retention.

## Local alternative experiment

Experiment ID: ASTRA-OCR-ALT-01. Tesseract 5.5.2, OEM 1, official `tessdata_fast/kor.traineddata`. Weight SHA-256: `6b85e11d9bbf07863b97b3523b1b112844c43e713df8b66418a081fd1060b3b2`. [Official model artifact](https://github.com/tesseract-ocr/tessdata_fast/blob/main/kor.traineddata)

The model was downloaded into an isolated `/tmp` directory; no production dependency was added. Representative subset: ASTRA-R03 low-resolution transcript JPEG, ASTRA-R04 scanned transcript PDF rendered with the same 250-DPI setting as ADVS, ASTRA-R06 low-resolution stamped SME image. Images retain their original pixels. PSM 3 (automatic layout) and PSM 6 (single uniform text block) are a prespecified segmentation ablation, not sample-specific tuning. Word TSVs, grouped lines, raw recognition, and generated page images remain outside Git.

The first trial exposed an evaluation-runner issue: an isolated tessdata directory has no `tsv` config file; `tessedit_create_tsv=1` was required. A second trial exposed macOS `/tmp` symlink handling in Leptonica; a canonical `/private/tmp` input path fixed the observed file-open failure. These failed setup trials are retained privately and are not counted as OCR accuracy failures.

The completed controlled comparison uses frozen gold `astra-gold-1.2`, scorer `astra-safety-1.1`, and the same preserved starting classifier/extractor for both providers. Across 18 PRESENT assertions plus two AMBIGUOUS assertions, cached Paddle produced 11 supported correct values, zero proven wrong non-null values, and seven unresolved PRESENT fields; it also populated one ambiguous value. Tesseract PSM 3 produced one correct, one wrong, and 16 unresolved; PSM 6 produced three correct, one wrong, and 14 unresolved. Both Tesseract modes left nine study-required fields unresolved versus four for Paddle. This is not a comparison against the final hardened application and does not evaluate READY.

The two Tesseract wrong values exposed downstream ADVS boundary/semantic-scope defects as well as OCR limitations: border artifacts contaminated a student identifier despite correct digits being available, and a semester GPA was selected as the overall GPA. More recognized text did not imply safer extraction. Do not replace Paddle or choose a Tesseract mode per document from this tiny development subset. See the full [local alternative experiment](ocr_alternative.md) and [sanitized machine-readable result](ocr_alternative.safe.json). Raw box counts are not detection accuracy.

## Provisional architecture recommendation

Repair ADVS's normalization, semantic date scoping, provenance, evidence policy, and transaction/version safety before attributing errors to OCR. Preserve current explicit Korean OCR and introduce only the inexpensive source geometry/transform metadata justified by observed failures. Compare a parser on transcript summary regions only after gold is frozen. Keep cloud and semantic fallback disabled for this task. The final selection must cite measured failures and the final evaluation; this research alone does not authorize a parser replacement.

See [architecture alternatives](architecture_options.md) for the comparative decision matrix. This document intentionally makes no claim of general Korean-document support or production readiness.
