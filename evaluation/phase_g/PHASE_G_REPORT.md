# Phase G report — close the known shortcomings and test them

Date: 2026-10-11. Presentation: 2026-10-15. Demo build: **`midterm-demo-v3`** (the deck matches v3). Evidence labels: every number below comes from a file named next to it.

## 1. Git identity switch and the Phase F commit

| | before | after |
|---|---|---|
| `user.name` / `user.email` (local, all worktrees) | Munira / munira@knu.ac.kr | KHABIBILLO / khabibillionaire@gmail.com |
| `origin` | `git@github-munira:khabibro/ADVS.git` | `git@github-khabibro:khabibro/ADVS.git` (`ssh -T` greets `khabibro`) |

The auto-mode safety classifier flagged one later command as a "remote repoint" although it did not touch remotes; the switch itself had already been done as you instructed, and nothing was worked around.

Phase F files were committed in four logical commits on `phase-f/docs` (authored by KHABIBILLO), merged into `main` with `--no-ff` (`95ef2da`) and pushed. Before that, the deck pages Phase F had not viewed (9–12, 14, 15, 17) were rendered and checked; one layout defect (slide 15: the table overlapped its footnote) was fixed, nothing else.

Earlier history keeps its authorship and its older commit-message lines (the D3 branch commits made in a previous session carry a `Co-Authored-By: Claude` trailer); history was not rewritten. **No Phase G commit has an AI attribution line.**

## 2. Fixes (`phase-g/fixes`)

### G-1 — hidden PDF text is no longer trusted (D-1)

- **Cause:** `PdfProcessor` returned every text object of a PDF, including invisible ones; the pipeline treated the page as an exact digital original.
- **Change:** new `preprocessing/text_layer.py`. Text is kept only if a person can see it, judged two independent ways: the PDF's own flags (render mode 3, zero opacity, font under 2 pt, outside the page) and a render test (page drawn with and without all text: text that changes no pixel under its own box is not visible; text whose colour equals the page behind it, measured on the text-free render, is hidden). Pages with unreadable font encodings, mostly pictures, or two different texts on top of each other, and pages whose hidden text carries a date or number, are read by OCR instead. If hidden dates or numbers are not on the page as the OCR reads it, the document gets the review issue **`TEXT_LAYER_MISMATCH`** and the submission is held at 확인 필요 (never 제출 가능). Producer/creator/signature fields are stored as informational provenance only. An OCR "searchable PDF" of a scan is treated as OCR.
- **Files:** `preprocessing/text_layer.py` (new), `processor.py`, `ocr/models.py`, `services/processing.py`, `services/document_validation.py`, `services/verification.py`, `validation/submission.py`, web copy `copy.ts`.
- **Tests (`tests/test_phase_g_text_layer.py`, 17):** the probe case, invisible text, white on white (also over other text), tiny and off-page text, text under an opaque image, unmapped fonts, hybrid pages, overlapping texts, provenance, the audit comparison, and an end-to-end API test (hidden date → OCR used, mismatch issue, never READY). Run against the old code they fail (the module does not exist; the Phase F probe shows the old behaviour).
- **Found by the manipulation suite, fixed:** white text drawn *over other text* passed the render test (198 of 235 copies leaked); the contrast check was added and re-measured.
- **Commits:** `51fc636`, `0355cdb`, `a885ee1`.

| Check (final code) | Result | Source |
|---|---|---|
| Manipulated copies of every development digital PDF (hidden mode 3, white on white, tiny; 235 each), effective against a plain extractor | **705 of 705 handled**: hidden date/number never in the text read, page never trusted (95 % upper bound for a miss 0.43 %); off-page text is dropped by the PDF library itself (0 effective) | `evaluation/phase_g/results/pdf_manipulation_suite.md` |
| Same manipulations through the real API with OCR (B01 submission, one document replaced, 12 submissions + control) | **0 of 12 reached 제출 가능** (all 12 at 확인 필요 with `TEXT_LAYER_MISMATCH`); the unmanipulated control stayed 제출 가능. n is small: the bound at n=12 is 25 %. | `pdf_manipulation_pipeline.md` |
| False-alarm rate on normal digital PDFs | **0 of 307** pages flagged untrusted, text identical to the old extraction (95 % upper bound 1.0 %) | `false_alarm_digital_pdfs.txt` |

### G-2 — `university_name` on scans and photos (D-3)

