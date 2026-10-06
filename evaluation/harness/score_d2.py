"""Phase D2 entry point for scorer v2 (score_v2.py stays frozen and unmodified).

Adds the `holdout` (now development data) and `holdout2` (final judgement only) manifests."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_v2  # noqa: E402

SYN = score_v2.REPO_ROOT / "evaluation" / "datasets" / "synthetic"
score_v2.CORPUS_MANIFESTS["holdout2"] = SYN / "holdout2" / "manifest.json"

if __name__ == "__main__":
    if "holdout2" in sys.argv and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
        raise SystemExit("Refusing to score hold-out set 2 outside final judgement.")
    sys.argv = [a if a != "--corpus" else a for a in sys.argv]
    # argparse choices in score_v2.main only allow dev/holdout; patch by pre-registering
    import argparse

    orig = argparse.ArgumentParser.add_argument

    def patched(self, *a, **k):
        if a and a[0] == "--corpus":
            k["choices"] = ["dev", "holdout", "holdout2"]
        return orig(self, *a, **k)

    argparse.ArgumentParser.add_argument = patched  # type: ignore[method-assign]
    raise SystemExit(score_v2.main())
