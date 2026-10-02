"""End-to-end pipeline tests: real upload -> process -> API response, using
MockOCRProvider (real OCR is never called in this suite). Each test drives the
actual HTTP API, not the service class directly, so it also exercises
routing, persistence, and response shaping."""

import uuid
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    ExtractedField,
    OCRResult,
    ValidationResult,
    ValidationRule,
)


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
    page.insert_text((72, 72), text, fontsize=12, fontname="korea")
    data = doc.tobytes()
    doc.close()
    return data


def _blank_pdf_bytes_with_pages(page_count: int) -> bytes:
    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def _page(page_number: int, lines: list[str]) -> OCRPage:
    observations = [
        OCRLine(
            text=line,
            confidence=0.97,
            bounding_box=BoundingBox(x=12.0, y=float(index * 30), width=420.0, height=22.0),
        )
        for index, line in enumerate(lines)
    ]
    return OCRPage(
        page_number=page_number,
        text="\n".join(lines),
        lines=observations,
        confidence=0.97,
        metadata={"provider": "controlled"},
    )


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
    assert detail["overall_status"] == "REVIEW_REQUIRED"
    assert "OCR_REQUIRES_CONFIRMATION" in fields["applicant_name"]["assessment_reasons"]


def test_full_pipeline_business_registration_success(client: TestClient, db_session) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "business_cert.pdf")
    processed = _process(client, document["id"])

    assert processed["document_type"] == "BUSINESS_REGISTRATION_CERTIFICATE"
    detail = _detail(client, document["id"])
    fields = {f["field_name"]: f for f in detail["extracted_fields"]}
    assert fields["business_registration_number"]["normalized_value"] == "1234567890"
    evidence = fields["business_registration_number"]["evidence"][0]
    assert evidence["page_number"] == 1
    assert evidence["source_text"] == "사업자등록번호 123-45-67890"
    assert evidence["bounding_box"] == {"x": 10.0, "y": 72.0, "width": 500.0, "height": 20.0}
    assert evidence["confidence"] == 0.99
    assert evidence["coordinate_space"] == "pixel"
    assert detail["missing_expected_fields"] == []
    assert detail["overall_status"] == "REVIEW_REQUIRED"
    assert (
        "OCR_REQUIRES_CONFIRMATION" in fields["business_registration_number"]["assessment_reasons"]
    )


def test_full_pipeline_unknown_document(client: TestClient, db_session) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "unknown_document_scan.pdf")
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "COMPLETED"
    assert processed["document_type"] == "UNKNOWN"
    assert processed["classification_meta"]["needs_review"] is True

    detail = _detail(client, document["id"])
    assert detail["extracted_fields"] == []
    assert detail["overall_status"] == "REVIEW_REQUIRED"


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
    assert _detail(client, document["id"])["overall_status"] == "REVIEW_REQUIRED"


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
    assert detail["overall_status"] == "REVIEW_REQUIRED"
    assert "EXPIRED_DOCUMENT" not in {v["code"] for v in detail["validation_results"]}
    confirmation = client.post(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}/fields/valid_until/review",
        json={
            "decision": "CONFIRMED",
            "expected_processing_version": processed["processing_version"],
        },
    )
    assert confirmation.status_code == 201
    detail = _detail(client, document["id"])
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
    assert ocr_row.lines
    applicant = next(
        field for field in detail["extracted_fields"] if field["field_name"] == "applicant_name"
    )
    assert applicant["evidence"][0]["source_kind"] == "embedded_pdf_text"
    assert applicant["evidence"][0]["coordinate_space"] == "pdf_point"
    assert applicant["evidence"][0]["confidence"] is None


def test_reprocessing_same_document_does_not_duplicate_rows(client: TestClient, db_session) -> None:
    import uuid as uuid_module

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

    _process(client, document["id"])
    assert row_counts() == first_counts


