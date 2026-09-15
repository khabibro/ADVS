# DocCheck-AI Baseline

## Environment
- Baseline: `baseline_v0`
- Git commit: `1ba16d1ae6da9e3830dc5af3a519db48eb6cfd4c`
- Git dirty: `True`
- Python: `3.12.14`
- Node: `v22.23.1`
- PaddlePaddle: `3.1.1`
- PaddleOCR: `3.2.0`
- OCR provider/device: `paddle` / `cpu`
- Models: `PP-OCRv5_mobile_det`, `korean_PP-OCRv5_mobile_rec`

## Dataset
- Count: `137`
- Fingerprint: `d303ac29f817452421c5db5742a040b53deb194ff00b0eb99193c71bde1639d8`
- Document types: `{'BUSINESS_REGISTRATION_CERTIFICATE': 29, 'CAREER_CERTIFICATE': 26, 'GRADUATION_CERTIFICATE': 29, 'SME_CONFIRMATION_CERTIFICATE': 28, 'UNKNOWN': 25}`
- Splits: `{'dev': 105, 'held_out': 32}`
- Source classes: `{'NEGATIVE_OUT_OF_SCOPE': 25, 'RECREATED_FROM_PUBLIC_REFERENCE': 5, 'SYNTHETIC_REALISTIC': 107}`
- Validation labels: `{'NEEDS_CORRECTION': 7, 'NOT_AVAILABLE': 25, 'PASS': 85, 'REVIEW': 20}`

## Gold Text
- Classification accuracy: 97.08%
- Field accuracy: 99.73%
- Document-level extraction success: 99.11%
- Validation accuracy: 100.00%
- False PASS: `0` / `112`

## Real PaddleOCR
- OCR attempts: `137`
- OCR succeeded: `137`
- OCR failed: `0`
- OCR empty: `0`
- CER mean: `0.006216580049629349`
- Text similarity mean: `0.9946301522361104`
- Classification accuracy: 97.08%
- Field accuracy: 62.55%
- Document-level extraction success: 11.61%
- Validation accuracy: 38.39%
- False PASS: `0` / `112`

## Gold vs OCR Gap
- Field accuracy gap: 37.17%
- Document success gap: 87.50%
- Validation accuracy gap: 61.61%

| Field | Gold | PaddleOCR | Gap |
|---|---:|---:|---:|
| certificate_number | 100.00% | 25.00% | 75.00% |
| validity_period | 100.00% | 35.71% | 64.29% |
| position | 100.00% | 46.15% | 53.85% |
| employment_end_date | 96.15% | 46.15% | 50.00% |
| expiration_date | 100.00% | 50.00% | 50.00% |
| business_registration_number | 100.00% | 50.88% | 49.12% |
| applicant_name | 100.00% | 50.91% | 49.09% |
| issue_date | 100.00% | 53.57% | 46.43% |
| business_address | 100.00% | 55.17% | 44.83% |
| business_item | 100.00% | 58.62% | 41.38% |
| employment_start_date | 96.15% | 57.69% | 38.46% |
| business_type | 100.00% | 62.07% | 37.93% |
| department | 100.00% | 65.52% | 34.48% |
| graduation_date | 100.00% | 65.52% | 34.48% |
| company_name | 100.00% | 80.72% | 19.28% |
| university_name | 100.00% | 96.55% | 3.45% |
| representative_name | 100.00% | 98.25% | 1.75% |
| degree | 100.00% | 100.00% | 0.00% |

## Failure Categories

### Gold Text
{
  "total_failing_samples": 5,
  "by_category": {
    "AMBIGUOUS_DOCUMENT": {
      "count": 4,
      "pct": 0.8
    },
    "UNSUPPORTED_LAYOUT": {
      "count": 1,
      "pct": 0.2
    }
  }
}

### PaddleOCR
{
  "total_failing_samples": 103,
  "by_category": {
    "EXTRACTION_LABEL_ERROR": {
      "count": 60,
      "pct": 0.5825242718446602
    },
    "EXTRACTION_PATTERN_ERROR": {
      "count": 31,
      "pct": 0.30097087378640774
    },
    "UNSUPPORTED_LAYOUT": {
      "count": 8,
      "pct": 0.07766990291262135
    },
    "AMBIGUOUS_DOCUMENT": {
      "count": 4,
      "pct": 0.038834951456310676
    }
  }
}

## Safety
- Gold false PASS samples: `[]`
- Paddle false PASS samples: `[]`

## Performance
- Total runtime seconds: `247.915`
- Documents processed: `274`
- Average seconds per document: `0.905`

## Known Limitations
- REAL OCR EVALUATION: NOT YET AVAILABLE.
- Synthetic/recreated rendered samples are development evidence only.
- Sample-level results omit field values and raw OCR text to avoid unnecessary sensitive text storage.

## Reproduction Command
- `make baseline`
