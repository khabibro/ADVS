"""Run one corpus under many acceptance policies (evaluation only).

Each submission / injected case is uploaded and processed ONCE (OCR replayed from the frozen cache,
extraction and second-pass reads unchanged). Only the acceptance decision differs between policies,
so verification, field details and review items are re-read per distinct decision set. The result
for a policy is identical to a fresh run under that policy (checked by `check_equivalence.py`).

Usage (from apps/api, with its venv):
    PYTHONPATH=. .venv312/bin/python ../../eval/kiiss2026/run_corpus.py \
        --corpus dev --pass P0 --policy-set main --out ../../eval/kiiss2026/runs
"""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import json
import shutil
import sys
import time
import uuid
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "evaluation" / "harness"))
sys.path.insert(0, str(REPO / "apps" / "api"))
sys.path.insert(0, str(HERE))

import harness_core  # noqa: E402
from harness_core import Runner, git_head  # noqa: E402
import inject_errors as ie  # noqa: E402
import inject_errors_d2 as d2  # noqa: E402
import inject_errors_d3 as d3  # noqa: E402
import score_v2  # noqa: E402

import policies as pol  # noqa: E402
from policy_sets import POLICY_SETS  # noqa: E402

CACHES = {
    "dev": REPO / "evaluation" / "phase_d" / "ocr_cache",
    "holdout": REPO / "evaluation" / "phase_d" / "ocr_cache_holdout",
    "holdout2": REPO / "evaluation" / "phase_d2" / "ocr_cache_holdout2",
    "holdout3": REPO / "evaluation" / "phase_d3" / "ocr_cache_holdout3",
}
KEEP_LEAKS = ("ADVS", "ADVS-", "ABL-", "H14", "MAJ")  # name prefixes whose leak details are kept


class MultiRunner(Runner):
    """Processes each submission once; re-evaluates it per policy (see module docstring)."""

    def __init__(self, *a, memo: bool = True, **k) -> None:
        super().__init__(*a, **k)
        self.stored: list[tuple[str, str, list[dict]]] = []  # (name, project_id, base file results)
        self.inputs: dict[int, tuple] = {}
        self.call_idx = 0
        self.memo = memo
        self.sig_cache: dict[tuple, dict] = {}
        self.burdens: dict[str, dict] = {}
        self.verify_calls = 0
        self.reuse_calls = 0
        self.ref_date = date.fromisoformat(self.submission_date)

    def reset_pass(self) -> None:
        self.call_idx = 0
        self.burdens = {}

    def _inputs(self, idx: int, project_id: str):
        if idx not in self.inputs:
            import app.services.auto_acceptance as svc
            from app.models.entities import Project

            captured: list = []
            original = svc.decide

            def spy(fields, context, strategy):
                captured.append((list(fields), context))
                return original(fields, context, strategy)

            svc.decide = spy
            try:
                with self.SessionLocal() as db:
                    project = db.get(Project, uuid.UUID(project_id))
                    svc.decisions_for_project(db, project, self.ref_date)
            finally:
                svc.decide = original
            self.inputs[idx] = captured[0] if captured else ([], None)
        return self.inputs[idx]

    def run_submission(self, workflow, checklist_id, name, files):
        idx = self.call_idx
        self.call_idx += 1
        started = time.perf_counter()
        if idx < len(self.stored):
            stored_name, project_id, base = self.stored[idx]
            assert stored_name == name, (stored_name, name)
            file_results = copy.deepcopy(base)
        else:
            project_id = self.make_project(workflow, checklist_id, name)
            file_results = self.upload_and_process(project_id, files)
            self.stored.append((name, project_id, copy.deepcopy(file_results)))
        fields, context = self._inputs(idx, project_id)
        decisions = pol.eval_decide(fields, context, None) if context is not None else {}
        key = (idx, pol.signature(decisions))
        if self.memo and key in self.sig_cache:
            self.reuse_calls += 1
            entry = copy.deepcopy(self.sig_cache[key])
        else:
            self.verify_calls += 1
            verification = self.verify(project_id)
            self.capture_details(file_results)
            reviews = self.client.get(f"/api/v1/projects/{project_id}/review-items")
            review_items = (
                [
                    {"document_id": i["document_id"], "field_name": i["field_name"], "queue_status": i["queue_status"], "state": i["assessment_state"]}
                    for i in reviews.json()
                ]
                if reviews.status_code == 200
                else []
            )
            entry = {
                "project_id": project_id,
                "review_items": review_items,
                "actual_submission_status": verification.get("status"),
                "actual_issue_codes": verification.get("issue_codes"),
                "notices": verification.get("notices"),
                "files": file_results,
                "elapsed_seconds": round(time.perf_counter() - started, 1),
            }
            self.sig_cache[key] = copy.deepcopy(entry)
        self.burdens[name] = score_v2.burden(entry["files"], self.by_file)
        return entry


