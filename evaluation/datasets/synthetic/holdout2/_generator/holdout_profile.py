"""Hold-out profile for the ADVS test-variant generator.

Same document structures as the development set, but:
- different fictional companies, people, numbers, university and dates;
- small random shifts in field positions and font sizes (layout jitter);
- digital PDFs whose text layer is stored in a shuffled order (simulates a
  different PDF generator; the visual layout is unchanged);
- a generic red "TEST 견본" stamp overlapping the issuer line, the way real
  seals overlap printed text (it does not imitate any real seal);
- extra near-miss scenarios (one-character company name, transposed business
  number, one-digit student number) that a fuzzy or over-trusting matcher
  would wrongly accept.

The hold-out set is for the final judgement of a phase only.
"""

from __future__ import annotations

import datetime as dt
import random
import re

_rng = random.Random(77123)


def _brn_variant_transposed(brn: str, check_digit) -> str:
    """Return a checksum-valid number made by transposing two adjacent digits
    of `brn` (positions 4..8), so the cross-document comparison is the only
    thing that can catch it."""
    d = brn.replace("-", "")
    for i in range(3, 8):
        if d[i] == d[i + 1]:
            continue
        t = d[:i] + d[i + 1] + d[i] + d[i + 2 :]
        if check_digit(t[:9]) == int(t[9]):
            return f"{t[:3]}-{t[3:5]}-{t[5:]}"
    # fall back: transpose and recompute the check digit (two-digit difference)
    t9 = d[:5] + d[6] + d[5] + d[7:9]
    t = t9 + str(check_digit(t9))
    return f"{t[:3]}-{t[3:5]}-{t[5:]}"


VARIANT = {"n": 1}


def apply(G: dict, L, variant: int = 1) -> None:
    make_brn = G["make_brn"]
    VARIANT["n"] = variant
    if variant == 2:
        _rng.seed(90517)
        _apply_v2(G, make_brn)
        _patch_layouts(L, jitter=1.7, fonts=True, tag="HOLD-OUT-2")
        return
    G["PROFILE"].update({"name": "holdout", "holdout": True})
    G["COMPANY_A"] = {
        "core": "한빛테스트",
        "full": "주식회사 한빛테스트",
        "representative": "정가상",
        "corp_reg_no": "110111-9345678",
        "address": "부산광역시 가상구 샘플로 77, 3층 (견본동)",
        "brn": make_brn("617813579"),
        "mgmt_no": "6171357911-0",
    }
    G["COMPANY_B"] = {
        "core": "미래샘플",
        "full": "주식회사 미래샘플",
        "representative": "윤가상",
        "corp_reg_no": "110111-9456789",
        "address": "대전광역시 가상구 견본대로 12, 5층",
        "brn": make_brn("314862468"),
        "mgmt_no": "3148624681-0",
    }
    G["BRN_A_CONFLICT"] = make_brn("617819753")
    G["BRN_A_INVALID"] = make_brn("617813579", valid=False)
    G["STUDENT"] = {
        "name": "박샘플",
        "birth": dt.date(2002, 11, 3),
        "university": "가상과학기술대학교",
        "college": "자연과학대학",
        "department": "통계학과",
        "major": "응용통계전공",
        "student_id": "2022087654",
        "admission": dt.date(2022, 3, 2),
    }
    G["ALT"].update(
        {
            "student_name": "정테스트",
            "college": "경영대학",
            "department": "경영학과",
            "company_near_miss": "한빛데스트",
        }
    )

    _patch_layouts(L, jitter=1.0, fonts=False, tag="HOLD-OUT")


def _apply_v2(G: dict, make_brn) -> None:
    G["PROFILE"].update({"name": "holdout2", "holdout": True})
    G["COMPANY_A"] = {
        "core": "온누리샘플",
        "full": "주식회사 온누리샘플",
        "representative": "한가상",
        "corp_reg_no": "110111-9567890",
        "address": "광주광역시 가상구 예시로 9, 2층 (견본동)",
        "brn": make_brn("402856172"),
        "mgmt_no": "4028561721-0",
    }
    G["COMPANY_B"] = {
        "core": "다온테스트",
        "full": "주식회사 다온테스트",
        "representative": "서가상",
        "corp_reg_no": "110111-9678901",
        "address": "인천광역시 가상구 시험로 210",
        "brn": make_brn("129874563"),
        "mgmt_no": "1298745631-0",
    }
    G["BRN_A_CONFLICT"] = make_brn("402851234")
    G["BRN_A_INVALID"] = make_brn("402856172", valid=False)
    G["STUDENT"] = {
        "name": "최견본",
        "birth": dt.date(2004, 7, 21),
        "university": "가상국립대학교",
        "college": "IT대학",
        "department": "컴퓨터학부",
        "major": "소프트웨어전공",
        "student_id": "2024015432",
        "admission": dt.date(2024, 3, 4),
    }
    G["ALT"].update(
        {
            "student_name": "한샘플",
            "college": "사회과학대학",
            "department": "심리학과",
            "company_near_miss": "온누리샘풀",
        }
    )


