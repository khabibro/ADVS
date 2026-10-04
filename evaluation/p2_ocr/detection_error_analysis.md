# Detection Error Analysis

The current provider returned 650 non-empty OCR lines with bounding boxes across
seven pages. This is an observation count, not a detection recall: expected text
regions have not been independently annotated and therefore a missing box
cannot yet be distinguished from a recognition miss.

P1 reported a merged table-cell observation. That is a plausible detection
granularity failure, but the P1 unresolved-field table has inconsistent counts
and does not contain a box-level visibility annotation. It remains an
unconfirmed detection finding for P2.

No detector thresholds, model, or box merge behavior was changed.
