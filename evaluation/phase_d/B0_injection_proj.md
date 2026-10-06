# Injection results — B0 injection (proj)

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `110ead2`, strategy `None`, project values `True`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 24 | 24 | 0 | 0 | 24 | 0 | 1 | 23 |
| E2-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 0 | 14 |
| E3-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 0 | 14 |
| E3-one | 44 | 26 | 26 | 0 | 0 | 26 | 0 | 1 | 25 |
| E4-one | 44 | 21 | 0 | 0 | 0 | 21 | 0 | 1 | 20 |
| E5-all | 20 | 6 | 6 | 0 | 0 | 6 | 0 | 0 | 6 |
| E5-one | 40 | 22 | 22 | 0 | 0 | 22 | 0 | 0 | 22 |
| E6-one | 4 | 2 | 1 | 0 | 0 | 2 | 0 | 0 | 2 |
| E6-one-both | 4 | 2 | 1 | 0 | 0 | 2 | 0 | 0 | 2 |
| E7-all | 24 | 24 | 24 | 0 | 0 | 24 | 0 | 2 | 22 |
| E7-one | 48 | 45 | 45 | 0 | 0 | 45 | 0 | 4 | 41 |
| E8-one | 18 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E8-one-both | 18 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E9-one | 38 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |
| E9-one-both | 38 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |

Totals: planned 428, exercised 250, effective 227.

**Totals: false auto-accept 0, false READY 0.**

