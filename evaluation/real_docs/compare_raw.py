"""Field-level difference between two run_variants raw outputs (gate: 0 differences against the previous freeze).

    python3 compare_raw.py A_raw.json B_raw.json

Volatile keys (git head, labels, timings, run ids) are ignored; everything else must be equal.
"""
import json
import re
import sys

IGNORE = {"git_head", "label", "run_id", "generated_at", "duration_ms", "seconds", "elapsed", "elapsed_seconds",
          "started_at", "finished_at", "timestamp", "document_id", "project_id", "id", "created_at", "processing_seconds", "process_ms", "duration", "elapsed_ms", "ms", "document_duration_ms"}


_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def walk(a, b, path, out):
    if isinstance(a, str) and isinstance(b, str):
        a, b = _UUID.sub("<uuid>", a), _UUID.sub("<uuid>", b)
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in IGNORE:
                continue
            if key not in a or key not in b:
                out.append(f"{path}/{key}: only in {'A' if key in a else 'B'}")
            else:
                walk(a[key], b[key], f"{path}/{key}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if path.endswith("review_items"):  # an unordered collection: compare as a set of items
            key = lambda item: json.dumps(item, sort_keys=True, default=str)  # noqa: E731
            a, b = sorted(a, key=lambda i: _UUID.sub("<uuid>", key(i))), sorted(b, key=lambda i: _UUID.sub("<uuid>", key(i)))
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(f"{path}: {str(a)[:40]} != {str(b)[:40]}")


if __name__ == "__main__":
    diffs: list[str] = []
    walk(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), "", diffs)
    print(f"{len(diffs)} differences")
    for line in diffs[:15]:
        print(" ", line)
    raise SystemExit(1 if diffs else 0)
