# Why a human is still needed (scanned + images; fields with no effective value)

## dev: 194 fields

| Reason | Fields | Share | Fields affected (count) |
|---|---|---|---|
| NO_INDEPENDENT_CONFIRMATION | 65 | 34% | valid_until 44, university_name 13, student_id 6, student_name 2 |
| DISAGREES_WITH_OTHER_DOCUMENT | 30 | 15% | business_registration_number 18, company_name 6, student_name 4, workplace_name 2 |
| NOT_EXTRACTED | 22 | 11% | university_name 19, student_id 2, company_name 1 |
| SEMANTIC_INFERENCE | 20 | 10% | issue_date 20 |
| NO_RULE_FOR_FIELD | 16 | 8% | department 16 |
| NO_DECISION_RECORD | 12 | 6% | issue_date 12 |
| UNCERTAIN_TYPE:TITLE_NOT_CLEAN_AND_NO_SECOND_SIGNAL | 10 | 5% | student_name 2, university_name 2, department 2, student_id 2, issue_date 2 |
| EXTRACTION_MARKED_FOR_REVIEW | 8 | 4% | business_registration_number 8 |
| ABSENT_IN_DOCUMENT | 6 | 3% | valid_until 2, issue_date 2, student_id 2 |
| CONFIDENCE_BELOW_FLOOR | 3 | 2% | company_name 3 |
| NEAR_DECISION_BOUNDARY | 2 | 1% | valid_until 2 |

## holdout2: 246 fields

| Reason | Fields | Share | Fields affected (count) |
|---|---|---|---|
| NO_INDEPENDENT_CONFIRMATION | 74 | 30% | valid_until 52, university_name 17, student_id 3, student_name 2 |
| DISAGREES_WITH_OTHER_DOCUMENT | 50 | 20% | business_registration_number 26, company_name 12, workplace_name 4, student_name 4, student_id 4 |
| NOT_EXTRACTED | 26 | 11% | university_name 18, valid_from 2, valid_until 2, department 2, company_name 1, student_name 1 |
| SEMANTIC_INFERENCE | 21 | 9% | issue_date 21 |
| CONFIDENCE_BELOW_FLOOR | 18 | 7% | company_name 12, student_id 3, student_name 2, university_name 1 |
| NO_RULE_FOR_FIELD | 18 | 7% | department 18 |
| NO_DECISION_RECORD | 16 | 7% | issue_date 16 |
| EXTRACTION_MARKED_FOR_REVIEW | 8 | 3% | business_registration_number 8 |
| ABSENT_IN_DOCUMENT | 6 | 2% | valid_until 2, issue_date 2, student_id 2 |
| UNCERTAIN_TYPE:UNEXPLAINED_CHARACTERS_BEFORE_TITLE | 6 | 2% | student_name 1, university_name 1, student_id 1, issue_date 1, gpa 1, gpa_scale 1 |
| NEAR_DECISION_BOUNDARY | 2 | 1% | valid_until 2 |
| SECOND_PASS_CONTRADICTS_NAME | 1 | 0% | university_name 1 |
