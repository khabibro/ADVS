"""Phase D: auto-acceptance of OCR values.

Unit tests of the decision rules and pipeline tests through the real API. Every value here
is made up for these tests (it appears in neither evaluation corpus)."""

from __future__ import annotations

import uuid
from datetime import date

import fitz
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.domain import DocumentType, RuleType, Severity
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    SecondPassInput,
    Strategy,
    canonical_key,
    decide,
    parse_second_pass,
    parse_strategy,
)
from app.document_intelligence.normalization.field_normalizer import is_valid_business_number
from app.document_intelligence.ocr.models import (
    BoundingBox,
    OCRLine,
    OCRPage,
    RegionReading,
)
from app.models.entities import Checklist, DocumentRequirement, ValidationRule

BR = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
SME = DocumentType.SME_CONFIRMATION_CERTIFICATE
TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
ENR = DocumentType.ENROLLMENT_CERTIFICATE
TRN = DocumentType.TRANSCRIPT

GOOD_BRN = "1234567891"  # valid check digit
OTHER_BRN = "2148655302"  # valid check digit, different number


def _checksum_preserving_transposition() -> tuple[str, str]:
    for base in range(1000000000, 1000000000 + 5000):
        digits = str(base)
        if not is_valid_business_number(digits):
            continue
        for i in range(9):
            swapped = digits[:i] + digits[i + 1] + digits[i] + digits[i + 2 :]
            if swapped != digits and is_valid_business_number(swapped):
                return digits, swapped
    raise AssertionError("no checksum-preserving transposition found")


def field(
    doc: uuid.UUID,
    name: str,
    value: str | None,
    *,
    doc_type: DocumentType = BR,
    checksum: str | None = None,
    confidence: float | None = 0.97,
    ocr: bool = True,
    needs_review: bool = False,
    method: str | None = "label_match",
    second: str | None = None,
    reviewed: bool = False,
) -> FieldInput:
    return FieldInput(
        document_id=doc,
        checksum=checksum or doc.hex,
        document_type=doc_type,
        field_name=name,
        value=value,
        confidence=confidence,
        ocr=ocr,
        needs_review=needs_review,
        extraction_method=method,
        second_pass=SecondPassInput(second, second, 0.9) if second else None,
        has_current_review=reviewed,
    )


def accepted(decisions: dict, doc: uuid.UUID, name: str) -> bool:
    item = decisions.get((doc, name))
    return bool(item and item.accepted)


D1, D2, D3, D4 = (uuid.uuid4() for _ in range(4))
CTX = ProjectContext(reference_date=date(2027, 3, 1))


# ------------------------------------------------------------------ unit: strategies


def test_s0_accepts_nothing_and_unknown_strategy_falls_back_to_s0() -> None:
    fields = [field(D1, "business_registration_number", GOOD_BRN)]
    assert decide(fields, CTX, Strategy.S0) == {}
    assert parse_strategy("nonsense") == Strategy.S0


def test_s1_confidence_alone_accepts_a_wrong_number_which_is_why_it_is_unsafe() -> None:
    wrong = "1234567890"  # fails the check digit
    fields = [field(D1, "business_registration_number", wrong)]
    assert accepted(decide(fields, CTX, Strategy.S1), D1, "business_registration_number")
    assert not accepted(decide(fields, CTX, Strategy.S2), D1, "business_registration_number")


def test_confidence_below_the_floor_is_never_accepted() -> None:
    fields = [
        field(D1, "business_registration_number", GOOD_BRN, confidence=0.89),
        field(D2, "business_registration_number", GOOD_BRN, doc_type=SME, confidence=0.99),
    ]
    decisions = decide(fields, CTX, Strategy.S3)
    assert not accepted(decisions, D1, "business_registration_number")
    assert decisions[(D1, "business_registration_number")].reason == "CONFIDENCE_BELOW_FLOOR"
    assert accepted(decisions, D2, "business_registration_number")


