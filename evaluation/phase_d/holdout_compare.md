### Hold-out, default (no application values)

| Metric | B0 | B1 |
|---|---|---|
| digital: CORRECT / WRONG / UNRESOLVED (of 275) | 174 / 0 / 101 | 174 / 0 / 101 |
| scanned: CORRECT / WRONG / UNRESOLVED (of 275) | 175 / 5 / 95 | 251 / 0 / 24 |
| images: CORRECT / WRONG / UNRESOLVED (of 275) | 212 / 7 / 56 | 255 / 0 / 20 |
| scanned: OCR fields auto-accepted | 0 / 275 (0.0%) | 188 / 275 (68.4%) |
| scanned: false auto-accept | 0 | 0 |
| images: OCR fields auto-accepted | 0 / 275 (0.0%) | 195 / 275 (70.9%) |
| images: false auto-accept | 0 | 0 |
| digital: review burden (fields a human must confirm/supply per submission) | 5.44 | 4.8 |
| scanned: review burden (fields a human must confirm/supply per submission) | 11.64 | 4.12 (65% lower) |
| images: review burden (fields a human must confirm/supply per submission) | 11.64 | 3.72 (68% lower) |
| scanned: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 5/25 |
| images: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 6/25 |
| False READY | 0 [] | 1 ['B11/images'] |
| Effective (acted-on) wrong fields | [] | [] |
| READY on RECORD rows | [] | ['B06/scanned', 'B09/images'] |
| Status vs expectation | {'digital': {'MISMATCH': 8, 'MATCH': 10, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}, 'images': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}} | {'digital': {'MISMATCH': 8, 'MATCH': 10, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 8, 'MATCH': 10, 'RECORD': 7}, 'images': {'MATCH': 9, 'CONSERVATIVE': 8, 'RECORD': 7, 'MISMATCH': 1}} |

### Hold-out, with application values

| Metric | B0 | B1 |
|---|---|---|
| digital: CORRECT / WRONG / UNRESOLVED (of 275) | 174 / 0 / 101 | 174 / 0 / 101 |
| scanned: CORRECT / WRONG / UNRESOLVED (of 275) | 175 / 5 / 95 | 251 / 0 / 24 |
| images: CORRECT / WRONG / UNRESOLVED (of 275) | 212 / 7 / 56 | 255 / 0 / 20 |
| scanned: OCR fields auto-accepted | 0 / 275 (0.0%) | 195 / 275 (70.9%) |
| scanned: false auto-accept | 0 | 0 |
| images: OCR fields auto-accepted | 0 / 275 (0.0%) | 202 / 275 (73.5%) |
| images: false auto-accept | 0 | 0 |
| digital: review burden (fields a human must confirm/supply per submission) | 5.44 | 4.8 |
| scanned: review burden (fields a human must confirm/supply per submission) | 11.64 | 3.84 (67% lower) |
| images: review burden (fields a human must confirm/supply per submission) | 11.64 | 3.44 (70% lower) |
| scanned: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 5/25 |
| images: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | 1/25 | 6/25 |
| False READY | 0 [] | 1 ['B11/images'] |
| Effective (acted-on) wrong fields | [] | [] |
| READY on RECORD rows | [] | ['B06/scanned', 'B09/images'] |
| Status vs expectation | {'digital': {'MISMATCH': 6, 'MATCH': 12, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}, 'images': {'CONSERVATIVE': 11, 'RECORD': 7, 'MATCH': 7}} | {'digital': {'MISMATCH': 6, 'MATCH': 12, 'RECORD': 7}, 'scanned': {'CONSERVATIVE': 8, 'MATCH': 10, 'RECORD': 7}, 'images': {'MATCH': 9, 'CONSERVATIVE': 8, 'RECORD': 7, 'MISMATCH': 1}} |

