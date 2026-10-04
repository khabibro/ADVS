# ADVS Test-Variant Document Set

Fictional test documents for ADVS. They are built on the layouts of the seven sample documents (사업자등록증, 중소기업확인서, 납세증명서, 4대보험 완납증명원, two 재학증명서 layouts, two 성적증명서 layouts). Each set tests one scenario and has a known expected result.

- **Submission date used for all dates: 2026-10-05.** Dates are computed relative to it (see "Regenerating" below).
- **299 files:** 22 scenario sets (12 business, 10 student), each in three versions (digital PDF, scanned PDF, image files), and 16 file-format / scan-quality sets.
- **Version 2 of the set.** It replaces the earlier 188-file delivery: same scenarios and values, plus an image version of every scenario document, and the PNG / JPEG / WEBP / phone-photo variants extended to all eight layouts.
- **Answer key:** `manifest.json`.

## Privacy and marking

- **No real data.** Every layout was rebuilt from scratch in HTML. No pixel, name, number or address from the original samples was reused.
- **Verified against the originals.** The text of every output was checked against the names, numbers and addresses on the seven original samples: **0 matches**.
- **Visible marking on every page:** `TEST SAMPLE · 테스트용 견본 · 법적 효력 없음`.
- **Authentication features replaced with grey dashed placeholders:** seals (직인), QR codes, anti-forgery barcodes and issuer logos.
- **Fictional identifiers.** Issuance numbers start with `TEST`. Companies (`테스트상사`, `가나다솔루션`), people (`박가상`, `김테스트`, `이샘플`), the university (`한국가상대학교`), and tax offices (`가상세무서장`, `가상구청장`) are invented.
- **Business numbers have the correct format and check digit**, except B10, which deliberately fails it. They are invented and may coincidentally match a real registration; the files are marked as samples.

## Folder layout

```
business/B01_all_valid/
    digital/   PDF with a real text layer (embedded-text path)
    scanned/   image-only PDF, 170 DPI, slight tilt, light noise and paper tint (OCR path)
    images/    the same documents as image files, the way people upload photos
               and scans: document 1 → .jpg, 2 → .png, 3 → .webp, 4 → .jpg …
business/B02_name_notation/ …
student/S01_all_valid/ …
formats/F01_digital_pdf/ … F16_corrupt_files/
manifest.json        answer key: every file, expected fields, expected statuses
_generator/          the scripts that produced this set
```

File names start with the set ID and the document's position in the set, e.g. `B05-3_납세증명서.pdf`.

## How to use it

1. **Pick a set.** Upload all files from **one version folder** (`digital/`, `scanned/` or `images/`) into one submission. Mixing versions is also a valid test, e.g. a digital 사업자등록증 with photographed certificates.
2. **Check the checklist condition.** If the set's `checklist_condition` in `manifest.json` names one (B07, S03, S04), configure it first. Otherwise use the default checklist for that workflow.
3. **Compare.** Compare ADVS's document types, extracted fields and status with `expected_classification`, `expected_fields` and `expected`.
4. **Record "record actual" results.** Where the expected status says "record actual", the correct result is a decision you haven't made yet. Write down what ADVS does.

### Digital vs scanned

ADVS sends **every OCR-read field to review**, regardless of confidence (audit F-010). Consequences:

- **Scanned and image sets** normally end at `REVIEW_REQUIRED`, never READY. Their expected results are the same. They test that the system abstains safely and doesn't produce confident wrong values.
- **Digital sets** go through the embedded-text path, which can reach READY or NEEDS_CORRECTION automatically. **The bug-exposing scenarios (B02, B07, B10, B11) only show their bug on the digital sets.**

### Important: regenerate before testing on another date

ADVS currently checks validity against the server's `date.today()`, not the submission date. Regenerate with the test-run date so the validity windows line up:

```bash
cd _generator
python3 gen_test_variants.py --out ../../ADVS_test_variants_new --submission-date 2026-11-20
```

Requirements: Python 3.10+, Pillow, numpy, opencv-python, python-docx, `wkhtmltopdf`, poppler-utils (`pdftoppm`), and the Noto Sans/Serif CJK KR fonts.

## Scenario summary

### Business (company 테스트상사)

