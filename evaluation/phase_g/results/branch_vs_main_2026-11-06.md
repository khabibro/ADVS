# Injection suites: branch fix/live-strictness vs main (2026-11-06)

Development data only (dev, hold-out 1, hold-out 2; hold-out 3 not run). OCR replayed from caches, FINAL_RESULTS metric definitions (scorer v2). main = 8503a72, branch = 909292c. Suites E1-E21 incl. the -both and c variants. A branch value above main would block the merge; none is above, and no suite differs in any metric.

| corpus | cases | metric | main | branch |
|---|---|---|---|---|
| dev | 1554 | wrong_confirmed | 0 | 0 |
| dev | 1554 | false_ready_decision | 0 | 0 |
| dev | 1554 | robust_wrong | 24 | 24 |
| dev | 1554 | false_auto_accept | 24 | 24 |
| dev | 1554 | false_ready | 4 | 4 |
| dev | 1554 | E19 READY | 0 | 0 |
| holdout | 1758 | wrong_confirmed | 0 | 0 |
| holdout | 1758 | false_ready_decision | 0 | 0 |
| holdout | 1758 | robust_wrong | 57 | 57 |
| holdout | 1758 | false_auto_accept | 57 | 57 |
| holdout | 1758 | false_ready | 4 | 4 |
| holdout | 1758 | E19 READY | 0 | 0 |
| holdout2 | 1740 | wrong_confirmed | 1 | 1 |
| holdout2 | 1740 | false_ready_decision | 0 | 0 |
| holdout2 | 1740 | robust_wrong | 29 | 29 |
| holdout2 | 1740 | false_auto_accept | 30 | 30 |
| holdout2 | 1740 | false_ready | 4 | 4 |
| holdout2 | 1740 | E19 READY | 0 | 0 |

Per-suite comparison: 0 differences in wrong_confirmed, false_ready_decision, robust_wrong, false_auto_accept, false_ready, READY on every suite of every corpus. The one wrong_confirmed on hold-out 2 is the known E3c-both case, identical on main.