- **Causes (from cached OCR, development data only):** (1) the issuer line is read fused or damaged: `…대학교총장` without the space, `총창`, or only `총` (a seal covers the title); (2) letter-spaced print with mixed token sizes (`가 나 다라 대 학 교 총`) kept internal spaces; (3) a seal split the name into `…대학` and a separate `교` box; (4) a remaining 3 cases where OCR read `교` as `(` or `!` — left unresolved on purpose (a person confirms; the code never completes a name by guessing).
- **Change (`extraction/base.py`, general):** accept the title in fused/truncated/misread forms, join letter-spaced tokens when at least half are single syllables, and rejoin `…대학` + `교` only when the two boxes are on one row, left to right, with a gap no wider than a line. No university name is in the code (grep of the app code for every name used in the data sets: none).
- **Tests (`test_phase_g_university_name.py`, 12):** invented names that are in no data set; they fail on the old code (5 of 12) and pass now; negative cases (other row, far away, two universities, department text).
- **Before → after, development data, replay of cached OCR (`results/university_name_before_after.txt`):** scans **21/58 → 56/58** (Wilson 95 % 0.88–0.99), photos **24/58 → 57/58** (0.91–1.00), **0 wrong values** both before and after. Final pipeline run: hold-out 3 **9/20 → 19/20** (scans) and **11/20 → 20/20** (photos), main baseline vs integrated.
- **Commits:** `4287ce3`, `6b12591`.

#### The merge conflict between G-2 and D3 (resolved on `phase-g/integrated`)

D3 (`phase-d3/internal-automation`) had its own fix for the glued 총장 line in the same function (`issuer_university_candidate`). Both sides changed the lines that turn the matched tokens into a name:

```
<<<<<<< HEAD (phase-g/fixes)                      ======= (phase-g/d3)
tokens = _ISSUER_TITLE_TAIL_RE.sub("", collapsed).split()      tokens = collapsed.split()
# Letter-spaced print …                                        if tokens and tokens[-1] == "총장": tokens = tokens[:-1]
spaced = sum(len(t) == 1 for t in tokens) * 2 >= len(tokens)   elif collapsed.endswith("총 장"): tokens = tokens[:-2]
name = "".join(tokens) if spaced else " ".join(tokens)         elif tokens[-1].endswith("총장") and len(tokens[-1]) > 2:
                                                                   tokens[-1] = tokens[-1].removesuffix("총장")
                                                               name = "".join(tokens) if all(len(t)==1 …) else " ".join(tokens)
```

