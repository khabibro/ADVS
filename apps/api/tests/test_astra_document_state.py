import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Event

import pytest
from test_astra_consistency import ready_case as ready_case
from test_astra_consistency import review, verify

from app.core.domain import DocumentType, OverallStatus, RuleType, Severity
from app.core.errors import ProcessingErrorCode
from app.db.session import SessionLocal
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.ocr.models import (
    OCRDocumentResult,
    OCRLine,
    OCRPage,
    OCRProviderError,
)
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine
from app.document_intelligence.validation.submission import RuleConfigurationError
from app.models.entities import (
    Document,
    DocumentRequirement,
    ExtractedField,
    FieldReview,
    Project,
    ValidationRule,
)
from app.services.processing import DocumentProcessingService
from app.services.reviews import StaleReviewError
from app.services.verification import SubmissionVerificationService
from scripts.recover_processing import recover_document


def test_successful_reprocess_switches_generation_then_stales_review(ready_case):
    project_id, document_id, field_id, _ = ready_case
    review_id = review(project_id, document_id)
    service = DocumentProcessingService()
    text = "성적증명서\n평점평균: 3.5\n발급일자: 2026.09.29"

    async def source(db, document):
        return OCRDocumentResult(
            "direct_pdf_text",
            [
                OCRPage(
                    1,
                    text,
                    [OCRLine(line) for line in text.splitlines()],
                    metadata={"source": "direct_pdf_text"},
                )
            ],
            text,
        )

    service._obtain_source = source
    with SessionLocal() as db:
        result = asyncio.run(service.process(db, document_id))
        assert result.processing_status == "COMPLETED"
        assert result.processing_version == 2
        assert db.get(ExtractedField, field_id) is None
        old_review = db.get(FieldReview, review_id)
        assert not old_review.is_current and old_review.stale_at is not None
    with pytest.raises(StaleReviewError):
        review(project_id, document_id, expected=1)


def test_verify_then_processing_cannot_leave_ready_without_support(ready_case):
    project_id, document_id, _, _ = ready_case
    entered, release = Event(), Event()
    verification = SubmissionVerificationService()
    original = verification.engine.verify

    def paused(**kwargs):
        entered.set()
        assert release.wait(5)
        return original(**kwargs)

    verification.engine.verify = paused

    def verifying():
        with SessionLocal() as db:
            return verification.verify(db, project_id, date(2026, 9, 29))

    def processing():
        with SessionLocal() as db:
            service = DocumentProcessingService()

            async def fail(db, document):
                raise OCRProviderError(ProcessingErrorCode.OCR_TIMEOUT)

            service._obtain_source = fail
            return asyncio.run(service.process(db, document_id)).processing_status

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(verifying)
        assert entered.wait(5)
        second = pool.submit(processing)
        release.set()
        assert first.result(timeout=5).result.status == OverallStatus.READY
        assert second.result(timeout=5) == "FAILED"
    with SessionLocal() as db:
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"
        assert not SubmissionVerificationService().get_latest(db, project_id).is_current


def test_offline_recovery_requires_stopped_worker_assertion(ready_case):
    project_id, document_id, field_id, _ = ready_case
    review_id = review(project_id, document_id)
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        document.processing_status = "OCR_PROCESSING"
        db.commit()
        with pytest.raises(ValueError):
            recover_document(db, document_id, workers_stopped=False)
        assert recover_document(db, document_id, workers_stopped=True)
        assert db.get(Document, document_id).processing_version == 1
        assert db.get(Document, document_id).processing_status == "FAILED"
        assert db.get(ExtractedField, field_id) is not None
        assert db.get(FieldReview, review_id).is_current
        assert db.get(Project, project_id).status == "REVIEW_REQUIRED"


