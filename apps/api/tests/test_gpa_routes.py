"""Route A (the page's own GPA-to-백분율 conversion) and route B (the applicant-entered GPA). Every number is
invented."""

from __future__ import annotations

import uuid

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    Strategy,
    decide,
)
from app.document_intelligence.confirmations import gpa_percent_relation, percent_relation_fit
from app.document_intelligence.internal_evidence import DocFacts, GpaFacts

# invented conversion: 백분율 = 20 * GPA + 12 (4.0 -> 92)
SEMESTERS = ((3.0, 72.0), (3.5, 82.0), (2.5, 62.0))


def facts(total: tuple[float, float] | None, semesters=SEMESTERS, legend=()) -> DocFacts:
    return DocFacts(
        gpa=GpaFacts(
            semester_percent_pairs=tuple(semesters), total_pair=total, legend_pairs=tuple(legend)
        )
    )


def test_total_on_the_relation_is_confirmed() -> None:
    assert gpa_percent_relation(facts((3.2, 76.0)), 3.2).state == "CONFIRMED"


def test_one_digit_misread_on_the_total_line_is_not_confirmed() -> None:
    assert gpa_percent_relation(facts((3.8, 76.0)), 3.8).state == "MISMATCH"
    assert gpa_percent_relation(facts((3.2, 78.0)), 3.2).state == "MISMATCH"


def test_a_legend_misread_leaves_no_relation() -> None:
    legend = ((4.0, 92.0), (3.0, 72.0), (2.0, 90.0))  # one entry misread
    assert percent_relation_fit(facts((3.2, 76.0), semesters=(), legend=legend)) is None


def test_the_total_line_cannot_confirm_itself() -> None:
    # two other pairs plus the total: fewer than three independent pairs
    assert gpa_percent_relation(facts((3.2, 76.0), semesters=SEMESTERS[:2]), 3.2).state == "NONE"
    # a semester line equal to the total does not stand in for it
    assert (
        gpa_percent_relation(
            facts((3.0, 72.0), semesters=SEMESTERS[:2] + ((3.0, 72.0),)), 3.0
        ).state
        == "NONE"
    )


def test_no_total_pair_says_nothing() -> None:
    assert gpa_percent_relation(facts(None), 3.2).state == "NONE"


def _items(gpa: str, scale: str, confidence: float = 0.5):
    doc = uuid.uuid4()
    return [
        FieldInput(doc, "x", DocumentType.TRANSCRIPT, name, value, confidence, True, False)
        for name, value in (("gpa", gpa), ("gpa_scale", scale))
    ]


def _decide(items, typed_gpa, typed_scale, strategy=Strategy.S17):
    context = ProjectContext(applicant_gpa=typed_gpa, applicant_gpa_scale=typed_scale)
    return decide(items, context, strategy)


def test_applicant_gpa_exact_match_confirms_even_below_floor() -> None:
    items = _items("3.40", "4.3")
    got = _decide(items, "3.4", "4.3")
    assert all(d.accepted for d in got.values())


def test_applicant_one_digit_typo_goes_to_review() -> None:
    items = _items("3.40", "4.3")
    got = _decide(items, "3.49", "4.3")
    gpa = got[(items[0].document_id, "gpa")]
    assert not gpa.accepted and gpa.reason == "CONFLICTS_WITH_APPLICANT_GPA"


def test_applicant_scale_mismatch_goes_to_review() -> None:
    items = _items("3.40", "4.3")
    got = _decide(items, "3.40", "4.5")
    assert got[(items[0].document_id, "gpa")].accepted
    assert not got[(items[0].document_id, "gpa_scale")].accepted


def test_route_b_is_off_by_default() -> None:
    items = _items("3.40", "4.3")
    got = _decide(items, "3.40", "4.3", strategy=Strategy.S11)
    assert not any(d.accepted for d in got.values())
