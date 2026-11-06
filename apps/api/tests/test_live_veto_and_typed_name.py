"""Item 4 (a same-image re-read may not veto a first read that the other document reads identically, unless the
re-read is a plausible different value) and item 6 (a typed name equal to a below-floor read confirms it).
Invented names."""

from __future__ import annotations

import uuid

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    SecondPassInput,
    Strategy,
    _plausible_different_value,
    decide,
)

E, T = uuid.uuid4(), uuid.uuid4()


def _item(doc, kind, name, value, confidence, reread=None) -> FieldInput:
    second = SecondPassInput(reread, reread, 0.9) if reread is not None else None
    return FieldInput(
        doc, f"c{doc}", kind, name, value, confidence, True, False, second_pass=second
    )


def _pair(reread_e, reread_t, strategy, university="가나대학교"):
    items = [
        _item(
            E, DocumentType.ENROLLMENT_CERTIFICATE, "university_name", university, 0.95, reread_e
        ),
        _item(T, DocumentType.TRANSCRIPT, "university_name", university, 0.955, reread_t),
    ]
    return decide(items, ProjectContext(), strategy)


@pytest.mark.parametrize(
    "garbled", ["가나대대학교총", '가나2UZU린"학교총IU팔1', "가나대", "가나대학", "ᄋᄋ가나"]
)
def test_a_garbled_or_truncated_reread_does_not_veto_a_pair_that_agrees(garbled: str) -> None:
    got = _pair(garbled, garbled, Strategy.S21)
    assert got[(E, "university_name")].accepted and got[(T, "university_name")].accepted
    assert got[(E, "university_name")].lifted_veto == garbled


def test_before_the_fix_the_same_reread_vetoed() -> None:
    got = _pair("가나대대학교총", "가나대대학교총", Strategy.S17)
    assert got[(E, "university_name")].reason == "SECOND_PASS_CONTRADICTS_NAME"


def test_a_plausible_different_value_still_vetoes() -> None:
    got = _pair("가다대학교", "가다대학교", Strategy.S21)  # same length, letters only, no stutter
    assert not got[(E, "university_name")].accepted
    assert got[(E, "university_name")].reason == "SECOND_PASS_CONTRADICTS_NAME"


def test_no_matching_partner_keeps_the_veto() -> None:
    items = [
        _item(
            E,
            DocumentType.ENROLLMENT_CERTIFICATE,
            "university_name",
            "가나대학교",
            0.95,
            "가나대대학교총",
        )
    ]
    got = decide(items, ProjectContext(), Strategy.S21)
    assert not got[(E, "university_name")].accepted


def test_a_partner_with_another_value_keeps_the_veto() -> None:
    items = [
        _item(
            E,
            DocumentType.ENROLLMENT_CERTIFICATE,
            "university_name",
            "가나대학교",
            0.95,
            "가나대대학교총",
        ),
        _item(T, DocumentType.TRANSCRIPT, "university_name", "다라대학교", 0.955),
    ]
    got = decide(items, ProjectContext(), Strategy.S21)
    assert not got[(E, "university_name")].accepted


@pytest.mark.parametrize(
    ("reading", "plausible"),
    [
        ("가나대대학교총", False),
        ("가다대학교", True),
        ("가나대", False),
        ("가나2대학교", False),
        ("가나대학교", False),
    ],
)
def test_plausible_different_value(reading: str, plausible: bool) -> None:
    assert _plausible_different_value("가나대학교", reading) is plausible


# ---- item 6: the typed name -----------------------------------------------------------------------------------
def _name(confidence: float, value: str = "김가나", reread=None, doc=E):
    return _item(
        doc, DocumentType.ENROLLMENT_CERTIFICATE, "student_name", value, confidence, reread
    )


def test_typed_name_equal_to_a_low_read_confirms_it() -> None:
    got = decide([_name(0.812)], ProjectContext(applicant_name="김 가나"), Strategy.S21)
    assert got[(E, "student_name")].accepted
    assert got[(E, "student_name")].rule_id.endswith(":APPLICANT_ENTERED")


def test_typed_name_that_differs_confirms_nothing() -> None:
    got = decide([_name(0.812)], ProjectContext(applicant_name="김가다"), Strategy.S21)
    assert not got[(E, "student_name")].accepted


def test_typed_name_never_overrides_a_reliable_read_that_differs() -> None:
    got = decide([_name(0.99, "김가다")], ProjectContext(applicant_name="김가나"), Strategy.S21)
    assert not got[(E, "student_name")].accepted
    assert got[(E, "student_name")].reason == "CONFLICTS_WITH_APPLICATION_VALUE"


def test_a_plausible_different_reread_stops_the_typed_confirmation() -> None:
    got = decide(
        [_name(0.812, reread="김가다")], ProjectContext(applicant_name="김가나"), Strategy.S21
    )
    assert not got[(E, "student_name")].accepted


def test_typed_name_is_inert_before_the_fix() -> None:
    got = decide([_name(0.812)], ProjectContext(applicant_name="김가나"), Strategy.S17)
    assert not got[(E, "student_name")].accepted


def test_reliable_read_with_garbled_reread_is_accepted_when_the_typed_name_equals_it() -> None:
    got = decide(
        [_name(0.995, reread="김가가나나나")], ProjectContext(applicant_name="김가나"), Strategy.S21
    )
    assert got[(E, "student_name")].accepted


def test_a_stray_latin_letter_makes_the_reread_garbled_not_plausible() -> None:
    assert _plausible_different_value("가나대학교", "가나대학m") is False
    assert _plausible_different_value("가나대학교", "가다대학교") is True