Resolution: **kept the Phase G side**. It is a superset: it handles the fused `…대학교총장` (D3's case), `총창`, truncated `총`, and mixed-size letter spacing, with one regex for the title tail instead of three special cases. Result: the **Phase G tests (29 in the two Phase G files) and all D3 tests pass together** — 118 tests that touch issuer/총장 handling (`test_phase_d3_internal.py`, `test_phase_d_items.py`, `test_phase_c_extraction.py`, …) pass, and the full backend suite is 613 passed.

### G-3 — other audit defects

No further code fix was made; each was triaged:

| ID | Decision | Reason / target |
|---|---|---|
| D-2 (scans rarely decided without a person) | addressed by D3 (below); by design | policy, owner-accepted |
| D-4 (OCR confidence does not separate right from wrong) | design constraint | already floor-only in the policy |
| D-5 (no real or physical data) | **deferred** | cannot be fixed in code; physical corpus, November |
| D-6 (no HEIC, perspective correction, quality gate) | **deferred** | a feature with new dependencies; optional, November, needs the physical corpus to be measured |
| D-7 (OCR ~16 s/page, synchronous) | **deferred** | background jobs, December |
| D-8 (same file twice makes two rows) | **deferred** | low; the check reports a notice; UI/API contract, November |
| D-9 (same finding reported by two rules) | **deferred** | low; `/overview` (what the UI reads) already de-duplicates; changing `/verify` would change the scored issue lists |
| D-10 (D5 look-alike attributed to the 국세 requirement) | **deferred** | low; the scorer accepts the actual status |
| D-11 (SQLite only, no login, admin shell) | deferred | December |
| D-12 / the 13 documentation conflicts | **fixed** (G-4) | |

### G-4 — documentation conflicts

Fixed, with code as the source of truth: `layout/` is "structural layout derived from OCR geometry" and `text_layer.py` is in the module map (`ARCHITECTURE.md`); the test-set README no longer says validity is checked against `date.today()` (the API takes an explicit evaluation date); `docs/domains/ocr.md` and `README.md` describe the visible-text rule; `TECHNICAL_AUDIT.md` §10 records the status of every defect; `RESULTS.md`, `ROADMAP.md`, `testing.md`, `DOCUMENTATION_INDEX.md`, `evaluation/README.md`, `metrics.csv`, `slides_sources.md` carry the v3 numbers. Two conflicts stay open for you (not for code): the course deck says 5 min + 2 min Q&A and a first midterm on 10/22 (the deck is built as a 5-minute main path plus appendix), and the real Projects documents were not found.

## 3. D3 finished (`phase-g/d3`)

The branch already contained the internal confirmations (GPA arithmetic, validity date pairs, value printed twice, scale), decision-robust acceptance, decision-relevant blocking, stamp-aware second-pass reading, the scanned 사업자등록증 company name, constrained candidate repair (proposal only, never confirms) and the calibration/learning-loop reports. Phase G merged `main` into it (two conflicts, resolved by keeping both fields: `decision_relevant` and `used_by_rules`), and adapted the demo:

- D3 makes the clean scan **D6 reach 제출 가능 with no reviewer** (the reason the earlier merge attempt was stopped). Demo scenario **D9** (scanned student documents S01) still genuinely needs a person: the two 발급일 values have no independent confirmation; the reviewer confirms both, then 제출 가능. `demo_scenarios.py`, `demo_rehearsal`, the Playwright tests, `demo_screenshots.mjs` and `DEMO_SCRIPT.md` follow (D1–D9). The frozen tags are unaffected.
- **Development-data gates (final code):** 0 false 제출 가능 in all three corpora; 0 false auto-accepts on single-error injections; review fields per submission 3.73 / 3.09 (dev), 4.16 / 3.52 (hold-out 1), 3.84 / 3.72 (hold-out 2) — v2 build: 7.23 / 6.59 (`results/gate_summary_dev_final.md`).
- **Owner-accepted residual (E3c-both / H14):** documented, no special-case code. It reproduced exactly once on development data (hold-out 2, 1 false auto-accept and 1 false 제출 가능 of 1,523 injections); it did **not** occur on hold-out 3.

## 4. Integration and the single hold-out 3 judgement

`phase-g/integrated` = `main` + `phase-g/fixes` + `phase-g/d3` (full gates after each merge). Gates on development data (final code): backend 613 passed, ruff, format, mypy clean; web lint, typecheck, build clean, 108 unit tests; Playwright 22 tests: 15 pass (the 7 skipped need real mentor PDFs via `MENTOR_DIR`, deliberately not set), axe included; `make demo-rehearsal` **3 of 3 passes** (D1–D9, web, admin, browser smoke test).

**Hold-out 3 was run once**, with `ADVS_FINAL_JUDGEMENT=1`, with the frozen scorer `score_v2.py` sha256 `49674a9c…2ad2594`, injection suites E1–E18 (Phase D `a81e4ef2…`, D2 `08229da0…`, D3 `968e4c1a…`). Baseline = main's application code (`95ef2da`) under the integrated harness (the same combination reproduces main's recorded development numbers exactly); candidate = `phase-g/integrated` at `d0177c7`. Files: `evaluation/phase_g/final/`. **Notes on honesty:** a raw OCR capture of hold-out 3 had been logged on 2026-10-06 (never scored); its OCR cache was reused (OCR output does not depend on the code under test). Three launch attempts of the session aborted before opening any hold-out data (an argument-parsing error, then a missing `manifest.json` in the baseline worktree); no setting was changed after seeing results. The hold-out access log is committed.

| Hold-out 3 (judged once) | main baseline | integrated |
|---|---|---|
| False 제출 가능 (submissions whose correct status is not READY, per input type, n=14 each) | 0 / 14 (bound 21.4 %) | **0 / 14** (bound 21.4 %) |
| Wrong values | 0 | 0 |
| Digital fields correct | 274 / 275 | 274 / 275 (the same student name on a layout with no student number; not a regression) |
| Scan fields correct | 257 / 275 (93.5 %) | **268 / 275 (97.5 %)** |
| Photo fields correct | 264 / 275 (96.0 %) | **273 / 275 (99.3 %)** |
| `university_name` scans / photos | 9/20, 11/20 | **19/20, 20/20** |
| Review fields per submission, scans / photos | 7.68 / 7.32 | **4.28 / 4.08** |
| Scanned submissions decided without a person | 1 / 25 | 2 / 25 |
| Injections E1–E18: false auto-accept / false READY | n/a (baseline harness has no E13–E18) | **0 / 0 of 1,525** (bound 0.20 %) |
| H13 / H14 / H15 (digital / scan / photo) | NEEDS_CORRECTION / REVIEW_REQUIRED / REVIEW_REQUIRED, never READY | the same statuses, never READY; review fields 8 → 4 (H13, H14), 11 → 11 (H15) |

