"""HTML layouts for ADVS test-variant documents.

Every layout is rebuilt from scratch to mirror the *structure* of a sample
certificate (labels, rows, table shape, positions). No pixel or text from any
original document is reused. All values come from the fictional data passed
in. Authentication features (seals, QR codes, anti-forgery barcodes, logos,
real issuance numbers) are replaced by grey dashed placeholders, and every
page carries a visible "TEST SAMPLE" marking.
"""

from __future__ import annotations

import html

MARK_TEXT = "TEST SAMPLE · 테스트용 견본 · 법적 효력 없음"

CSS = """
body{margin:0;zoom:1.2988;font-family:'Noto Sans CJK KR';color:#161616}
.page{position:relative;width:210mm;height:296.6mm;overflow:hidden;page-break-after:always;background:#fff}
.a{position:absolute;white-space:pre}
.t{position:absolute;left:0;width:210mm;text-align:center;white-space:nowrap}
.ph{position:absolute;border:0.3mm dashed #9c9c9c;background:#f3f3f3;color:#7c7c7c;font-size:7pt;text-align:center;overflow:hidden;white-space:nowrap}
.mark{position:absolute;left:0;width:210mm;bottom:2.2mm;text-align:center;font-size:6.5pt;color:#8a8a8a}
.marktop{position:absolute;right:4mm;top:2.2mm;font-size:6.5pt;color:#8a8a8a}
.serif{font-family:'Noto Serif CJK KR'}
.b{font-weight:bold}
.wmc{position:absolute;border:2.4mm solid #eef0ea;border-radius:50%}
.wmt{position:absolute;color:#e9ece4;font-weight:bold;text-align:center;white-space:nowrap}
table.g{border-collapse:collapse;width:100%}
table.g td{border:0.25mm solid #333;padding:0.7mm 1.4mm;vertical-align:middle}
.c{text-align:center}
.r{text-align:right}
.small{font-size:7pt}
.ct td{padding:0 0.3mm;line-height:3.45mm}
table.g.si td{padding:2.25mm 1.6mm}
.phi{display:inline-block;border:0.3mm dashed #9c9c9c;background:#f3f3f3;color:#7c7c7c;font-size:7pt;width:20mm;height:15mm;line-height:15mm;text-align:center;vertical-align:middle;font-weight:normal}
"""


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def ph(x, y, w, h, label) -> str:
    return (
        f'<div class="ph" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;'
        f'line-height:{h}mm">{esc(label)}</div>'
    )


def mark(doc_tag: str) -> str:
    return (
        f'<div class="mark">{MARK_TEXT} · {esc(doc_tag)}</div>'
        f'<div class="marktop">TEST SAMPLE</div>'
    )


def wm(x, y, d) -> str:
    """Generic faint background emblem (a plain ring), standing in for the
    issuer emblems printed behind real certificates."""
    return (
        f'<div class="wmc" style="left:{x}mm;top:{y}mm;width:{d}mm;height:{d}mm"></div>'
        f'<div class="wmt" style="left:{x}mm;top:{y + d / 2 - 9}mm;width:{d}mm;font-size:30pt">SAMPLE</div>'
    )


def kv(y, label, value, lx=22, lw=36, vx=None, size=11, cls="", colon=True) -> str:
    vx = vx if vx is not None else lx + lw + 4
    out = f'<div class="a {cls}" style="left:{lx}mm;top:{y}mm;font-size:{size}pt">{esc(label)}</div>'
    if colon:
        out += f'<div class="a {cls}" style="left:{lx + lw}mm;top:{y}mm;font-size:{size}pt">:</div>'
    out += f'<div class="a {cls}" style="left:{vx}mm;top:{y}mm;font-size:{size}pt">{esc(value)}</div>'
    return out


def text(x, y, s, size=10, cls="", raw=False) -> str:
    body = s if raw else esc(s)
    return f'<div class="a {cls}" style="left:{x}mm;top:{y}mm;font-size:{size}pt">{body}</div>'


def ctext(y, s, size=12, cls="", spacing=0, raw=False) -> str:
    body = s if raw else esc(s)
    ls = f"letter-spacing:{spacing}mm;" if spacing else ""
    return f'<div class="t {cls}" style="top:{y}mm;font-size:{size}pt;{ls}">{body}</div>'


def page(inner: str, doc_tag: str) -> str:
    return f'<div class="page">{inner}{mark(doc_tag)}</div>'


