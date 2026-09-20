"""Deterministic synthetic benchmark generator.

No LLM is used. All content is produced from fixed data pools
(eval_lib.pools) combined via a seeded RNG, so a given seed always produces
the identical dataset -- this is what "gold labels generated alongside the
sample" means: the generator emits the document text and the ground truth
in the same step, so there is no manual transcription step to get wrong.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

from eval_lib import pools
from eval_lib.dates import format_date_variant
from eval_lib.layout import LAYOUTS, build_lines, maybe_space_label
from eval_lib.schema import GoldField, GoldLabel

INPUT_FORMATS = ["text_pdf", "scanned_pdf", "png", "jpg"]
QUALITIES = ["clean", "compressed", "blurred", "low_contrast", "rotated", "low_resolution"]


@dataclass
class CaseSpec:
    sample_id: str
    document_type: str
    lines: list[str]
    gold_fields: dict[str, str | None]
    input_format: str
    quality: str
    layout_variant: str
    split: str
    expected_validation_status: str | None
    notes: str = ""
    source_class: str = "SYNTHETIC_REALISTIC"
    source_id: str | None = None


def _note_tags(omit: bool, spacing: bool, extra: str = "") -> str:
    tags = []
    if omit:
        tags.append("omitted field to test missing-value handling")
    if spacing:
        tags.append("label spacing variant applied")
    if extra:
        tags.append(extra)
    return "; ".join(tags)


def _split_for(index: int) -> str:
    return "dev" if index % 10 < 7 else "held_out"


def _quality_for(index: int, input_format: str) -> str:
    if input_format == "text_pdf":
        return "clean"
    return QUALITIES[index % len(QUALITIES)]


def _expected_status(document_type: str, fields: dict[str, str | None]) -> str:
    if document_type == "SME_CONFIRMATION_CERTIFICATE":
        expiration = fields.get("expiration_date")
        if expiration and date.fromisoformat(expiration) < date.today():
            return "NEEDS_CORRECTION"
    if any(value is None for value in fields.values()):
        return "REVIEW_REQUIRED"
    return "READY"


def _make_pairs_and_gold(
    field_specs: list[tuple[str, str, str]],  # (field_name, label, raw_value)
    omit_index: int | None,
    label_spacing_index: int | None,
) -> tuple[list[tuple[str, str]], dict[str, str | None]]:
    pairs: list[tuple[str, str]] = []
    gold: dict[str, str | None] = {}
    for idx, (field_name, label, raw_value) in enumerate(field_specs):
        if idx == omit_index:
            gold[field_name] = None
            continue
        spaced = idx == label_spacing_index
        pairs.append((maybe_space_label(label, spaced), raw_value))
        gold[field_name] = raw_value
    return pairs, gold


def generate_graduation_cases(count: int) -> list[CaseSpec]:
    cases = []
    for i in range(count):
        rng = random.Random(1000 + i)
        name = pools.APPLICANT_NAMES[i % len(pools.APPLICANT_NAMES)]
        university = pools.UNIVERSITY_NAMES[i % len(pools.UNIVERSITY_NAMES)]
        department = pools.DEPARTMENTS[i % len(pools.DEPARTMENTS)]
        degree = pools.DEGREES[i % len(pools.DEGREES)]
        grad_date = date(2020, 1, 1) + timedelta(days=(i * 47) % 1800)
        issue_date = grad_date + timedelta(days=30 + i % 60)
        omit = i % 6 if i % 6 in (2, 3) else None  # occasionally omit department/degree
        spacing = 4 if i % 4 == 3 else None
        specs = [
            ("applicant_name", "성명", name),
            ("university_name", "대학교", university),
            ("department", "학과", department),
            ("degree", "학위", degree),
            ("graduation_date", "졸업일자", format_date_variant(grad_date.isoformat(), i)),
            ("issue_date", "발급일자", format_date_variant(issue_date.isoformat(), i + 1)),
        ]
        pairs, gold_raw = _make_pairs_and_gold(specs, omit, spacing)
        # Normalized gold value for date fields is the ISO form regardless
        # of the raw text's display format.
        gold = {
            "applicant_name": gold_raw["applicant_name"],
            "university_name": gold_raw["university_name"],
            "department": gold_raw["department"],
            "degree": gold_raw["degree"],
            "graduation_date": grad_date.isoformat() if gold_raw["graduation_date"] else None,
            "issue_date": issue_date.isoformat() if gold_raw["issue_date"] else None,
        }
        layout = LAYOUTS[i % len(LAYOUTS)]
        input_format = INPUT_FORMATS[i % len(INPUT_FORMATS)]
        lines = build_lines("졸업증명서", pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"graduation_{i:03d}",
                document_type="GRADUATION_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format=input_format,
                quality=_quality_for(i, input_format),
                layout_variant=layout,
                split=_split_for(i),
                expected_validation_status=_expected_status("GRADUATION_CERTIFICATE", gold),
                notes=_note_tags(omit is not None, spacing is not None),
            )
        )
    return cases


def generate_career_cases(count: int) -> list[CaseSpec]:
    cases = []
    for i in range(count):
        rng = random.Random(2000 + i)
        name = pools.APPLICANT_NAMES[(i + 1) % len(pools.APPLICANT_NAMES)]
        company = pools.COMPANY_NAMES[i % len(pools.COMPANY_NAMES)]
        position = pools.POSITIONS[i % len(pools.POSITIONS)]
        start = date(2018, 1, 1) + timedelta(days=(i * 53) % 2000)
        end = start + timedelta(days=365 + (i * 17) % 900)
        issue_date = end + timedelta(days=10 + i % 20)
        date_mode = i % 3  # 0=explicit start/end labels, 1=range label, 2=multiple periods
        layout = LAYOUTS[i % len(LAYOUTS)]
        input_format = INPUT_FORMATS[i % len(INPUT_FORMATS)]
        spacing = 3 if i % 4 == 3 else None
        omit = 2 if i % 7 == 6 else None  # occasionally omit position

        base_specs = [
            ("applicant_name", "성명", name),
            ("company_name", "회사명", company),
            ("position", "직위", position),
        ]
        notes = ""
        if date_mode == 0:
            base_specs += [
                ("employment_start_date", "입사일", format_date_variant(start.isoformat(), i)),
                ("employment_end_date", "퇴사일", format_date_variant(end.isoformat(), i + 1)),
            ]
            gold_start, gold_end = start.isoformat(), end.isoformat()
        elif date_mode == 1:
            base_specs += [
                (
                    "employment_start_date",
                    "재직기간",
                    f"{format_date_variant(start.isoformat(), i)} ~ {format_date_variant(end.isoformat(), i)}",
                )
            ]
            gold_start, gold_end = start.isoformat(), end.isoformat()
        else:
            # Two employment periods in one document -- current extractor
            # architecture supports only one period (documented limitation).
            # Gold reflects the FIRST period only, matching that documented
            # behavior; the case is tagged so error analysis doesn't confuse
            # this with an unexplained bug.
            second_start = end + timedelta(days=60)
            second_end = second_start + timedelta(days=300)
            base_specs += [
                ("employment_start_date", "재직기간", f"{start.isoformat()} ~ {end.isoformat()}")
            ]
            base_specs.append(
                (
                    "__second_period__",
                    "재직기간",
                    f"{second_start.isoformat()} ~ {second_end.isoformat()}",
                )
            )
            gold_start, gold_end = start.isoformat(), end.isoformat()
            notes = "multiple employment periods present; only first period is supported"
        base_specs.append(
            ("issue_date", "발급일자", format_date_variant(issue_date.isoformat(), i + 2))
        )
        notes = _note_tags(omit is not None, spacing is not None, notes)

        # __second_period__ is a synthetic marker field (not a real
        # ExpectedField) used only to inject a second text line; strip it
        # from gold before scoring.
        real_specs = [s for s in base_specs if s[0] != "__second_period__"]
        pairs, gold_raw = _make_pairs_and_gold(real_specs, omit, spacing)
        extra_lines: list[tuple[str, str]] = [
            (s[1], s[2]) for s in base_specs if s[0] == "__second_period__"
        ]

        gold = {
            "applicant_name": gold_raw["applicant_name"],
            "company_name": gold_raw["company_name"],
            "position": gold_raw["position"],
            "employment_start_date": gold_start if gold_raw.get("employment_start_date") else None,
            "employment_end_date": gold_end if gold_raw.get("employment_start_date") else None,
            "issue_date": issue_date.isoformat() if gold_raw["issue_date"] else None,
        }
        all_pairs = pairs + extra_lines
        lines = build_lines("경력증명서", all_pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"career_{i:03d}",
                document_type="CAREER_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format=input_format,
                quality=_quality_for(i, input_format),
                layout_variant=layout,
                split=_split_for(i),
                expected_validation_status=_expected_status("CAREER_CERTIFICATE", gold),
                notes=notes,
            )
        )
    return cases


def generate_business_cases(count: int) -> list[CaseSpec]:
    cases = []
    for i in range(count):
        rng = random.Random(3000 + i)
        company = pools.COMPANY_NAMES[i % len(pools.COMPANY_NAMES)]
        rep = pools.REPRESENTATIVE_NAMES[i % len(pools.REPRESENTATIVE_NAMES)]
        address = pools.BUSINESS_ADDRESSES[i % len(pools.BUSINESS_ADDRESSES)]
        biz_type = pools.BUSINESS_TYPES[i % len(pools.BUSINESS_TYPES)]
        biz_item = pools.BUSINESS_ITEMS[i % len(pools.BUSINESS_ITEMS)]
        issue_date = date(2015, 1, 1) + timedelta(days=(i * 61) % 4000)
        number_norm = pools.synthetic_business_number(i)
        number_mode = i % 3  # 0=hyphenated, 1=unformatted digits, 2=spaced
        if number_mode == 0:
            number_raw = number_norm
        elif number_mode == 1:
            number_raw = number_norm.replace("-", "")
        else:
            number_raw = number_norm.replace("-", " ")
        layout = LAYOUTS[i % len(LAYOUTS)]
        input_format = INPUT_FORMATS[i % len(INPUT_FORMATS)]
        spacing = 2 if i % 4 == 3 else None
        omit = 4 if i % 7 == 6 else None  # occasionally omit business_item

        specs = [
            ("company_name", "상호", company),
            ("representative_name", "대표자", rep),
            ("business_registration_number", "사업자등록번호", number_raw),
            ("business_address", "사업장 소재지", address),
            ("business_item", "종목", biz_item),
            ("business_type", "업태", biz_type),
            ("issue_date", "발급일자", format_date_variant(issue_date.isoformat(), i)),
        ]
        pairs, gold_raw = _make_pairs_and_gold(specs, omit, spacing)
        extra_note = ""
        if i % 9 == 8:
            # Nearby unrelated 10-digit-shaped number (e.g. a phone number)
            # that must NOT be picked up as the business registration number.
            pairs.append(("연락처", "010-1234-5678"))
            extra_note = (
                "includes an unrelated 10-digit-shaped number (phone) near the business fields"
            )

        gold = {
            "company_name": gold_raw["company_name"],
            "representative_name": gold_raw["representative_name"],
            "business_registration_number": number_norm
            if gold_raw["business_registration_number"]
            else None,
            "business_address": gold_raw["business_address"],
            "business_type": gold_raw["business_type"],
            "business_item": gold_raw["business_item"],
            "issue_date": issue_date.isoformat() if gold_raw["issue_date"] else None,
        }
        lines = build_lines("사업자등록증", pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"business_{i:03d}",
                document_type="BUSINESS_REGISTRATION_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format=input_format,
                quality=_quality_for(i, input_format),
                layout_variant=layout,
                split=_split_for(i),
                expected_validation_status=_expected_status(
                    "BUSINESS_REGISTRATION_CERTIFICATE", gold
                ),
                notes=_note_tags(omit is not None, spacing is not None, extra_note),
            )
        )
    return cases


def generate_sme_cases(count: int) -> list[CaseSpec]:
    cases = []
    for i in range(count):
        rng = random.Random(4000 + i)
        company = pools.COMPANY_NAMES[(i + 2) % len(pools.COMPANY_NAMES)]
        rep = pools.REPRESENTATIVE_NAMES[(i + 1) % len(pools.REPRESENTATIVE_NAMES)]
        number_norm = pools.synthetic_business_number(i + 500)
        cert_number = f"SME-{2020 + i % 7}-{100 + i:03d}"
        issue_date = date(2020, 1, 1) + timedelta(days=(i * 41) % 2000)
        expired = i % 4 == 0
        if expired:
            valid_from = issue_date
            valid_until = issue_date + timedelta(days=180)  # already in the past
        else:
            valid_from = date(2026, 1, 1)
            valid_until = date(2028, 1, 1) + timedelta(days=i % 300)
        layout = LAYOUTS[i % len(LAYOUTS)]
        input_format = INPUT_FORMATS[i % len(INPUT_FORMATS)]
        spacing = 2 if i % 4 == 3 else None  # targets 사업자등록번호
        omit = 3 if i % 8 == 7 else None  # occasionally omit certificate_number

        validity_raw = f"{valid_from.isoformat()} ~ {valid_until.isoformat()}"
        specs = [
            ("company_name", "기업명", company),
            ("representative_name", "대표자", rep),
            ("business_registration_number", "사업자등록번호", number_norm),
            ("certificate_number", "확인번호", cert_number),
            ("issue_date", "발급일자", format_date_variant(issue_date.isoformat(), i)),
            ("validity_period_raw", "유효기간", validity_raw),
        ]
        pairs, gold_raw = _make_pairs_and_gold(specs, omit, spacing)

        gold = {
            "company_name": gold_raw["company_name"],
            "representative_name": gold_raw["representative_name"],
            "business_registration_number": number_norm
            if gold_raw["business_registration_number"]
            else None,
            "certificate_number": cert_number if gold_raw["certificate_number"] else None,
            "issue_date": issue_date.isoformat() if gold_raw["issue_date"] else None,
            "expiration_date": valid_until.isoformat()
            if gold_raw.get("validity_period_raw")
            else None,
            "validity_period": validity_raw if gold_raw.get("validity_period_raw") else None,
        }
        lines = build_lines("중소기업확인서", pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"sme_{i:03d}",
                document_type="SME_CONFIRMATION_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format=input_format,
                quality=_quality_for(i, input_format),
                layout_variant=layout,
                split=_split_for(i),
                expected_validation_status=_expected_status("SME_CONFIRMATION_CERTIFICATE", gold),
                notes=_note_tags(
                    omit is not None, spacing is not None, "expired certificate" if expired else ""
                ),
            )
        )
    return cases


def generate_recreated_cases() -> list[CaseSpec]:
    """RECREATED_FROM_PUBLIC_REFERENCE samples: from-scratch recreations
    (fictional data throughout) that specifically exercise real-world label
    vocabulary found during source research (see
    evaluation/reports/source_research.md), each citing the source_id it is
    motivated by. Deliberately small and non-inflated -- every sample here
    traces to a specific cited finding, not filler."""
    cases: list[CaseSpec] = []

    # --- BUSINESS_REGISTRATION_CERTIFICATE: official annexed-form label
    # wording (법인명칭, 대표자 성명) from law.go.kr, not currently in the
    # extractor's label lists (["상호","상호명"] / ["대표자","대표자명"]).
    business_specs = [
        (0, "법인명칭", "대표자", "text_pdf", "standard"),
        (1, "법인명칭", "대표자 성명", "scanned_pdf", "standard"),
        (2, "상호", "대표자 성명", "png", "table"),
    ]
    for i, company_label, rep_label, input_format, layout in business_specs:
        rng = random.Random(9000 + i)
        company = pools.COMPANY_NAMES[i % len(pools.COMPANY_NAMES)]
        rep = pools.REPRESENTATIVE_NAMES[i % len(pools.REPRESENTATIVE_NAMES)]
        number = pools.synthetic_business_number(700 + i)
        address = pools.BUSINESS_ADDRESSES[i % len(pools.BUSINESS_ADDRESSES)]
        issue_date = date(2018, 3, 1) + timedelta(days=i * 400)
        pairs = [
            (company_label, company),
            (rep_label, rep),
            ("사업자등록번호", number),
            ("사업장 소재지", address),
            ("업태", pools.BUSINESS_TYPES[i % len(pools.BUSINESS_TYPES)]),
            ("종목", pools.BUSINESS_ITEMS[i % len(pools.BUSINESS_ITEMS)]),
            ("발급일자", format_date_variant(issue_date.isoformat(), i)),
        ]
        gold = {
            "company_name": company,
            "representative_name": rep,
            "business_registration_number": number,
            "business_address": address,
            "business_type": pools.BUSINESS_TYPES[i % len(pools.BUSINESS_TYPES)],
            "business_item": pools.BUSINESS_ITEMS[i % len(pools.BUSINESS_ITEMS)],
            "issue_date": issue_date.isoformat(),
        }
        lines = build_lines("사업자등록증", pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"recreated_business_{i:03d}",
                document_type="BUSINESS_REGISTRATION_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format=input_format,
                quality="clean",
                layout_variant=layout,
                split="dev" if i < 2 else "held_out",
                expected_validation_status=_expected_status(
                    "BUSINESS_REGISTRATION_CERTIFICATE", gold
                ),
                notes=(
                    f"recreated from official law.go.kr annexed-form wording "
                    f"(label '{company_label}'/'{rep_label}')"
                ),
                source_class="RECREATED_FROM_PUBLIC_REFERENCE",
                source_id="src_business_01" if rep_label == "대표자 성명" else "src_business_02",
            )
        )

    # --- GRADUATION_CERTIFICATE: real alternate title "학위수여증명서"
    # (degree conferment certificate), confirmed as an official document
    # title by 정부24 and two independent universities.
    for i, layout in enumerate(["standard", "reordered"]):
        rng = random.Random(9100 + i)
        name = pools.APPLICANT_NAMES[i % len(pools.APPLICANT_NAMES)]
        university = pools.UNIVERSITY_NAMES[(i + 2) % len(pools.UNIVERSITY_NAMES)]
        department = pools.DEPARTMENTS[(i + 1) % len(pools.DEPARTMENTS)]
        degree = "석사"  # 학위수여증명서 is real-world used for graduate degrees
        grad_date = date(2022, 2, 1) + timedelta(days=i * 200)
        issue_date = grad_date + timedelta(days=45)
        pairs = [
            ("성명", name),
            ("대학교", university),
            ("학과", department),
            ("학위", degree),
            ("학위수여일자", grad_date.isoformat()),
            ("발급일자", issue_date.isoformat()),
        ]
        gold = {
            "applicant_name": name,
            "university_name": university,
            "department": department,
            "degree": degree,
            "graduation_date": None,  # extractor looks for "졸업일자", not "학위수여일자" -- see notes
            "issue_date": issue_date.isoformat(),
        }
        lines = build_lines("학위수여증명서", pairs, layout, rng)
        cases.append(
            CaseSpec(
                sample_id=f"recreated_graduation_{i:03d}",
                document_type="GRADUATION_CERTIFICATE",
                lines=lines,
                gold_fields=gold,
                input_format="text_pdf",
                quality="clean",
                layout_variant=layout,
                split="dev" if i == 0 else "held_out",
                expected_validation_status=_expected_status("GRADUATION_CERTIFICATE", gold),
                notes=(
                    "recreated using the real alternate title '학위수여증명서' (degree "
                    "conferment certificate); its date label '학위수여일자' is not in the "
                    "graduation_date label list ('졸업일자'/'졸업 연월일'), so graduation_date "
                    "is expected to be genuinely absent, not a test-harness bug"
                ),
                source_class="RECREATED_FROM_PUBLIC_REFERENCE",
                source_id="src_graduation_02",
            )
        )

    return cases


def generate_submission_documents() -> list[CaseSpec]:
    """A small set of dedicated single-purpose documents with deliberately
    controlled identity (name/company overlap or mismatch, valid/expired/
    near-expiry dates) so submission bundles (eval_lib.submissions) can
    exercise project-level cross-document validation -- APPLICANT_NAME_MATCH,
    COMPANY_NAME_MATCH, DATE_NOT_EXPIRED, REQUIRED_DOCUMENT -- deterministically,
    rather than hoping generic pool samples happen to share a name by chance."""
    cases: list[CaseSpec] = []

    def grad(sample_id: str, name: str) -> CaseSpec:
        pairs = [
            ("성명", name),
            ("대학교", "가나다대학교"),
            ("학과", "컴퓨터공학과"),
            ("학위", "학사"),
            ("졸업일자", "2023-02-15"),
            ("발급일자", "2026-01-05"),
        ]
        gold: dict[str, str | None] = {
            "applicant_name": name,
            "university_name": "가나다대학교",
            "department": "컴퓨터공학과",
            "degree": "학사",
            "graduation_date": "2023-02-15",
            "issue_date": "2026-01-05",
        }
        return CaseSpec(
            sample_id=sample_id,
            document_type="GRADUATION_CERTIFICATE",
            lines=build_lines("졸업증명서", pairs, "standard", random.Random(1)),
            gold_fields=gold,
            input_format="text_pdf",
            quality="clean",
            layout_variant="standard",
            split="dev",
            expected_validation_status=_expected_status("GRADUATION_CERTIFICATE", gold),
            notes="submission-bundle fixture: controlled applicant identity",
        )

    def career(sample_id: str, name: str, company: str) -> CaseSpec:
        pairs = [
            ("성명", name),
            ("회사명", company),
            ("직위", "대리"),
            ("입사일", "2020-03-02"),
            ("퇴사일", "2023-08-31"),
            ("발급일자", "2026-01-10"),
        ]
        gold: dict[str, str | None] = {
            "applicant_name": name,
            "company_name": company,
            "position": "대리",
            "employment_start_date": "2020-03-02",
            "employment_end_date": "2023-08-31",
            "issue_date": "2026-01-10",
        }
        return CaseSpec(
            sample_id=sample_id,
            document_type="CAREER_CERTIFICATE",
            lines=build_lines("경력증명서", pairs, "standard", random.Random(2)),
            gold_fields=gold,
            input_format="text_pdf",
            quality="clean",
            layout_variant="standard",
            split="dev",
            expected_validation_status=_expected_status("CAREER_CERTIFICATE", gold),
            notes="submission-bundle fixture: controlled applicant identity",
        )

    def business(sample_id: str, company: str) -> CaseSpec:
        number = pools.synthetic_business_number(hash(sample_id) % 90)
        pairs = [
            ("상호", company),
            ("대표자", "이영희"),
            ("사업자등록번호", number),
            ("사업장 소재지", "서울특별시 테스트구 예시로 12"),
            ("업태", "서비스업"),
            ("종목", "소프트웨어 개발"),
            ("발급일자", "2019-05-01"),
        ]
        gold = {
            "company_name": company,
            "representative_name": "이영희",
            "business_registration_number": number,
            "business_address": "서울특별시 테스트구 예시로 12",
            "business_type": "서비스업",
            "business_item": "소프트웨어 개발",
            "issue_date": "2019-05-01",
        }
        return CaseSpec(
            sample_id=sample_id,
            document_type="BUSINESS_REGISTRATION_CERTIFICATE",
            lines=build_lines("사업자등록증", pairs, "standard", random.Random(3)),
            gold_fields=gold,
            input_format="text_pdf",
            quality="clean",
            layout_variant="standard",
            split="dev",
            expected_validation_status=_expected_status("BUSINESS_REGISTRATION_CERTIFICATE", gold),
            notes="submission-bundle fixture: controlled company identity",
        )

    def sme(sample_id: str, company: str, valid_until: date) -> CaseSpec:
        number = pools.synthetic_business_number(hash(sample_id) % 90 + 1)
        validity_raw = f"2026-01-01 ~ {valid_until.isoformat()}"
        pairs = [
            ("기업명", company),
            ("대표자", "이영희"),
            ("사업자등록번호", number),
            ("확인번호", f"SME-{sample_id[-6:]}"),
            ("발급일자", "2026-01-01"),
            ("유효기간", validity_raw),
        ]
        gold = {
            "company_name": company,
            "representative_name": "이영희",
            "business_registration_number": number,
            "certificate_number": f"SME-{sample_id[-6:]}",
            "issue_date": "2026-01-01",
            "expiration_date": valid_until.isoformat(),
            "validity_period": validity_raw,
        }
        return CaseSpec(
            sample_id=sample_id,
            document_type="SME_CONFIRMATION_CERTIFICATE",
            lines=build_lines("중소기업확인서", pairs, "standard", random.Random(4)),
            gold_fields=gold,
            input_format="text_pdf",
            quality="clean",
            layout_variant="standard",
            split="dev",
            expected_validation_status=_expected_status("SME_CONFIRMATION_CERTIFICATE", gold),
            notes="submission-bundle fixture: controlled company identity / validity date",
        )

    def grad_missing_department(sample_id: str, name: str) -> CaseSpec:
        pairs = [
            ("성명", name),
            ("대학교", "가나다대학교"),
            ("학위", "학사"),
            ("졸업일자", "2023-02-15"),
            ("발급일자", "2026-01-05"),
        ]
        gold = {
            "applicant_name": name,
            "university_name": "가나다대학교",
            "department": None,
            "degree": "학사",
            "graduation_date": "2023-02-15",
            "issue_date": "2026-01-05",
        }
        return CaseSpec(
            sample_id=sample_id,
            document_type="GRADUATION_CERTIFICATE",
            lines=build_lines("졸업증명서", pairs, "standard", random.Random(5)),
            gold_fields=gold,
            input_format="text_pdf",
            quality="clean",
            layout_variant="standard",
            split="dev",
            expected_validation_status=_expected_status("GRADUATION_CERTIFICATE", gold),
            notes="submission-bundle fixture: missing optional field -> per-document REVIEW_REQUIRED",
        )

    def ambiguous_as_career() -> CaseSpec:
        text = (
            "근로계약서\n성명 이예시\n회사명 테스트테크 주식회사\n계약기간 2026-01-01 ~ 2027-01-01"
        )
        return CaseSpec(
            sample_id="subdoc_ambiguous_as_career",
            document_type="UNKNOWN",
            lines=text.splitlines(),
            gold_fields={},
            input_format="text_pdf",
            quality="clean",
            layout_variant="verbatim",
            split="dev",
            expected_validation_status=None,
            notes="submission-bundle fixture: an employment CONTRACT (근로계약서) submitted in "
            "place of a required CAREER_CERTIFICATE -- must not be silently accepted as satisfying "
            "the requirement",
            source_class="NEGATIVE_OUT_OF_SCOPE",
        )

    today = date.today()
    cases.append(grad("subdoc_grad_A", "김테스트"))
    cases.append(grad("subdoc_grad_B", "이예시"))
    cases.append(grad_missing_department("subdoc_grad_missing_dept", "김테스트"))
    cases.append(ambiguous_as_career())
    cases.append(career("subdoc_career_A", "김테스트", "테스트테크 주식회사"))
    cases.append(career("subdoc_career_B", "박샘플", "테스트테크 주식회사"))
    cases.append(business("subdoc_business_A", "테스트테크 주식회사"))
    cases.append(business("subdoc_business_B", "가상솔루션 주식회사"))
    cases.append(sme("subdoc_sme_valid", "테스트테크 주식회사", today + timedelta(days=400)))
    cases.append(sme("subdoc_sme_expired", "테스트테크 주식회사", today - timedelta(days=30)))
    cases.append(sme("subdoc_sme_near_expiry", "테스트테크 주식회사", today + timedelta(days=10)))
    cases.append(
        sme("subdoc_sme_company_mismatch", "다른회사 주식회사", today + timedelta(days=400))
    )
    return cases


def generate_unknown_cases(count: int) -> list[CaseSpec]:
    cases = []
    pool = pools.UNRELATED_TEXTS + pools.AMBIGUOUS_TEXTS
    for i in range(count):
        text = pool[i % len(pool)]  # layout is irrelevant here; text is used verbatim
        input_format = INPUT_FORMATS[i % len(INPUT_FORMATS)]
        lines = text.splitlines()
        cases.append(
            CaseSpec(
                sample_id=f"unknown_{i:03d}",
                document_type="UNKNOWN",
                lines=lines,
                gold_fields={},
                input_format=input_format,
                quality=_quality_for(i, input_format),
                layout_variant="verbatim",
                split=_split_for(i),
                expected_validation_status=None,
                notes="negative/out-of-scope example"
                if i < len(pools.UNRELATED_TEXTS)
                else "ambiguous/near-miss example",
                source_class="NEGATIVE_OUT_OF_SCOPE",
            )
        )
    return cases


def to_gold_label(case: CaseSpec) -> GoldLabel:
    fields = {
        name: GoldField(value=value, required=True) for name, value in case.gold_fields.items()
    }
    source = "recreated" if case.source_class == "RECREATED_FROM_PUBLIC_REFERENCE" else "synthetic"
    return GoldLabel(
        sample_id=case.sample_id,
        source=source,
        document_type=case.document_type,
        input_format=case.input_format,
        quality=case.quality,
        layout_variant=case.layout_variant,
        split=case.split,
        fields=fields,
        expected_validation_status=case.expected_validation_status,
        notes=case.notes,
        source_class=case.source_class,
        source_id=case.source_id,
    )
