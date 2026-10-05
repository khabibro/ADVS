#!/usr/bin/env python3
"""Generate the ADVS test-variant document set (fictional data only).

Usage:
    python3 gen_test_variants.py --out ./ADVS_test_variants --submission-date 2026-10-05

Requirements: Python 3.10+, Pillow, numpy, opencv-python, python-docx,
wkhtmltopdf and poppler-utils (pdftoppm, pdftotext) on PATH, and the
Noto Sans/Serif CJK KR fonts installed.

All dates are computed relative to --submission-date, so the set can be
regenerated whenever validity windows would otherwise go stale. (ADVS
currently compares validity against the server's date.today(), not the
submission date — see audit finding on validity reference — so regenerate
with today's date before a test run.)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

import layouts as L

# ----------------------------------------------------------------- helpers


def d_sp(d: dt.date) -> str:
    return f"{d.year} 년 {d.month:02d} 월 {d.day:02d} 일"


def d_kr(d: dt.date) -> str:
    return f"{d.year}년 {d.month:02d}월 {d.day:02d}일"


def d_kr_nz(d: dt.date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일"


def brn_check_digit(d9: str) -> int:
    """Korean business registration number check digit (public algorithm)."""
    w = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    s = sum(int(a) * b for a, b in zip(d9, w))
    s += (int(d9[8]) * 5) // 10
    return (10 - s % 10) % 10


def make_brn(prefix9: str, valid: bool = True) -> str:
    c = brn_check_digit(prefix9)
    if not valid:
        c = (c + 1) % 10
    n = prefix9 + str(c)
    return f"{n[:3]}-{n[3:5]}-{n[5:]}"


def brn_is_valid(brn: str) -> bool:
    digits = brn.replace("-", "")
    return brn_check_digit(digits[:9]) == int(digits[9])


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def known(value, printed=None):
    return {"state": "KNOWN_VALUE", "value": value, "printed": printed if printed is not None else value}


def absent(note=""):
    out = {"state": "VERIFIED_ABSENT", "value": None}
    if note:
        out["note"] = note
    return out


# ----------------------------------------------------------------- entities

COMPANY_A = {
    "core": "테스트상사",
    "full": "주식회사 테스트상사",
    "representative": "박가상",
    "corp_reg_no": "110111-9234567",
    "address": "서울특별시 가상구 테스트로 123, 4층 (샘플동)",
    "brn": make_brn("220811234"),
    "mgmt_no": "2201234567-0",
}
COMPANY_B = {
    "core": "가나다솔루션",
    "full": "주식회사 가나다솔루션",
    "representative": "최샘플",
    "corp_reg_no": "110111-9876543",
    "address": "경기도 가상시 샘플대로 45, 2층",
    "brn": make_brn("105874455"),
    "mgmt_no": "1059876543-0",
}
BRN_A_CONFLICT = make_brn("220819876")
BRN_A_INVALID = make_brn("220811234", valid=False)

STUDENT = {
    "name": "김테스트",
    "birth": dt.date(2003, 5, 15),
    "university": "한국가상대학교",
    "college": "공과대학",
    "department": "데이터공학과",
    "major": "데이터사이언스전공",
    "student_id": "2023123456",
    "admission": dt.date(2023, 3, 2),
}

ALT = {"student_name": "이샘플", "college": "인문대학", "department": "국어국문학과",
       "company_near_miss": None}
PROFILE = {"name": "dev", "holdout": False}

COURSES_GENERAL = ["대학글쓰기", "영어회화1", "글로벌문화이해", "철학의이해", "경제학원론", "심리학개론", "진로탐색", "체육(수영)", "영어회화2", "창의적사고", "한국사의이해", "과학기술과사회", "법과생활", "미술의이해"]
COURSES_MAJOR = ["프로그래밍기초", "이산수학", "자료구조", "컴퓨터구조", "운영체제", "데이터베이스", "알고리즘", "확률및통계", "선형대수", "소프트웨어공학", "컴퓨터네트워크", "인공지능개론", "기계학습", "데이터시각화", "웹프로그래밍", "데이터마이닝", "빅데이터처리", "클라우드컴퓨팅", "정보보호개론", "캡스톤디자인1", "컴파일러", "분산시스템", "자연어처리", "컴퓨터비전", "모바일프로그래밍", "데이터공학세미나", "수치해석", "최적화이론"]

SCALES = {
    "4.5": {
        "points": [("A+", 4.5), ("A0", 4.0), ("B+", 3.5), ("B0", 3.0), ("C+", 2.5), ("C0", 2.0), ("D+", 1.5), ("D0", 1.0), ("F", 0.0)],
        "legend": "A+=4.5(95-100), A0=4.0(90-94), B+=3.5(85-89), B0=3.0(80-84), C+=2.5(75-79), C0=2.0(70-74), D+=1.5(65-69), D0=1.0(60-64), F=0.0(0), S=이수, U=미이수",
    },
    "4.3": {
        "points": [("A+", 4.3), ("A0", 4.0), ("A-", 3.7), ("B+", 3.3), ("B0", 3.0), ("B-", 2.7), ("C+", 2.3), ("C0", 2.0), ("C-", 1.7), ("D+", 1.3), ("D0", 1.0), ("D-", 0.7), ("F", 0.0)],
        "legend": "A+=4.3(97-100), A0=4.0(94-96), A-=3.7(90-93), B+=3.3(87-89), B0=3.0(84-86), B-=2.7(80-83), C+=2.3(77-79), C0=2.0(74-76), C-=1.7(70-73), D+=1.3(67-69), D0=1.0(64-66), D-=0.7(60-63), F=0.0(0)",
    },
}


def pct_of(gpa: float, scale: float) -> str:
    return f"{60 + gpa / scale * 37.5:.2f}"


def make_transcript(target: float, scale_key: str, seed: int) -> dict:
    """Build a course list whose credit-weighted GPA rounds exactly to target."""
    rng = random.Random(seed)
    pts = SCALES[scale_key]["points"][:-1]  # never F in the fixture
    scale = float(scale_key)
    term_labels = ["2023학년도 1학기", "2023학년도 2학기", "2024학년도 1학기", "2024학년도 2학기", "2025학년도 1학기", "2025학년도 2학기"]
    gen = COURSES_GENERAL[:]
    maj = COURSES_MAJOR[:]
    rng.shuffle(gen)
    rng.shuffle(maj)
    courses = []
    for ti, label in enumerate(term_labels):
        for k in range(6):
            if k < 2 and gen:
                name, cat = gen.pop(), "교양"
            else:
                name = maj.pop() if maj else f"전공선택{ti}{k}"
                cat = "전필" if k == 2 else "전공"
            credit = rng.choice([3, 3, 3, 2]) if k < 5 else rng.choice([1, 2, 3])
            courses.append({"term": ti, "cat": cat, "name": name, "credit": credit, "g": rng.randrange(len(pts))})

    def gpa_of(cs):
        tc = sum(c["credit"] for c in cs)
        return sum(pts[c["g"]][1] * c["credit"] for c in cs) / tc

    for _ in range(20000):
        g = gpa_of(courses)
        if round(g + 1e-9, 2) == round(target, 2):
            break
        c = rng.choice(courses)
        if g < target and c["g"] > 0:
            c["g"] -= 1
        elif g > target and c["g"] < len(pts) - 1:
            c["g"] += 1
    final = round(gpa_of(courses) + 1e-9, 2)
    terms = []
    for ti, label in enumerate(term_labels):
        cs = [c for c in courses if c["term"] == ti]
        tg = gpa_of(cs)
        terms.append(
            {
                "label": label,
                "courses": [(c["cat"], c["name"], c["credit"], pts[c["g"]][0]) for c in cs],
                "credits": sum(c["credit"] for c in cs),
                "gpa_str": f"{tg:.2f}",
                "pct": pct_of(tg, scale),
            }
        )
    total = sum(c["credit"] for c in courses)
    split_gen = sum(c["credit"] for c in courses if c["cat"] == "교양")
    split_maj = total - split_gen
    return {
        "terms": terms,
        "gpa": final,
        "gpa_printed": f"{final:.2f}",
        "scale_str": scale_key,
        "pct": pct_of(final, scale),
        "total_credits": total,
        "total_points": f"{sum(pts[c['g']][1] * c['credit'] for c in courses):.2f}",
        "credit_split": [split_gen, split_maj, 0],
        "legend": SCALES[scale_key]["legend"],
    }


# ----------------------------------------------------------------- doc specs

DOC_NAMES = {
    "BUSINESS_REGISTRATION_CERTIFICATE": "사업자등록증",
    "SME_CONFIRMATION_CERTIFICATE": "중소기업확인서",
    "NATIONAL_TAX_PAYMENT_CERTIFICATE": "납세증명서",
    "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE": "4대사회보험료완납증명서",
    "ENROLLMENT_CERTIFICATE": "재학증명서",
    "TRANSCRIPT": "성적증명서",
}


class Ctx:
    def __init__(self, sub: dt.date):
        self.sub = sub
        self.counter = 0

    def next_no(self) -> int:
        self.counter += 1
        return self.counter


def doc_brc(ctx, tag, company, printed=None, brn=None, issue=None):
    issue = issue or ctx.sub - dt.timedelta(days=14)
    brn = brn or company["brn"]
    printed = printed or company["full"]
    data = {
        "tag": tag,
        "brn_printed": brn,
        "company_printed": printed,
        "representative": company["representative"],
        "opening_date_sp": d_sp(dt.date(2021, 3, 2)),
        "corp_reg_no": company["corp_reg_no"],
        "address": company["address"],
        "biz_type": "정보통신업",
        "biz_item": "응용 소프트웨어 개발 및 공급업",
        "biz_item2": "컴퓨터 시스템 통합 자문 및 구축 서비스업",
        "issue_date_sp": d_sp(issue),
        "issuer": "가상세무서장",
    }
    return {
        "layout": "business_registration",
        "data": data,
        "document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
        "expected_classification": "BUSINESS_REGISTRATION_CERTIFICATE",
        "expected_fields": {
            "company_name": known(printed),
            "business_registration_number": known(brn),
        },
        "other_printed_values": {
            "representative": company["representative"],
            "corporate_registration_number": company["corp_reg_no"],
            "opening_date": "2021-03-02",
            "issue_date": issue.isoformat(),
            "address": company["address"],
        },
    }


def doc_sme(ctx, tag, company, printed=None, brn=None):
    vf = ctx.sub - dt.timedelta(days=187)
    vu = vf.replace(year=vf.year + 1) - dt.timedelta(days=1)
    issue = vf + dt.timedelta(days=8)
    brn = brn or company["brn"]
    printed = printed or company["full"]
    data = {
        "tag": tag,
        "issue_no": f"TEST-0010-{ctx.sub.year}-{ctx.next_no():05d}",
        "company_printed": printed,
        "brn_printed": brn,
        "corp_reg_no": company["corp_reg_no"],
        "representative": company["representative"],
        "address": company["address"],
        "validity_printed": f"{vf.isoformat()} ~ {vu.isoformat()}",
        "issue_date_kr": d_kr(issue),
    }
    return {
        "layout": "sme_confirmation",
        "data": data,
        "document_type": "SME_CONFIRMATION_CERTIFICATE",
        "expected_classification": "SME_CONFIRMATION_CERTIFICATE",
        "expected_fields": {
            "company_name": known(printed),
            "business_registration_number": known(brn),
            "valid_from": known(vf.isoformat()),
            "valid_until": known(vu.isoformat()),
        },
        "other_printed_values": {
            "representative": company["representative"],
            "corporate_registration_number": company["corp_reg_no"],
            "issue_date": issue.isoformat(),
            "size_class": "중기업",
        },
    }


def doc_nts(ctx, tag, company, printed=None, brn=None, issue=None, valid_until=None, local_tax=False):
    issue = issue or ctx.sub - dt.timedelta(days=4)
    vu = valid_until or issue + dt.timedelta(days=30)
    brn = brn or company["brn"]
    printed = printed or company["full"]
    n = ctx.next_no()
    data = {
        "tag": tag,
        "local_tax": local_tax,
        "issue_no": f"TEST-{ctx.sub.year}-{n:04d}-{n * 7919 % 10000:04d}",
        "company_printed": printed,
        "brn_printed": brn,
        "address": company["address"],
        "valid_until_sp": d_sp(vu),
        "receipt_no": f"TEST{n:08d}",
        "issue_date_sp": d_sp(issue),
        "issuer": "가상구청장" if local_tax else "가상세무서장",
    }
    dtype = "NATIONAL_TAX_PAYMENT_CERTIFICATE"
    return {
        "layout": "tax_payment",
        "data": data,
        "document_type": "LOCAL_TAX_PAYMENT_CERTIFICATE (not modelled in ADVS)" if local_tax else dtype,
        "expected_classification": "UNKNOWN" if local_tax else dtype,
        "filename_override": "지방세납세증명서" if local_tax else None,
        "expected_fields": {
            "company_name": known(printed),
            "business_registration_number": known(brn),
            "valid_until": known(vu.isoformat(), d_sp(vu)),
        },
        "other_printed_values": {"issue_date": issue.isoformat(), "issuer": data["issuer"]},
    }


def doc_si(ctx, tag, company, printed=None, brn=None, validity_row=True):
    issue = ctx.sub - dt.timedelta(days=4)
    vu = issue + dt.timedelta(days=30)
    brn = brn or company["brn"]
    printed = printed or company["full"]
    data = {
        "tag": tag,
        "workplace_printed": printed,
        "address": company["address"],
        "representative": company["representative"],
        "rrn_masked": "800101-*******",
        "brn_printed": brn,
        "mgmt_no": company["mgmt_no"],
        "insured_since": "2021-03-02",
        "valid_until_kr": d_kr(vu),
        "validity_row": validity_row,
        "issue_date_kr": d_kr(issue),
    }
    return {
        "layout": "social_insurance",
        "data": data,
        "document_type": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
        "expected_classification": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
        "expected_fields": {
            "workplace_name": known(printed),
            "business_registration_number": known(brn),
            "valid_until": known(vu.isoformat(), d_kr(vu)) if validity_row else absent("no validity row printed (original sample structure)"),
        },
        "other_printed_values": {
            "representative": company["representative"],
            "issue_date": issue.isoformat(),
            "workplace_management_number": company["mgmt_no"],
            "note": "validity row added to the original structure" if validity_row else "original structure: no validity date printed",
        },
    }


def doc_enr_a(ctx, tag, st=None, issue=None, issue_blank=False, title=None, dept=None):
    st = st or STUDENT
    issue = issue or ctx.sub - dt.timedelta(days=5)
    dept = dept or st["department"]
    n = ctx.next_no()
    data = {
        "tag": tag,
        "issue_no": f"{ctx.sub.year}-TEST-{n:04d}",
        "student_name": st["name"],
        "birth_kr": d_kr(st["birth"]),
        "college": st["college"],
        "department": dept,
        "student_id": st["student_id"],
        "year_term": "3 학년 (2학기)",
        "period_line1": f"{d_kr(st['admission'])} 입학",
        "period_line2": f"{d_kr(issue)} 재학중",
        "issue_date_kr": "" if issue_blank else d_kr(issue),
        "university": st["university"],
        "internet_no": f"TEST-K{n:010d}",
    }
    dtype = "ENROLLMENT_CERTIFICATE"
    expected_class = dtype
    fname = None
    if title == "휴학증명서":
        data.update(title="휴학증명서", period_label="휴  학  기  간",
                    period_line1=f"{d_kr(ctx.sub - dt.timedelta(days=35))} ~ {d_kr(ctx.sub + dt.timedelta(days=145))}",
                    period_line2="", year_term="3 학년 (1학기 수료)")
        dtype, expected_class, fname = "LEAVE_OF_ABSENCE_CERTIFICATE (not modelled)", "UNKNOWN", "휴학증명서"
    elif title == "졸업예정증명서":
        data.update(title="졸업예정증명서", period_label="졸 업 예 정 일",
                    period_line1=d_kr(dt.date(ctx.sub.year + 1, 2, 19)), period_line2="", year_term="4 학년 (2학기)")
        dtype, expected_class, fname = "EXPECTED_GRADUATION_CERTIFICATE (not modelled)", "UNKNOWN", "졸업예정증명서"
    fields = {
        "student_name": known(st["name"]),
        "university_name": known(st["university"]),
        "department": known(dept, f"{st['college']} {dept}"),
        "student_id": known(st["student_id"]),
        "issue_date": absent("issue-date line left blank") if issue_blank else known(issue.isoformat(), d_kr(issue)),
    }
    return {
        "layout": "enrollment_a",
        "data": data,
        "document_type": dtype,
        "expected_classification": expected_class,
        "filename_override": fname,
        "expected_fields": fields,
        "other_printed_values": {"birth_date": st["birth"].isoformat(), "admission_date": st["admission"].isoformat()},
    }


def doc_enr_b(ctx, tag, st=None):
    st = st or STUDENT
    issue = ctx.sub - dt.timedelta(days=5)
    n = ctx.next_no()
    data = {
        "tag": tag,
        "issue_no": f"{ctx.sub.year} - TEST{n:03d}",
        "student_name": st["name"],
        "birth_kr_nz": d_kr_nz(st["birth"]),
        "college": st["college"],
        "department": st["department"],
        "major": st["major"],
        "admission_kr_nz": d_kr_nz(st["admission"]),
        "year_only": "3학년",
        "double_major": "-",
        "issue_date_kr_nz": d_kr(issue),
        "university": st["university"],
        "internet_no": f"TEST-K{n:010d}",
    }
    return {
        "layout": "enrollment_b",
        "data": data,
        "document_type": "ENROLLMENT_CERTIFICATE",
        "expected_classification": "ENROLLMENT_CERTIFICATE",
        "expected_fields": {
            "student_name": known(st["name"]),
            "university_name": known(st["university"]),
            "department": known(st["department"], f"{st['college']} {st['department']}"),
            "student_id": absent("this layout prints no student number (like the bordered sample)"),
            "issue_date": known(issue.isoformat(), d_kr(issue)),
        },
        "other_printed_values": {"major": st["major"], "birth_date": st["birth"].isoformat()},
    }


def doc_tr(ctx, tag, layout="transcript_a", target=3.80, scale="4.5", seed=1, name=None, dept=None):
    st = STUDENT
    issue = ctx.sub - dt.timedelta(days=5)
    tr = make_transcript(target, scale, seed)
    n = ctx.next_no()
    data = {
        "tag": tag,
        "issue_no": f"{ctx.sub.year} - TEST{n:04d}",
        "college": st["college"] if not dept else ALT["college"],
        "department": dept or st["department"],
        "student_id": st["student_id"],
        "admission_kr_nz": d_kr_nz(st["admission"]),
        "admission_iso_slash": st["admission"].strftime("%Y/%m/%d"),
        "birth_kr_nz": d_kr_nz(st["birth"]),
        "student_name": name or st["name"],
        "rrn_masked": "030515-*******",
        "issue_date_kr": d_kr(issue),
        "university": st["university"],
        "internet_no": f"TEST-K{n:010d}",
        **tr,
    }
    return {
        "layout": layout,
        "data": data,
        "document_type": "TRANSCRIPT",
        "expected_classification": "TRANSCRIPT",
        "expected_fields": {
            "student_name": known(name or st["name"]),
            "university_name": known(st["university"]),
            "student_id": known(st["student_id"]),
            "issue_date": known(issue.isoformat(), d_kr(issue)),
            "gpa": known(tr["gpa_printed"], f"{tr['gpa_printed']}/{scale}" if layout == "transcript_a" else f"{tr['gpa_printed']} / {scale}"),
            "gpa_scale": known(scale),
        },
        "other_printed_values": {
            "department_printed": f"{data['college']} {data['department']}",
            "total_credits": tr["total_credits"],
            "gpa_location": "summary line '평점평균: x/scale' after the last term" if layout == "transcript_a" else "header table cell under '총평점평균'",
            "note": "TRANSCRIPT schema in ADVS has no department field; printed for cross-document tests",
        },
    }


# ----------------------------------------------------------------- rendering


def render_pdf(pages_html: list[str], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(L.document(pages_html))
        tmp = f.name
    subprocess.run(
        ["wkhtmltopdf", "-q", "--page-size", "A4", "-T", "0", "-B", "0", "-L", "0", "-R", "0",
         "--disable-smart-shrinking", tmp, str(out)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    Path(tmp).unlink()


def rasterize(pdf: Path, dpi: int) -> list[Image.Image]:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), f"{td}/p"], check=True)
        return [Image.open(p).convert("RGB").copy() for p in sorted(Path(td).glob("p-*.png"))]


def scan_effect(img: Image.Image, rng: np.random.Generator, angle=None, noise=1.0, blur=0.55) -> Image.Image:
    if angle is None:
        angle = float(rng.uniform(-0.45, 0.45))
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    a = np.asarray(img).astype(np.float32)
    a = a * 0.955 + np.array([9.0, 7.0, 1.0], dtype=np.float32)
    a += rng.normal(0, noise, a.shape[:2]).astype(np.float32)[..., None]
    a = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(a).filter(ImageFilter.GaussianBlur(blur))


def save_image_pdf(images: list[Image.Image], out: Path, dpi: int, quality: int = 60) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    first, rest = images[0], images[1:]
    first.save(out, "PDF", resolution=float(dpi), save_all=True, append_images=rest, quality=quality)


def phone_photo(img: Image.Image, rng: np.random.Generator) -> Image.Image:
    a = np.asarray(img.convert("RGB"))
    h, w = a.shape[:2]
    cw, ch = int(w * 1.22), int(h * 1.16)
    bg = np.full((ch, cw, 3), (88, 80, 70), np.uint8)
    bg = np.clip(bg.astype(np.int16) + rng.normal(0, 6, (ch, cw, 1)).astype(np.int16), 0, 255).astype(np.uint8)
    ox, oy = (cw - w) // 2, (ch - h) // 2
    j = lambda: float(rng.uniform(-0.035, 0.035)) * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[ox + j(), oy + j()], [ox + w + j(), oy + j()], [ox + w + j(), oy + h + j()], [ox + j(), oy + h + j()]])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(a, M, (cw, ch), dst=bg.copy(), borderMode=cv2.BORDER_TRANSPARENT)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    shade = 0.70 + 0.30 * (xx / cw)
    shade *= 1.0 - 0.18 * (((xx - cw * 0.6) / cw) ** 2 + ((yy - ch * 0.4) / ch) ** 2)
    out = np.clip(warped.astype(np.float32) * shade[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(out).filter(ImageFilter.GaussianBlur(0.9))


# ----------------------------------------------------------------- main build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ADVS_test_variants")
    ap.add_argument("--submission-date", default="2026-10-05")
    ap.add_argument("--seed", type=int, default=20261005)
    ap.add_argument("--profile", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--formats", default="all", help="comma list of format set ids, or 'all'")
    args = ap.parse_args()
    if args.profile == "holdout":
        import holdout_profile

        holdout_profile.apply(globals(), L)
    fmt_filter = None if args.formats == "all" else set(args.formats.split(","))

    sub = dt.date.fromisoformat(args.submission_date)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    rng = np.random.default_rng(args.seed)
    ctx = Ctx(sub)

    # A different, still checksum-valid number. (Changing exactly one digit of a
    # valid number always breaks the check digit, so a checksum-valid mismatch
    # must differ in at least two digits: here the 9th digit and the check digit.)
    a = COMPANY_A["brn"].replace("-", "")
    cand9 = a[:8] + str((int(a[8]) + 1) % 10)
    off = cand9 + str(brn_check_digit(cand9))
    brn_off = f"{off[:3]}-{off[3:5]}-{off[5:]}"

    files_meta: list[dict] = []
    sets_meta: list[dict] = []

    IMAGE_CYCLE = ["jpg", "png", "webp"]
    SCEN_DPI = 170  # scenario scans/photos; format set F02-F09 stays at 200 DPI

    def save_scan_image(im: Image.Image, path_noext: Path, fmt: str) -> Path:
        path_noext.parent.mkdir(parents=True, exist_ok=True)
        p = path_noext.with_suffix("." + fmt)
        if fmt == "jpg":
            im.save(p, "JPEG", quality=60)
        elif fmt == "webp":
            im.save(p, "WEBP", quality=75)
        else:  # png: grayscale at 150 DPI keeps lossless files a realistic size
            w, h = im.size
            im.convert("L").resize((int(w * 0.88), int(h * 0.88)), Image.LANCZOS).save(p, "PNG", optimize=True)
        return p

    def emit(folder: Path, base: str, spec: dict, set_id: str, styles=("digital", "scanned", "images")) -> dict:
        """Render one document in the requested styles; return per-style paths."""
        name = spec.get("filename_override") or DOC_NAMES.get(spec["document_type"], spec["document_type"])
        stem = f"{base}_{name}"
        paths = {}
        html = L.LAYOUTS[spec["layout"]](spec["data"])
        dig = folder / "digital" / f"{stem}.pdf"
        render_pdf([html], dig)
        if "digital" in styles:
            paths["digital"] = dig
        if "scanned" in styles:
            imgs = [scan_effect(im, rng) for im in rasterize(dig, SCEN_DPI)]
            sc = folder / "scanned" / f"{stem}_스캔.pdf"
            save_image_pdf(imgs, sc, SCEN_DPI)
            paths["scanned"] = sc
        if "images" in styles:
            idx = int(base.split("-")[-1])
            fmt = IMAGE_CYCLE[(idx - 1) % len(IMAGE_CYCLE)]
            imgs2 = [scan_effect(im, rng, noise=0.0 if fmt == "png" else 1.0) for im in rasterize(dig, SCEN_DPI)]
            paths["images"] = save_scan_image(imgs2[0], folder / "images" / f"{stem}_사진", fmt)
        if "digital" not in styles:
            dig.unlink()
            try:
                dig.parent.rmdir()
            except OSError:
                pass
        for style, p in paths.items():
            files_meta.append(
                {
                    "file": str(p.relative_to(out)),
                    "set_id": set_id,
                    "document_type": spec["document_type"],
                    "expected_classification": spec["expected_classification"],
                    "layout": spec["layout"],
                    "style": style,
                    "text_layer": style == "digital",
                    "format": p.suffix.lstrip(".").lower(),
                    "expected_fields": spec["expected_fields"],
                    "other_printed_values": spec.get("other_printed_values", {}),
                    "provenance": "SYNTHETIC_VARIANT",
                    "contains_real_personal_data": False,
                    "_verify_printed": [
                        v.get("printed") for v in spec["expected_fields"].values() if v.get("state") == "KNOWN_VALUE"
                    ] if style == "digital" else [],
                }
            )
        return paths

    def add_set(set_id, slug, title, workflow, specs, expected, correct, current=None, bug=None, condition=None, styles=("digital", "scanned", "images"), extra_files=None):
        folder = out / workflow / f"{set_id}_{slug}"
        if "scanned" in expected and "images" not in expected:
            expected["images"] = dict(expected["scanned"])
        per_style = {s: [] for s in styles}
        for i, spec in enumerate(specs, 1):
            paths = emit(folder, f"{set_id}-{i}", spec, set_id, styles)
            for s, p in paths.items():
                per_style[s].append(str(p.relative_to(out)))
        if extra_files:
            for s, rels in extra_files(folder).items():
                per_style.setdefault(s, []).extend(rels)
        sets_meta.append(
            {
                "set_id": set_id,
                "title": title,
                "workflow": workflow,
                "submission_date": sub.isoformat(),
                "checklist_condition": condition or ("default business checklist: all four business documents required" if workflow == "business" else "default student checklist: 재학증명서 required, 성적증명서 optional"),
                "files": per_style,
                "expected": expected,
                "correct_behavior": correct,
                "current_behavior_per_audit": current,
                "known_bug_reference": bug,
            }
        )

    A = COMPANY_A
    sub_s = sub.isoformat()

    # ---------------------------------------------------------- business sets
    def b01():
        return [doc_brc(ctx, "B01", A), doc_sme(ctx, "B01", A), doc_nts(ctx, "B01", A), doc_si(ctx, "B01", A)]

    add_set("B01", "all_valid", "All consistent, all valid", "business", b01(),
            {"digital": {"submission_status": "READY", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["OCR_UNCERTAIN (every OCR field needs confirmation)"]}},
            "Digital: READY. Scanned: REVIEW_REQUIRED by policy; READY only after a reviewer confirms the OCR fields.")

    add_set("B02", "name_notation", "Company name written four different ways", "business",
            [doc_brc(ctx, "B02", A, printed=f"주식회사 {A['core']}"), doc_sme(ctx, "B02", A, printed=f"(주){A['core']}"),
             doc_nts(ctx, "B02", A, printed=f"㈜{A['core']}"), doc_si(ctx, "B02", A, printed=f"{A['core']}(주)")],
            {"digital": {"submission_status": "READY", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Same company, so names should match: digital READY.",
            "Digital currently NEEDS_CORRECTION (INFORMATION_MISMATCH): 주식회사 / (주) / ㈜ / trailing (주) normalise to different keys. Only visible on the digital set (OCR values cannot auto-decide).",
            "F-002")

    add_set("B03", "different_company", "Tax certificate belongs to another company", "business",
            [doc_brc(ctx, "B03", A), doc_sme(ctx, "B03", A), doc_nts(ctx, "B03", COMPANY_B, brn=A["brn"]), doc_si(ctx, "B03", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["INFORMATION_MISMATCH (company_name)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Digital: NEEDS_CORRECTION on company name. Scanned: REVIEW_REQUIRED (mismatch can only be decided after confirmation), never READY.")

    add_set("B04", "brn_mismatch", "SME certificate business number differs (last two digits)", "business",
            [doc_brc(ctx, "B04", A), doc_sme(ctx, "B04", A, brn=brn_off), doc_nts(ctx, "B04", A), doc_si(ctx, "B04", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["INFORMATION_MISMATCH (business_registration_number)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            f"The altered number ({brn_off}) differs from the reference in its last two digits and still passes the check digit, so only the cross-document comparison can catch it.")

    add_set("B05", "tax_expired", "Tax certificate expired before submission", "business",
            [doc_brc(ctx, "B05", A), doc_sme(ctx, "B05", A),
             doc_nts(ctx, "B05", A, issue=sub - dt.timedelta(days=65), valid_until=sub - dt.timedelta(days=35)), doc_si(ctx, "B05", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["EXPIRED_DOCUMENT"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED or NEEDS_CORRECTION — record actual", "issue_codes": []}},
            "Digital: NEEDS_CORRECTION (expired). Scanned: never READY.")

    add_set("B06", "expiry_on_submission_day", "Tax certificate validity ends on the submission date", "business",
            [doc_brc(ctx, "B06", A), doc_sme(ctx, "B06", A),
             doc_nts(ctx, "B06", A, issue=sub - dt.timedelta(days=30), valid_until=sub), doc_si(ctx, "B06", A)],
            {"digital": {"submission_status": "READY (if expiry is inclusive) — record actual", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Boundary case. ADVS treats valid_until >= today as valid (inclusive). Result depends on the date the test is run, because ADVS uses date.today(), not the submission date.",
            "Run on the submission date to test the boundary; on any later day it becomes an expired-document test.",
            "validity-date reference (date.today vs submission date)")

    add_set("B07", "validity_missing", "Social-insurance certificate has no validity date (original sample structure)", "business",
            [doc_brc(ctx, "B07", A), doc_sme(ctx, "B07", A), doc_nts(ctx, "B07", A), doc_si(ctx, "B07", A, validity_row=False)],
            {"digital": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["MISSING_REQUIRED_FIELD (valid_until)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Missing validity must never be READY.",
            "With a checklist that has one REQUIRED_FIELD rule for another field only (e.g. company_name), the digital set currently returns READY — this is the full-path test for F-001.",
            "F-001", condition="run twice: (1) default checklist; (2) checklist with a single REQUIRED_FIELD rule for company_name")

    add_set("B08", "reference_missing", "No 사업자등록증 in the submission", "business",
            [doc_sme(ctx, "B08", A), doc_nts(ctx, "B08", A), doc_si(ctx, "B08", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["MISSING_REQUIRED_DOCUMENT"]},
             "scanned": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["MISSING_REQUIRED_DOCUMENT"]}},
            "Missing required document outranks everything (NEEDS_CORRECTION in both styles).")

    def b09_extra(folder):
        res = {}
        for style in ("digital", "scanned", "images"):
            srcs = sorted((folder / style).glob("B09-3_*"))
            if srcs:
                src = srcs[0]
                dup = src.with_name(src.stem + " (사본)" + src.suffix)
                shutil.copyfile(src, dup)
                res[style] = [str(dup.relative_to(out))]
                files_meta.append({**[m for m in files_meta if m["file"] == str(src.relative_to(out))][0],
                                   "file": str(dup.relative_to(out)), "note": "byte-identical copy of B09-3 under another filename",
                                   "_verify_printed": []})
        return res

    add_set("B09", "duplicate_upload", "The same tax certificate uploaded twice (plus a renamed copy)", "business", b01(),
            {"digital": {"submission_status": "record actual", "issue_codes": ["duplicate detected (record the actual code)"]},
             "scanned": {"submission_status": "record actual", "issue_codes": ["duplicate detected"]}},
            "Upload B09-3 twice and also upload the '(사본)' copy; all three are byte-identical and should be flagged as duplicates within the submission.",
            extra_files=b09_extra)

    add_set("B10", "invalid_check_digit", "Business number fails the check digit (consistent on all documents)", "business",
            [doc_brc(ctx, "B10", A, brn=BRN_A_INVALID), doc_sme(ctx, "B10", A, brn=BRN_A_INVALID),
             doc_nts(ctx, "B10", A, brn=BRN_A_INVALID), doc_si(ctx, "B10", A, brn=BRN_A_INVALID)],
            {"digital": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["business number fails check digit"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "An impossible business number should be flagged even when all documents agree.",
            "Digital currently READY: no check-digit validation exists.", "F-004")

    add_set("B11", "local_tax_lookalike", "지방세 납세증명서 submitted instead of the national-tax certificate", "business",
            [doc_brc(ctx, "B11", A), doc_sme(ctx, "B11", A), doc_nts(ctx, "B11", A, local_tax=True), doc_si(ctx, "B11", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["document classified UNKNOWN", "MISSING_REQUIRED_DOCUMENT (national tax)"]},
             "scanned": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["MISSING_REQUIRED_DOCUMENT"]}},
            "The local-tax certificate is not a 국세 납세증명서: it should be UNKNOWN (or review), leaving the national-tax requirement unmet.",
            "Currently classified as NATIONAL_TAX_PAYMENT_CERTIFICATE at confidence 0.9 because '납세증명서' is matched as a substring; the digital set then returns READY.",
            "F-003")

    add_set("B12", "conflicting_references", "Two 사업자등록증 with different business numbers", "business",
            [doc_brc(ctx, "B12", A), doc_brc(ctx, "B12", A, brn=BRN_A_CONFLICT), doc_sme(ctx, "B12", A), doc_nts(ctx, "B12", A), doc_si(ctx, "B12", A)],
            {"digital": {"submission_status": "NEEDS_CORRECTION or REVIEW_REQUIRED — record actual", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED or NEEDS_CORRECTION — record actual", "issue_codes": []}},
            "Ambiguous reference: must never be READY.")

    # ---------------------------------------------------------- student sets
    add_set("S01", "all_valid", "Enrollment + transcript, consistent and recent", "student",
            [doc_enr_a(ctx, "S01"), doc_tr(ctx, "S01", target=3.80, seed=11)],
            {"digital": {"submission_status": "READY", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Digital READY; scanned REVIEW_REQUIRED by OCR policy.")

    add_set("S02", "issue_date_too_old", "Enrollment certificate issued 120 days before submission", "student",
            [doc_enr_a(ctx, "S02", issue=sub - dt.timedelta(days=120)), doc_tr(ctx, "S02", target=3.80, seed=12)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["issue date older than max age (default 90 days)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED or NEEDS_CORRECTION — record actual", "issue_codes": []}},
            "Default ISSUE_DATE_MAX_AGE is 90 days per the audit; confirm the configured value.")

    add_set("S03", "gpa_below_threshold", "GPA 2.70/4.5 against a 3.0 threshold", "student",
            [doc_enr_a(ctx, "S03"), doc_tr(ctx, "S03", target=2.70, seed=13)],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["GPA below configured threshold"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Requires a GPA threshold rule of 3.0 to be configured; without it the transcript is optional and the set is READY.",
            condition="student checklist with a GPA threshold rule: gpa >= 3.0")

    add_set("S04", "gpa_scale_43", "GPA 3.10 on a 4.3 scale", "student",
            [doc_enr_a(ctx, "S04"), doc_tr(ctx, "S04", target=3.10, scale="4.3", seed=14)],
            {"digital": {"submission_status": "record actual (scale handling)", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Decision needed: convert across scales, or route scale mismatch to review. 3.10/4.3 is above 3.0 raw but below 3.0 if converted to 4.5 proportionally (3.24).",
            condition="student checklist with a GPA threshold rule: gpa >= 3.0")

    add_set("S05", "student_name_differs", "Transcript shows a different student name", "student",
            [doc_enr_a(ctx, "S05"), doc_tr(ctx, "S05", target=3.80, seed=15, name=ALT["student_name"])],
            {"digital": {"submission_status": "record actual", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Same student number, different name. The mentor table defines no student cross-document name check; record whether one exists. A careful pre-check should not silently pass this.")

    add_set("S06", "department_differs", "Enrollment and transcript show different departments", "student",
            [doc_enr_a(ctx, "S06"), doc_tr(ctx, "S06", target=3.80, seed=16, dept=ALT["department"])],
            {"digital": {"submission_status": "record actual", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "TRANSCRIPT has no department field in ADVS, so no comparison is expected today; record the result.")

    add_set("S07", "lookalike_types", "휴학증명서 and 졸업예정증명서 built on the enrollment layout", "student",
            [doc_enr_a(ctx, "S07", title="휴학증명서"), doc_enr_a(ctx, "S07", title="졸업예정증명서")],
            {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["both classified UNKNOWN", "MISSING_REQUIRED_DOCUMENT (enrollment)"]},
             "scanned": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["MISSING_REQUIRED_DOCUMENT"]}},
            "Neither is a 재학증명서; '졸업예정' must not be read as 졸업증명서 or 재학증명서. Submit each alone or both together.")

    add_set("S08", "issue_date_missing", "Enrollment certificate with the issue-date line blank", "student",
            [doc_enr_a(ctx, "S08", issue_blank=True), doc_tr(ctx, "S08", target=3.80, seed=18)],
            {"digital": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["MISSING_REQUIRED_FIELD (issue_date)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Missing issue date must never be READY or treated as expired. Note: the 재학기간 line still prints a date — a correct system must not adopt it as the issue date.")

    add_set("S09", "layout_no_student_id", "Bordered enrollment layout that prints no student number", "student",
            [doc_enr_b(ctx, "S09"), doc_tr(ctx, "S09", target=3.80, seed=19)],
            {"digital": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["MISSING_REQUIRED_FIELD (student_id)"]},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Real layouts sometimes omit a field ADVS expects. The student number is printed on the transcript, but must not be borrowed silently.")

    add_set("S10", "layout_table_transcript", "Older table-style transcript (GPA inside a header table cell)", "student",
            [doc_enr_a(ctx, "S10"), doc_tr(ctx, "S10", layout="transcript_b", target=3.80, seed=20)],
            {"digital": {"submission_status": "READY", "issue_codes": []},
             "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
            "Same values as S01 in a different layout; tests header/value table association for gpa (총평점평균).")

    if PROFILE["holdout"]:
        import holdout_profile

        holdout_profile.extra_sets(globals(), locals(), add_set, ctx, sub)

    # ---------------------------------------------------------- format variants
    fmt_root = out / "formats"
    base_specs = {
        "사업자등록증": doc_brc(ctx, "F", A),
        "재학증명서": doc_enr_a(ctx, "F"),
        "중소기업확인서": doc_sme(ctx, "F", A),
        "납세증명서": doc_nts(ctx, "F", A),
        "4대사회보험료완납증명서": doc_si(ctx, "F", A),
        "재학증명서_레이아웃B": doc_enr_b(ctx, "F"),
        "성적증명서": doc_tr(ctx, "F", target=3.80, seed=31),
        "성적증명서_레이아웃B": doc_tr(ctx, "F", layout="transcript_b", target=3.80, seed=31),
    }
    CORE_TWO = ["사업자등록증", "재학증명서"]
    fmt_sets: list[dict] = []

    def add_fmt(fid, slug, title, expectation, make, docs=None):
        if fmt_filter is not None and fid not in fmt_filter:
            return
        folder = fmt_root / f"{fid}_{slug}"
        folder.mkdir(parents=True, exist_ok=True)
        produced = []
        for docname in (docs or CORE_TWO):
            spec = base_specs[docname]
            for p, meta in make(folder, docname, spec):
                produced.append(str(p.relative_to(out)))
                files_meta.append(
                    {
                        "file": str(p.relative_to(out)),
                        "set_id": fid,
                        "document_type": spec["document_type"] if meta.get("classifiable", True) else "n/a",
                        "expected_classification": meta.get("expected_classification", spec["expected_classification"]),
                        "layout": spec["layout"],
                        "style": meta.get("style", "scanned"),
                        "text_layer": meta.get("text_layer", False),
                        "format": p.suffix.lstrip(".").lower() or "none",
                        "expected_fields": spec["expected_fields"] if meta.get("classifiable", True) else {},
                        "variant_note": meta.get("note", ""),
                        "provenance": "SYNTHETIC_VARIANT",
                        "contains_real_personal_data": False,
                        "_verify_printed": meta.get("verify", []),
                    }
                )
        fmt_sets.append({"set_id": fid, "title": title, "expected": expectation, "files": produced})

    cache_pdf = {}
    cache_img = {}

    def digital_pdf(docname, spec):
        if docname not in cache_pdf:
            p = Path(tempfile.mkdtemp()) / "d.pdf"
            render_pdf([L.LAYOUTS[spec["layout"]](spec["data"])], p)
            cache_pdf[docname] = p
        return cache_pdf[docname]

    def base_img(docname, spec, dpi=200):
        key = (docname, dpi)
        if key not in cache_img:
            cache_img[key] = rasterize(digital_pdf(docname, spec), dpi)[0]
        return cache_img[key].copy()

    def printed(spec):
        return [v["printed"] for v in spec["expected_fields"].values() if v.get("state") == "KNOWN_VALUE"]

    def f01(folder, n, spec):
        p = folder / f"F01_{n}.pdf"
        shutil.copyfile(digital_pdf(n, spec), p)
        return [(p, {"style": "digital", "text_layer": True, "verify": printed(spec)})]

    def f02(folder, n, spec):
        p = folder / f"F02_{n}_스캔.pdf"
        save_image_pdf([scan_effect(base_img(n, spec), rng)], p, 200)
        return [(p, {})]

    def img_variant(ext, **kw):
        def f(folder, n, spec, _ext=ext, _kw=kw):
            p = folder / f"{folder.name[:3]}_{n}.{_ext}"
            im = scan_effect(base_img(n, spec), rng, noise=0.0 if _ext in ("png", "tiff", "bmp") else 1.0)
            if _ext in ("png", "tiff", "bmp"):
                im = im.convert("L")  # grayscale, as many office scanners save lossless scans
            fmt = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "tiff": "TIFF", "bmp": "BMP"}[_ext]
            im.save(p, fmt, **_kw)
            return [(p, {})]
        return f

    def f07(folder, n, spec):
        p = folder / f"F07_{n}_90도회전.png"
        scan_effect(base_img(n, spec), rng, noise=0.0).convert("L").rotate(90, expand=True).save(p, "PNG")
        return [(p, {"note": "pixels rotated 90° counter-clockwise; no EXIF"})]

    def f08(folder, n, spec):
        im = scan_effect(base_img(n, spec), rng)
        exif = Image.Exif()
        exif[0x0112] = 6
        p1 = folder / f"F08a_{n}_EXIF정상.jpg"
        im.rotate(90, expand=True).save(p1, "JPEG", quality=90, exif=exif.tobytes())
        p2 = folder / f"F08b_{n}_EXIF오류.jpg"
        im.save(p2, "JPEG", quality=90, exif=exif.tobytes())
        return [
            (p1, {"note": "pixels stored rotated; EXIF Orientation=6 makes it upright when honoured (correct handling: upright)"}),
            (p2, {"note": "pixels already upright but EXIF Orientation=6 (a wrong tag, as some phones/scanners write); honouring it turns the page sideways"}),
        ]

    def f09(folder, n, spec):
        p = folder / f"F09_{n}_기울기3도.png"
        im = base_img(n, spec).rotate(3, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        scan_effect(im, rng, angle=0, noise=0.0).convert("L").save(p, "PNG")
        return [(p, {"note": "rotated 3 degrees"})]

    def f10(folder, n, spec):
        im = scan_effect(base_img(n, spec, dpi=100), rng, blur=0.4)
        p1 = folder / f"F10_{n}_100dpi.png"
        im.convert("L").save(p1, "PNG")
        p2 = folder / f"F10_{n}_100dpi.pdf"
        save_image_pdf([im], p2, 100)
        return [(p1, {"note": "~100 DPI"}), (p2, {"note": "~100 DPI image-only PDF"})]

    def f11(folder, n, spec):
        p = folder / f"F11_{n}_휴대폰촬영.jpg"
        phone_photo(base_img(n, spec), rng).save(p, "JPEG", quality=78)
        return [(p, {"note": "perspective, background, shadow and uneven light"})]

    def multipage(fid, extra_layouts):
        def f(folder, n, spec):
            pages = [L.LAYOUTS[spec["layout"]](spec["data"])]
            for lay, d in extra_layouts(n):
                pages.append(L.LAYOUTS[lay](d))
            dig = folder / f"{fid}_{n}.pdf"
            render_pdf(pages, dig)
            sc = folder / f"{fid}_{n}_스캔.pdf"
            save_image_pdf([scan_effect(im, rng) for im in rasterize(dig, 200)], sc, 200)
            return [(dig, {"style": "digital", "text_layer": True, "verify": printed(spec)}), (sc, {})]
        return f

    def f13_extra(n):
        return [("tax_payment", doc_nts(ctx, "F13", A)["data"])]

    def f15(folder, n, spec):
        out_list = []
        p = folder / f"F15_{n}.tiff"
        scan_effect(base_img(n, spec), rng, noise=0.0).convert("L").save(p, "TIFF", compression="tiff_lzw")
        out_list.append((p, {"note": "TIFF image"}))
        p = folder / f"F15_{n}.bmp"
        scan_effect(base_img(n, spec), rng, noise=0.0).convert("L").save(p, "BMP")
        out_list.append((p, {"note": "BMP image"}))
        try:
            import docx  # type: ignore

            doc = docx.Document()
            doc.add_heading(n, 0)
            for v in printed(spec):
                doc.add_paragraph(str(v))
            doc.add_paragraph(L.MARK_TEXT)
            p = folder / f"F15_{n}.docx"
            doc.save(p)
            out_list.append((p, {"note": "Word file with the same values", "classifiable": False}))
        except ImportError:
            pass
        return out_list

    def f16(folder, n, spec):
        src = digital_pdf(n, spec).read_bytes()
        p1 = folder / f"F16a_{n}_손상.pdf"
        p1.write_bytes(src[: int(len(src) * 0.6)])
        p2 = folder / f"F16b_{n}_빈파일.pdf"
        p2.write_bytes(b"")
        p3 = folder / f"F16c_{n}_확장자위장.pdf"
        buf = io.BytesIO()
        base_img(n, spec).save(buf, "PNG")
        p3.write_bytes(buf.getvalue())
        return [
            (p1, {"note": "truncated at 60% of its bytes", "classifiable": False, "expected_classification": "n/a"}),
            (p2, {"note": "0-byte file", "classifiable": False, "expected_classification": "n/a"}),
            (p3, {"note": "PNG bytes saved with a .pdf extension", "classifiable": False, "expected_classification": "n/a"}),
        ]

    add_fmt("F01", "digital_pdf", "Digital PDF with text layer", "processed via embedded text; READY-capable", f01, docs=list(base_specs))
    add_fmt("F02", "scanned_pdf", "Scanned PDF (image only, 200 DPI)", "OCR path; fields go to review", f02, docs=list(base_specs))
    add_fmt("F03", "png", "PNG image", "OCR path", img_variant("png"), docs=list(base_specs))
    add_fmt("F04", "jpeg", "JPEG, normal quality", "OCR path", img_variant("jpg", quality=80), docs=list(base_specs))
    add_fmt("F05", "jpeg_low_quality", "JPEG, heavy compression (quality 30)", "OCR path; expect more unresolved fields", img_variant("jpg", quality=30), docs=list(base_specs))
    add_fmt("F06", "webp", "WEBP image", "OCR path (WEBP acceptance was a past regression)", img_variant("webp", quality=80), docs=list(base_specs))
    add_fmt("F07", "rotated_90", "Page rotated 90°", "orientation correction should recover it; otherwise review, never wrong values", f07)
    add_fmt("F08", "exif_orientation", "EXIF orientation tags (correct and wrong)", "F08a should read upright; F08b documents behaviour with a wrong tag", f08)
    add_fmt("F09", "skew_3deg", "Skewed 3°", "OCR path; should still extract or abstain", f09)
    add_fmt("F10", "low_resolution", "Low resolution (~100 DPI)", "more unresolved fields; never confident wrong values", f10)
    add_fmt("F11", "phone_photo", "Phone-photo style", "OCR path; expect review", f11, docs=list(base_specs))
    add_fmt("F12", "multipage_unrelated", "Certificate + unrelated second page", "classified by the certificate page; no field taken from page 2",
            multipage("F12", lambda n: [("notice", {"tag": "F12"})]))
    add_fmt("F13", "multipage_two_certs", "Two different certificates in one PDF (page 2 = 납세증명서)", "should be flagged or split; must not merge fields from both",
            multipage("F13", f13_extra))
    add_fmt("F14", "blank_page_appended", "Certificate + blank page", "blank page ignored", multipage("F14", lambda n: [("blank", {"tag": "F14"})]))
    add_fmt("F15", "other_formats", "TIFF, BMP and DOCX", "accepted or rejected per upload rules; record which (HEIC not generated: no encoder available)", f15)
    add_fmt("F16", "corrupt_files", "Truncated PDF, 0-byte file, PNG disguised as .pdf", "FAILED or rejected; never READY", f16)

    # ---------------------------------------------------------- manifest + readme
    for m in files_meta:
        p = out / m["file"]
        m["sha256"] = sha256(p)
        m["bytes"] = p.stat().st_size
    manifest = {
        "name": "ADVS test-variant document set" + (" — HOLD-OUT" if PROFILE["holdout"] else ""),
        "profile": PROFILE["name"],
        "holdout": PROFILE["holdout"],
        "holdout_rule": "Do not use for development, debugging or tuning. Run only for the final judgement of a phase; report aggregate results." if PROFILE["holdout"] else None,
        "generated": dt.date.today().isoformat(),
        "submission_date": sub_s,
        "generator": "_generator/gen_test_variants.py",
        "provenance": "SYNTHETIC_VARIANT — layouts rebuilt from scratch; no pixel or value from any real document",
        "contains_real_personal_data": False,
        "fictional_entities": {
            "company_A": {k: COMPANY_A[k] for k in ("full", "brn", "corp_reg_no", "representative")},
            "company_B": {k: COMPANY_B[k] for k in ("full", "brn")},
            "brn_A_mismatch_checksum_valid": brn_off,
            "brn_A_conflicting_reference": BRN_A_CONFLICT,
            "brn_A_invalid_check_digit": BRN_A_INVALID,
            "student": {"name": STUDENT["name"], "student_id": STUDENT["student_id"], "university": STUDENT["university"], "department": STUDENT["department"]},
            "alternates": ALT,
        },
        "check_digit_validity": {
            "company_A": brn_is_valid(COMPANY_A["brn"]),
            "company_B": brn_is_valid(COMPANY_B["brn"]),
            "mismatch_checksum_valid": brn_is_valid(brn_off),
            "conflicting_reference": brn_is_valid(BRN_A_CONFLICT),
            "invalid_check_digit": brn_is_valid(BRN_A_INVALID),
        },
        "assumptions": [
            "Expected statuses follow ADVS rules as described in the independent audit (evaluation/system_audit/ADVS_system_audit_report.md); verify against code where marked 'record actual'.",
            "Every OCR-sourced field is routed to review regardless of confidence (audit F-010), so scanned sets cannot reach READY or decide a mismatch without confirmation. Bug-exposing scenarios (B02, B07, B10, B11) are only visible on the digital sets.",
            "Digital PDFs carry a real text layer and exercise the embedded-text path, which the real corpus has never tested.",
            "ADVS checks validity against date.today(), not the submission date. Regenerate with --submission-date set to the test-run date so validity windows match.",
            "The social-insurance layout adds a 유효기간 row (not in the original sample) so ADVS's valid_until field has a source; B07 keeps the original structure without it.",
        ],
        "business_sets": [s for s in sets_meta if s["workflow"] == "business"],
        "student_sets": [s for s in sets_meta if s["workflow"] == "student"],
        "format_sets": fmt_sets,
        "files": [{k: v for k, v in m.items() if not k.startswith("_")} for m in files_meta],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "_verify_index.json").write_text(
        json.dumps([{"file": m["file"], "printed": m["_verify_printed"], "text_layer": m.get("text_layer", False)} for m in files_meta], ensure_ascii=False),
        encoding="utf-8",
    )
    gen_dir = out / "_generator"
    gen_dir.mkdir()
    here = Path(__file__).resolve().parent
    shutil.copyfile(here / "gen_test_variants.py", gen_dir / "gen_test_variants.py")
    shutil.copyfile(here / "layouts.py", gen_dir / "layouts.py")
    shutil.copyfile(here / "holdout_profile.py", gen_dir / "holdout_profile.py")
    print(f"files: {len(files_meta)}  sets: {len(sets_meta)}  formats: {len(fmt_sets)}  brn_off={brn_off}")


if __name__ == "__main__":
    main()