def document(pages: list[str]) -> str:
    return (
        '<html><head><meta charset="utf-8"><style>'
        + CSS
        + "</style></head><body>"
        + "".join(pages)
        + "</body></html>"
    )


# ---------------------------------------------------------------- business


def business_registration(d: dict) -> str:
    """사업자등록증 (법인사업자) — structure of the sample business registration."""
    s = ph(170, 10, 26, 26, "[QR·로고 생략]")
    s += wm(57, 104, 96)
    s += ctext(22, "사업자등록증", 28, "b", spacing=5)
    s += ctext(39, "( 법인사업자 )", 14)
    s += ctext(48, f"등록번호 : {d['brn_printed']}", 16)
    L = dict(lx=22, lw=36, vx=62, size=11)
    s += kv(66, "법 인 명 ( 단 체 명 )", d["company_printed"], **L)
    s += kv(75, "대        표        자", d["representative"], **L)
    s += kv(87, "개   업   연   월   일", d["opening_date_sp"], **L)
    s += text(118, 87, f"법인등록번호 : {d['corp_reg_no']}", 11)
    s += kv(96, "사 업 장  소 재 지", d["address"], **L)
    s += kv(108, "본   점   소   재   지", d["address"], **L)
    s += kv(122, "사   업   의   종   류", "", **L)
    s += text(62, 122, "업태  " + d["biz_type"], 11)
    s += text(114, 122, "종목  " + d["biz_item"], 11)
    s += text(124.5, 128, d["biz_item2"], 10)
    s += kv(142, "발   급   사   유", d.get("issue_reason", ""), **L)
    s += text(22, 196, "사업자 단위 과세 적용사업자 여부 :  여(  )  부(∨)", 10.5)
    s += text(22, 203, "전자세금계산서 전용 전자우편주소 :", 10.5)
    s += ctext(236, d["issue_date_sp"], 13)
    s += ctext(249, d["issuer"], 20, "b", spacing=3)
    s += ph(146, 236, 24, 24, "[직인 생략]")
    s += ph(14, 268, 182, 19, "[위변조방지 바코드 · 발급기관 로고 생략]")
    return page(s, d["tag"])


def sme_confirmation(d: dict) -> str:
    """중소기업 확인서 — structure of the sample SME confirmation."""
    s = text(20, 14, f"발급번호 : {d['issue_no']}", 11)
    s += ctext(26, "중소기업 확인서", 27)
    s += ctext(41, f"[{d.get('size_class', '중기업')}]", 17)
    L = dict(lx=22, lw=32, vx=58, size=11.5)
    s += kv(62, "기    업    명", d["company_printed"], **L)
    s += kv(73, "사업자등록번호", d["brn_printed"], **L)
    s += text(118, 73, f"법인등록번호 :  {d['corp_reg_no']}", 11.5)
    s += kv(84, "대 표 자 명", d["representative"], **L)
    s += kv(95, "주          소", d["address"], **L)
    s += kv(112, "유 효 기 간", d["validity_printed"], **L)
    s += kv(123, "용          도", "공공기관 입찰 이외 용도", **L)
    s += text(26, 141, "위 기업은 「중소기업기본법」 제2조에 의한 중소기업임을 확인합니다.", 11.5)
    s += ctext(196, d["issue_date_kr"], 13)
    s += ctext(210, "중소벤처기업부장관", 19, "b")
    s += ph(146, 199, 24, 24, "[직인 생략]")
    notes = (
        "발급사실 및 발급취소 등 변동사항은 중소기업현황정보시스템에서 확인할 수 있습니다.<br>"
        "유효기간 중이라도 발급일 이후 합병·분할 등으로 기업 규모가 바뀌면 중소기업 지위를 잃을 수 있습니다.<br>"
        "거짓으로 확인을 받은 경우 관계 법령에 따라 과태료 처분 및 지원 취소 등의 조치를 받을 수 있습니다."
    )
    s += (
        '<div class="a" style="left:20mm;top:234mm;width:166mm;border:0.25mm solid #555;'
        f'padding:3mm 2mm;font-size:8pt;line-height:4.6mm;white-space:normal">{notes}</div>'
    )
    return page(s, d["tag"])


