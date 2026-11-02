"""Student pair: the enrolment certificate is primary, the transcript confirms (all values invented).

Layout of the invented pair: both documents print the same person's name and birth date, the admission date, the
issuer line and the issue date on one day."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import FieldInput, ProjectContext, Strategy, decide
from app.document_intelligence.decision_robust import RuleSpec

ENR, TRN = DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT
REF = date(2030, 6, 10)
CTX = ProjectContext(
    reference_date=REF,
    issue_max_age_days=90,
    rules=(RuleSpec(ENR, "issue_date", "max_age", days=90),),
)
NAME, BIRTH, ADMIT, UNIV, ISSUE = "류하늘", "2008-05-17", "2026-03-02", "가상과학기술대학교", "2030-05-20"
GOOD = 0.97
LOW = 0.80


def item(doc, kind, field, value, conf=GOOD, method="regex", review=False):
    return FieldInput(
        document_id=doc,
        checksum=doc.hex,
        document_type=kind,
        field_name=field,
        value=value,
        confidence=conf,
        ocr=True,
        needs_review=review,
        extraction_method=method,
    )


def pair(strategy=Strategy.S10, enr=None, trn=None):
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    base = {"student_name": NAME, "birth_date": BIRTH, "admission_date": ADMIT, "university_name": UNIV}
    e = {**base, "issue_date": ISSUE, **(enr or {})}
    t = {**base, "issue_date": ISSUE, **(trn or {})}
    fields = [item(d1, ENR, k, v if not isinstance(v, tuple) else v[0], conf=v[1] if isinstance(v, tuple) else GOOD,
                   method="document_semantic_issue_date" if k == "issue_date" else "regex",
                   review=(k == "issue_date")) for k, v in e.items() if v is not None]
    fields += [item(d2, TRN, k, v if not isinstance(v, tuple) else v[0], conf=v[1] if isinstance(v, tuple) else GOOD,
                    method="document_semantic_issue_date" if k == "issue_date" else "regex",
                    review=(k == "issue_date")) for k, v in t.items() if v is not None]
    out = decide(fields, CTX, strategy)
    return {(doc, f): out.get((doc, f)) for doc in (d1, d2) for f in base | {"issue_date": 0}}, d1, d2


def accepted(result, doc, field):
    decision = result.get((doc, field))
    return bool(decision and decision.accepted)


def test_equal_values_on_both_documents_confirm_each_other() -> None:
    res, enr, trn = pair()
    for field in ("student_name", "birth_date", "admission_date", "university_name", "issue_date"):
        assert accepted(res, enr, field) and accepted(res, trn, field), field


def test_an_issue_date_is_confirmed_by_the_same_date_and_marked_cross_document() -> None:
    res, enr, _ = pair()
    assert "cross_document" in res[(enr, "issue_date")].sources


def test_issued_on_different_days_gives_no_date_confirmation() -> None:
    res, enr, trn = pair(trn={"issue_date": "2030-05-21"})
    assert not accepted(res, enr, "issue_date") and not accepted(res, trn, "issue_date")


def test_a_different_value_on_one_document_confirms_nothing_for_that_field() -> None:
    for field, wrong in (
        ("student_name", "류하눌"),
        ("birth_date", "2008-05-18"),
        ("admission_date", "2026-03-03"),
        ("university_name", "가상과학기술대학원"),
    ):
        res, enr, trn = pair(trn={field: wrong})
        assert not accepted(res, enr, field), field
        assert not accepted(res, trn, field), field


def test_a_missing_side_gives_no_confirmation() -> None:
    res, enr, _ = pair(trn={"birth_date": None, "issue_date": None})
    assert not accepted(res, enr, "birth_date") and not accepted(res, enr, "issue_date")


def test_both_reads_must_be_above_the_floor_in_variant_a() -> None:
    res, enr, trn = pair(Strategy.S10, trn={"student_name": (NAME, LOW), "birth_date": (BIRTH, LOW)})
    assert not accepted(res, enr, "student_name")  # the other read is below its floor: no evidence
    assert not accepted(res, trn, "student_name")
    assert not accepted(res, enr, "birth_date")


def test_a_below_floor_read_is_confirmed_by_an_exact_reliable_match_in_variant_b() -> None:
    res, enr, trn = pair(Strategy.S11, trn={"student_name": (NAME, LOW), "issue_date": (ISSUE, LOW)})
    assert accepted(res, trn, "student_name") and accepted(res, enr, "student_name")
    assert accepted(res, trn, "issue_date") and accepted(res, enr, "issue_date")


def test_variant_b_never_confirms_two_below_floor_reads_or_a_mismatch() -> None:
    both_low = pair(
        Strategy.S11,
        enr={"student_name": (NAME, LOW)},
        trn={"student_name": (NAME, LOW)},
    )
    res, enr, trn = both_low
    assert not accepted(res, enr, "student_name") and not accepted(res, trn, "student_name")
    res, enr, trn = pair(Strategy.S11, trn={"student_name": ("박다라", LOW)})
    assert not accepted(res, trn, "student_name") and not accepted(res, enr, "student_name")


def test_the_baseline_strategy_does_not_use_the_pair_rules() -> None:
    res, enr, trn = pair(Strategy.S9)
    assert not accepted(res, enr, "issue_date")  # no cross-document issue date in S9


def test_the_institution_name_part_is_compared_when_a_stamp_covers_the_title() -> None:
    res, enr, trn = pair(enr={"university_name": "가상과학기술대학교총장"})
    assert accepted(res, trn, "university_name")


# ---- S12: the same-person verdict is decision-robust when both names read the same and the birth date is confirmed

def robust_pair(enr=None, trn=None, name_conf=LOW):
    return pair(
        Strategy.S12,
        enr={"student_name": (NAME, name_conf), **(enr or {})},
        trn={"student_name": (NAME, name_conf), **(trn or {})},
    )


def test_two_below_floor_reads_of_the_same_name_settle_the_verdict_not_the_value() -> None:
    res, enr, trn = robust_pair()
    for doc in (enr, trn):
        decision = res[(doc, "student_name")]
        assert decision.accepted and decision.robust
        data = decision.to_dict()
        assert data["confirmation"] == "DECISION_ROBUST" and "값 미확정" in data["label_ko"]


def test_the_baseline_variants_do_not_settle_two_below_floor_names() -> None:
    for strategy in (Strategy.S9, Strategy.S10, Strategy.S11):
        d1, d2 = uuid.uuid4(), uuid.uuid4()
        fields = [
            item(d1, ENR, "student_name", NAME, conf=LOW),
            item(d2, TRN, "student_name", NAME, conf=LOW),
            item(d1, ENR, "birth_date", BIRTH),
            item(d2, TRN, "birth_date", BIRTH),
        ]
        out = decide(fields, CTX, strategy)
        assert not out[(d1, "student_name")].accepted, strategy


def test_a_different_name_on_one_document_settles_nothing() -> None:
    res, enr, trn = robust_pair(trn={"student_name": ("박다라", LOW)})
    assert not accepted(res, enr, "student_name") and not accepted(res, trn, "student_name")
    res, enr, trn = robust_pair(trn={"student_name": ("류하눌", LOW)})  # one character misread on one document
    assert not accepted(res, enr, "student_name") and not accepted(res, trn, "student_name")


def test_a_birth_date_that_is_not_confirmed_on_both_settles_nothing() -> None:
    for trn_birth in ("2008-05-18", None):
        res, enr, trn = robust_pair(trn={"birth_date": trn_birth})
        assert not accepted(res, enr, "student_name"), trn_birth
        assert not accepted(res, trn, "student_name"), trn_birth
    # two below-floor birth dates are not confirmed either (a below-floor read needs a reliable partner)
    res, enr, trn = robust_pair(enr={"birth_date": (BIRTH, LOW)}, trn={"birth_date": (BIRTH, LOW)})
    assert not accepted(res, enr, "student_name") and not accepted(res, trn, "student_name")
    # one below-floor birth date IS confirmed by the reliable one (variant b), so the verdict is settled
    res, enr, trn = robust_pair(trn={"birth_date": (BIRTH, LOW)})
    assert accepted(res, enr, "student_name") and accepted(res, trn, "student_name")


def test_a_name_the_second_reading_contradicts_stays_vetoed() -> None:
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    from app.document_intelligence.auto_acceptance import SecondPassInput

    one = item(d1, ENR, "student_name", NAME, conf=LOW)
    one = FieldInput(**{**one.__dict__, "second_pass": SecondPassInput("류하눌", "류하눌", 0.9)})
    fields = [
        one,
        item(d2, TRN, "student_name", NAME, conf=LOW),
        item(d1, ENR, "birth_date", BIRTH),
        item(d2, TRN, "birth_date", BIRTH),
    ]
    out = decide(fields, CTX, Strategy.S12)
    assert not out[(d1, "student_name")].accepted
