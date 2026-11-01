"""Shared company-name agreement used by the acceptance policy and the submission rules (invented names)."""

from app.document_intelligence.company_names import company_key, company_names_agree

NUMBER = "1234567891"  # valid check digit
OTHER = "2148655302"  # valid check digit


def agree(left: str, right: str, left_number: str | None = NUMBER, right_number: str | None = NUMBER) -> bool:
    return company_names_agree(company_key(left), company_key(right), left_number, right_number)


def test_legal_form_spacing_and_latin_parentheses_do_not_matter() -> None:
    assert agree("(주) 가나다상사 (Kanada Trading)", "주식회사가나다상사", None, None)


def test_a_different_company_is_a_mismatch_even_with_the_same_number() -> None:
    assert not agree("(주)가나다상사", "(주)라마바물산")


def test_a_shorter_name_needs_the_same_valid_business_number() -> None:
    assert agree("(주)가나다상사(Kanada)", "(주)가나다상")
    assert not agree("(주)가나다상사", "(주)가나다상", NUMBER, OTHER)
    assert not agree("(주)가나다상사", "(주)가나다상", NUMBER, None)


def test_a_number_that_fails_the_check_digit_does_not_anchor() -> None:
    bad = "1234567890"
    assert not agree("(주)가나다상사", "(주)가나다상", bad, bad)


def test_a_very_short_name_is_not_a_prefix_match() -> None:
    assert not agree("(주)가나다상사", "(주)가나")
