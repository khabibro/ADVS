from app.document_intelligence.extraction.transcript import TranscriptExtractor

HEADER = "성 적 증 명 서\n생년월일\n학성\n번\n명\n:{id}\n:가나다\n입학일자:2020년3월2일\n구분\n이 수 과 목\n학점성적"


def student_id(text: str) -> str | None:
    values = {v.field_name: v for v in TranscriptExtractor().extract(text)}
    return values["student_id"].normalized_value


def test_split_label_number_is_read() -> None:
    assert student_id(HEADER.format(id="2020123456")) == "2020123456"


def test_labelled_number_is_unchanged() -> None:
    assert student_id("학번 : 2019000111\n성명 : 가나다") == "2019000111"


def test_two_numbers_stay_missing() -> None:
    text = HEADER.format(id="2020123456").replace(":가나다", ":2021654321")
    assert student_id(text) is None


def test_date_shaped_or_unlabelled_numbers_stay_missing() -> None:
    assert student_id(HEADER.format(id="20200302")) is None
    assert student_id("성 적 증 명 서\n:2020123456\n구분") is None
    assert student_id("성 적 증 명 서\n문서\n서\n류\n:3020123456\n구분") is None


def test_number_after_table_header_is_ignored() -> None:
    assert student_id("학성\n번\n구분\n:2020123456") is None


def birth(text: str, extractor=None) -> str | None:
    values = {v.field_name: v for v in (extractor or TranscriptExtractor()).extract(text)}
    return values["birth_date"].normalized_value


def test_birth_date_beside_label_and_separated_label() -> None:
    assert birth("생년월일 : 2002년 5월 17일\n성명 : 가나다") == "2002-05-17"
    separated = "성 적 증 명 서\n생년월일\n소\n속\n:\n가 대학 나 학부\n2002년 5월 17일\n입학일자:2020년3월2일\n구분"
    assert birth(separated) == "2002-05-17"


def test_birth_date_ambiguous_or_implausible_stays_missing() -> None:
    two = "생년월일\n소속\n2002년 5월 17일\n2001년 1월 2일\n구분"
    assert birth(two) is None
    assert birth("생년월일\n소속\n2024년 5월 17일\n구분") is None  # a child, not a student
    assert birth("성 적 증 명 서\n입학일자:2002년 5월 17일\n구분") is None  # no label


def name(text: str) -> str | None:
    values = {v.field_name: v for v in TranscriptExtractor().extract(text)}
    return values["student_name"].normalized_value


def test_split_label_name_is_read() -> None:
    text = "성 적 증 명 서\n생년월일\n학성\n번\n명\n:류하늘\n:2020123456\n입학일자:2020년3월2일\n구분\n이 수 과 목"
    assert name(text) == "류하늘"


def test_split_label_name_refuses_ambiguous_or_unlabelled_values() -> None:
    assert name("학성\n번\n명\n:류하늘\n:박다라\n구분") is None  # two candidates
    assert name("성 적 증 명 서\n:류하늘\n구분") is None  # no label fragment above
    assert name("학성\n번\n명\n:자연과학대학\n구분") is None  # an institution word is not a name
    assert name("학성\n번\n구분\n명\n:류하늘") is None  # after the table header
    assert name("성명 : 류하늘\n구분") == "류하늘"  # the labelled form is unchanged


def test_split_label_name_longer_names_and_the_last_fragment_sharing_its_box() -> None:
    assert name("학성\n번\n명:라마드리안마리아\n:2020123456\n구분") == "라마드리안마리아"
    assert name("학성\n번\n명\n:라마드리안마리아\n구분") == "라마드리안마리아"
