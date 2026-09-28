# Phase 7 confidence and review evaluation

Phase 7 uses `evidence-policy-v1`, an operational evidence-sufficiency policy. OCR confidence is
recognition confidence and is never described as semantic correctness, document validity, or a
submission pass probability. The policy uses field-level supporting evidence, not page averages.

The read-only mentor dataset contains 38 controlled synthetic PDFs. Thirty-two supported PDFs are
in scope and six local-tax PDFs are excluded. The evaluator stores no PDFs, filenames, OCR text,
names, business numbers, student IDs, or corrected values. The mentor data has no complete
field-level answer key, so the distributions and routing rates are not accuracy metrics.

`confidence_summary.json` contains privacy-safe observations and descriptive distributions by
document type, important field, and source kind. `evidence_policy.json` records the policy and its
limitations. `mentor_review_routing.json` compares Phase 6 and Phase 7 scenario outcomes and
reports review burden and automatic evidence sufficiency.

Human reviews are facts about evidence, not approval decisions. Machine extraction remains
unchanged. A current confirmation uses the machine normalized value; a correction is normalized by
the same canonical field functions; rejection and cannot-determine make the effective value
unavailable. Verification is invalidated after a review and must be explicitly rerun. Reprocessing
conservatively marks every current review stale, even if bytes later prove identical.

Review endpoints currently accept a free-form reviewer label under application-level access
assumptions. It is not authenticated identity. The service uses a one-current-review database
constraint; ordinary sequential replacement is last-write-wins, while genuinely concurrent
replacement may be rejected by that constraint. No distributed locking or multi-reviewer approval
is implemented. Review outcomes are pre-verification assistance only and carry no legal or
official approval semantics.
