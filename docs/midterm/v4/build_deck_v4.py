"""Builds docs/midterm/v4/ADVS_1차중간발표.pptx (16:9, visual, results-first).

Every number on a slide comes from a repository file; the table of sources is SOURCES below and is written to
slides_sources.md. Screenshots come from docs/midterm/v4/screenshots (1920x1080 @2x). Native shapes and native charts only.
"""
import json
import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

REPO = Path("/Users/admin/Documents/ADVS")
V4 = REPO / "docs/midterm/v4"
SHOTS = V4 / "screenshots"
TMP = Path("/private/tmp/claude-501/-Users-admin-Documents-ADVS/5e11d9dd-b231-440f-8432-92dc4b35dec2/scratchpad/v4/img")
TMP.mkdir(parents=True, exist_ok=True)
OUT = V4 / "ADVS_1차중간발표.pptx"

FONT = "Apple SD Gothic Neo"
LATIN = "Helvetica Neue"
NAVY = RGBColor(0x17, 0x32, 0x5C)      # accent
INK = RGBColor(0x1B, 0x24, 0x33)
MUTED = RGBColor(0x4A, 0x58, 0x72)
LINE = RGBColor(0xC9, 0xD2, 0xE0)
BG = RGBColor(0xF3, 0xF6, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN_BG, GREEN_TX = RGBColor(0xE3, 0xF5, 0xEC), RGBColor(0x0B, 0x5D, 0x3B)
AMBER_BG, AMBER_TX = RGBColor(0xFF, 0xF1, 0xCC), RGBColor(0x6B, 0x43, 0x00)
RED_BG, RED_TX = RGBColor(0xFC, 0xE8, 0xE6), RGBColor(0x8C, 0x1D, 0x18)
GREY_BAR = RGBColor(0xD3, 0xDA, 0xE6)

SW, SH = 13.333, 7.5
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
BLANK = prs.slide_layouts[6]
count = 0
BODY_WORDS: dict[int, int] = {}
SOURCES: list[tuple] = []   # (slide, claim, file, where)
CRITERIA: dict[int, list[int]] = {1: [], 2: [], 3: [], 4: [], 5: []}


def _style(run, size, bold=False, color=INK):
    run.font.size, run.font.bold, run.font.name = Pt(size), bold, LATIN
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    for tag in ("a:ea", "a:cs"):
        el = OxmlElement(tag)
        el.set("typeface", FONT)
        latin.addnext(el)


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, fill=None, line=None, margin=0.0, shape=None, align=None,
         kind="label", lw=1.25, radius=0.08):
    """paras: list of dicts {t,size,bold,color,bullet,align,space}. kind='body' counts toward the word budget."""
    if shape is None:
        shp = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    else:
        shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        shp.shadow.inherit = False
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            shp.adjustments[0] = radius
    if fill is not None:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    elif shape is not None:
        shp.fill.background()
    if line is not None:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
    elif shape is not None:
        shp.line.fill.background()
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(margin * 0.6)
    first = True
    for p in paras:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.alignment = p.get("align", align) or PP_ALIGN.LEFT
        if "space" in p:
            para.space_before = Pt(p["space"])
        para.line_spacing = p.get("ls", 1.05)
        run = para.add_run()
        run.text = p["t"]
        _style(run, p.get("size", 18), p.get("bold", False), p.get("color", INK))
        if kind == "body":
            BODY_WORDS[count] = BODY_WORDS.get(count, 0) + len(p["t"].split())
    return shp


def new_slide(title, number=True, size=28, criteria=()):
    global count
    count += 1
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.2), prs.slide_height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    bar.shadow.inherit = False
    if title:
        text(s, 0.6, 0.32, 12.2, 0.95, [{"t": title, "size": size, "bold": True, "color": NAVY, "ls": 1.0}])
    if number and count > 1:
        text(s, 12.1, 7.05, 0.8, 0.32, [{"t": str(count), "size": 12, "color": MUTED, "align": PP_ALIGN.RIGHT}])
        text(s, 0.6, 7.05, 7, 0.32, [{"t": "ADVS · 1차 중간발표 · 2026-10-15", "size": 12, "color": MUTED}])
    for c in criteria:
        CRITERIA[c].append(count)
    return s


def notes(slide, seconds, star, ko, en):
    tf = slide.notes_slide.notes_text_frame
    tf.text = f"{'★ ' if star else ''}목표 시간 {seconds}초\n\n{ko}\n\n[English] {en}"


def src(claim, file, where):
    SOURCES.append((count, claim, file, where))


def box(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.25, radius=0.08):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    if fill is not None:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    else:
        shp.fill.background()
    if line is not None:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
    else:
        shp.line.fill.background()
    return shp


def arrow_line(slide, x1, y1, x2, y2, color=NAVY, width=2.25, head=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if head:
        ln = c.line._get_or_add_ln()
        tail = OxmlElement("a:tailEnd")
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
        ln.append(tail)
    return c


def block_arrow(slide, x, y, w=0.5, h=0.4, color=MUTED):
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid()
    a.fill.fore_color.rgb = color
    a.line.fill.background()
    a.shadow.inherit = False
    return a


def chip(slide, x, y, w, label, fill, tx, size=18, h=0.5):
    return text(slide, x, y, w, h, [{"t": label, "size": size, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}],
                anchor=MSO_ANCHOR.MIDDLE, fill=fill, line=tx, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.06, radius=0.3)


def num_circle(slide, n, cx, cy, d=0.44):
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - d / 2), Inches(cy - d / 2), Inches(d), Inches(d))
    c.fill.solid()
    c.fill.fore_color.rgb = NAVY
    c.line.color.rgb = WHITE
    c.line.width = Pt(2)
    c.shadow.inherit = False
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    _style(r, 16, True, WHITE)
    return c


# ------------------------------------------------------------------ screenshots
def prep_image(name, crop):
    """crop = (x, y, w, h) in CSS px of the 1920x1080 viewport; the PNG is 2x. Returns the JPEG path."""
    x, y, w, h = crop
    im = Image.open(SHOTS / f"{name}.png").convert("RGB").crop((x * 2, y * 2, (x + w) * 2, (y + h) * 2))
    p = TMP / f"{name}_{x}_{y}_{w}.jpg"
    im.save(p, quality=90, optimize=True)
    return p


def shot_slide(title, name, crop, callouts, criteria, seconds, star, ko, en, width=11.3, y0=1.2):
    """One big screenshot (>= 85 % of the slide width) and 2-3 numbered callouts.
    callouts: (n, label, (tx, ty) target in viewport px, (lx, ly) label top-left in viewport px, label width in px)."""
    s = new_slide(title, criteria=criteria)
    cx, cy, cw, ch = crop
    k = width / cw
    x0 = (SW - width) / 2
    pic = s.shapes.add_picture(str(prep_image(name, crop)), Inches(x0), Inches(y0), width=Inches(width))
    pic.line.color.rgb = LINE
    pic.line.width = Pt(1)
    f = lambda px, py: (x0 + (px - cx) * k, y0 + (py - cy) * k)
    for n, label, (tx, ty), (lx, ly), lwpx in callouts:
        tX, tY = f(tx, ty)
        lX, lY = f(lx, ly)
        wi = lwpx * k
        hh = 0.46
        lab = text(s, lX, lY, wi, hh, [{"t": label, "size": 16, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER}],
                   anchor=MSO_ANCHOR.MIDDLE, fill=WHITE, line=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.05, lw=2, radius=0.25)
        # arrow from the nearest edge of the label to the target
        ax = lX if tX < lX else (lX + wi if tX > lX + wi else tX)
        ay = lY + hh / 2 if (tX < lX or tX > lX + wi) else (lY if tY < lY else lY + hh)
        arrow_line(s, ax, ay, tX, tY)
        num_circle(s, n, tX, tY)
    notes(s, seconds, star, ko, en)
    return s


# ====================================================================== SLIDES
# ---- 1 title
s = new_slide(None, number=False)
box(s, 0, 0, SW, SH, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.9, 0.9, 11.5, 0.5, [{"t": "KNU 종합설계프로젝트 1 · 플래시21 · 1차 중간발표", "size": 20, "color": RGBColor(0xC7, 0xD3, 0xE8)}])
text(s, 0.9, 1.7, 11.8, 2.3, [{"t": "AI 기반 행정 제출서류", "size": 44, "bold": True, "color": WHITE, "ls": 1.0},
                              {"t": "분석 및 자동 점검 시스템 (ADVS)", "size": 44, "bold": True, "color": WHITE, "ls": 1.0}])
text(s, 0.9, 4.15, 11.5, 0.6, [{"t": "제출 전에, 설정된 기준으로, 근거와 함께 점검합니다", "size": 24, "color": WHITE}])
text(s, 0.9, 5.15, 11.5, 1.5, [
    {"t": "팀 올림조노바 무니라 · 굴로모프 하비빌로", "size": 22, "color": WHITE},
    {"t": "멘토 이현지 (플래시21)   지도교수 김동균", "size": 22, "color": WHITE, "space": 6},
    {"t": "2026년 10월 15일", "size": 20, "color": RGBColor(0xC7, 0xD3, 0xE8), "space": 6}])