# ----------------------------------------------------------------------------- metrics


def clean_metrics(raw: dict, manifest: dict) -> list[dict]:
    """One row per input type (digital / scanned / images) with the Step-1 metrics."""
    scored = score_v2.score(raw, manifest)
    rows = []
    for version in score_v2.VERSIONS:
        r = dict(version=version, submissions=0, not_ready_n=0, false_ready=0, false_ready_in_not_ready=0,
                 false_ready_wrong_value=0, fields_evaluated=0, machine_correct=0, machine_wrong=0,
                 machine_unresolved=0, accepted_fields=0, false_auto_accepted_fields=0, review_fields=0,
                 subs_with_review=0, auto_decided=0, auto_decided_correct=0, ready=0, needs_correction=0,
                 review_required=0, ocr_fields=0, ocr_auto_accepted=0)
        for set_id, sset in scored["sets"].items():
            v = sset["versions"].get(version)
            if v is None:
                continue
            scenario_kind, token = None, None
            r["submissions"] += 1
            status = v["actual_status"]
            r["ready"] += status == "READY"
            r["needs_correction"] += status == "NEEDS_CORRECTION"
            r["review_required"] += status == "REVIEW_REQUIRED"
            expected = v["expected_status"] or ""
            # population: correct status is known and is not READY
            is_scored_not_ready = False
            kind_token = None
            raw_expect = None
            for s in raw_scenarios(manifest):
                if s["set_id"] == set_id:
                    raw_expect = s["expected"].get("digital", {})
                    break
            kind, token = score_v2.status_expectation(raw_expect or {})
            if version != "digital":
                pass  # scanned/images use the digital expectation
            is_scored_not_ready = kind == "SCORED" and token != "READY"
            r["not_ready_n"] += is_scored_not_ready
            if v["false_ready"]:
                r["false_ready"] += 1
                if is_scored_not_ready:
                    r["false_ready_in_not_ready"] += 1
                else:
                    r["false_ready_wrong_value"] += 1
            if v["burden"]["needs_human"] > 0:
                r["subs_with_review"] += 1
            r["review_fields"] += v["burden"]["needs_human"]
            if version in score_v2.OCR_VERSIONS and v["auto_decided"]:
                r["auto_decided"] += 1
                r["auto_decided_correct"] += v["status_comparison"] == "MATCH"
            for f in v["files"]:
                for name, fs in f["fields"].items():
                    if fs["category"] == "EVALUATED":
                        r["fields_evaluated"] += 1
                        r["machine_correct"] += fs["outcome"] == "CORRECT"
                        r["machine_wrong"] += fs["outcome"] == "WRONG"
                        r["machine_unresolved"] += fs["outcome"] == "UNRESOLVED"
                        r["accepted_fields"] += bool(fs["acts"])
                        if f["ocr_doc"]:
                            r["ocr_fields"] += 1
                            r["ocr_auto_accepted"] += bool(fs["acts"])
                    if fs.get("false_auto_accept") or (fs["category"] == "EVALUATED" and fs["acts"] and fs.get("effective_outcome") == "WRONG"):
                        r["false_auto_accepted_fields"] += 1
        rows.append(r)
    return rows


_SCEN = {}


def raw_scenarios(manifest: dict) -> list[dict]:
    key = id(manifest)
    if key not in _SCEN:
        _SCEN[key] = manifest["business_sets"] + manifest["student_sets"]
    return _SCEN[key]


def run_clean(runner: MultiRunner, manifest: dict, policy: pol.Policy) -> dict:
    runner.reset_pass()
    pol.set_active(policy)
    raw = runner.run_corpus(["digital", "scanned", "images"], None, include_formats=False, log=lambda s: None)
    return {"policy": policy.name, "rows": clean_metrics(raw, manifest), "false_ready_sets": [
        f"{sid}/{ver}" for sid, s in score_v2.score(raw, manifest)["sets"].items() for ver, v in s["versions"].items() if v["false_ready"]]}


# ----------------------------------------------------------------------------- injection


def plan_injection(corpus: str, manifest: dict, root: Path, cache: Path):
    planner3 = d3.Planner3(manifest, root, cache)
    cases = ie.Planner(manifest, root, cache).plan() + d2.plan_boundary(manifest, root, cache)
    cases += planner3.plan()
    return planner3, cases


def run_injection(runner: MultiRunner, corpus: str, manifest: dict, planner3, cases, injector, policy: pol.Policy) -> list[dict]:
    runner.reset_pass()
    pol.set_active(policy)
    cache = CACHES[corpus]
    quiet = lambda *a, **k: None
    results = ie.run_cases(cases, runner, injector, planner3.manifest, log=quiet)
    results += d2.run_e10(runner, injector, manifest, cache, log=quiet)
    ctrl = d3.plan_control_cases(manifest, runner.root, cache)
    results += d3.run_control_cases(ctrl, runner, injector, manifest, log=quiet)
    for r in results:
        b = runner.burdens.get(r["case"])
        r["review_fields"] = b["needs_human"] if b else None
        r["n_target_wrong"] = sum(1 for t in r.get("targets", []) if t.get("wrong"))
        r["n_targets"] = len(r.get("targets", []))
    return results