One scanned enrolment certificate is misclassified on hold-out 3 in both baseline and candidate.

## 5. Merge gates (`phase-g/integrated` → `main`)

| Gate | Result |
|---|---|
| 0 false 제출 가능 on development data, hold-out 3 and all injections | **Met, with the one owner-accepted exception:** 0 on dev, hold-out 1, hold-out 3 and hold-out 3 injections; **1 false 제출 가능 / 1 false auto-accept in the 1,523 hold-out 2 injections (the H14 case)**, exactly the residual you accepted |
| 0 false auto-accepts on single-error injections | Met (0 in all four suites; the only one is the H14 case above) |
| PDF manipulation tests: hidden text never trusted, never 제출 가능 | Met (705/705; pipeline 0/12 READY) |
| Digital extraction still 100 % | Met on development data (790/790); hold-out 3 274/275, identical to the baseline |
| `university_name` improved on development data and not worse on hold-out 3 | Met (56/58, 57/58; hold-out 3 improved) |
| Backend suite, ruff, format, mypy | Met (613 passed) |
| Frontend lint, typecheck, build, unit tests | Met (108 passed) |
| Playwright, axe | Met (15 run, 0 failed; 7 skipped by design) |
| `make demo-rehearsal` 3× | Met (3 of 3) |

## 6. Presentation tag and deck

The gates passed on 2026-10-11, well before the 2026-10-13 18:00 deadline: **present from `midterm-demo-v3`** (superseded: present from `midterm-demo-v3.1`, the same code after the OCR-only cleanup). `DEMO_SCRIPT.md` is v3 (D1–D9); the v2 script is `DEMO_SCRIPT_v2.md`; screenshots are in `docs/midterm/screenshots_v3/` (1280×720 with the review and upload flows, 1920×1080, 390×844). `midterm-demo-v2` and `midterm-demo-2026-10-14` were not moved.

Deck changes (`docs/midterm/ADVS_midterm.pptx`/`.pdf`, 18 slides, re-rendered; every changed slide checked visually): the date is **2026-10-15** (footers; it said 10-14); scan/photo accuracy, injections, review burden, the limits slide (university name and hidden-text gaps now closed; hold-out 3 judged once), approach table, protocol baselines and the plan/limits appendix carry v3 numbers, each traced in `slides_sources.md`; D9 replaces D6 as the human-review example. (A later cleanup on 2026-10-11 aligned the deck, the roadmap and the documents with the OCR-only scope decision; see §7.)

## 7. Scope decision (2026-10-11)

The owner decided that the MVP uses traditional OCR only. The second-reader experiment that Phase G had run in isolation was removed from the active project: its code, results, documentation, roadmap entries and deck content. The retained direction is traditional OCR → deterministic field extraction and normalisation → validation and cross-document checks → safe submission decision, with a person confirming uncertain or conflicting values. The Phase G fixes, D3 and the hold-out 3 judgement above concern that pipeline and are unchanged.

## 8. Remaining risks

1. All data are synthetic and clean: no claim about real or physical documents (D-5), no authenticity claim. 2. The H14 residual (1 false 제출 가능 in the 1,523 hold-out 2 injections). 3. Hold-out 3 is now used up as a judgement set; a new one is needed. 4. The deployment uses a new text-layer stage (render comparison per PDF page; tens of milliseconds, measured on the synthetic corpus only). 5. Two course-schedule conflicts (deck length/date) need a confirmation from the course. 6. The demo needs the OCR model warm-up and about 90 s for the two scanned scenes at `make demo-reset`.

## 9. Reproduce

```bash
git checkout midterm-demo-v3.1 && make demo-reset && make demo-rehearsal           # demo and rehearsal
cd apps/api && PYTHONPATH=. pytest -q                                              # 613 tests
evaluation/phase_g/scripts/dev_gates.sh F <main checkout>/evaluation <out-dir>      # development-data gates (OCR replayed from caches)
python evaluation/phase_g/scripts/gate_summary.py <out-dir> F dev holdout holdout2
cd apps/api && PYTHONPATH=. python ../../evaluation/phase_g/scripts/pdf_manipulation_suite.py <synthetic dir>
python evaluation/phase_f/scripts/denominators.py --phase-g                        # denominators and bounds
cd apps/api && PYTHONPATH=. python ../../evaluation/phase_g/scripts/university_replay.py --data-root <main checkout>/evaluation
# hold-out 3 (once; the set is used up): evaluation/phase_g/scripts/final_judgement.sh
```
