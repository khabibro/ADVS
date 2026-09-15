"""Fictional Korean data pools for synthetic document generation.

All names, organizations, and identifiers here are deliberately fictional
and formatted so they cannot be mistaken for a real assigned business
registration number (see BUSINESS_NUMBER_PREFIX). Do not add real personal
or business data to this file.
"""

APPLICANT_NAMES = ["김테스트", "이예시", "박샘플", "최가상", "정더미", "한모형", "오테스트", "서예시"]

UNIVERSITY_NAMES = ["가나다대학교", "마바사대학교", "아자차대학교", "카파타대학교", "하거너대학교"]
DEPARTMENTS = ["컴퓨터공학과", "전자공학과", "경영학과", "산업공학과", "정보통신학과"]
DEGREES = ["학사", "석사", "박사"]

COMPANY_NAMES = [
    "테스트테크 주식회사",
    "예시산업 주식회사",
    "가상소프트 주식회사",
    "모형전자 주식회사",
    "더미시스템 주식회사",
]
POSITIONS = ["대리", "과장", "사원", "팀장", "차장"]
RESPONSIBILITIES = ["백엔드 개발", "회계 관리", "고객 상담", "생산 관리 및 품질 검사"]

REPRESENTATIVE_NAMES = ["이영희", "박대표", "최사장", "정법인", "한사업"]
BUSINESS_ADDRESSES = [
    "서울특별시 테스트구 예시로 12",
    "경기도 가상시 모형대로 34",
    "부산광역시 더미구 샘플길 56",
    "인천광역시 견본구 표본로 78",
]
BUSINESS_TYPES = ["서비스업", "제조업", "도소매업", "정보통신업"]
BUSINESS_ITEMS = ["소프트웨어 개발", "전자부품 제조", "무역업", "경영 컨설팅"]

SME_CATEGORIES = ["소기업", "중기업", "소상공인"]

# Deliberately outside any real assigned range; format-valid only (the
# codebase does not implement a real checksum validator for this number).
BUSINESS_NUMBER_PREFIX = 900


def synthetic_business_number(index: int) -> str:
    mid = 80 + (index % 20)
    tail = 10000 + (index * 37) % 90000
    return f"{BUSINESS_NUMBER_PREFIX + (index % 90):03d}-{mid:02d}-{tail:05d}"


UNRELATED_TEXTS = [
    "회의록\n일시 2026-01-01\n참석자 홍길동, 김철수\n안건 분기 실적 논의",
    "청구서\n청구번호 INV-2026-0012\n금액 1,200,000원\n결제기한 2026-02-01",
    "안내문\n본 안내문은 정보 제공 목적으로 작성되었습니다.\n문의처 02-000-0000",
    "여행 일정표\n1일차 서울 도착\n2일차 부산 이동\n3일차 귀국",
]

AMBIGUOUS_TEXTS = [
    # Enrollment confirmation -- university-adjacent but not a graduation
    # certificate; classifier must not force GRADUATION_CERTIFICATE.
    # Real, common document type (see evaluation/sources/source_registry.json
    # src_graduation_03/04/05).
    "재학증명서\n성명 김테스트\n대학교 가나다대학교\n학과 컴퓨터공학과\n재학 여부 재학중",
    # Employment offer -- career-adjacent but not a career certificate.
    "근로계약서\n성명 이예시\n회사명 테스트테크 주식회사\n계약기간 2026-01-01 ~ 2027-01-01",
    # Sparse/incomplete business-like text with no strong title signal.
    "상호 테스트테크\n주소 서울시",
    # Conflicting signals: both graduation and career titles present.
    "졸업증명서 겸 경력증명서\n성명 박샘플\n대학교 가나다대학교\n회사명 예시산업 주식회사",
    # Transcript -- a real, distinct university document (src_graduation_03),
    # shares "대학교"/"학과" vocabulary with GRADUATION_CERTIFICATE but is a
    # grades record, not a graduation certificate.
    "성적증명서\n성명 최가상\n대학교 마바사대학교\n학과 전자공학과\n학년 4학년\n평점 3.8/4.5",
    # Current-employment confirmation -- a real, distinct document from a
    # career certificate (src_career_01/02): proves present employment, not
    # past work history.
    "재직증명서\n성명 정더미\n회사명 가상소프트 주식회사\n직위 과장\n재직 여부 재직중",
    # A related-but-distinct official business document (src_business_04):
    # a registration-status confirmation, not the registration certificate
    # itself.
    "사업자등록증명원\n상호 더미시스템\n사업자등록번호 901-84-15037\n증명 목적 제출용",
    # Generic confirmation letter -- shares "확인서" with SME_CONFIRMATION
    # but has no business/company substance at all.
    "확인서\n상기 내용은 사실과 다름없음을 확인합니다.\n확인자 서예시",
]
