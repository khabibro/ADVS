# Security and upload regression (F-01, F-17)

## Hostile upload probes, live HTTP

Ten probes were sent to the real upload endpoint of a running server.

| Probe | HTTP | Error code | Assessment |
|---|---|---|---|
| Empty file | 400 | `EMPTY_FILE` | rejected |
| PDF extension, PNG bytes | 400 | `INVALID_FILE_TYPE` | rejected — bytes, not extension, decide |
| Text bytes declared as PDF | 400 | `INVALID_FILE_TYPE` | rejected |
| Path traversal filename `../…` | 201 | — | accepted, sanitised (below) |
| Double extension `x.pdf.exe` | 400 | `INVALID_FILE_TYPE` | rejected |
| Disallowed extension `x.exe` | 400 | `INVALID_FILE_TYPE` | rejected |
| Real PDF sent as `image/png` | 201 | — | accepted, processed as PDF |
| Oversized image dimensions | 400 | `CORRUPT_DOCUMENT` | rejected |
| Encrypted PDF | 400 | `CORRUPT_DOCUMENT` | rejected |
| 31-page PDF | 400 | `TOO_MANY_PAGES` | rejected |

The two 201 responses are correct behaviour, not gaps:

- **Traversal filename.** Accepted, then verified: exactly one file created, the
  stored name contains no path separator and no `..`, nothing was written
  outside the storage root, the stored bytes are exactly the uploaded bytes, and
  the document classified correctly from its content.
- **Mismatched declared content type.** ADVS deliberately trusts the bytes on
  disk over the client-declared extension and content type. A PDF announced as a
  PNG is stored and processed as the PDF it is.

Rejected uploads are rejected with a typed error code and leave no partial file
behind.

## F-01 upload resource validation

### The original finding

Storage projected the OCR render resolution onto the PDF page box when deciding
whether an upload was acceptable. A legitimate PDF whose page box is about 3× A4
was rejected with `PIXEL_BUDGET_EXCEEDED` purely because OCR rendering would have
produced a larger raster. Storage security and OCR resource policy were the same
decision, so a valid document was refused for a downstream concern.

### Current behaviour

Storage now validates the **actual PDF page geometry in points**, independent of
any render setting, and applies the image dimension budget only to real raster
inputs. The raster budget lives where the raster is produced. All seven corpus
documents upload successfully.

### A P0 regression found and fixed during this validation

Separating the budgets was necessary but not sufficient, and the P0 work had
introduced a new false rejection:

- `fa38ef8` added a per-page pixel budget of 25,000,000 and applied it to the
  page box at the configured render DPI of 288.
- The corpus document with a 1117×1408 pt page box carrying a **72 DPI** scan
  rendered to 4468×5632 = 25,163,776 px, which is **0.65 % over** the budget.
- It was rejected with `RESOURCE_LIMIT` and failed processing in 14 ms — a
  document the PRE-P0 pipeline had processed successfully.

The underlying point is that the budget bounds decode cost, not document
validity, and that rendering such a page at 288 DPI is a 4× upsample of a 72 DPI
source. It multiplies memory and OCR time while adding no evidence.

The fix computes, per page, the render scale the page's own embedded raster
justifies, and applies it **only when the configured scale would exceed the
budget**. It never renders below the source resolution, never touches a page
that fits the budget, and never downsamples a vector page that has no source
resolution. The chosen scale and the reason are recorded in the page transform
metadata, so the decision is auditable after the fact.

Measured on the corpus:

| Document | Page box | Source resolution | Scale before | Scale after | Raster before | Raster after |
|---|---|---|---|---|---|---|
| DS-001 | 1117×1408 pt | 72 DPI | 4.0 | 1.5 | 25.16 MP (over budget) | 3.54 MP |
| DS-004 | 595×842 pt | 200 DPI | 4.0 | 4.0 | 8.02 MP | 8.02 MP |
| DS-007 | 595×842 pt | 200 DPI | 4.0 | 4.0 | 8.02 MP | 8.02 MP |

The two documents that already fit are **bit-for-bit unchanged**. The fix is
general: it depends only on the relationship between a page's declared box and
its embedded raster, and encodes no sample, dimension or filename.

Three regression tests were added covering the rejection, the
must-not-downscale case, and the vector-page case.

## F-17 comparison semantics

Comparison was exercised through the real submission verification engine, not by
calling a string helper in isolation.

| Case | Value type | Expected match | Actual |
|---|---|---|---|
| Safe whitespace difference | string | yes | **yes** |
| Safe whitespace difference | identifier | yes | **yes** |
| Safe punctuation difference | identifier | yes | **yes** |
| Identical value | string | yes | **yes** |
| Genuinely different value | string | no | **no** |
| Similar but not identical | string | no | **no** |
| Punctuation retained for names | string | no | **no** |
| Case difference | identifier | no | **no** |

End-to-end through the engine:

| Scenario | Result |
|---|---|
| Same company, whitespace formatting differs | no mismatch |
| Same company, a field null on **both** sides | **no mismatch**, status `REVIEW_REQUIRED` |
| Genuinely different company names | `INFORMATION_MISMATCH`, status `NEEDS_CORRECTION` |
| `valid_until` absent | **no expiry issue** |

- **Null-derived mismatch: 0**
- **Null-derived expiry: 0**
- A null on both sides is never read as a mismatch, and never as agreement.
- There is no fuzzy identity matching: a similar name is not the same name.

### Documented asymmetry between scopes

The two validation scopes normalise differently, and this is recorded rather
than changed:

| Value | Document scope | Submission scope, `string` |
|---|---|---|
| `ABC-industries Co., Ltd.` | `abcindustriescoltd` | `ABC-industriesCo.,Ltd.` |
| `주식회사 (주)` | `주식회사주` | `주식회사(주)` |
| `Abc Industry` | `abcindustry` | `AbcIndustry` |

Document-scope comparison lowercases and strips all non-word characters;
submission-scope `string` comparison removes whitespace only, and
`identifier` comparison strips everything non-alphanumeric but preserves case.

This is a deliberate conservatism: stripping punctuation from a name is lossy,
so it is available only where a workflow explicitly declares the field an
identifier. Both behaviours are safe in the direction that matters — a
disagreement produces a review, never a false `READY`. Unifying the two scopes
is a design decision for a later phase, not a P0 fix, and is listed under P1.

## Gate results

| Gate | Result |
|---|---|
| `git diff --check` | PASS |
| `pnpm env:validate` | PASS |
| `pnpm security:audit` | PASS |
| Hostile upload probes | 8 of 10 rejected; 2 accepted correctly, both verified |
| Path traversal escape | none |
| Partial-file residue on rejection | none |