def test_human_correction_recomputes_document_expiry(client, db_session, ready_case):
    project_id, document_id, field_id, requirement_id = ready_case
    document = db_session.get(Document, document_id)
    document.document_type = "SME_CONFIRMATION_CERTIFICATE"
    requirement = db_session.get(DocumentRequirement, requirement_id)
    requirement.document_type = "SME_CONFIRMATION_CERTIFICATE"
    requirement.rules[0].params = {"field": "valid_until"}
    field = db_session.get(ExtractedField, field_id)
    field.field_name = "valid_until"
    field.raw_value = field.normalized_value = "2000-01-01"
    db_session.commit()
    assert (
        client.get(f"/api/v1/documents/{document_id}").json()["overall_status"]
        == "NEEDS_CORRECTION"
    )
    response = client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/fields/valid_until/review",
        json={
            "decision": "CORRECTED",
            "corrected_value": "2099-12-31",
            "expected_processing_version": 1,
        },
    )
    assert response.status_code == 201
    detail = client.get(f"/api/v1/documents/{document_id}").json()
    assert detail["overall_status"] == "READY"
    assert not any(item["code"] == "EXPIRED_DOCUMENT" for item in detail["validation_results"])


def test_unsupported_persisted_rule_cannot_silently_authorize_ready(db_session, ready_case):
    project_id, _, _, requirement_id = ready_case
    db_session.add(
        ValidationRule(
            requirement_id=requirement_id,
            rule_type="CUSTOM_TEXT_RULE",
            severity="ERROR",
            params={"field": "student_name", "equals": "가상학생"},
        )
    )
    db_session.commit()
    with pytest.raises(RuleConfigurationError):
        verify(project_id)


def test_issue_age_uses_evaluation_date_and_unavailable_never_fails(db_session, ready_case):
    project_id, _, field_id, requirement_id = ready_case
    requirement = db_session.get(DocumentRequirement, requirement_id)
    requirement.rules[0].params = {"field": "issue_date"}
    db_session.add(
        ValidationRule(
            requirement_id=requirement_id,
            rule_type="ISSUE_DATE_MAX_AGE",
            severity="ERROR",
            params={"max_age_days": 30},
        )
    )
    field = db_session.get(ExtractedField, field_id)
    field.field_name = "issue_date"
    field.normalized_value = "2026-09-01"
    db_session.commit()
    assert verify(project_id).result.status == OverallStatus.READY
    field.normalized_value = "2026-01-01"
    db_session.commit()
    assert verify(project_id).result.status == OverallStatus.NEEDS_CORRECTION
    field.normalized_value = None
    db_session.commit()
    result = verify(project_id).result
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert all(item.outcome != "FAIL" for item in result.rule_results)


@pytest.mark.parametrize(
    "name",
    ["company_name", "applicant_name", "business_registration_number", "valid_until", "issue_date"],
)
def test_missing_or_uncertain_value_never_becomes_deterministic_failure(name):
    engine = ValidationEngine()
    for value in (
        None,
        "2000-01-01" if name.endswith("date") or name == "valid_until" else "untrusted",
    ):
        fields = [ExtractedValue(name, value, value, 0.99, True)]
        rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.ERROR, {"field": name})]
        if name == "valid_until":
            rules.append(ConfiguredRule(RuleType.DATE_NOT_EXPIRED, Severity.ERROR, {"field": name}))
        if name == "issue_date":
            rules.append(
                ConfiguredRule(RuleType.ISSUE_DATE_MAX_AGE, Severity.ERROR, {"field": name})
            )
        if name == "business_registration_number":
            rules.append(
                ConfiguredRule(
                    RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH,
                    Severity.ERROR,
                    {"expected_value": "1111111111"},
                )
            )
        issues = engine.validate_document(
            None,
            DocumentType.CAREER_CERTIFICATE,
            fields,
            applicant_name="synthetic",
            company_name="synthetic",
            configured_rules=rules,
        )
        assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED
        assert not any(
            issue.code
            in {
                "APPLICANT_NAME_MISMATCH",
                "COMPANY_NAME_MISMATCH",
                "BUSINESS_NUMBER_MISMATCH",
                "EXPIRED_DOCUMENT",
                "ISSUE_DATE_TOO_OLD",
            }
            for issue in issues
        )
