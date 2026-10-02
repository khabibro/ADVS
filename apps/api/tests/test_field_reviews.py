import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.domain import (
    DocumentType,
    ProcessingStatus,
    RuleOperator,
    RuleType,
    Severity,
)
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    ExtractedField,
    FieldReview,
    Project,
    Submission,
    User,
    ValidationRule,
)
from app.services.reviews import invalidate_document_reviews
from app.services.verification import invalidate_submission_verification


def _project(db_session, *, transcript: bool = False):
    user = User(email=f"phase7-{uuid.uuid4()}@advs.local", display_name="Phase 7")
    workflow = Checklist(name=f"Phase 7 {uuid.uuid4()}")
    db_session.add_all([user, workflow])
    db_session.flush()
    if transcript:
        requirement = DocumentRequirement(
            checklist_id=workflow.id,
            document_type=DocumentType.TRANSCRIPT.value,
            required=True,
        )
        db_session.add(requirement)
        db_session.flush()
        db_session.add(
            ValidationRule(
                requirement_id=requirement.id,
                rule_type=RuleType.NUMERIC_COMPARISON.value,
                severity=Severity.ERROR.value,
                params={
                    "document_type": DocumentType.TRANSCRIPT.value,
                    "field": "gpa",
                    "operator": RuleOperator.GREATER_THAN_OR_EQUAL.value,
                    "expected_value": "3.0",
                },
            )
        )
    else:
        reference = DocumentRequirement(
            checklist_id=workflow.id,
            document_type=DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
            required=True,
        )
        target = DocumentRequirement(
            checklist_id=workflow.id,
            document_type=DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
            required=True,
        )
        db_session.add_all([reference, target])
        db_session.flush()
        db_session.add_all(
            [
                ValidationRule(
                    requirement_id=target.id,
                    rule_type=RuleType.FIELD_COMPARISON.value,
                    severity=Severity.ERROR.value,
                    params={
                        "source_document_type": DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
                        "source_field": "business_registration_number",
                        "target_document_type": DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
                        "target_field": "business_registration_number",
                        "operator": RuleOperator.EQUALS.value,
                        "value_type": "identifier",
                    },
                ),
                ValidationRule(
                    requirement_id=target.id,
                    rule_type=RuleType.DATE_COMPARISON.value,
                    severity=Severity.ERROR.value,
                    params={
                        "document_type": DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
                        "field": "valid_until",
                        "operator": RuleOperator.ON_OR_AFTER.value,
                        "comparison_source": "EVALUATION_DATE",
                    },
                ),
            ]
        )
    project = Project(owner_id=user.id, checklist_id=workflow.id, name="Phase 7")
    # These focused workflows deliberately require only their rule inputs.
    # Default identity/completeness behavior is tested separately by Astra.
    for required_item in [requirement] if transcript else [reference, target]:
        db_session.add(
            ValidationRule(
                requirement_id=required_item.id,
                rule_type=RuleType.REQUIRED_FIELD.value,
                severity=Severity.WARNING.value,
                params={"field": "gpa" if transcript else "business_registration_number"},
            )
        )
    db_session.add(project)
    db_session.flush()
    submission = Submission(project_id=project.id)
    db_session.add(submission)
    db_session.commit()
    return project, submission


def _document(
    db_session,
    submission,
    document_type: DocumentType,
    values: dict[str, tuple[str | None, float | None]],
):
    document = Document(
        submission_id=submission.id,
        original_filename=f"{uuid.uuid4()}.pdf",
        storage_key=f"phase7/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        checksum_sha256=uuid.uuid4().hex,
        processing_status=ProcessingStatus.COMPLETED.value,
        document_type=document_type.value,
        processing_version=1,
    )
    db_session.add(document)
    db_session.flush()
    fields = {}
    for name, (value, confidence) in values.items():
        field = ExtractedField(
            document_id=document.id,
            field_name=name,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            needs_review=value is None,
            extraction_method="test",
            evidence=(
                [
                    {
                        "page_number": 1,
                        "source_text": "redacted fixture",
                        "bounding_box": None,
                        "confidence": confidence,
                        "source_kind": "ocr"
                        if confidence is not None and confidence < 0.9
                        else "embedded_pdf_text",
                        "coordinate_space": "pixel",
                    }
                ]
                if value is not None
                else None
            ),
        )
        db_session.add(field)
        fields[name] = field
    db_session.commit()
    return document, fields


