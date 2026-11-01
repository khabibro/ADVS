"""The checklist rows exactly as ``scripts/seed.py`` built them before checklists were versioned.

Kept only as the golden reference for the equivalence test: version 1 must compile to what these
rows produced, except for the two deliberate changes listed in the test.
"""

from __future__ import annotations

from app.core.domain import DocumentType, RuleOperator, RuleType, Severity
from app.models.entities import Checklist, DocumentRequirement, ValidationRule

BR = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE


def _comparison(target_type, source_field, target_field, value_type="string"):
    return (
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": BR.value,
            "source_field": source_field,
            "target_document_type": target_type.value,
            "target_field": target_field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": value_type,
        },
    )


def _student_identity(field, value_type="string"):
    return (
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
            "source_field": field,
            "target_document_type": DocumentType.TRANSCRIPT.value,
            "target_field": field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": value_type,
        },
    )


def _validity(document_type):
    return (
        RuleType.DATE_COMPARISON,
        Severity.ERROR,
        {
            "document_type": document_type.value,
            "field": "valid_until",
            "operator": RuleOperator.ON_OR_AFTER.value,
            "comparison_source": "EVALUATION_DATE",
        },
    )


def _issue_before_year_end(document_type):
    return (
        RuleType.DATE_COMPARISON,
        Severity.ERROR,
        {
            "document_type": document_type.value,
            "field": "issue_date",
            "operator": RuleOperator.ON_OR_BEFORE.value,
            "expected_value": "2026-12-31",
        },
    )


def _workflow(name, requirements) -> Checklist:
    workflow = Checklist(name=name, is_active=True)
    for document_type, required, rules in requirements:
        requirement = DocumentRequirement(document_type=document_type.value, required=required)
        requirement.rules.extend(
            ValidationRule(rule_type=t.value, severity=s.value, params=p) for t, s, p in rules
        )
        workflow.requirements.append(requirement)
    return workflow


def legacy_business() -> Checklist:
    sme = DocumentType.SME_CONFIRMATION_CERTIFICATE
    tax = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
    ins = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    brn = "business_registration_number"
    return _workflow(
        "기업 제출서류 점검",
        [
            (BR, True, []),
            (
                sme,
                True,
                [
                    _comparison(sme, brn, brn, "identifier"),
                    _comparison(sme, "company_name", "company_name"),
                    _validity(sme),
                ],
            ),
            (
                tax,
                True,
                [
                    _comparison(tax, brn, brn, "identifier"),
                    _comparison(tax, "company_name", "company_name"),
                    _validity(tax),
                ],
            ),
            (
                ins,
                True,
                [
                    _comparison(ins, brn, brn, "identifier"),
                    _comparison(ins, "company_name", "workplace_name"),
                    _validity(ins),
                ],
            ),
        ],
    )


def legacy_student() -> Checklist:
    enrollment = DocumentType.ENROLLMENT_CERTIFICATE
    transcript = DocumentType.TRANSCRIPT
    return _workflow(
        "학생 제출서류 점검",
        [
            (
                enrollment,
                True,
                [
                    _issue_before_year_end(enrollment),
                    (RuleType.ISSUE_DATE_MAX_AGE, Severity.ERROR, {"max_age_days": 90}),
                    (RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "student_id"}),
                ],
            ),
            (
                transcript,
                False,
                [
                    _student_identity("student_id", "identifier"),
                    _student_identity("student_name"),
                    _student_identity("university_name", "institution"),
                    _issue_before_year_end(transcript),
                    (
                        RuleType.NUMERIC_COMPARISON,
                        Severity.ERROR,
                        {
                            "document_type": transcript.value,
                            "field": "gpa",
                            "operator": RuleOperator.GREATER_THAN_OR_EQUAL.value,
                            "expected_value": "3.0",
                        },
                    ),
                ],
            ),
        ],
    )