def tax_payment(d: dict) -> str:
    """납세증명서 — structure of the sample national-tax payment certificate.
    With d['local_tax'] the same structure is retitled as a local-tax
    certificate (look-alike test)."""
    local = d.get("local_tax", False)
    title = "지방세 납세증명서" if local else "납세증명서"
    law = "「지방세징수법」" if local else "「국세징수법」"
    law_dec = "「지방세징수법 시행령」" if local else "「국세징수법 시행령」"
    s = ph(22, 11, 18, 18, "[QR 생략]")
    s += text(22, 32, "( 1 / 1 )", 9, "serif")
    s += ph(166, 9, 24, 24, "[로고 생략]")
    s += wm(62, 112, 86)
    s += ctext(36, title, 23, "serif b", spacing=3.5)
    tds = 'style="font-size:9pt"'
    t1 = (
        '<table class="g serif" ' + tds + '><tr>'
        '<td style="width:26mm">발급번호</td>'
        f'<td style="width:66mm">{esc(d["issue_no"])}</td>'
        '<td style="width:22mm">처리기간</td>'
        '<td>즉시(단, 해외이주용 10일)</td></tr></table>'
    )
    t2 = (
        '<table class="g serif" ' + tds + ' style="margin-top:-0.25mm"><tr>'
        '<td rowspan="2" class="c" style="width:22mm">납세자<br>인적사항</td>'
        '<td style="width:24mm">성명(상호)</td>'
        f'<td style="width:54mm">{esc(d["company_printed"])}</td>'
        '<td style="width:30mm">주민등록번호<br>(사업자등록번호)</td>'
        f'<td>{esc(d["brn_printed"])}</td></tr>'
        '<tr><td>주소(사업장)</td>'
        f'<td colspan="3">{esc(d["address"])}</td></tr></table>'
    )
    t3 = (
        '<table class="g serif" ' + tds + ' style="margin-top:-0.25mm"><tr>'
        '<td class="c" style="width:22mm">증명서의<br>사용목적</td>'
        '<td style="line-height:5.2mm">☑ 대금수령<br>'
        '☐ 해외이주 (이주번호 제 &nbsp;&nbsp;&nbsp;&nbsp; 호, 이주확인일 &nbsp;&nbsp; 년 &nbsp; 월 &nbsp; 일)<br>'
        '☐ 기 타</td></tr></table>'
    )
    t4 = (
        '<table class="g serif" ' + tds + ' style="margin-top:-0.25mm"><tr>'
        '<td rowspan="2" class="c" style="width:22mm">증명서의<br>유효기간</td>'
        '<td style="width:30mm">유효기간</td>'
        f'<td>{esc(d["valid_until_sp"])}</td></tr>'
        '<tr><td>유효기간을<br>정한 사유</td>'
        f'<td>☑ {law_dec} 제96조 제1항<br>☐ 기 타 (사유: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; )</td></tr></table>'
    )

    def none_table(label, headers):
        widths = [26, 22, 18, 18, 20, 22, 22]
        head = "".join(
            f'<td class="c" style="width:{w}mm;font-size:8pt">{h}</td>'
            for w, h in zip(widths, headers)
        )
        first = (
            '<td></td><td class="c">해</td><td class="c">당</td><td class="c">없</td>'
            '<td class="c">음</td><td></td><td></td>'
        )
        empty = "<td>&nbsp;</td>" * 7
        return (
            '<table class="g serif" ' + tds + ' style="margin-top:-0.25mm">'
            f'<tr><td rowspan="4" class="c" style="width:22mm;font-size:8pt">{label}</td>{head}</tr>'
            f"<tr>{first}</tr><tr>{empty}</tr><tr>{empty}</tr></table>"
        )

    t5 = none_table(
        "연장·유예<br>내역<br><br>(단위 : 원)",
        ["연장·유예<br>종류", "연장·유예<br>기간", "과세기간", "세 목", "납부기한", "세 액", "가산금"],
    )
    t6 = none_table(
        "물적납세의무<br>체납내역<br><br>(단위 : 원)",
        ["위탁자·양도<br>담보설정자", "", "과세기간", "세 목", "납부기한", "세 액", "가산금"],
    )
    stmt = (
        f'<div class="serif" style="margin-top:4mm;font-size:9pt;line-height:5mm;padding:0 3mm">'
        f"{law} 제108조 및 같은 법 시행령 제95조에 따라 발급일 현재 위의 연장·유예액 또는 "
        "물적납세의무와 관련된 체납액을 제외하고는 다른 체납액이 없음을 증명합니다.<br>"
        "※ 발급일 현재 납부기한이 도래하지 않은 미납 세액은 체납액이 아니므로 증명 대상에서 제외됨.</div>"
    )
    bottom = (
        '<table style="width:100%;margin-top:4mm;border-collapse:collapse"><tr>'
        '<td style="width:74mm;vertical-align:top">'
        '<table class="g serif" ' + tds + '>'
        f'<tr><td style="width:20mm">접수번호</td><td>{esc(d["receipt_no"])}</td></tr>'
        '<tr><td>담당부서</td><td>민원봉사실</td></tr>'
        '<tr><td>담 당 자</td><td>&nbsp;</td></tr>'
        '<tr><td>연 락 처</td><td>000-000-0000</td></tr></table></td>'
        '<td class="serif" style="text-align:center;vertical-align:middle;position:relative">'
        f'<div style="font-size:12pt">{esc(d["issue_date_sp"])}</div>'
        f'<div style="font-size:15pt;font-weight:bold;margin-top:7mm;letter-spacing:1.5mm">{esc(d["issuer"])}</div>'
        "</td></tr></table>"
    )
    body = t1 + t2 + t3 + t4 + t5 + t6 + stmt + bottom
    s += f'<div class="a" style="left:20mm;top:50mm;width:170mm;white-space:normal">{body}</div>'
    s += ph(160, 216, 22, 22, "[직인 생략]")
    s += ph(20, 250, 170, 18, "[위변조방지 바코드 · 발급기관 로고 생략]")
    s += text(20, 271, "※ 이 문서는 테스트용 견본으로 진위확인 기능이 없습니다.", 7.5, "serif")
    s += text(20, 275.5, "※ 공문서를 위·변조하거나 행사하는 행위는 법에 따라 처벌될 수 있습니다.", 7.5, "serif b")
    return page(s, d["tag"])


