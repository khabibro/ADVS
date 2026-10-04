# Selected Configuration

## Selection

Retain the existing local PaddleOCR production configuration as the P2
measurement baseline:

- PP-OCRv5 mobile detector
- Korean PP-OCRv5 mobile recognizer
- CPU
- source-aware PDF rendering with a nominal 288 DPI target and resource caps
- current conditional document-orientation retry
- current EXIF/format normalization only

## Why

This is the only candidate measured end to end against the actual ADVS adapter
and real private documents. It reproduced cached page and line text on all 7/7
documents. There is no observation gold to establish whether another DPI,
preprocessing pass, or detector improves correctness without increasing wrong
non-null values. Official model documentation does not establish a better
Korean server recognizer or a Korean PP-OCRv6 recognizer.

This is a baseline-retention decision, not a claim that the current model is
optimal. No production files or dependencies changed.
