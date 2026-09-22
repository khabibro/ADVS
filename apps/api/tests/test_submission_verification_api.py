import uuid
from pathlib import Path
from runpy import run_path

import fitz
from fastapi.testclient import TestClient

from app.core.domain import (
    DocumentType,
    OverallStatus,
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
    Project,
    Submission,
    User,
    ValidationResult,
    ValidationRule,
)
from app.services.verification import SUBMISSION_SCOPE


def _blank_pdf_bytes() -> bytes:
    pdf = fitz.open()
    pdf.new_page()
    value = pdf.tobytes()
    pdf.close()
    return value


def _business_project(db_session):
    user = User(email=f"phase6-{uuid.uuid4()}@advs.local", display_name="Phase 6")
    workflow = Checklist(name=f"Phase 6 workflow {uuid.uuid4()}")
    db_session.add_all([user, workflow])
    db_session.flush()
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
                requirement_id=reference.id,
                rule_type=RuleType.REQUIRED_FIELD.value,
                severity=Severity.WARNING.value,
                params={},
            ),
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
    project = Project(owner_id=user.id, checklist_id=workflow.id, name="Phase 6 project")
    db_session.add(project)
    db_session.flush()
    submission = Submission(project_id=project.id)
    db_session.add(submission)
    db_session.flush()
    db_session.commit()
    return project, submission, target


def _document(db_session, submission, document_type: DocumentType, values: dict[str, str | None]):
    row = Document(
        submission_id=submission.id,
        original_filename=f"{document_type.value}.pdf",
        storage_key=f"test/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        checksum_sha256=uuid.uuid4().hex,
        processing_status=ProcessingStatus.COMPLETED.value,
        document_type=document_type.value,
    )
    db_session.add(row)
    db_session.flush()
    for name, value in values.items():
        db_session.add(
            ExtractedField(
                document_id=row.id,
                field_name=name,
                raw_value=value,
                normalized_value=value,
                needs_review=value is None,
                evidence=[{"page_number": 1}] if value is not None else None,
            )
        )
    db_session.flush()
    return row


def _verify(client: TestClient, project_id: uuid.UUID) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/verify",
        json={"evaluation_date": "2026-09-22"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_verify_and_read_persisted_result_without_ocr(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": "1234567890", "valid_until": "2026-12-31"},
    )
    db_session.commit()

    created = _verify(client, project.id)
    read = client.get(f"/api/v1/projects/{project.id}/verification")

    assert created["status"] == "READY"
    assert created["issues"] == []
    assert created["evaluation_date"] == "2026-09-22"
    assert created["is_current"] is True
    assert read.status_code == 200
    assert read.json()["status"] == "READY"
    assert read.json()["rule_results"] == created["rule_results"]


def test_reverification_replaces_results_and_corrected_mismatch_disappears(
    client: TestClient, db_session
) -> None:
    project, submission, _ = _business_project(db_session)
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    target = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": "9999999999", "valid_until": "2026-12-31"},
    )
    db_session.commit()

    first = _verify(client, project.id)
    first_count = (
        db_session.query(ValidationResult)
        .filter_by(project_id=project.id, scope=SUBMISSION_SCOPE)
        .count()
    )
    number = (
        db_session.query(ExtractedField)
        .filter_by(document_id=target.id, field_name="business_registration_number")
        .one()
    )
    number.raw_value = "1234567890"
    number.normalized_value = "1234567890"
    db_session.commit()
    second = _verify(client, project.id)
    second_count = (
        db_session.query(ValidationResult)
        .filter_by(project_id=project.id, scope=SUBMISSION_SCOPE)
        .count()
    )

    assert first["status"] == "NEEDS_CORRECTION"
    assert {item["code"] for item in first["issues"]} == {"INFORMATION_MISMATCH"}
    assert second["status"] == "READY"
    assert second["issues"] == []
    assert second_count == first_count


