# ADVS — roadmap after the midterm (slide version)

The full roadmap with tasks, tests, acceptance criteria and fallbacks is `docs/planning/ROADMAP.md`; the evidence is in `evaluation/phase_f/`. This page is the short version used for the "next steps" slides. Dates are conditional on the confirmed course deadlines (the course deck lists 10/22, 11/19 and 12/10; the master plan assumes 10/14).

Status today: a working pipeline and review flow on fictional documents; safety measured on synthetic data only (see `RESULTS.md`); no LLM or vision-language model in the system; not yet real-world ready.

## October (now): freeze, document, present — no production code changes
- Present from tag `midterm-demo-v2`; rehearsal 3× the morning of the talk.
- Documents, slides and results traceable to evidence, with n and uncertainty for safety claims.
- Confirm the exam date and the presentation format (5 min + 2 min Q&A in the course deck).
- Start the physical corpus (printed fictional documents, photographed and scanned) — no code.

## November: measure, fix the verified defects, test feasibility
1. **Baseline report** with denominators and bounds; field-level ground truth.
2. **PDF text-layer trust check** (hidden or OCR-generated text must not count as a digital original) — a verified gap.
3. **Scanned `university_name` extraction** (21/58 and 24/58 correct) — the largest measured extraction defect.
4. **Finish D3 and judge it once on hold-out set 3** (5.41 → 2.68 decision-blocking fields on development data; 진행 중, unmerged).
5. Reviewer queue and admin checklist screen; real-document pilot (read-only, counts only); PostgreSQL and concurrency tests.
6. *Optional:* photo quality gate with perspective correction; an isolated PaddleOCR-VL proof of concept with an error-correlation study.

## December: final system and evidence-based decision
- Decide on selective VLM verification **only if** it lowers human review at unchanged false-READY and false-auto-accept bounds, shows independent errors, and fits the hardware; otherwise keep the simpler pipeline.
- Login and per-project access, privacy (logs, retention, deletion), audit log; optional National Tax Service registry check if the mentor agrees.
- End-to-end tests, deployment instructions, final evaluation report with honest limits.
