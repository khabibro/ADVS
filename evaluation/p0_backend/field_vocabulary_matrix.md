# Field vocabulary matrix

`EXPECTED_FIELDS` remains the default workflow-required field set. `OPTIONAL_SUPPORTED_FIELDS` lists additional extractor-supported fields. `SUPPORTED_FIELDS` and `REVIEWABLE_FIELDS` are derived from those two sources.

| Document type | Default expected fields | Additional supported/reviewable fields |
|---|---|---|
| GRADUATION_CERTIFICATE | applicant_name, university_name, department, degree, graduation_date, issue_date | none |
| CAREER_CERTIFICATE | applicant_name, company_name, position, employment_start_date, employment_end_date, issue_date | none |
| BUSINESS_REGISTRATION_CERTIFICATE | company_name, business_registration_number | representative_name, business_address, business_type, business_item, issue_date |
| SME_CONFIRMATION_CERTIFICATE | company_name, business_registration_number, valid_from, valid_until | representative_name, certificate_number, issue_date |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | company_name, business_registration_number, valid_until | issue_date |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | workplace_name, business_registration_number, valid_until | issue_date |
| ENROLLMENT_CERTIFICATE | student_name, university_name, department, student_id, issue_date | none |
| TRANSCRIPT | student_name, university_name, student_id, issue_date, gpa, gpa_scale | none |

Invariant: supported optional fields are reviewable and rule-referenceable, but they do not become default required fields.
