"""Choose the page rotation from what the OCR itself reads.

A certificate photographed or scanned sideways or upside down is read badly by the
detector and, worse, the built-in angle classifier is not reliable on a flat page
(measured on rotated flat pages: "no angle" for 180 degrees, the opposite direction
for 270). Reading the page in all four rotations and keeping the one that reads best
does not depend on the classifier: upright text produces long, confident Hangul runs
and recognisable certificate words; text read upside down produces neither.

Pure functions only: the provider runs the OCR, this module scores and decides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.document_intelligence.ocr.models import OCRLine

ROTATIONS = (0, 90, 180, 270)

#: Generic certificate vocabulary (field and form words, no institution or person names).
#: Reading a few of these in one rotation and none in the others is strong evidence.
FORM_WORDS = (
    "증명", "성명", "성적", "학번", "학과", "학년", "학점", "평점", "과목", "발급", "발행",
    "대학", "학교", "등록번호", "상호", "대표자", "사업자", "주소", "소재지", "생년월일",
    "기간", "확인", "납세", "조회", "구분", "법인", "재학", "졸업", "휴학", "년", "월",
)  # fmt: skip
_LABEL_CAP = 6
#: A rotation must read at least this much better than the runner-up to win outright.
TIE_MARGIN = 0.10

_HANGUL = re.compile(r"[가-힣]")


@dataclass(frozen=True)
class RotationEvidence:
    mean_confidence: float
    hangul_chars: int
    hangul_ratio: float
    label_hits: int

    @property
    def quality(self) -> float:
        """Hangul characters weighted by how confidently they were read."""
        return self.hangul_chars * self.mean_confidence


def evidence_for(lines: list[OCRLine]) -> RotationEvidence:
    kept = [line for line in lines if line.text.strip()]
    if not kept:
        return RotationEvidence(0.0, 0, 0.0, 0)
    confidences = [line.confidence if line.confidence is not None else 0.5 for line in kept]
    joined = "".join(line.text for line in kept)
    compact = re.sub(r"\s+", "", joined)
    hangul = len(_HANGUL.findall(compact))
    hits = sum(1 for word in FORM_WORDS if word in compact)
    return RotationEvidence(
        mean_confidence=sum(confidences) / len(confidences),
        hangul_chars=hangul,
        hangul_ratio=hangul / len(compact) if compact else 0.0,
        label_hits=min(hits, _LABEL_CAP),
    )


def pick_rotation(candidates: dict[int, RotationEvidence]) -> int | None:
    """The rotation that reads clearly best, or None when the evidence is a tie.

    Ranking: the number of certificate words read first, then the confidence-weighted
    Hangul count. Upright (0) is the default: another rotation must beat it, not just
    match it. A tie returns None and the caller keeps its existing detector.
    """
    if not candidates:
        return None
    ranked = sorted(candidates.items(), key=lambda item: _rank(item[1]), reverse=True)
    best_rotation, best = ranked[0]
    if best.hangul_chars == 0:
        return None
    if len(ranked) > 1:
        runner = ranked[1][1]
        if best.label_hits == runner.label_hits and best.quality < runner.quality * (
            1 + TIE_MARGIN
        ):
            return None
    return best_rotation


def _rank(evidence: RotationEvidence) -> tuple[int, float]:
    return evidence.label_hits, evidence.quality


def looks_unread(evidence: RotationEvidence) -> bool:
    """A first pass that read no certificate word, or little Hangul, may be sideways."""
    return evidence.label_hits == 0 or evidence.hangul_ratio < 0.4


_TRANSPOSE = {
    90: Image.Transpose.ROTATE_90,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_270,
}


def rotate_image(src: Path, dst: Path, degrees: int) -> Path:
    """Write `src` rotated counter-clockwise by `degrees` (90/180/270) to `dst`, losslessly."""
    with Image.open(src) as image:
        rotated = image.transpose(_TRANSPOSE[degrees])
        rotated.save(dst, format="PNG")
    return dst


def crop_centre(src: Path, dst: Path, fraction: float) -> Path:
    """Write the centre `fraction` (of each side) of `src` to `dst`: a cheap sample of the page for scoring.

    The centre of an image stays the centre under 90/180/270 rotation, so the same crop of each rotated copy is
    the same region of the page, read in four directions."""
    with Image.open(src) as image:
        width, height = image.size
        margin_x, margin_y = int(width * (1 - fraction) / 2), int(height * (1 - fraction) / 2)
        image.crop((margin_x, margin_y, width - margin_x, height - margin_y)).save(
            dst, format="PNG"
        )
    return dst