def social_insurance(d: dict) -> str:
    """고용·산재보험료 완납 증명원 — structure of the sample social-insurance
    payment certificate. d['validity_row'] adds a 유효기간 row (absent in the
    original structure; added so ADVS's valid_until field has a source)."""
    s = wm(58, 118, 92)
    rows = []
    rows.append(
        '<tr style="height:17mm"><td class="c" style="width:34mm">발 급 번 호</td>'
        '<td colspan="5"><span style="font-size:14pt;font-weight:bold;line-height:7mm">'
        "☑ 고용보험료<br>☑ 산재보험료</span>"
        '<span style="font-size:19pt;font-weight:bold;margin-left:22mm;position:relative;top:-3mm">'
        "완납 증명원</span></td></tr>"
    )
    rows.append(
        '<tr><td class="c">발 급 기 준</td><td colspan="5">☑ 사업장관리번호'
        " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ☐ 법인등록번호 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ☐ 사업자등록번호</td></tr>"
    )
    rows.append(f'<tr><td class="c">사 업 장 명</td><td colspan="5">{esc(d["workplace_printed"])}</td></tr>')
    rows.append('<tr><td class="c">건설공사명</td><td colspan="5">-</td></tr>')
    rows.append(f'<tr><td class="c">소 재 지</td><td colspan="5">{esc(d["address"])}</td></tr>')
    rows.append(
        '<tr><td class="c">보험가입자(대표자)</td>'
        f'<td colspan="2">{esc(d["representative"])}</td>'
        '<td class="c" style="width:34mm">주민등록번호</td>'
        f'<td colspan="2">{esc(d["rrn_masked"])}</td></tr>'
    )
    rows.append(
        '<tr><td class="c">사업자등록번호<br>(법인등록번호)</td>'
        f'<td colspan="2">{esc(d["brn_printed"])}</td>'
        '<td class="c">사업장관리번호<br>(사업개시번호)</td>'
        f'<td colspan="2">{esc(d["mgmt_no"])}</td></tr>'
    )
    rows.append(
        '<tr><td rowspan="2" class="c">보험성립일</td>'
        f'<td class="c" style="width:14mm">고용</td><td style="width:36mm">{esc(d["insured_since"])}</td>'
        '<td rowspan="2" class="c">보험소멸일</td><td class="c" style="width:14mm">고용</td><td>-</td></tr>'
    )
    rows.append(
        f'<tr><td class="c">산재</td><td>{esc(d["insured_since"])}</td><td class="c">산재</td><td>-</td></tr>'
    )
    rows.append(
        '<tr><td rowspan="2" class="c">사 업 의 종 류</td><td class="c">고용</td>'
        '<td colspan="4">62010 &nbsp;&nbsp; 소프트웨어 개발 및 공급업</td></tr>'
    )
    rows.append(
        '<tr><td class="c">산재</td><td colspan="4">62010 &nbsp;&nbsp; 소프트웨어 개발 및 공급업</td></tr>'
    )
    rows.append(
        '<tr><td class="c">사업개시번호</td><td colspan="2" class="c">사업개시일</td>'
        '<td colspan="3" class="c">사업개시(공사)명</td></tr>'
    )
    rows.append(
        f'<tr><td class="c">001</td><td colspan="2" class="c">{esc(d["insured_since"])}</td>'
        f'<td colspan="3">{esc(d["workplace_printed"])} 본사</td></tr>'
    )
    rows.append('<tr><td>&nbsp;</td><td colspan="2"></td><td colspan="3"></td></tr>')
    rows.append(
        '<tr><td rowspan="2" class="c">징수유예 내역</td><td colspan="2" class="c">금액</td>'
        '<td colspan="3" class="r">원</td></tr>'
    )
    rows.append('<tr><td colspan="2" class="c">유예기간</td><td colspan="3" class="c">~</td></tr>')
    rows.append(
        '<tr><td class="c">용 &nbsp;&nbsp;&nbsp; 도</td><td colspan="2">기타 (제출용)</td>'
        '<td class="c">제출기관</td><td colspan="2">기타 (샘플 제출용)</td></tr>'
    )
    if d.get("validity_row", True):
        rows.append(
            f'<tr><td class="c">유 효 기 간</td><td colspan="5">{esc(d["valid_until_kr"])} 까지</td></tr>'
        )
    rows.append(
        '<tr><td colspan="6" class="c" style="line-height:7.5mm;padding:2mm">'
        "완납 증명원 발급일 현재 징수유예액을 제외하고는 체납액이 없음을 증명하여 주시기 바랍니다<br>"
        f"{esc(d['issue_date_kr'])}<br>"
        f"신청인: &nbsp;&nbsp;&nbsp;&nbsp; {esc(d['representative'])} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (서명 또는 인)<br>"
        '<span style="font-size:15pt;font-weight:bold">근로복지공단 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 귀하</span></td></tr>'
    )
    rows.append(
        '<tr><td colspan="6" class="c" style="line-height:7mm;padding:2mm">'
        "위와 같이 증명합니다.<br>"
        "※ 이 증명원은 납부기한이 도래하지 않은 보험료의 수납여부를 증명하지 않습니다.<br>"
        f"{esc(d['issue_date_kr'])}<br>"
        '<span style="font-size:15pt;font-weight:bold">근로복지공단</span>'
        '<span class="phi" style="margin-left:8mm">[직인 생략]</span></td></tr>'
    )
    table = '<table class="g si" style="font-size:9.8pt">' + "".join(rows) + "</table>"
    s += f'<div class="a" style="left:18mm;top:10mm;width:174mm;white-space:normal">{table}</div>'
    s += ctext(285, "이 출력물은 개인정보 보호 관련 법령에 따라 비밀이 보장되어야 하는 자료입니다.", 8)
    return page(s, d["tag"])