def test_s2_accepts_validated_numbers_but_never_names() -> None:
    fields = [
        field(D1, "business_registration_number", GOOD_BRN),
        field(D1, "company_name", "주식회사 가온정밀"),
    ]
    decisions = decide(fields, CTX, Strategy.S2)
    assert accepted(decisions, D1, "business_registration_number")
    assert not accepted(decisions, D1, "company_name")


def test_s3_requires_another_document() -> None:
    alone = [field(D1, "business_registration_number", GOOD_BRN)]
    assert not accepted(decide(alone, CTX, Strategy.S3), D1, "business_registration_number")
    pair = alone + [field(D2, "business_registration_number", GOOD_BRN, doc_type=SME)]
    decisions = decide(pair, CTX, Strategy.S3)
    assert accepted(decisions, D1, "business_registration_number")
    assert decisions[(D1, "business_registration_number")].corroborating_document_ids == (D2,)
    assert decisions[(D1, "business_registration_number")].sources == ("documents",)


def test_corroboration_uses_exact_equality_only_after_canonicalisation() -> None:
    near = [
        field(D1, "company_name", "주식회사 가온정밀"),
        field(D2, "company_name", "주식회사 가온정믹", doc_type=SME),
    ]
    decisions = decide(near, CTX, Strategy.S3)
    assert not accepted(decisions, D1, "company_name")
    assert not accepted(decisions, D2, "company_name")
    same = [
        field(D1, "company_name", "주식회사 가온정밀"),
        field(D2, "company_name", "(주)가온 정밀", doc_type=SME),
    ]
    assert accepted(decide(same, CTX, Strategy.S3), D1, "company_name")
    assert canonical_key("company", "㈜가온정밀") == canonical_key("company", "주식회사 가온정밀")


def test_a_value_never_corroborates_itself_and_duplicate_files_do_not_count() -> None:
    twin = [
        field(D1, "business_registration_number", GOOD_BRN, checksum="same-bytes"),
        field(D2, "business_registration_number", GOOD_BRN, checksum="same-bytes"),
    ]
    decisions = decide(twin, CTX, Strategy.S3)
    assert not accepted(decisions, D1, "business_registration_number")
    assert not accepted(decisions, D2, "business_registration_number")


def test_no_majority_voting() -> None:
    fields = [
        field(D1, "company_name", "주식회사 가온정밀"),
        field(D2, "company_name", "주식회사 가온정밀", doc_type=SME),
        field(D3, "company_name", "주식회사 가온정밀", doc_type=TAX),
        field(
            D4,
            "workplace_name",
            "주식회사 다온정밀",
            doc_type=DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
        ),
    ]
    decisions = decide(fields, CTX, Strategy.S4)
    for doc, name in (
        (D1, "company_name"),
        (D2, "company_name"),
        (D3, "company_name"),
        (D4, "workplace_name"),
    ):
        assert not accepted(decisions, doc, name)
    assert decisions[(D1, "company_name")].reason == "DISAGREES_WITH_OTHER_DOCUMENT"


def test_invalid_number_on_another_document_is_noise_not_a_disagreement() -> None:
    fields = [
        field(D1, "business_registration_number", GOOD_BRN),
        field(D2, "business_registration_number", GOOD_BRN, doc_type=SME),
        field(D3, "business_registration_number", "1234567899", doc_type=TAX),  # bad check digit
    ]
    decisions = decide(fields, CTX, Strategy.S3)
    assert accepted(decisions, D1, "business_registration_number")
    assert not accepted(decisions, D3, "business_registration_number")