def _verify(client: TestClient, project_id: uuid.UUID) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/verify",
        json={"evaluation_date": "2026-09-22"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _review(
    client: TestClient,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    field_name: str,
    decision: str,
    corrected_value: str | None = None,
):
    payload = {
        "decision": decision,
        "reviewer_label": "reviewer-1",
        "expected_processing_version": 1,
    }
    if corrected_value is not None:
        payload["corrected_value"] = corrected_value
    return client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/fields/{field_name}/review",
        json=payload,
    )


def test_confirm_low_confidence_value_preserves_machine_and_enables_rule(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session)
    _, reference_fields = _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": ("1234567890", 0.95)},
    )
    target, target_fields = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {
            "business_registration_number": ("1234567890", 0.80),
            "valid_until": ("2026-12-31", 0.95),
        },
    )
    db_session.commit()
    original = target_fields["business_registration_number"]
    before = (original.raw_value, original.normalized_value, original.confidence, original.evidence)

    initial = _verify(client, project.id)
    response = _review(
        client,
        project.id,
        target.id,
        "business_registration_number",
        "CONFIRMED",
    )
    latest = client.get(f"/api/v1/projects/{project.id}/verification").json()
    final = _verify(client, project.id)
    detail = client.get(f"/api/v1/documents/{target.id}").json()

    assert initial["status"] == "REVIEW_REQUIRED"
    assert {item["code"] for item in initial["issues"]} == {"OCR_UNCERTAIN"}
    assert response.status_code == 201
    assert len(response.json()["original_evidence_fingerprint"]) == 64
    assert latest["is_current"] is False
    assert final["status"] == "READY"
    reviewed_field = next(
        item
        for item in detail["extracted_fields"]
        if item["field_name"] == "business_registration_number"
    )
    assert reviewed_field["evidence_assessment"] == "SUFFICIENT"
    assert reviewed_field["effective_source"] == "HUMAN_CONFIRMED"
    assert reviewed_field["current_review_decision"] == "CONFIRMED"
    db_session.refresh(original)
    assert (
        original.raw_value,
        original.normalized_value,
        original.confidence,
        original.evidence,
    ) == before
    assert reference_fields["business_registration_number"].normalized_value == "1234567890"


def test_correct_false_mismatch_normalizes_without_mutating_machine(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session)
    reference, _ = _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": ("1234567890", 0.95)},
    )
    target, fields = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {
            "business_registration_number": ("9999999999", 0.80),
            "valid_until": ("2026-12-31", 0.95),
        },
    )
    response = _review(
        client,
        project.id,
        target.id,
        "business_registration_number",
        "CORRECTED",
        "123-45-67890",
    )
    result = _verify(client, project.id)

    assert response.status_code == 201
    assert response.json()["reviewed_normalized_value"] == "1234567890"
    assert result["status"] == "READY"
    assert not any(item["code"] == "INFORMATION_MISMATCH" for item in result["issues"])
    db_session.refresh(fields["business_registration_number"])
    assert fields["business_registration_number"].normalized_value == "9999999999"
    assert reference.id != target.id


