# P1 Structural Layer Decision

## Decision

The layer stays inert. The generic geometric representation is worth retaining
as a dormant experiment; the candidate-generation adapter is not approved for
production. No candidate source is activated. P1 files are retained in the
worktree for audit, per the instruction not to delete P1 artifacts.

## Component audit

| COMPONENT | CURRENT USE | BENEFIT | COST | RISK | DECISION | REASON |
|---|---|---|---|---|---|---|
| `layout/columns.py` | No authoritative-path consumer; imported by `structure.py` | Represents horizontal bands using existing OCR geometry | Additional inferred geometry and thresholds | Bands can be mistaken for semantic columns | KEEP_DORMANT | Small, generic, dependency free, isolated, and tested against spacing counterexamples; preserves raw OCR lines. Revisit only after improved observations. |
| `layout/sections.py` | No authoritative-path consumer; imported by `structure.py` | Represents explicit headings and whitespace-separated blocks | Adds page-scoped section state | Heuristic cuts can split a logical block | KEEP_DORMANT | Generic, modular and covered by heading/spacing tests. It does not create field values or change raw evidence. |
| `layout/headers.py` | No authoritative-path consumer; imported by `structure.py` | Finds aligned header/value row pairs | Alignment thresholds and inferred pairing | Geometric alignment can imply a relationship the page does not establish | KEEP_DORMANT | Useful downstream capability if observations improve, but pairing remains descriptive only and must not resolve a field without stronger evidence. No field is auto-filled by this module. |
| `layout/structure.py` and `layout/__init__.py` | No production consumer | Composes page-local derived geometry | API surface and shared maintenance | Consumers may mistake derived structure for authoritative evidence | KEEP_DORMANT | Thin composition over the three small generic helpers; page-scoped and provenance-preserving. |
| `extraction/structural.py`: `header_value_candidate` | No production consumer | Could propose a measured value from an aligned header | Candidate policy layered over geometry | Alignment plus a numeric shape does not establish meaning | REMOVE | Inert, extraction-specific, and not supported as a safe resolver by the P1 end-to-end results. Recreate later behind an explicit evidence policy if a broader corpus supports it. |
| `extraction/structural.py`: `section_scoped_values` | No production consumer; deliberately returns no candidates | Intended to scope repeated labels | Dead/speculative branch and maintenance burden | P1 probe produced wrong values when enabled | REMOVE | Its own experiment disproved the proposed rule. A permanent production function that always abstains is not useful capability. |
| `extraction/structural.py`: `issuer_block_candidate` | No production consumer; deliberately returns no candidate | Intended to identify standalone issuer text | Role markers and candidate plumbing | P1 produced plausible but wrong issuer, legend, and footer values | REMOVE | Directly contradicted by unsafe candidate probes; do not reactivate from shape or OCR confidence alone. |
| `test_p1_layout.py` | Tests the dormant geometric utilities | Guards generic geometry and counterexamples | Test upkeep | Tests may be mistaken for production validation | TEST_ONLY | Retain as exploratory coverage; tests do not establish field-level safety or production benefit. |
| `evaluation/p1_layout/*` probes and benchmark artifacts | Evaluation only | Reproducible record of P1 findings | Corpus-specific maintenance | May contain overly detailed private observations in untracked report artifacts | EVALUATION_ONLY | Not imported by production. Preserve as requested; do not stage raw OCR or private data. |

## Findings

- Repository search finds no authoritative extraction or workflow consumer of
  the structural package or `extraction/structural.py`.
- The modules introduce no new runtime dependency and do not overwrite OCR
  observations. Derived geometry remains separate from raw OCR evidence.
- The P1 benchmark reports no field-level delta: 16 correct, 1 wrong non-null,
  17 unresolved, recall 0.471, and False READY 0 for both baseline and geometry
  candidate.
- The candidate-probe evidence rejects automatic value admission. A layout
  region or plausible token is not sufficient evidence for a field.
- The geometry helpers can be reproduced from OCR boxes later at modest cost.
  The disabled extraction policy is not worth carrying as active architecture.

This is a maintenance decision, not evidence that layout is generally
irrelevant. P2 must first establish which observations are available and whether
the generic geometry has a safe consumer after OCR improves.
