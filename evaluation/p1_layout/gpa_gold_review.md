# Transcript GPA Gold Review

## Historical assumption

The frozen evaluation note treats the first reading-order occurrence of
`평점평균` as the overall GPA. P1 already recorded that this assumption was
unverified. Reading order is not semantic evidence.

## Visible evidence

Both transcript pages were inspected directly. One contains repeated semester
sections, each with its own GPA and percentage, but no visible cumulative marker
that selects one of those semester values as the overall value. Its GPA gold is
therefore **AMBIGUOUS**. The other contains repeated semester sections and a
separate summary block labeled by total acquired credits, with a GPA and
percentage in that summary. The first semester GPA and the total-credit summary
are visibly different. The total-credit label and bounded summary row establish
which value is cumulative; no external university convention is needed.

## Assessment

- Is “first `평점평균` is overall” justified? **No.** It is contradicted by the
  semester headings and the separate total-credit summary.
- Transcript with no cumulative marker: **AMBIGUOUS**. Several plausible
  semester GPA values are visible and the document does not identify one as
  overall.
- Transcript with an explicit total-credit summary: **KNOWN_VALUE**. Its
  semantic overall value is the GPA adjacent to that summary; the private value
  is intentionally not copied into this tracked record.
- The corrected annotations are stored in ignored runtime
  `evaluation/backend_round2/work/ground_truth_v2.json` (SHA-256
  `218ac059ed117403022bbae6035eb056613d26e46180a7670bb2201626e17107`). The
  frozen v1 file remains unchanged.

## Evaluation effect

The existing v1 gold and historical P0/P1 metrics remain frozen and unchanged.
The P1 record of 0.471 recall remains the result under that historical scorer.
A corrected semantic gold requires a separately versioned gold_v2: mark the
unscoped repeated-semester case ambiguous and use the explicitly cumulative
summary for the other transcript. Run a new scorer against that version. It may
change the denominator and field outcome; it must not be reported as a change to
historical P0 recall. Ground-truth values remain in an ignored runtime location.
Against v2, the same P2 run scores 16 correct, 1 incorrect non-null, 16
unresolved, and 8 not evaluated; recall is 0.4848. This is a gold/scorer
denominator change, not an OCR improvement.

## Limits

This review establishes one visible cumulative figure and one ambiguous
repeated-semester case. It does not make GPA extraction generally safe and does
not authorize first/last, largest/smallest, or reading-order selection. Until
gold_v2 exists, the frozen benchmark continues to score against gold_v1 and the
production system should abstain when its field-level intent is ambiguous.