# ---------------------------------------------------------------- student


def enrollment_type_a(d: dict) -> str:
    """재학증명서 layout A — the sample with 학번 and 재학기간 rows.
    d['title'] lets the same structure be retitled (휴학/졸업예정 look-alikes)."""
    title = d.get("title", "재학증명서")
    s = text(20, 14, f"제 {d['issue_no']} 호", 13)
    s += ph(176, 8, 24, 24, "[로고 생략]")
    s += wm(70, 100, 70)
    s += ctext(48, title, 27, spacing=8)
    L = dict(lx=40, lw=38, vx=82, size=13)
    s += kv(92, "성           명", d["student_name"], **L)
    s += kv(101, "생  년  월  일", d["birth_kr"], **L)
    s += kv(110, "소           속", f"{d['college']} {d['department']}", **L)
    s += kv(119, "학           번", d["student_id"], **L)
    s += kv(128, "학  년 (학기)", d["year_term"], **L)
    period_label = d.get("period_label", "재  학  기  간")
    s += kv(137, period_label, d["period_line1"], **L)
    if d.get("period_line2"):
        s += text(82, 145, d["period_line2"], 13)
    s += ctext(164, "위의 내용을 증명합니다.", 15, spacing=1.5)
    s += ctext(186, d.get("issue_date_kr", ""), 14)
    s += ctext(214, d["university"], 22, spacing=1)
    s += ph(146, 205, 26, 26, "[직인 생략]")
    s += text(
        16, 251, "[인터넷 발급] 이 문서는 테스트용 견본이므로 원본대조 및 진위확인을 할 수 없습니다.", 7
    )
    s += ph(16, 256, 140, 20, "[위변조방지 바코드 생략]")
    s += ph(160, 256, 22, 20, "[QR 생략]")
    s += text(16, 278, f"(Internet no) {d['internet_no']}", 9)
    return page(s, d["tag"])


