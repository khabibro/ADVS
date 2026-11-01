# Requirements for the applicant / reviewer UI from the real-document work

Source: owner decisions after the real-document automation loop. For the web work (Munira) and the admin Phase 3
reviewer queue. Nothing here is implemented by the backend.

## 1. Photo capture guidance (applicant UI)

The confidence floor and the second-pass veto stay unchanged; most remaining student review items are small or
distorted text on photographs. The upload screen should tell the applicant, before and after the upload:

- **Prefer the PDF** from the issuing system over a photograph (a PDF with a text layer is read exactly).
- If a photograph is unavoidable: **flat** (no curl or fold), the **whole page** in the frame, **good even light** (no
  shadow, no glare over the stamp), straight from above, and as close as the whole page allows.
- After an upload read from a photograph, show that the reading was made from a photograph and, when many fields
  need review, the same hint again with a "replace with a PDF or a clearer photo" action.

## 2. Student target for now: two clicks

A student submission is complete after staff confirmation of the **enrolment issue date** and the **GPA** (two one-click
confirmations, see `REVIEWER_ONE_CLICK_CONFIRMATION.md`). No per-semester entry by staff. The status line may say
"ready after 2 confirmations".

## 3. Later phase (separate, with its own test): applicant-entered GPA with scale

An **applicant-entered GPA (with its scale)** as an independent source for the transcript GPA: if the entered value
equals the read value (same scale), the GPA is confirmed by two independent sources; a mismatch is reviewed. This
needs its own input field, its own tests (including entered-wrong, read-wrong and both-equal-wrong cases) and a
measurement; it is not part of the current release. The applicant-name field already exists but is optional; a
what-if run with it filled in did not unlock any student submission by itself (see the automation log, round 4).
