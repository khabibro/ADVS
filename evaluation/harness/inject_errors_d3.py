"""Phase D3 injection suite: E13-E18 (E1-E12 are the frozen Phase D / D2 suites, imported unchanged).

Frozen at Phase D3 step 0 (hash recorded in every report) BEFORE any D3 fix.

Every type has a *single-error* and a *correlated* version; "-both" repeats a version with the same
error also injected into the second OCR pass of that field (common-mode).

E13  cumulative GPA misread (digit confusion) with the semester GPAs and credits untouched.
     Correlated: the cumulative GPA and one semester GPA are misread by the same amount.
E14  issue_date and valid_until misread (digit confusion). Single: one of the two. Correlated: the
     SAME glyph confusion in both dates (a systematic recogniser bias), which keeps their relation.
E15  a date printed in two places (the issuer-block date and the date beside "재학중", or the two
     dates of a 완납증명원): single = one occurrence misread, correlated = both identically.
E16  a digit misread in the corporate registration number (법인등록번호), which no rule uses:
     must never change the decision.
E17  a misread in a field no active rule uses (department, representative): must never change the
     decision.
E18  misreads on the issuer line and the issue date where a seal is printed (the lines nearest the
     seal placeholder).

Metrics as in the earlier suites (false auto-accept = an acted-on value differs from the manifest
truth; false READY = READY while an acted-on value is wrong or the digital expectation is not READY),
plus for E16/E17 `decision_changed` (status differs from the un-injected control).
In-memory only: the scoring manifest is extended with each document's printed `issue_date`
(`other_printed_values`) as an expected field; manifest files are not edited.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inject_errors as ie  # noqa: E402  (frozen Phase D suite)
import inject_errors_d2 as d2  # noqa: E402  (frozen D2 suite)
import score_v2  # noqa: E402
from harness_core import REPO_ROOT, Runner, git_head, guard_corpus  # noqa: E402

SUITE_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
CONF = ie.DIGIT_CONFUSIONS
GPA_RE = r"(?<![\d.]){}(?![\d])"


def augmented_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(manifest)
    for entry in out["files"]:
        printed = (entry.get("other_printed_values") or {}).get("issue_date")
        fields = entry.setdefault("expected_fields", {})
        if printed and "issue_date" not in fields:
            fields["issue_date"] = {"state": "KNOWN_VALUE", "value": printed, "printed": printed}
    return out


def _alt_digit_values(text: str, rng, validator) -> list[str]:
    options = []
    for index, char in enumerate(text):
        for sub in CONF.get(char, []):
            candidate = text[:index] + sub + text[index + 1 :]
            if candidate != text and validator(candidate):
                options.append(candidate)
    rng.shuffle(options)
    return options


def _valid_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False


def _gpa_edit(expected: str, new: str, kind_field: str = "gpa") -> ie.Edit:
    cumulative = GPA_RE.format(re.escape(expected))
    pattern = re.compile(r"(평점평균\s*[:：]?\s*)" + cumulative + r"(?=\s*/)")
    cell = re.compile(cumulative + r"(?=\s*/\s*\d(?:\.\d+)?)")

    def apply(text: str) -> str | None:
        changed, count = pattern.subn(lambda m: m.group(1) + new, text)
        if count:
            return changed
        if "평점" in text or "/" in text:
            changed, count = cell.subn(new, text)
            if count and "백분율" not in text:
                return changed
        return None

    return ie.Edit("E13", kind_field, expected, new, f"cumulative GPA {expected} misread as {new}", apply)


def _semester_edit(token: str, new: str) -> ie.Edit:
    pattern = re.compile(r"(평점평균\s*[:：]?\s*)" + GPA_RE.format(re.escape(token)) + r"(?=\s*/)")

    def apply(text: str) -> str | None:
        changed, count = pattern.subn(lambda m: m.group(1) + new, text, count=1)
        return changed if count else None

    return ie.Edit("E13", "gpa_semester", token, new, "one semester GPA misread by the same amount", apply)


def _nth_date_edit(expected_iso: str, new_iso: str, field_name: str, nth: int | None, kind: str, description: str) -> ie.Edit:
    """Edit the date `expected_iso` in a line; `nth` selects one occurrence (counting across lines)."""
    seen = {"n": 0}
    inner = ie.date_edit(expected_iso, new_iso, description, field_name)

    def apply(text: str) -> str | None:
        changed = inner.apply(text)
        if changed is None:
            return None
        seen["n"] += 1
        if nth is not None and seen["n"] - 1 != nth:
            return None
        return changed

    return ie.Edit(kind, field_name, expected_iso, new_iso, description, apply)


class Planner3:
    def __init__(self, manifest: dict[str, Any], root: Path, cache: Path) -> None:
        self.manifest = augmented_manifest(manifest)
        self.root = root
        self.cache = cache
        self.by_file = {e["file"]: e for e in self.manifest["files"]}

    def digest(self, rel: str) -> str:
        return ie.sha256_file(self.root / rel)

    def lines(self, rel: str) -> list[str]:
        return ie.load_cache_lines(self.cache, self.digest(rel)) or []

    def plan(self, versions=("scanned", "images")) -> list[ie.Case]:
        cases: list[ie.Case] = []
        for scenario in self.manifest["business_sets"] + self.manifest["student_sets"]:
            for version in versions:
                for rel in scenario["files"].get(version, []):
                    cases.extend(self._doc_cases(scenario, version, rel))
        return cases

    # -------------------------------------------------------------------------------------

    def _case(self, scenario, version, rel, case_id, error, scope, both, edits: list[ie.Edit], targets: list[str]) -> ie.Case | None:
        lines = self.lines(rel)
        if not any(ie.applicable(edit, lines) for edit in edits[:1]):
            return None
        digest = self.digest(rel)
        return ie.Case(
            f"{scenario['set_id']}/{version}:{case_id}:{rel.rsplit('/', 1)[-1]}{':both' if both else ''}",
            error, scope, scenario["set_id"], version, both, {digest: edits}, [(digest, rel, name) for name in targets],
        )

    def _doc_cases(self, scenario, version, rel) -> list[ie.Case]:
        entry = self.by_file.get(rel) or {}
        fields = entry.get("expected_fields") or {}
        printed = entry.get("other_printed_values") or {}
        sid = scenario["set_id"]
        rng = ie.stable_rng(sid, version, rel, "d3")
        out: list[ie.Case] = []

        def add(case):
            if case is not None:
                out.append(case)

        # ---- E13 ---------------------------------------------------------------------
        gpa = fields.get("gpa")
        if gpa and gpa.get("state") == "KNOWN_VALUE":
            exp = gpa["value"]
            scale = float(fields.get("gpa_scale", {}).get("value", 4.5))
            alts = _alt_digit_values(exp, rng, lambda t: t.replace(".", "", 1).isdigit() and 0 <= float(t) <= scale)
            for new in alts[:2]:
                for both in (False, True):
                    add(self._case(scenario, version, rel, f"E13-{new}", "E13", "one", both, [_gpa_edit(exp, new)], ["gpa"]))
                    sem = self._semester_value(rel, exp)
                    if sem is not None:
                        delta = float(new) - float(exp)
                        sem_new = f"{min(scale, max(0.0, float(sem) + delta)):.2f}"
                        add(self._case(scenario, version, rel, f"E13c-{new}", "E13", "one", both, [_gpa_edit(exp, new), _semester_edit(sem, sem_new)], ["gpa"]))
        # ---- E14 / E15 / E18 ---------------------------------------------------------
        valid_until = fields.get("valid_until")
        issue = fields.get("issue_date")
        if valid_until and valid_until.get("state") == "KNOWN_VALUE" and issue and issue.get("state") == "KNOWN_VALUE":
            vu, iss = valid_until["value"], issue["value"]
            for both in (False, True):
                for new in _alt_digit_values(vu, rng, _valid_date)[:2]:
                    add(self._case(scenario, version, rel, f"E14-vu-{new}", "E14", "one", both, [ie.date_edit(vu, new, "valid_until misread", "valid_until")], ["valid_until"]))
                for new in _alt_digit_values(iss, rng, _valid_date)[:2]:
                    add(self._case(scenario, version, rel, f"E14-iss-{new}", "E14", "one", both, [ie.date_edit(iss, new, "issue_date misread", "issue_date")], ["issue_date"]))
                # the same glyph confusion in both dates (systematic recogniser bias)
                for index in range(len(vu)):
                    if vu[index] != iss[index] or vu[index] not in CONF:
                        continue
                    done = False
                    for sub in CONF[vu[index]]:
                        nv, ni = vu[:index] + sub + vu[index + 1 :], iss[:index] + sub + iss[index + 1 :]
                        if _valid_date(nv) and _valid_date(ni):
                            add(self._case(scenario, version, rel, f"E14c-{index}{sub}", "E14", "all", both, [ie.date_edit(vu, nv, "valid_until, systematic", "valid_until"), ie.date_edit(iss, ni, "issue_date, systematic", "issue_date")], ["valid_until", "issue_date"]))
                            done = True
                            break
                    if done:
                        break
        if issue and issue.get("state") == "KNOWN_VALUE":
            iss = issue["value"]
            lines = self.lines(rel)
            occurrences = sum(1 for line in lines for _ in [0] if ie.date_edit(iss, iss, "", "issue_date").apply(line) is not None)
            if occurrences >= 2:
                for both in (False, True):
                    for new in _alt_digit_values(iss, rng, _valid_date)[:2]:
                        add(self._case(scenario, version, rel, f"E15-one-{new}", "E15", "one", both, [_nth_date_edit(iss, new, "issue_date", 0, "E15", "one occurrence misread")], ["issue_date"]))
                        add(self._case(scenario, version, rel, f"E15-all-{new}", "E15", "all", both, [_nth_date_edit(iss, new, "issue_date", None, "E15", "both occurrences misread identically")], ["issue_date"]))
            # E18: the date line nearest a seal placeholder
            if self._near_seal(rel):
                for new in _alt_digit_values(iss, rng, _valid_date)[:2]:
                    add(self._case(scenario, version, rel, f"E18-{new}", "E18", "one", False, [ie.date_edit(iss, new, "issue date near a seal misread", "issue_date")], ["issue_date"]))
        return out

    def _semester_value(self, rel: str, cumulative: str) -> str | None:
        for line in self.lines(rel):
            m = re.search(r"평점평균\s*[:：]?\s*(\d\.\d+)\s*/", line)
            if m and abs(float(m.group(1)) - float(cumulative)) > 1e-9:
                return m.group(1)
        return None

    def _near_seal(self, rel: str) -> bool:
        path = self.cache / f"{self.digest(rel)}.json"
        if not path.exists():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        if "error" in data:
            return False
        for page in data["pages"]:
            seals = [l["bounding_box"] for l in page["lines"] if "직인" in l["text"] and l.get("bounding_box")]
            dates = [l["bounding_box"] for l in page["lines"] if re.search(r"(19|20)\d\d\s*[-./년]", l["text"]) and l.get("bounding_box")]
            for s in seals:
                for d in dates:
                    if abs((d["y"] + d["height"] / 2) - (s["y"] + s["height"] / 2)) <= 4 * max(s["height"], d["height"]):
                        return True
        return False


# ----------------------------------------------------------------------------- control-based cases


def plan_control_cases(manifest: dict[str, Any], root: Path, cache: Path, versions=("scanned", "images")) -> list[dict[str, Any]]:
    """E16 / E17: edits to values no rule uses. Returned as plain dicts (set, version, file, edit)."""
    by_file = {e["file"]: e for e in manifest["files"]}
    cases = []
    for scenario in manifest["business_sets"] + manifest["student_sets"]:
        for version in versions:
            for rel in scenario["files"].get(version, []):
                entry = by_file.get(rel) or {}
                printed = entry.get("other_printed_values") or {}
                digest = ie.sha256_file(root / rel)
                lines = ie.load_cache_lines(cache, digest) or []
                rng = ie.stable_rng(scenario["set_id"], version, rel, "d3c")
                corp = printed.get("corporate_registration_number")
                if corp:
                    digits = re.sub(r"\D", "", corp)
                    pos = [i for i, c in enumerate(digits) if c in CONF]
                    if pos:
                        i = rng.choice(pos)
                        new = digits[:i] + rng.choice(CONF[digits[i]]) + digits[i + 1 :]
                        pattern = re.compile(r"(\d{6})(\s*-\s*)(\d{7})")

                        def apply(text, digits=digits, new=new, pattern=pattern):
                            for m in pattern.finditer(text):
                                if m.group(1) + m.group(3) == digits:
                                    return text[: m.start()] + new[:6] + m.group(2) + new[6:] + text[m.end() :]
                            return None

                        edit = ie.Edit("E16", "corporate_registration_number", digits, new, "corporate registration number digit misread", apply)
                        if ie.applicable(edit, lines):
                            cases.append({"error": "E16", "set": scenario["set_id"], "version": version, "rel": rel, "digest": digest, "edit": edit})
                for name, source in (("department", (entry.get("expected_fields") or {}).get("department", {}).get("value")), ("representative", printed.get("representative"))):
                    if not source:
                        continue
                    compact = "".join(source.split())
                    options = []
                    for i, ch in enumerate(compact):
                        sub = ie.confusable_char(ch, rng)
                        if sub:
                            options.append((i, sub))
                    if not options:
                        continue
                    i, sub = rng.choice(options)
                    edit = ie.text_edit(compact, i, sub, "E17", name, f"{name} misread")
                    if ie.applicable(edit, lines):
                        cases.append({"error": "E17", "set": scenario["set_id"], "version": version, "rel": rel, "digest": digest, "edit": edit})
    return cases


def run_control_cases(cases: list[dict[str, Any]], runner: Runner, injector: ie.Injector, manifest: dict[str, Any], log=print) -> list[dict[str, Any]]:
    scenarios = {s["set_id"]: s for s in manifest["business_sets"] + manifest["student_sets"]}
    controls: dict[tuple[str, str], tuple[str, list[str]]] = {}
    results = []
    for item in cases:
        scenario = scenarios[item["set"]]
        workflow = scenario["workflow"]
        checklist = runner.business_id if workflow == "business" else runner.student_id
        rels = scenario["files"][item["version"]]
        key = (item["set"], item["version"])
        if key not in controls:
            injector.set_case(None)
            control = runner.run_submission(workflow, checklist, f"control-{item['set']}-{item['version']}", [(r, runner.root / r) for r in rels])
            controls[key] = (control["actual_submission_status"], sorted(set(control["actual_issue_codes"] or [])))
        case = ie.Case(f"{item['set']}/{item['version']}:{item['error']}:{item['rel'].rsplit('/', 1)[-1]}", item["error"], "one", item["set"], item["version"], False, {item["digest"]: [item["edit"]]}, [])
        injector.set_case(case)
        entry = runner.run_submission(workflow, checklist, case.case_id, [(r, runner.root / r) for r in rels])
        injector.set_case(None)
        status, codes = entry["actual_submission_status"], sorted(set(entry["actual_issue_codes"] or []))
        control_status, control_codes = controls[key]
        results.append(
            {
                "case": case.case_id, "error": item["error"], "scope": "one", "both_passes": False, "set": item["set"], "version": item["version"],
                "status": status, "control_status": control_status,
                "decision_changed": status != control_status or codes != control_codes,
                "false_auto_accept": False,
                "false_ready": status == "READY" and control_status != "READY",
                "exercised": True, "effective": True, "targets_accepted": False, "targets": [],
            }
        )
    log(f"E16/E17: {len(results)} cases")
    return results


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    table: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        if not r.get("exercised", True):
            continue
        correlated = r["error"] in ("E13", "E14") and f"{r['error']}c-" in r["case"]
        key = f"{r['error']}{'c' if correlated else ''}{'-both' if r['both_passes'] else ''}"
        t = table[key]
        t["cases"] += 1
        t["false_auto_accept"] += int(r["false_auto_accept"])
        t["false_ready"] += int(r["false_ready"])
        t["decision_changed"] += int(bool(r.get("decision_changed")))
        for status in ("READY", "NEEDS_CORRECTION", "REVIEW_REQUIRED"):
            t[status] += int(r["status"] == status)
    return {k: dict(v) for k, v in sorted(table.items())}


def render(label: str, summary: dict[str, Any], results: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    lines = [f"# D3 injection results — {label}\n", f"- Suites: Phase D `{meta['phase_d_suite']}`, D2 `{meta['d2_suite']}`, D3 `{meta['suite_sha256']}`; scorer v2 `{meta['scorer_sha256']}`", f"- corpus `{meta['corpus']}`, git `{meta['git_head']}`, cases {len(results)}\n", "| Injection | Cases | False auto-accept | False READY | decision changed (E16/E17) | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |", "|---|---|---|---|---|---|---|---|"]
    for key, t in summary.items():
        lines.append(f"| {key} | {t['cases']} | {t['false_auto_accept']} | {t['false_ready']} | {t.get('decision_changed', 0)} | {t.get('READY', 0)} | {t.get('NEEDS_CORRECTION', 0)} | {t.get('REVIEW_REQUIRED', 0)} |")
    lines.append(f"\n**Totals: false auto-accept {sum(t['false_auto_accept'] for t in summary.values())}, false READY {sum(t['false_ready'] for t in summary.values())}.**\n")
    leaks = [r for r in results if r.get("exercised", True) and (r["false_auto_accept"] or r["false_ready"])]
    if leaks:
        lines.append("## Leaks\n\n| Case | status | detail |\n|---|---|---|")
        for r in leaks[:80]:
            detail = "; ".join(f"{t['field']}: {t['expected']}→{t['effective_value']}" for t in r["targets"] if t["wrong"])
            lines.append(f"| {r['case']} | {r['status']} | {detail} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=["dev", "holdout", "holdout2", "holdout3"], default="dev")
    parser.add_argument("--ocr-cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--errors", default=None, help="comma-separated, E1..E18; default all")
    args = parser.parse_args()

    root = guard_corpus(args.corpus)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
    wanted = set(args.errors.split(",")) if args.errors else None
    planner3 = Planner3(manifest, root, args.ocr_cache)
    scoring_manifest = planner3.manifest
    cases: list[ie.Case] = []
    if wanted is None or wanted & {f"E{i}" for i in range(1, 13)}:
        cases += ie.Planner(manifest, root, args.ocr_cache).plan() + d2.plan_boundary(manifest, root, args.ocr_cache)
    cases += planner3.plan()
    if wanted:
        cases = [c for c in cases if c.error in wanted]
    injector = d2.D2Injector()
    extra_env = {"ADVS_AUTO_ACCEPT_STRATEGY": args.strategy} if args.strategy else {}
    runner = Runner(args.corpus, ocr_mode="replay", ocr_cache_dir=args.ocr_cache, injector=injector.pages, extra_env=extra_env)
    if runner.ocr_cache is not None:
        runner.ocr_cache.reading_editor = injector.reading
    results: list[dict[str, Any]] = []
    try:
        if cases:
            results += ie.run_cases(cases, runner, injector, scoring_manifest)
        if wanted is None or "E10" in wanted:
            results += d2.run_e10(runner, injector, manifest, args.ocr_cache)
        if wanted is None or wanted & {"E16", "E17"}:
            ctrl = [c for c in plan_control_cases(manifest, root, args.ocr_cache) if wanted is None or c["error"] in wanted]
            results += run_control_cases(ctrl, runner, injector, manifest)
    finally:
        runner.close()
    summary = summarise(results)
    meta = {
        "suite_sha256": SUITE_SHA,
        "d2_suite": hashlib.sha256(Path(d2.__file__).read_bytes()).hexdigest(),
        "phase_d_suite": hashlib.sha256(Path(ie.__file__).read_bytes()).hexdigest(),
        "scorer_sha256": score_v2.sha256_of(Path(score_v2.__file__)),
        "git_head": git_head(), "corpus": args.corpus, "strategy": args.strategy,
    }
    args.out.with_suffix(".json").write_text(json.dumps({"meta": meta, "summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    text = render(args.label, summary, results, meta)
    args.out.with_suffix(".md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