def enrollment_type_b(d: dict) -> str:
    """재학증명서 layout B — the bordered sample with 전공/복수전공 rows and no
    student-number row."""
    s = (
        '<div class="a" style="left:10mm;top:12mm;width:190mm;height:252mm;'
        'border:0.4mm solid #222"></div>'
    )
    s += text(16, 22, f"제 {d['issue_no']} 호", 12)
    s += ctext(38, d.get("title", "재학증명서"), 24, spacing=13)
    L = dict(lx=40, lw=38, vx=80, size=12)
    s += kv(82, "성           명", d["student_name"], **L)
    s += kv(92, "생   년   월   일", d["birth_kr_nz"], **L)
    s += kv(102, "소           속", f"{d['college']} {d['department']}", **L)
    s += kv(112, "전           공", d["major"], **L)
    s += kv(122, "입   학   일   자", d["admission_kr_nz"], **L)
    s += kv(132, "재   학   학   년", d["year_only"], **L)
    s += kv(142, "복   수   전   공", d.get("double_major", "-"), **L)
    s += ctext(196, "위의 사실을 증명합니다.", 14, spacing=1)
    s += ctext(206, d.get("issue_date_kr_nz", ""), 12)
    s += ctext(216, " ".join(d["university"] + "총장"), 22, "b", spacing=2.5)
    s += ph(154, 205, 24, 24, "[직인 생략]")
    s += text(
        12, 266, "[인터넷 발급] 이 문서는 테스트용 견본이므로 원본대조 및 진위확인을 할 수 없습니다.", 6.5
    )
    s += ph(12, 271, 150, 15, "[위변조방지 바코드 생략]")
    s += ph(166, 269, 22, 18, "[QR 생략]")
    s += text(12, 288, f"(internet no) {d['internet_no']}", 8)
    return page(s, d["tag"])


def _course_columns(d, max_lines=46):
    lines = []
    for term in d["terms"]:
        lines.append(("term", f"<<{term['label']}>>"))
        for c in term["courses"]:
            lines.append(("course", c))
        lines.append(("sum", f"취득학점: {term['credits']}"))
        lines.append(("sum", f"평점평균: {term['gpa_str']}/{d['scale_str']} 백분율: {term['pct']}/100"))
        lines.append(("sep", ""))
    lines.append(("sum", f"총 취득학점: {d['total_credits']}"))
    lines.append(("sum", f"평점평균: {d['gpa_printed']}/{d['scale_str']} 백분율: {d['pct']}/100"))
    cols = [lines[i : i + max_lines] for i in range(0, len(lines), max_lines)]
    return cols[:3]


def _render_col(col):
    out = ['<table class="ct" style="border-collapse:collapse;width:100%;font-size:7.4pt">']
    for kind, val in col:
        if kind == "term":
            out.append(f'<tr><td colspan="4" class="c">{esc(val)}</td></tr>')
        elif kind == "course":
            cat, name, cr, gr = val
            out.append(
                f'<tr><td style="width:7mm">{esc(cat)}</td><td>{esc(name)}</td>'
                f'<td style="width:5mm" class="r">{cr}</td><td style="width:8mm;padding-left:2mm">{esc(gr)}</td></tr>'
            )
        elif kind == "sum":
            out.append(f'<tr><td colspan="4" class="c">{esc(val)}</td></tr>')
        else:
            out.append('<tr><td colspan="4" class="c" style="color:#777">--------------------------------</td></tr>')
    out.append("</table>")
    return "".join(out)


