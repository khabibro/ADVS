"""Realistic variants of real scanned certificates (private output; deterministic per seed).

Contains no document content and no coordinates. Inputs: the original PDFs (image-only scans) and, for the
image-edit negatives, a baseline OCR dump (to find where the issue date and GPA are printed).

    python make_variants.py --originals data/private_real/originals --ocr data/private_real/results/baseline/submission_all_ocr.json \
        --out data/private_real/variants --seed-name A --seed 1001

Every variant is applied to BOTH documents with the same parameters, and each variant becomes one submission
(재학증명서 + 성적증명서) in SUBMISSIONS.json. Gold values are inherited from the originals; the expected outcome
of the negative cases is written next to them. Seeds: A = development, B = test (generated, never opened before the
final evaluation).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOREAN_FONTS = ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/Library/Fonts/NanumGothic.ttf"]
DOC_ORDER = ["재학증명서", "성적증명서"]
EVAL_DATE = "2026-08-03"


def rng_for(seed: int, *parts: str) -> np.random.Generator:
    digest = hashlib.sha256("|".join([str(seed), *parts]).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def load_scan(pdf: Path) -> np.ndarray:
    doc = fitz.open(pdf)
    info = doc.extract_image(doc.get_page_images(0)[0][0])
    return cv2.imdecode(np.frombuffer(info["image"], np.uint8), cv2.IMREAD_COLOR)


# ------------------------------------------------------------------ operations (all BGR uint8 in/out)


def op_dpi(img: np.ndarray, dpi: int, base: int = 200) -> np.ndarray:
    scale = dpi / base
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)
    return small


def op_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)


def op_binarise(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(b, cv2.COLOR_GRAY2BGR)


def op_noise(img: np.ndarray, rng: np.random.Generator, sigma: float) -> np.ndarray:
    n = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)


def op_rotate(img: np.ndarray, degrees: float) -> np.ndarray:
    if degrees in (90, 180, 270):
        return np.ascontiguousarray(np.rot90(img, k=int(degrees // 90) % 4 * -1))
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    bg = tuple(int(v) for v in np.median(img.reshape(-1, 3), axis=0))
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=bg)


def op_shear(img: np.ndarray, factor: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = np.float32([[1, factor, -factor * h / 2], [0, 1, 0]])
    bg = tuple(int(v) for v in np.median(img.reshape(-1, 3), axis=0))
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=bg)


def op_crop_margins(img: np.ndarray, fraction: float) -> np.ndarray:
    h, w = img.shape[:2]
    dy, dx = int(h * fraction), int(w * fraction)
    return img[dy:h - dy, dx:w - dx].copy()


def op_perspective(img: np.ndarray, rng: np.random.Generator, strength: float, canvas_bgr=(70, 90, 110)) -> np.ndarray:
    h, w = img.shape[:2]
    pad = int(0.06 * max(h, w))
    big_w, big_h = w + 2 * pad, h + 2 * pad
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jitter = rng.uniform(-strength, strength, (4, 2)) * np.array([w, h])
    dst = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]]) + jitter.astype(np.float32)
    m = cv2.getPerspectiveTransform(src, dst)
    canvas = np.full((big_h, big_w, 3), canvas_bgr, np.uint8)
    warped = cv2.warpPerspective(img, m, (big_w, big_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_TRANSPARENT, dst=canvas)
    return warped


def op_lighting(img: np.ndarray, rng: np.random.Generator, depth: float) -> np.ndarray:
    h, w = img.shape[:2]
    angle = rng.uniform(0, 2 * np.pi)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ramp = (np.cos(angle) * (xx / w - 0.5) + np.sin(angle) * (yy / h - 0.5))
    ramp = (ramp - ramp.min()) / (ramp.max() - ramp.min())
    vignette = 1 - 0.25 * (((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2)
    gain = (1 - depth + depth * ramp) * vignette
    return np.clip(img.astype(np.float32) * gain[..., None], 0, 255).astype(np.uint8)


def op_blur(img: np.ndarray, rng: np.random.Generator, kind: str, strength: float) -> np.ndarray:
    if kind == "defocus":
        k = int(max(3, round(strength)) // 2 * 2 + 1)
        return cv2.GaussianBlur(img, (k, k), 0)
    length = int(max(3, round(strength * 2)))
    kernel = np.zeros((length, length), np.float32)
    kernel[length // 2, :] = 1.0 / length
    m = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), float(rng.uniform(0, 180)), 1.0)
    kernel = cv2.warpAffine(kernel, m, (length, length))
    kernel /= max(kernel.sum(), 1e-6)
    return cv2.filter2D(img, -1, kernel)


def op_colour_cast(img: np.ndarray, rng: np.random.Generator, amount: float) -> np.ndarray:
    gains = 1 + rng.uniform(-amount, amount, 3)
    return np.clip(img.astype(np.float32) * gains, 0, 255).astype(np.uint8)


def jpeg_roundtrip(img: np.ndarray, quality: int) -> np.ndarray:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


# ------------------------------------------------------------------ image edits (negative cases)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in KOREAN_FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("no Korean font found for the image-edit cases")


def find_boxes(ocr: dict, doc_name: str, pattern: str, scale: float) -> list[tuple[int, int, int, int]]:
    """Boxes (x, y, w, h in the 200-dpi scan) of OCR lines whose text matches `pattern`."""
    out = []
    for line in ocr[doc_name][0]["lines"]:
        if re.search(pattern, line["text"]):
            b = line["bounding_box"]
            out.append(tuple(int(round(v * scale)) for v in (b["x"], b["y"], b["width"], b["height"])))
    return out


def paint_text(img: np.ndarray, box: tuple[int, int, int, int], text: str) -> np.ndarray:
    x, y, w, h = box
    pad = 6
    region = img[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
    ring = np.concatenate([img[max(0, y - 14):max(0, y - 6), x:x + w].reshape(-1, 3), img[y + h + 6:y + h + 14, x:x + w].reshape(-1, 3)])
    bg = tuple(int(v) for v in np.median(ring, axis=0)) if len(ring) else (255, 255, 255)
    out = img.copy()
    out[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad] = bg
    pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    font = _font(int(h * 0.95))
    draw.text((x, y - int(h * 0.1)), text, font=font, fill=(25, 25, 25))
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


# ------------------------------------------------------------------ output


def save_variant(images: dict[str, np.ndarray], out_dir: Path, vid: str, fmt: str, dpi_hint: int = 200) -> list[str]:
    """Write one file per document (or a single multi-page PDF for fmt 'pdf_multi'). Returns relative file names."""
    names = []
    if fmt == "pdf_multi":
        doc = fitz.open()
        for key in DOC_ORDER:
            img = images[key]
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            h, w = img.shape[:2]
            page = doc.new_page(width=w / dpi_hint * 72, height=h / dpi_hint * 72)
            page.insert_image(page.rect, stream=buf.tobytes())
        name = f"{vid}__combined.pdf"
        doc.save(out_dir / name)
        return [name]
    for key in DOC_ORDER:
        img = images[key]
        if fmt == "pdf":
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            h, w = img.shape[:2]
            doc = fitz.open()
            page = doc.new_page(width=w / dpi_hint * 72, height=h / dpi_hint * 72)
            page.insert_image(page.rect, stream=buf.tobytes())
            name = f"{vid}__{key}.pdf"
            doc.save(out_dir / name)
        else:
            name = f"{vid}__{key}.{fmt}"
            params = {"jpg": [cv2.IMWRITE_JPEG_QUALITY, 92], "webp": [cv2.IMWRITE_WEBP_QUALITY, 92], "png": []}[fmt]
            cv2.imwrite(str(out_dir / name), img, params)
        names.append(name)
    return names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--originals", type=Path, required=True)
    ap.add_argument("--ocr", type=Path, required=True, help="baseline OCR dump, used only to locate the date/GPA for the edit negatives")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed-name", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fictional-pair", type=Path, default=None, help="folder with a fictional 성적증명서 (any format) for the identity-mismatch negative")
    a = ap.parse_args()
    out = a.out / f"seed{a.seed_name}"
    out.mkdir(parents=True, exist_ok=True)
    base = {k: load_scan(a.originals / f"{k}.pdf") for k in DOC_ORDER}
    ocr = json.loads(a.ocr.read_text(encoding="utf-8"))
    ocr_key = {k: f"{k}.pdf" for k in DOC_ORDER}
    scale = 200 / 288
    recipe: list[dict] = []
    subs: list[dict] = []

    def add(vid: str, group: str, params: dict, build, fmt: str = "pdf", expected: str = "same_as_original", notes: str = "", eval_date: str = EVAL_DATE) -> None:
        images = {}
        for key in DOC_ORDER:
            images[key] = build(base[key].copy(), key, rng_for(a.seed, vid, key))
        files = save_variant(images, out, vid, fmt)
        recipe.append({"id": vid, "group": group, "params": params, "format": fmt, "seed": a.seed})
        subs.append({"id": vid, "group": group, "files": files, "eval_date": eval_date, "expected": expected, "notes": notes})

    # ---- scan quality
    for dpi in (150, 300):
        add(f"q_dpi{dpi}", "scan_quality", {"dpi": dpi}, lambda im, k, r, d=dpi: op_dpi(im, d))
    add("q_gray", "scan_quality", {}, lambda im, k, r: op_gray(im))
    add("q_binarised", "scan_quality", {}, lambda im, k, r: op_binarise(im))
    for q in (50, 70, 90):
        add(f"q_jpeg{q}", "scan_quality", {"jpeg_quality": q}, lambda im, k, r, q=q: jpeg_roundtrip(im, q))
    add("q_noise", "scan_quality", {"sigma": 6}, lambda im, k, r: op_noise(im, r, 6.0))
    add("q_dpi150_gray_jpeg70", "scan_quality", {"dpi": 150, "gray": True, "jpeg_quality": 70}, lambda im, k, r: jpeg_roundtrip(op_gray(op_dpi(im, 150)), 70))

    # ---- geometry
    for deg in (1, 2, 3):
        sign = 1 if rng_for(a.seed, "sign", str(deg)).random() < 0.5 else -1
        add(f"g_rot{sign * deg:+d}", "geometry", {"degrees": sign * deg}, lambda im, k, r, d=sign * deg: op_rotate(im, d))
    add("g_rot90", "geometry", {"degrees": 90}, lambda im, k, r: op_rotate(im, 90))
    add("g_rot180", "geometry", {"degrees": 180}, lambda im, k, r: op_rotate(im, 180))
    add("g_shear", "geometry", {"factor": 0.02}, lambda im, k, r: op_shear(im, 0.02))
    add("g_crop", "geometry", {"fraction": 0.012}, lambda im, k, r: op_crop_margins(im, 0.012))

    # ---- phone photo (perspective, uneven light, blur, colour cast, JPEG)
    def photo(im, k, r, strength, depth, blur_kind, blur_strength, cast):
        x = op_perspective(im, r, strength)
        x = op_lighting(x, r, depth)
        x = op_blur(x, r, blur_kind, blur_strength)
        x = op_colour_cast(x, r, cast)
        return jpeg_roundtrip(x, 85)

    presets = [("photo_mild", 0.015, 0.25, "defocus", 3, 0.05), ("photo_tilt", 0.03, 0.35, "defocus", 3, 0.08),
               ("photo_shadow", 0.02, 0.55, "defocus", 3, 0.06), ("photo_motion", 0.02, 0.3, "motion", 4, 0.05),
               ("photo_defocus", 0.02, 0.3, "defocus", 7, 0.05), ("photo_warm", 0.025, 0.4, "defocus", 3, 0.18)]
    for name, s, d, bk, bs, c in presets:
        add(name, "phone_photo", {"perspective": s, "lighting_depth": d, "blur": bk, "blur_strength": bs, "cast": c},
            lambda im, k, r, s=s, d=d, bk=bk, bs=bs, c=c: photo(im, k, r, s, d, bk, bs, c), fmt="jpg")

    # ---- formats
    for fmt in ("pdf", "jpg", "png", "webp"):
        add(f"f_{fmt}", "formats", {"format": fmt}, lambda im, k, r: im, fmt=fmt)
    add("f_pdf_multi", "formats", {"format": "one 2-page PDF with both documents"}, lambda im, k, r: im, fmt="pdf_multi",
        notes="single file holding both documents; expected to be split/classified per page")

    # ---- negative / safety cases
    date_pat = r"20\d\d\s*년\s*0?\d+\s*월\s*\d+\s*일"
    gpa_pat = r"평점평균\s*[:：]?\s*3\.62"

    def edit_date(im, key, r):
        boxes = [b for b in find_boxes(ocr, ocr_key[key], date_pat, scale) if True]
        # the issue date is the LAST date-like line above the issuer block (largest y among matches printed alone)
        boxes.sort(key=lambda b: b[1])
        target = boxes[-1] if boxes else None
        return paint_text(im, target, "2026년 08월 29일") if target else im

    add("n_date_edited", "negative", {"edit": "issue date painted over in both documents (2026-07-29 -> 2026-08-29)"}, edit_date,
        expected="no wrong value auto-accepted; never READY unless a person confirms the (wrong) printed date",
        notes="the edited date is a visible forgery of the printed value; the system may read it correctly as printed, but must not accept it without a person")

    def edit_gpa(im, key, r):
        if key != "성적증명서":
            return im
        boxes = find_boxes(ocr, ocr_key[key], gpa_pat, scale)
        return paint_text(im, boxes[-1], "평점평균 : 3.92/4.5 백분율 : 90.00/100") if boxes else im

    add("n_gpa_edited", "negative", {"edit": "cumulative GPA 3.62 -> 3.92 in the transcript"}, edit_gpa,
        expected="the wrong GPA must not be auto-accepted", notes="GPA edited in the image")

    add("n_expired_boundary_valid", "negative", {"eval_date": "2026-10-27"}, lambda im, k, r: im, eval_date="2026-10-27",
        expected="issue-date rule passes (age 90 days, inclusive); status as for the original at that date")
    add("n_expired_boundary_expired", "negative", {"eval_date": "2026-10-28"}, lambda im, k, r: im, eval_date="2026-10-28",
        expected="ISSUE_DATE_TOO_OLD (age 91) -> 보완 필요 (NEEDS_CORRECTION)")
    add("n_duplicate_upload", "negative", {"duplicate": "the 재학증명서 uploaded twice"}, lambda im, k, r: im,
        expected="duplicate notice; never READY", notes="builder adds the second copy of the first file to the submission")
    subs[-1]["files"] = [subs[-1]["files"][0], subs[-1]["files"][0], subs[-1]["files"][1]]

    # hidden text: an image-only PDF gets an invisible text layer with a different date (render mode 3)
    add("n_hidden_text", "negative", {"hidden_text": "invisible date 2026-09-30 in the PDF text layer"}, lambda im, k, r: im,
        expected="TEXT_LAYER_MISMATCH or OCR used; never READY")
    for fname in subs[-1]["files"]:
        doc = fitz.open(out / fname)
        page = doc[0]
        page.insert_text((60, 120), "Issued 2026-09-30 / 2026.09.30", fontsize=12, render_mode=3, fontname="helv")
        tmp = out / (fname + ".tmp")
        doc.save(tmp)
        doc.close()
        tmp.replace(out / fname)

    if a.fictional_pair is not None:
        pair = sorted(p for p in a.fictional_pair.iterdir() if p.is_file())
        if pair:
            subs.append({"id": "n_identity_mismatch", "group": "negative", "files": ["__REAL_ENROLMENT__", pair[0].name],
                         "eval_date": EVAL_DATE, "copy_from": str(pair[0]),
                         "expected": "NEEDS_CORRECTION (보완 필요): the two documents name different students",
                         "notes": "real 재학증명서 + a FICTIONAL 성적증명서 of another student"})
            (out / pair[0].name).write_bytes(pair[0].read_bytes())
            subs[-1]["files"][0] = f"f_pdf__{DOC_ORDER[0]}.pdf"  # the real 재학증명서 as an image-only PDF

    (out / "SUBMISSIONS.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "RECIPE.json").write_text(json.dumps({"seed_name": a.seed_name, "seed": a.seed, "eval_date_default": EVAL_DATE, "variants": recipe,
                                                 "note": "variants of the same two documents are correlated: they test robustness, not generalisation to other people's documents"},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"seed {a.seed_name}: {len(subs)} submissions, {len(list(out.iterdir()))} files in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