| Set | Scenario | Correct result (digital) | Exposes |
|---|---|---|---|
| B01 | All consistent, all valid | READY | — |
| B02 | Name written as 주식회사 / (주) / ㈜ / trailing (주) | READY (same company) | F-002 (currently mismatch) |
| B03 | 납세증명서 belongs to 가나다솔루션 | NEEDS_CORRECTION | — |
| B04 | 중소기업확인서 business number differs (last two digits, still checksum-valid) | NEEDS_CORRECTION | — |
| B05 | 납세증명서 expired 35 days ago | NEEDS_CORRECTION | — |
| B06 | Validity ends on the submission date | READY if inclusive; depends on run date | validity reference |
| B07 | 4대보험 certificate with no validity date (original structure) | REVIEW_REQUIRED | F-001 (READY under a partial REQUIRED_FIELD checklist) |
| B08 | No 사업자등록증 | NEEDS_CORRECTION | — |
| B09 | Same 납세증명서 twice + a renamed copy | Duplicate flagged | — |
| B10 | Business number fails the check digit everywhere | REVIEW_REQUIRED | F-004 (currently READY) |
| B11 | 지방세 납세증명서 instead of 국세 | NEEDS_CORRECTION (missing national-tax certificate) | F-003 (currently classified as 국세) |
| B12 | Two 사업자등록증 with different numbers | Not READY | — |

### Student (김테스트, 한국가상대학교)

| Set | Scenario | Correct result (digital) |
|---|---|---|
| S01 | Consistent and recent (GPA 3.80/4.5) | READY |
| S02 | 재학증명서 issued 120 days ago | NEEDS_CORRECTION (default max age 90) |
| S03 | GPA 2.70/4.5 with a 3.0 threshold | NEEDS_CORRECTION |
| S04 | GPA 3.10/4.3 | Decision needed (scale handling) |
| S05 | Transcript shows another student name | Record actual |
| S06 | Departments differ | Record actual |
| S07 | 휴학증명서 and 졸업예정증명서 look-alikes | UNKNOWN, enrollment requirement unmet |
| S08 | Issue-date line blank | REVIEW_REQUIRED (must not borrow the 재학기간 date) |
| S09 | Enrollment layout with no student number | REVIEW_REQUIRED |
| S10 | Table-style transcript (GPA in a header cell) | READY |

### Formats

F01–F06 and F11 cover **all eight layouts** (사업자등록증, 중소기업확인서, 납세증명서, 4대보험 완납증명원, 재학증명서 A and B, 성적증명서 A and B). The other format sets use the 사업자등록증 and the 재학증명서.

- **F01 – F06:** digital PDF, scanned PDF, PNG, JPEG, JPEG quality 30, WEBP.
- **F07 – F09:** rotated 90°, EXIF orientation (F08a correct tag, F08b wrong tag), skewed 3°.
- **F10 – F11:** ~100 DPI, phone-photo style.
- **F12 – F14:** certificate + unrelated page, two certificates in one PDF, blank page appended.
- **F15:** TIFF, BMP, DOCX.
- **F16:** truncated PDF, 0-byte file, PNG saved with a `.pdf` extension. Expected: FAILED or rejected, never READY.

## Limitations

- **Layouts are close reconstructions, not pixel copies.** Fonts are Noto Sans/Serif CJK KR, and background emblems are a plain ring.
- **Resolution and compression were tuned to fit one 30 MiB zip.** Scenario scans and photos are 170 DPI (JPEG quality 60); format sets F02–F09 are 200 DPI. PNG, TIFF and BMP files are grayscale without added noise (PNGs in `images/` are ~150 DPI). Everything stays clearly readable; F05 (quality 30) and F10 (~100 DPI) are the deliberately degraded cases.
- **The 4대보험 layout adds a 유효기간 row** that the original sample doesn't have, so ADVS's `valid_until` field has a source. B07 keeps the original structure without it.
- **Look-alikes reuse the matching layout with a different title.** The 지방세 certificate uses the 국세 layout; 휴학 and 졸업예정 use the enrollment layout. Real versions of those documents look different.
- **Expected statuses follow the independent audit's description of ADVS rules.** Items marked "record actual" are open decisions.
- **Not generated:** HEIC (no encoder was available in the build environment). Scanned files could not be OCR-checked for Korean in the build environment. They are rasterized from the digital PDFs, whose text was verified.
- **The check-digit algorithm used is the commonly published one.** Confirm it against the official specification before relying on B10.

## Delivery

The whole set (all 299 files, all versions) is delivered as one zip, `ADVS_test_variants_ALL.zip`. It replaces every earlier zip.
