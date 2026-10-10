"""Shared loaders for the OCR-vs-VLM comparison (research code; reads the app, never changes it).

Run with the app's interpreter and PYTHONPATH=<checkout>/apps/api. All paths come from the command
line; hold-out 3 is only reachable with ADVS_FINAL_JUDGEMENT=1.
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

CORPUS_DIRS = {"dev": "test_variants", "holdout": "holdout", "holdout2": "holdout2", "holdout3": "holdout3"}
HIGH_RISK = {"business_registration_number", "valid_from", "valid_until", "issue_date", "gpa", "student_id"}
NUMERIC_DATE = HIGH_RISK | {"gpa_scale"}


def guard(corpus: str) -> None:
    if corpus == "holdout3" and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
        raise SystemExit("hold-out 3 is for the single final run only (ADVS_FINAL_JUDGEMENT=1)")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(k: int, n: int) -> str:
    if n == 0:
        return "n/a (n=0)"
    lo, hi = wilson(k, n)
    extra = (f", rule of three ≤{3 / n:.1%}" if 3 / n < 1 else ", n too small for a bound") if k == 0 else ""
    return f"{k}/{n} = {k / n:.1%} [{lo:.1%}–{hi:.1%}]{extra}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_type(rel: str, style: str | None) -> str:
    return {"digital": "digital", "scanned": "scan", "images": "photo"}.get(style or "", style or "other")


def load_manifest(synth: Path, corpus: str) -> list[dict]:
    guard(corpus)
    data = json.loads((synth / CORPUS_DIRS[corpus] / "manifest.json").read_text(encoding="utf-8"))
    return [f for f in data["files"] if f.get("expected_fields") and f["file"].lower().rsplit(".", 1)[-1] in {"pdf", "jpg", "jpeg", "png", "webp"}]
