"""Scorer v3 entry point: score_v2.py (frozen, unchanged) with the v3 manifests.

The comparison rules, outcomes and metrics are exactly score_v2's; only the expectations differ (see
evaluation/datasets/synthetic/make_manifests_v3.py for the change log: S09 digital -> READY, dev set S11).
Usage as score_d2.py:  python score_d3_v3.py --raw RAW.json --corpus dev|holdout|holdout2|holdout3 --out-json ... --out-md ... --label ...
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_v2  # noqa: E402

SYN = score_v2.REPO_ROOT / "evaluation" / "datasets" / "synthetic"
for _corpus, _dir in (("dev", "test_variants"), ("holdout", "holdout"), ("holdout2", "holdout2"), ("holdout3", "holdout3")):
    score_v2.CORPUS_MANIFESTS[_corpus] = SYN / _dir / "manifest_v3.json"

if __name__ == "__main__":
    if "holdout3" in sys.argv and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
        raise SystemExit("Refusing to score hold-out set 3 outside the regression check.")
    if any(c in sys.argv for c in ("holdout", "holdout2", "holdout3")):
        os.environ["ADVS_FINAL_JUDGEMENT"] = "1"  # score_v2 guards the hold-out names
    import argparse

    orig = argparse.ArgumentParser.add_argument

    def patched(self, *a, **k):
        if a and a[0] == "--corpus":
            k["choices"] = ["dev", "holdout", "holdout2", "holdout3"]
        return orig(self, *a, **k)

    argparse.ArgumentParser.add_argument = patched  # type: ignore[method-assign]
    raise SystemExit(score_v2.main())
