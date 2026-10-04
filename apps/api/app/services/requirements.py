"""Workflow readiness requirements, separate from extractor capabilities.

These conservative defaults cover identity and applicable validity. A
workflow's explicit REQUIRED_FIELD rules ADD to them -- naming a field
lets the checklist set that field's own severity/params, but it does not
drop the check for every default field it doesn't name (audit F-001: one
REQUIRED_FIELD(company_name) rule used to silently disable the net for
every other field of the document, including an unresolved valid_until
with no other protection). Comparison rules still require their own
inputs. Missing optional extractor fields do not block READY.
"""

from app.core.domain import EXPECTED_FIELDS, REVIEWABLE_FIELDS, DocumentType, RuleType
from app.document_intelligence.validation.submission import RuleConfigurationError
from app.models.entities import DocumentRequirement

DEFAULT_REQUIRED_FIELDS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: (
        "company_name",
        "business_registration_number",
    ),
    DocumentType.SME_CONFIRMATION_CERTIFICATE: (
        "company_name",
        "business_registration_number",
        "valid_from",
        "valid_until",
    ),
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: (
        "company_name",
        "business_registration_number",
        "valid_until",
    ),
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: (
        "workplace_name",
        "business_registration_number",
        "valid_until",
    ),
    DocumentType.ENROLLMENT_CERTIFICATE: ("student_name", "university_name", "issue_date"),
    DocumentType.TRANSCRIPT: ("student_name", "university_name", "issue_date"),
    DocumentType.GRADUATION_CERTIFICATE: (
        "applicant_name",
        "university_name",
        "graduation_date",
        "issue_date",
    ),
    DocumentType.CAREER_CERTIFICATE: (
        "applicant_name",
        "company_name",
        "employment_start_date",
        "issue_date",
    ),
    DocumentType.UNKNOWN: (),
}


def required_fields(requirement: DocumentRequirement) -> tuple[str, ...]:
    document_type = DocumentType(requirement.document_type)
    explicit = [rule for rule in requirement.rules if rule.rule_type == RuleType.REQUIRED_FIELD]
    result: set[str] = (
        set(DEFAULT_REQUIRED_FIELDS[document_type]) if requirement.required else set()
    )
    for rule in explicit:
        name = (rule.params or {}).get("field")
        names = [name] if name is not None else EXPECTED_FIELDS[document_type]
        if any(item not in REVIEWABLE_FIELDS[document_type] for item in names):
            raise RuleConfigurationError("Unknown workflow-required canonical field")
        result.update(names)
    return tuple(sorted(result))
