# Benchmark protocol

## Fairness controls

Every candidate was measured on **identical inputs**. To make that true, OCR was
run **once** and the observations cached; every candidate then replayed the same
observations.

| Control | How it was held fixed |
|---|---|
| Documents | the same 7 files, by SHA-256 |
| Gold | the same frozen file, SHA-256 `ff4b226c…` |
| Denominator | 7 files, 34 evaluated fields, frozen before any output was read |
| Evaluator | the same `run_round2.py` and `summarise.py`, both unedited |
| Observations | replayed from one cache, so text, boxes and confidences are byte-identical across candidates |
| Preprocessing | unchanged; no candidate altered the render pipeline |
| Hardware | same machine, CPU only, same process |
| Authoritative path | untouched throughout; candidates were probed out-of-band |

This matters because the candidate comparison is between *structural layers*, not
between OCR runs. Re-running OCR per candidate would have confounded recognition
noise with structural effect.

## Two measurement tracks

**Track 1 — end-to-end, frozen scorer.** Each candidate's output was scored with
the unmodified P0 runner and summariser. This is the only track that counts for
acceptance.

**Track 2 — out-of-band candidate probe.** For each proposed candidate source,
the value it *would* produce was computed and compared against the frozen gold,
without touching the authoritative path. This is a safety probe: it reveals
fabrication before anything is wired in. It is why two sources were disabled
rather than shipped.

Both tracks used the same cached observations.

## What was measured

| Dimension | Instrument |
|---|---|
| Field outcomes | frozen runner + summariser, Track 1 |
| Classification | frozen runner |
| False READY | frozen summariser safety block, plus an independent check |
| Wrong non-null | frozen summariser safety block, plus Track 2 fabrication probe |
| Structural quality | `structural_probe.py`: columns, sections, header/value pairs per page |
| Latency | per-document process time from the runner; per-page layout time for Architecture C |
| Memory | not measured; recorded as a limitation |

## Threshold sensitivity

Constants were **swept, not chosen**. For column inference, a grid of
`COLUMN_GAP_RATIO × MIN_COLUMN_WIDTH_RATIO` was run over all seven documents and
scored against manually established ground truth for which pages are genuinely
tabular (P1-001, P1-003, P1-004) versus which are key/value forms (P1-002,
P1-005, P1-006, P1-007).

| gap ratio | min width | columns per page | classification correct |
|---:|---:|---|---:|
| 1.2 | 0.04 | 10, 2, 16, 16, 3, 3, 2 | 7/7 |
| 2.0 | 0.08 | 6, 1, 11, 10, 3, 3, 2 | 7/7 |
| 2.5 | 0.12 | 5, 1, 7, 8, 3, 3, 1 | 7/7 |
| 3.0 | 0.18 | 4, 1, 5, 6, 2, 2, 1 | 7/7 |

The table/form decision is **insensitive** across the whole grid: 7/7 correct
everywhere. The chosen point (2.0 / 0.08) sits mid-grid rather than at an edge,
and a regression test asserts that ordinary label spacing does not create a
column. A counterexample guard pins the threshold as structural rather than
fitted.

## Guarding against tuning to one sample

Three adversarial tests were written specifically to fail if a constant had been
fitted to these seven documents:

1. letter-spaced labels must not become columns,
2. a parenthetical sub-caption must not become a section heading — this one
   **did** catch a real defect during development, splitting a business
   certificate into three phantom sections,
3. a value row that is not column-aligned must produce no header/value pairing.

## Honest limitations of this protocol

- **Seven documents.** Enough to compare architectures and to catch
  regressions; not enough to estimate accuracy.
- **One OCR run per document.** Recognition variance between runs is not
  characterised, so a candidate's effect is measured against a fixed recognition,
  not a distribution.
- **No born-digital, no multi-page, no rotation, three document types absent.**
  Those paths are untested here.
- **Memory not measured.**
- **Table recognition for Architecture C was not benchmarked**, because it
  cannot be executed in this environment. Its rejection rests on the documented
  absence of Korean training data plus the recognition-side finding, not on a
  measurement of its Korean accuracy. That is a real gap in the comparison and is
  stated as such.