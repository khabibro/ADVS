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
