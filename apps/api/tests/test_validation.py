import pytest

from app.core.domain import (
    DocumentType,
    OverallStatus,
    RuleType,
    Severity,
    normalize_overall_status,
)
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine

engine = ValidationEngine()


def test_all_requirements_satisfied_passes() -> None:
    fields = [ExtractedValue("applicant_name", "홍길동", "홍길동", 0.9)]
    issues = engine.validate_document(
        None,
        DocumentType.GRADUATION_CERTIFICATE,
        fields,
        applicant_name="홍길동",
        configured_rules=[],
    )
    assert engine.overall_status(issues) == OverallStatus.READY


def test_name_mismatch_needs_correction() -> None:
    issues = engine.validate_document(
        None,
        DocumentType.CAREER_CERTIFICATE,
        [ExtractedValue("applicant_name", "김철수", "김철수", 0.9)],
        applicant_name="홍길동",
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_wrong_document_type_needs_correction() -> None:
    issues = engine.validate_document(
        DocumentType.GRADUATION_CERTIFICATE,
        DocumentType.CAREER_CERTIFICATE,
        [],
        configured_rules=[],
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_duplicate_warning_review() -> None:
    issues = engine.validate_document(
        None,
        DocumentType.GRADUATION_CERTIFICATE,
        [],
        duplicate=True,
        configured_rules=[],
    )
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_default_behavior_flags_missing_fields_when_no_rules_configured() -> None:
    fields = [ExtractedValue("graduation_date", None, None, None, True)]
    issues = engine.validate_document(
        None, DocumentType.GRADUATION_CERTIFICATE, fields, configured_rules=None
    )
    assert any(i.rule_type == RuleType.REQUIRED_FIELD for i in issues)
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_required_field_rule_targets_specific_field() -> None:
    fields = [ExtractedValue("issue_date", None, None, None, True)]
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.ERROR, {"field": "issue_date"})]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_required_field_rule_without_target_uses_document_schema() -> None:
    fields = [
        ExtractedValue("company_name", "예시기업", "예시기업"),
        ExtractedValue("business_registration_number", "123-45-67890", "1234567890"),
        # Optional legacy extraction fields must not silently become required.
        ExtractedValue("issue_date", None, None, None, True),
    ]
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {})]
    issues = engine.validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        configured_rules=rules,
    )
    assert issues == []


def test_date_not_expired_rule_expired_fails() -> None:
    fields = [ExtractedValue("expiration_date", "2020-01-01", "2020-01-01", 0.6)]
    rules = [
        ConfiguredRule(RuleType.DATE_NOT_EXPIRED, Severity.ERROR, {"field": "expiration_date"})
    ]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_date_not_expired_rule_future_date_passes() -> None:
    fields = [ExtractedValue("expiration_date", "2099-01-01", "2099-01-01", 0.6)]
    rules = [
        ConfiguredRule(RuleType.DATE_NOT_EXPIRED, Severity.ERROR, {"field": "expiration_date"})
    ]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert engine.overall_status(issues) == OverallStatus.READY


def test_issue_date_max_age_rule_too_old_fails() -> None:
    fields = [ExtractedValue("issue_date", "2000-01-01", "2000-01-01", 0.6)]
    rules = [
        ConfiguredRule(
            RuleType.ISSUE_DATE_MAX_AGE, Severity.ERROR, {"field": "issue_date", "max_age_days": 90}
        )
    ]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_business_number_match_rule_mismatch() -> None:
    fields = [ExtractedValue("business_registration_number", "123-45-67890", "123-45-67890", 0.9)]
    rules = [
        ConfiguredRule(
            RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH,
            Severity.ERROR,
            {"expected_value": "999-99-99999"},
        )
    ]
    issues = engine.validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        configured_rules=rules,
    )
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_business_number_match_rule_without_expected_value_skips() -> None:
    fields = [ExtractedValue("business_registration_number", "123-45-67890", "123-45-67890", 0.9)]
    rules = [ConfiguredRule(RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH, Severity.ERROR, {})]
    issues = engine.validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        configured_rules=rules,
    )
    assert issues == []


def test_custom_text_rule_contains_pass() -> None:
    fields = [ExtractedValue("business_type", "서비스업", "서비스업", 0.7)]
    rules = [
        ConfiguredRule(
            RuleType.CUSTOM_TEXT_RULE,
            Severity.WARNING,
            {"field": "business_type", "contains": "서비스"},
        )
    ]
    issues = engine.validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        configured_rules=rules,
    )
    assert engine.overall_status(issues) == OverallStatus.READY


def test_custom_text_rule_missing_field_reviews() -> None:
    rules = [
        ConfiguredRule(
            RuleType.CUSTOM_TEXT_RULE,
            Severity.WARNING,
            {"field": "business_type", "contains": "서비스"},
        )
    ]
    issues = engine.validate_document(
        None, DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, [], configured_rules=rules
    )
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_required_documents_missing_flagged() -> None:
    required = [DocumentType.GRADUATION_CERTIFICATE, DocumentType.CAREER_CERTIFICATE]
    present = {DocumentType.GRADUATION_CERTIFICATE}
    issues = engine.validate_required_documents(required, present)
    assert len(issues) == 1
    assert issues[0].rule_type == RuleType.REQUIRED_DOCUMENT
    assert engine.overall_status(issues) == OverallStatus.NEEDS_CORRECTION


def test_required_documents_all_present_passes() -> None:
    required = [DocumentType.GRADUATION_CERTIFICATE]
    present = {DocumentType.GRADUATION_CERTIFICATE}
    issues = engine.validate_required_documents(required, present)
    assert issues == []


def test_legacy_overall_status_values_are_normalized_safely() -> None:
    assert normalize_overall_status("PASS") == OverallStatus.READY
    assert normalize_overall_status("REVIEW") == OverallStatus.REVIEW_REQUIRED
    assert normalize_overall_status("NEEDS_CORRECTION") == OverallStatus.NEEDS_CORRECTION


def test_unknown_overall_status_does_not_default_to_ready() -> None:
    with pytest.raises(ValueError):
        normalize_overall_status("ERROR")


def test_status_precedence_is_correction_then_review_then_ready() -> None:
    warning = engine.validate_document(
        None,
        DocumentType.GRADUATION_CERTIFICATE,
        [],
        duplicate=True,
        configured_rules=[],
    )
    error = engine.validate_required_documents(
        [DocumentType.CAREER_CERTIFICATE], {DocumentType.GRADUATION_CERTIFICATE}
    )

    assert engine.overall_status([]) == OverallStatus.READY
    assert engine.overall_status(warning) == OverallStatus.REVIEW_REQUIRED
    assert engine.overall_status(warning + error) == OverallStatus.NEEDS_CORRECTION