def test_application_value_is_an_independent_source_and_overrides_agreeing_documents() -> None:
    context = ProjectContext(company_name="(주)가온정밀", reference_date=date(2027, 3, 1))
    single = [field(D1, "company_name", "주식회사 가온정밀")]
    assert accepted(decide(single, context, Strategy.S5), D1, "company_name")
    assert not accepted(
        decide(single, context, Strategy.S4), D1, "company_name"
    )  # S4 has no application
    # three documents agree with each other but not with the application value: none wins
    wrong = [
        field(D1, "company_name", "주식회사 다온정밀"),
        field(D2, "company_name", "주식회사 다온정밀", doc_type=SME),
        field(D3, "company_name", "주식회사 다온정밀", doc_type=TAX),
    ]
    decisions = decide(wrong, context, Strategy.S5)
    assert all(not accepted(decisions, d, "company_name") for d in (D1, D2, D3))
    assert decisions[(D1, "company_name")].reason == "CONFLICTS_WITH_APPLICATION_VALUE"


def test_person_name_is_never_accepted_by_a_second_pass_alone() -> None:
    fields = [field(D1, "student_name", "류하늘", doc_type=ENR, second="류하늘")]
    for strategy in (Strategy.S4, Strategy.S5, Strategy.S6):
        assert not accepted(decide(fields, CTX, strategy), D1, "student_name")
    pair = fields + [field(D2, "student_name", "류하늘", doc_type=TRN)]
    assert accepted(decide(pair, CTX, Strategy.S4), D1, "student_name")


def test_second_pass_consensus_accepts_when_no_document_can_confirm() -> None:
    fields = [field(D1, "student_id", "2025123456", doc_type=ENR, second="2025123456")]
    assert accepted(decide(fields, CTX, Strategy.S4), D1, "student_id")
    assert not accepted(decide(fields, CTX, Strategy.S3), D1, "student_id")
    disagree = [field(D1, "student_id", "2025123456", doc_type=ENR, second="2025123458")]
    assert not accepted(decide(disagree, CTX, Strategy.S4), D1, "student_id")


def test_second_pass_veto_stops_a_corroborated_checksum_preserving_misread() -> None:
    truth, swapped = _checksum_preserving_transposition()
    # every document carries the same wrong (but check-digit-valid) number: the correlated case
    fields = [
        field(D1, "business_registration_number", swapped, second=truth),
        field(D2, "business_registration_number", swapped, doc_type=SME, second=truth),
    ]
    assert accepted(
        decide(fields, CTX, Strategy.S5), D1, "business_registration_number"
    )  # residual risk
    vetoed = decide(fields, CTX, Strategy.S6)
    assert not accepted(vetoed, D1, "business_registration_number")
    assert vetoed[(D1, "business_registration_number")].reason == "SECOND_PASS_DISAGREES"


def test_fields_marked_for_review_and_semantic_inference_are_never_accepted() -> None:
    fields = [
        field(D1, "business_registration_number", GOOD_BRN, needs_review=True),
        field(
            D2,
            "issue_date",
            "2027-02-01",
            doc_type=ENR,
            method="document_semantic_issue_date",
            second="2027-02-01",
        ),
    ]
    decisions = decide(fields, CTX, Strategy.S6)
    assert not accepted(decisions, D1, "business_registration_number")
    assert not accepted(decisions, D2, "issue_date")


def test_embedded_text_and_reviewed_fields_are_not_decided() -> None:
    fields = [
        field(D1, "business_registration_number", GOOD_BRN, ocr=False),
        field(D2, "business_registration_number", GOOD_BRN, reviewed=True),
    ]
    assert decide(fields, CTX, Strategy.S5) == {}


