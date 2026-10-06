# ADVS Hold-out Test Set 2

**Do not use this set for development, debugging or tuning.** It is only run at the end of a phase to judge the result, and only aggregate numbers are reported. If fixes are tested against it while they are being made, it stops measuring anything.

## What is different from the main test set

The main test set (`test_variants`) is the development set. This hold-out set uses the same document structures and the same scenario IDs (B01–B12, S01–S10), but:

- **New fictional values.** Company 온누리샘플 / 다온테스트, representative 한가상, student 최견본 at 가상국립대학교 (IT대학 컴퓨터학부), and new business numbers, student numbers and dates.
- **Submission date 2026-10-19.** Fix the harness clock to this date.
- **Layout jitter.** Field positions shift by up to about 2.5 mm and font sizes vary by ±4%. About half the documents use a serif font.
- **Shuffled text layer.** The digital PDFs store their text in a random order, as a different PDF generator would. The visual layout is unchanged.
- **Overlapping stamps.** A generic red "TEST 견본" stamp overlaps the issuer line, the way real seals overlap printed text. It does not imitate any real seal.
- **Three extra near-miss scenarios:**
  - **H13:** the company name on one certificate differs by one character (온누리샘플 / 온누리샘풀). Expected NEEDS_CORRECTION, never a match.
  - **H14:** three certificates carry a checksum-valid business number with two adjacent digits swapped. They agree with each other but not with the reference, and must not outvote it.
  - **H15:** the transcript's student number differs by one digit. It must not count as corroboration.
- **Fewer format sets:** F02, F04, F07, F09, F11, F12, F13, F16.

**279 files.** The answer key is `manifest.json` (`"holdout": true`). Generator: `_generator/` (`--profile holdout2`).

## Privacy and marking

Everything is fictional. Every page is marked `TEST SAMPLE · 테스트용 견본 · 법적 효력 없음 · HOLD-OUT-2`, and seals, QR codes and barcodes are placeholders or the generic test stamp. A check against the original seven samples found no matching names, numbers or addresses.

## Relation to hold-out set 1

Hold-out set 1 was used for the Phase D judgement, so from now on it counts as development data. This set replaces it as the unseen hold-out. Its fictional values share nothing with the development set or hold-out set 1.
