"""B-1 (audit F-001): a configured REQUIRED_FIELD rule must ADD to a
document type's default required fields, not replace them.

Covers both layers the bug lived in:
- the engine (`ValidationEngine.validate_document` / `_apply_configured_rule`)
- the service (`services.document_validation.configured_document_rules`)

Also pins the existing R2-02 regression (a checklist of rules this engine
cannot execute at document scope must still produce missing-field warnings)
and the existing blanket-REQUIRED_FIELD-rule test (optional fields must not
silently become required), neither of which this fix may weaken.
"""

from __future__ import annotations

import uuid

from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    Project,
    Submission,
    User,
    ValidationRule,
)
from app.services.document_validation import configured_document_rules, validate_effective_document

engine = ValidationEngine()


def _sme_fields(valid_until_resolved: bool) -> list[ExtractedValue]:
    return [
        ExtractedValue("company_name", "테스트상사", "테스트상사"),
        ExtractedValue("business_registration_number", "123-45-00018", "1234500018"),
        ExtractedValue("valid_from", "2026-01-01", "2026-01-01"),
        ExtractedValue(
            "valid_until",
            "2026-12-31" if valid_until_resolved else None,
            "2026-12-31" if valid_until_resolved else None,
            None,
            not valid_until_resolved,
        ),
    ]


def test_partial_checklist_still_flags_the_unresolved_field_it_does_not_name() -> None:
    """The exact shape the audit (F-001) and Phase A's probe reproduced:
    one REQUIRED_FIELD rule for company_name, valid_until unresolved."""
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "company_name"})]
    fields = _sme_fields(valid_until_resolved=False)
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    missing = {i.expected_value for i in issues if i.code == "MISSING_REQUIRED_FIELD"}
    assert "valid_until" in missing
    assert engine.overall_status(issues) == ValidationEngine().overall_status(issues)
    from app.core.domain import OverallStatus

    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_partial_checklist_does_not_duplicate_the_explicitly_named_field() -> None:
    """company_name is explicitly required and unresolved: exactly one
    MISSING_REQUIRED_FIELD issue for it, not one from each mechanism.

    Configuring ERROR severity on the rule does not escalate a *missing*
    field to a deterministic failure -- see
    test_missing_or_uncertain_value_never_becomes_deterministic_failure in
    test_astra_document_state.py, which pins this invariant directly. A
    missing-field issue is always WARNING; only a value that *was* read
    (e.g. an expired date) can carry a configured ERROR severity.
    """
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.ERROR, {"field": "company_name"})]
    fields = [
        ExtractedValue("company_name", None, None, None, True),
        ExtractedValue("business_registration_number", "123-45-00018", "1234500018"),
        ExtractedValue("valid_from", "2026-01-01", "2026-01-01"),
        ExtractedValue("valid_until", "2026-12-31", "2026-12-31"),
    ]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    company_issues = [i for i in issues if i.expected_value == "company_name"]
    assert len(company_issues) == 1
    assert company_issues[0].severity == Severity.WARNING


def test_checklist_listing_every_field_explicitly_behaves_as_configured() -> None:
    """When every field has its own explicit rule, nothing is left for the
    default net to add -- the configured severities are exactly what's used."""
    rules = [
        ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.ERROR, {"field": "company_name"}),
        ConfiguredRule(
            RuleType.REQUIRED_FIELD, Severity.ERROR, {"field": "business_registration_number"}
        ),
        ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "valid_from"}),
        ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "valid_until"}),
    ]
    fields = _sme_fields(valid_until_resolved=True)
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    # No MISSING_REQUIRED_FIELD issue: every field is present. The always-on
    # expiration check still independently reports (unrelated to this fix)
    # that the resolved, future valid_until has not expired -- a passed
    # issue, not a failure.
    assert all(i.code != "MISSING_REQUIRED_FIELD" for i in issues)
    assert all(i.passed for i in issues)
    from app.core.domain import OverallStatus

    assert engine.overall_status(issues) == OverallStatus.READY


def test_blanket_required_field_rule_still_exempts_optional_fields() -> None:
    """Pre-existing invariant this fix must not weaken: a bare REQUIRED_FIELD
    rule (no `field` param) targets the document type's own schema, not
    every extracted field -- an unresolved *optional* field stays optional."""
    fields = [
        ExtractedValue("company_name", "예시기업", "예시기업"),
        ExtractedValue("business_registration_number", "123-45-67890", "1234567890"),
        ExtractedValue("issue_date", None, None, None, True),  # optional, legacy
    ]
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {})]
    issues = engine.validate_document(
        None, DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert issues == []


def test_r2_02_regression_unexecutable_checklist_still_nets_missing_fields() -> None:
    """R2-02: a checklist made only of submission-scope rule types (this
    engine has no document-level handler for them) must not silently
    disable the missing-field net."""
    from app.core.domain import OverallStatus

    unexecutable = [
        ConfiguredRule(RuleType.DATE_COMPARISON, Severity.ERROR, {"field": "issue_date"}),
        ConfiguredRule(RuleType.NUMERIC_COMPARISON, Severity.ERROR, {"field": "gpa"}),
    ]
    fields = [ExtractedValue("company_name", None, None, None, True)]
    issues = engine.validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        configured_rules=unexecutable,
    )
    assert any(i.code == "MISSING_REQUIRED_FIELD" for i in issues)
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


# ---------------------------------------------------------------------
# Service layer: services.document_validation.configured_document_rules
# ---------------------------------------------------------------------


def test_service_layer_partial_checklist_still_auto_fills_the_rest(db_session) -> None:
    user = User(email=f"{uuid.uuid4()}@test.local", display_name="t")
    db_session.add(user)
    db_session.flush()
    checklist = Checklist(name=f"b1-test-{uuid.uuid4()}", is_active=True)
    db_session.add(checklist)
    db_session.flush()
    requirement = DocumentRequirement(
        checklist_id=checklist.id,
        document_type=DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
        required=True,
    )
    db_session.add(requirement)
    db_session.flush()
    db_session.add(
        ValidationRule(
            requirement_id=requirement.id,
            rule_type=RuleType.REQUIRED_FIELD.value,
            severity=Severity.WARNING.value,
            params={"field": "company_name"},
        )
    )
    project = Project(owner_id=user.id, checklist_id=checklist.id, name="b1-test")
    db_session.add(project)
    db_session.commit()

    rules = configured_document_rules(
        db_session, project, DocumentType.SME_CONFIRMATION_CERTIFICATE
    )
    assert rules is not None
    named_fields = {r.params.get("field") for r in rules if r.rule_type == RuleType.REQUIRED_FIELD}
    # company_name (explicit) plus the rest of this document type's default
    # required fields (business_registration_number, valid_from, valid_until)
    # must all still be present -- additive, not replaced.
    assert "company_name" in named_fields
    assert "valid_until" in named_fields
    assert "business_registration_number" in named_fields

    submission = Submission(project_id=project.id)
    db_session.add(submission)
    db_session.flush()
    document = Document(
        submission_id=submission.id,
        original_filename="sme.pdf",
        storage_key="b1-test/sme.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        checksum_sha256="b1-test-checksum",
    )
    db_session.add(document)
    db_session.commit()

    fields = _sme_fields(valid_until_resolved=False)
    issues, resolved_project = validate_effective_document(
        db_session, document, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields
    )
    assert resolved_project.id == project.id
    missing = {i.expected_value for i in issues if i.code == "MISSING_REQUIRED_FIELD"}
    assert "valid_until" in missing