def test_date_logic_validators() -> None:
    ctx = ProjectContext(reference_date=date(2027, 3, 1))
    ok = [
        field(D1, "valid_from", "2027-01-01", doc_type=SME, second="2027-01-01"),
        field(D1, "valid_until", "2027-12-31", doc_type=SME, second="2027-12-31"),
        field(D2, "issue_date", "2027-02-20", doc_type=ENR, second="2027-02-20"),
    ]
    decisions = decide(ok, ctx, Strategy.S4)
    assert all(d.accepted for d in decisions.values())
    reversed_range = [
        field(D1, "valid_from", "2027-12-31", doc_type=SME, second="2027-12-31"),
        field(D1, "valid_until", "2027-01-01", doc_type=SME, second="2027-01-01"),
        field(D2, "issue_date", "2027-04-01", doc_type=ENR, second="2027-04-01"),
        field(D3, "issue_date", "2027-02-30", doc_type=ENR, second="2027-02-30"),
    ]
    decisions = decide(reversed_range, ctx, Strategy.S4)
    assert decisions[(D1, "valid_from")].reason == "FORMAT_VALIDITY_ORDER"
    assert decisions[(D2, "issue_date")].reason == "FORMAT_ISSUE_DATE_AFTER_SUBMISSION"
    assert decisions[(D3, "issue_date")].reason == "FORMAT_DATE_INVALID"


def test_gpa_validators_and_student_id_format() -> None:
    def gpa_fields(gpa: str, scale: str) -> list[FieldInput]:
        return [
            field(D1, "gpa", gpa, doc_type=TRN, second=gpa),
            field(D1, "gpa_scale", scale, doc_type=TRN, second=scale),
        ]

    assert accepted(decide(gpa_fields("3.4", "4.5"), CTX, Strategy.S4), D1, "gpa")
    assert (
        decide(gpa_fields("4.6", "4.5"), CTX, Strategy.S4)[(D1, "gpa")].reason
        == "FORMAT_GPA_ABOVE_SCALE"
    )
    assert (
        decide(gpa_fields("3.4", "5"), CTX, Strategy.S4)[(D1, "gpa_scale")].reason
        == "FORMAT_GPA_SCALE_UNKNOWN"
    )
    assert (
        decide([field(D1, "student_id", "12345", doc_type=ENR, second="12345")], CTX, Strategy.S4)[
            (D1, "student_id")
        ].reason
        == "FORMAT_STUDENT_ID"
    )


def test_second_pass_parsing_matches_first_pass_normalisation() -> None:
    assert (
        parse_second_pass("business_registration_number", "등록번호 : 123-45-67891") == "1234567891"
    )
    assert parse_second_pass("valid_from", ": 2027-01-01 ~2 2027-12-31") == "2027-01-01"
    assert parse_second_pass("valid_until", ": 2027-01-01 ~2 2027-12-31") == "2027-12-31"
    assert parse_second_pass("valid_until", "2027년12월31일까지") == "2027-12-31"
    assert parse_second_pass("gpa", "평점평균: 3.40/4.5 백분율: 88.00/100") == "3.4"
    assert parse_second_pass("gpa_scale", "평점평균: 3.40/4.5 백분율: 88.00/100") == "4.5"
    assert parse_second_pass("student_id", "∴. 2025123456") == "2025123456"
    assert parse_second_pass("business_registration_number", "") is None


# ------------------------------------------------------------------ pipeline


class ControlledProvider:
    """Serves fixed OCR pages per original filename, and fixed second-pass readings."""

    def __init__(self, pages: dict[str, list[str]], readings: dict[str, str] | None = None) -> None:
        self.pages = pages
        self.readings = readings or {}

    async def extract_document(self, path, mime_type, original_filename=""):  # noqa: ANN001
        lines = self.pages[original_filename]
        observations = [
            OCRLine(
                text=text,
                confidence=0.97,
                bounding_box=BoundingBox(
                    x=40.0, y=float(index * 40 + 20), width=500.0, height=24.0
                ),
            )
            for index, text in enumerate(lines)
        ]
        return [OCRPage(1, "\n".join(lines), observations, 0.97, 1, {"provider": "controlled"})]

    async def read_regions(self, path, mime_type, requests):  # noqa: ANN001
        return [
            RegionReading(r.field_name, r.page_number, self.readings[r.field_name], 0.9, "test")
            for r in requests
            if r.field_name in self.readings
        ]

    async def health_check(self) -> bool:
        return True