def _patch_layouts(L, jitter: float, fonts: bool, tag: str) -> None:
    orig_kv, orig_text, orig_ctext, orig_ph, orig_page = L.kv, L.text, L.ctext, L.ph, L.page
    k = jitter

    def j(a=1.2):
        return _rng.uniform(-a * k, a * k)

    def kv(y, label, value, lx=22, lw=36, vx=None, size=11, cls="", colon=True):
        dy, dx = j(1.0), j(1.5)
        s = size * _rng.uniform(0.96, 1.04)
        vx2 = (vx if vx is not None else lx + lw + 4) + j(0.8)
        return orig_kv(y + dy, label, value, lx=lx + dx, lw=lw, vx=vx2, size=round(s, 2), cls=cls, colon=colon)

    def text(x, y, s, size=10, cls="", raw=False):
        return orig_text(x + j(1.2), y + j(0.8), s, size=round(size * _rng.uniform(0.96, 1.04), 2), cls=cls, raw=raw)

    def ctext(y, s, size=12, cls="", spacing=0, raw=False):
        return orig_ctext(y + j(1.0), s, size=round(size * _rng.uniform(0.97, 1.03), 2), cls=cls, spacing=spacing, raw=raw)

    def ph(x, y, w, h, label):
        if "직인" in label:
            # generic red test stamp, shifted left so it overlaps the issuer text
            d = max(w, h) + 2
            sx, sy = x - d * 0.45 + j(1.5), y + j(1.5)
            return (
                f'<div style="position:absolute;left:{sx:.1f}mm;top:{sy:.1f}mm;width:{d}mm;height:{d}mm;'
                f'border:0.9mm solid rgba(200,30,30,0.72);border-radius:50%;color:rgba(200,30,30,0.72);'
                f'font-weight:bold;text-align:center;font-size:9pt;line-height:4.6mm;'
                f'transform:rotate({_rng.uniform(-14, 14):.1f}deg);display:flex;align-items:center;justify-content:center">'
                f'<div>TEST<br>견본</div></div>'
            )
        return orig_ph(x, y, w, h, label)

    def split_top_divs(s: str) -> list[str]:
        out, depth, start = [], 0, 0
        for m in re.finditer(r"<div\b[^>]*>|</div>", s):
            if m.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    out.append(s[start : m.end()])
                    start = m.end()
            else:
                if depth == 0:
                    if s[start : m.start()].strip():
                        out.append(s[start : m.start()])
                    start = m.start()
                depth += 1
        if s[start:].strip():
            out.append(s[start:])
        return out

    def page(inner: str, doc_tag: str):
        parts = split_top_divs(inner)
        if len("".join(parts)) == len(inner):
            # background emblem stays at the bottom of the drawing order and the
            # stamp on top (as on paper); everything else is stored in random order
            back = [p for p in parts if 'class="wmc"' in p or 'class="wmt"' in p]
            stamp = [p for p in parts if "TEST<br>견본" in p]
            rest = [p for p in parts if p not in back and p not in stamp]
            _rng.shuffle(rest)
            inner = "".join(back + rest + stamp)
        out = orig_page(inner, doc_tag)
        if fonts and _rng.random() < 0.5:
            out = out.replace('<div class="page">', '<div class="page serif">', 1)
        return out

    L.kv, L.text, L.ctext, L.ph, L.page = kv, text, ctext, ph, page
    L.MARK_TEXT = f"TEST SAMPLE · 테스트용 견본 · 법적 효력 없음 · {tag}"


def extra_sets(G: dict, Lc: dict, add_set, ctx, sub) -> None:
    A = G["COMPANY_A"]
    near = dict(A, core=G["ALT"]["company_near_miss"], full=f"주식회사 {G['ALT']['company_near_miss']}")
    transposed = _brn_variant_transposed(A["brn"], G["brn_check_digit"])
    doc_brc, doc_sme, doc_nts, doc_si = G["doc_brc"], G["doc_sme"], G["doc_nts"], G["doc_si"]
    doc_enr_a, doc_tr = G["doc_enr_a"], G["doc_tr"]

    add_set(
        "H13", "near_miss_company_name", "Tax certificate company name differs by one character", "business",
        [doc_brc(ctx, "H13", A), doc_sme(ctx, "H13", A), doc_nts(ctx, "H13", near, brn=A["brn"]), doc_si(ctx, "H13", A)],
        {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["INFORMATION_MISMATCH (company_name)"]},
         "scanned": {"submission_status": "REVIEW_REQUIRED or NEEDS_CORRECTION — never READY", "issue_codes": []}},
        f"{A['core']} vs {near['core']}: one character apart. Must never be treated as a match (no fuzzy matching, no auto-acceptance as 'corroborated').",
    )
    add_set(
        "H14", "transposed_business_number", "Business number on three certificates has two adjacent digits swapped", "business",
        [doc_brc(ctx, "H14", A), doc_sme(ctx, "H14", A, brn=transposed), doc_nts(ctx, "H14", A, brn=transposed), doc_si(ctx, "H14", A, brn=transposed)],
        {"digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["INFORMATION_MISMATCH (business_registration_number)"]},
         "scanned": {"submission_status": "REVIEW_REQUIRED or NEEDS_CORRECTION — never READY", "issue_codes": []}},
        f"Reference {A['brn']} vs {transposed} on the other three (checksum-valid). Three documents agreeing with each other must not outvote the reference.",
    )
    st = G["STUDENT"]
    sid2 = st["student_id"][:-1] + str((int(st["student_id"][-1]) + 1) % 10)
    st2 = dict(st, student_id=sid2)
    G_STUDENT = G["STUDENT"]
    G["STUDENT"] = st2
    tr = doc_tr(ctx, "H15", target=3.80, seed=21)
    G["STUDENT"] = G_STUDENT
    add_set(
        "H15", "student_id_one_digit", "Transcript student number differs by one digit", "student",
        [doc_enr_a(ctx, "H15"), tr],
        {"digital": {"submission_status": "record actual — must not auto-accept student_id as corroborated", "issue_codes": []},
         "scanned": {"submission_status": "REVIEW_REQUIRED", "issue_codes": []}},
        f"{st['student_id']} vs {sid2}. If ADVS uses cross-document agreement to auto-accept OCR values, this pair must NOT count as agreement.",
    )