INJ_COLS = ["policy", "case", "error", "scope", "both_passes", "set", "version", "exercised", "effective", "status",
            "false_auto_accept", "false_ready", "targets_accepted", "n_targets", "n_target_wrong", "review_fields", "decision_changed"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, choices=list(CACHES))
    ap.add_argument("--pass", dest="pass_", default="P0", choices=["P0", "P1"], help="P0 = as reported (no project values); P1 = application values supplied")
    ap.add_argument("--policy-set", default="main")
    ap.add_argument("--kind", default="clean,injection")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tau-file", type=Path, default=None)
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--no-memo", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    started = time.time()
    root = harness_core.guard_corpus(args.corpus)  # holdout3 needs ADVS_FINAL_JUDGEMENT=1 and is logged
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    policies = POLICY_SETS[args.policy_set](args.tau_file)

    # frozen OCR cache is copied so a second-pass cache miss can never alter the original files
    work = args.out / f"_cache_{args.corpus}_{args.pass_}{args.tag}"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(CACHES[args.corpus], work)
    before = {p.name for p in work.rglob("*") if p.is_file()}
    injector = d2.D2Injector()
    runner = MultiRunner(args.corpus, ocr_mode="replay", ocr_cache_dir=work, injector=injector.pages,
                         project_values=(args.pass_ == "P1"), memo=not args.no_memo)
    runner.ocr_cache.reading_editor = injector.reading
    from app.db.session import engine as _engine

    assert "advs_harness_" in str(_engine.url), f"refusing to run against {_engine.url}"
    pol.install()
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.corpus}_{args.pass_}{args.tag}"
    out: dict = {"corpus": args.corpus, "pass": args.pass_, "git_head": git_head(), "policies": [p.name for p in policies],
                 "project_values": args.pass_ == "P1", "submission_date": runner.submission_date}
    kinds = set(args.kind.split(","))
    try:
        if "clean" in kinds:
            t0 = time.time()
            out["clean"] = [run_clean(runner, manifest, p) for p in policies]
            out["clean_seconds"] = round(time.time() - t0, 1)
            out["clean_verify_calls"] = runner.verify_calls
            print(f"[{stem}] clean done {out['clean_seconds']}s verify_calls={runner.verify_calls} reused={runner.reuse_calls}", flush=True)
        if "injection" in kinds:
            runner.stored.clear(); runner.inputs.clear(); runner.sig_cache.clear()
            planner3, cases = plan_injection(args.corpus, manifest, root, work)
            if args.limit_cases:
                cases = cases[: args.limit_cases]
            out["injection_cases_planned"] = len(cases)
            t0 = time.time()
            rows_path = args.out / f"inj_rows_{stem}.csv.gz"
            leaks: dict = {}
            with gzip.open(rows_path, "wt", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(INJ_COLS)
                for n, p in enumerate(policies, 1):
                    res = run_injection(runner, args.corpus, manifest, planner3, cases, injector, p)
                    for r in res:
                        w.writerow([p.name, r["case"], r["error"], r["scope"], int(r["both_passes"]), r["set"], r["version"],
                                    int(bool(r.get("exercised", True))), int(bool(r.get("effective", False))), r["status"],
                                    int(bool(r["false_auto_accept"])), int(bool(r["false_ready"])), int(bool(r.get("targets_accepted"))),
                                    r["n_targets"], r["n_target_wrong"], r["review_fields"], int(bool(r.get("decision_changed", False)))])
                    if p.name.startswith(KEEP_LEAKS):
                        leaks[p.name] = [r for r in res if r.get("exercised", True) and (r["false_auto_accept"] or r["false_ready"])]
                    print(f"[{stem}] policy {n}/{len(policies)} {p.name}: {time.time()-t0:.0f}s verify_calls={runner.verify_calls} reused={runner.reuse_calls}", flush=True)
            out["injection_seconds"] = round(time.time() - t0, 1)
            out["injection_leaks"] = leaks
    finally:
        runner.close()
    after = {p.name for p in work.rglob("*") if p.is_file()}
    out["ocr_cache_misses_computed"] = len(after - before)
    out["verify_calls"] = runner.verify_calls
    out["reuse_calls"] = runner.reuse_calls
    out["runtime_seconds"] = round(time.time() - started, 1)
    (args.out / f"summary_{stem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(f"[{stem}] done in {out['runtime_seconds']}s; cache misses computed: {out['ocr_cache_misses_computed']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
