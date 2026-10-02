import uuid
from datetime import date

import pytest

from app.core.domain import (
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    RuleOperator,
    RuleOutcome,
    RuleType,
    Severity,
)
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    RuleConfigurationError,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)

EVALUATION_DATE = date(2026, 9, 22)
PROJECT_ID = uuid.UUID(int=1)
WORKFLOW_ID = uuid.UUID(int=2)


def field(name: str, value: str | None, *, review: bool = False) -> FieldSnapshot:
    return FieldSnapshot(uuid.uuid4(), name, value, review, value is not None)


def document(
    document_type: DocumentType,
    values: dict[str, str | None],
    *,
    status: ProcessingStatus = ProcessingStatus.COMPLETED,
    checksum: str | None = None,
    review_fields: set[str] | None = None,
) -> DocumentSnapshot:
    review_fields = review_fields or set()
    return DocumentSnapshot(
        uuid.uuid4(),
        document_type,
        status,
        checksum or uuid.uuid4().hex,
        {name: field(name, value, review=name in review_fields) for name, value in values.items()},
    )


def rule(rule_type: RuleType, **params: str) -> SubmissionRule:
    return SubmissionRule(uuid.uuid4(), rule_type, Severity.ERROR, params)


def requirement(
    document_type: DocumentType,
    *,
    required: bool = True,
    rules: tuple[SubmissionRule, ...] = (),
) -> RequirementSnapshot:
    return RequirementSnapshot(uuid.uuid4(), document_type, required, rules)


def verify(requirements: list[RequirementSnapshot], documents: list[DocumentSnapshot]):
    return SubmissionVerificationEngine().verify(
        project_id=PROJECT_ID,
        workflow_id=WORKFLOW_ID,
        requirements=requirements,
        documents=documents,
        context=VerificationContext(EVALUATION_DATE),
    )


def field_comparison(
    target_type: DocumentType,
    source_field: str = "business_registration_number",
    target_field: str = "business_registration_number",
) -> SubmissionRule:
    return rule(
        RuleType.FIELD_COMPARISON,
        source_document_type=DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
        source_field=source_field,
        target_document_type=target_type.value,
        target_field=target_field,
        operator=RuleOperator.EQUALS.value,
        value_type="identifier" if "number" in source_field else "string",
    )


def date_rule(
    document_type: DocumentType,
    field_name: str = "valid_until",
    operator: RuleOperator = RuleOperator.ON_OR_AFTER,
    expected_value: str | None = None,
) -> SubmissionRule:
    params = {
        "document_type": document_type.value,
        "field": field_name,
        "operator": operator.value,
    }
    if expected_value is None:
        params["comparison_source"] = "EVALUATION_DATE"
    else:
        params["expected_value"] = expected_value
    return rule(RuleType.DATE_COMPARISON, **params)


def gpa_rule() -> SubmissionRule:
    return rule(
        RuleType.NUMERIC_COMPARISON,
        document_type=DocumentType.TRANSCRIPT.value,
        field="gpa",
        operator=RuleOperator.GREATER_THAN_OR_EQUAL.value,
        expected_value="3.0",
    )


def issue_codes(result) -> set[str]:
    return {item.code for item in result.issues}


def test_all_valid_business_documents_are_ready() -> None:
    reference = document(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890", "company_name": "예시기업"},
    )
    target_types = [
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
        DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
    ]
    requirements = [requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE)]
    documents = [reference]
    for document_type in target_types:
        name_field = (
            "workplace_name"
            if document_type == DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
            else "company_name"
        )
        requirements.append(
            requirement(
                document_type,
                rules=(
                    field_comparison(document_type),
                    field_comparison(document_type, "company_name", name_field),
                    date_rule(document_type),
                ),
            )
        )
        documents.append(
            document(
                document_type,
                {
                    "business_registration_number": "1234567890",
                    name_field: "예시기업",
                    "valid_until": "2026-12-31",
                },
            )
        )

    result = verify(requirements, documents)

    assert result.status == OverallStatus.READY
    assert result.issues == ()