def transcript_type_a(d: dict) -> str:
    """성적증명서 layout A — dense three-column transcript (sample structure)."""
    s = text(10, 17, f"제 {d['issue_no']} 호", 8.5)
    s += ctext(6, "성 적 증 명 서", 24, "b", spacing=6)
    head = (
        '<table style="width:100%;border-collapse:collapse;font-size:8pt;line-height:4mm">'
        f'<tr><td style="width:88mm">소 &nbsp;&nbsp; 속 : {esc(d["college"])} {esc(d["department"])}</td>'
        f'<td style="width:55mm">학 &nbsp;&nbsp; 번 : {esc(d["student_id"])}</td>'
        f'<td>입학일자 : {esc(d["admission_kr_nz"])}</td></tr>'
        f'<tr><td>생년월일 : {esc(d["birth_kr_nz"])}</td><td>성 &nbsp;&nbsp; 명 : {esc(d["student_name"])}</td><td></td></tr>'
        '<tr><td>복수전공 : *****</td><td>부전공 : *****</td><td></td></tr></table>'
    )
    s += (
        '<div class="a" style="left:8mm;top:23mm;width:192mm;border:0.25mm solid #333;'
        f'border-bottom:none;padding:0.5mm 1mm;white-space:normal">{head}</div>'
    )
    cols = _course_columns(d)
    hdr = (
        '<table style="width:100%;border-collapse:collapse;font-size:8pt"><tr>'
        '<td style="width:7mm">구분</td><td class="c">이 수 과 목</td><td style="width:15mm">학점 성적</td></tr></table>'
    )
    grid = '<table style="width:194mm;border-collapse:collapse;table-layout:fixed"><tr>'
    for _ in range(3):
        grid += f'<td style="border:0.25mm solid #333;padding:0 1mm">{hdr}</td>'
    grid += "</tr><tr>"
    for i in range(3):
        col = cols[i] if i < len(cols) else []
        grid += (
            '<td style="border:0.25mm solid #333;vertical-align:top;height:170mm;padding:0.5mm 1mm">'
            f"{_render_col(col)}</td>"
        )
    grid += "</tr></table>"
    s += f'<div class="a" style="left:8mm;top:39mm;white-space:normal">{grid}</div>'
    cats = ["교과구분", "교양", "전공", "복수", "융합", "연계", "부전", "마크", "일선", "자선", "교직", "공학", "전반", "전교", "전기", "전심"]
    vals = ["이수학점"] + [str(v) for v in d["credit_split"]] + ["0"] * (len(cats) - 1 - len(d["credit_split"]))
    ct = '<table class="g" style="font-size:7pt;width:194mm"><tr>' + "".join(f'<td class="c">{c}</td>' for c in cats) + "</tr><tr>"
    ct += "".join(f'<td class="c">{v}</td>' for v in vals) + "</tr></table>"
    s += f'<div class="a" style="left:8mm;top:218mm;white-space:normal">{ct}</div>'
    s += text(8, 228, "교양: 교양, 전공: 전공, 복수: 복수전공, 융합: 융합전공, 연계: 연계전공, 부전: 부전공, 일선: 일반선택, 자선: 자유선택", 6.3)
    s += text(8, 233, d["legend"], 6.3)
    s += (
        '<div class="a" style="left:8mm;top:238mm;width:194mm;height:28mm;border:0.25mm solid #333"></div>'
    )
    s += ctext(240, "위의 사실을 증명합니다.", 12, "b", spacing=1)
    s += ctext(247, d.get("issue_date_kr", ""), 10)
    s += ctext(253, " ".join(d["university"] + "총장"), 22, "b")
    s += ph(160, 241, 24, 24, "[직인 생략]")
    s += text(8, 268, "※ 본 문서는 테스트용 견본이며 원본대조 및 진위확인을 할 수 없습니다.", 7.5)
    s += ph(8, 273, 160, 13, "[위변조방지 바코드 생략]")
    s += ph(172, 271, 22, 17, "[QR 생략]")
    s += text(8, 288, f"(internet no) {d['internet_no']}", 8)
    return page(s, d["tag"])


