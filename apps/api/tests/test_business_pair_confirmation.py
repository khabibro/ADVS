"""Business certificates: the business number, its second copy, a below-floor validity end and the name veto
(all values invented; 123-45-67891 is an invented number with a valid check digit)."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    SecondPassInput,
    Strategy,
    decide,
)
from app.document_intelligence.internal_evidence import DocFacts

BRC = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
INS = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
CTX = ProjectContext(reference_date=date(2030, 6, 10))
GOOD, LOW = 0.97, 0.80
BRN = "1234567891"
BAD_CHECK = "1234567890"


def item(doc, kind, field, value, conf=GOOD, facts=None, second=None):
    return FieldInput(
        document_id=doc,
        checksum=doc.hex,
        document_type=kind,
        field_name=field,
        value=value,
        confidence=conf,
        ocr=True,
        needs_review=False,
        extraction_method="regex",
        facts=facts,
        second_pass=second,
    )


def run(strategy, fields):
    return decide(fields, CTX, strategy)


def ok(result, doc, field):
    decision = result.get((doc, field))
    return bool(decision and decision.accepted)


# ---- the second copy of the business number on the same page ------------------------------------------------

def test_the_second_copy_on_the_page_confirms_the_business_number() -> None:
    d = uuid.uuid4()
    facts = DocFacts(management_numbers=((BRN, GOOD),))
    res = run(Strategy.S13, [item(d, INS, "business_registration_number", BRN, facts=facts)])
    assert ok(res, d, "business_registration_number")
    assert res[(d, "business_registration_number")].sources == ("second_copy",)
    assert not ok(run(Strategy.S11, [item(d, INS, "business_registration_number", BRN, facts=facts)]), d, "business_registration_number")


def test_a_differing_unreliable_or_invalid_copy_confirms_nothing() -> None:
    d = uuid.uuid4()
    for facts, value in (
        (DocFacts(management_numbers=(("1234567899", GOOD),)), BRN),  # a different number
        (DocFacts(management_numbers=((BRN, LOW),)), BRN),  # the copy itself below the floor
        (DocFacts(management_numbers=((BAD_CHECK, GOOD),)), BAD_CHECK),  # the check digit fails
        (DocFacts(), BRN),  # no copy on the page
    ):
        res = run(Strategy.S13, [item(d, INS, "business_registration_number", value, facts=facts)])
        assert not ok(res, d, "business_registration_number"), (facts, value)


# ---- a below-floor business number, confirmed by an exact reliable read on another document -----------------

def test_a_below_floor_business_number_is_confirmed_by_an_exact_reliable_match() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    fields = [item(a, TAX, "business_registration_number", BRN, conf=LOW), item(b, BRC, "business_registration_number", BRN)]
    assert ok(run(Strategy.S13, fields), a, "business_registration_number")
    assert not ok(run(Strategy.S11, fields), a, "business_registration_number")


def test_a_below_floor_business_number_is_not_confirmed_without_a_reliable_exact_match() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    for partner, value in (
        (item(b, BRC, "business_registration_number", BRN, conf=LOW), BRN),  # the partner is below the floor too
        (item(b, BRC, "business_registration_number", "1234567899"), BRN),  # one digit differs
        (item(b, BRC, "business_registration_number", BAD_CHECK), BAD_CHECK),  # the check digit fails
    ):
        res = run(Strategy.S13, [item(a, TAX, "business_registration_number", value, conf=LOW), partner])
        assert not ok(res, a, "business_registration_number"), (value, partner.value)


# ---- a below-floor validity end, confirmed by the issue date plus the legal period -----------------------------

def validity(issue, end, issue_conf=GOOD, end_conf=LOW, kind=TAX):
    d = uuid.uuid4()
    res = run(Strategy.S13, [item(d, kind, "issue_date", issue, conf=issue_conf), item(d, kind, "valid_until", end, conf=end_conf)])
    return ok(res, d, "valid_until")


def test_a_below_floor_validity_end_exactly_the_legal_period_after_a_reliable_issue_date_is_confirmed() -> None:
    assert validity("2030-05-20", "2030-06-19")  # +30


def test_a_shorter_longer_or_earlier_validity_end_is_not_confirmed_and_a_weak_issue_date_does_not_count() -> None:
    assert not validity("2030-05-20", "2030-06-14")  # +25: a shortened validity is consistent, not confirmed
    assert not validity("2030-05-20", "2030-06-20")  # +31
    assert not validity("2030-05-20", "2030-05-10")  # before the issue date
    assert not validity("2030-05-20", "2030-06-19", issue_conf=LOW)
    # the 4대보험 완납증명서 has no legal period: never confirmed this way, whatever the offset
    assert not validity("2030-05-20", "2030-06-19", kind=INS)


def test_the_business_pair_rules_do_not_touch_the_baseline_strategies() -> None:
    d = uuid.uuid4()
    fields = [item(d, TAX, "issue_date", "2030-05-20"), item(d, TAX, "valid_until", "2030-06-19", conf=LOW)]
    assert not ok(run(Strategy.S11, fields), d, "valid_until")


# ---- the name veto lift (S14) -------------------------------------------------------------------------------

NAME = "가나다상사"
JUMBLE = "발 급 일 2030 년 10 월 30 일 총 장"
MISREAD = "가나라상사"  # one character differs: the shape of a misread


def names(first_reading, other_reading, other_value=NAME, strategy=Strategy.S14):
    a, b = uuid.uuid4(), uuid.uuid4()
    one = item(a, BRC, "company_name", NAME, second=SecondPassInput(first_reading, first_reading, 0.9))
    two = item(b, TAX, "company_name", other_value, second=SecondPassInput(other_reading, other_reading, 0.9) if other_reading else None)
    return run(strategy, [one, two]), a


def test_a_jumbled_re_read_does_not_veto_a_name_another_document_reads_back() -> None:
    res, a = names(JUMBLE, NAME)
    assert ok(res, a, "company_name")
    res, a = names(JUMBLE, NAME, strategy=Strategy.S13)
    assert not ok(res, a, "company_name")  # the baseline keeps the veto


def test_the_veto_stays_when_nothing_reads_the_name_back_or_the_re_read_looks_like_a_misread() -> None:
    res, a = names(JUMBLE, None)
    assert not ok(res, a, "company_name")
    res, a = names(JUMBLE, JUMBLE)
    assert not ok(res, a, "company_name")
    res, a = names(MISREAD, NAME)  # a different version of the name: a contradiction, never lifted
    assert not ok(res, a, "company_name")
    res, a = names(JUMBLE, NAME, other_value="마바사상사")  # the other document carries another name
    assert not ok(res, a, "company_name")
