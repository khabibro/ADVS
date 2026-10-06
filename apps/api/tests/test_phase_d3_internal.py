"""Phase D3: confirmation from the document's own content. Made-up values only."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    Strategy,
    decide,
)
from app.document_intelligence.confirmations import (
    date_pair,
    gpa_arithmetic,
    printed_twice,
    scale_confirmation,
)
from app.document_intelligence.internal_evidence import (
    DateBox,
    DocFacts,
    GpaFacts,
    corporate_number_valid,
    extract_facts,
)

TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
SME = DocumentType.SME_CONFIRMATION_CERTIFICATE
SOC = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
ENR = DocumentType.ENROLLMENT_CERTIFICATE
TRN = DocumentType.TRANSCRIPT


def box(text: str, x: float, y: float, width: float = 300.0, height: float = 30.0) -> dict:
    return {"text": text, "bounding_box": {"x": x, "y": y, "width": width, "height": height}}


def page(*lines: dict) -> list[dict]:
    return [{"page_number": 1, "lines": list(lines)}]


# ----------------------------------------------------------------- facts


def test_facts_pair_each_semester_gpa_with_the_credits_above_it_and_skip_the_cumulative_line() -> (
    None
):
    lines = [
        box("취득학점: 15", 100, 100, 120),
        box("평점평균: 3.00/4.5 백분율: 80.00/100", 80, 140, 400),
        box("취득학점: 18", 100, 220, 120),
        box("평점평균: 4.00/4.5 백분율: 93.00/100", 80, 260, 400),
        box("취득학점: 12", 100, 340, 120),
        box("평점평균: 3.50/4.5 백분율: 87.00/100", 80, 380, 400),
        box("총 취득학점: 45", 100, 460, 120),
        box("평점평균: 3.53/4.5 백분율: 88.00/100", 80, 500, 400),
        box("A+=4.5(95-100), A0=4.0(90-94)", 40, 900, 500),
    ]
    facts = extract_facts(page(*lines))
    assert facts.gpa is not None
    assert facts.gpa.pairs == ((15, 3.0), (18, 4.0), (12, 3.5))
    assert facts.gpa.total_credits == 45
    assert facts.gpa.legend_max == "4.5"
    assert (
        gpa_arithmetic(facts, 3.53).state == "CONFIRMED"
    )  # (45 + 72 + 42) / 45 = 3.533 -> within 0.02?


def test_gpa_arithmetic_confirms_blocks_or_abstains() -> None:
    pairs = GpaFacts(pairs=((15, 3.0), (18, 4.0), (12, 3.5)), total_credits=45)
    facts = DocFacts(gpa=pairs)
    assert gpa_arithmetic(facts, 3.53).state == "CONFIRMED"
    assert gpa_arithmetic(facts, 3.80).state == "MISMATCH"  # a misread never confirms itself
    assert (
        gpa_arithmetic(DocFacts(gpa=GpaFacts(pairs=((15, 3.0), (18, 4.0)))), 3.5).state == "NONE"
    )  # too few
    # printed totals are checked against the pairs: inconsistent credits give no evidence
    assert (
        gpa_arithmetic(DocFacts(gpa=GpaFacts(pairs=pairs.pairs, total_credits=60)), 3.53).state
        == "NONE"
    )
    points = DocFacts(gpa=GpaFacts(total_points=372.0, total_credits=98))
    assert gpa_arithmetic(points, 3.80).state == "CONFIRMED"
    assert gpa_arithmetic(points, 3.30).state == "MISMATCH"
    assert gpa_arithmetic(None, 3.0).state == "NONE"


def test_scale_is_confirmed_by_the_legend_and_the_semester_scales() -> None:
    facts = DocFacts(gpa=GpaFacts(semester_scales=("4.3", "4.3", "4.3"), legend_max="4.3"))
    assert scale_confirmation(facts, "4.3").state == "CONFIRMED"
    assert scale_confirmation(facts, "4.5").state == "MISMATCH"
    assert scale_confirmation(DocFacts(gpa=GpaFacts()), "4.5").state == "NONE"


# ----------------------------------------------------------------- dates


def test_tax_and_social_certificates_confirm_issue_date_and_validity_end_by_their_profile() -> None:
    issue = date(2027, 3, 1)
    assert date_pair(TAX, issue, None, date(2027, 3, 31)).state == "CONFIRMED"
    assert date_pair(SOC, issue, None, date(2027, 4, 1)).state == "CONFIRMED"  # tolerance 1 day
    assert date_pair(TAX, issue, None, date(2027, 5, 30)).state == "MISMATCH"
    assert date_pair(TAX, None, None, date(2027, 3, 31)).state == "NONE"  # never inferred
    assert date_pair(TAX, issue, None, None).state == "NONE"


def test_sme_range_is_confirmed_only_together_with_the_separately_printed_issue_date() -> None:
    assert (
        date_pair(SME, date(2027, 1, 9), date(2027, 1, 1), date(2027, 12, 31)).state == "CONFIRMED"
    )
    assert date_pair(SME, None, date(2027, 1, 1), date(2027, 12, 31)).state == "NONE"
    assert (
        date_pair(SME, date(2027, 6, 9), date(2027, 1, 1), date(2027, 12, 31)).state == "MISMATCH"
    )
    assert date_pair(SME, date(2027, 1, 9), date(2027, 1, 1), date(2028, 6, 30)).state == "MISMATCH"


def test_a_date_printed_twice_is_confirmed_only_with_two_separate_bare_boxes() -> None:
    a = DateBox("2027-02-20", 1, 100, 100, 200, 30, True)
    b = DateBox("2027-02-20", 1, 100, 400, 260, 30, True)
    assert printed_twice(DocFacts(dates=(a, b)), "2027-02-20").state == "CONFIRMED"
    assert printed_twice(DocFacts(dates=(a,)), "2027-02-20").state == "NONE"  # never borrowed
    close = DateBox("2027-02-20", 1, 100, 110, 200, 30, True)
    assert (
        printed_twice(DocFacts(dates=(a, close)), "2027-02-20").state == "NONE"
    )  # same line region
    labelled = DateBox("2027-02-20", 1, 100, 400, 260, 30, False)
    assert printed_twice(DocFacts(dates=(a, labelled)), "2027-02-20").state == "NONE"
    assert printed_twice(DocFacts(dates=(a, b)), "2027-02-21").state == "NONE"


def test_facts_mark_a_date_followed_by_enrolment_status_as_bare_and_a_labelled_date_as_not() -> (
    None
):
    facts = extract_facts(
        page(
            box("2027년 02월 20일 재학중", 100, 100),
            box("입학일자 : 2025년 03월 02일", 100, 160),
            box("2027년 02월 20일", 100, 400),
        )
    )
    bare = [(d.iso, d.bare) for d in facts.dates]
    assert ("2027-02-20", True) in bare and ("2025-03-02", False) in bare
    assert printed_twice(facts, "2027-02-20").state == "CONFIRMED"


def test_corporate_registration_number_check_digit() -> None:
    def build(prefix: str) -> str:
        total = sum(int(d) * (1 if i % 2 == 0 else 2) for i, d in enumerate(prefix))
        return prefix + str((10 - total % 10) % 10)

    good = build("110111234567")
    assert corporate_number_valid(good) and corporate_number_valid(good[:6] + "-" + good[6:])
    assert not corporate_number_valid(good[:-1] + str((int(good[-1]) + 1) % 10))
    assert not corporate_number_valid("12345")


# ----------------------------------------------------------------- policy


D1 = uuid.uuid4()
CTX = ProjectContext(reference_date=date(2027, 3, 10))


def f(
    name: str,
    value: str,
    doc_type: DocumentType = TAX,
    *,
    method: str | None = "label_match",
    review: bool = False,
    facts: DocFacts | None = None,
    doc: uuid.UUID = D1,
) -> FieldInput:
    return FieldInput(doc, doc.hex, doc_type, name, value, 0.96, True, review, method, facts=facts)


def test_s8_confirms_an_ocr_issue_date_and_validity_end_that_fit_the_profile() -> None:
    fields = [
        f("issue_date", "2027-03-01", method="document_semantic_issue_date", review=True),
        f("valid_until", "2027-03-31"),
    ]
    for strategy in (Strategy.S4, Strategy.S7):
        assert not any(d.accepted for d in decide(fields, CTX, strategy).values())
    decisions = decide(fields, CTX, Strategy.S8)
    assert all(d.accepted and d.sources == ("date_pair",) for d in decisions.values())


def test_s8_blocks_a_pair_that_does_not_fit_and_never_accepts_a_lone_inferred_date() -> None:
    off = [
        f("issue_date", "2027-03-01", method="document_semantic_issue_date", review=True),
        f("valid_until", "2027-04-20"),
    ]
    decisions = decide(off, CTX, Strategy.S8)
    assert decisions[(D1, "valid_until")].reason == "DATE_PAIR_MISMATCH"
    assert not decisions[(D1, "issue_date")].accepted
    lone = [f("issue_date", "2027-03-01", ENR, method="document_semantic_issue_date", review=True)]
    assert decide(lone, CTX, Strategy.S8)[(D1, "issue_date")].reason == "SEMANTIC_INFERENCE"


def test_s8_confirms_a_student_issue_date_printed_twice() -> None:
    a = DateBox("2027-03-01", 1, 100, 100, 200, 30, True)
    b = DateBox("2027-03-01", 1, 100, 500, 200, 30, True)
    one = DocFacts(dates=(a,))
    two = DocFacts(dates=(a, b))

    def item(facts: DocFacts) -> list[FieldInput]:
        return [
            f(
                "issue_date",
                "2027-03-01",
                ENR,
                method="document_semantic_issue_date",
                review=True,
                facts=facts,
            )
        ]

    assert not decide(item(one), CTX, Strategy.S8)[(D1, "issue_date")].accepted
    decision = decide(item(two), CTX, Strategy.S8)[(D1, "issue_date")]
    assert decision.accepted and decision.sources == ("printed_twice",)


def test_s8_confirms_gpa_and_scale_from_the_page_and_blocks_a_mismatch() -> None:
    facts = DocFacts(
        gpa=GpaFacts(
            pairs=((15, 3.0), (18, 4.0), (12, 3.5)),
            total_credits=45,
            semester_scales=("4.5",) * 3,
            legend_max="4.5",
        )
    )
    good = [f("gpa", "3.53", TRN, facts=facts), f("gpa_scale", "4.5", TRN, facts=facts)]
    decisions = decide(good, CTX, Strategy.S8)
    assert decisions[(D1, "gpa")].sources == ("arithmetic",)
    assert decisions[(D1, "gpa_scale")].sources == ("grading_scale",)
    bad = [f("gpa", "3.93", TRN, facts=facts), f("gpa_scale", "4.5", TRN, facts=facts)]
    assert decide(bad, CTX, Strategy.S8)[(D1, "gpa")].reason == "ARITHMETIC_MISMATCH"
    assert not decide(good, CTX, Strategy.S7)[(D1, "gpa")].accepted  # not before D3


def test_validity_end_is_supported_by_a_separately_printed_date_one_period_earlier() -> None:
    from app.document_intelligence.confirmations import issue_date_box_for

    own = DateBox("2027-03-31", 1, 100, 300, 200, 30, False)
    earlier = DateBox("2027-03-01", 1, 400, 800, 200, 30, True)
    other = DateBox("2026-01-15", 1, 400, 900, 200, 30, True)
    assert (
        issue_date_box_for(TAX, DocFacts(dates=(own, earlier, other)), date(2027, 3, 31)).state
        == "CONFIRMED"
    )
    assert (
        issue_date_box_for(TAX, DocFacts(dates=(own, other)), date(2027, 3, 31)).state == "NONE"
    )  # never invented
    assert (
        issue_date_box_for(TAX, DocFacts(dates=(earlier,)), date(2027, 3, 31)).state == "NONE"
    )  # needs its own box
    unlabelled = DateBox(
        "2027-03-01", 1, 400, 800, 200, 30, False
    )  # a labelled date does not count
    assert (
        issue_date_box_for(TAX, DocFacts(dates=(own, unlabelled)), date(2027, 3, 31)).state
        == "NONE"
    )
    assert (
        issue_date_box_for(SME, DocFacts(dates=(own, earlier)), date(2027, 3, 31)).state == "NONE"
    )


def test_s8_confirms_a_validity_end_from_the_page_when_the_issue_date_was_not_extracted() -> None:
    facts = DocFacts(
        dates=(
            DateBox("2027-03-31", 1, 100, 300, 200, 30, False),
            DateBox("2027-03-01", 1, 400, 800, 200, 30, True),
        )
    )
    item = [f("valid_until", "2027-03-31", facts=facts)]
    assert decide(item, CTX, Strategy.S8)[(D1, "valid_until")].accepted
    assert not decide(item, CTX, Strategy.S7)[(D1, "valid_until")].accepted


def test_issuer_university_with_the_title_glued_on_is_read() -> None:
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.ocr.models import (
        BoundingBox,
        OCRDocumentResult,
        OCRLine,
        OCRPage,
    )

    line = OCRLine("한국샘플대학교총장", 0.99, BoundingBox(100, 900, 700, 80))
    page = OCRPage(1, line.text, [line], metadata={"source": "ocr"})
    values = ExtractorRegistry().extract(TRN, OCRDocumentResult("ocr", [page], line.text))
    assert {v.field_name: v.normalized_value for v in values}["university_name"] == "한국샘플대학교"


# ----------------------------------------------------------------- decision-robust (D3-5)


def test_alternative_readings_cover_substitution_transposition_drop_and_add() -> None:
    from app.document_intelligence.ocr_confusions import (
        CONFUSION_TABLE_VERSION,
        alternative_readings,
    )

    alts = alternative_readings("3.8")
    assert {"3.0", "3.6", "3.3"} <= alts  # 8 -> 0 / 6 / 3
    assert alternative_readings("38") >= {"83"}  # adjacent digits transposed
    assert ".38" not in alts  # a separator is not transposed
    assert ".8" in alts and "3." in alts  # a dropped digit
    assert "33.8" in alts and "3.88" in alts  # an added digit
    assert "3.8" not in alts and CONFUSION_TABLE_VERSION


def test_gpa_is_decision_robust_only_when_every_plausible_misreading_gives_the_same_outcome() -> (
    None
):
    from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust

    low = [RuleSpec(TRN, "gpa", "at_least", bound_number=0.5)]
    high = [RuleSpec(TRN, "gpa", "at_least", bound_number=3.5)]
    assert is_decision_robust(low, None, "gpa", TRN, "3.8", scale=4.5)
    assert not is_decision_robust(high, None, "gpa", TRN, "3.8", scale=4.5)  # 3.0 would flip it
    assert not is_decision_robust([], None, "gpa", TRN, "3.8", scale=4.5)  # no rule uses it


def test_a_date_is_almost_never_robust_because_a_transposed_year_flips_expiry() -> None:
    from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust

    spec = [RuleSpec(TAX, "valid_until", "on_or_after_ref")]
    ref = date(2027, 3, 10)
    assert not is_decision_robust(
        spec, ref, "valid_until", TAX, "2030-12-31"
    )  # 2003-12-31 would be expired
    assert not is_decision_robust(
        spec, ref, "valid_until", TAX, "2027-03-31"
    )  # 2021-03-31 would be expired


def test_a_confirmed_date_profile_rules_out_alternatives_that_break_it() -> None:
    from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust

    spec = [RuleSpec(TAX, "valid_until", "on_or_after_ref")]
    ref = date(2027, 3, 10)
    siblings = {
        "issue_date": date(2027, 3, 1),
        "valid_from": None,
        "valid_until": date(2027, 3, 31),
    }
    # the year 2021 reading would break the 30-day profile with the printed issue date
    assert is_decision_robust(spec, ref, "valid_until", TAX, "2027-03-31", siblings=siblings)


def test_s9_accepts_a_robust_value_and_labels_it_s8_does_not() -> None:
    from app.document_intelligence.decision_robust import RuleSpec

    ctx = ProjectContext(
        reference_date=date(2027, 3, 10),
        rules=(RuleSpec(TRN, "gpa", "at_least", bound_number=0.5),),
    )
    gpa = [f("gpa", "3.8", TRN), f("gpa_scale", "4.5", TRN)]
    assert not decide(gpa, ctx, Strategy.S8)[(D1, "gpa")].accepted
    decision = decide(gpa, ctx, Strategy.S9)[(D1, "gpa")]
    assert decision.accepted and decision.robust and decision.to_dict()["confusion_table_version"]


def test_fields_no_rule_uses_are_marked_informational(client, db_session) -> None:
    import runpy
    import uuid as _uuid
    from pathlib import Path

    import fitz
    from sqlalchemy import select

    from app.models.entities import Checklist

    runpy.run_path(str(Path(__file__).resolve().parents[3] / "scripts" / "seed.py"))["main"]()
    workflow = db_session.scalar(select(Checklist).where(Checklist.name == "학생 제출서류 점검"))
    project = client.post(
        "/api/v1/projects",
        json={"name": f"i{_uuid.uuid4().hex[:4]}", "workflow_id": str(workflow.id)},
    ).json()
    document = fitz.open()
    page = document.new_page()
    for index, line in enumerate(
        [
            "재 학 증 명 서",
            "성          명 : 류하늘",
            "소          속 : 공과대학 기계공학과",
            "학          번 : 2025123456",
            "위의 사실을 증명합니다.",
            "2026년 09월 20일",
            "한국샘플대학교 총장",
        ]
    ):
        page.insert_text((60, 60 + index * 26), line, fontsize=12, fontname="korea")
    data = document.tobytes()
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("e.pdf", data, "application/pdf")},
    ).json()
    client.post(f"/api/v1/documents/{uploaded['id']}/process")
    fields = {
        f["field_name"]: f
        for f in client.get(f"/api/v1/documents/{uploaded['id']}").json()["extracted_fields"]
    }
    assert fields["student_id"]["decision_relevant"] is True  # required by the workflow
    assert fields["issue_date"]["decision_relevant"] is True
    assert fields["department"]["decision_relevant"] is False  # no rule uses it


def test_business_number_type_code_plausibility() -> None:
    from app.document_intelligence.confirmations import business_number_type_plausible

    assert business_number_type_plausible("1048127382", "corporate") is True  # code 81
    assert business_number_type_plausible("1043127382", "corporate") is False  # code 31
    assert business_number_type_plausible("1043127382", "individual") is True
    assert business_number_type_plausible("1048127382", "individual") is False
    assert business_number_type_plausible("1043127382", None) is None
    assert business_number_type_plausible("123", "corporate") is None