def _blank_pdf(seed: int) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.draw_rect(fitz.Rect(10, 10, 20 + seed, 20 + seed))
    data = document.tobytes()
    document.close()
    return data


def _workflow(db_session) -> Checklist:
    checklist = Checklist(name=f"auto-accept {uuid.uuid4().hex[:6]}", description="")
    db_session.add(checklist)
    db_session.flush()
    for document_type in (BR, SME):
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


BR_LINES = [
    "사업자등록증",
    "사업자등록번호 : 123-45-67891",
    "상호 : 주식회사 가온정밀",
    "대표자 : 류하늘",
]
SME_LINES = [
    "중소기업확인서",
    "기업명 : 주식회사 가온정밀",
    "사업자등록번호 : 123-45-67891",
    "유효기간 : 2027-01-01 ~ 2027-12-31",
]


@pytest.fixture
def setup(client: TestClient, db_session, monkeypatch):
    def build(strategy: str, pages: dict[str, list[str]], readings=None, **project):
        monkeypatch.setattr(get_settings(), "auto_accept_strategy", strategy)
        provider = ControlledProvider(pages, readings)
        monkeypatch.setattr("app.services.processing.get_ocr_provider", lambda settings: provider)
        workflow = _workflow(db_session)
        created = client.post(
            "/api/v1/projects", json={"name": "t", "workflow_id": str(workflow.id), **project}
        )
        assert created.status_code == 201
        return created.json()["id"], provider

    return build


def _run(client: TestClient, project_id: str, files: dict[str, int]) -> dict[str, str]:
    ids = {}
    for name, seed in files.items():
        up = client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": (name, _blank_pdf(seed), "application/pdf")},
        )
        assert up.status_code == 201
        ids[name] = up.json()["id"]
        assert client.post(f"/api/v1/documents/{ids[name]}/process").status_code == 200
    return ids


def _fields(client: TestClient, document_id: str) -> dict[str, dict]:
    body = client.get(f"/api/v1/documents/{document_id}").json()
    return {item["field_name"]: item for item in body["extracted_fields"]}


def test_pipeline_corroborated_ocr_number_is_accepted_and_exposed(client, setup) -> None:
    project_id, _ = setup("S3", {"br.pdf": BR_LINES, "sme.pdf": SME_LINES})
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    brn = _fields(client, ids["br.pdf"])["business_registration_number"]
    assert brn["effective_normalized_value"] == "1234567891"
    assert brn["normalized_value"] == "1234567891"  # machine evidence unchanged
    assert brn["auto_acceptance"]["accepted"] is True
    assert brn["auto_acceptance"]["sources"] == ["documents"]
    assert brn["auto_acceptance"]["policy_version"]
    assert brn["auto_acceptance"]["corroborating_document_ids"] == [ids["sme.pdf"]]
    # a company name is not accepted without its own corroboration under S3?  It is: two documents agree.
    assert _fields(client, ids["br.pdf"])["company_name"]["auto_acceptance"]["accepted"] is True


def test_pipeline_s0_keeps_every_ocr_field_with_a_human(client, setup) -> None:
    project_id, _ = setup("S0", {"br.pdf": BR_LINES, "sme.pdf": SME_LINES})
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    brn = _fields(client, ids["br.pdf"])["business_registration_number"]
    assert brn["effective_normalized_value"] is None
    assert brn["auto_acceptance"] is None
    assert brn["evidence_assessment"] == "REVIEW_REQUIRED"


def test_pipeline_disagreement_leaves_both_values_to_a_human(client, setup) -> None:
    other = [line.replace("123-45-67891", "214-86-55302") for line in SME_LINES]
    project_id, _ = setup("S5", {"br.pdf": BR_LINES, "sme.pdf": other})
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    for name in ids:
        field_ = _fields(client, ids[name])["business_registration_number"]
        assert field_["effective_normalized_value"] is None
        assert field_["auto_acceptance"]["reason"] == "DISAGREES_WITH_OTHER_DOCUMENT"


