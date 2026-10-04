# OCR Candidate Research

Research checked official PaddleOCR/PaddleX documentation and repositories on
2026-10-03. Facts below are separated from local measurements and inference.

## Documented facts

- The installed stack is PaddlePaddle 3.1.1, PaddleOCR 3.2.0, PaddleX 3.2.1.
- Official PP-OCRv5 multilingual documentation lists
  `korean_PP-OCRv5_mobile_rec` for Korean and English. It reports 88.0% on the
  model's corresponding evaluation set and a 14 MB model. That is not an ADVS
  real-document accuracy estimate.
- Official PP-OCRv5 module documentation lists the Korean recognizer as the
  supported Korean model. The server recognizer is documented for Chinese
  variants, English and Japanese, not Korean. It is therefore not a justified
  Korean server-scale candidate.
- Official PaddleOCR source maps PP-OCRv5 `lang="korean"` to
  `korean_PP-OCRv5_mobile_rec`, while using the PP-OCRv5 server detector in that
  pipeline mapping. Compatibility in the ADVS adapter still requires local
  integration measurement.
- Official model docs list a Korean PP-OCRv3 mobile recognizer (60.21% on its
  corresponding evaluation set, 9.6 MB). It is older and the published metric
  is not directly comparable to the PP-OCRv5 Korean benchmark.
- Current official PP-OCRv6 recognition listings describe 50 supported
  languages, but the official repository discussion specifically says Korean
  is not among those current languages. A PP-OCRv6 recognizer is not a Korean
  replacement candidate. Its detector could be considered only if official
  package compatibility and ADVS box-level detection errors justify it.
- No official documentation reviewed here establishes Korean support for a
  PP-OCRv5 server recognizer.

## Measured locally

- The production configuration loads the cached PP-OCRv5 mobile detector and
  Korean PP-OCRv5 mobile recognizer on CPU.
- Current stack versions and source configuration are recorded in
  `baseline_state.md`.
- A fresh 7-page production adapter capture exactly matched the frozen P1 OCR
  page text and line text for all seven samples.
- No alternative model was installed or benchmarked. No network model download
  was attempted.

## Inference and candidate decision

- Keep the present detector/recognizer while constructing observation gold.
- Do not move to PP-OCRv6 recognition for Korean; current official language
  support does not establish it.
- PP-OCRv3 Korean has weaker published corresponding-dataset performance than
  PP-OCRv5 but is not an apples-to-apples comparison; it is a lower-priority
  ablation, not a presumed regression or improvement.
- A server detector plus Korean mobile recognizer is a plausible detector-only
  candidate if boxes are missing/merged. The current corpus has not yet been
  independently annotated at box level, so it is not selected.
- Cloud OCR is not evaluated. No document was sent externally and no
  credentials or upload authorization were provided.

## Primary sources

- [PP-OCRv5 multilingual models](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md)
- [Text recognition module/model table](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/module_usage/text_recognition.en.md)
- [Official OCR pipeline model selection](https://github.com/PaddlePaddle/PaddleOCR/blob/main/paddleocr/_pipelines/pp_structurev3.py)
- [Official PP-OCRv6 Korean-language support discussion](https://github.com/PaddlePaddle/PaddleOCR/discussions/18249)
- [Korean PP-OCRv3 model configuration](https://github.com/PaddlePaddle/PaddleOCR/blob/main/configs/rec/PP-OCRv3/multi_language/korean_PP-OCRv3_mobile_rec.yml)
