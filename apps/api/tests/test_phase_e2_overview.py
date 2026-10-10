"""Phase E2: the project overview read model (state, counts, next step, issue values)."""

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient
from test_submission_verification_api import (
    _business_project,
    _document,
    _verify,
)

from app.core.domain import DocumentType, ProcessingStatus
from app.models.entities import Document, ExtractedField
from app.services.overview import _unique

BR = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
SME = DocumentType.SME_CONFIRMATION_CERTIFICATE


def _overview(client: TestClient, project_id: uuid.UUID) -> dict:
    response = client.get(f"/api/v1/projects/{project_id}/overview")
    assert response.status_code == 200, response.text
    return response.json()


def _states(overview: dict) -> dict[str, str]:
    return {r["document_type"]: r["state"] for r in overview["requirements"]}


def _both_valid(db_session, submission, brn_sme="1234567890", valid_until="2026-12-31"):
    _document(
        db_session,
        submission,
        BR,
        {"business_registration_number": "1234567890", "company_name": "테스트상사"},
    )
    _document(
        db_session,
        submission,
        SME,
        {
            "business_registration_number": brn_sme,
            "valid_until": valid_until,
            "company_name": "테스트상사",
            "valid_from": "2026-01-01",
        },
    )
    db_session.commit()


def test_empty_project_asks_for_uploads(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    overview = _overview(client, project.id)
    assert overview["check_state"] == "NOT_CURRENT"
    assert overview["status"] is None
    assert overview["status_item_count"] is None
    assert overview["next_step"] == "UPLOAD_DOCUMENTS"
    assert set(_states(overview).values()) == {"MISSING"}
    assert overview["counts"]["required_total"] == 2
    assert overview["counts"]["required_missing"] == 2


def test_uploaded_but_unchecked_documents_are_not_checked(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission)
    overview = _overview(client, project.id)
    assert overview["next_step"] == "RUN_CHECK"
    assert set(_states(overview).values()) == {"NOT_CHECKED"}
    assert overview["suggested_evaluation_date"]


def test_ready_submission(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission)
    _verify(client, project.id)
    overview = _overview(client, project.id)
    assert overview["check_state"] == "CURRENT"
    assert overview["status"] == "READY"
    assert overview["status_item_count"] == 0
    assert overview["next_step"] == "DONE"
    assert set(_states(overview).values()) == {"OK"}
    assert overview["counts"]["required_ok"] == 2
    assert overview["issues"] == []
    assert overview["evaluation_date"] == "2026-09-22"


def test_mismatch_names_both_documents_and_quotes_both_values(
    client: TestClient, db_session
) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission, brn_sme="9999999999")
    _verify(client, project.id)
    overview = _overview(client, project.id)
    assert overview["status"] == "NEEDS_CORRECTION"
    assert overview["status_item_count"] == 1
    assert overview["next_step"] == "FIX_ISSUES"
    assert _states(overview) == {BR.value: "NEEDS_CORRECTION", SME.value: "NEEDS_CORRECTION"}
    (issue,) = overview["issues"]
    assert issue["code"] == "INFORMATION_MISMATCH"
    assert {issue["value"], issue["related_value"]} == {"1234567890", "9999999999"}


def test_expired_document_carries_value_and_reference_date(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission, valid_until="2026-01-31")
    _verify(client, project.id)
    overview = _overview(client, project.id)
    (issue,) = overview["issues"]
    assert issue["code"] == "EXPIRED_DOCUMENT"
    assert issue["value"] == "2026-01-31"
    assert issue["reference_date"] == "2026-09-22"
    assert _states(overview)[SME.value] == "NEEDS_CORRECTION"
    assert _states(overview)[BR.value] == "OK"


