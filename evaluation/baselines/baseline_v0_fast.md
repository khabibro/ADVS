# DocCheck-AI Baseline

## Environment
- Baseline: `baseline_v0_fast`
- Git commit: `1ba16d1ae6da9e3830dc5af3a519db48eb6cfd4c`
- Git dirty: `True`
- Python: `3.12.14`
- Node: `v22.23.1`
- PaddlePaddle: `3.1.1`
- PaddleOCR: `3.2.0`
- OCR provider/device: `paddle` / `cpu`
- Models: `PP-OCRv5_mobile_det`, `korean_PP-OCRv5_mobile_rec`

## Dataset
- Count: `5`
- Fingerprint: `4475534fb38a48c3e5fe1908e8b7742945e59b7f2f6bf07a2c9d66bddd49674d`
- Document types: `{'BUSINESS_REGISTRATION_CERTIFICATE': 1, 'CAREER_CERTIFICATE': 1, 'GRADUATION_CERTIFICATE': 1, 'SME_CONFIRMATION_CERTIFICATE': 1, 'UNKNOWN': 1}`
- Splits: `{'dev': 5}`
- Source classes: `{'NEGATIVE_OUT_OF_SCOPE': 1, 'SYNTHETIC_REALISTIC': 4}`
- Validation labels: `{'NEEDS_CORRECTION': 1, 'NOT_AVAILABLE': 1, 'PASS': 3}`

## Gold Text
- Classification accuracy: 100.00%
- Field accuracy: 100.00%
- Document-level extraction success: 100.00%
- Validation accuracy: 100.00%
- False PASS: `0` / `4`

## Real PaddleOCR
- OCR attempts: `5`
- OCR succeeded: `5`
- OCR failed: `0`
- OCR empty: `0`
- CER mean: `0.0`
- Text similarity mean: `1.0`
- Classification accuracy: 100.00%
- Field accuracy: 88.46%
- Document-level extraction success: 50.00%
- Validation accuracy: 75.00%
- False PASS: `0` / `4`

## Gold vs OCR Gap
- Field accuracy gap: 11.54%
- Document success gap: 50.00%
- Validation accuracy gap: 25.00%

| Field | Gold | PaddleOCR | Gap |
|---|---:|---:|---:|
| business_address | 100.00% | 0.00% | 100.00% |
| position | 100.00% | 0.00% | 100.00% |
| applicant_name | 100.00% | 50.00% | 50.00% |
| business_item | 100.00% | 100.00% | 0.00% |
| business_registration_number | 100.00% | 100.00% | 0.00% |
| business_type | 100.00% | 100.00% | 0.00% |
| certificate_number | 100.00% | 100.00% | 0.00% |
| company_name | 100.00% | 100.00% | 0.00% |
| degree | 100.00% | 100.00% | 0.00% |
| department | 100.00% | 100.00% | 0.00% |
| employment_end_date | 100.00% | 100.00% | 0.00% |
| employment_start_date | 100.00% | 100.00% | 0.00% |
| expiration_date | 100.00% | 100.00% | 0.00% |
| graduation_date | 100.00% | 100.00% | 0.00% |
| issue_date | 100.00% | 100.00% | 0.00% |
| representative_name | 100.00% | 100.00% | 0.00% |
| university_name | 100.00% | 100.00% | 0.00% |
| validity_period | 100.00% | 100.00% | 0.00% |

## Failure Categories

### Gold Text
{
  "total_failing_samples": 0,
  "by_category": {}
}

### PaddleOCR
{
  "total_failing_samples": 2,
  "by_category": {
    "EXTRACTION_LABEL_ERROR": {
      "count": 2,
      "pct": 1.0
    }
  }
}

## Safety
- Gold false PASS samples: `[]`
- Paddle false PASS samples: `[]`

## Performance
- Total runtime seconds: `12.700`
- Documents processed: `10`
- Average seconds per document: `1.270`

## Known Limitations
- REAL OCR EVALUATION: NOT YET AVAILABLE.
- Synthetic/recreated rendered samples are development evidence only.
- Sample-level results omit field values and raw OCR text to avoid unnecessary sensitive text storage.

## Reproduction Command
- `make baseline-fast`