def test_pipeline_application_value_decides_and_status_is_never_ready_on_a_wrong_company(
    client, setup
) -> None:
    project_id, _ = setup(
        "S5", {"br.pdf": BR_LINES, "sme.pdf": SME_LINES}, company_name="(주)다온정밀"
    )
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    company = _fields(client, ids["br.pdf"])["company_name"]
    assert company["effective_normalized_value"] is None
    assert company["auto_acceptance"]["reason"] == "CONFLICTS_WITH_APPLICATION_VALUE"
    verdict = client.post(
        f"/api/v1/projects/{project_id}/verify", json={"evaluation_date": "2027-03-01"}
    ).json()
    assert verdict["status"] != "READY"


def test_pipeline_second_pass_consensus_and_veto(client, setup) -> None:
    only_br = {"br.pdf": BR_LINES}
    project_id, _ = setup(
        "S4", only_br, readings={"business_registration_number": "사업자등록번호 : 123-45-67891"}
    )
    ids = _run(client, project_id, {"br.pdf": 1})
    brn = _fields(client, ids["br.pdf"])["business_registration_number"]
    assert brn["auto_acceptance"]["accepted"] is True
    assert brn["auto_acceptance"]["sources"] == ["second_pass"]
    assert brn["auto_acceptance"]["second_pass_value"] == "1234567891"

    project_id, _ = setup(
        "S4", only_br, readings={"business_registration_number": "사업자등록번호 : 123-45-67892"}
    )
    ids = _run(client, project_id, {"br.pdf": 1})
    brn = _fields(client, ids["br.pdf"])["business_registration_number"]
    assert brn["effective_normalized_value"] is None


def test_pipeline_reprocessing_recomputes_the_decision(client, setup) -> None:
    project_id, provider = setup("S3", {"br.pdf": BR_LINES, "sme.pdf": SME_LINES})
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    assert _fields(client, ids["br.pdf"])["business_registration_number"]["auto_acceptance"][
        "accepted"
    ]
    # the second document is re-read and now disagrees: the earlier decision must not survive
    provider.pages["sme.pdf"] = [line.replace("123-45-67891", "214-86-55302") for line in SME_LINES]
    assert client.post(f"/api/v1/documents/{ids['sme.pdf']}/process").status_code == 200
    field_ = _fields(client, ids["br.pdf"])["business_registration_number"]
    assert field_["effective_normalized_value"] is None
    assert field_["auto_acceptance"]["accepted"] is False


def test_pipeline_workflow_can_switch_auto_acceptance_off(client, setup, monkeypatch) -> None:
    project_id, _ = setup("S5", {"br.pdf": BR_LINES, "sme.pdf": SME_LINES})
    project = client.get(f"/api/v1/projects/{project_id}").json()
    monkeypatch.setattr(
        get_settings(), "auto_accept_disabled_workflows", str(project["workflow_id"])
    )
    ids = _run(client, project_id, {"br.pdf": 1, "sme.pdf": 2})
    assert (
        _fields(client, ids["br.pdf"])["business_registration_number"]["effective_normalized_value"]
        is None
    )


def test_s7_second_pass_can_contradict_a_corroborated_name_but_never_confirm_one() -> None:
    wrong = "주식회사 가온정말"  # every document carries the same misread
    docs = [
        field(D1, "company_name", wrong, second="법인명:주식회사가온정밀"),
        field(D2, "company_name", wrong, doc_type=SME, second="기업명:주식회사가온정밀"),
    ]
    assert accepted(decide(docs, CTX, Strategy.S5), D1, "company_name")  # residual without the veto
    vetoed = decide(docs, CTX, Strategy.S7)
    assert not accepted(vetoed, D1, "company_name")
    assert vetoed[(D1, "company_name")].reason == "SECOND_PASS_CONTRADICTS_NAME"
    agreeing = [
        field(D1, "company_name", "주식회사 가온정밀", second="법인명:주식회사가온정밀"),
        field(
            D2, "company_name", "주식회사 가온정밀", doc_type=SME, second="기업명:주식회사가온정밀"
        ),
    ]
    assert accepted(decide(agreeing, CTX, Strategy.S7), D1, "company_name")
    # a lone name is still not accepted by a matching second pass (rule 4)
    alone = [field(D1, "student_name", "류하늘", doc_type=ENR, second="성명:류하늘")]
    assert not accepted(decide(alone, CTX, Strategy.S7), D1, "student_name")
    assert parse_strategy("s7") == Strategy.S7


