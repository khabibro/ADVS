# Why a human is still needed (scanned + images; fields with no effective value)

## dev: 278 fields

| Reason | Fields | Share | Fields affected (count) |
|---|---|---|---|
| NO_INDEPENDENT_CONFIRMATION | 145 | 52% | valid_until 68, valid_from 24, gpa_scale 18, gpa 14, university_name 13, student_id 6 |
| EXTRACTION_MARKED_FOR_REVIEW | 40 | 14% | issue_date 32, business_registration_number 8 |
| DISAGREES_WITH_OTHER_DOCUMENT | 30 | 11% | business_registration_number 18, company_name 6, student_name 4, workplace_name 2 |
| NOT_EXTRACTED | 22 | 8% | university_name 19, student_id 2, company_name 1 |
| NO_RULE_FOR_FIELD | 16 | 6% | department 16 |
| UNCERTAIN_TYPE:TITLE_NOT_CLEAN_AND_NO_SECOND_SIGNAL | 10 | 4% | student_name 2, university_name 2, department 2, student_id 2, issue_date 2 |
| NEAR_DECISION_BOUNDARY | 6 | 2% | gpa 4, valid_until 2 |
| ABSENT_IN_DOCUMENT | 6 | 2% | valid_until 2, issue_date 2, student_id 2 |
| CONFIDENCE_BELOW_FLOOR | 3 | 1% | company_name 3 |

## holdout1: 330 fields

| Reason | Fields | Share | Fields affected (count) |
|---|---|---|---|
| NO_INDEPENDENT_CONFIRMATION | 153 | 46% | valid_until 79, valid_from 28, gpa_scale 20, gpa 16, student_id 5, university_name 4 |
| DISAGREES_WITH_OTHER_DOCUMENT | 50 | 15% | business_registration_number 26, company_name 12, workplace_name 4, student_name 4, student_id 4 |
| EXTRACTION_MARKED_FOR_REVIEW | 45 | 14% | issue_date 37, business_registration_number 8 |
| NOT_EXTRACTED | 38 | 12% | university_name 33, student_id 2, business_registration_number 1, company_name 1, department 1 |
| NO_RULE_FOR_FIELD | 18 | 5% | department 18 |
| CONFIDENCE_BELOW_FLOOR | 7 | 2% | company_name 3, student_name 2, business_registration_number 1, valid_until 1 |
| NEAR_DECISION_BOUNDARY | 6 | 2% | gpa 4, valid_until 2 |
| ABSENT_IN_DOCUMENT | 6 | 2% | valid_until 2, issue_date 2, student_id 2 |
| UNCERTAIN_TYPE:TITLE_NOT_CLEAN_AND_NO_SECOND_SIGNAL | 5 | 2% | student_name 1, university_name 1, department 1, student_id 1, issue_date 1 |
| SECOND_PASS_CONTRADICTS_NAME | 2 | 1% | university_name 2 |

## holdout2: 336 fields

| Reason | Fields | Share | Fields affected (count) |
|---|---|---|---|
| NO_INDEPENDENT_CONFIRMATION | 160 | 48% | valid_until 78, valid_from 26, gpa_scale 19, university_name 17, gpa 15, student_id 3 |
| DISAGREES_WITH_OTHER_DOCUMENT | 50 | 15% | business_registration_number 26, company_name 12, workplace_name 4, student_name 4, student_id 4 |
| EXTRACTION_MARKED_FOR_REVIEW | 45 | 13% | issue_date 37, business_registration_number 8 |
| NOT_EXTRACTED | 26 | 8% | university_name 18, valid_from 2, valid_until 2, department 2, company_name 1, student_name 1 |
| CONFIDENCE_BELOW_FLOOR | 18 | 5% | company_name 12, student_id 3, student_name 2, university_name 1 |
| NO_RULE_FOR_FIELD | 18 | 5% | department 18 |
| NEAR_DECISION_BOUNDARY | 6 | 2% | gpa 4, valid_until 2 |
| ABSENT_IN_DOCUMENT | 6 | 2% | valid_until 2, issue_date 2, student_id 2 |
| UNCERTAIN_TYPE:UNEXPLAINED_CHARACTERS_BEFORE_TITLE | 6 | 2% | student_name 1, university_name 1, student_id 1, issue_date 1, gpa 1, gpa_scale 1 |
| SECOND_PASS_CONTRADICTS_NAME | 1 | 0% | university_name 1 |