@pytest.mark.parametrize(
    "missing_type",
    [
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
    ],
)
def test_missing_required_document_needs_correction(missing_type: DocumentType) -> None:
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(missing_type, rules=(field_comparison(missing_type),)),
        ],
        [document(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, {})],
    )

    assert result.status == OverallStatus.NEEDS_CORRECTION
    assert issue_codes(result) == {"MISSING_REQUIRED_DOCUMENT"}
    assert not any(item.code == "INFORMATION_MISMATCH" for item in result.issues)


def test_missing_reference_does_not_cascade_mismatches() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(target_type, rules=(field_comparison(target_type),)),
        ],
        [document(target_type, {"business_registration_number": "1234567890"})],
    )

    assert result.status == OverallStatus.NEEDS_CORRECTION
    assert issue_codes(result) == {"MISSING_REQUIRED_DOCUMENT"}
    comparison = next(item for item in result.rule_results if item.rule_id is not None)
    assert comparison.outcome == RuleOutcome.NOT_APPLICABLE


def test_normalized_business_number_match_passes() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(target_type, rules=(field_comparison(target_type),)),
        ],
        [
            document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"business_registration_number": "1234567890"},
            ),
            document(target_type, {"business_registration_number": "1234567890"}),
        ],
    )

    assert result.status == OverallStatus.READY


def test_business_number_mismatch_has_traceable_issue() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    reference = document(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    target = document(target_type, {"business_registration_number": "9999999999"})
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(target_type, rules=(field_comparison(target_type),)),
        ],
        [reference, target],
    )

    assert result.status == OverallStatus.NEEDS_CORRECTION
    issue = result.issues[0]
    assert issue.code == "INFORMATION_MISMATCH"
    assert issue.document_id == reference.id
    assert issue.related_document_id == target.id
    assert issue.field_name == "business_registration_number"
    assert issue.field_id is not None and issue.related_field_id is not None


@pytest.mark.parametrize(
    ("source_value", "target_value"), [("예시기업", "다른기업"), (None, "예시기업")]
)
def test_company_name_mismatch_and_null_are_distinct(
    source_value: str | None, target_value: str
) -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(
                target_type,
                rules=(field_comparison(target_type, "company_name", "company_name"),),
            ),
        ],
        [
            document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"company_name": source_value},
            ),
            document(target_type, {"company_name": target_value}),
        ],
    )

    expected_code = "REQUIRED_FIELD_UNRESOLVED" if source_value is None else "INFORMATION_MISMATCH"
    expected_status = (
        OverallStatus.REVIEW_REQUIRED if source_value is None else OverallStatus.NEEDS_CORRECTION
    )
    assert result.status == expected_status
    assert issue_codes(result) == {expected_code}


def test_populated_field_without_provenance_is_unresolved() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    reference = document(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    target = document(target_type, {"business_registration_number": "1234567890"})
    target.fields["business_registration_number"] = FieldSnapshot(
        uuid.uuid4(), "business_registration_number", "1234567890", False, False
    )

    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(target_type, rules=(field_comparison(target_type),)),
        ],
        [reference, target],
    )

    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert issue_codes(result) == {"REQUIRED_FIELD_UNRESOLVED"}


def test_explicitly_review_marked_field_is_ocr_uncertain() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(target_type, rules=(field_comparison(target_type),)),
        ],
        [
            document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"business_registration_number": "1234567890"},
            ),
            document(
                target_type,
                {"business_registration_number": "1234567890"},
                review_fields={"business_registration_number"},
            ),
        ],
    )

    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert issue_codes(result) == {"OCR_UNCERTAIN"}


