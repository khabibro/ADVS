"""Error-injection suite (the stress test).

Takes the *real* OCR observations recorded for the scanned / image documents of the
development set and injects high-confidence errors at observation level
(confidence drawn from 0.95-0.999). The rest of the real pipeline then runs
unchanged: extraction -> evidence policy -> auto-acceptance -> validation -> status.

Frozen at Phase D step D2; its SHA-256 (and the seed) are recorded in every report.

Error types
-----------
E1   one visually confusable digit in the business number (0<->8, 1<->7, 3<->8, 5<->6, 6<->8, 2<->7)
       scope: one document
E2   the same substitution as E1 on every document of the submission (correlated)
E3   two adjacent digits of the business number transposed      (one document / every document)
E3c  like E3 but chosen so the check digit still passes (adversarial)   (one / every)
E4   one digit of the business number dropped or duplicated    (one document)
E5   a similar-looking Korean character in the student name     (one document / every document)
E6   a date digit confusion that turns an expired validity date into a valid one, or a too-old
       issue date into a recent one (one document)
E7   one character changed in the company name                  (one document / every document)
E8   a GPA digit change that crosses the 3.0 threshold          (one document)
E9   one digit changed in the student number                    (one document)

Variants
--------
"both-passes": the same error is also applied to the second-pass reading of that field
(common-mode failure: the second read of the same glyph is wrong in the same way).

Metrics per case
----------------
false auto-accept   the system acts on (auto-accepts) a value that differs from the manifest truth
false READY         submission READY while an acted-on value is wrong, or while the digital
                    expectation of the set is not READY
detected            the injected field was not auto-accepted (a human is asked)

Deterministic: every random choice is seeded from SEED and the case id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_v2  # noqa: E402
from harness_core import REPO_ROOT, Runner, git_head, sha256_file  # noqa: E402

SEED = 20261005
CONF_RANGE = (0.95, 0.999)
SCRIPT_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

DIGIT_CONFUSIONS: dict[str, list[str]] = {
    "0": ["8"],
    "8": ["0", "3", "6"],
    "1": ["7"],
    "7": ["1", "2"],
    "3": ["8"],
    "5": ["6"],
    "6": ["5", "8"],
    "2": ["7"],
}
# similar-looking Hangul syllables (both directions are listed explicitly)
HANGUL_CONFUSIONS: dict[str, list[str]] = {
    "박": ["막"], "막": ["박"], "정": ["청"], "청": ["정"], "김": ["길"], "길": ["김"],
    "샘": ["셈"], "셈": ["샘"], "이": ["미"], "미": ["이"], "최": ["초"], "초": ["최"],
    "한": ["안"], "안": ["한"], "상": ["성"], "성": ["상"], "사": ["자"], "자": ["사"],
    "테": ["데"], "데": ["테"], "스": ["소"], "소": ["스"], "트": ["드"], "드": ["트"],
    "솔": ["술"], "술": ["솔"], "루": ["두"], "두": ["루"], "나": ["너"], "너": ["나"],
    "다": ["더"], "더": ["다"], "가": ["거"], "거": ["가"], "빛": ["빚"], "빚": ["빛"],
    "래": ["레"], "레": ["래"], "플": ["풀"], "풀": ["플"], "윤": ["운"], "운": ["윤"],
}
BRN_RE = re.compile(r"(?<!\d)(\d)(\d)(\d)\D{0,3}(\d)(\d)\D{0,3}(\d)(\d)(\d)(\d)(\d)(?!\d)")
DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(\s*[.\-/년]\s*)(\d{1,2})(\s*[.\-/월]\s*)(\d{1,2})(?!\d)")


def stable_rng(*parts: object) -> random.Random:
    digest = hashlib.sha256(("|".join(str(p) for p in (SEED, *parts))).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def brn_valid(digits: str) -> bool:
    weights = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    numbers = [int(c) for c in digits]
    if len(numbers) != 10:
        return False
    total = sum(d * w for d, w in zip(numbers[:9], weights, strict=True)) + numbers[8] * 5 // 10
    return (10 - total % 10) % 10 == numbers[9]


# ----------------------------------------------------------------------------- edits


@dataclass
class Edit:
    """A mutation of text that contains the target value. `apply` returns the new text or None."""

    kind: str
    field_name: str
    expected: str
    wrong: str
    description: str
    apply: Callable[[str], str | None] = field(repr=False, default=lambda text: None)


def _replace_digits_in_span(text: str, match: re.Match[str], new_digits: str) -> str:
    """Replace the digit characters inside the matched span, in order, keeping separators.
    Different length -> rebuild the span from the plain digits."""
    span = match.group(0)
    positions = [i for i, ch in enumerate(span) if ch.isdigit()]
    if len(new_digits) == len(positions):
        chars = list(span)
        for pos, digit in zip(positions, new_digits, strict=True):
            chars[pos] = digit
        replaced = "".join(chars)
    else:
        replaced = new_digits
    return text[: match.start()] + replaced + text[match.end() :]


def brn_edit(expected: str, new: str, kind: str, description: str, field_name: str = "business_registration_number") -> Edit:
    def apply(text: str) -> str | None:
        for match in BRN_RE.finditer(text):
            if "".join(match.groups()) == expected:
                return _replace_digits_in_span(text, match, new)
        return None

    return Edit(kind, field_name, expected, new, description, apply)


def digit_run_edit(expected: str, new: str, kind: str, description: str, field_name: str) -> Edit:
    def apply(text: str) -> str | None:
        index = text.find(expected)
        if index < 0:
            return None
        return text[:index] + new + text[index + len(expected) :]

    return Edit(kind, field_name, expected, new, description, apply)


def date_edit(expected_iso: str, new_iso: str, description: str, field_name: str) -> Edit:
    def apply(text: str) -> str | None:
        for match in DATE_RE.finditer(text):
            year, sep1, month, sep2, day = match.groups()
            try:
                found = date(int(year), int(month), int(day)).isoformat()
            except ValueError:
                continue
            if found != expected_iso:
                continue
            ny, nm, nd = new_iso.split("-")
            width_m, width_d = len(month), len(day)
            replacement = f"{ny}{sep1}{int(nm):0{width_m}d}{sep2}{int(nd):0{width_d}d}"
            return text[: match.start()] + replacement + text[match.end() :]
        return None

    return Edit("E6", field_name, expected_iso, new_iso, description, apply)


def spaced_pattern(core: str) -> re.Pattern[str]:
    return re.compile(r"\s*".join(re.escape(ch) for ch in core))


def text_edit(core: str, index: int, new_char: str, kind: str, field_name: str, description: str) -> Edit:
    pattern = spaced_pattern(core)
    wrong = core[:index] + new_char + core[index + 1 :]

    def apply(text: str) -> str | None:
        match = pattern.search(unicodedata.normalize("NFC", text))
        if not match:
            return None
        normalized = unicodedata.normalize("NFC", text)
        span = match.group(0)
        positions = [i for i, ch in enumerate(span) if not ch.isspace()]
        chars = list(span)
        chars[positions[index]] = new_char
        return normalized[: match.start()] + "".join(chars) + normalized[match.end() :]

    return Edit(kind, field_name, core, wrong, description, apply)


def confusable_char(ch: str, rng: random.Random) -> str | None:
    options = HANGUL_CONFUSIONS.get(ch)
    if options:
        return rng.choice(options)
    if "가" <= ch <= "힣":  # generic: swap the medial vowel ㅏ <-> ㅓ
        medial = ((ord(ch) - 0xAC00) // 28) % 21
        if medial == 0:
            return chr(ord(ch) + 4 * 28)
        if medial == 4:
            return chr(ord(ch) - 4 * 28)
    return None


def gpa_edit(expected: str, scale: str, description: str) -> Edit | None:
    value = float(expected)
    if value < 3.0:
        wrong = f"{value + 1.0:.2f}"
    else:
        wrong = f"{min(float(scale) - 0.1, value + 0.7):.2f}"
    if wrong == expected:
        return None
    candidates = {expected, f"{value:.2f}", f"{value:.1f}"}

    def apply(text: str) -> str | None:
        for token in sorted(candidates, key=len, reverse=True):
            index = text.find(token)
            if index >= 0:
                return text[:index] + wrong + text[index + len(token) :]
        return None

    return Edit("E8", "gpa", expected, wrong, description, apply)


# ----------------------------------------------------------------------------- case planning


@dataclass
class Case:
    case_id: str
    error: str
    scope: str  # one | all
    set_id: str
    version: str
    both_passes: bool
    edits: dict[str, list[Edit]]  # sha256 -> edits
    targets: list[tuple[str, str, str]]  # (sha256, relative file, field)
    note: str = ""


def load_cache_lines(cache_dir: Path, digest: str) -> list[str] | None:
    path = cache_dir / f"{digest}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if "error" in data:
        return None
    return [line["text"] for page in data["pages"] for line in page["lines"]]


def applicable(edit: Edit, lines: list[str]) -> bool:
    return any(edit.apply(line) is not None for line in lines)


class Planner:
    def __init__(self, manifest: dict[str, Any], root: Path, cache_dir: Path, max_per_submission: int = 2) -> None:
        self.manifest = manifest
        self.root = root
        self.cache = cache_dir
        self.by_file = {e["file"]: e for e in manifest["files"]}
        self.max_per = max_per_submission
        self.digest: dict[str, str] = {}
        self.submission_date = date.fromisoformat(manifest["submission_date"])

    def _digest(self, rel: str) -> str:
        if rel not in self.digest:
            self.digest[rel] = sha256_file(self.root / rel)
        return self.digest[rel]

    def _docs(self, set_id: str, scenario: dict[str, Any], version: str, field_names: tuple[str, ...]):
        for rel in scenario["files"].get(version, []):
            entry = self.by_file.get(rel, {})
            for name in field_names:
                spec = entry.get("expected_fields", {}).get(name)
                if spec and spec.get("state") == "KNOWN_VALUE":
                    yield rel, name, spec["value"]
                    break

    # -- per-error builders (return an Edit for one document or None) ------

    def _brn_sub(self, expected: str, rng: random.Random, fixed: tuple[int, str] | None) -> tuple[Edit | None, tuple[int, str] | None]:
        digits = re.sub(r"\D", "", expected)
        if fixed is None:
            options = [(i, s) for i, d in enumerate(digits) for s in DIGIT_CONFUSIONS.get(d, [])]
            if not options:
                return None, None
            fixed = rng.choice(options)
        position, substitute = fixed
        if position >= len(digits) or digits[position] not in DIGIT_CONFUSIONS:
            return None, fixed
        new = digits[:position] + substitute + digits[position + 1 :]
        return brn_edit(digits, new, "E1", f"digit {position + 1}: {digits[position]}->{substitute}"), fixed

    def _brn_transpose(self, expected: str, rng: random.Random, checksum_preserving: bool, fixed: int | None) -> tuple[Edit | None, int | None]:
        digits = re.sub(r"\D", "", expected)
        pairs = [i for i in range(len(digits) - 1) if digits[i] != digits[i + 1]]
        if checksum_preserving:
            pairs = [i for i in pairs if brn_valid(digits[:i] + digits[i + 1] + digits[i] + digits[i + 2 :])]
        if fixed is not None:
            pairs = [i for i in pairs if i == fixed]
        if not pairs:
            return None, None
        i = rng.choice(pairs)
        new = digits[:i] + digits[i + 1] + digits[i] + digits[i + 2 :]
        kind = "E3c" if checksum_preserving else "E3"
        return brn_edit(digits, new, kind, f"digits {i + 1},{i + 2} transposed"), i

    def _brn_drop_dup(self, expected: str, rng: random.Random) -> Edit | None:
        digits = re.sub(r"\D", "", expected)
        i = rng.randrange(len(digits))
        if rng.random() < 0.5:
            new, how = digits[:i] + digits[i + 1 :], f"digit {i + 1} dropped"
        else:
            new, how = digits[: i + 1] + digits[i] + digits[i + 1 :], f"digit {i + 1} duplicated"
        return brn_edit(digits, new, "E4", how)

    def _name_edit(self, name: str, kind: str, field_name: str, rng: random.Random, fixed: tuple[int, str] | None):
        compact = "".join(name.split())
        if fixed is None:
            options = []
            for i, ch in enumerate(compact):
                for sub in ([confusable_char(ch, rng)] if confusable_char(ch, rng) else []):
                    options.append((i, sub))
            if not options:
                return None, None
            fixed = rng.choice(options)
        index, new_char = fixed
        if index >= len(compact):
            return None, fixed
        return text_edit(compact, index, new_char, kind, field_name, f"char {index + 1}: {compact[index]}->{new_char}"), fixed

    def _company_edit(self, name: str, rng: random.Random, fixed: tuple[int, str] | None):
        # work on the core (without 주식회사 / (주) / ㈜ ...), as OCR prints the core contiguously
        from app.document_intelligence.normalization.field_normalizer import strip_legal_entity_markers

        core = "".join(strip_legal_entity_markers(unicodedata.normalize("NFKC", name)).split())
        return self._name_edit(core, "E7", "company_name", rng, fixed)

    def _date_edit(self, field_name: str, expected: str, rng: random.Random) -> Edit | None:
        expected_date = date.fromisoformat(expected)
        digits_pos = [i for i, ch in enumerate(expected) if ch.isdigit()]
        flips = []
        for i in digits_pos:
            for sub in DIGIT_CONFUSIONS.get(expected[i], []):
                text = expected[:i] + sub + expected[i + 1 :]
                try:
                    candidate = date.fromisoformat(text)
                except ValueError:
                    continue
                if field_name == "valid_until":
                    if expected_date < self.submission_date <= candidate:
                        flips.append(text)
                elif field_name == "issue_date":
                    if (self.submission_date - expected_date).days > 90 >= (self.submission_date - candidate).days >= 0:
                        flips.append(text)
        if not flips:
            return None
        return date_edit(expected, rng.choice(sorted(flips)), "expired/too-old date misread as valid/recent", field_name)

    # -- planning ---------------------------------------------------------------

    def plan(self, versions: tuple[str, ...] = ("scanned", "images")) -> list[Case]:
        cases: list[Case] = []
        scenarios = self.manifest["business_sets"] + self.manifest["student_sets"]
        for scenario in scenarios:
            set_id = scenario["set_id"]
            for version in versions:
                if not scenario["files"].get(version):
                    continue
                cases.extend(self._plan_submission(set_id, scenario, version))
        return cases

    def _lines(self, rel: str) -> list[str]:
        return load_cache_lines(self.cache, self._digest(rel)) or []

    def _plan_submission(self, set_id: str, scenario: dict[str, Any], version: str) -> list[Case]:
        out: list[Case] = []
        sub_id = f"{set_id}/{version}"

        def add(case_id, error, scope, edits_for, both, note=""):
            edits: dict[str, list[Edit]] = {}
            targets = []
            for rel, edit in edits_for:
                digest = self._digest(rel)
                edits.setdefault(digest, []).append(edit)
                targets.append((digest, rel, edit.field_name))
            if edits:
                out.append(Case(case_id, error, scope, set_id, version, both, edits, targets, note))

        def valid(rel: str, edit: Edit | None) -> bool:
            return edit is not None and applicable(edit, self._lines(rel))

        # ---- business number ----------------------------------------------------
        brn_docs = list(self._docs(set_id, scenario, version, ("business_registration_number",)))
        brn_docs = [(rel, name, val) for rel, name, val in brn_docs if brn_valid(re.sub(r"\D", "", val))]

        def one_doc(error: str, build: Callable[[str, str, random.Random], Edit | None], both: bool = False) -> None:
            chosen = list(brn_docs)
            stable_rng(sub_id, error, "choose").shuffle(chosen)
            made = 0
            for rel, name, val in chosen:
                rng = stable_rng(sub_id, error, rel)
                edit = build(rel, val, rng)
                if valid(rel, edit):
                    assert edit is not None
                    add(f"{sub_id}:{error}-one:{rel.rsplit('/', 1)[-1]}{':both' if both else ''}", error, "one", [(rel, edit)], both)
                    made += 1
                    if made >= self.max_per:
                        break

        one_doc("E1", lambda rel, val, rng: self._brn_sub(val, rng, None)[0])
        one_doc("E3", lambda rel, val, rng: self._brn_transpose(val, rng, False, None)[0])
        one_doc("E3c", lambda rel, val, rng: self._brn_transpose(val, rng, True, None)[0])
        one_doc("E4", lambda rel, val, rng: self._brn_drop_dup(val, rng))
        one_doc("E3c", lambda rel, val, rng: self._brn_transpose(val, rng, True, None)[0], both=True)

        def all_docs(error: str, builder: Callable[..., tuple[Edit | None, Any]], both: bool = False) -> None:
            if len(brn_docs) < 2:
                return
            rng = stable_rng(sub_id, error, "all")
            fixed = None
            pairs: list[tuple[str, Edit]] = []
            for rel, name, val in brn_docs:
                edit, fixed = builder(val, rng, fixed)
                if valid(rel, edit):
                    assert edit is not None
                    pairs.append((rel, edit))
            if len(pairs) >= 2:
                add(f"{sub_id}:{error}-all{':both' if both else ''}", error, "all", pairs, both)

        all_docs("E2", lambda val, rng, fixed: self._brn_sub(val, rng, fixed))
        all_docs("E3", lambda val, rng, fixed: self._brn_transpose(val, rng, False, fixed))
        all_docs("E3c", lambda val, rng, fixed: self._brn_transpose(val, rng, True, fixed))

        # ---- student / person name -------------------------------------------------
        names = list(self._docs(set_id, scenario, version, ("student_name",)))
        stable_rng(sub_id, "E5", "choose").shuffle(names)
        made = 0
        for rel, name, val in names:
            edit, _ = self._name_edit(val, "E5", "student_name", stable_rng(sub_id, "E5", rel), None)
            if valid(rel, edit):
                assert edit is not None
                add(f"{sub_id}:E5-one:{rel.rsplit('/', 1)[-1]}", "E5", "one", [(rel, edit)], False)
                made += 1
                if made >= self.max_per:
                    break
        if len(names) >= 2:
            rng = stable_rng(sub_id, "E5", "all")
            fixed = None
            pairs = []
            for rel, name, val in names:
                edit, fixed = self._name_edit(val, "E5", "student_name", rng, fixed)
                if valid(rel, edit):
                    assert edit is not None
                    pairs.append((rel, edit))
            if len(pairs) >= 2:
                add(f"{sub_id}:E5-all", "E5", "all", pairs, False)

        # ---- company name --------------------------------------------------------------
        companies = list(self._docs(set_id, scenario, version, ("company_name", "workplace_name")))
        stable_rng(sub_id, "E7", "choose").shuffle(companies)
        made = 0
        for rel, name, val in companies:
            edit, _ = self._company_edit(val, stable_rng(sub_id, "E7", rel), None)
            if valid(rel, edit):
                assert edit is not None
                edit.field_name = "company_name" if "workplace_name" not in (self.by_file[rel].get("expected_fields") or {}) else "workplace_name"
                add(f"{sub_id}:E7-one:{rel.rsplit('/', 1)[-1]}", "E7", "one", [(rel, edit)], False)
                made += 1
                if made >= self.max_per:
                    break
        if len(companies) >= 2:
            rng = stable_rng(sub_id, "E7", "all")
            fixed = None
            pairs = []
            for rel, name, val in companies:
                edit, fixed = self._company_edit(val, rng, fixed)
                if valid(rel, edit):
                    assert edit is not None
                    edit.field_name = "workplace_name" if "workplace_name" in (self.by_file[rel].get("expected_fields") or {}) else "company_name"
                    pairs.append((rel, edit))
            if len(pairs) >= 2:
                add(f"{sub_id}:E7-all", "E7", "all", pairs, False)

        # ---- dates ------------------------------------------------------------------------
        for rel in scenario["files"].get(version, []):
            entry = self.by_file.get(rel, {})
            for name in ("valid_until", "issue_date"):
                spec = entry.get("expected_fields", {}).get(name)
                if not spec or spec.get("state") != "KNOWN_VALUE":
                    continue
                edit = self._date_edit(name, spec["value"], stable_rng(sub_id, "E6", rel, name))
                if valid(rel, edit):
                    assert edit is not None
                    add(f"{sub_id}:E6-{name}:{rel.rsplit('/', 1)[-1]}", "E6", "one", [(rel, edit)], False)
                    add(f"{sub_id}:E6-{name}:{rel.rsplit('/', 1)[-1]}:both", "E6", "one", [(rel, edit)], True)

        # ---- GPA ----------------------------------------------------------------------------
        for rel in scenario["files"].get(version, []):
            entry = self.by_file.get(rel, {})
            fields = entry.get("expected_fields", {})
            if fields.get("gpa", {}).get("state") == "KNOWN_VALUE":
                edit = gpa_edit(fields["gpa"]["value"], fields.get("gpa_scale", {}).get("value", "4.5"), "GPA digit change crossing 3.0")
                if valid(rel, edit):
                    assert edit is not None
                    add(f"{sub_id}:E8:{rel.rsplit('/', 1)[-1]}", "E8", "one", [(rel, edit)], False)
                    add(f"{sub_id}:E8:{rel.rsplit('/', 1)[-1]}:both", "E8", "one", [(rel, edit)], True)

        # ---- student number -----------------------------------------------------------------
        sids = list(self._docs(set_id, scenario, version, ("student_id",)))
        stable_rng(sub_id, "E9", "choose").shuffle(sids)
        made = 0
        for rel, name, val in sids:
            rng = stable_rng(sub_id, "E9", rel)
            options = [(i, s) for i, d in enumerate(val) for s in DIGIT_CONFUSIONS.get(d, [])]
            if not options:
                continue
            i, sub = rng.choice(options)
            edit = digit_run_edit(val, val[:i] + sub + val[i + 1 :], "E9", f"digit {i + 1}: {val[i]}->{sub}", "student_id")
            if valid(rel, edit):
                add(f"{sub_id}:E9:{rel.rsplit('/', 1)[-1]}", "E9", "one", [(rel, edit)], False)
                add(f"{sub_id}:E9:{rel.rsplit('/', 1)[-1]}:both", "E9", "one", [(rel, edit)], True)
                made += 1
                if made >= self.max_per:
                    break
        return out


# ----------------------------------------------------------------------------- injector


class Injector:
    """Applied by the harness OCR wrapper to a document's pages (and, for 'both-passes', to
    the second-pass readings of the same field)."""

    def __init__(self) -> None:
        self.edits: dict[str, list[Edit]] = {}
        self.both = False
        self.applied: Counter[str] = Counter()

    def set_case(self, case: Case | None) -> None:
        self.edits = case.edits if case else {}
        self.both = bool(case and case.both_passes)
        self.applied.clear()

    def pages(self, digest: str, pages: list[Any]) -> list[Any]:
        edits = self.edits.get(digest)
        if not edits:
            return pages
        from app.document_intelligence.ocr.text_assembly import assemble_page_text

        for page in pages:
            changed = False
            for line in page.lines:
                for edit in edits:
                    new = edit.apply(line.text)
                    if new is not None and new != line.text:
                        rng = stable_rng("conf", digest, line.text)
                        line.text = new
                        line.confidence = round(rng.uniform(*CONF_RANGE), 4)
                        self.applied[edit.field_name] += 1
                        changed = True
            if changed:
                page.text = assemble_page_text(page.lines)
        return pages

    def reading(self, digest: str, field_name: str, text: str | None) -> str | None:
        """Second-pass reading editor (only for both-passes cases)."""
        if not self.both or text is None:
            return text
        for edit in self.edits.get(digest, []):
            if edit.field_name == field_name:
                new = edit.apply(text)
                if new is not None:
                    return new
        return text


# ----------------------------------------------------------------------------- run


def run_cases(cases: list[Case], runner: Runner, injector: Injector, manifest: dict[str, Any], log=print) -> list[dict[str, Any]]:
    by_file = {e["file"]: e for e in manifest["files"]}
    scenarios = {s["set_id"]: s for s in manifest["business_sets"] + manifest["student_sets"]}
    results = []
    controls: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}

    def control(case: Case) -> dict[str, dict[str, Any]]:
        """Un-injected run of the same submission: which fields does this pipeline read correctly?"""
        key = (case.set_id, case.version)
        if key not in controls:
            scenario = scenarios[case.set_id]
            workflow = scenario["workflow"]
            checklist = runner.business_id if workflow == "business" else runner.student_id
            rels = scenario["files"][case.version]
            injector.set_case(None)
            entry = runner.run_submission(workflow, checklist, f"control-{case.set_id}-{case.version}", [(r, runner.root / r) for r in rels])
            read: dict[str, dict[str, Any]] = {}
            for f in entry["files"]:
                spec = (by_file.get(f["file"]) or {}).get("expected_fields") or {}
                for name, info in (f.get("fields") or {}).items():
                    if name in spec and spec[name].get("state") == "KNOWN_VALUE":
                        read[f"{f['file']}|{name}"] = {
                            "ok": score_v2.normalize(name, info.get("machine_value")) == score_v2.normalize(name, spec[name]["value"]),
                            "acts": info.get("value") is not None,
                        }
            controls[key] = read
        return controls[key]
    for index, case in enumerate(cases, start=1):
        scenario = scenarios[case.set_id]
        workflow = scenario["workflow"]
        checklist = runner.business_id if workflow == "business" else runner.student_id
        rels = scenario["files"][case.version]
        baseline = control(case)
        ok_targets = [t for t in case.targets if baseline.get(f"{t[1]}|{t[2]}", {}).get("ok")]
        # one document: its field must be read correctly un-injected; every document (correlated):
        # at least two documents must be (the others are injected but not measured).
        exercised = len(ok_targets) >= (2 if case.scope == "all" else 1) and (case.scope == "all" or len(ok_targets) == len(case.targets))
        measured = ok_targets if exercised else case.targets
        injector.set_case(case)
        entry = runner.run_submission(workflow, checklist, case.case_id, [(r, runner.root / r) for r in rels])
        injector.set_case(None)
        scored_files = [score_v2.score_file(f, by_file.get(f["file"])) for f in entry["files"]]
        digital = scenario["expected"].get("digital", {})
        kind, token = score_v2.status_expectation(digital)
        actual = entry["actual_submission_status"]
        target_rows = []
        false_accept = False
        accepted = False
        for digest, rel, field_name in measured:
            scored = next((f for f in scored_files if f["file"] == rel), None)
            fs = (scored or {}).get("fields", {}).get(field_name)
            raw_field = next((f for f in entry["files"] if f["file"] == rel), {}).get("fields", {}).get(field_name, {})
            edit = next(e for e in case.edits[digest] if e.field_name == field_name)
            acts = bool(fs and fs["acts"])
            wrong = bool(fs and fs.get("effective_outcome") == "WRONG")
            accepted = accepted or acts
            false_accept = false_accept or wrong
            target_rows.append(
                {
                    "file": rel.rsplit("/", 1)[-1],
                    "field": field_name,
                    "expected": edit.expected,
                    "injected": edit.wrong,
                    "description": edit.description,
                    "effective_value": raw_field.get("value"),
                    "machine_value": raw_field.get("machine_value"),
                    "read_wrong_value": (
                        score_v2.normalize(field_name, edit.wrong) in score_v2.normalize(field_name, raw_field.get("machine_value") or "")
                        if edit.kind == "E7"
                        else score_v2.normalize(field_name, raw_field.get("machine_value")) == score_v2.normalize(field_name, edit.wrong)
                    ),
                    "control_acts": baseline.get(f"{rel}|{field_name}", {}).get("acts"),
                    "acts": acts,
                    "wrong": wrong,
                    "auto_acceptance": raw_field.get("auto_acceptance"),
                }
            )
        any_wrong_effective = any(fs.get("effective_outcome") == "WRONG" for f in scored_files for fs in f["fields"].values())
        false_ready = actual == "READY" and ((kind == "SCORED" and token != "READY") or any_wrong_effective)
        results.append(
            {
                "case": case.case_id,
                "error": case.error,
                "scope": case.scope,
                "both_passes": case.both_passes,
                "set": case.set_id,
                "version": case.version,
                "status": actual,
                "issue_codes": sorted(set(entry["actual_issue_codes"] or [])),
                "false_auto_accept": false_accept or any_wrong_effective,
                "false_ready": false_ready,
                "targets_accepted": accepted,
                "exercised": exercised,
                "effective": exercised and any(t["read_wrong_value"] for t in target_rows),
                "targets": target_rows,
            }
        )
        if index % 25 == 0:
            log(f"  {index}/{len(cases)} cases")
    return results


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        key = f"{r['error']}-{r['scope']}{'-both' if r['both_passes'] else ''}"
        t = table[key]
        t["planned"] += 1
        if not r["exercised"]:
            continue
        t["cases"] += 1
        t["effective"] += int(r["effective"])
        t["false_auto_accept"] += int(r["false_auto_accept"])
        t["false_ready"] += int(r["false_ready"])
        t["target_accepted"] += int(r["targets_accepted"])
        t["detected"] += int(not r["targets_accepted"])
        t["READY"] += int(r["status"] == "READY")
        t["NEEDS_CORRECTION"] += int(r["status"] == "NEEDS_CORRECTION")
        t["REVIEW_REQUIRED"] += int(r["status"] == "REVIEW_REQUIRED")
    for t in table.values():
        for k in ("cases", "effective", "false_auto_accept", "false_ready", "target_accepted", "detected", "READY", "NEEDS_CORRECTION", "REVIEW_REQUIRED"):
            t.setdefault(k, 0)
    return {k: dict(v) for k, v in sorted(table.items())}


def render(label: str, summary: dict[str, Any], results: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    lines = [f"# Injection results — {label}\n"]
    lines.append(f"- Suite SHA-256 `{meta['suite_sha256']}`, seed {SEED}, git `{meta['git_head']}`, strategy `{meta.get('strategy')}`, project values `{meta['project_values']}`")
    lines.append(f"- Scorer v2 SHA-256 `{meta['scorer_sha256']}`; cases: {len(results)}\n")
    lines.append("`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.\n")
    lines.append("| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for key, t in summary.items():
        lines.append(
            f"| {key} | {t['planned']} | {t['cases']} | {t['effective']} | {t['false_auto_accept']} | {t['false_ready']} | {t['detected']} | {t['READY']} | {t['NEEDS_CORRECTION']} | {t['REVIEW_REQUIRED']} |"
        )
    total_fa = sum(t["false_auto_accept"] for t in summary.values())
    lines.append(f"\nTotals: planned {sum(t['planned'] for t in summary.values())}, exercised {sum(t['cases'] for t in summary.values())}, effective {sum(t['effective'] for t in summary.values())}.")
    total_fr = sum(t["false_ready"] for t in summary.values())
    lines.append(f"\n**Totals: false auto-accept {total_fa}, false READY {total_fr}.**\n")
    leaks = [r for r in results if r["exercised"] and (r["false_auto_accept"] or r["false_ready"])]
    if leaks:
        lines.append("## Leaks\n")
        lines.append("| Case | status | injected → accepted value |")
        lines.append("|---|---|---|")
        for r in leaks:
            detail = "; ".join(f"{t['field']}: {t['expected']}→{t['effective_value']}" for t in r["targets"] if t["wrong"])
            lines.append(f"| {r['case']} | {r['status']} | {detail} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="output prefix (writes .json and .md)")
    parser.add_argument("--label", default="B0")
    parser.add_argument("--project-values", action="store_true")
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--versions", default="scanned,images")
    parser.add_argument("--errors", default=None, help="comma-separated error ids to run, e.g. E1,E2")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    manifest_path = REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
    planner = Planner(manifest, root, args.ocr_cache)
    cases = planner.plan(tuple(v for v in args.versions.split(",") if v))
    if args.errors:
        wanted = set(args.errors.split(","))
        cases = [c for c in cases if c.error in wanted]
    if args.limit:
        cases = cases[: args.limit]
    print(f"planned {len(cases)} cases")
    injector = Injector()
    extra_env = {"ADVS_AUTO_ACCEPT_STRATEGY": args.strategy} if args.strategy else {}
    runner = Runner("dev", ocr_mode="replay", ocr_cache_dir=args.ocr_cache, injector=injector.pages, project_values=args.project_values, extra_env=extra_env)
    if runner.ocr_cache is not None:
        runner.ocr_cache.reading_editor = injector.reading
    try:
        results = run_cases(cases, runner, injector, manifest)
    finally:
        runner.close()
    summary = summarise(results)
    meta = {
        "suite_sha256": SCRIPT_SHA,
        "scorer_sha256": score_v2.sha256_of(Path(score_v2.__file__)),
        "git_head": git_head(),
        "strategy": args.strategy,
        "project_values": args.project_values,
        "seed": SEED,
    }
    args.out.with_suffix(".json").write_text(json.dumps({"meta": meta, "summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    args.out.with_suffix(".md").write_text(render(args.label, summary, results, meta), encoding="utf-8")
    print(render(args.label, summary, results, meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
