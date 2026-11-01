"""Transcript arithmetic over a three-column layout in which a semester continues at the top of the next column
(invented values)."""

from __future__ import annotations

from app.document_intelligence.confirmations import gpa_arithmetic, scale_confirmation
from app.document_intelligence.internal_evidence import extract_facts

SEMESTERS = [(15, "3.00", "80.00"), (18, "4.00", "93.00"), (12, "3.50", "87.00"),
             (16, "3.25", "82.00"), (17, "3.50", "85.00"), (14, "3.75", "90.00")]
TOTAL_CREDITS, TOTAL_GPA, TOTAL_PERCENT = 92, 3.51, "86.25"  # 323 / 92 and 7935 / 92


def box(text: str, x: float, y: float, width: float) -> dict:
    return {"text": text, "bounding_box": {"x": x, "y": y, "width": width, "height": 30}}


def facts_for(semesters=SEMESTERS, total=TOTAL_GPA, percent=TOTAL_PERCENT, drop_credit=None, scale="4.5", legend="4.5"):
    c1, c2, c3 = 100, 600, 1100
    # credits: S1..S3 in column 1 (S3 at the bottom), S4..S6 in column 2 (S6 at the bottom)
    credit_at = [(c1, 100), (c1, 220), (c1, 340), (c2, 180), (c2, 300), (c2, 420)]
    # GPA lines: S1, S2 in column 1; S3 continues at the top of column 2; S4, S5 follow; S6 at the top of column 3
    gpa_at = [(c1, 140), (c1, 260), (c2, 100), (c2, 220), (c2, 340), (c3, 100)]
    lines = []
    for index, ((credits, gpa, pct), (cx, cy), (gx, gy)) in enumerate(zip(semesters, credit_at, gpa_at, strict=True)):
        if index != drop_credit:
            lines.append(box(f"취득학점: {credits}", cx, cy, 120))
        lines.append(box(f"평점평균: {gpa}/{scale} 백분율: {pct}/100", gx, gy, 400))
    lines += [box(f"총 취득학점: {TOTAL_CREDITS}", c3, 300, 120),
              box(f"평점평균: {total:.2f}/{scale} 백분율: {percent}/100", c3, 340, 400),
              box(f"A+={legend}(95-100), A0=4.0(90-94)", 100, 900, 500)]
    return extract_facts([{"page_number": 1, "lines": lines}])


def test_columns_and_a_semester_continuing_in_the_next_column_confirm_the_total() -> None:
    facts = facts_for()
    assert facts.gpa is not None and facts.gpa.ordered_pairing
    assert facts.gpa.pairs == tuple((c, float(g)) for c, g, _ in SEMESTERS)
    verdict = gpa_arithmetic(facts, 3.51)
    assert verdict.state == "CONFIRMED" and "weighted_percent" in (verdict.detail or "")


def test_a_misread_semester_gpa_total_or_percent_never_confirms() -> None:
    bad_semester = [*SEMESTERS[:3], (16, "3.85", "82.00"), *SEMESTERS[4:]]
    assert gpa_arithmetic(facts_for(bad_semester), 3.51).state == "MISMATCH"
    assert gpa_arithmetic(facts_for(total=3.57), 3.57).state == "MISMATCH"
    bad_percent = [*SEMESTERS[:4], (17, "3.50", "75.00"), SEMESTERS[5]]
    # a table that does not reproduce the printed 백분율 is a reading problem: it cannot be judged by
    assert gpa_arithmetic(facts_for(bad_percent), 3.51).state == "NONE"


def test_misread_credits_or_a_dropped_line_do_not_confirm() -> None:
    bad_credits = [SEMESTERS[0], (19, "4.00", "93.00"), *SEMESTERS[2:]]
    assert gpa_arithmetic(facts_for(bad_credits), 3.51).state != "CONFIRMED"  # the sum differs from the total
    assert gpa_arithmetic(facts_for(drop_credit=2), 3.51).state != "CONFIRMED"


def test_the_scale_is_confirmed_when_every_line_and_the_legend_agree() -> None:
    assert scale_confirmation(facts_for(), "4.5").state == "CONFIRMED"
    assert scale_confirmation(facts_for(legend="4.0"), "4.5").state == "MISMATCH"


def test_the_tolerance_is_the_rounding_bound_and_not_wider() -> None:
    # the credit-weighted mean of the invented table is 3.5109, which rounds to 3.51; the printed total may be
    # one last-place unit away from that and no more
    for total in (3.50, 3.51, 3.52):
        assert gpa_arithmetic(facts_for(total=total), total).state == "CONFIRMED", total
    for total in (3.49, 3.53, 3.62):
        assert gpa_arithmetic(facts_for(total=total), total).state == "MISMATCH", total


def test_a_sound_table_that_disagrees_is_a_mismatch_a_broken_table_is_not() -> None:
    # semester GPA misread (one digit): credits and 백분율 still add up, the GPA does not -> truly disagrees
    bad_semester = [*SEMESTERS[:2], (12, "3.80", "87.00"), *SEMESTERS[3:]]
    assert gpa_arithmetic(facts_for(bad_semester), 3.51).state == "MISMATCH"
    # two semesters' values swapped between their credits (a pairing error): 백분율 no longer adds up -> NONE
    swapped = [(15, "3.00", "93.00"), (18, "4.00", "80.00"), *SEMESTERS[2:]]
    assert gpa_arithmetic(facts_for(swapped), 3.51).state == "NONE"
    # a dropped credits line: the credits cannot add up to the total -> NONE
    assert gpa_arithmetic(facts_for(drop_credit=1), 3.51).state == "NONE"
