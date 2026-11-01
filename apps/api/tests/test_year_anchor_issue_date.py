"""A student issue date inferred from an unlabelled block: the certificate number's year anchors it
(all values invented)."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import FieldInput, ProjectContext, Strategy, decide
from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust
from app.document_intelligence.internal_evidence import DateBox, DocFacts, extract_facts

ENR = DocumentType.ENROLLMENT_CERTIFICATE
SPECS = [
    RuleSpec(ENR, "issue_date", "max_age", days=90),
    RuleSpec(ENR, "issue_date", "on_or_before", bound_date=date(2030, 12, 31)),
]
REFERENCE = date(2030, 6, 10)
ISSUED = "2030-05-31"  # 10 days old; every digit-confusion reading with the anchored year is still valid
DOC = uuid.uuid4()


def robust(value: str, year: int | None) -> bool:
    return is_decision_robust(SPECS, REFERENCE, "issue_date", ENR, value, year_anchor=year)


def test_the_anchor_removes_the_year_readings() -> None:
    assert robust(ISSUED, None) is False  # a year digit could be misread
    assert robust(ISSUED, 2030) is True


def test_a_date_whose_year_differs_from_the_anchor_is_never_robust() -> None:
    assert robust(ISSUED, 2029) is False


def test_a_month_or_day_misreading_that_flips_the_verdict_keeps_it_out() -> None:
    assert robust("2030-03-15", 2030) is False  # 87 days old: a digit away from the limit


def verdict(*, years: tuple[int, ...], boxes: tuple[DateBox, ...], value: str = ISSUED):
    item = FieldInput(
        document_id=DOC,
        checksum=DOC.hex,
        document_type=ENR,
        field_name="issue_date",
        value=value,
        confidence=0.97,
        ocr=True,
        needs_review=True,
        extraction_method="document_semantic_issue_date",
        facts=DocFacts(dates=boxes, number_years=years),
    )
    context = ProjectContext(reference_date=REFERENCE, issue_max_age_days=90, rules=tuple(SPECS))
    return decide([item], context, Strategy.S9)[(DOC, "issue_date")]


OWN = DateBox(ISSUED, 1, 100, 900, 300, 40, True)
FAR_BIRTH = DateBox("2001-09-27", 1, 100, 100, 300, 40, True)
NEAR_ADMISSION = DateBox("2028-03-02", 1, 100, 800, 300, 40, True)


def test_anchored_alone_in_its_block_is_accepted_as_robust() -> None:
    decision = verdict(years=(2030,), boxes=(FAR_BIRTH, OWN))
    assert decision.accepted and decision.robust
    assert decision.to_dict()["confirmation"] == "DECISION_ROBUST"


def test_another_date_in_the_same_block_keeps_it_in_review() -> None:
    assert not verdict(years=(2030,), boxes=(NEAR_ADMISSION, OWN)).accepted


def test_a_year_that_does_not_match_the_number_keeps_it_in_review() -> None:
    assert not verdict(years=(2029,), boxes=(FAR_BIRTH, OWN)).accepted


def test_no_or_two_printed_number_years_keep_it_in_review() -> None:
    assert not verdict(years=(), boxes=(FAR_BIRTH, OWN)).accepted
    assert not verdict(years=(2030, 2029), boxes=(FAR_BIRTH, OWN)).accepted


def test_a_value_next_to_the_age_limit_is_not_accepted() -> None:
    near = DateBox("2030-03-13", 1, 100, 900, 300, 40, True)
    assert not verdict(years=(2030,), boxes=(FAR_BIRTH, near), value="2030-03-13").accepted


def _page(lines: list[str]) -> list[dict]:
    return [
        {
            "page_number": 1,
            "lines": [
                {"text": t, "bounding_box": {"x": 10, "y": 20 + 40 * i, "width": 300, "height": 30}}
                for i, t in enumerate(lines)
            ],
        }
    ]


def test_the_number_year_is_read_even_when_the_number_is_split_over_boxes() -> None:
    facts = extract_facts(_page(["제2030", "-0012345호", "재 학 증 명 서"]))
    assert facts.number_years == (2030,)


def test_a_number_further_down_the_page_or_two_different_years() -> None:
    body = ["본문"] * 9 + ["제2030-123호"]
    assert extract_facts(_page(body)).number_years == ()
    assert extract_facts(_page(["제2030-1호", "제2029-2호"])).number_years == (2029, 2030)
