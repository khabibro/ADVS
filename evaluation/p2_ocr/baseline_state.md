# P2 Baseline State

## Repository and evaluator

| Item | Value |
|---|---|
| Starting HEAD | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` |
| Branch | `main` |
| Tracked changes at start | none |
| Historical field baseline | 7 documents; 16 correct; 1 incorrect non-null; 17 unresolved; recall 0.471; False READY 0 |
| Frozen gold SHA-256 | `ff4b226c946b78d79ee320c3e30fd349ca715a7db18c403159088e9b05e53893` |
| Frozen runner SHA-256 | `de667f011d196c8cdbc292bd2a198a82d7b752c899957492fb165b9a15db8f64` |
| Frozen summarizer SHA-256 | `4d44a504c89eab8a636f5067879164473f7ac0daf2f1e3b9b6155d13aaa1a8fc` |
| P1 diagnosis SHA-256 | `88b8b48420d54005c63623808e43d01fd25f5956347690cab17b39f2c801a879` |
| P1 observation loader SHA-256 | `101397bc1f610003bcfcb69312775c516db88e798331f9797a6339dba4f3f972` |

## Dataset integrity

Seven originals were discovered in the existing private directory and read only.
Their per-file SHA-256 and sizes match all seven records in the frozen P1
manifest. Safe-ID fingerprints including size and nanosecond mtime were captured
before P2 in ignored `evaluation/backend_round2/work/p2_original_fingerprints.json`.
The after-run comparison reports all seven hashes, sizes, and mtimes unchanged.
No private path or filename is recorded here.

The frozen gold is ignored by Git at `evaluation/backend_round2/work/`; the P1
observation cache is outside the repository. `evaluation/p2_ocr/` is not an
ignored directory, so only sanitized reports are written there.

Corrected transcript annotations are versioned in ignored
`evaluation/backend_round2/work/ground_truth_v2.json`; the frozen v1 file was
not edited.

## Runtime

| Item | Value |
|---|---|
| System Python | 3.14.3; Paddle packages unavailable |
| Project interpreter | Python 3.12.14, `apps/api/.venv312` |
| PaddlePaddle | 3.1.1 |
| PaddleOCR | 3.2.0 |
| PaddleX | 3.2.1 |
| PyMuPDF | 1.28.2 |
| Device | CPU; no GPU detected in prior P1 environment |
| Models | `PP-OCRv5_mobile_det`, `korean_PP-OCRv5_mobile_rec` |
| Model cache | present under ignored `apps/api/storage/paddleocr-cache`; cached model inventory documented by P1 |
| Rendering configuration | 288 DPI nominal for PDFs; scale clamped to 1.5–6.0 |
| Image preprocessing | EXIF transpose and RGB conversion when preparation is required; PDF rasterization path is in the Paddle provider |
| Orientation | document orientation classifier enabled only on a retry when output looks orientation-damaged; text-line orientation disabled |
| Detection/recognition thresholds | ADVS does not override PaddleOCR/PaddleX defaults; effective numeric defaults are not pinned in Settings or the adapter |
| Batch behavior | ADVS submits one page image per OCR worker call; no batch-size override |
| Input limits | 20 MB upload; 30 PDF pages; 16,000 px maximum side; 25,000,000 input pixels; 250,000,000 total PDF-render pixels; 100,000,000 temporary bytes |
| Timeout | `ocr_timeout_seconds=120` per OCR worker call |
| Runtime environment variables | `DATABASE_URL` set to in-memory SQLite by P1 observation capture; `PADDLE_OCR_CACHE_DIR` defaults to repository storage; `PADDLE_PDX_CACHE_HOME` set by provider |

## Reproduction caveat

The system Python cannot run OCR. The project 3.12 interpreter imports the
historical Paddle stack and local models. P1's 8/17 alias-absence statement was
reproduced with a qualification: one case is a visible OCR-readable synonym
outside the extractor alias set. Detection and recognition remain unseparated
without labeled regions.
