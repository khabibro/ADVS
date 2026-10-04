"""Probe: does a partial REQUIRED_FIELD checklist silently disable the
missing-field safety net for fields it does NOT mention?

Hypothesis from reading app/document_intelligence/validation/engine.py:
`_has_required_field_rule` suppresses the blanket "unresolved field" net as
soon as ANY REQUIRED_FIELD rule is configured, regardless of which single
field that rule targets. If an admin configures one REQUIRED_FIELD rule for
"company_name" only, and valid_until is unresolved, and no DATE_NOT_EXPIRED
rule is configured either, does the missing valid_until produce zero issues
and an overall READY status?

Read-only probe against the real ValidationEngine / ExtractedValue classes.
No production files modified.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine


def field(name, value=None, needs_review=False):
    return ExtractedValue(
        field_name=name,
        raw_value=value,
        normalized_value=value,
        confidence=0.95 if value else None,
        needs_review=needs_review,
        extraction_method="probe",
    )


engine = ValidationEngine()

fields = [
    field("company_name", "샘플 주식회사"),
    field("business_registration_number", "1234567890"),
    field("valid_from", None),
    field("valid_until", None),  # unresolved -- document may or may not be expired
]

print("=== Case A: no configured_rules at all (pure default net) ===")
issues = engine.validate_document(
    expected_type=DocumentType.SME_CONFIRMATION_CERTIFICATE,
    actual_type=DocumentType.SME_CONFIRMATION_CERTIFICATE,
    fields=fields,
    configured_rules=None,
)
for i in issues:
    print(f"  {i.rule_type} passed={i.passed} severity={i.severity} code={i.code}")
print("  overall_status =", engine.overall_status(issues))

print()
print("=== Case B: ONE configured REQUIRED_FIELD rule, targeting company_name only ===")
configured = [
    ConfiguredRule(rule_type=RuleType.REQUIRED_FIELD, severity=Severity.WARNING, params={"field": "company_name"}),
]
issues = engine.validate_document(
    expected_type=DocumentType.SME_CONFIRMATION_CERTIFICATE,
    actual_type=DocumentType.SME_CONFIRMATION_CERTIFICATE,
    fields=fields,
    configured_rules=configured,
)
for i in issues:
    print(f"  {i.rule_type} passed={i.passed} severity={i.severity} code={i.code}")
print("  overall_status =", engine.overall_status(issues))
print()
print("  valid_until is unresolved (None) in the input. If no issue above")
print("  mentions valid_until/DATE_NOT_EXPIRED/REQUIRED_FIELD for it, the")
print("  missing expiration date produced ZERO issues under this checklist.")