def test_multi_page_raster_pipeline_preserves_page_evidence(
    client: TestClient, db_session, monkeypatch
) -> None:
    class MultiPageProvider:
        async def extract_document(self, *_args, **_kwargs):
            return [
                _page(1, ["사업자등록증", "상호 한국테크"]),
                _page(2, ["사업자등록번호 123-45-67890"]),
            ]

    monkeypatch.setattr(
        "app.services.processing.get_ocr_provider", lambda _settings: MultiPageProvider()
    )
    project = _create_project(client, db_session)
    document = _upload(
        client,
        project["id"],
        "two_page_business.pdf",
        _blank_pdf_bytes_with_pages(2),
    )

    processed = _process(client, document["id"])
    detail = _detail(client, document["id"])
    document_id = uuid.UUID(document["id"])
    registration_number = next(
        field
        for field in detail["extracted_fields"]
        if field["field_name"] == "business_registration_number"
    )
    rows = (
        db_session.query(OCRResult)
        .filter_by(document_id=document_id)
        .order_by(OCRResult.page_number)
        .all()
    )

    assert processed["processing_status"] == "COMPLETED"
    assert [row.page_number for row in rows] == [1, 2]
    assert registration_number["evidence"][0]["page_number"] == 2
    assert registration_number["evidence"][0]["confidence"] == 0.97
    assert registration_number["evidence"][0]["coordinate_space"] == "pixel"


def test_corrupt_stored_pdf_fails_safely_and_clears_derived_state(
    client: TestClient, db_session
) -> None:
    from app.core.config import get_settings

    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "business_corrupt_later.pdf")
    row = db_session.get(Document, uuid.UUID(document["id"]))
    (get_settings().storage_path / row.storage_key).write_bytes(b"%PDF-1.4\ntruncated")

    processed = _process(client, document["id"])

    assert processed["processing_status"] == "FAILED"
    assert processed["error_code"] == "CORRUPT_DOCUMENT"
    assert processed["error_message"] == "File could not be opened; it may be corrupt."
    assert db_session.query(OCRResult).filter_by(document_id=row.id).count() == 0
    assert db_session.query(ExtractedField).filter_by(document_id=row.id).count() == 0


def test_reprocessing_replaces_changed_classification_fields_and_evidence(
    client: TestClient, db_session, monkeypatch
) -> None:
    class ChangingProvider:
        calls = 0

        async def extract_document(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return [
                    _page(
                        1,
                        [
                            "졸업증명서",
                            "성명 홍길동",
                            "대학교 한국대학교",
                            "학과 컴퓨터공학과",
                            "학위 학사",
                            "졸업일자 2024-02-20",
                            "발급일자 2026-01-10",
                        ],
                    )
                ]
            return [
                _page(
                    1,
                    [
                        "사업자등록증",
                        "상호 새회사",
                        "사업자등록번호 111-22-33333",
                    ],
                )
            ]

    provider = ChangingProvider()
    monkeypatch.setattr("app.services.processing.get_ocr_provider", lambda _settings: provider)
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "changing_scan.pdf")
    document_id = uuid.UUID(document["id"])

    assert _process(client, document["id"])["document_type"] == "GRADUATION_CERTIFICATE"
    assert _process(client, document["id"])["document_type"] == "BUSINESS_REGISTRATION_CERTIFICATE"
    detail = _detail(client, document["id"])
    field_names = [field["field_name"] for field in detail["extracted_fields"]]

    assert "business_registration_number" in field_names
    assert "graduation_date" not in field_names
    assert len(field_names) == len(set(field_names))
    assert db_session.query(OCRResult).filter_by(document_id=document_id).count() == 1


def test_failed_reprocessing_preserves_last_good_result_but_marks_failure(
    client: TestClient, db_session
) -> None:
    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "business_scan.pdf")
    _process(client, document["id"])
    row = db_session.get(Document, uuid.UUID(document["id"]))
    assert db_session.query(ExtractedField).filter_by(document_id=row.id).count() > 0
    previous_ids = {
        field.id for field in db_session.query(ExtractedField).filter_by(document_id=row.id)
    }
    previous_version = row.processing_version

    row.original_filename = "ocr_failure_scan.pdf"
    db_session.commit()
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "FAILED"
    assert processed["document_type"] == "BUSINESS_REGISTRATION_CERTIFICATE"
    assert processed["classification_meta"] is not None
    assert processed["processing_version"] == previous_version
    assert db_session.query(OCRResult).filter_by(document_id=row.id).count() == 1
    assert {
        field.id for field in db_session.query(ExtractedField).filter_by(document_id=row.id)
    } == previous_ids
    assert _detail(client, document["id"])["overall_status"] == "REVIEW_REQUIRED"


