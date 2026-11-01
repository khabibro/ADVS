"""v3 additions to the development set: S11 (two different universities, same student name and number).

The v2 files are never touched. S11 is derived from S01 (the generator's own enrolment and transcript):
  * the enrolment certificate is S01's, unchanged (university A);
  * the transcript is S01's with the letter-spaced issuer name replaced by another fictional university B at
    character level (the text layer stays real, so the digital version exercises the embedded-text path);
  * scanned and photo versions use the generator's scan_effect / save_image_pdf and the S01 image-format cycle.
Run (from apps/api, which has PyMuPDF and Pillow):
    python gen_v3_additions.py --root <test_variants dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_test_variants as g  # noqa: E402  (module-level helpers only; main() is not run)

OLD_UNIVERSITY = "한국가상대학교"
NEW_UNIVERSITY = "새빛가상대학교"
SET_DIR = "S11_university_differs"
SCEN_DPI = 170
SEED = 20261105


def replace_letter_spaced(page: fitz.Page, old: str, new: str) -> bool:
    """Replace a letter-spaced printed name by another, glyph by glyph over the same span of the line."""
    chars = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for ch in span["chars"]:
                    if ch["c"].strip():
                        chars.append((ch["c"], fitz.Rect(ch["bbox"]), span["size"], ch["origin"]))
    letters = "".join(c[0] for c in chars)
    start = letters.find(old)
    if start < 0:
        return False
    run = chars[start : start + len(old)]
    rect = run[0][1]
    for item in run[1:]:
        rect |= item[1]
    size, baseline = run[0][2], run[0][3][1]
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    step = (rect.width - size) / (len(new) - 1)
    for index, glyph in enumerate(new):
        page.insert_text((rect.x0 + index * step, baseline), glyph, fontsize=size, fontname="korea")
    return True


def rasterize(pdf: Path, dpi: int) -> list[Image.Image]:
    out = []
    for page in fitz.open(pdf):
        pix = page.get_pixmap(dpi=dpi)
        out.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return out


def save_scan_image(im: Image.Image, path_noext: Path, fmt: str) -> Path:
    path_noext.parent.mkdir(parents=True, exist_ok=True)
    p = path_noext.with_suffix("." + fmt)
    if fmt == "jpg":
        im.save(p, "JPEG", quality=60)
    elif fmt == "webp":
        im.save(p, "WEBP", quality=75)
    else:
        w, h = im.size
        im.convert("L").resize((int(w * 0.88), int(h * 0.88)), Image.LANCZOS).save(p, "PNG", optimize=True)
    return p


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    a = ap.parse_args()
    root = a.root
    src = root / "student" / "S01_all_valid"
    dst = root / "student" / SET_DIR
    if dst.exists():
        raise SystemExit(f"{dst} exists; refusing to overwrite")
    rng = np.random.default_rng(SEED)
    cycle = ["jpg", "png", "webp"]
    names = {1: "재학증명서", 2: "성적증명서"}
    made: dict[str, list[str]] = {"digital": [], "scanned": [], "images": []}
    (dst / "digital").mkdir(parents=True)
    for n in (1, 2):
        out = dst / "digital" / f"S11-{n}_{names[n]}.pdf"
        shutil.copyfile(src / "digital" / f"S01-{n}_{names[n]}.pdf", out)
        if n == 2:
            doc = fitz.open(out)
            assert replace_letter_spaced(doc[0], OLD_UNIVERSITY, NEW_UNIVERSITY), "issuer name not found"
            tmp = out.with_suffix(".tmp")
            doc.save(tmp, garbage=3, deflate=True)
            doc.close()
            tmp.replace(out)
        made["digital"].append(str(out.relative_to(root)))
        digital = out
        scan_imgs = [g.scan_effect(im, rng) for im in rasterize(digital, SCEN_DPI)]
        scanned = dst / "scanned" / f"S11-{n}_{names[n]}_스캔.pdf"
        g.save_image_pdf(scan_imgs, scanned, SCEN_DPI)
        made["scanned"].append(str(scanned.relative_to(root)))
        fmt = cycle[(n - 1) % 3]
        photo = g.scan_effect(rasterize(digital, SCEN_DPI)[0], rng, noise=0.0 if fmt == "png" else 1.0)
        made["images"].append(str(save_scan_image(photo, dst / "images" / f"S11-{n}_{names[n]}_사진", fmt).relative_to(root)))
    # manifest entries (derived from S01's, with the university changed on the transcript)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    template = {e["file"]: e for e in manifest["files"]}
    entries = []
    for style, files in made.items():
        for n, rel in enumerate(files, 1):
            old_rel = next(f for f in template if f.startswith("student/S01_all_valid/" + style + "/S01-" + str(n) + "_"))
            entry = json.loads(json.dumps(template[old_rel]))
            entry.update(file=rel, set_id="S11", sha256=sha(root / rel), bytes=(root / rel).stat().st_size)
            if n == 2:
                entry["expected_fields"]["university_name"] = {"state": "KNOWN_VALUE", "value": NEW_UNIVERSITY, "printed": NEW_UNIVERSITY}
                entry["note"] = "derived from S01-2: issuer university replaced (v3 addition)"
            entry["provenance"] = "SYNTHETIC_VARIANT (v3 addition derived from S01)"
            if style == "digital":
                entry["_verify_printed"] = []
            entries.append(entry)
    (dst / "v3_additions.json").write_text(
        json.dumps({"set_dir": SET_DIR, "files": made, "entries": entries, "seed": SEED}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print({k: len(v) for k, v in made.items()}, "entries:", len(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
