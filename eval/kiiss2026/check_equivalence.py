"""Check that the multi-policy shortcut (process once, re-verify per decision set) gives exactly the
results of a fresh run per policy, on clean and injected submissions of the development set.

    cd apps/api && PYTHONPATH=. .venv312/bin/python ../../eval/kiiss2026/check_equivalence.py --out <dir>
"""
from __future__ import annotations

import argparse, json, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_corpus as rc  # noqa: E402
import policies as pol  # noqa: E402
import harness_core, inject_errors_d2 as d2  # noqa: E402

CHECK = ["ADVS", "H14", "ABL-a_no_docs", "ABL-c_no_second", "ABL-d_no_internal", "CONF@0.97", "CONF@0.996", "CONFF@0.95", "NONE"]


def make_runner(corpus, tmp, injector):
    cache = Path(tmp) / "cache"
    if not cache.exists():
        shutil.copytree(rc.CACHES[corpus], cache)
    r = rc.MultiRunner(corpus, ocr_mode="replay", ocr_cache_dir=cache, injector=injector.pages)
    r.ocr_cache.reading_editor = injector.reading
    return r, cache


def key(res):
    return [(x["case"], x["status"], bool(x["false_auto_accept"]), bool(x["false_ready"]), x["review_fields"], x["n_target_wrong"]) for x in res]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--stride", type=int, default=15); ap.add_argument("--only", default=None)
    a = ap.parse_args()
    corpus = "dev"
    root = harness_core.guard_corpus(corpus)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    from policy_sets import advs_family, baselines, COARSE_TAU
    allp = {p.name: p for p in advs_family() + baselines(COARSE_TAU)}
    pols = [allp[n] for n in (a.only.split(",") if a.only else CHECK)]
    tmp = tempfile.mkdtemp(prefix="eqv_", dir=str(a.out))
    ok = True
    try:
        inj = d2.D2Injector()
        multi, cache = make_runner(corpus, tmp, inj)
        pol.install()
        planner3, cases = rc.plan_injection(corpus, manifest, root, cache)
        cases = cases[:: a.stride]
        print(f"{len(cases)} injected cases, {len(pols)} policies")
        res_multi = {}
        clean_multi = {}
        for p in pols:
            clean_multi[p.name] = rc.run_clean(multi, manifest, p)["rows"]
        multi.stored.clear(); multi.inputs.clear(); multi.sig_cache.clear()
        for p in pols:
            res_multi[p.name] = key(rc.run_injection(multi, corpus, manifest, planner3, cases, inj, p))
        print(f"multi: verify_calls={multi.verify_calls} reused={multi.reuse_calls}")
        multi.close()
        for p in pols:
            inj2 = d2.D2Injector()
            fresh, _ = make_runner(corpus, tmp, inj2)
            clean_f = rc.run_clean(fresh, manifest, p)["rows"]
            fresh.stored.clear(); fresh.inputs.clear(); fresh.sig_cache.clear()
            res_f = key(rc.run_injection(fresh, corpus, manifest, planner3, cases, inj2, p))
            fresh.close()
            same_inj = res_f == res_multi[p.name]
            same_clean = clean_f == clean_multi[p.name]
            ok &= same_inj and same_clean
            for x, y in zip(res_f, res_multi[p.name]):
                if x != y:
                    print("  DIFF fresh", x, "multi", y)
            print(f"{p.name:22s} clean identical={same_clean} injection identical={same_inj}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("EQUIVALENCE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
