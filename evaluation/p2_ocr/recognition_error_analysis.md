# Recognition Error Analysis

The P1 report records OCR-related wrong/missing field observations, including a
high-confidence Hangul name substitution. A fresh OCR run exactly reproduces
the P1 text and line strings on all seven pages, but the 17-field denominator
and P1 stage counts need a corrected field-to-gold join before those examples
can be reported as P2 recognition error rates.

## Measured status

| Error class | Count | Evidence status |
|---|---:|---|
| Hangul syllable substitution | pending | Requires reviewed visible-label/value annotation and line alignment |
| Similar glyph confusion | pending | Same |
| Digit confusion | pending | Same |
| Spacing/punctuation | pending | Same |
| Mixed Korean/English | pending | Same |
| Fragmented label | pending | Requires detection box annotation |

OCR confidence is not calibrated as correctness. No confidence threshold or
private correction dictionary is proposed.
