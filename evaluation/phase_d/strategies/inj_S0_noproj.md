# Injection results — S0 injection noproj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `bf0106c`, strategy `S0`, project values `False`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 42 | 42 | 0 | 0 | 42 | 0 | 4 | 38 |
| E2-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 2 | 20 |
| E3-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 2 | 20 |
| E3-one | 44 | 43 | 43 | 0 | 0 | 43 | 0 | 4 | 39 |
| E4-one | 44 | 44 | 0 | 0 | 0 | 44 | 0 | 4 | 40 |
| E5-all | 20 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |
| E5-one | 40 | 36 | 36 | 0 | 0 | 36 | 0 | 0 | 36 |
| E6-one | 4 | 4 | 3 | 0 | 0 | 4 | 0 | 0 | 4 |
| E6-one-both | 4 | 4 | 3 | 0 | 0 | 4 | 0 | 0 | 4 |
| E7-all | 24 | 24 | 24 | 0 | 0 | 24 | 0 | 2 | 22 |
| E7-one | 48 | 46 | 46 | 0 | 0 | 46 | 0 | 4 | 42 |
| E8-one | 18 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |
| E8-one-both | 18 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |
| E9-one | 38 | 32 | 32 | 0 | 0 | 32 | 0 | 0 | 32 |
| E9-one-both | 38 | 32 | 32 | 0 | 0 | 32 | 0 | 0 | 32 |

Totals: planned 428, exercised 405, effective 359.

**Totals: false auto-accept 0, false READY 0.**

