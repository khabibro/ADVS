# ADVS — roadmap after the midterm (slide version)

The full roadmap with tasks, tests, acceptance criteria and fallbacks is `docs/planning/ROADMAP.md`; the evidence is in `evaluation/`. This page is the short version used for the "next steps" slides. Dates are conditional on the confirmed course deadlines.

Status today: a working pipeline and review flow on fictional documents; safety measured on synthetic data only (see `RESULTS.md`); the pipeline is traditional OCR → deterministic extraction and normalisation → validation → safe submission decision, with a person confirming what cannot be confirmed; not yet real-world ready.

## October (done): fix, judge, freeze, present
- Hidden PDF text is ignored and flagged; scanned `university_name` extraction fixed (21/58 → 56/58 on scans); D3 internal confirmation merged; hold-out set 3 judged once.
- Present from tag `midterm-demo-v3.1`; rehearsal 3× the morning of the talk.
- Documents, slides and results traceable to evidence, with n and uncertainty for safety claims.
- Confirm the exam date and the presentation format (5 min + 2 min Q&A in the course deck).

## November: measure on real captures, finish the product
1. **Physical corpus** (printed fictional documents, photographed and scanned) with an answer key; baseline report with denominators and bounds.
2. Reviewer queue and admin checklist screen; real-document pilot (read-only, counts only); PostgreSQL and concurrency tests.
3. Review the owner-accepted residual risk (a misread repeated identically on several documents).
4. *Optional:* photo quality gate with perspective correction.

## December: final system
- Login and per-project access, privacy (logs, retention, deletion), audit log; optional National Tax Service registry check if the mentor agrees.
- End-to-end tests, deployment instructions, final evaluation report with honest limits.
