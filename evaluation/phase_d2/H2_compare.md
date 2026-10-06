### Hold-out set 2, default (no application values)

| Metric | B0 | B1 |
|---|---|---|
| digital: CORRECT / WRONG / UNRESOLVED (of 275) | 176 / 1 / 98 | 275 / 0 / 0 |
| scanned: CORRECT / WRONG / UNRESOLVED (of 275) | 219 / 0 / 56 | 259 / 0 / 16 |
| images: CORRECT / WRONG / UNRESOLVED (of 275) | 235 / 2 / 38 | 264 / 0 / 11 |
| scanned: OCR fields auto-accepted | 0 / 275 (0.0%) | 176 / 275 (64.0%) |
| scanned: false auto-accept | 0 | 0 |
| images: OCR fields auto-accepted | 0 / 275 (0.0%) | 185 / 275 (67.3%) |
| images: false auto-accept | 0 | 0 |
| digital: review burden (fields a human must confirm/supply per submission) | 5.32 | 0.8 |
| scanned: review burden (fields a human must confirm/supply per submission) | 11.64 | 4.6 (60% lower) |
| images: review burden (fields a human must confirm/supply per submission) | 11.64 | 4.24 (64% lower) |
| scanned: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 3/25 |
| images: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 4/25 |
| False READY | 0 [] | 0 [] |
| Effective (acted-on) wrong fields | ['S09/digital:S09-1_재학증명서.pdf:department'] | [] |
| READY on RECORD rows | [] | ['B06/digital', 'B09/digital', 'B09/images', 'S04/digital', 'S06/digital'] |
| Status vs expectation | {'digital': {'MISMATCH': 8, 'MATCH': 10, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}, 'images': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}} | {'digital': {'MATCH': 18, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 9, 'MATCH': 9, 'RECORD': 7}, 'images': {'CONSERVATIVE': 9, 'MATCH': 9, 'RECORD': 7}} |

### Hold-out set 2, with application values

| Metric | B0 | B1 |
|---|---|---|
| digital: CORRECT / WRONG / UNRESOLVED (of 275) | 176 / 1 / 98 | 275 / 0 / 0 |
| scanned: CORRECT / WRONG / UNRESOLVED (of 275) | 219 / 0 / 56 | 259 / 0 / 16 |
| images: CORRECT / WRONG / UNRESOLVED (of 275) | 235 / 2 / 38 | 264 / 0 / 11 |
| scanned: OCR fields auto-accepted | 0 / 275 (0.0%) | 184 / 275 (66.9%) |
| scanned: false auto-accept | 0 | 0 |
| images: OCR fields auto-accepted | 0 / 275 (0.0%) | 193 / 275 (70.2%) |
| images: false auto-accept | 0 | 0 |
| digital: review burden (fields a human must confirm/supply per submission) | 5.32 | 0.8 |
| scanned: review burden (fields a human must confirm/supply per submission) | 11.64 | 4.28 (63% lower) |
| images: review burden (fields a human must confirm/supply per submission) | 11.64 | 3.92 (66% lower) |
| scanned: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 3/25 |
| images: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 4/25 |
| False READY | 0 [] | 0 [] |
| Effective (acted-on) wrong fields | ['S09/digital:S09-1_재학증명서.pdf:department'] | [] |
| READY on RECORD rows | [] | ['B06/digital', 'B09/digital', 'B09/images', 'S04/digital', 'S06/digital'] |
| Status vs expectation | {'digital': {'MISMATCH': 6, 'MATCH': 12, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}, 'images': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}} | {'digital': {'MATCH': 18, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 9, 'MATCH': 9, 'RECORD': 7}, 'images': {'CONSERVATIVE': 9, 'MATCH': 9, 'RECORD': 7}} |

