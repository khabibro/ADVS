"""Phase D2 injection suite: E10-E12 (E1-E9 are the frozen Phase D suite, imported unchanged).

Frozen at Phase D2 step D2-0 (hash recorded in every report) BEFORE any D2 fix.

E10  garbled look-alike title: the qualifier before a supported title is corrupted by an OCR
     confusion (지방세 -> 지방새 / 지빙세 / X방세 / 지세; 휴학 -> 휴힉 / 후학 / X학 / 학;
     졸업예정 -> 졸업에정 / 졸엄예정 / X업예정 / 졸업정). Applied to the real OCR of the
     look-alike documents (expected type UNKNOWN). Must never end READY and the document must
     never have a field auto-accepted. The qualifier may be spread over per-character boxes:
     it is found in reading order across boxes.
E11  boundary dates: an EXPIRED valid_until (or a too-old issue_date) is misread, identically in
     both OCR passes, to a date just on the valid side: submission date + {0,1,3,7} days for
     valid_until; the 90-day limit - {0,1,3,7} days for issue_date.
E12  boundary GPA: a GPA below the 3.0 threshold is misread, identically in both passes, to
     3.00 / 3.05 / 3.10.

Metrics: false auto-accept = the system acts on a wrong value; false READY = submission READY
while an acted-on value is wrong (E11/E12) or while a look-alike document is READY (E10).
Deterministic (fixed seed from the Phase D suite).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inject_errors as ie  # noqa: E402  (frozen Phase D suite, unchanged)
import score_v2  # noqa: E402
from harness_core import REPO_ROOT, CORPORA, Runner, git_head, guard_corpus  # noqa: E402

SUITE_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

QUALIFIER_VARIANTS: dict[str, list[str]] = {
    "지방세": ["지방새", "지빙세", "X방세", "지세"],
    "휴학": ["휴힉", "후학", "X학", "학"],
    "졸업예정": ["졸업에정", "졸엄예정", "X업예정", "졸업정"],
}
BOUNDARY_DAYS = (0, 1, 3, 7)
BOUNDARY_GPA = ("3.00", "3.05", "3.10")


# ----------------------------------------------------------------------------- E10


def corrupt_qualifier(page: Any, qualifier: str, replacement: str) -> bool:
    """Replace `qualifier` (found in reading order across boxes, spaces ignored) by `replacement`."""
    from app.document_intelligence.ocr.text_assembly import assemble_page_text, order_lines

    ordered = order_lines(page.lines)
    flat = [(li, ci, ch) for li, line in enumerate(ordered) for ci, ch in enumerate(line.text) if not ch.isspace()]
    target = list(qualifier)
    for start in range(len(flat) - len(target) + 1):
        if [c for _, _, c in flat[start : start + len(target)]] != target:
            continue
        chars = {id(line): list(line.text) for line in ordered}
        new = list(replacement)
        for offset, (li, ci, _) in enumerate(flat[start : start + len(target)]):
            line = ordered[li]
            chars[id(line)][ci] = new[offset] if offset < len(new) else ""
        for line in ordered:
            line.text = "".join(chars[id(line)])
        page.text = assemble_page_text(page.lines)
        return True
    return False


class D2Injector(ie.Injector):
    def __init__(self) -> None:
        super().__init__()
        self.qualifier: tuple[str, str] | None = None
        self.title_digest: str | None = None

    def set_title_case(self, digest: str | None, qualifier: str | None, replacement: str | None) -> None:
        self.title_digest = digest
        self.qualifier = (qualifier, replacement) if qualifier and replacement is not None else None

    def pages(self, digest: str, pages: list[Any]) -> list[Any]:
        if self.qualifier and digest == self.title_digest:
            for page in pages:
                corrupt_qualifier(page, *self.qualifier)
            return pages
        return super().pages(digest, pages)


def detect_qualifier(cache: Path, digest: str) -> str | None:
    path = cache / f"{digest}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if "error" in data:
        return None
    squashed = re.sub(r"\s+", "", "".join(line["text"] for page in data["pages"] for line in page["lines"]))
    return next((q for q in QUALIFIER_VARIANTS if q in squashed), None)


def run_e10(runner: Runner, injector: D2Injector, manifest: dict[str, Any], cache: Path, versions=("scanned", "images"), log=print) -> list[dict[str, Any]]:
    by_file = {e["file"]: e for e in manifest["files"]}
    results = []
    for scenario in manifest["business_sets"] + manifest["student_sets"]:
        workflow = scenario["workflow"]
        checklist = runner.business_id if workflow == "business" else runner.student_id
        for version in versions:
            rels = scenario["files"].get(version, [])
            lookalikes = [r for r in rels if (by_file.get(r) or {}).get("expected_classification") == "UNKNOWN"]
            for rel in lookalikes:
                digest = ie.sha256_file(runner.root / rel)
                qualifier = detect_qualifier(cache, digest)
                if qualifier is None:
                    continue
                for variant in QUALIFIER_VARIANTS[qualifier]:
                    injector.set_title_case(digest, qualifier, variant)
                    entry = runner.run_submission(workflow, checklist, f"E10-{scenario['set_id']}", [(r, runner.root / r) for r in rels])
                    injector.set_title_case(None, None, None)
                    doc = next(f for f in entry["files"] if f["file"] == rel)
                    acted = [name for name, info in (doc.get("fields") or {}).items() if info.get("value") is not None]
                    results.append(
                        {
                            "case": f"{scenario['set_id']}/{version}:E10:{rel.rsplit('/', 1)[-1]}:{qualifier}->{variant}",
                            "error": "E10", "scope": "one", "both_passes": False,
                            "set": scenario["set_id"], "version": version,
                            "status": entry["actual_submission_status"],
                            "predicted_type": doc.get("predicted_document_type"),
                            "acted_fields": acted,
                            "exercised": True,
                            "effective": doc.get("predicted_document_type") not in (None, "UNKNOWN"),
                            "false_auto_accept": bool(acted),
                            "false_ready": entry["actual_submission_status"] == "READY",
                            "targets_accepted": bool(acted),
                            "targets": [],
                        }
                    )
    log(f"E10: {len(results)} cases")
    return results


# ----------------------------------------------------------------------------- E11 / E12


def _gpa_token_edit(expected: str, new: str) -> ie.Edit:
    candidates = sorted({expected, f"{float(expected):.2f}", f"{float(expected):.1f}"}, key=len, reverse=True)

    def apply(text: str) -> str | None:
        for token in candidates:
            index = text.find(token)
            if index >= 0:
                return text[:index] + new + text[index + len(token) :]
        return None

    return ie.Edit("E12", "gpa", expected, new, f"GPA {expected} misread as {new}", apply)


def plan_boundary(manifest: dict[str, Any], root: Path, cache: Path, versions=("scanned", "images")) -> list[ie.Case]:
    submission = date.fromisoformat(manifest["submission_date"])
    by_file = {e["file"]: e for e in manifest["files"]}
    cases: list[ie.Case] = []
    for scenario in manifest["business_sets"] + manifest["student_sets"]:
        for version in versions:
            for rel in scenario["files"].get(version, []):
                entry = by_file.get(rel) or {}
                fields = entry.get("expected_fields") or {}
                digest = ie.sha256_file(root / rel)
                lines = ie.load_cache_lines(cache, digest) or []
                tag = f"{scenario['set_id']}/{version}"
                name = rel.rsplit("/", 1)[-1]

                def add(case_id: str, error: str, edit: ie.Edit) -> None:
                    if ie.applicable(edit, lines):
                        cases.append(ie.Case(case_id, error, "one", scenario["set_id"], version, True, {digest: [edit]}, [(digest, rel, edit.field_name)]))

                spec = fields.get("valid_until")
                if spec and spec.get("state") == "KNOWN_VALUE" and date.fromisoformat(spec["value"]) < submission:
                    for days in BOUNDARY_DAYS:
                        new = (submission + timedelta(days=days)).isoformat()
                        add(f"{tag}:E11-valid_until+{days}:{name}", "E11", ie.date_edit(spec["value"], new, f"expired valid_until misread as submission+{days}d", "valid_until"))
                spec = fields.get("issue_date")
                if spec and spec.get("state") == "KNOWN_VALUE" and (submission - date.fromisoformat(spec["value"])).days > 90:
                    for days in BOUNDARY_DAYS:
                        new = (submission - timedelta(days=90 - days)).isoformat()
                        add(f"{tag}:E11-issue_date-{90 - days}d:{name}", "E11", ie.date_edit(spec["value"], new, f"too-old issue_date misread as {90 - days} days old", "issue_date"))
                spec = fields.get("gpa")
                if spec and spec.get("state") == "KNOWN_VALUE" and float(spec["value"]) < 3.0:
                    for new in BOUNDARY_GPA:
                        add(f"{tag}:E12-gpa->{new}:{name}", "E12", _gpa_token_edit(spec["value"], new))
    return cases


# ----------------------------------------------------------------------------- run


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    table: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for r in results:
        if not r.get("exercised", True):
            continue
        key = f"{r['error']}{'-both' if r['both_passes'] else ''}"
        t = table[key]
        t["cases"] += 1
        t["false_auto_accept"] += int(r["false_auto_accept"])
        t["false_ready"] += int(r["false_ready"])
        t["READY"] += int(r["status"] == "READY")
        t["NEEDS_CORRECTION"] += int(r["status"] == "NEEDS_CORRECTION")
        t["REVIEW_REQUIRED"] += int(r["status"] == "REVIEW_REQUIRED")
        if r["error"] == "E10":
            t["type_breach"] += int(bool(r["effective"]))
    return {k: dict(v) for k, v in sorted(table.items())}


def render(label: str, summary: dict[str, Any], results: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    L = [f"# D2 injection results — {label}\n", f"- Frozen Phase D suite SHA-256 `{meta['phase_d_suite_sha256']}`; D2 suite SHA-256 `{meta['suite_sha256']}`; scorer v2 `{meta['scorer_sha256']}`", f"- corpus `{meta['corpus']}`, git `{meta['git_head']}`, project values `{meta['project_values']}`, cases {len(results)}\n"]
    L.append("| Injection | Cases | False auto-accept | False READY | READY | NEEDS_CORRECTION | REVIEW_REQUIRED | E10: classified as a supported type |")
    L.append("|---|---|---|---|---|---|---|---|")
    for key, t in summary.items():
        L.append(f"| {key} | {t['cases']} | {t['false_auto_accept']} | {t['false_ready']} | {t.get('READY', 0)} | {t.get('NEEDS_CORRECTION', 0)} | {t.get('REVIEW_REQUIRED', 0)} | {t.get('type_breach', '-') if key.startswith('E10') else '-'} |")
    leaks = [r for r in results if r["false_auto_accept"] or r["false_ready"]]
    L.append(f"\n**Totals: false auto-accept {sum(t['false_auto_accept'] for t in summary.values())}, false READY {sum(t['false_ready'] for t in summary.values())}.**\n")
    if leaks:
        L.append("## Leaks\n\n| Case | status | detail |\n|---|---|---|")
        for r in leaks[:60]:
            detail = f"type={r.get('predicted_type')} acted={r.get('acted_fields')}" if r["error"] == "E10" else "; ".join(f"{t['field']}: {t['expected']}→{t['effective_value']}" for t in r["targets"] if t["wrong"])
            L.append(f"| {r['case']} | {r['status']} | {detail} |")
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=["dev", "holdout", "holdout2"], default="dev")
    parser.add_argument("--ocr-cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--project-values", action="store_true")
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--errors", default=None, help="comma-separated, e.g. E1,E10")
    args = parser.parse_args()

    root = guard_corpus(args.corpus)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
    wanted = set(args.errors.split(",")) if args.errors else None
    planner = ie.Planner(manifest, root, args.ocr_cache)
    cases = planner.plan() + plan_boundary(manifest, root, args.ocr_cache)
    if wanted:
        cases = [c for c in cases if c.error in wanted]
    injector = D2Injector()
    extra_env = {"ADVS_AUTO_ACCEPT_STRATEGY": args.strategy} if args.strategy else {}
    runner = Runner(args.corpus, ocr_mode="replay", ocr_cache_dir=args.ocr_cache, injector=injector.pages, project_values=args.project_values, extra_env=extra_env)
    if runner.ocr_cache is not None:
        runner.ocr_cache.reading_editor = injector.reading
    try:
        results = ie.run_cases(cases, runner, injector, manifest) if cases else []
        if wanted is None or "E10" in wanted:
            results += run_e10(runner, injector, manifest, args.ocr_cache)
    finally:
        runner.close()
    summary = summarise(results)
    meta = {
        "suite_sha256": SUITE_SHA,
        "phase_d_suite_sha256": hashlib.sha256(Path(ie.__file__).read_bytes()).hexdigest(),
        "scorer_sha256": score_v2.sha256_of(Path(score_v2.__file__)),
        "git_head": git_head(), "corpus": args.corpus, "project_values": args.project_values, "strategy": args.strategy,
    }
    args.out.with_suffix(".json").write_text(json.dumps({"meta": meta, "summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    text = render(args.label, summary, results, meta)
    args.out.with_suffix(".md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
