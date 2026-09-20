"""End-to-end pipeline tests: real upload -> process -> API response, using
MockOCRProvider (real OCR is never called in this suite). Each test drives the
actual HTTP API, not the service class directly, so it also exercises
routing, persistence, and response shaping."""

import fitz
from fastapi.testclient import TestClient

from app.core.domain import DocumentType, RuleType, Severity
from app.models.entities import Checklist, DocumentRequirement, ValidationRule


def _blank_pdf_bytes() -> bytes:
    """A syntactically valid PDF with no embedded text layer, forcing the
    OCR path rather than direct-PDF-text extraction."""
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def _text_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _create_workflow(db_session) -> Checklist:
    checklist = Checklist(
        name="Integration Test Workflow",
        description="Workflow used by API integration tests.",
    )
    db_session.add(checklist)
    db_session.flush()
    for document_type in (
        DocumentType.GRADUATION_CERTIFICATE,
        DocumentType.CAREER_CERTIFICATE,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
    ):
        requirement = DocumentRequirement(
            checklist_id=checklist.id,
            document_type=document_type.value,
            required=True,
        )
        db_session.add(requirement)
        db_session.flush()
        db_session.add(
            ValidationRule(
                requirement_id=requirement.id,
                rule_type=RuleType.REQUIRED_FIELD,
                severity=Severity.WARNING,
                params={},
            )
        )
    db_session.commit()
    db_session.refresh(checklist)
    return checklist


def _create_project(client: TestClient, db_session, **overrides: object) -> dict:
    workflow = _create_workflow(db_session)
    payload = {"name": "Integration Test Project", "workflow_id": str(workflow.id), **overrides}
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    return response.json()


def _upload(
    client: TestClient, project_id: str, filename: str, content: bytes | None = None
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": (filename, content or _blank_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def _process(client: TestClient, document_id: str) -> dict:
    response = client.post(f"/api/v1/documents/{document_id}/process")
    assert response.status_code == 200
    return response.json()


def _detail(client: TestClient, document_id: str) -> dict:
    response = client.get(f"/api/v1/documents/{document_id}")
    assert response.status_code == 200
    return response.json()


def test_full_pipeline_graduation_certificate_success(client: TestClient, db_session) -> None:
    project = _create_project(client, db_session, applicant_name="홍길동")
    document = _upload(client, project["id"], "graduation_scan.pdf")
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "COMPLETED"
    assert processed["document_type"] == "GRADUATION_CERTIFICATE"
    assert processed["classification_meta"]["classifier_version"]

    detail = _detail(client, document["id"])
    fields = {f["field_name"]: f for f in detail["extracted_fields"]}
    assert fields["applicant_name"]["normalized_value"] == "홍길동"
    assert fields["university_name"]["normalized_value"] == "한국대학교"
    assert fields["graduation_date"]["normalized_value"] == "2024-02-20"
    assert fields["graduation_date"]["extraction_method"] == "regex_date"
    assert detail["overall_status"] == "READY"


def test_full_pipeline_business_registration_success(client: TestClient, db_session) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "business_cert.pdf")
    processed = _process(client, document["id"])

    assert processed["document_type"] == "BUSINESS_REGISTRATION_CERTIFICATE"
    detail = _detail(client, document["id"])
    fields = {f["field_name"]: f for f in detail["extracted_fields"]}
    assert fields["business_registration_number"]["normalized_value"] == "1234567890"
    assert detail["overall_status"] == "READY"


def test_full_pipeline_unknown_document(client: TestClient, db_session) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "unknown_document_scan.pdf")
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "COMPLETED"
    assert processed["document_type"] == "UNKNOWN"
    assert processed["classification_meta"]["needs_review"] is True

    detail = _detail(client, document["id"])
    assert detail["extracted_fields"] == []


def test_full_pipeline_ocr_failure_is_distinct_from_unknown(client: TestClient, db_session) -> None:
    """OCR_PROVIDER_ERROR must not be silently converted into a
    classification of UNKNOWN -- classification must never run at all."""
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "ocr_failure_scan.pdf")
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "FAILED"
    assert processed["error_code"] == "OCR_PROVIDER_ERROR"
    assert processed["classification_confidence"] is None
    assert processed["classification_meta"] is None


