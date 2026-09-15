# ADVS Agent Guide

Use these role files before substantial changes:
- `.agents/architecture.md`
- `.agents/frontend.md`
- `.agents/backend.md`
- `.agents/document-intelligence.md`
- `.agents/qa-integration.md`

The core rule is dependency direction: UI consumes contracts and API responses; API owns persistence and business workflows; document intelligence owns OCR/classification/extraction/validation internals. Do not duplicate validation logic in React, expose OCR internals, or add infrastructure without a ADVS requirement.
