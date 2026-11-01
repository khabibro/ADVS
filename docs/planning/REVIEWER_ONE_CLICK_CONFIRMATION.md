# Requirement for the reviewer queue (admin Phase 3): one-click confirmation

Source: owner decision after the real-document automation loop. Status: requirement, not implemented here (the
reviewer queue belongs to the admin app).

## Why

Some fields cannot be made safe to accept automatically, however much the extraction improves, because every plausible
OCR misreading flips a verdict or the page offers no independent evidence:

- the **issue date of a 재학증명서** (the 90-day rule: any digit confusion changes the verdict);
- a **GPA whose arithmetic is not evaluable** on the page (semester rows missing or unreadable);
- dates that are decision-robust but not individually confirmed (they carry the label "decision-robust, value not
  individually confirmed").

The owner decided that for these fields the only path is a person's confirmation. No other automatic path is added.

## Requirement

1. The reviewer sees, for the field, **the crop of the page region and the machine value** side by side.
2. **Enter confirms** the machine value as read; a different value can be typed and confirmed instead. One field, one
   keystroke in the common case.
3. The confirmation is a normal field review (`CONFIRMED` or `CORRECTED`), recorded in the audit log with reviewer,
   time, and the evidence it was made against; it is invalidated when the document or the check date changes, like any
   review.
4. Fields of this kind are marked as one-click in the queue and can be worked in a batch (all issue dates of the open
   submissions, one after another), because most submissions need only these.
5. A submission whose only blockers are one-click fields shows that in its status line ("ready after N confirmations").

## Metric (reported by the harness)

"READY after at most N staff confirmations": valid submissions whose verification issues are all field issues on
one-click fields (issue date, GPA, validity dates), with 0 wrong values among the auto-accepted rest. Computed by
`evaluation/real_docs/loop_score.py` (N = 0, 1, 2, 3, and any number of one-click fields).
