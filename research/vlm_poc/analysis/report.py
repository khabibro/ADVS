"""Tables for research/vlm_poc/COMPARISON.md from the per-corpus field rows, crop readings and
injection results. Uses the frozen scorer's normaliser; every proportion is printed with n and a
Wilson interval, every zero with the rule-of-three bound.

  PYTHONPATH=<app>/apps/api python analysis/report.py --label dev --harness <harness> \
      --fields results/fields_dev.json results/fields_holdout.json ... \
      [--crops results/crops_dev results/crops_holdout ...] [--readings results/crop_readings_dev.json ...] \
      [--inj <G_inj_dev.json> ...] [--pages results/pages_test_variants ...] --out results/tables_dev.md
"""
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fmt  # noqa: E402

GROUPS = {"business number": {"business_registration_number"}, "dates": {"valid_from", "valid_until", "issue_date", "graduation_date", "opening_date"},
          "student number / GPA": {"student_id", "gpa", "gpa_scale"}}


def group_of(field: str) -> str:
    for name, members in GROUPS.items():
        if field in members or (name == "dates" and field.endswith("_date")):
            return name
    return "names and text"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--harness", type=Path, required=True)
    ap.add_argument("--fields", type=Path, nargs="+", required=True)
    ap.add_argument("--crops", type=Path, nargs="*", default=[])
    ap.add_argument("--readings", type=Path, nargs="*", default=[])
    ap.add_argument("--inj", type=Path, nargs="*", default=[])
    ap.add_argument("--pages", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(args.harness))
    import score_v2  # type: ignore[import-not-found]

    from app.document_intelligence.auto_acceptance import parse_second_pass

    rows = []
    for path in args.fields:
        rows += json.loads(path.read_text(encoding="utf-8"))["rows"]
    rows = [r for r in rows if r["state"] == "KNOWN_VALUE" and r["b_outcome"] is not None]
    out: list[str] = []
    w = out.append
    w(f"# Tables — {args.label}\n")
    w(f"Fields scored: {len(rows)} (KNOWN_VALUE fields of files that both engines processed). Scorer `score_v2.py` sha256 `{json.loads(args.fields[0].read_text())['meta']['scorer_sha256']}`.\n")

    def err(o: str) -> bool:
        return o != "CORRECT"

    # 1. accuracy per input type and field group
    w("## 1. Exact-match accuracy, wrong non-null values and hallucinations (value not printed on the page)\n")
    w("| Input | Field group | n | A correct | B correct | A wrong non-null | B wrong non-null | B wrong and not on the page | B unresolved |")
    w("|---|---|---|---|---|---|---|---|---|")
    for itype in ("digital", "scan", "photo"):
        for grp in (*GROUPS, "names and text", "ALL"):
            sel = [r for r in rows if r["input"] == itype and (grp == "ALL" or group_of(r["field"]) == grp)]
            if not sel:
                continue
            n = len(sel)
            a_ok = sum(r["a_outcome"] == "CORRECT" for r in sel)
            b_ok = sum(r["b_outcome"] == "CORRECT" for r in sel)
            a_w = sum(r["a_outcome"] == "WRONG" for r in sel)
            b_w = sum(r["b_outcome"] == "WRONG" for r in sel)
            b_h = sum(r["b_outcome"] == "WRONG" and r["b_on_page"] is False for r in sel)
            b_u = sum(r["b_outcome"] == "UNRESOLVED" for r in sel)
            w(f"| {itype} | {grp} | {n} | {fmt(a_ok, n)} | {fmt(b_ok, n)} | {fmt(a_w, n)} | {fmt(b_w, n)} | {fmt(b_h, n)} | {fmt(b_u, n)} |")
    w("")
    w("## 2. Per document type (all input types together)\n")
    w("| Document type | n | A correct | B correct |")
    w("|---|---|---|---|")
    for dt in sorted({r["doc_type"] for r in rows}):
        sel = [r for r in rows if r["doc_type"] == dt]
        w(f"| {dt} | {len(sel)} | {fmt(sum(r['a_outcome'] == 'CORRECT' for r in sel), len(sel))} | {fmt(sum(r['b_outcome'] == 'CORRECT' for r in sel), len(sel))} |")
    w("")
    # 3. joint errors
    w("## 3. Joint errors, A (current OCR) and B (VLM page parse)\n")
    w("Error = not correct (wrong or unresolved). 'Identical' = both produced the same wrong value.\n")
    w("| Input | Field group | n | P(A err) | P(B err) | P(A err and B err) | P(both wrong and identical output) |")
    w("|---|---|---|---|---|---|---|")
    for itype in ("digital", "scan", "photo"):
        for grp in (*GROUPS, "names and text", "ALL"):
            sel = [r for r in rows if r["input"] == itype and (grp == "ALL" or group_of(r["field"]) == grp)]
            if not sel:
                continue
            n = len(sel)
            both = sum(err(r["a_outcome"]) and err(r["b_outcome"]) for r in sel)
            same = sum(r["a_outcome"] == "WRONG" and r["b_outcome"] == "WRONG" and score_v2.normalize(r["field"], r["a_value"]) == score_v2.normalize(r["field"], r["b_value"]) for r in sel)
            w(f"| {itype} | {grp} | {n} | {fmt(sum(err(r['a_outcome']) for r in sel), n)} | {fmt(sum(err(r['b_outcome']) for r in sel), n)} | {fmt(both, n)} | {fmt(same, n)} |")
    w("")
    # 4. simulated automation gain with B
    w("## 4. Simulated automation gain if exact agreement were accepted as confirmation (no production change)\n")
    w("Rows are fields that the current system leaves to a person (A decision NEEDS_HUMAN, scans and photos). Agreement = both engines produced the same normalised value.\n")
    w("| Method | Field group | fields needing a person | would be auto-accepted | of those wrong (simulated false auto-accepts) |")
    w("|---|---|---|---|---|")
    need = [r for r in rows if r["a_decision"] == "NEEDS_HUMAN" and r["input"] != "digital"]
    for grp in (*GROUPS, "names and text", "ALL"):
        sel = [r for r in need if grp == "ALL" or group_of(r["field"]) == grp]
        if not sel:
            continue
        agree = [r for r in sel if r["a_value"] is not None and r["b_value"] is not None and score_v2.normalize(r["field"], r["a_value"]) == score_v2.normalize(r["field"], r["b_value"])]
        bad = [r for r in agree if r["a_outcome"] != "CORRECT"]
        w(f"| B page parse | {grp} | {len(sel)} | {fmt(len(agree), len(sel))} | {fmt(len(bad), len(agree)) if agree else 'n/a (nothing accepted)'} |")
    # D from crops
    crops, readings = [], {}
    for cdir, rpath in zip(args.crops, args.readings):
        items = json.loads((cdir / "crops.json").read_text(encoding="utf-8"))
        got = json.loads(rpath.read_text(encoding="utf-8"))
        for item in items:
            reading = got.get(item["id"], {})
            item["text"] = reading.get("text")
            item["seconds"] = reading.get("seconds")
            item["corpus_dir"] = str(cdir)
            crops.append(item)

    def d_value(item: dict):
        text = item.get("text")
        if text is None:
            return None
        parsed = parse_second_pass(item["field"], text)
        return parsed

    def d_agrees(item: dict) -> bool:
        text = item.get("text")
        if not text or item["a_value"] is None:
            return False
        if item["field"] in {"business_registration_number", "valid_from", "valid_until", "issue_date", "gpa", "gpa_scale", "student_id"}:
            parsed = d_value(item)
            return parsed is not None and score_v2.normalize(item["field"], parsed) == score_v2.normalize(item["field"], item["a_value"])
        return score_v2.text_key(item["a_value"]) in score_v2.text_key(text)

    if crops:
        for grp in (*GROUPS, "names and text", "ALL"):
            sel = [c for c in crops if c["a_decision"] == "NEEDS_HUMAN" and c["input"] != "digital" and (grp == "ALL" or group_of(c["field"]) == grp)]
            if not sel:
                continue
            agree = [c for c in sel if d_agrees(c)]
            bad = [c for c in agree if score_v2.normalize(c["field"], c["a_value"]) != score_v2.normalize(c["field"], c["expected"])]
            w(f"| D selective crops | {grp} | {len(sel)} | {fmt(len(agree), len(sel))} | {fmt(len(bad), len(agree)) if agree else 'n/a (nothing accepted)'} |")
        w("")
        w("## 5. Method D: VLM reading of field crops (confirms or disputes A's value)\n")
        w("| Input | Field group | crops | VLM parsed reading equals the expected value | A value wrong | of those, VLM disputes A | A value right | of those, VLM confirms A |")
        w("|---|---|---|---|---|---|---|---|")
        for itype in ("digital", "scan", "photo"):
            for grp in (*GROUPS, "names and text", "ALL"):
                sel = [c for c in crops if c["input"] == itype and (grp == "ALL" or group_of(c["field"]) == grp)]
                if not sel:
                    continue
                reads = [c for c in sel if c["field"] in {"business_registration_number", "valid_from", "valid_until", "issue_date", "gpa", "gpa_scale", "student_id"}]
                right_read = sum(d_value(c) is not None and score_v2.normalize(c["field"], d_value(c)) == score_v2.normalize(c["field"], c["expected"]) for c in reads)
                a_bad = [c for c in sel if score_v2.normalize(c["field"], c["a_value"]) != score_v2.normalize(c["field"], c["expected"])]
                a_ok = [c for c in sel if c not in a_bad]
                w(f"| {itype} | {grp} | {len(sel)} | {fmt(right_read, len(reads)) if reads else 'n/a'} | {len(a_bad)} | {fmt(sum(not d_agrees(c) for c in a_bad), len(a_bad)) if a_bad else 'n/a'} | {len(a_ok)} | {fmt(sum(d_agrees(c) for c in a_ok), len(a_ok)) if a_ok else 'n/a'} |")
        w("")
    # 6. injection catch rates
    if args.inj:
        w("## 6. Error catching on the injected-error suites (E1–E18)\n")
        w("The suite corrupts the OCR reading of a field; the VLM reads the real pixels. Caught = the VLM value exists and differs from the injected one.\n")
        by_file = collections.defaultdict(list)
        for r in rows:
            by_file[(r["file"].rsplit("/", 1)[-1], r["field"])].append(r)
        crop_by = collections.defaultdict(list)
        for c in crops:
            crop_by[(c["file"].rsplit("/", 1)[-1], c["field"])].append(c)
        tally = {"B": collections.Counter(), "D": collections.Counter()}
        for path in args.inj:
            for case in json.loads(path.read_text(encoding="utf-8"))["results"]:
                if not case.get("exercised", True):
                    continue
                for t in case["targets"]:
                    if t.get("injected") in (None, t.get("expected")):
                        continue
                    key = (t["file"], t["field"])
                    inj = score_v2.normalize(t["field"], t["injected"])
                    for rr in by_file.get(key, [])[:1]:
                        v = rr["b_value"]
                        tally["B"]["caught" if v is not None and score_v2.normalize(t["field"], v) != inj else ("missed" if v is not None else "no reading")] += 1
                    for cc in crop_by.get(key, [])[:1]:
                        v = d_value(cc) if cc["field"] in {"business_registration_number", "valid_from", "valid_until", "issue_date", "gpa", "gpa_scale", "student_id"} else cc.get("text")
                        if cc["field"] in {"business_registration_number", "valid_from", "valid_until", "issue_date", "gpa", "gpa_scale", "student_id"}:
                            state = "caught" if v is not None and score_v2.normalize(t["field"], v) != inj else ("missed" if v is not None else "no reading")
                        else:
                            state = "caught" if v and score_v2.text_key(t["injected"]) not in score_v2.text_key(v) else ("missed" if v else "no reading")
                        tally["D"][state] += 1
        w("| Method | injected targets with a reading | caught | missed (VLM reproduces the injected value) | no usable reading |")
        w("|---|---|---|---|---|")
        for name, label in (("B", "B page parse"), ("D", "D field crop")):
            c = tally[name]
            total = sum(c.values())
            w(f"| {label} | {total} | {fmt(c['caught'], total) if total else 'n/a'} | {fmt(c['missed'], total) if total else 'n/a'} | {c['no reading']} |")
        w("")
    # 7. latency
    w("## 7. Speed\n")
    secs, pages_n, per_file = [], 0, []
    for d in args.pages:
        for line in (d / "_timing.jsonl").read_text().splitlines() if (d / "_timing.jsonl").exists() else []:
            item = json.loads(line)
            per_file.append(item["seconds"])
            if item["pages"]:
                secs.append(item["seconds"] / item["pages"])
                pages_n += item["pages"]
    if secs:
        w(f"- B page parse: {len(per_file)} files, {pages_n} pages; per page median {statistics.median(secs):.1f} s, mean {statistics.mean(secs):.1f} s, p95 {sorted(secs)[int(0.95 * (len(secs) - 1))]:.1f} s (Apple M3 Pro, llama.cpp Metal, layout model on CPU; other jobs were running at the same time on part of the data, so these are upper bounds).")
    cs = [c["seconds"] for c in crops if c.get("seconds")]
    if cs:
        w(f"- D field crop: {len(cs)} crops; median {statistics.median(cs):.2f} s, mean {statistics.mean(cs):.2f} s, p95 {sorted(cs)[int(0.95 * (len(cs) - 1))]:.2f} s per crop.")
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:30]))


if __name__ == "__main__":
    main()