@pytest.mark.parametrize(
    ("value", "outcome", "status", "code"),
    [
        ("2026-12-31", RuleOutcome.PASS, OverallStatus.READY, None),
        ("2026-09-22", RuleOutcome.PASS, OverallStatus.READY, None),
        ("2026-09-21", RuleOutcome.FAIL, OverallStatus.NEEDS_CORRECTION, "EXPIRED_DOCUMENT"),
        (None, RuleOutcome.UNRESOLVED, OverallStatus.REVIEW_REQUIRED, "REQUIRED_FIELD_UNRESOLVED"),
    ],
)
def test_validity_is_inclusive_and_null_safe(
    value: str | None, outcome: RuleOutcome, status: OverallStatus, code: str | None
) -> None:
    document_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [requirement(document_type, rules=(date_rule(document_type),))],
        [document(document_type, {"valid_until": value})],
    )

    evaluated = next(item for item in result.rule_results if item.rule_id is not None)
    assert evaluated.outcome == outcome
    assert result.status == status
    assert issue_codes(result) == ({code} if code else set())


def test_optional_transcript_absent_is_not_applicable() -> None:
    result = verify(
        [
            requirement(DocumentType.ENROLLMENT_CERTIFICATE),
            requirement(DocumentType.TRANSCRIPT, required=False, rules=(gpa_rule(),)),
        ],
        [document(DocumentType.ENROLLMENT_CERTIFICATE, {})],
    )

    assert result.status == OverallStatus.READY
    transcript_results = [
        item for item in result.rule_results if item.document_type == DocumentType.TRANSCRIPT
    ]
    assert transcript_results
    assert all(item.outcome == RuleOutcome.NOT_APPLICABLE for item in transcript_results)


@pytest.mark.parametrize(
    ("value", "outcome", "status", "code"),
    [
        ("2026-12-30", RuleOutcome.PASS, OverallStatus.READY, None),
        ("2026-12-31", RuleOutcome.PASS, OverallStatus.READY, None),
        ("2027-01-01", RuleOutcome.FAIL, OverallStatus.NEEDS_CORRECTION, "RULE_CONDITION_NOT_MET"),
        (None, RuleOutcome.UNRESOLVED, OverallStatus.REVIEW_REQUIRED, "REQUIRED_FIELD_UNRESOLVED"),
    ],
)
def test_configured_issue_date_rule(
    value: str | None, outcome: RuleOutcome, status: OverallStatus, code: str | None
) -> None:
    rule_config = date_rule(
        DocumentType.ENROLLMENT_CERTIFICATE,
        "issue_date",
        RuleOperator.ON_OR_BEFORE,
        "2026-12-31",
    )
    result = verify(
        [requirement(DocumentType.ENROLLMENT_CERTIFICATE, rules=(rule_config,))],
        [document(DocumentType.ENROLLMENT_CERTIFICATE, {"issue_date": value})],
    )

    evaluated = next(item for item in result.rule_results if item.rule_id is not None)
    assert evaluated.outcome == outcome
    assert result.status == status
    assert issue_codes(result) == ({code} if code else set())


@pytest.mark.parametrize(
    ("value", "outcome", "status", "code"),
    [
        ("3.85", RuleOutcome.PASS, OverallStatus.READY, None),
        ("3.0", RuleOutcome.PASS, OverallStatus.READY, None),
        ("2.99", RuleOutcome.FAIL, OverallStatus.NEEDS_CORRECTION, "RULE_CONDITION_NOT_MET"),
        (None, RuleOutcome.UNRESOLVED, OverallStatus.REVIEW_REQUIRED, "REQUIRED_FIELD_UNRESOLVED"),
    ],
)
def test_gpa_rule_uses_decimal_and_is_null_safe(
    value: str | None, outcome: RuleOutcome, status: OverallStatus, code: str | None
) -> None:
    result = verify(
        [requirement(DocumentType.TRANSCRIPT, required=False, rules=(gpa_rule(),))],
        [document(DocumentType.TRANSCRIPT, {"gpa": value})],
    )

    evaluated = next(item for item in result.rule_results if item.rule_id is not None)
    assert evaluated.outcome == outcome
    assert result.status == status
    assert issue_codes(result) == ({code} if code else set())