src("Team, mentor, professor names; date", "docs/midterm/slides_sources.md (v3 deck), course brief", "slide 1 row")
notes(s, 10, True, "ADVS는 행정 서류를 제출하기 전에 점검하는 시스템입니다. 오늘은 만든 것, 결과, 그리고 어떻게 달성했는지를 화면으로 보여 드리겠습니다.",
      "ADVS checks administrative documents before submission; today: what we built, the results and how we got them.")

# ---- 2 problem
s = new_slide("서류 제출은 반복적이고 실수가 잦습니다", criteria=())
# a pile of documents on the left
for i, (dx, dy) in enumerate([(0.0, 0.0), (0.25, 0.2), (0.5, 0.4), (0.75, 0.6)]):
    d = box(s, 1.0 + dx, 2.3 + dy, 1.9, 2.6, fill=WHITE if i < 3 else BG, line=MUTED, shape=MSO_SHAPE.RECTANGLE, lw=1.5)
    for r in range(5):
        box(s, 1.2 + dx, 2.7 + dy + r * 0.38, 1.4 - (r % 2) * 0.4, 0.1, fill=GREY_BAR, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.9, 5.7, 3.4, 0.5, [{"t": "제출 서류 더미", "size": 18, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER}])
block_arrow(s, 4.35, 3.5, 0.9, 0.7)
problems = [("누락", "필수 서류가 빠짐"), ("만료", "유효기간이 지남"), ("불일치", "서류마다 회사명이 다름"),
            ("중복", "같은 서류를 두 번"), ("유사 서류", "비슷하지만 다른 서류")]
