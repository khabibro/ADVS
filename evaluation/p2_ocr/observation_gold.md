# Observation-Level Gold Protocol

The P1 frozen field gold does not provide a complete, independent visible-text
annotation for detection versus recognition. P2 requires a versioned private
annotation held outside Git. Every expected field records visibility and OCR
outcome separately, keyed only by `REAL-###` in tracked summaries.

For both label and value, visibility is one of:

- `VISIBLE`
- `NOT_VISIBLE`
- `AMBIGUOUS`
- `NOT_APPLICABLE`

Detection and recognition outcomes are recorded independently:

- `DETECTED_CORRECTLY`
- `DETECTED_INCORRECTLY`
- `NOT_DETECTED`
- `RECOGNIZED_CORRECTLY`
- `RECOGNIZED_INCORRECTLY`
- `PARTIAL`

For detection, a correct box must overlap the human-annotated label/value region
at the agreed geometry criterion. For recognition, compare normalized text only
after preserving exact raw observation text. Normalization may ignore agreed
spacing/punctuation variants, but must not erase distinguishing Hangul or digit
errors. A box without correct recognition is a detection success and recognition
failure, not a detection miss.

The annotation must also capture whether usable raw observation text survives
adapter conversion and page assembly. Exact crops, text, values, and raw OCR stay
in ignored runtime files. Tracked outputs contain safe IDs, field names, status
enums, and aggregate counts only.

Current status: this private observation gold has not been authored or
independently reviewed. Therefore no new detection or recognition rate is
claimed yet.