@pytest.mark.parametrize("invalid", ["ABC-123", "", "   "])
def test_invalid_business_number_correction_is_rejected(
    client: TestClient, db_session, invalid: str
) -> None:
    project, submission = _project(db_session)
    target, _ = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": ("9999999999", 0.80)},
    )
    response = _review(
        client,
        project.id,
        target.id,
        "business_registration_number",
        "CORRECTED",
        invalid,
    )
    assert response.status_code in {400, 422}
    assert db_session.query(FieldReview).filter_by(document_id=target.id).count() == 0


@pytest.mark.parametrize(
    ("value", "expected_status", "expected_code"),
    [
        ("2026-12-31", "READY", None),
        ("2026-09-01", "NEEDS_CORRECTION", "EXPIRED_DOCUMENT"),
    ],
)
def test_fill_missing_valid_until_then_rules_decide(
    client: TestClient,
    db_session,
    value: str,
    expected_status: str,
    expected_code: str | None,
) -> None:
    project, submission = _project(db_session)
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": ("1234567890", 0.95)},
    )
    target, _ = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {
            "business_registration_number": ("1234567890", 0.95),
            "valid_until": (None, None),
        },
    )
    response = _review(client, project.id, target.id, "valid_until", "CORRECTED", value)
    result = _verify(client, project.id)
    assert response.status_code == 201
    assert response.json()["reviewed_normalized_value"] == value
    assert result["status"] == expected_status
    assert (
        (expected_code in {item["code"] for item in result["issues"]})
        if expected_code
        else not result["issues"]
    )


@pytest.mark.parametrize(
    ("value", "expected_status", "expected_code"),
    [("3.85", "READY", None), ("2.80", "NEEDS_CORRECTION", "RULE_CONDITION_NOT_MET")],
)
def test_fill_missing_gpa_then_rules_decide(
    client: TestClient,
    db_session,
    value: str,
    expected_status: str,
    expected_code: str | None,
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(db_session, submission, DocumentType.TRANSCRIPT, {"gpa": (None, None)})
    response = _review(client, project.id, document.id, "gpa", "CORRECTED", value)
    result = _verify(client, project.id)
    assert response.status_code == 201
    assert result["status"] == expected_status
    assert (
        (expected_code in {item["code"] for item in result["issues"]})
        if expected_code
        else not result["issues"]
    )


@pytest.mark.parametrize("decision", ["REJECTED", "CANNOT_DETERMINE"])
def test_unavailable_human_decisions_remain_unresolved(
    client: TestClient, db_session, decision: str
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.85", 0.95)}
    )
    response = _review(client, project.id, document.id, "gpa", decision)
    result = _verify(client, project.id)
    assert response.status_code == 201
    assert result["status"] == "REVIEW_REQUIRED"
    assert {item["code"] for item in result["issues"]} == {"REQUIRED_FIELD_UNRESOLVED"}


def test_confirm_real_mismatch_still_fails_business_rule(client: TestClient, db_session) -> None:
    project, submission = _project(db_session)
    reference, _ = _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": ("1234567890", 0.80)},
    )
    target, _ = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {
            "business_registration_number": ("9999999999", 0.80),
            "valid_until": ("2026-12-31", 0.95),
        },
    )
    assert (
        _review(
            client, project.id, reference.id, "business_registration_number", "CONFIRMED"
        ).status_code
        == 201
    )
    assert (
        _review(
            client, project.id, target.id, "business_registration_number", "CONFIRMED"
        ).status_code
        == 201
    )
    result = _verify(client, project.id)
    assert result["status"] == "NEEDS_CORRECTION"
    assert {item["code"] for item in result["issues"]} == {"INFORMATION_MISMATCH"}