def test_correction_precedes_review_without_discarding_review_issue() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [
            requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
            requirement(
                target_type,
                rules=(field_comparison(target_type), date_rule(target_type)),
            ),
        ],
        [
            document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"business_registration_number": "1234567890"},
            ),
            document(
                target_type,
                {"business_registration_number": "9999999999", "valid_until": None},
            ),
        ],
    )

    assert result.status == OverallStatus.NEEDS_CORRECTION
    assert issue_codes(result) == {"INFORMATION_MISMATCH", "REQUIRED_FIELD_UNRESOLVED"}


@pytest.mark.parametrize(
    ("processing_status", "code"),
    [
        (ProcessingStatus.FAILED, "DOCUMENT_PROCESSING_FAILED"),
        (ProcessingStatus.OCR_PROCESSING, "DOCUMENT_PROCESSING_IN_PROGRESS"),
    ],
)
def test_incomplete_required_document_never_produces_ready(
    processing_status: ProcessingStatus, code: str
) -> None:
    document_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = verify(
        [requirement(document_type)],
        [document(document_type, {}, status=processing_status)],
    )

    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert issue_codes(result) == {code}


def test_unknown_does_not_satisfy_known_requirement() -> None:
    result = verify(
        [requirement(DocumentType.SME_CONFIRMATION_CERTIFICATE)],
        [document(DocumentType.UNKNOWN, {})],
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert issue_codes(result) == {"UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW"}


def test_required_enrollment_missing_needs_correction() -> None:
    result = verify([requirement(DocumentType.ENROLLMENT_CERTIFICATE)], [])

    assert result.status == OverallStatus.NEEDS_CORRECTION
    assert issue_codes(result) == {"MISSING_REQUIRED_DOCUMENT"}


def test_multiple_distinct_documents_require_review_but_exact_duplicates_collapse() -> None:
    document_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    requirement_item = requirement(document_type)
    ambiguous = verify(
        [requirement_item],
        [document(document_type, {}), document(document_type, {})],
    )
    duplicate = verify(
        [requirement_item],
        [
            document(document_type, {}, checksum="same"),
            document(document_type, {}, checksum="same"),
        ],
    )

    assert ambiguous.status == OverallStatus.REVIEW_REQUIRED
    assert issue_codes(ambiguous) == {"MULTIPLE_DOCUMENTS_REQUIRE_REVIEW"}
    assert duplicate.status == OverallStatus.READY


@pytest.mark.parametrize(
    "bad_rule",
    [
        rule(
            RuleType.DATE_COMPARISON,
            document_type=DocumentType.ENROLLMENT_CERTIFICATE.value,
            field="unknown_field",
            operator=RuleOperator.ON_OR_BEFORE.value,
            expected_value="2026-12-31",
        ),
        rule(
            RuleType.DATE_COMPARISON,
            document_type=DocumentType.ENROLLMENT_CERTIFICATE.value,
            field="issue_date",
            operator=RuleOperator.ON_OR_BEFORE.value,
            expected_value="not-a-date",
        ),
        rule(
            RuleType.NUMERIC_COMPARISON,
            document_type=DocumentType.TRANSCRIPT.value,
            field="gpa",
            operator=RuleOperator.GREATER_THAN_OR_EQUAL.value,
            expected_value="not-a-decimal",
        ),
        rule(
            RuleType.FIELD_COMPARISON,
            source_field="business_registration_number",
            target_document_type=DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
            target_field="business_registration_number",
            operator=RuleOperator.EQUALS.value,
        ),
    ],
)
def test_invalid_rule_configuration_fails_safely(bad_rule: SubmissionRule) -> None:
    with pytest.raises(RuleConfigurationError):
        verify(
            [
                requirement(DocumentType.ENROLLMENT_CERTIFICATE, rules=(bad_rule,)),
                requirement(DocumentType.TRANSCRIPT),
                requirement(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE),
                requirement(DocumentType.SME_CONFIRMATION_CERTIFICATE),
            ],
            [],
        )