# ------------------------------------------------------------------ D2: boundary rule and plausibility


def _ctx(**extra) -> ProjectContext:
    return ProjectContext(reference_date=date(2027, 3, 1), **extra)


def test_second_pass_only_date_near_the_reference_date_is_left_to_a_human() -> None:
    near = [field(D1, "valid_until", "2027-03-05", doc_type=TAX, second="2027-03-05")]
    far = [field(D1, "valid_until", "2027-03-25", doc_type=TAX, second="2027-03-25")]
    assert decide(near, _ctx(), Strategy.S7)[(D1, "valid_until")].reason == "NEAR_DECISION_BOUNDARY"
    assert accepted(decide(far, _ctx(), Strategy.S7), D1, "valid_until")
    expired_side = [field(D1, "valid_until", "2027-02-24", doc_type=TAX, second="2027-02-24")]
    assert not accepted(decide(expired_side, _ctx(), Strategy.S7), D1, "valid_until")


def test_issue_date_near_the_age_limit_and_gpa_near_the_threshold_are_left_to_a_human() -> None:
    ctx = _ctx(issue_max_age_days=90, gpa_threshold=3.0)
    near_limit = [
        field(D1, "issue_date", "2026-12-05", doc_type=ENR, second="2026-12-05")
    ]  # 86 days
    assert (
        decide(near_limit, ctx, Strategy.S7)[(D1, "issue_date")].reason == "NEAR_DECISION_BOUNDARY"
    )
    recent = [field(D1, "issue_date", "2027-02-10", doc_type=ENR, second="2027-02-10")]
    assert accepted(decide(recent, ctx, Strategy.S7), D1, "issue_date")
    gpa_near = [
        field(D1, "gpa", "3.1", doc_type=TRN, second="3.1"),
        field(D1, "gpa_scale", "4.5", doc_type=TRN, second="4.5"),
    ]
    assert decide(gpa_near, ctx, Strategy.S7)[(D1, "gpa")].reason == "NEAR_DECISION_BOUNDARY"
    gpa_clear = [
        field(D1, "gpa", "3.8", doc_type=TRN, second="3.8"),
        field(D1, "gpa_scale", "4.5", doc_type=TRN, second="4.5"),
    ]
    assert accepted(decide(gpa_clear, ctx, Strategy.S7), D1, "gpa")
    # without a configured boundary nothing is near one
    assert accepted(decide(gpa_near, _ctx(), Strategy.S7), D1, "gpa")


def test_validity_end_implausibly_far_from_the_issue_date_is_blocked() -> None:
    fields = [
        field(D1, "issue_date", "2027-02-20", doc_type=TAX, method="document_semantic_issue_date"),
        field(
            D1, "valid_until", "2029-03-22", doc_type=TAX, second="2029-03-22"
        ),  # a year digit misread
    ]
    assert (
        decide(fields, _ctx(), Strategy.S7)[(D1, "valid_until")].reason
        == "FORMAT_VALIDITY_TOO_LONG"
    )
    plausible = [
        field(D1, "issue_date", "2027-02-20", doc_type=TAX, method="document_semantic_issue_date"),
        field(D1, "valid_until", "2027-03-22", doc_type=TAX, second="2027-03-22"),
    ]
    assert accepted(decide(plausible, _ctx(), Strategy.S7), D1, "valid_until")