def test_full_pipeline_expired_sme_certificate_needs_correction(
    client: TestClient, db_session
) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "sme_expired_scan.pdf")
    processed = _process(client, document["id"])

    assert processed["document_type"] == "SME_CONFIRMATION_CERTIFICATE"
    detail = _detail(client, document["id"])
    fields = {f["field_name"]: f for f in detail["extracted_fields"]}
    assert fields["valid_until"]["normalized_value"] == "2020-01-01"
    assert detail["overall_status"] == "NEEDS_CORRECTION"
    codes = {v["code"] for v in detail["validation_results"]}
    assert "EXPIRED_DOCUMENT" in codes


def test_full_pipeline_missing_fields_are_reviewed_not_guessed(
    client: TestClient, db_session
) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "career_partial_scan.pdf")
    processed = _process(client, document["id"])
    assert processed["processing_status"] == "COMPLETED"
    assert processed["document_type"] == "CAREER_CERTIFICATE"

    detail = _detail(client, document["id"])
    fields = {f["field_name"]: f for f in detail["extracted_fields"]}
    # Present in the partial fixture:
    assert fields["applicant_name"]["normalized_value"] == "김철수"
    assert fields["company_name"]["normalized_value"] == "한국테크"
    # Absent from the partial fixture -- must be null and flagged for
    # review, never a fabricated value.
    for missing_field in ("position", "employment_start_date", "employment_end_date", "issue_date"):
        assert fields[missing_field]["normalized_value"] is None
        assert fields[missing_field]["raw_value"] is None
        assert fields[missing_field]["needs_review"] is True
    assert detail["overall_status"] == "REVIEW_REQUIRED"


def test_digital_pdf_with_meaningful_text_skips_ocr_provider(
    client: TestClient, db_session, monkeypatch
) -> None:
    import uuid as uuid_module

    from app.models.entities import OCRResult

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR provider should not be called for usable digital PDF text")

    class ExplodingProvider:
        extract_document = fail_if_called

    def exploding_provider(_settings):
        return ExplodingProvider()

    monkeypatch.setattr("app.services.processing.get_ocr_provider", exploding_provider)
    project = _create_project(client, db_session, applicant_name="홍길동")
    content = _text_pdf_bytes(
        "졸업증명서\n성명 홍길동\n대학교 한국대학교\n학과 컴퓨터공학과\n학위 학사\n"
        "졸업일자 2024-02-20\n발급일자 2026-01-10"
    )
    document = _upload(client, project["id"], "graduation_digital.pdf", content)
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "COMPLETED"
    detail = _detail(client, document["id"])
    assert detail["overall_status"] == "READY"
    ocr_row = (
        db_session.query(OCRResult).filter_by(document_id=uuid_module.UUID(document["id"])).one()
    )
    assert ocr_row.provider == "direct_pdf_text"
    assert ocr_row.lines == []


def test_reprocessing_same_document_does_not_duplicate_rows(client: TestClient, db_session) -> None:
    import uuid as uuid_module

    from app.models.entities import Document, ExtractedField, OCRResult, ValidationResult

    project = _create_project(client, db_session, applicant_name="홍길동")
    document = _upload(client, project["id"], "graduation_scan.pdf")
    _process(client, document["id"])
    doc_uuid = uuid_module.UUID(document["id"])

    def row_counts() -> tuple[int, int, int]:
        return (
            db_session.query(OCRResult).filter_by(document_id=doc_uuid).count(),
            db_session.query(ExtractedField).filter_by(document_id=doc_uuid).count(),
            db_session.query(ValidationResult).filter_by(document_id=doc_uuid).count(),
        )

    first_counts = row_counts()
    assert first_counts[0] > 0
    assert first_counts[1] > 0

    # Simulate a retry (e.g. after a transient failure) by putting the
    # document back into a reprocessable state -- /process short-circuits on
    # COMPLETED by design, so this bypasses that guard the way a real retry
    # of a FAILED document would.
    db_row = db_session.get(Document, doc_uuid)
    db_row.processing_status = "UPLOADED"
    db_session.commit()

    _process(client, document["id"])
    assert row_counts() == first_counts
