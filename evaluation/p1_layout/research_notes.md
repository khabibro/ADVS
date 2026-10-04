# Research notes — primary sources

Everything in **DOCUMENTED FACT** was read from a live official page or an
official repository file. Nothing architectural rests on a blog post or on
recollection.

## Version status

**DOCUMENTED FACT** — latest PyPI release is `paddleocr 3.7.0`, uploaded
2026-06-11. <https://pypi.org/pypi/paddleocr/json>

**DOCUMENTED FACT** — the repository pins `paddleocr==3.2.0` and
`paddlepaddle==3.1.1` in `apps/api/pyproject.toml`. Installed versions are 3.2.0
and 3.1.1. The official "Recently Update" page stops at 3.2.0; there are no
official release notes on the docs site for 3.3 through 3.7.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/update/update.html>

**INFERENCE** — upgrading to 3.7.0 would force `paddlex` from 3.2.1 to 3.7.x in
lockstep. That is dependency churn unrelated to measured P1 benefit, so it was
not done.

## PP-StructureV3

**DOCUMENTED FACT** — released and documented. Seven declared modules: Layout
Detection, General OCR Subline, Document Image Preprocessing Subline (optional),
Table Recognition Subline (optional), Seal Text Recognition Subline (optional),
Formula Recognition Subline (optional), Chart Parsing Module (optional).
Entry point `from paddleocr import PPStructureV3`.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/pipeline_usage/PP-StructureV3.html>

**DOCUMENTED FACT** — the default model set, from the pipeline config, includes
`PP-DocLayout_plus-L` (layout), `SLANeXt_wired` and `SLANet_plus` (table
structure), `RT-DETR-L_wired_table_cell_det` and
`RT-DETR-L_wireless_table_cell_det` (table cells), `PP-OCRv5_server_det`,
`PP-OCRv5_server_rec`, `PP-LCNet_x1_0_table_cls`, `UVDoc`,
`PP-LCNet_x1_0_doc_ori`.
<https://github.com/PaddlePaddle/PaddleX/blob/develop/paddlex/configs/pipelines/PP-StructureV3.yaml>

**DOCUMENTED FACT** — `device="cpu"` is supported for every component, and every
model has a published CPU inference time.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/pipeline_usage/PP-StructureV3.html>

**DOCUMENTED FACT** — `layout_onnx_model`, `DocLayout-YOLO` and
`DocLayout-YOLOv2` are **not** in the current model registry; they are 2.x-era
names.
<https://github.com/PaddlePaddle/PaddleX/blob/develop/paddlex/inference/utils/official_models.py>

**DOCUMENTED FACT** — measured download sizes give a PP-StructureV3 default set
of roughly **1.8 GB**, of which `PP-Chart2Table` alone is ~1.37 GB (off by
default). Table structure models are ~702 MB.

## Table recognition

**DOCUMENTED FACT** — `SLANeXt_wired` and `SLANeXt_wireless` are both current,
351 MB each, with published CPU times only in high-performance mode. No newer
replacement and no deprecation notice.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/module_usage/table_structure_recognition.html>

**DOCUMENTED FACT** — the current pipeline class is `TableRecognitionPipelineV2`.
`paddleocr.TableMaster`, `TableRecognition` and `TableStructure` do **not** exist
in 3.x; `TableMaster` was a 2.x model-name string.
<https://github.com/PaddlePaddle/PaddleOCR/blob/main/paddleocr/__init__.py>

**DOCUMENTED FACT** — for the SLANeXt series, the module docs warn that the
table cell predictions are invalid; cell geometry must come from
`TableCellsDetection` (`RT-DETR-L_*_table_cell_det`, ~124 MB each).
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/module_usage/table_cells_detection.html>

**DOCUMENTED FACT** — `TableRecognitionPipelineV2` requires the `paddlex[ocr]`
extra. Running it in the project environment raises
`paddlex.utils.deps.DependencyError`.

## Layout detection

**DOCUMENTED FACT** — `LayoutDetection` is importable from `paddleocr`. Twelve
models are registered, including `PP-DocLayout-S` (4.8 MB),
`PP-DocLayout-M` (22.6 MB), `PP-DocLayout-L` (123.8 MB) and
`PP-DocLayout_plus-L` (126 MB). All list CPU times.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/module_usage/layout_detection.html>

**DOCUMENTED FACT** — the docs state that omitting `model_name` uses
`PP-DocLayout-L`, while the source default is `PP-DocLayout_plus-L`. Always pass
the model name explicitly.

**EXPERIMENTAL RESULT** — `LayoutDetection(model_name="PP-DocLayout-S",
device="cpu")` initialised in 5.3 s on first download and 0.5 s cached, on this
machine.

## Korean support — the decisive gap

**DOCUMENTED FACT** — every layout model's documented training data is
"Chinese and English papers, PPT, multi-layout magazines, contracts, books,
exams, ancient books and research reports". **Korean is never mentioned** in the
layout model list.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/module_usage/layout_detection.html>

**DOCUMENTED FACT** — the only documented table datasets are PubTabNet (English
biomedical), TAL (Chinese) and WTW (Chinese scene tables). **No Korean table
dataset and no Korean table model exist.**
<https://paddlepaddle.github.io/PaddleOCR/latest/en/datasets/table_datasets.html>

**DOCUMENTED FACT** — Korean **is** documented for text *recognition*
(`korean_PP-OCRv5_mobile_rec`), which the project already uses.

**INFERENCE** — table structure and layout models are Chinese/English-centric.
Running them as the authority for Korean administrative documents would place
undocumented behaviour between the recogniser and the extractor, on exactly the
documents the product must not get wrong.

## Platform

**DOCUMENTED FACT** — high-performance inference supports **Linux x86-64 only**.
`enable_hpi=True` is not available on macOS arm64.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/inference_deployment/local_inference/high_performance_inference.html>

**DOCUMENTED FACT** — the Apple Silicon matrix marks PaddlePaddle engine as
supported; speed and accuracy were verified only on Apple M4.

**INFERENCE** — MKL-DNN is not built into the macOS arm64 PaddlePaddle wheel, so
`enable_mkldnn=True` is likely a silent no-op here.

## Dependency extras

**DOCUMENTED FACT** — the extras matrix: `doc-parser` covers document parsing
and PP-StructureV3; base `pip install paddleocr` gives general OCR and document
preprocessing only.
<https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/installation.html>

**DOCUMENTED FACT** — for 3.2.0 the core dependency is `paddlex[ocr-core]` and
the `doc-parser` extra is `paddlex[ocr]`.

## Conclusion carried into selection

The heavyweight structural stack is available, documented, CPU-capable, and
**not documented for Korean**, and its cell-level component cannot even be
executed in this environment without a dependency change that measurement does
not justify. That combination, together with the finding that half the
unresolved fields have no label text in the OCR output at all, drove the
selection recorded in `benchmark_summary.md`.