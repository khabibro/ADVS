# Safety results

P1 changed no field outcome on the frozen corpus. Every safety metric is
therefore identical to the P0 baseline, re-measured at `48e3824`.

## Independent False READY evaluation

False READY is defined **independently** of the system under test, not by
reading the system's own verdict back to itself. A submission counts as a false
READY when the frozen gold expects at least one evaluated field to be unresolved
or incorrect, and the submission reaches `READY` anyway.

| Metric | Numerator | Denominator | Rate |
|---|---:|---:|---:|
| False READY, P0 baseline | 0 | 7 | 0.000 |
| False READY, P1 tree | **0** | 7 | 0.000 |

Numerator and denominator are both reported, as required.

## Adversarial scenarios

Each was exercised; none produced a False READY.

| Scenario | Expected | Observed |
|---|---|---|
| All documents scanned, all evidence OCR-sourced | no automatic `READY` | 0 of 7 reached `READY`; all `REVIEW_REQUIRED` |
| Ambiguous GPA, several distinct values | review, not a value | `UNRESOLVED`, `needs_review` set |
| Wrong personal name at high confidence | gated | `REVIEW_REQUIRED`; policy-gated out of rule consumption |
| Missing required field | unresolved, not mismatch | `REQUIRED_FIELD_UNRESOLVED` |
| Null on both sides of a comparison | no mismatch | 0 null-derived mismatches |
| Absent validity date | no expiry | 0 null-derived expiries |
| `UNKNOWN` document | conservative | `UNKNOWN`, zero fields, `REVIEW_REQUIRED` |
| Negative assertions (values that must never be produced) | never produced | 0 violations |

## Wrong non-null values

| Metric | P0 baseline | P1 tree |
|---|---:|---:|
| Wrong non-null, on the authoritative path | 1 | **1** |
| Wrong values introduced by structural candidates | — | **0** |

The single wrong value is unchanged: a personal name from a scanned transcript at
0.917 OCR confidence, with truthful evidence and `REVIEW_REQUIRED` assessment.

**No structural candidate source is wired into the authoritative path**, so it is
structurally impossible for one to produce a wrong value in production. The
fabrication risk was found and removed *before* integration, not after.

## Hallucination detection

The scorer examines gold keys **and** machine-emitted keys. A machine field
outside the expected set is reported rather than ignored.

| Metric | P0 baseline | P1 tree |
|---|---:|---:|
| `HALLUCINATED_EXTRA_FIELD` | 0 | **0** |

Every field the pipeline emitted belongs to the extractor's supported set for its
classified document type.

## Abstention behaviour

| Case | P0 | P1 |
|---|---|---|
| Correctly abstained per gold (`VERIFIED_ABSENT`) | 2 | 2 |
| Ambiguous field left unresolved | yes | yes |

Abstention is unchanged. P1 added no path that converts an abstention into a
value.

## Resource limits

Unchanged. P1 added no render, dimension, pixel or timeout limit, and modified
no resource configuration.

| Limit | Status |
|---|---|
| Upload size, dimension, page count | unchanged |
| OCR raster budget | unchanged |
| OCR timeout, per page | unchanged |
| OCR worker slot, no terminal `OCR_BUSY` | unchanged |

## Privacy

| Check | Result |
|---|---|
| Private documents modified | 0 |
| Private documents staged or committed | 0 |
| Ground truth committed | 0 |
| Raw OCR committed | 0 |
| Absolute private paths in tracked artefacts | 0 |
| Institution names from personal documents in tracked artefacts | 0 |

A programmatic scan compared every private ground-truth value and every source
filename against all tracked P1 files; zero matches.

## Conclusion

False READY remains 0. Wrong non-null does not increase. No hallucination is
introduced. Null safety is preserved. No safety-critical criterion regressed.