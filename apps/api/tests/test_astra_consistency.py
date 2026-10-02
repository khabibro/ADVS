"""Behavioral safety tests with separate database sessions and controlled overlap.

No real document content is used. Thread events create overlap at transaction
boundaries; assertions concern persisted generations/decisions, never timing.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Event

import pytest
from sqlalchemy import select

from app.core.domain import OverallStatus
from app.core.errors import ProcessingErrorCode
from app.db.session import SessionLocal
from app.document_intelligence.evidence_sufficiency import FieldReviewDecision
from app.document_intelligence.ocr.models import OCRProviderError
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    ExtractedField,
    FieldReview,
    Project,
    Submission,
    User,
    ValidationResult,
    ValidationRule,
)
from app.services.consistency import lock_project
from app.services.processing import DocumentProcessingService
from app.services.reviews import FieldReviewService, StaleReviewError
from app.services.verification import (
    SubmissionVerificationService,
    invalidate_submission_verification,
)


@pytest.fixture
def ready_case(db_session):
    user = User(email=f"astra-{uuid.uuid4()}@example.invalid", display_name="Synthetic")
    workflow = Checklist(name="Astra test workflow")
    db_session.add_all([user, workflow])
    db_session.flush()
    requirement = DocumentRequirement(
        checklist_id=workflow.id, document_type="TRANSCRIPT", required=True
    )
    db_session.add(requirement)
    db_session.flush()
    db_session.add(
        ValidationRule(
            requirement_id=requirement.id,
            rule_type="REQUIRED_FIELD",
            severity="WARNING",
            params={"field": "gpa"},
        )
    )
    project = Project(owner_id=user.id, checklist_id=workflow.id, name="Synthetic")
    db_session.add(project)
    db_session.flush()
    submission = Submission(project_id=project.id)
    db_session.add(submission)
    db_session.flush()
    document = Document(
        submission_id=submission.id,
        original_filename="synthetic.pdf",
        storage_key=f"{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        checksum_sha256=uuid.uuid4().hex,
        processing_status="COMPLETED",
        document_type="TRANSCRIPT",
        processing_version=1,
    )
    db_session.add(document)
    db_session.flush()
    field = ExtractedField(
        document_id=document.id,
        field_name="gpa",
        raw_value="3.5",
        normalized_value="3.5",
        needs_review=False,
        evidence=[
            {
                "source_kind": "embedded_pdf_text",
                "page_number": 1,
                "source_text": "synthetic",
                "coordinate_space": "pdf_points",
            }
        ],
    )
    db_session.add(field)
    db_session.commit()
    return project.id, document.id, field.id, requirement.id


def verify(project_id):
    with SessionLocal() as db:
        return SubmissionVerificationService().verify(db, project_id, date(2026, 9, 29))


def review(project_id, document_id, decision=FieldReviewDecision.CONFIRMED, value=None, expected=1):
    with SessionLocal() as db:
        service = FieldReviewService()
        target = service.target(db, project_id, document_id, "gpa")
        assert target is not None
        result = service.submit(
            db,
            target,
            decision=decision,
            corrected_value=value,
            reviewer_label="synthetic",
            note=None,
            expected_processing_version=expected,
        )
        return result.id


def test_workflow_default_required_fields_and_explicit_override(db_session, ready_case):
    project_id, document_id, _, requirement_id = ready_case
    requirement = db_session.get(DocumentRequirement, requirement_id)
    requirement.document_type = "ENROLLMENT_CERTIFICATE"
    requirement.rules.clear()
    document = db_session.get(Document, document_id)
    document.document_type = "ENROLLMENT_CERTIFICATE"
    for name, value in {"student_name": "가상학생", "issue_date": "2026-09-29"}.items():
        db_session.add(
            ExtractedField(
                document_id=document_id,
                field_name=name,
                raw_value=value,
                normalized_value=value,
                needs_review=False,
                evidence=[{"source_kind": "embedded_pdf_text"}],
            )
        )
    db_session.commit()
    result = verify(project_id).result
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert {issue.field_name for issue in result.issues} == {"university_name"}
    db_session.add(
        ValidationRule(
            requirement_id=requirement_id,
            rule_type="REQUIRED_FIELD",
            severity="WARNING",
            params={"field": "student_name"},
        )
    )
    db_session.commit()
    assert verify(project_id).result.status == OverallStatus.READY


@pytest.mark.parametrize(
    "state,code",
    [
        ("UNKNOWN", "UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW"),
        ("AMBIGUOUS", "CLASSIFICATION_REQUIRES_REVIEW"),
        ("FAILED", "DOCUMENT_PROCESSING_FAILED"),
        ("OCR_PROCESSING", "DOCUMENT_PROCESSING_IN_PROGRESS"),
    ],
)
def test_required_document_uncertainty_is_never_ready(db_session, ready_case, state, code):
    project_id, document_id, _, _ = ready_case
    document = db_session.get(Document, document_id)
    if state == "UNKNOWN":
        document.document_type = "UNKNOWN"
    elif state == "AMBIGUOUS":
        document.classification_meta = {"needs_review": True}
    else:
        document.processing_status = state
    db_session.commit()
    result = verify(project_id).result
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert code in {issue.code for issue in result.issues}


def test_high_ocr_score_does_not_authorize_deterministic_use(db_session, ready_case):
    project_id, _, field_id, _ = ready_case
    field = db_session.get(ExtractedField, field_id)
    field.evidence = [{"source_kind": "ocr", "confidence": 0.9999}]
    field.confidence = 0.9999
    db_session.commit()
    assert verify(project_id).result.status == OverallStatus.REVIEW_REQUIRED


def test_stale_review_is_explicit_conflict(client, db_session, ready_case):
    project_id, document_id, _, _ = ready_case
    document = db_session.get(Document, document_id)
    document.processing_version = 2
    db_session.commit()
    response = client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/fields/gpa/review",
        json={"decision": "CONFIRMED", "expected_processing_version": 1},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STALE_PROCESSING_VERSION"
    assert (
        db_session.scalar(select(FieldReview).where(FieldReview.document_id == document_id)) is None
    )


@pytest.mark.parametrize(
    "decision", [FieldReviewDecision.REJECTED, FieldReviewDecision.CANNOT_DETERMINE]
)
def test_unavailable_reviews_keep_distinct_pending_actions(ready_case, decision):
    project_id, document_id, _, _ = ready_case
    review(project_id, document_id, decision)
    with SessionLocal() as db:
        items = FieldReviewService().review_items(db, project_id)
    assert items[0]["queue_status"] == decision.value
    assert items[0]["assessment_reasons"] == [f"HUMAN_{decision.value}"]
    assert verify(project_id).result.status == OverallStatus.REVIEW_REQUIRED


def test_snapshot_detects_rule_change_without_explicit_invalidation(db_session, ready_case):
    project_id, _, _, requirement_id = ready_case
    assert verify(project_id).result.status == OverallStatus.READY
    rule = db_session.scalar(
        select(ValidationRule).where(ValidationRule.requirement_id == requirement_id)
    )
    rule.params = {"field": "issue_date"}
    db_session.commit()
    with SessionLocal() as db:
        latest = SubmissionVerificationService().get_latest(db, project_id)
        assert not latest.is_current
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"


def test_snapshot_records_exact_versions_and_stale_generation_invalidates(db_session, ready_case):
    project_id, document_id, _, _ = ready_case
    assert verify(project_id).result.status == OverallStatus.READY
    row = db_session.scalar(
        select(ValidationResult).where(ValidationResult.project_id == project_id)
    )
    assert row.details["input_snapshot"]["document_versions"] == {str(document_id): 1}
    document = db_session.get(Document, document_id)
    document.processing_version = 2
    db_session.commit()
    with SessionLocal() as db:
        assert not SubmissionVerificationService().get_latest(db, project_id).is_current
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"


def test_process_process_review_verify_and_failed_reprocess_preserve_last_good(ready_case):
    project_id, document_id, field_id, _ = ready_case
    review_id = review(project_id, document_id)
    assert verify(project_id).result.status == OverallStatus.READY
    entered, release = Event(), Event()
    calls = []
    first_service = DocumentProcessingService()

    async def fail_source(db, document):
        calls.append(document.id)
        entered.set()
        assert release.wait(5)
        raise OCRProviderError(ProcessingErrorCode.OCR_TIMEOUT)

    first_service._obtain_source = fail_source

    def first_process():
        with SessionLocal() as db:
            return asyncio.run(first_service.process(db, document_id)).processing_status

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_process)
        assert entered.wait(5)
        try:
            with SessionLocal() as db:
                duplicate = asyncio.run(DocumentProcessingService().process(db, document_id))
                assert duplicate.processing_status == "PREPROCESSING"
            assert verify(project_id).result.status == OverallStatus.REVIEW_REQUIRED
            with pytest.raises(StaleReviewError):
                review(project_id, document_id)
        finally:
            release.set()
        assert first.result(timeout=5) == "FAILED"
    assert len(calls) == 1
    with SessionLocal() as db:
        assert db.get(ExtractedField, field_id).normalized_value == "3.5"
        old_review = db.get(FieldReview, review_id)
        assert old_review.is_current and old_review.stale_at is None
        assert db.get(Document, document_id).processing_version == 1
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"
        assert not SubmissionVerificationService().get_latest(db, project_id).is_current


def test_verify_verify_serializes_without_duplicate_rows(ready_case):
    project_id, _, _, _ = ready_case
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(verify, [project_id, project_id]))
    assert all(item.result.status == OverallStatus.READY for item in results)
    with SessionLocal() as db:
        rows = db.scalars(
            select(ValidationResult).where(
                ValidationResult.project_id == project_id, ValidationResult.scope == "SUBMISSION"
            )
        ).all()
        assert len(rows) == len(results[-1].result.rule_results)
        assert SubmissionVerificationService().get_latest(db, project_id).is_current


def test_review_review_serializes_and_keeps_one_current(ready_case):
    project_id, document_id, _, _ = ready_case
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(review, project_id, document_id, FieldReviewDecision.CORRECTED, "3.6")
        second = pool.submit(review, project_id, document_id, FieldReviewDecision.CORRECTED, "3.7")
        assert first.result(timeout=5) != second.result(timeout=5)
    with SessionLocal() as db:
        rows = db.scalars(select(FieldReview).where(FieldReview.document_id == document_id)).all()
        assert len(rows) == 2
        assert sum(item.is_current for item in rows) == 1
        assert sum(item.superseded_at is not None for item in rows) == 1


def test_project_update_waiting_on_verify_invalidates_ready(ready_case):
    project_id, _, _, _ = ready_case
    entered, release = Event(), Event()
    service = SubmissionVerificationService()
    real_verify = service.engine.verify

    def paused_verify(**kwargs):
        entered.set()
        assert release.wait(5)
        return real_verify(**kwargs)

    service.engine.verify = paused_verify

    def verifying():
        with SessionLocal() as db:
            return service.verify(db, project_id, date(2026, 9, 29))

    def updating():
        with SessionLocal() as db:
            project = lock_project(db, project_id)
            project.name = "Updated synthetic"
            invalidate_submission_verification(db, project_id)
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(verifying)
        assert entered.wait(5)
        second = pool.submit(updating)
        release.set()
        assert first.result(timeout=5).result.status == OverallStatus.READY
        second.result(timeout=5)
    with SessionLocal() as db:
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"
        assert not SubmissionVerificationService().get_latest(db, project_id).is_current


def test_delete_rejects_active_processing_and_missing_is_404(client, db_session, ready_case):
    project_id, document_id, _, _ = ready_case
    document = db_session.get(Document, document_id)
    document.processing_status = "OCR_PROCESSING"
    db_session.commit()
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 409
    assert db_session.get(Document, document_id) is not None
    assert client.delete(f"/api/v1/projects/{uuid.uuid4()}").status_code == 404


def test_human_corrected_missing_row_appears_in_document_detail(client, ready_case):
    project_id, document_id, _, _ = ready_case
    response = client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/fields/student_id/review",
        json={
            "decision": "CORRECTED",
            "corrected_value": "20260000",
            "expected_processing_version": 1,
        },
    )
    assert response.status_code == 201
    detail = client.get(f"/api/v1/documents/{document_id}").json()
    assert "student_id" not in detail["missing_expected_fields"]
    assert (
        next(item for item in detail["extracted_fields"] if item["field_name"] == "student_id")[
            "effective_normalized_value"
        ]
        == "20260000"
    )
