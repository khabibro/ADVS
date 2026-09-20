"""Deterministic layout arrangement of (label, value) pairs into text lines.

These layouts are chosen specifically because the extraction architecture
(`after_label` in app/document_intelligence/extraction/base.py) matches a
label to the *rest of its own line* -- so "vertical" and "compact" layouts
are expected, honest stress tests of that specific implementation choice,
not arbitrary noise.
"""

import random

LAYOUTS = ["standard", "table", "reordered", "vertical", "compact"]

# Label text mutated to a whitespace-variant form, applied to a deterministic
# subset of samples to stress-test extraction's label matching (which -- unlike
# classification -- does not currently tolerate internal whitespace variation).
LABEL_SPACING_VARIANTS: dict[str, str] = {
    "사업자등록번호": "사업자 등록번호",
    "등록번호": "등록 번호",
    "발급일자": "발급 일자",
    "유효기간": "유효 기간",
    "졸업일자": "졸업 일자",
    "재직기간": "재직 기간",
    "근무기간": "근무 기간",
}


def maybe_space_label(label: str, apply: bool) -> str:
    if not apply:
        return label
    return LABEL_SPACING_VARIANTS.get(label, label)


def build_lines(
    title: str, pairs: list[tuple[str, str]], layout: str, rng: random.Random
) -> list[str]:
    lines = [title] if title else []
    if layout == "vertical":
        for label, value in pairs:
            lines.append(label)
            lines.append(value)
        return lines
    if layout == "compact":
        i = 0
        while i < len(pairs):
            chunk = pairs[i : i + 2]
            lines.append("   ".join(f"{label} {value}" for label, value in chunk))
            i += 2
        return lines
    if layout == "table":
        lines.extend(f"{label}: {value}" for label, value in pairs)
        return lines
    if layout == "reordered":
        shuffled = list(pairs)
        rng.shuffle(shuffled)
        lines.extend(f"{label} {value}" for label, value in shuffled)
        return lines
    # standard
    lines.extend(f"{label} {value}" for label, value in pairs)
    return lines