def test_review_queue_is_rule_dependent_and_project_isolated(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(
        db_session,
        submission,
        DocumentType.TRANSCRIPT,
        {"gpa": ("3.85", 0.80), "student_name": ("학생", 0.70)},
    )
    other, _ = _project(db_session, transcript=True)
    queue = client.get(f"/api/v1/projects/{project.id}/review-items")
    forbidden = _review(client, other.id, document.id, "gpa", "CONFIRMED")
    assert queue.status_code == 200
    assert [item["field_name"] for item in queue.json()] == ["gpa"]
    assert queue.json()[0]["assessment_reasons"] == [
        "OCR_REQUIRES_CONFIRMATION",
        "OCR_CONFIDENCE_BELOW_POLICY",
    ]
    assert forbidden.status_code == 404


def test_repeated_and_replaced_reviews_have_one_current_record(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.85", 0.80)}
    )
    first = _review(client, project.id, document.id, "gpa", "CONFIRMED")
    repeated = _review(client, project.id, document.id, "gpa", "CONFIRMED")
    replaced = _review(client, project.id, document.id, "gpa", "CORRECTED", "3.90")
    history = client.get(
        f"/api/v1/projects/{project.id}/reviews", params={"include_history": True}
    ).json()
    assert first.json()["id"] == repeated.json()["id"]
    assert replaced.status_code == 201
    assert len(history) == 2
    assert sum(item["is_current"] for item in history) == 1
    assert next(item for item in history if item["is_current"])["decision"] == "CORRECTED"


def test_missing_row_can_be_reviewed_by_canonical_field_name(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(db_session, submission, DocumentType.TRANSCRIPT, {})
    response = _review(client, project.id, document.id, "gpa", "CORRECTED", "3.85")
    result = _verify(client, project.id)
    assert response.status_code == 201
    assert response.json()["extracted_field_id"] is None
    assert response.json()["original_normalized_value"] is None
    assert result["status"] == "READY"


def test_stale_review_is_not_used_after_processing_version_changes(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("2.0", 0.80)})
    response = _review(client, project.id, document.id, "gpa", "CORRECTED", "3.85")
    assert response.status_code == 201
    assert _verify(client, project.id)["status"] == "READY"

    invalidate_document_reviews(db_session, document.id)
    document.processing_version += 1
    invalidate_submission_verification(db_session, project.id)
    db_session.commit()
    result = _verify(client, project.id)
    history = client.get(
        f"/api/v1/projects/{project.id}/reviews", params={"include_history": True}
    ).json()

    assert result["status"] == "REVIEW_REQUIRED"
    assert {item["code"] for item in result["issues"]} == {"OCR_UNCERTAIN"}
    assert history[0]["is_current"] is False
    assert history[0]["stale_at"] is not None


def test_workflow_invalidation_does_not_destroy_evidence_review(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.85", 0.80)}
    )
    assert _review(client, project.id, document.id, "gpa", "CONFIRMED").status_code == 201
    assert _verify(client, project.id)["status"] == "READY"
    invalidate_submission_verification(db_session, project.id)
    db_session.commit()

    reviews = client.get(f"/api/v1/projects/{project.id}/reviews").json()
    verification = client.get(f"/api/v1/projects/{project.id}/verification").json()
    assert len(reviews) == 1
    assert reviews[0]["is_current"] is True
    assert verification["is_current"] is False


def test_review_request_decision_combinations_and_unknown_targets(
    client: TestClient, db_session
) -> None:
    project, submission = _project(db_session, transcript=True)
    document, _ = _document(
        db_session, submission, DocumentType.TRANSCRIPT, {"gpa": ("3.85", 0.80)}
    )
    bad_confirm = client.post(
        f"/api/v1/projects/{project.id}/documents/{document.id}/fields/gpa/review",
        json={"decision": "CONFIRMED", "corrected_value": "3.9"},
    )
    unknown_field = _review(client, project.id, document.id, "not_a_field", "CONFIRMED")
    invalid_id = client.post(
        f"/api/v1/projects/{project.id}/documents/{uuid.uuid4()}/fields/gpa/review",
        json={"decision": "CONFIRMED", "expected_processing_version": 1},
    )
    assert bad_confirm.status_code == 422
    assert unknown_field.status_code == 400
    assert invalid_id.status_code == 404
