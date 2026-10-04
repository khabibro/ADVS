# Safety Results

| Safety measure | P0/P1 baseline | P2 result |
|---|---:|---|
| False READY on seven real documents | 0/7 | 0/7 |
| Wrong non-null fields | 1 | 1 |
| OCR confidence treated as correctness | no | no new threshold introduced |
| Null/ambiguous handling | conservative baseline | No production code changed; all seven real docs remain REVIEW_REQUIRED |
| External OCR/cloud use | none | none |
| Private originals modified | 0 reported in P1 | Before/after fingerprint check pending |

The independent adversarial False READY suite, concurrency, multi-page and
UNKNOWN/security rechecks are still required before P2 acceptance.
