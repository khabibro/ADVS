"""Business submissions with a realistic check date (private inputs, no values in this file).

The original valid submissions are checked on the last valid day of the 국세 납세증명서, a boundary case by
construction. Here every valid submission is checked DAYS_BEFORE_EXPIRY days before the earliest printed
validity end of its documents (a customer who submits a few weeks after issue). N3/N4/N5 follow the same rule; N1/N2/N6 (expiry) keep their dates.

    python3 make_realistic_business.py data/private_real/business
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

DAYS_BEFORE_EXPIRY = 20


def main(folder: Path) -> int:
    gold = json.loads((folder / "gold.json").read_text(encoding="utf-8"))["documents"]
    subs = json.loads((folder / "SUBMISSIONS.json").read_text(encoding="utf-8"))
    changed = 0
    for sub in subs:
        # Valid submissions, and the negatives whose defect is not about the date (N3 company mismatch, N4 지방세 in place
        # of 국세, N5 duplicate upload): a negative that is only refused because its check date sits on the expiry day
        # would hide a real leak. N1, N2 and N6 are about expiry and keep their dates.
        if sub["kind"] != "valid" and sub.get("case") not in ("N3", "N4", "N5"):
            continue
        ends = []
        for name in sub["docs"].values():
            end = (gold.get(name, {}).get("fields", {}).get("valid_until") or {}).get("value")
            if end:
                ends.append(date.fromisoformat(end))
        if ends:
            sub["eval_date"] = (min(ends) - timedelta(days=DAYS_BEFORE_EXPIRY)).isoformat()
            changed += 1
    (folder / "SUBMISSIONS_realistic.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{changed} valid submissions re-dated; {len(subs) - changed} unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
