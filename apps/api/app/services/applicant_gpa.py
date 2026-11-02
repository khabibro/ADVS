"""The 평점평균 an applicant may type next to the transcript slot ("3.40" or "3.40 / 4.3").

It is only ever used to confirm what OCR read, by exact numeric agreement (auto_acceptance route B); it never
replaces a read value. Parsing is strict: anything that is not a plausible GPA (and scale) is rejected with a
message the applicant can act on."""

from __future__ import annotations

import re

_PATTERN = re.compile(r"^(\d(?:\.\d{1,2})?)\s*(?:/\s*(\d(?:\.\d{1,2})?))?$")
_SCALES = (4.0, 4.3, 4.5)


class ApplicantGpaError(ValueError):
    pass


def parse_applicant_gpa(text: str | None) -> tuple[str | None, str | None]:
    """(gpa, scale) as normalised strings ("3.40", "4.3"); (None, None) for an empty entry."""
    if text is None or not text.strip():
        return None, None
    cleaned = text.strip().replace(",", ".").replace("／", "/").replace("．", ".")
    match = _PATTERN.match(cleaned)
    if not match:
        raise ApplicantGpaError("평점평균은 3.40 또는 3.40 / 4.3 형식으로 입력해 주세요.")
    gpa = float(match.group(1))
    scale = float(match.group(2)) if match.group(2) else None
    if scale is not None and scale not in _SCALES:
        raise ApplicantGpaError("만점 기준은 4.0, 4.3, 4.5 중 하나여야 합니다.")
    if gpa <= 0 or gpa > (scale or max(_SCALES)):
        raise ApplicantGpaError("평점평균이 만점 기준보다 클 수 없습니다.")
    return f"{gpa:.2f}", (f"{scale:.1f}" if scale is not None else None)


def format_applicant_gpa(gpa: str | None, scale: str | None) -> str | None:
    if gpa is None:
        return None
    return f"{gpa} / {scale}" if scale else gpa
