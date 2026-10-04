# Dataset Manifest

Seven documents, safe IDs only. Filenames, paths and text are deliberately
absent. IDs are the frozen `REAL-001..REAL-007` identifiers, assigned by
SHA-256 content hash, so they are stable across phases and independent of file
naming or directory order.

## Provenance

Provenance was taken from the frozen P1 annotation's own source categorisation,
not guessed from filenames.

| Safe ID | Category | Provenance | Pages | Ext | MIME | Pixels / pt | Orientation | Embedded text |
|---|---|---|---|---|---|---|---|---|
| REAL-001 | Social insurance payment certificate | `SYNTHETIC_REALISTIC` | 1 | pdf | application/pdf | 1117×1408 pt | portrait | **0 chars** |
| REAL-002 | Business registration certificate | `SYNTHETIC_REALISTIC` | 1 | png | image/png | 595×842 | portrait | **0 chars** |
| REAL-003 | Transcript | `REAL_PERSONAL` | 1 | jpeg | image/jpeg | 743×1020 | portrait | **0 chars** |
| REAL-004 | Transcript | `SYNTHETIC_REALISTIC` | 1 | pdf | application/pdf | 595×842 pt | portrait | **0 chars** |
| REAL-005 | Enrollment certificate | `SYNTHETIC_REALISTIC` | 1 | pdf | application/pdf | 595×842 pt | portrait | **0 chars** |
| REAL-006 | Enrollment certificate | `REAL_PERSONAL` | 1 | webp | image/webp | 1200×1854 | portrait | **0 chars** |
| REAL-007 | SME confirmation certificate | `SYNTHETIC_REALISTIC` | 1 | jpg | image/jpeg | 400×566 | portrait | **0 chars** |

Totals: 7 documents, 7 unique SHA-256 values, 7 pages, 0 embedded characters,
0 landscape, 0 multi-page.

## Fingerprints

Recorded so a later phase can prove the corpus did not change.

| Safe ID | Size (bytes) | SHA-256 (first 16) |
|---|---|---|
| REAL-001 | 320 926 | `fd0438a39c1840ad` |
| REAL-002 | 195 020 | `62508e58e0e39764` |
| REAL-003 | 157 846 | `98350c274a78a526` |
| REAL-004 | 576 127 | `040d1ea8cf0f2bb1` |
| REAL-005 | 334 767 | `25dac931280bba44` |
| REAL-006 | 151 610 | `fea33de7892df9b9` |
| REAL-007 | 63 309 | `e94ae848c6347e74` |

All seven were matched against the frozen P1/P2 fingerprint record, so the
corpus is the same one P1 and P2 measured.

## Integrity

The originals were opened read-only. Before-and-after comparison of SHA-256,
byte size and nanosecond mtime for all seven:

```
REAL-001: UNCHANGED      REAL-005: UNCHANGED
REAL-002: UNCHANGED      REAL-006: UNCHANGED
REAL-003: UNCHANGED      REAL-007: UNCHANGED
REAL-004: UNCHANGED      all_unchanged: True
```

No file was moved, renamed, rewritten or copied into the repository.

## Three findings that constrain everything downstream

**1. No document contains an embedded text layer.** All seven have zero
extractable characters. Every field value therefore depends entirely on OCR.
There is no fallback path and no way to recover a value that OCR misses.

**2. The corpus is not one resolution.** Effective resolution at the detector
ranges from about 48 DPI (REAL-007) to 288 DPI (REAL-004/005), with REAL-001
additionally downsampled to 108 DPI by the provider's own
`source_resolution_fit` rule. Any conclusion about OCR quality drawn from
"the baseline" is really a conclusion about a mixture.

**3. Provenance is mixed, and mostly not real.** Two documents are genuinely
personal (`REAL_PERSONAL`: REAL-003, REAL-006). Five are realistic
synthetic or recreated material, three of which carry obviously placeholder
identities. **There is no `NEGATIVE_OUT_OF_SCOPE` document in the frozen
corpus at all**, so the corpus cannot demonstrate out-of-scope rejection on
real material; that is covered only by the synthetic safety fixtures. Any
accuracy figure from these seven documents is dominated by synthetic content
and should not be read as a field estimate for real Korean administrative
paper.
