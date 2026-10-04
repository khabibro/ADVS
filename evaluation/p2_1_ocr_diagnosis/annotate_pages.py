"""P2.1 annotation surface builder.

Two deliberately separate views of the exact OCR input page:

* ``grid``  -- normalized coordinate grid only. Used for the blind pass: where
  a human can see a label and a value, recorded before any OCR geometry is
  visible, so the annotation cannot be anchored onto OCR output.
* ``boxes`` -- the same grid plus every OCR observation rectangle. Used only
  afterwards, to score the blind annotation.

Everything is written to the ignored runtime directory.

Usage:
    python annotate_pages.py grid
    python annotate_pages.py boxes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUNTIME = Path("evaluation/private_runtime/p2_1")
PAGES_DIR = RUNTIME / "pages"
MAX_VIEW_SIDE = 1500
GRID_STEP = 0.05
MAJOR_STEP = 0.10


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_grid(image: Image.Image) -> Image.Image:
    canvas = image.convert("RGB").copy()
    width, height = canvas.size
    scale = MAX_VIEW_SIDE / max(width, height)
    if scale < 1:
        canvas = canvas.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(canvas, "RGBA")
    vw, vh = canvas.size
    font = load_font(max(11, int(min(vw, vh) * 0.018)))

    minor = max(1, round(min(vw, vh) * 0.0016))
    major = max(2, round(min(vw, vh) * 0.0032))

    steps = round(1.0 / GRID_STEP)
    for index in range(steps + 1):
        fraction = index * GRID_STEP
        is_major = abs(fraction / MAJOR_STEP - round(fraction / MAJOR_STEP)) < 1e-6
        colour = (255, 40, 40, 150) if is_major else (60, 110, 220, 85)
        width_px = major if is_major else minor
        x = fraction * vw
        draw.line([(x, 0), (x, vh)], fill=colour, width=width_px)
        draw.line([(0, x), (vw, x)], fill=colour, width=width_px)
        if is_major:
            percent = round(fraction * 100)
            draw.text((x + 2, 2), f"x{percent}", fill=(200, 0, 0, 255), font=font)
            draw.text((2, x + 2), f"y{percent}", fill=(200, 0, 0, 255), font=font)
    return canvas


def draw_observations(image: Image.Image, lines: list[dict]) -> Image.Image:
    canvas = image.convert("RGB").copy()
    width, height = canvas.size
    scale = MAX_VIEW_SIDE / max(width, height)
    if scale < 1:
        canvas = canvas.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(canvas, "RGBA")
    vw, vh = canvas.size
    font = load_font(max(10, int(min(vw, vh) * 0.014)))
    stroke = max(1, round(min(vw, vh) * 0.0018))

    for index, line in enumerate(lines, start=1):
        box = line.get("bbox")
        if not box:
            continue
        x0 = box["x"] * scale
        y0 = box["y"] * scale
        x1 = (box["x"] + box["width"]) * scale
        y1 = (box["y"] + box["height"]) * scale
        confidence = line.get("confidence")
        low = confidence is not None and confidence < 0.90
        colour = (255, 140, 0, 235) if low else (0, 170, 60, 235)
        draw.rectangle([x0, y0, x1, y1], outline=colour, width=stroke)
        tag = f"{index}"
        if confidence is not None:
            tag += f" {confidence:.2f}"
        draw.text((x0 + 1, max(0, y0 - font.size - 1)), tag, fill=colour, font=font)
    return canvas


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "grid"
    observations = json.loads(
        (RUNTIME / "observations_private.json").read_text(encoding="utf-8")
    )
    out_dir = RUNTIME / ("grid" if mode == "grid" else "boxes")
    out_dir.mkdir(parents=True, exist_ok=True)

    for document in observations["documents"]:
        for page in document["pages"]:
            source = Path(
                next(
                    image["image_path"]
                    for image in document["captured_input_images"]
                    if image["page_number"] == page["page_number"]
                )
            )
            with Image.open(source) as image:
                rendered = (
                    draw_grid(image)
                    if mode == "grid"
                    else draw_observations(image, page["lines"])
                )
            target = (
                out_dir / f"{document['sample_id']}_p{page['page_number']}_{mode}.png"
            )
            rendered.save(target)
            print(
                f"wrote {target} ({rendered.size[0]}x{rendered.size[1]}, {len(page['lines'])} obs)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