def test_late_transaction_failure_rolls_back_and_leaves_coherent_failed_state(
    client: TestClient, db_session, monkeypatch
) -> None:
    from app.services.processing import DocumentProcessingService

    project = _create_project(client, db_session)
    document = _upload(client, project["id"], "business_scan.pdf")
    _process(client, document["id"])
    document_id = uuid.UUID(document["id"])

    previous_ids = {
        field.id for field in db_session.query(ExtractedField).filter_by(document_id=document_id)
    }

    def fail_after_deleting_rows(self, db, row, *_args, **_kwargs):
        self._delete_derived_rows(db, row.id)
        db.flush()
        raise RuntimeError("controlled late persistence failure")

    monkeypatch.setattr(DocumentProcessingService, "_persist_success", fail_after_deleting_rows)
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "FAILED"
    assert processed["error_code"] == "PROCESSING_FAILED"
    assert "controlled" not in processed["error_message"]
    assert db_session.query(OCRResult).filter_by(document_id=document_id).count() == 1
    assert {
        field.id for field in db_session.query(ExtractedField).filter_by(document_id=document_id)
    } == previous_ids
    assert _detail(client, document["id"])["overall_status"] == "REVIEW_REQUIRED"


def test_process_missing_document_returns_safe_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/documents/{uuid.uuid4()}/process")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"


def test_mixed_pdf_ocrs_only_the_pages_without_a_text_layer(
    client: TestClient, db_session, monkeypatch
) -> None:
    """A PDF can mix a digital page and a scanned page. Routing used to be a
    single document-level gate, so one usable text page made the whole file
    skip OCR and every scanned page silently contributed nothing."""
    import uuid as uuid_module

    from app.models.entities import OCRResult

    calls: list[Path] = []

    class RecordingProvider:
        async def extract_document(self, path, mime_type, original_filename=""):
            calls.append(Path(path))
            return [
                _page(
                    1,
                    ["재학증명서", "성명 홍길동", "학번 202312345"],
                ),
                _page(
                    2,
                    ["성명 김학생", "입학일자 2023-09-01"],
                ),
            ]

    monkeypatch.setattr(
        "app.services.processing.get_ocr_provider", lambda _settings: RecordingProvider()
    )
    project = _create_project(client, db_session, applicant_name="홍길동")

    doc = fitz.open()
    digital = doc.new_page()
    digital.insert_text(
        (72, 72),
        "사업자등록증\n상호 한빛상사\n사업자등록번호 123-45-67890\n발급일자 2026-01-10",
        fontsize=12,
        fontname="korea",
    )
    doc.new_page()  # scanned page: image only, no text layer
    content = doc.tobytes()
    doc.close()

    document = _upload(client, project["id"], "mixed.pdf", content)
    processed = _process(client, document["id"])

    assert processed["processing_status"] == "COMPLETED"
    # The scanned page must have been sent to OCR despite page 1's text layer.
    assert calls, "OCR provider was never called for the scanned page"

    rows = (
        db_session.query(OCRResult)
        .filter_by(document_id=uuid_module.UUID(document["id"]))
        .order_by(OCRResult.page_number)
        .all()
    )
    assert [row.page_number for row in rows] == [1, 2]
    # Page 1 keeps the exact embedded text; only page 2 came from OCR.
    assert rows[0].provider == "direct_pdf_text"
    assert "한빛상사" in rows[0].normalized_text
    assert rows[1].provider == "controlled"
    assert "김학생" in rows[1].normalized_text
