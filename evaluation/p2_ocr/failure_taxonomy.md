# P2 Failure Taxonomy

Categories are assigned at the earliest measured pipeline stage that loses
usable information. Do not infer a cause from a wrong final field alone.

| Category | Meaning | Measured count |
|---|---|---:|
| SOURCE_NOT_VISIBLE | Expected information is absent from the original page | pending annotation |
| RENDERING_LOSS | Visible source content is absent/degraded in OCR input image | pending benchmark |
| RESOLUTION_TOO_LOW | Glyph detail is lost at effective source/render resolution | pending benchmark |
| RESOLUTION_TOO_HIGH | Resource/pixel limits truncate or reject the OCR input | pending benchmark |
| TEXT_DETECTION_MISS | Visible text has no corresponding OCR detection box | 0 confirmed; not scored |
| TEXT_DETECTION_FRAGMENTATION | One label/value is split into unusable boxes | pending annotation |
| TEXT_DETECTION_MERGE | Separate text fields are merged into one unusable box | pending annotation |
| KOREAN_RECOGNITION_ERROR | Detected Korean text is read incorrectly | not separated from detection |
| DIGIT_RECOGNITION_ERROR | Detected numeric text is read incorrectly | not separated from detection |
| CHARACTER_SUBSTITUTION | Detected glyph sequence contains substitutions | pending annotation |
| SPACING_ERROR | Text content is correct except for spacing | pending annotation |
| PUNCTUATION_ERROR | Delimiters or punctuation are wrong/missing | pending annotation |
| ROTATION_ERROR | Orientation handling prevents correct detection/recognition | pending benchmark |
| TABLE_BORDER_INTERFERENCE | Borders obscure or split text | pending annotation |
| LOW_CONTRAST | Contrast prevents reliable detection/recognition | pending annotation |
| NOISE | Image artifacts degrade recognition | pending annotation |
| STAMP_OVERLAP | Seal/stamp occludes expected text | pending annotation |
| SMALL_TEXT | Text size is below practical detector/recognizer resolution | pending annotation |
| MODEL_LANGUAGE_LIMITATION | Model documentation or measured output supports a language limitation | pending research |
| OBSERVATION_PRESENT_EXTRACTION_FAILED | Usable OCR text exists but no correct field candidate is generated | 7 downstream candidate/association/path cases in the 17-field trace |
| STRUCTURAL_AMBIGUITY | Candidates exist but the visible structure does not select one safely | pending trace |
| UNKNOWN | Evidence does not establish a stage cause | pending |

No frequency ranking is asserted until field-level visibility annotations and
box-level detection judgments exist.

## Current 17-field replay

The real production-path run reproduces 17 unresolved outcomes. Joining those
fields to the P1 cached-observation diagnosis gives: 9 `NO_LABEL_OBSERVED`
results, 3 adjacent-column contamination results, 2 candidate shape rejections,
1 label/value association failure, 1 ranked-path/production-path mismatch, and
1 untraced field. These are *candidate-path diagnoses*, not detection versus
recognition counts. One no-label field has no such label/value on the document;
one visible department label is an OCR-readable synonym missing from the
extractor alias list. Thus eight fields lack the extractor-expected label alias
among the unresolved fields, but only seven are visible-label observation
misses. The seven still cannot be split into detection and recognition without
annotated regions.