y = 1.5
for name, sub in problems:
    box(s, 5.5, y, 7.1, 0.76, fill=AMBER_BG, line=AMBER_TX)
    text(s, 5.7, y, 2.1, 0.76, [{"t": "⚠ " + name, "size": 24, "bold": True, "color": AMBER_TX}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 7.9, y, 4.6, 0.76, [{"t": sub, "size": 20, "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.9
text(s, 0.9, 6.3, 11.8, 0.5, [{"t": "제출 후에 발견하면 다시 준비해 재제출해야 합니다", "size": 20, "bold": True, "color": NAVY}], kind="body")
src("Five problem types (누락, 만료, 불일치, 중복, 유사 서류)", "docs/midterm/RESULTS.md; evaluation/reports/ADVS_system_audit_report.md", "requirements table / checks")
notes(s, 15, True, "서류를 제출할 때 누락, 만료, 회사명 불일치, 중복, 비슷한 다른 서류가 자주 생깁니다. 제출 후에 발견하면 처음부터 다시 해야 합니다.",
      "Typical problems: missing, expired, mismatched, duplicate and look-alike documents; found after submission they cost a resubmission.")

# ---- 3 what ADVS does
s = new_slide("ADVS: 업로드하면 세 가지 결과로 자동 점검합니다", criteria=(3,))
box(s, 0.7, 2.4, 2.4, 2.8, fill=BG, line=MUTED, shape=MSO_SHAPE.RECTANGLE, lw=1.5)
text(s, 0.7, 2.4, 2.4, 2.8, [{"t": "PDF · 사진", "size": 26, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER},
                             {"t": "서류 업로드", "size": 20, "color": MUTED, "align": PP_ALIGN.CENTER, "space": 8}], anchor=MSO_ANCHOR.MIDDLE)
block_arrow(s, 3.25, 3.45, 0.7, 0.6)
box(s, 4.1, 2.4, 2.6, 2.8, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 4.1, 2.4, 2.6, 2.8, [{"t": "ADVS", "size": 40, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER},
                             {"t": "자동 점검", "size": 22, "color": WHITE, "align": PP_ALIGN.CENTER, "space": 6}], anchor=MSO_ANCHOR.MIDDLE)
block_arrow(s, 6.85, 3.45, 0.7, 0.6)
cards = [("제출 가능", GREEN_BG, GREEN_TX, "✓", "문제 없음 · 공식 승인 아님"),
         ("보완 필요", RED_BG, RED_TX, "✕", "고쳐야 할 문제가 확인됨"),
         ("확인 필요", AMBER_BG, AMBER_TX, "⚠", "사람이 원본과 대조")]
y = 1.65
for name, bg, tx, ic, meaning in cards:
    box(s, 7.7, y, 5.1, 1.5, fill=bg, line=tx, lw=2)
    text(s, 7.9, y, 1.0, 1.5, [{"t": ic, "size": 44, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 8.9, y + 0.12, 3.8, 0.6, [{"t": name, "size": 28, "bold": True, "color": tx}])
    text(s, 8.9, y + 0.78, 3.8, 0.6, [{"t": meaning, "size": 18, "color": INK}], kind="body")
    y += 1.7
src("Three statuses and their meaning; 제출 가능 is not official approval", "README.md; docs/midterm/RESULTS.md", "status paragraph, line 5")
notes(s, 20, True, "서류를 올리면 ADVS가 세 가지 중 하나로 알려줍니다. 초록은 문제가 발견되지 않음, 빨강은 고쳐야 할 문제, 노랑은 사람이 확인해야 함입니다. 제출 가능은 공식 승인이 아닙니다.",
      "Upload documents and ADVS answers with one of three results; 'ready' is never an official approval.")

# ---- 4 Gantt
s = new_slide("계획 대비 진행: 핵심 기능이 계획보다 앞서 완료되었습니다", criteria=(1,), size=26)
GX0, GX1 = 3.55, 12.75          # timeline x range (inches)
D0, D1 = 0, 122                 # 2026-09-01 .. 2026-12-31 (days)
import datetime as dt
base = dt.date(2026, 9, 1)
dx = lambda d: GX0 + (GX1 - GX0) * ((d - base).days / 122)
# month header
for mname, mstart in (("9월", dt.date(2026, 9, 1)), ("10월", dt.date(2026, 10, 1)), ("11월", dt.date(2026, 11, 1)), ("12월", dt.date(2026, 12, 1))):
    mend = {9: dt.date(2026, 10, 1), 10: dt.date(2026, 11, 1), 11: dt.date(2026, 12, 1), 12: dt.date(2027, 1, 1)}[mstart.month]
    x1, x2 = dx(mstart), dx(min(mend, dt.date(2026, 12, 31)))
    text(s, x1, 1.4, x2 - x1, 0.4, [{"t": mname, "size": 18, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE,
         fill=NAVY if mstart.month % 2 == 1 else RGBColor(0x2F, 0x4C, 0x7C), shape=MSO_SHAPE.RECTANGLE)
rows = [
    ("요구사항·설계", (dt.date(2026, 9, 1), dt.date(2026, 9, 30)), (dt.date(2026, 9, 5), dt.date(2026, 9, 15)), "✔"),
    ("PDF·OCR 처리", (dt.date(2026, 10, 1), dt.date(2026, 10, 31)), (dt.date(2026, 9, 15), dt.date(2026, 10, 2)), "✔"),
    ("문서 분류·정보 추출", (dt.date(2026, 10, 1), dt.date(2026, 10, 31)), (dt.date(2026, 9, 22), dt.date(2026, 10, 6)), "✔"),
    ("규칙 검증·자동 점검", (dt.date(2026, 11, 1), dt.date(2026, 11, 30)), (dt.date(2026, 9, 29), dt.date(2026, 10, 5)), "✔"),
    ("화면(UI)·통합", (dt.date(2026, 11, 1), dt.date(2026, 11, 30)), (dt.date(2026, 9, 29), dt.date(2026, 10, 10)), "✔"),
    ("평가·안전성", (dt.date(2026, 12, 1), dt.date(2026, 12, 31)), (dt.date(2026, 10, 4), dt.date(2026, 10, 11)), "✔"),
    ("로그인·DB·배포", (dt.date(2026, 12, 1), dt.date(2026, 12, 31)), None, "예정"),
]
y = 1.95
RH = 0.64
for label, plan, act, st in rows:
    box(s, 0.6, y, 12.3, RH - 0.06, fill=BG if rows.index((label, plan, act, st)) % 2 == 0 else WHITE, shape=MSO_SHAPE.RECTANGLE)
    text(s, 0.7, y, 2.8, RH - 0.06, [{"t": label, "size": 18, "bold": True, "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
    px1, px2 = dx(plan[0]), dx(plan[1])
    box(s, px1, y + 0.06, px2 - px1, 0.2, fill=GREY_BAR, line=MUTED, shape=MSO_SHAPE.RECTANGLE, lw=1)
    if act:
        ax1, ax2 = dx(act[0]), dx(act[1])
        box(s, ax1, y + 0.3, ax2 - ax1, 0.22, fill=GREEN_TX, shape=MSO_SHAPE.RECTANGLE)
        text(s, ax2 + 0.05, y + 0.2, 0.5, 0.4, [{"t": st, "size": 20, "bold": True, "color": GREEN_TX}], anchor=MSO_ANCHOR.MIDDLE)
    else:
        text(s, px1 + 0.05, y + 0.28, 1.2, 0.3, [{"t": st, "size": 14, "bold": True, "color": AMBER_TX}])
    y += RH
# today line (presentation date)
tx = dx(dt.date(2026, 10, 15))
ln = arrow_line(s, tx, 1.85, tx, y + 0.05, color=RED_TX, width=2.5, head=False)
ln.line.dash_style = 4
text(s, tx - 0.6, y + 0.07, 1.2, 0.35, [{"t": "오늘 10/15", "size": 14, "bold": True, "color": RED_TX, "align": PP_ALIGN.CENTER}])
# legend
box(s, 0.7, 6.55, 0.5, 0.2, fill=GREY_BAR, line=MUTED, shape=MSO_SHAPE.RECTANGLE, lw=1)
text(s, 1.3, 6.45, 2.0, 0.4, [{"t": "계획 (수행계획서)", "size": 14, "color": INK}])
box(s, 3.5, 6.55, 0.5, 0.2, fill=GREEN_TX, shape=MSO_SHAPE.RECTANGLE)
text(s, 4.1, 6.45, 2.4, 0.4, [{"t": "실제 (커밋 기록)", "size": 14, "color": INK}])
text(s, 6.6, 6.4, 6.3, 0.5, [{"t": "멘토 요구사항 11개 중 구현 8 · 일부 1 · 예정 2", "size": 16, "bold": True, "color": NAVY, "align": PP_ALIGN.RIGHT}])
src("Planned schedule by month (9월 설계, 10월 PDF·OCR·분류·추출, 11월 자동 점검·통합, 12월 평가·최종 시연)",
    "EXTERNAL: owner's 수행계획발표 script ~/Downloads/ADVS.docx, 'Slide 8. 수행 일정 및 멘토링 계획' (not in the repository)", "Slide 8")
src("Actual dates: first commit 2026-09-05; implementation added 2026-09-15; classification/extraction hardened 09-22; frontend workflow + real-document processing 09-29; OCR ingestion + verification safety 10-02; B-1..B-3 rule fixes and harness 10-04; phases C/D/D2 10-05..10-06; demo + UI/UX Part A + audit 10-10; Phase G and hold-out 3 10-11",
    "git log (dates of the commits named in the Phase B-G reports)", "evaluation/reports/PHASE_B_REPORT.md, evaluation/phase_c|d|d2|e|e2|f|g reports")
src("Mentor requirements 8 implemented / 1 partly / 2 planned (11 rows)", "docs/midterm/RESULTS.md", "table 'Mentor requirements → status'")
notes(s, 30, True, "회색 막대가 수행계획서의 월별 계획이고 초록 막대가 실제 작업 기간입니다. 분류·추출과 규칙 검증, 화면은 계획보다 앞서 10월 초에 마쳤고, 평가와 안전성 작업도 시작했습니다. 로그인·DB·배포만 12월 예정입니다. 월 단위 계획이라 막대의 길이는 대략적인 비교입니다.",
      "Grey = monthly plan, green = actual work periods from the commit history: classification, rules and UI finished early in October; login, DB and deployment remain for December. The plan is monthly, so the comparison is approximate; no per-module percentages are claimed.")

# ---- 5 roles
s = new_slide("역할 분담: 백엔드·AI·평가 / 프론트엔드·UX", criteria=(2,))
cols = [("굴로모프 하비빌로", "Backend · 문서 분석 · OCR/AI · 점검 로직 · 평가", [
            ("문서 분류·정보 추출·규칙 검증", "6종 서류"), ("평가 체계", "고정 채점기 · 처음 보는 문서"), ("안전성", "독립 확인 · 숨은 글자 검사")], 0.7),
        ("올림조노바 무니라", "UI/UX · Frontend", [
            ("점검 결과 화면", "상태 · 체크리스트"), ("근거·검토 화면", "원본 옆에서 확인"), ("업로드 · 접근성", "화면 점검 (axe)")], 7.05)]
for name, role, items, x in cols:
    box(s, x, 1.55, 5.6, 4.5, fill=BG, line=LINE)
    box(s, x, 1.55, 5.6, 1.15, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 0.25, 1.6, 5.1, 0.6, [{"t": name, "size": 26, "bold": True, "color": WHITE}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.25, 2.15, 5.1, 0.5, [{"t": role, "size": 17, "color": RGBColor(0xDC, 0xE5, 0xF4)}], anchor=MSO_ANCHOR.MIDDLE)
    yy = 2.95
    for head, sub in items:
        o = box(s, x + 0.3, yy + 0.05, 0.5, 0.5, fill=GREEN_BG, line=GREEN_TX, shape=MSO_SHAPE.OVAL, lw=2)
        text(s, x + 0.3, yy + 0.05, 0.5, 0.5, [{"t": "✔", "size": 20, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 1.0, yy - 0.02, 4.5, 0.4, [{"t": head, "size": 19, "bold": True, "color": INK}])
        text(s, x + 1.0, yy + 0.36, 4.5, 0.35, [{"t": sub, "size": 16, "color": MUTED}])
        yy += 1.0
text(s, 0.7, 6.25, 11.9, 0.55, [{"t": "함께: 요구사항 분석 · 통합 테스트 · 멘토링 · 발표와 문서화", "size": 20, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER}],
     fill=GREEN_BG, line=GREEN_TX, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.08, kind="body")
src("Roles: 무니라 UI/UX·Frontend; 하비빌로 Backend·문서 분석·OCR/AI·점검 로직·통합·평가; shared 요구사항 분석·통합 테스트·멘토링·발표·문서화",
    "EXTERNAL: owner's 수행계획발표 script ~/Downloads/ADVS.docx, 'Slide 9. 팀원 간 역할 분배'", "Slide 9")
src("Frontend deliverables (status banner, checklist, evidence view, review flow, uploader, axe checks)", "evaluation/phase_e2/PHASE_E2_REPORT.md; evaluation/phase_e2/UX_AUDIT.md; docs/planning/ROADMAP.md", "Part A report; N7 'frontend, Munira'")
src("Backend/AI/evaluation deliverables (6 document types, frozen scorer, hold-out sets, independent confirmation, hidden-text check)",
    "docs/midterm/RESULTS.md; evaluation/phase_d/PHASE_D_REPORT.md; evaluation/phase_g/PHASE_G_REPORT.md", "requirements table; §2 G-1; §4")
notes(s, 25, True, "하비빌로는 백엔드와 문서 분석, OCR, 점검 로직, 그리고 평가 체계와 안전성을 맡았고, 무니라는 사용자 화면과 UX를 맡았습니다. 요구사항 분석, 통합 테스트, 멘토링, 발표는 함께 했습니다. 기여도는 커밋 수가 아니라 담당 영역과 결과물로 설명했습니다.",
      "Habibillo: backend, document analysis, OCR, validation logic, evaluation and safety. Munira: UI/UX and frontend. Shared: requirements, integration tests, mentoring, presentation. Roles are described by area and deliverable, not by commit counts.")

# ---- 6 architecture
s = new_slide("구조: 기존 OCR + 규칙 기반 점검 + 사람 확인", criteria=(3,))
def node(x, y, w, h, label, sub=None, fill=BG, line=NAVY, tcol=NAVY, size=18):
    paras = [{"t": label, "size": size, "bold": True, "color": tcol, "align": PP_ALIGN.CENTER}]
    if sub:
        paras.append({"t": sub, "size": 14, "color": MUTED, "align": PP_ALIGN.CENTER, "space": 2})
    return text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.MIDDLE, fill=fill, line=line, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.06, lw=2)
node(0.6, 3.1, 1.5, 1.2, "업로드", "PDF · 사진")
block_arrow(s, 2.15, 3.5, 0.4, 0.4)
node(2.6, 1.75, 3.0, 1.35, "디지털 PDF", "텍스트 추출 + 숨은 텍스트 검사", fill=GREEN_BG, line=GREEN_TX, tcol=GREEN_TX)
node(2.6, 4.3, 3.0, 1.35, "스캔 · 사진", "OCR (PaddleOCR PP-OCRv5)", fill=AMBER_BG, line=AMBER_TX, tcol=AMBER_TX)
arrow_line(s, 2.1, 3.7, 2.6, 2.55)
arrow_line(s, 2.1, 3.7, 2.6, 4.95)
arrow_line(s, 5.6, 2.45, 6.1, 3.7)
arrow_line(s, 5.6, 4.95, 6.1, 3.7)
node(6.1, 3.1, 1.45, 1.2, "문서 분류", "규칙 기반")
block_arrow(s, 7.6, 3.5, 0.35, 0.4)
node(8.0, 3.1, 1.45, 1.2, "항목 추출", "값 + 위치")
block_arrow(s, 9.5, 3.5, 0.35, 0.4)
node(9.9, 3.1, 1.45, 1.2, "규칙 검증", "서류 간 비교")
block_arrow(s, 11.4, 3.5, 0.35, 0.4)
node(11.8, 3.1, 1.0, 1.2, "결과", None, size=18)
node(9.9, 5.0, 2.9, 0.9, "불확실하면 사람 확인", None, fill=AMBER_BG, line=AMBER_TX, tcol=AMBER_TX)
arrow_line(s, 10.6, 4.3, 10.6, 5.0, color=AMBER_TX)
arrow_line(s, 12.3, 5.0, 12.3, 4.3, color=AMBER_TX)
text(s, 0.6, 6.25, 12.2, 0.5, [{"t": "Next.js  ·  FastAPI  ·  PaddleOCR  ·  Python  ·  SQLite", "size": 20, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER}],
     fill=BG, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.05)
src("Pipeline stages and stack (Next.js, FastAPI, PaddleOCR PP-OCRv5, Python, SQLite)", "docs/architecture/ARCHITECTURE.md; README.md; apps/api/pyproject.toml", "'Document intelligence pipeline'; Tech Stack; paddle extra")
notes(s, 25, True, "디지털 PDF는 글자층을 읽고 숨은 텍스트를 검사합니다. 스캔과 사진은 기존 OCR로 읽습니다. 그다음 규칙으로 분류하고 항목을 뽑아 서류끼리 비교합니다. 불확실한 값은 사람이 확인합니다. 새 모델은 쓰지 않고 검증 가능한 규칙에 집중했습니다.",
      "Digital PDFs: text layer plus a hidden-text check; scans and photos: the existing OCR. Then rule-based classification, extraction and cross-document checks; uncertain values go to a person. Traditional OCR only.")

# ---- 7-13 screenshot slides
shot_slide("① 서류 제출: 빠진 서류는 바로 올립니다", "S1_upload", (300, 240, 1320, 672),
           [(1, "누락 → 보완 필요", (505, 287), (850, 262), 380),
            (2, "제출됨 · 확인 완료", (1448, 587), (900, 540), 380),
            (3, "미제출 서류 칸", (1495, 843), (1000, 795), 330)],
           (4,), 15, True, "서류를 올리면 칸마다 상태가 보입니다. 두 서류는 제출되었고 두 서류는 빠져 있어서 상단 배너가 보완 필요로 알려 줍니다. 빠진 칸에서 바로 업로드할 수 있습니다.",
           "Two documents are in, two are missing; the banner says so and the missing slots have an upload button.")
src("Screenshot S1 (new submission, two of four documents)", "docs/midterm/v4/screenshots/S1_upload.png", "captured from `scripts/demo` on 2026-10-11, 점검 기준일 2026-10-05")
shot_slide("② 정상 서류: 제출 가능", "S2_ready", (300, 240, 1320, 672),
           [(1, "결과: 제출 가능", (505, 287), (850, 262), 360),
            (2, "공식 승인은 아님", (785, 358), (900, 345), 380),
            (3, "서류별 확인 완료", (1448, 587), (900, 540), 380)],
           (4,), 20, True, "네 서류가 모두 있고 유효하며 서로 일치하면 초록 배너로 제출 가능을 알려 줍니다. 공식 승인이 아니라는 문구를 항상 함께 보여 줍니다.",
           "All four required documents are present, valid and consistent: green banner, with the 'not an official approval' note.")
src("Screenshot S2 (D1 normal submission)", "docs/midterm/v4/screenshots/S2_ready.png", "demo scenario D1 (docs/midterm/DEMO_SCRIPT.md)")
shot_slide("③ 결과마다 근거를 보여줍니다", "S3_evidence", (300, 240, 1320, 672),
           [(1, "원본에서 읽은 위치", (600, 553), (480, 300), 400),
            (2, "읽은 값 + 출처", (1330, 525), (1250, 575), 340),
            (3, "규칙 통과", (1535, 816), (1330, 690), 240)],
           (4,), 15, False, "왼쪽 원본 서류에서 읽은 위치가 표시되고, 오른쪽에는 읽은 값과 그 출처, 그리고 통과한 규칙이 나옵니다. 사람이 몇 초 안에 확인할 수 있습니다.",
           "The value read, where it came from on the original, and the rule it passed.")
src("Screenshot S3 (evidence of 유효기간 종료일 in D1)", "docs/midterm/v4/screenshots/S3_evidence.png", "document detail page")
shot_slide("④ 만료 서류: 보완 필요와 이유", "S4_expired", (300, 330, 1320, 672),
           [(1, "보완 필요", (1495, 843), (1020, 790), 280),
            (2, "만료일 < 기준일", (910, 927), (960, 880), 340),
            (3, "새 서류로 교체", (520, 967), (700, 940), 340)],
           (4,), 20, True, "납세증명서의 유효기간 종료일이 점검 기준일보다 이전이면 보완 필요로 알려 주고, 어느 날짜가 문제인지 문장으로 보여 줍니다.",
           "An expired tax certificate is caught, with the two dates that matter written out.")
src("Screenshot S4 (D2: 유효기간 종료일 2026. 08. 31. earlier than 점검 기준일 2026. 10. 05.)", "docs/midterm/v4/screenshots/S4_expired.png", "demo scenario D2")
shot_slide("⑤ 서류 사이의 불일치도 잡습니다", "S5_mismatch", (300, 240, 1320, 672),
           [(1, "결과: 보완 필요", (505, 287), (850, 262), 360),
            (2, "서류 간 회사명 불일치", (905, 661), (960, 610), 440)],
           (4,), 15, False, "사업자등록증과 납세증명서의 회사명이 다르면 두 값을 나란히 보여 주며 보완 필요로 알려 줍니다. 서류 하나가 아니라 제출 전체를 비교합니다.",
           "Company names differ between two documents; both values are quoted. The submission is checked as a whole.")
src("Screenshot S5 (D3 company-name mismatch)", "docs/midterm/v4/screenshots/S5_mismatch.png", "demo scenario D3")
shot_slide("⑥ 불확실하면 사람에게: 원본 이미지 옆에서 확인", "S7_review", (300, 150, 1320, 672),
           [(1, "자동으로 읽은 값", (492, 247), (560, 215), 330),
            (2, "원본 이미지 crop", (1570, 330), (1250, 372), 340),
            (3, "같으면 Enter로 확인", (532, 438), (735, 375), 420)],
           (4,), 25, True, "스캔 서류는 값이 맞다는 독립적인 증거가 없으면 사람에게 넘깁니다. 읽은 값과 원본의 해당 부분을 나란히 보여 주고, 같으면 확인 버튼 하나로 끝납니다.",
           "No independent confirmation for a scanned value, so it goes to a person: the value next to the original crop, one key to confirm.")
src("Screenshot S7 (D9 review: two 발급일 values with the cropped original)", "docs/midterm/v4/screenshots/S7_review.png", "demo scenario D9")
shot_slide("⑦ 확인이 끝나면 자동으로 다시 점검합니다", "S8_after_review", (300, 240, 1320, 672),
           [(1, "확인 필요 → 제출 가능", (505, 287), (850, 262), 440),
            (2, "자동 재점검", (690, 358), (900, 345), 340)],
           (4,), 15, False, "마지막 항목을 확인하면 점검 버튼을 누르지 않아도 상태가 제출 가능으로 바뀝니다. 사람의 확인이 결과에 반영됩니다.",
           "After the last confirmation the check re-runs by itself and the status changes.")
src("Screenshot S8 (D9 after review)", "docs/midterm/v4/screenshots/S8_after_review.png", "demo scenario D9, after the reviewer confirms both values")

# ---- 14 result tiles
s = new_slide("결과: 잘못된 ‘제출 가능’ 0건", criteria=(), size=30)
tiles = [("0 / 14", "잘못된 ‘제출 가능’", "처음 보는 문서 (hold-out 3)", "개발 문서: 0 / 40", GREEN_BG, GREEN_TX),
         ("790 / 790", "디지털 PDF 추출", "개발 문서", "처음 보는 문서: 274 / 275", GREEN_BG, GREEN_TX),
         ("268 / 275", "스캔 필드 정확도", "처음 보는 문서 (hold-out 3)", "틀린 값 0 · 나머지는 사람 확인", AMBER_BG, AMBER_TX),
         ("12 / 12", "위·변조 PDF 차단", "숨은 글자가 있는 PDF", "제출 가능까지 간 것 0", GREEN_BG, GREEN_TX)]
x = 0.6
for big, label, ctx, sub, bg, tx in tiles:
    box(s, x, 1.6, 2.95, 4.7, fill=bg, line=tx, lw=2.5)
    text(s, x + 0.1, 1.85, 2.75, 1.1, [{"t": big, "size": 40, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 3.05, 2.65, 0.9, [{"t": label, "size": 22, "bold": True, "color": INK, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 4.0, 2.65, 0.8, [{"t": ctx, "size": 16, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 4.95, 2.65, 1.1, [{"t": sub, "size": 16, "color": MUTED, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.TOP)
    x += 3.12
text(s, 0.6, 6.45, 12.2, 0.5, [{"t": "가상 테스트 문서 기준 · 분모를 항상 함께 표시", "size": 18, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER}], kind="body")
src("0/14 false 제출 가능 on hold-out 3 per input type (95% upper bound 21.4%); 0/40 on development corpora", "docs/midterm/RESULTS.md; evaluation/phase_g/results/denominators_final.txt; evaluation/phase_g/final/H3_integrated_report.md", "Safety table row 1-2")
src("Digital 790/790 (dev) and 274/275 (hold-out 3)", "docs/midterm/RESULTS.md; evaluation/phase_g/results/denominators_final.txt", "Accuracy table row 1")
src("Scan fields 268/275 on hold-out 3, 0 wrong values", "docs/midterm/RESULTS.md; evaluation/phase_g/final/H3_integrated.json", "Accuracy table row 3; metrics.csv 'Phase G, hold-out 3'")
src("Hidden-text PDFs: 12/12 held at 확인 필요 (TEXT_LAYER_MISMATCH), 0 reached 제출 가능", "evaluation/phase_g/results/pdf_manipulation_pipeline.md", "table and last line")
notes(s, 20, True, "가장 중요한 안전 지표는 잘못된 제출 가능입니다. 처음 보는 문서에서 열네 건 중 0건이었고 개발 문서에서는 마흔 건 중 0건입니다. 디지털 PDF는 거의 모두 맞고, 스캔도 틀린 값은 없었으며 불확실한 값만 사람에게 넘깁니다. 숨은 글자로 조작한 PDF 열두 건은 모두 확인 필요로 막았습니다. 표본이 작아서 0건이 위험이 없다는 뜻은 아닙니다.",
      "Safety: 0 wrong 'ready' on unseen documents (0/14) and on development documents (0/40); digital PDFs nearly perfect; scans have no wrong values, uncertain ones go to a person; all 12 tampered PDFs were held. Small samples: zero events is not zero risk.")

# ---- 15 how it improved (step chart)
s = new_slide("어떻게: 사람 확인 항목 11.64 → 3.73 (스캔 1건당, 개발 문서)", criteria=(4,), size=26)
cd = CategoryChartData()
cd.categories = ["기준선\n(모두 사람 확인)", "Phase D", "D2 (안전 강화)", "Phase G (현재)"]
cd.add_series("사람이 확인할 항목 수 (스캔 1건당)", (11.64, 3.82, 7.23, 3.73))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.35), Inches(8.6), Inches(4.5), cd)
ch = gf.chart
ch.has_legend = False
ch.has_title = False
ch.font.size, ch.font.name = Pt(14), FONT
pl = ch.plots[0]
pl.gap_width = 60
pl.has_data_labels = True
pl.data_labels.font.size, pl.data_labels.font.bold = Pt(20), True
pl.data_labels.number_format = "0.00"
pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
ser = pl.series[0]
ser.format.fill.solid()
ser.format.fill.fore_color.rgb = NAVY
for i, col in enumerate((GREY_BAR, NAVY, AMBER_TX, GREEN_TX)):
    pt = ser.points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = col
va = ch.value_axis
va.minimum_scale, va.maximum_scale, va.major_unit = 0, 14, 2
va.has_title = True
va.axis_title.text_frame.text = "항목 수 (스캔 제출 1건당)"
va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
va.major_gridlines.format.line.color.rgb = LINE
ch.category_axis.tick_labels.font.size = Pt(14)
# technique chips between the bars
chips = [("독립 확인\n(다른 서류·검증숫자)", 1.95, GREEN_BG, GREEN_TX), ("안전 규칙 강화\n(소유자 승인)", 4.1, AMBER_BG, AMBER_TX), ("내부 검증\n(GPA 재계산·날짜 쌍)", 6.4, GREEN_BG, GREEN_TX)]
for lab, cxp, bg, tx in chips:
    text(s, cxp - 0.1, 1.4, 2.1, 0.8, [{"t": lab, "size": 14, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE, fill=bg, line=tx, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.04, radius=0.2)
    arrow_line(s, cxp + 0.95, 2.2, cxp + 0.95, 2.6, color=tx, width=2)
box(s, 9.45, 1.55, 3.4, 2.5, fill=GREEN_BG, line=GREEN_TX, lw=2.5)
text(s, 9.55, 1.6, 3.2, 0.5, [{"t": "처음 보는 문서 (hold-out 3)", "size": 16, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
text(s, 9.55, 2.15, 3.2, 1.2, [{"t": "7.68 → 4.28", "size": 40, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
text(s, 9.55, 3.35, 3.2, 0.6, [{"t": "스캔 1건당 (Phase G 이전 → 이후)", "size": 14, "color": INK, "align": PP_ALIGN.CENTER}])
text(s, 9.45, 4.3, 3.4, 2.4, [{"t": "중간에 늘어난 것은 안전을 위해 규칙을 강화했기 때문입니다 (소유자 승인).", "size": 18, "bold": True, "color": AMBER_TX}],
     fill=AMBER_BG, line=AMBER_TX, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE, lw=2, kind="body")
src("11.64 baseline (every OCR field to a person), dev, scans", "docs/midterm/metrics.csv", "'B0 baseline,dev,review burden scanned'; evaluation/phase_d/PHASE_D_REPORT.md §3")
src("3.82 Phase D (independent confirmation), dev, scans", "docs/midterm/metrics.csv", "'D (S7 before D2),dev,review burden scanned'; PHASE_D_REPORT.md §4")
src("7.23 D2 after safety rules (title gate, boundary margins, second-pass limit; owner-approved), dev, scans", "docs/midterm/metrics.csv; evaluation/phase_d2/PHASE_D2_REPORT.md", "'D2 final (main)'; §11")
src("3.73 Phase G (D3 internal confirmation merged), dev, scans", "evaluation/phase_g/results/gate_summary_dev_final.md; docs/midterm/RESULTS.md", "dev row; 'Automation' table")
src("Hold-out 3: 7.68 (main baseline) → 4.28 (integrated), scans", "evaluation/phase_g/PHASE_G_REPORT.md; docs/midterm/metrics.csv", "§4 table; 'Phase G, hold-out 3, review fields'")
src("Techniques: independent confirmation, safety rules, internal confirmations (GPA arithmetic, validity date pairs, value printed twice)", "evaluation/phase_d/PHASE_D_REPORT.md §4; evaluation/phase_d2/PHASE_D2_REPORT.md §4; evaluation/phase_g/PHASE_G_REPORT.md §3", "")
notes(s, 30, True, "문제는 스캔 서류의 값을 전부 사람이 확인해야 한다는 점이었고, 한 건당 11.64개였습니다. 다른 서류와 대조하고 검증숫자를 쓰는 독립 확인으로 3.82개까지 줄였습니다. 그런데 처음 보는 문서에서 잘못된 제출 가능이 나와 안전 규칙을 강화했고 그래서 7.23개로 늘었습니다. 이후 GPA 재계산과 날짜 쌍 같은 내부 검증을 더해 다시 3.73개로 줄였습니다. 오른쪽은 처음 보는 문서에서의 같은 개선입니다.",
      "Problem: every scanned value needed a person (11.64 per submission). Independent confirmation cut it to 3.82; tightening safety after a false 'ready' on unseen data raised it to 7.23 (owner-approved); internal checks brought it to 3.73. Right: the same improvement on unseen documents.")

# ---- 16 accuracy grouped bars
s = new_slide("정확도 개선: 처음 보는 문서 기준 (hold-out 3)", criteria=(4,))
cd = CategoryChartData()
cd.categories = ["스캔 필드\n257 → 268 / 275", "사진 필드\n264 → 273 / 275", "대학명 (스캔)\n9 → 19 / 20", "대학명 (사진)\n11 → 20 / 20"]
cd.add_series("Phase G 이전", (round(257 / 275 * 100, 1), round(264 / 275 * 100, 1), 45.0, 55.0))
cd.add_series("Phase G 이후", (round(268 / 275 * 100, 1), round(273 / 275 * 100, 1), 95.0, 100.0))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.4), Inches(12.1), Inches(5.0), cd)
ch = gf.chart
ch.has_legend = True
ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
ch.legend.font.size = Pt(16)
ch.has_title = False
ch.font.size, ch.font.name = Pt(14), FONT
pl = ch.plots[0]
pl.gap_width, pl.overlap = 70, -5
pl.has_data_labels = True
pl.data_labels.font.size, pl.data_labels.font.bold = Pt(16), True
pl.data_labels.number_format = '0.0"%"'
pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
for ser, col in zip(pl.series, (GREY_BAR, NAVY)):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = col
va = ch.value_axis
va.minimum_scale, va.maximum_scale, va.major_unit = 0, 110, 20
va.has_title = True
va.axis_title.text_frame.text = "정확한 필드 (%)"
va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
va.major_gridlines.format.line.color.rgb = LINE
ch.category_axis.tick_labels.font.size = Pt(15)
text(s, 0.6, 6.5, 12.1, 0.45, [{"t": "잘못된 값 0 · 처음 보는 문서 (hold-out 3, 한 번만 판정)", "size": 18, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER}], kind="body")
src("Scan fields 257 → 268 / 275; photo fields 264 → 273 / 275 (main baseline → integrated), 0 wrong", "evaluation/phase_g/PHASE_G_REPORT.md", "§4 hold-out 3 table; docs/midterm/metrics.csv 'Phase G, hold-out 3, field accuracy'")
src("university_name scans 9 → 19 / 20, photos 11 → 20 / 20 (percent = counts / 20 or / 275)", "evaluation/phase_g/PHASE_G_REPORT.md; docs/midterm/RESULTS.md", "§4 table; Accuracy table row 4")
notes(s, 20, False, "같은 처음 보는 문서로 개선 전후를 비교했습니다. 스캔 필드는 275개 중 257개에서 268개로, 사진은 264개에서 273개로 늘었고, 대학명은 스캔 9개에서 19개, 사진 11개에서 20개로 올랐습니다. 틀린 값은 0개입니다.",
      "Same unseen documents before and after: scans 257 to 268 of 275, photos 264 to 273, university name 9 to 19 and 11 to 20 of 20; no wrong values.")

# ---- 17 difficulties
s = new_slide("어려웠던 점 → 해결", criteria=(4,))
def pair(x, y, title, before, after, bcol, acol):
    box(s, x, y, 6.0, 2.45, fill=WHITE, line=LINE, lw=1.5)
    text(s, x + 0.15, y + 0.05, 5.7, 0.45, [{"t": title, "size": 18, "bold": True, "color": NAVY}])
    text(s, x + 0.15, y + 0.62, 2.55, 1.6, [{"t": before, "size": 16, "bold": True, "color": RED_TX, "align": PP_ALIGN.CENTER}],
         anchor=MSO_ANCHOR.MIDDLE, fill=RED_BG, line=RED_TX, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.08, lw=1.5)
    block_arrow(s, x + 2.78, y + 1.18, 0.4, 0.4)
    text(s, x + 3.28, y + 0.62, 2.55, 1.6, [{"t": after, "size": 16, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER}],
         anchor=MSO_ANCHOR.MIDDLE, fill=GREEN_BG, line=GREEN_TX, shape=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.08, lw=1.5)
pair(0.6, 1.4, "도장이 글자를 가림", "도장 아래 날짜를\n잘못 읽음", "도장 영역을\n따로 읽음", RED_TX, GREEN_TX)
pair(6.75, 1.4, "대학명이 붙거나 잘림", "대학명 21 / 58\n(스캔)", "추출 규칙 개선\n56 / 58", RED_TX, GREEN_TX)
pair(0.6, 4.05, "숨은 텍스트로 날짜 조작", "화면 2025-01-31\n글자층 2027-12-31", "화면과 비교해 차단\n705건 중 0 통과", RED_TX, GREEN_TX)
pair(6.75, 4.05, "처음 보는 문서에서 과적합", "hold-out 1\n디지털 174 / 275", "수정 후 hold-out 2\n275 / 275", RED_TX, GREEN_TX)
src("Seal over text → stamp-aware second-pass reading (red channel); no number shown", "evaluation/phase_g/PHASE_G_REPORT.md", "§3 (stamp-aware second-pass reading, line 82); cause (1)/(3) of university-name errors, line 37")
src("University name 21/58 → 56/58 (scans, dev corpora)", "evaluation/phase_g/results/university_name_before_after.txt; docs/midterm/RESULTS.md", "before/after block; Accuracy table row 4")
src("Hidden text: 0 of 705 manipulated copies missed; example dates are the manipulation used in the suite (2099-12-31) and the probe (2025-01-31 vs 2027-12-31)", "evaluation/phase_g/results/pdf_manipulation_suite.md; evaluation/phase_f/results/text_layer_probe.txt", "table; probe output")
src("Overfitting found by unseen data: hold-out 1 digital 174/275 (63 %) → hold-out 2 275/275 after fixes", "evaluation/phase_d/PHASE_D_REPORT.md §8-9; evaluation/phase_d2/PHASE_D2_REPORT.md §6", "digital extraction rows")
notes(s, 30, False, "네 가지 어려움이 있었습니다. 도장이 글자를 가리는 문제는 도장 영역을 따로 읽어 해결했습니다. 대학명이 붙거나 잘리는 문제는 추출 규칙을 고쳐 스캔 58개 중 21개에서 56개로 올렸습니다. PDF에 숨은 글자로 날짜를 바꾸는 조작은 화면과 비교해 막았습니다. 마지막으로 개발 문서에서 완벽하던 디지털 추출이 처음 보는 문서에서는 275개 중 174개였던 과적합을 찾아 고쳤습니다.",
      "Four difficulties: seals over text (read the seal area separately), university names glued or cut (21/58 to 56/58), hidden text manipulating dates (blocked by comparing with the rendered page) and overfitting found on unseen documents (174/275 to 275/275 on the next unseen set).")

# ---- 18 how verified
s = new_slide("어떻게 검증했나: 개발은 개발 문서로, 판정은 처음 보는 문서로 1회", criteria=(3,), size=26)
box(s, 0.6, 1.7, 3.3, 2.2, fill=BG, line=NAVY, lw=2)
text(s, 0.6, 1.7, 3.3, 2.2, [{"t": "개발용 문서", "size": 24, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER},
                            {"t": "857개 (299 + 279 + 279)", "size": 18, "color": INK, "align": PP_ALIGN.CENTER, "space": 6}], anchor=MSO_ANCHOR.MIDDLE)
block_arrow(s, 4.0, 2.55, 0.55, 0.5)
box(s, 4.65, 1.7, 3.3, 2.2, fill=BG, line=NAVY, lw=2)
text(s, 4.65, 1.7, 3.3, 2.2, [{"t": "수정·개선", "size": 24, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER},
                             {"t": "고정된 채점기", "size": 18, "color": INK, "align": PP_ALIGN.CENTER, "space": 6}], anchor=MSO_ANCHOR.MIDDLE)
block_arrow(s, 8.05, 2.55, 0.55, 0.5)
box(s, 8.7, 1.7, 4.0, 2.2, fill=GREEN_BG, line=GREEN_TX, lw=3)
text(s, 8.7, 1.7, 4.0, 2.2, [{"t": "처음 보는 문서", "size": 24, "bold": True, "color": GREEN_TX, "align": PP_ALIGN.CENTER},
                            {"t": "hold-out 3: 279개, 1회만 판정", "size": 18, "color": INK, "align": PP_ALIGN.CENTER, "space": 6}], anchor=MSO_ANCHOR.MIDDLE)
side = [("일부러 넣은 OCR 오류", "개발 6,444건 · hold-out 3 2,238건"), ("위·변조 PDF", "705건 (추출) + 12건 (API)"), ("자동 테스트", "백엔드 613 · 화면 108 · E2E 15")]
x = 0.6
for head, sub in side:
    box(s, x, 4.45, 3.95, 1.7, fill=WHITE, line=LINE, lw=2)
    text(s, x + 0.1, 4.55, 3.75, 0.55, [{"t": head, "size": 20, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.1, 5.15, 3.75, 0.9, [{"t": sub, "size": 18, "color": INK, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    x += 4.1
text(s, 0.6, 6.4, 12.2, 0.5, [{"t": "모든 문서는 TEST SAMPLE 가상 문서", "size": 18, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER}], kind="body")
src("Development documents 299 + 279 + 279 = 857; hold-out 3 has 279 files, judged once", "evaluation/datasets/synthetic/test_variants/README.md; holdout/README.md; holdout2/README.md; holdout3 manifest", "file counts; evaluation/phase_g/final/session_log.txt")
src("Injected-error cases: dev corpora 1,968 + 2,238 + 2,238 = 6,444; hold-out 3 2,238", "evaluation/phase_g/results/dev_final/F_inj_dev.md, F_inj_holdout.md, F_inj_holdout2.md; evaluation/phase_g/final/H3_integrated_inj.md", "header line 'cases N'")
src("Manipulated PDFs 705 (extraction suite) and 12 (API)", "evaluation/phase_g/results/pdf_manipulation_suite.md; pdf_manipulation_pipeline.md", "tables")
src("Tests: backend 613, web unit 108, Playwright 15 run (22 total, 7 skipped)", "docs/midterm/RESULTS.md; docs/operations/testing.md", "Safety heading; Phase G paragraph")
notes(s, 25, False, "검증 원칙은 두 가지입니다. 개발은 개발용 문서로 하고, 판정은 처음 보는 문서로 딱 한 번 합니다. 거기에 일부러 OCR 오류를 넣은 시험, 조작한 PDF, 그리고 자동 테스트를 더했습니다. 모두 TEST SAMPLE 가상 문서입니다.",
      "Develop on development documents, judge once on unseen documents; plus injected OCR errors, tampered PDFs and automated tests; all documents are fictional TEST SAMPLE files.")

# ---- 19 limits
s = new_slide("한계와 현실성: 가상 문서로 검증, 실제 문서는 파일럿으로", criteria=(3,), size=26)
lims = [("📄", "가상 테스트 문서만", "실제 문서·실사진은 파일럿 예정", AMBER_BG, AMBER_TX),
        ("🧑", "스캔·사진은 일부 사람 확인", "독립 확인 없으면 사람 확인", AMBER_BG, AMBER_TX),
        ("🔒", "로그인 없음 · SQLite만 시험", "접근 제어·PostgreSQL은 12월", RED_BG, RED_TX)]
x = 0.7
for ic, head, sub, bg, tx in lims:
    box(s, x, 1.8, 3.85, 4.2, fill=bg, line=tx, lw=2.5)
    text(s, x, 2.0, 3.85, 1.3, [{"t": ic, "size": 60, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 3.4, 3.55, 1.2, [{"t": head, "size": 24, "bold": True, "color": tx, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.15, 4.65, 3.55, 1.1, [{"t": sub, "size": 18, "color": INK, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.TOP, kind="body")
    x += 4.05
src("Limits: fictional documents; scans/photos partly need a person; no authentication, SQLite only tested", "docs/midterm/RESULTS.md", "'Honest limits'")
src("OCR does not guarantee authenticity or remove extraction errors", "docs/architecture/ARCHITECTURE.md", "'Document intelligence pipeline' scope paragraph")
notes(s, 15, False, "한계도 말씀드립니다. OCR은 진위를 보증하지 못하고 오독을 없애지 못합니다. 지금까지는 가상 문서로만 검증했습니다. 스캔과 사진은 독립 확인이 없으면 사람이 확인합니다. 로그인은 없고 SQLite로만 시험했습니다. OCR은 진위를 보증하지 못합니다.",
      "Limits: only fictional documents so far; scans and photos still need a person for unconfirmed values; no login, SQLite only; OCR cannot guarantee authenticity.")

# ---- 20 future plan
s = new_slide("향후 계획: 11월 실제 데이터 검증, 12월 최종 시스템", criteria=(5,), size=28)
# timeline bar
box(s, 0.7, 2.05, 11.9, 0.14, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
for lab, cx in (("10/15  1차 중간", 0.7), ("11/19  2차 중간", 6.0), ("12/10  최종", 12.0)):
    o = box(s, cx - 0.01, 1.95, 0.34, 0.34, fill=RED_TX, shape=MSO_SHAPE.OVAL)
text(s, 0.6, 1.4, 2.8, 0.45, [{"t": "10/15 1차 중간", "size": 16, "bold": True, "color": NAVY}])
text(s, 5.3, 1.4, 2.8, 0.45, [{"t": "11/19 2차 중간", "size": 16, "bold": True, "color": NAVY}])
text(s, 10.2, 1.4, 2.5, 0.45, [{"t": "12/10 최종", "size": 16, "bold": True, "color": NAVY, "align": PP_ALIGN.RIGHT}])
cols = [("2차 중간 (11월)", 0.7, [("실제 스캔·사진으로 검증", "새 hold-out 판정"), ("촬영 품질 검사 · 재촬영 안내", "이미지 보정"), ("검토 대기열 · 관리자 화면", "")],
         "목표: 잘못된 ‘제출 가능’ 0 유지 · 사람 확인 항목 추가 감소"),
        ("최종 (12월)", 6.9, [("로그인 · 권한", "개인정보 보호 · 감사 로그"), ("PostgreSQL · 배포", "E2E 테스트"), ("(선택) 국세청 사업자 조회", "")],
         "목표: 최종 보고서와 재현 가능한 지표")]
for head, x, items, goal in cols:
    box(s, x, 2.55, 5.75, 3.55, fill=BG, line=LINE, lw=1.5)
    text(s, x + 0.2, 2.6, 5.3, 0.55, [{"t": head, "size": 24, "bold": True, "color": NAVY}], anchor=MSO_ANCHOR.MIDDLE)
    yy = 3.25
    for a, b in items:
        text(s, x + 0.25, yy, 5.3, 0.4, [{"t": "▸ " + a, "size": 19, "bold": True, "color": INK}])
        if b:
            text(s, x + 0.55, yy + 0.36, 4.9, 0.35, [{"t": b, "size": 16, "color": MUTED}])
        yy += 0.85
    text(s, x + 0.15, 5.6, 5.45, 0.5, [{"t": goal, "size": 15, "bold": True, "color": GREEN_TX}], anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.7, 6.3, 11.9, 0.5, [{"t": "목표 수치는 처음 보는 문서 기준으로 분모와 함께 보고합니다", "size": 18, "bold": True, "color": NAVY, "align": PP_ALIGN.CENTER}], kind="body")
src("November/December tasks (physical corpus, photo quality gate, reviewer queue and admin screen, real-document pilot; login, privacy, audit log, PostgreSQL, deployment, optional National Tax Service lookup)", "docs/planning/ROADMAP.md; docs/midterm/ROADMAP.md", "§November, §December tables")
src("Goals: keep false 제출 가능 at 0 and reduce review items further (acceptance criteria)", "docs/planning/ROADMAP.md", "'Acceptance for November/December'")
src("Dates 10/15, 11/19, 12/10 (course schedule; the course deck also lists 10/22 for the first midterm)", "docs/planning/ROADMAP.md; evaluation/phase_f/TECHNICAL_AUDIT.md", "Dates paragraph; conflicts table item 4")
notes(s, 30, True, "다음 단계의 핵심은 실제 스캔과 사진으로 검증하는 것입니다. 11월에는 촬영 품질 검사와 재촬영 안내, 이미지 보정, 검토 대기열과 관리자 화면을 만들고 새 처음 보는 문서로 판정합니다. 12월에는 로그인과 권한, 개인정보 보호, 감사 로그, PostgreSQL, 배포를 마치고, 선택으로 국세청 조회를 검토합니다. 각 단계의 목표는 잘못된 제출 가능 0을 유지하고 사람 확인 항목을 더 줄이는 것입니다.",
      "Next: validate on real scans and photos. November: photo quality check and retake guidance, image correction, reviewer queue and admin screen, a new unseen set. December: login and roles, privacy, audit log, PostgreSQL, deployment, optional National Tax Service lookup. Goals: keep false 'ready' at 0 and reduce review items further.")

# ---- 21 thanks / Q&A
s = new_slide(None, number=True)
box(s, 0, 0, SW, SH, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.9, 2.2, 11.5, 1.2, [{"t": "감사합니다", "size": 54, "bold": True, "color": WHITE}])
text(s, 0.9, 3.7, 11.5, 0.8, [{"t": "질문 · Q&A", "size": 32, "color": RGBColor(0xC7, 0xD3, 0xE8)}])
text(s, 0.9, 5.6, 11.5, 0.5, [{"t": "올림조노바 무니라 · 굴로모프 하비빌로", "size": 20, "color": WHITE}])
text(s, 11.9, 7.05, 1.0, 0.32, [{"t": str(count), "size": 12, "color": RGBColor(0xC7, 0xD3, 0xE8), "align": PP_ALIGN.RIGHT}])
notes(s, 10, True, "질문 받겠습니다. (준비한 답변) 1) 실제 문서에서도 되나요? 가상 테스트 문서로만 검증했고, 실제 스캔·사진과 읽기 전용 파일럿이 다음 단계입니다. 2) OCR이 틀리면요? 독립 확인이 없는 값은 자동으로 받아들이지 않고 사람이 원본과 대조합니다. 처음 보는 문서에서 틀린 값은 0개였지만 실제 문서는 측정하지 않았습니다. 3) 왜 잘못된 승인이 0이라고 확신하나요? 확신하지 않습니다. 열네 건 중 0건은 95퍼센트 상한이 약 21퍼센트이고, 가상 문서 기준입니다. 4) 위·변조 서류는요? 화면과 다른 숨은 글자는 읽지 않고 확인 필요로 막았고 진위 자체는 발급기관 확인이 필요합니다. 5) 역할은 어떻게 나눴나요? 하비빌로는 백엔드·문서 분석·평가, 무니라는 UI/UX와 프론트엔드이고, 요구사항·테스트·멘토링·발표는 함께 했습니다.",
      "Prepared answers: (1) real documents: only fictional tests so far, real scans and a read-only pilot next; (2) wrong OCR: values without independent confirmation are never accepted automatically and a person compares them; 0 wrong values on unseen documents, real documents not measured; (3) why trust 0: we do not; 0/14 has a 95% upper bound of about 21%, on synthetic data; (4) tampered PDFs: hidden text is not read and is flagged, authenticity needs the issuer; (5) roles: Habibillo backend, document analysis and evaluation; Munira UI/UX and frontend; shared requirements, testing, mentoring and presentation.")
MAIN_COUNT = count

# ====================================================================== APPENDIX
def appendix_title(title):
    return new_slide("[부록] " + title, size=26)

# A1 numbers table
s = appendix_title("전체 수치와 분모")
rows = [("지표", "개발 문서", "처음 보는 문서 (hold-out 3)"),
        ("잘못된 ‘제출 가능’ (입력 유형별)", "0 / 40", "0 / 14"),
        ("디지털 PDF 필드 정확", "790 / 790", "274 / 275"),
        ("스캔 필드 정확 (틀린 값 0)", "779 / 790", "268 / 275 (이전 257)"),
        ("사진 필드 정확 (틀린 값 0)", "785 / 790", "273 / 275 (이전 264)"),
        ("대학명 스캔 / 사진", "56 / 58 · 57 / 58", "19 / 20 · 20 / 20"),
        ("사람 확인 항목 (스캔 / 사진, 1건당)", "3.73 / 3.09", "4.28 / 4.08 (이전 7.68 / 7.32)"),
        ("주입 오류: 거짓 제출 가능", "0/1,354 · 0/1,532 · 1/1,523*", "0 / 1,525"),
        ("조작 PDF 통과 / API 제출 가능", "0 / 705 · 0 / 12", "—")]
tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.4), Inches(12.2), Inches(0.52 * len(rows))).table
for i, wv in enumerate([5.0, 3.6, 3.6]):
    tbl.columns[i].width = Inches(wv)
for r_i, row in enumerate(rows):
    tbl.rows[r_i].height = Inches(0.52)
    for c_i, v in enumerate(row):
        cell = tbl.cell(r_i, c_i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r_i == 0 else (BG if r_i % 2 == 0 else WHITE)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = v
        _style(run, 18 if r_i else 18, bold=(r_i == 0 or c_i == 0), color=WHITE if r_i == 0 else INK)
text(s, 0.6, 6.25, 12.2, 0.6, [{"t": "* 알려진 잔여 위험 1건 (소유자 승인). 숫자는 모두 가상 테스트 문서 결과이며 실제 위험이 아닙니다.", "size": 16, "color": MUTED}], kind="body")
src("Full table (all rows)", "docs/midterm/RESULTS.md; docs/midterm/metrics.csv; evaluation/phase_g/results/gate_summary_dev_final.md; evaluation/phase_g/final/", "Safety, Accuracy and Automation tables; see slides 14-16")
notes(s, 0, False, "질의응답용 전체 수치 표입니다. 모든 값은 분모와 함께 적었습니다.", "Full numbers table for Q&A, with denominators.")

# A2 document types
s = appendix_title("지원하는 서류 6종과 점검 항목")
types = [("사업자등록증", "사업자등록번호 검증숫자 · 회사명"), ("중소기업확인서", "유효기간 · 회사명 · 번호 일치"), ("국세 납세증명서", "유효기간 · 지방세 증명서와 구분"),
         ("4대 사회보험료 완납증명서", "유효기간 · 사업자번호 일치"), ("재학증명서", "발급일 90일 이내 · 학번 필수"), ("성적증명서", "평점 재계산 · 학생 정보 일치")]
y = 1.45
for i, (name, checks) in enumerate(types):
    box(s, 0.6, y, 12.2, 0.78, fill=BG if i % 2 == 0 else WHITE, line=LINE, shape=MSO_SHAPE.RECTANGLE, lw=1)
    text(s, 0.8, y, 4.6, 0.78, [{"t": name, "size": 20, "bold": True, "color": NAVY}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 5.5, y, 7.2, 0.78, [{"t": checks, "size": 18, "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.88
src("Six supported document types and their checks", "docs/midterm/RESULTS.md; docs/midterm/DEMO_SCRIPT.md; evaluation/phase_g/PHASE_G_REPORT.md (GPA arithmetic)", "Mentor requirements table; demo steps")
notes(s, 0, False, "멘토님이 정의하신 서류 6종과 각각의 점검 항목입니다.", "The six mentor-defined document types and their checks.")

# A3 remaining screenshots (full slide, no callouts)
for title, name, crop in [("유사 서류(지방세 납세증명서)는 ‘확인 필요’", "S6_lookalike", (300, 240, 1320, 672)),
                          ("위·변조 PDF: 숨은 글자가 화면과 다르면 ‘확인 필요’", "S9_tampered", (300, 240, 1320, 672)),
                          ("서류가 빠지면 ‘보완 필요’ (필수 서류 누락)", "S5b_missing", (300, 240, 1320, 672)),
                          ("관리자 화면 (예정: 문서 유형 목록만 동작)", "S10_admin", (300, 0, 1320, 672))]:
    s = appendix_title(title)
    k = 11.4 / crop[2]
    s.shapes.add_picture(str(prep_image(name, crop)), Inches((SW - 11.3) / 2), Inches(1.2), width=Inches(11.3)).line.color.rgb = LINE
    if name == "S10_admin":
        chip(s, 10.4, 1.4, 2.2, "예정", AMBER_BG, AMBER_TX, size=20)
    src(f"Screenshot {name.split('_')[0]} without callouts", f"docs/midterm/v4/screenshots/{name}.png", {"S6_lookalike": "demo scenario D5", "S9_tampered": "B01 submission with one tampered 납세증명서 (see make_tampered_pdf.py)", "S5b_missing": "demo scenario D8", "S10_admin": "http://localhost:3002 (placeholder pages; only the document-type list shows data)"}[name])
    notes(s, 0, False, "질의응답용 화면입니다.", "Backup screenshot for Q&A.")

# A4 demo scenarios
s = appendix_title("시연 시나리오 D1–D9와 기대 결과")
sc = [("D1", "정상 제출 (기업)", "제출 가능", GREEN_BG, GREEN_TX), ("D2", "만료된 납세증명서", "보완 필요", RED_BG, RED_TX), ("D3", "회사명 불일치", "보완 필요", RED_BG, RED_TX),
      ("D4", "회사명 표기 차이 (주식회사/(주)/㈜)", "제출 가능", GREEN_BG, GREEN_TX), ("D5", "유사 서류 (지방세)", "확인 필요", AMBER_BG, AMBER_TX),
      ("D6", "스캔본 제출 (자동 확인)", "제출 가능", GREEN_BG, GREEN_TX), ("D7", "정상 제출 (학생)", "제출 가능", GREEN_BG, GREEN_TX),
      ("D8", "필수 서류 누락", "보완 필요", RED_BG, RED_TX), ("D9", "스캔본 + 사람 확인 (학생)", "확인 필요 → 제출 가능", AMBER_BG, AMBER_TX)]
y = 1.4
for code, name, res, bg, tx in sc:
    text(s, 0.6, y, 0.9, 0.52, [{"t": code, "size": 18, "bold": True, "color": WHITE, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    text(s, 1.65, y, 7.0, 0.52, [{"t": name, "size": 18, "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
    chip(s, 8.8, y, 4.0, res, bg, tx, size=18, h=0.52)
    y += 0.62
src("Demo scenarios D1-D9 and expected results", "docs/midterm/DEMO_SCRIPT.md; scripts/demo_scenarios.py", "SCENARIOS tuple; steps table")
notes(s, 0, False, "시연 시나리오와 기대 결과입니다. 리허설은 세 번 통과했습니다.", "Demo scenarios and expected results; the rehearsal passed three times in a row.")

# A5 sources summary
s = appendix_title("수치의 출처 (슬라이드별)")
srcs = [("4 일정·역할", "수행계획서 (외부) · git 기록 · RESULTS.md"), ("14 결과", "RESULTS.md · phase_g/final · denominators_final.txt"),
        ("15 단계별 개선", "metrics.csv · PHASE_D/D2/G 보고서"), ("16 정확도", "PHASE_G_REPORT.md §4"), ("17 어려움", "university_name_before_after.txt · pdf_manipulation_suite.md"),
        ("18 검증", "각 corpus README · F_inj_*.md · testing.md"), ("20 계획", "docs/planning/ROADMAP.md")]
y = 1.45
for a, b in srcs:
    box(s, 0.6, y, 12.2, 0.6, fill=BG, line=LINE, shape=MSO_SHAPE.RECTANGLE, lw=1)
    text(s, 0.8, y, 3.2, 0.6, [{"t": a, "size": 18, "bold": True, "color": NAVY}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 4.1, y, 8.6, 0.6, [{"t": b, "size": 16, "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.7
text(s, 0.6, 6.5, 12.2, 0.3, [{"t": "전체 목록: docs/midterm/v4/slides_sources.md", "size": 14, "color": MUTED}])
notes(s, 0, False, "슬라이드별 출처 요약입니다. 전체 표는 slides_sources.md에 있습니다.", "Per-slide source summary; the full table is slides_sources.md.")

prs.save(str(OUT))
(TMP.parent / "build_state.json").write_text(json.dumps({"body_words": BODY_WORDS, "criteria": CRITERIA, "main_count": MAIN_COUNT, "total": count, "sources": SOURCES}, ensure_ascii=False))
print("saved", OUT, "slides:", count, "main:", MAIN_COUNT)