def test_missing_required_document(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _document(
        db_session,
        submission,
        BR,
        {"business_registration_number": "1234567890", "company_name": "테스트상사"},
    )
    db_session.commit()
    _verify(client, project.id)
    overview = _overview(client, project.id)
    assert overview["status"] == "NEEDS_CORRECTION"
    assert overview["next_step"] == "UPLOAD_DOCUMENTS"
    assert _states(overview)[SME.value] == "MISSING"
    assert overview["counts"]["required_missing"] == 1


def test_documents_in_flight_mean_wait(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    row = _document(db_session, submission, BR, {})
    row.processing_status = ProcessingStatus.OCR_PROCESSING.value
    db_session.commit()
    overview = _overview(client, project.id)
    assert overview["next_step"] == "WAIT_PROCESSING"
    assert _states(overview)[BR.value] == "PROCESSING"
    assert overview["counts"]["documents_processing"] == 1


def test_unrecognised_and_foreign_documents_are_listed_separately(
    client: TestClient, db_session
) -> None:
    project, submission, _ = _business_project(db_session)
    _document(db_session, submission, DocumentType.UNKNOWN, {})
    _document(db_session, submission, DocumentType.TRANSCRIPT, {})
    db_session.commit()
    reasons = {o["reason"] for o in _overview(client, project.id)["other_documents"]}
    assert reasons == {"UNKNOWN_TYPE", "NOT_IN_WORKFLOW"}


def test_same_finding_is_reported_once() -> None:
    a = SimpleNamespace(code="X", document_id=1, field_name="f", related_document_id=None)
    b = SimpleNamespace(code="X", document_id=1, field_name="f", related_document_id=None)
    c = SimpleNamespace(code="X", document_id=2, field_name="f", related_document_id=None)
    assert _unique([a, b, c]) == [a, c]


def test_unknown_project_is_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/projects/{uuid.uuid4()}/overview").status_code == 404


def test_document_fields_say_whether_a_rule_uses_them(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission)
    mine = db_session.query(Document).filter_by(submission_id=submission.id)
    for row in db_session.query(ExtractedField).filter(
        ExtractedField.document_id.in_([d.id for d in mine])
    ):
        if row.evidence:
            row.evidence = [
                {
                    "page_number": 1,
                    "source_text": row.raw_value,
                    "source_kind": "embedded_pdf_text",
                    "coordinate_space": "pdf_point",
                }
            ]
    sme_row = mine.filter_by(document_type=SME.value).one()
    db_session.add(
        ExtractedField(
            document_id=sme_row.id,
            field_name="fax_number",
            raw_value="02-000-0000",
            normalized_value="02-000-0000",
            needs_review=False,
        )
    )
    db_session.commit()
    sme = next(
        d
        for d in client.get(f"/api/v1/projects/{project.id}/documents").json()
        if d["document_type"] == SME.value
    )
    fields = {
        f["field_name"]: f["used_by_rules"]
        for f in client.get(f"/api/v1/documents/{sme['id']}").json()["extracted_fields"]
    }
    assert fields["business_registration_number"] is True
    assert fields["valid_until"] is True
    assert fields["fax_number"] is False


def test_project_summaries_match_the_overview(client: TestClient, db_session) -> None:
    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission, brn_sme="9999999999")
    _verify(client, project.id)
    overview = _overview(client, project.id)
    summary = next(
        s
        for s in client.get("/api/v1/project-summaries").json()
        if s["project_id"] == str(project.id)
    )
    assert summary["status"] == overview["status"] == "NEEDS_CORRECTION"
    assert summary["status_item_count"] == overview["status_item_count"] == 1
    assert summary["next_step"] == overview["next_step"]
    assert summary["required_total"] == overview["counts"]["required_total"]


def test_overview_is_read_only_and_leaves_a_stale_check_for_the_writer(
    client: TestClient, db_session
) -> None:
    """Polling the overview while documents are analysed must not lock or write the project."""
    from sqlalchemy import func, select

    from app.models.entities import ValidationResult

    project, submission, _ = _business_project(db_session)
    _both_valid(db_session, submission)
    _verify(client, project.id)

    def stored_rows() -> int:
        return db_session.scalar(
            select(func.count())
            .select_from(ValidationResult)
            .where(ValidationResult.project_id == project.id)
        )

    before = stored_rows()
    assert before > 0
    mine = [d.id for d in db_session.query(Document).filter_by(submission_id=submission.id)]
    row = (
        db_session.query(ExtractedField)
        .filter(ExtractedField.document_id.in_(mine), ExtractedField.field_name == "company_name")
        .first()
    )
    row.normalized_value = "다른상사"  # an input changes: the stored check is now stale
    db_session.commit()

    overview = _overview(client, project.id)
    assert overview["check_state"] == "NOT_CURRENT"
    assert stored_rows() == before  # not invalidated by the read
    assert client.get(f"/api/v1/projects/{project.id}/verification").json()["is_current"] is False
    assert stored_rows() == 0  # the writer path cleans it up