def transcript_type_b(d: dict) -> str:
    """성적증명서 layout B — older table-header transcript where the overall GPA
    sits in a header/value table cell ("총평점평균") rather than a labelled line."""
    s = ctext(8, "성 적 증 명 서", 24, "serif b", spacing=7)
    td = 'style="font-size:7.5pt"'
    head = (
        '<table class="g" ' + td + '>'
        f'<tr><td class="c" style="width:14mm">학 번</td><td style="width:26mm">{esc(d["student_id"])}</td>'
        f'<td class="c" style="width:12mm">성명</td><td style="width:26mm">{esc(d["student_name"])}</td>'
        '<td class="c" style="width:20mm">주민등록번호</td><td style="width:30mm">'
        f'{esc(d["rrn_masked"])}</td>'
        f'<td class="c" style="width:14mm">입학일</td><td>{esc(d["admission_iso_slash"])}</td></tr>'
        f'<tr><td class="c">대학/학과</td><td colspan="3">{esc(d["college"])} {esc(d["department"])}</td>'
        '<td class="c">학위등록번호</td><td></td><td class="c">졸업일</td><td></td></tr></table>'
    )
    summary = (
        '<table class="g" ' + td + ' style="margin-top:-0.25mm"><tr>'
        '<td rowspan="2" class="c" style="width:14mm">취득<br>학점</td>'
        + "".join(
            f'<td class="c">{h}</td>'
            for h in ["교양", "전공", "부전공", "복수전공", "일반", "총취득학점", "총평점", "총평점평균", "백분율환산"]
        )
        + "</tr><tr>"
        + "".join(
            f'<td class="c">{esc(v)}</td>'
            for v in [
                d["credit_split"][0],
                d["credit_split"][1],
                "-",
                d["credit_split"][2],
                "0.0",
                d["total_credits"],
                d["total_points"],
                f"{d['gpa_printed']} / {d['scale_str']}",
                f"{d['pct']} / 100",
            ]
        )
        + "</tr></table>"
    )
    s += f'<div class="a" style="left:8mm;top:20mm;width:194mm;white-space:normal">{head}{summary}</div>'
    cols = _course_columns(d, max_lines=44)
    grid = '<table style="width:194mm;border-collapse:collapse;table-layout:fixed"><tr>'
    for i in range(3):
        col = cols[i] if i < len(cols) else []
        grid += (
            '<td style="border:0.25mm solid #333;vertical-align:top;height:162mm;padding:0.5mm 1mm">'
            f"{_render_col(col)}</td>"
        )
    grid += "</tr></table>"
    s += f'<div class="a" style="left:8mm;top:44mm;white-space:normal">{grid}</div>'
    s += text(120, 222, f"제 {d['issue_no']} 호", 10, "serif")
    s += text(120, 229, "위의 사실을 증명합니다.", 11, "serif")
    s += text(124, 238, d.get("issue_date_kr", ""), 10, "serif")
    s += text(112, 248, d["university"] + " 총장", 18, "serif b")
    s += ph(174, 240, 22, 22, "[직인 생략]")
    s += text(8, 266, "[평가기준] " + d["legend"], 6.5)
    s += ph(8, 271, 160, 14, "[위변조방지 바코드 생략]")
    s += ph(172, 270, 22, 17, "[QR 생략]")
    s += text(8, 288, f"(Internet no) {d['internet_no']}", 8)
    return page(s, d["tag"])


def notice_page(d: dict) -> str:
    """An unrelated, non-certificate page used for multi-page tests."""
    s = ctext(30, "제출 서류 안내문", 22, "b")
    lines = [
        "1. 이 페이지는 증명서가 아닌 일반 안내문입니다.",
        "2. 제출 서류는 발급일로부터 정해진 기간 이내의 것이어야 합니다.",
        "3. 서류의 기재 내용이 서로 다를 경우 보완을 요청할 수 있습니다.",
        "4. 문의: 테스트 담당 부서",
    ]
    for i, ln in enumerate(lines):
        s += text(28, 60 + i * 10, ln, 12)
    return page(s, d["tag"])


def blank_page(d: dict) -> str:
    return page("", d["tag"])


LAYOUTS = {
    "business_registration": business_registration,
    "sme_confirmation": sme_confirmation,
    "tax_payment": tax_payment,
    "social_insurance": social_insurance,
    "enrollment_a": enrollment_type_a,
    "enrollment_b": enrollment_type_b,
    "transcript_a": transcript_type_a,
    "transcript_b": transcript_type_b,
    "notice": notice_page,
    "blank": blank_page,
}