def test_upload_invalidates_stale_ready(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": "1234567890", "valid_until": "2026-12-31"},
    )
    db_session.commit()
    assert _verify(client, project.id)["status"] == "READY"

    upload = client.post(
        f"/api/v1/projects/{project.id}/documents",
        files={"file": ("replacement.pdf", _blank_pdf_bytes(), "application/pdf")},
    )
    latest = client.get(f"/api/v1/projects/{project.id}/verification")

    assert upload.status_code == 201
    assert latest.status_code == 200
    assert latest.json()["status"] == OverallStatus.REVIEW_REQUIRED.value
    assert latest.json()["is_current"] is False
    assert latest.json()["evaluated_at"] is None
    assert (
        db_session.query(ValidationResult)
        .filter_by(project_id=project.id, scope=SUBMISSION_SCOPE)
        .count()
        == 0
    )


def test_reprocessing_invalidates_stale_ready(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    target = _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": "1234567890", "valid_until": "2026-12-31"},
    )
    db_session.commit()
    assert _verify(client, project.id)["status"] == "READY"

    # The synthetic row has no backing file; reprocessing therefore fails,
    # but the old READY decision must already have been invalidated.
    processed = client.post(f"/api/v1/documents/{target.id}/process")
    latest = client.get(f"/api/v1/projects/{project.id}/verification")

    assert processed.status_code == 200
    assert processed.json()["processing_status"] == "FAILED"
    assert latest.status_code == 200
    assert latest.json()["status"] == "REVIEW_REQUIRED"
    assert latest.json()["is_current"] is False


def test_invalid_persisted_rule_returns_safe_api_error(client: TestClient, db_session) -> None:
    project, submission, target_requirement = _business_project(db_session)
    bad_rule = target_requirement.rules[0]
    bad_rule.params = {**bad_rule.params, "source_field": "not_a_field"}
    _document(
        db_session,
        submission,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        {"business_registration_number": "1234567890"},
    )
    _document(
        db_session,
        submission,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        {"business_registration_number": "1234567890", "valid_until": "2026-12-31"},
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/verify",
        json={"evaluation_date": "2026-09-22"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_FAILED"
    assert "Unknown source_field" in response.json()["detail"]["message"]


def test_workflow_seed_is_idempotent(db_session) -> None:
    seed = run_path(str(Path(__file__).parents[3] / "scripts" / "seed.py"))
    name = f"Idempotent workflow {uuid.uuid4()}"
    specifications = [
        (
            DocumentType.TRANSCRIPT,
            False,
            [
                (
                    RuleType.NUMERIC_COMPARISON,
                    Severity.ERROR,
                    {
                        "document_type": DocumentType.TRANSCRIPT.value,
                        "field": "gpa",
                        "operator": RuleOperator.GREATER_THAN_OR_EQUAL.value,
                        "expected_value": "3.0",
                    },
                )
            ],
        )
    ]

    seed["upsert_workflow"](db_session, name, "Configured demo criteria.", specifications)
    db_session.commit()
    workflow = db_session.query(Checklist).filter_by(name=name).one()
    user = User(email=f"seed-{uuid.uuid4()}@advs.local", display_name="Seed")
    db_session.add(user)
    db_session.flush()
    project = Project(
        owner_id=user.id,
        checklist_id=workflow.id,
        name="Seed invalidation project",
        status=OverallStatus.READY.value,
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ValidationResult(
            project_id=project.id,
            rule_type=RuleType.REQUIRED_DOCUMENT.value,
            passed=True,
            severity=Severity.INFO.value,
            message="passed",
            code="RULE_PASSED",
            scope=SUBMISSION_SCOPE,
            outcome="PASS",
            details={"evaluation_date": "2026-09-22"},
        )
    )
    db_session.commit()
    seed["upsert_workflow"](db_session, name, "Configured demo criteria.", specifications)
    db_session.commit()

    db_session.refresh(project)
    workflow = db_session.query(Checklist).filter_by(name=name).one()
    assert len(workflow.requirements) == 1
    assert len(workflow.requirements[0].rules) == 1
    assert project.status == OverallStatus.REVIEW_REQUIRED.value
    assert (
        db_session.query(ValidationResult)
        .filter_by(project_id=project.id, scope=SUBMISSION_SCOPE)
        .count()
        == 0
    )
