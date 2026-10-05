"""Phase D D4 items: multi-document files, unlabelled student issue date (digital only),
submission-level duplicate notice, OCR word joining / reading order, transcript title variants.
Hold-out style values only (made up for these tests)."""

from __future__ import annotations

import uuid

import fitz
from fastapi.testclient import TestClient

from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.extraction.enrollment import department_without_college
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.layout import TextRow
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.ocr.text_assembly import assemble_page_text
from app.models.entities import Checklist, DocumentRequirement, ValidationRule

# ------------------------------------------------------------------ helpers


def _text_pdf(pages: list[list[str]]) -> bytes:
    document = fitz.open()
    for lines in pages:
        page = document.new_page()
        y = 60
        for line in lines:
            page.insert_text((60, y), line, fontsize=12, fontname="korea")
            y += 26
    data = document.tobytes()
    document.close()
    return data


def _workflow(db_session, types: list[DocumentType]) -> Checklist:
    checklist = Checklist(name=f"phase-d {uuid.uuid4().hex[:6]}", description="")
    db_session.add(checklist)
    db_session.flush()
    for document_type in types:
        requirement = DocumentRequirement(
            checklist_id=checklist.id, document_type=document_type.value, required=True
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
    return checklist


def _project(client: TestClient, db_session, types: list[DocumentType]) -> str:
    workflow = _workflow(db_session, types)
    response = client.post("/api/v1/projects", json={"name": "d4", "workflow_id": str(workflow.id)})
    assert response.status_code == 201
    return response.json()["id"]


def _upload_process(client: TestClient, project_id: str, name: str, data: bytes) -> dict:
    up = client.post(
        f"/api/v1/projects/{project_id}/documents", files={"file": (name, data, "application/pdf")}
    )
    assert up.status_code == 201
    document_id = up.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200
    return client.get(f"/api/v1/documents/{document_id}").json()


BR_PAGE = [
    "사업자등록증",
    "상호 : 주식회사 가온정밀",
    "대표자 : 류하늘",
    "사업자등록번호 : 123-45-67891",
    "사업장 소재지 : 서울특별시 어딘구 샘플로 1",
]
TAX_PAGE = [
    "납세증명서",
    "납세자명 : 주식회사 다온정밀",
    "사업자등록번호 : 214-86-55302",
    "유효기한 : 2027-06-30",
]

# ------------------------------------------------------------------ multi-document files


def test_pages_of_different_document_types_flag_the_file_and_never_merge_fields(
    client: TestClient, db_session
) -> None:
    project_id = _project(client, db_session, [DocumentType.BUSINESS_REGISTRATION_CERTIFICATE])
    detail = _upload_process(client, project_id, "two.pdf", _text_pdf([BR_PAGE, TAX_PAGE]))
    meta = detail["classification_meta"]
    assert meta["multiple_documents_in_file"] is True
    assert meta["needs_review"] is True
    assert detail["overall_status"] == "REVIEW_REQUIRED"
    codes = {row["code"] for row in detail["validation_results"] if not row["passed"]}
    assert "MULTIPLE_DOCUMENTS_IN_FILE" in codes
    fields = {item["field_name"]: item for item in detail["extracted_fields"]}
    assert fields["business_registration_number"]["normalized_value"] == "1234567891"
    assert fields["company_name"]["normalized_value"] == "주식회사 가온정밀"
    verdict = client.post(
        f"/api/v1/projects/{project_id}/verify", json={"evaluation_date": "2027-03-01"}
    ).json()
    assert verdict["status"] == "REVIEW_REQUIRED"
    assert "MULTIPLE_DOCUMENTS_IN_FILE" in {issue["code"] for issue in verdict["issues"]}


def test_unrelated_or_blank_extra_pages_do_not_flag_the_file(
    client: TestClient, db_session
) -> None:
    project_id = _project(client, db_session, [DocumentType.BUSINESS_REGISTRATION_CERTIFICATE])
    unrelated = _upload_process(
        client,
        project_id,
        "unrelated.pdf",
        _text_pdf([BR_PAGE, ["회의록", "일시 2027-01-01", "안건 분기 실적 논의 및 향후 계획"]]),
    )
    assert not (unrelated["classification_meta"] or {}).get("multiple_documents_in_file")
    blank = _upload_process(client, project_id, "blank.pdf", _text_pdf([BR_PAGE, []]))
    assert not (blank["classification_meta"] or {}).get("multiple_documents_in_file")


# ------------------------------------------------------------------ student issue date


def _source(lines: list[str], source: str) -> OCRDocumentResult:
    ocr_lines = [
        OCRLine(
            text=text,
            confidence=None if source == "direct_pdf_text" else 0.97,
            bounding_box=BoundingBox(x=60.0, y=40.0 + index * 30.0, width=400.0, height=14.0),
        )
        for index, text in enumerate(lines)
    ]
    page = OCRPage(1, "\n".join(lines), ocr_lines, metadata={"source": source})
    return OCRDocumentResult(source, [page], page.text)


def _issue_date(lines: list[str], source: str = "direct_pdf_text"):
    values = ExtractorRegistry().extract(
        DocumentType.ENROLLMENT_CERTIFICATE, _source(lines, source)
    )
    return next(v for v in values if v.field_name == "issue_date")


ENROLLMENT_BASE = [
    "재 학 증 명 서",
    "성          명 : 류하늘",
    "재 학 기 간 : 2025년 03월 02일 입학",
]


def test_digital_unlabelled_issue_date_in_the_issuer_block_is_trusted() -> None:
    value = _issue_date(
        [*ENROLLMENT_BASE, "위의 사실을 증명합니다.", "2027년 02월 20일", "한국샘플대학교 총장"]
    )
    assert value.normalized_value == "2027-02-20"
    assert value.needs_review is False
    assert value.extraction_method == "issuer_block_issue_date"


def test_issue_date_not_trusted_from_ocr() -> None:
    value = _issue_date(
        [*ENROLLMENT_BASE, "위의 사실을 증명합니다.", "2027년 02월 20일", "한국샘플대학교 총장"],
        source="ocr",
    )
    assert value.needs_review is True


def test_blank_issuer_block_date_with_an_enrolment_period_date_elsewhere_stays_unresolved() -> None:
    value = _issue_date(
        [
            *ENROLLMENT_BASE,
            "2027년 02월 20일 재학중",
            "위의 사실을 증명합니다.",
            "한국샘플대학교 총장",
        ]
    )
    assert value.normalized_value is None


def test_two_dates_in_the_issuer_block_are_not_trusted() -> None:
    value = _issue_date(
        [
            *ENROLLMENT_BASE,
            "위의 사실을 증명합니다.",
            "2027년 02월 19일",
            "2027년 02월 20일",
            "한국샘플대학교 총장",
        ]
    )
    assert value.normalized_value is None or value.needs_review is True


def test_date_with_no_certification_sentence_above_it_keeps_the_review_flag() -> None:
    value = _issue_date([*ENROLLMENT_BASE, "2027년 02월 20일", "한국샘플대학교 총장"])
    assert value.normalized_value is None or value.needs_review is True


# ------------------------------------------------------------------ duplicate notice


def test_duplicate_upload_is_reported_at_submission_level_without_changing_the_status(
    client: TestClient, db_session
) -> None:
    project_id = _project(client, db_session, [DocumentType.BUSINESS_REGISTRATION_CERTIFICATE])
    data = _text_pdf([BR_PAGE])
    _upload_process(client, project_id, "first.pdf", data)
    _upload_process(client, project_id, "copy.pdf", data)
    verdict = client.post(
        f"/api/v1/projects/{project_id}/verify", json={"evaluation_date": "2027-03-01"}
    ).json()
    notices = {item["code"]: item for item in verdict["notices"]}
    assert "DUPLICATE_UPLOAD_IGNORED" in notices
    assert notices["DUPLICATE_UPLOAD_IGNORED"]["status_effect"] == "READY"
    assert "DUPLICATE_UPLOAD_IGNORED" not in {issue["code"] for issue in verdict["issues"]}
    again = client.get(f"/api/v1/projects/{project_id}/verification").json()
    assert "DUPLICATE_UPLOAD_IGNORED" in {item["code"] for item in again["notices"]}


# ------------------------------------------------------------------ word joining / order


def _box(text: str, x: float, y: float, width: float, height: float = 40.0) -> OCRLine:
    return OCRLine(text=text, confidence=0.97, bounding_box=BoundingBox(x, y, width, height))


def test_row_text_joins_abutting_boxes_without_a_space_and_separate_boxes_with_one() -> None:
    abutting = TextRow(1, (_box("주식회사", 100, 10, 160), _box("가온정밀", 262, 10, 160)))
    apart = TextRow(1, (_box("성명", 100, 10, 80), _box("류하늘", 400, 10, 120)))
    assert abutting.text == "주식회사가온정밀"
    assert apart.text == "성명 류하늘"


def test_glued_college_and_department_are_separated_but_not_graduate_schools() -> None:
    from app.document_intelligence.extraction.base import ExtractedValue

    def dept(text: str) -> str | None:
        return department_without_college(ExtractedValue("department", text, text)).normalized_value

    assert dept("공과대학기계공학과") == "기계공학과"
    assert dept("자연과학대학 물리학과") == "물리학과"
    assert dept("경영대학원경영학과") == "경영대학원경영학과"
    assert dept("기계공학과") == "기계공학과"


def test_letter_spaced_title_boxes_with_vertical_jitter_keep_reading_order() -> None:
    jitter = [0.0, 14.0, -12.0, 15.0, -10.0]
    lines = [
        _box(char, 100 + index * 70, 200 + shift, 50, 60)
        for index, (char, shift) in enumerate(zip("성적증명서", jitter, strict=True))
    ]
    assert assemble_page_text(lines).replace("\n", "") == "성적증명서"


# ------------------------------------------------------------------ transcript classification


def test_transcript_with_a_garbled_title_still_classifies_from_its_own_layout_signals() -> None:
    text = "1적증명서\n학번 : 2025123456\n취득학점: 17\n평점평균: 3.40/4.5 백분율: 88.00/100\n한국샘플대학교 총장"
    assert DocumentClassifier().classify(text).predicted_type == DocumentType.TRANSCRIPT


def test_enrollment_certificate_is_not_pulled_towards_transcript_by_the_new_signals() -> None:
    text = "재학증명서\n성명 류하늘\n학번 2025123456\n소속 공과대학 기계공학과\n한국샘플대학교 총장"
    assert DocumentClassifier().classify(text).predicted_type == DocumentType.ENROLLMENT_CERTIFICATE


def test_graduation_certificate_listing_credits_is_not_a_transcript() -> None:
    text = "졸업증명서\n성명 류하늘\n학과 기계공학과\n졸업일자 2027-02-20\n취득학점 140\n학위 학사"
    assert DocumentClassifier().classify(text).predicted_type == DocumentType.GRADUATION_CERTIFICATE


# ------------------------------------------------------------------ extraction gaps seen on scans


def _fields_of(doc_type: DocumentType, lines: list[OCRLine]) -> dict[str, str | None]:
    page = OCRPage(1, "\n".join(item.text for item in lines), lines, metadata={"source": "ocr"})
    source = OCRDocumentResult("ocr", [page], page.text)
    return {v.field_name: v.normalized_value for v in ExtractorRegistry().extract(doc_type, source)}


def test_stacked_label_value_centred_between_the_two_lines_is_read() -> None:
    # value overlaps each label line by less than half its height (scan geometry)
    lines = [
        _box("납세증명서", 300, 100, 400, 60),
        _box("주민등록번호", 1465, 648, 229, 56),
        _box("(사업자등록번호)", 1468, 703, 285, 57),
        _box("123-45-67891", 1843, 679, 228, 42),
    ]
    got = _fields_of(DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, lines)
    assert got["business_registration_number"] == "1234567891"


def test_value_cell_with_a_spilled_closing_parenthesis_is_read() -> None:
    lines = [
        _box("사업자등록증", 600, 100, 800, 120),
        _box("법인명(단체명)", 247, 752, 335, 58),
        _box("):주식회사 가온정밀", 578, 752, 503, 57),
    ]
    got = _fields_of(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, lines)
    assert got["company_name"] == "주식회사 가온정밀"


def test_submitter_company_comparison_ignores_legal_entity_notation_only() -> None:
    from app.document_intelligence.validation.submission import _same_name

    rule = RuleType.COMPANY_NAME_MATCH
    assert _same_name("(주)가온정밀", "주식회사 가온정밀", rule)
    assert _same_name("가온정밀(주)", "㈜가온정밀", rule)
    assert not _same_name("(주)가온정밀", "주식회사 가온정믹", rule)
    assert not _same_name("류하늘", "류하눌", RuleType.APPLICANT_NAME_MATCH)
