"""Aggregate the policy runs into the CSV tables and SVG plots of eval/kiiss2026/.

    cd apps/api && PYTHONPATH=. .venv312/bin/python ../../eval/kiiss2026/analyze.py

Reads runs/summary_*.json and runs/inj_rows_*.csv.gz; writes tables/*.csv and figures/*.svg.
All error bounds are Clopper-Pearson, ONE-SIDED 95% upper bounds unless a column says otherwise;
`rule3` columns (3/n) are given only where the count is zero.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stats  # noqa: E402
import svgplot  # noqa: E402

RUNS = HERE / "runs"
TABLES = HERE / "tables"
FIGS = HERE / "figures"
TABLES.mkdir(exist_ok=True)
FIGS.mkdir(exist_ok=True)

CORPORA = ["dev", "holdout", "holdout2", "holdout3"]
LABEL = {"dev": "dev", "holdout": "hold-out 1", "holdout2": "hold-out 2", "holdout3": "hold-out 3",
         "HO123": "hold-outs 1+2+3"}
OCR = ("scanned", "images")
SEL = json.loads((HERE / "selected_tau.json").read_text()) if (HERE / "selected_tau.json").exists() else {}


def family(name: str) -> str:
    if name == "ADVS":
        return "advs"
    if name.startswith("ABL-"):
        return "ablation"
    if name == "H14":
        return "h14"
    if name == "NONE":
        return "none"
    prefix = name.split("@")[0]
    return {"CONF": "conf", "CONFG": "conf_gated", "CONFF": "conf_fmt", "CONF*": "conf_matched",
            "CONFG*": "conf_gated_matched", "CONFF*": "conf_fmt_matched"}[prefix]


def tau_of(name: str) -> str:
    return name.split("@")[1] if "@" in name else ""


def ub(k: int, n: int) -> str:
    return f"{100 * stats.upper_one_sided(k, n):.3f}" if n else ""


def r3(k: int, n: int) -> str:
    return f"{100 * stats.rule_of_three(n):.3f}" if (n and k == 0) else ""


def write(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    with (TABLES / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("wrote", name, len(rows))


# --------------------------------------------------------------------------- load


def load_summaries() -> dict[tuple[str, str], dict]:
    out = {}
    for path in sorted(RUNS.glob("summary_*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if path.stem.endswith("_select"):
            continue
        out[(d["corpus"], d["pass"])] = d
    return out


def load_injection(corpus: str, pass_: str) -> list[dict]:
    path = RUNS / f"inj_rows_{corpus}_{pass_}.csv.gz"
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- clean tables


def pooled_ocr(rows: list[dict]) -> dict:
    out: dict = {"version": "ocr_pooled"}
    keys = [k for k in rows[0] if k != "version"]
    for k in keys:
        out[k] = sum(r[k] for r in rows if r["version"] in OCR)
    return out


def clean_rows(summaries) -> list[dict]:
    out = []
    for (corpus, pass_), d in summaries.items():
        for entry in d.get("clean", []):
            rows = entry["rows"] + [pooled_ocr(entry["rows"])]
            for r in rows:
                n = r["submissions"]
                out.append({
                    "corpus": corpus, "pass": pass_, "policy": entry["policy"], "family": family(entry["policy"]),
                    "tau": tau_of(entry["policy"]), "input_type": r["version"],
                    "submissions": n,
                    "not_ready_submissions(denominator)": r["not_ready_n"],
                    "false_ready_in_not_ready": r["false_ready_in_not_ready"],
                    "false_ready_ub95_onesided_pct": ub(r["false_ready_in_not_ready"], r["not_ready_n"]),
                    "false_ready_rule3_pct": r3(r["false_ready_in_not_ready"], r["not_ready_n"]),
                    "false_ready_wrong_value_in_other_submissions": r["false_ready_wrong_value"],
                    "fields_evaluated": r["fields_evaluated"],
                    "machine_wrong": r["machine_wrong"],
                    "unresolved_fields_machine_null": r["machine_unresolved"],
                    "accepted_fields(acted_on)": r["accepted_fields"],
                    "false_auto_accepted_fields": r["false_auto_accepted_fields"],
                    "false_auto_accept_ub95_onesided_pct(of accepted)": ub(r["false_auto_accepted_fields"], r["accepted_fields"]),
                    "false_auto_accept_rule3_pct": r3(r["false_auto_accepted_fields"], r["accepted_fields"]),
                    "review_fields_total": r["review_fields"],
                    "mean_review_fields_per_submission": f"{r['review_fields'] / n:.3f}" if n else "",
                    "submissions_with_any_review_field": r["subs_with_review"],
                    "fully_automatic_submissions": r["auto_decided"] if r["version"] in OCR or r["version"] == "ocr_pooled" else "",
                    "fully_automatic_and_equal_to_digital_expectation": r["auto_decided_correct"] if r["version"] in OCR or r["version"] == "ocr_pooled" else "",
                })
    return out


# --------------------------------------------------------------------------- injection tables


def inj_agg(rows: list[dict]) -> dict:
    ex = [r for r in rows if r["exercised"] == "1"]
    n = len(ex)
    rev = [float(r["review_fields"]) for r in ex if r["review_fields"] not in ("", "None")]
    return {
        "cases": n,
        "effective_cases": sum(r["effective"] == "1" for r in ex),
        "false_auto_accept_cases": sum(r["false_auto_accept"] == "1" for r in ex),
        "false_ready_cases": sum(r["false_ready"] == "1" for r in ex),
        "target_fields": sum(int(r["n_targets"]) for r in ex),
        "false_accepted_target_fields": sum(int(r["n_target_wrong"]) for r in ex),
        "auto_decided_cases": sum(r["status"] in ("READY", "NEEDS_CORRECTION") for r in ex),
        "mean_review_fields_per_case": (sum(rev) / len(rev)) if rev else None,
        "review_cases(n with burden)": len(rev),
    }


def injected_rows(all_inj: dict[tuple[str, str], list[dict]]) -> list[dict]:
    out = []
    for (corpus, pass_), rows in all_inj.items():
        by_policy = defaultdict(list)
        for r in rows:
            by_policy[r["policy"]].append(r)
        for policy, prs in by_policy.items():
            groups = {"all": prs, "scanned": [r for r in prs if r["version"] == "scanned"], "images": [r for r in prs if r["version"] == "images"]}
            for label, g in groups.items():
                a = inj_agg(g)
                m = a["mean_review_fields_per_case"]
                out.append({
                    "corpus": corpus, "pass": pass_, "policy": policy, "family": family(policy), "tau": tau_of(policy), "input_type": label,
                    "cases(denominator)": a["cases"], "effective_cases(error actually read)": a["effective_cases"],
                    "false_auto_accept_cases": a["false_auto_accept_cases"],
                    "false_auto_accept_ub95_onesided_pct(of cases)": ub(a["false_auto_accept_cases"], a["cases"]),
                    "false_auto_accept_rule3_pct": r3(a["false_auto_accept_cases"], a["cases"]),
                    "false_ready_cases": a["false_ready_cases"],
                    "false_ready_ub95_onesided_pct(of cases)": ub(a["false_ready_cases"], a["cases"]),
                    "false_ready_rule3_pct": r3(a["false_ready_cases"], a["cases"]),
                    "injected_target_fields(denominator)": a["target_fields"],
                    "false_accepted_target_fields": a["false_accepted_target_fields"],
                    "false_accepted_target_ub95_onesided_pct": ub(a["false_accepted_target_fields"], a["target_fields"]),
                    "mean_review_fields_per_case": f"{m:.3f}" if m is not None else "",
                    "fully_automatic_cases": a["auto_decided_cases"],
                })
    return out


def injected_by_error(all_inj, names: set[str]) -> list[dict]:
    out = []
    for (corpus, pass_), rows in all_inj.items():
        groups = defaultdict(list)
        for r in rows:
            if r["policy"] in names:
                key = r["error"] + (f"{'c' if (r['error'] in ('E13','E14') and 'c-' in r['case']) else ''}") + ("-both" if r["both_passes"] == "1" else "")
                groups[(r["policy"], key)].append(r)
        for (policy, err), g in sorted(groups.items()):
            a = inj_agg(g)
            out.append({"corpus": corpus, "pass": pass_, "policy": policy, "error_class": err, "cases": a["cases"],
                        "effective_cases": a["effective_cases"], "false_auto_accept_cases": a["false_auto_accept_cases"],
                        "false_ready_cases": a["false_ready_cases"],
                        "mean_review_fields_per_case": f"{a['mean_review_fields_per_case']:.3f}" if a["mean_review_fields_per_case"] is not None else ""})
    return out


# --------------------------------------------------------------------------- pooled hold-outs


def pool_clean(rows: list[dict], corpora: list[str], label: str) -> list[dict]:
    """Sum counts of several corpora (same pass) per policy and input type."""
    acc: dict = {}
    for r in rows:
        if r["corpus"] not in corpora:
            continue
        key = (r["pass"], r["policy"], r["input_type"])
        a = acc.setdefault(key, {"family": r["family"], "tau": r["tau"], "sub": 0, "nr": 0, "fr": 0, "frw": 0, "acc": 0, "faa": 0, "rev": 0, "wrong": 0, "unres": 0, "auto": 0, "ev": 0})
        a["sub"] += r["submissions"]; a["nr"] += r["not_ready_submissions(denominator)"]; a["fr"] += r["false_ready_in_not_ready"]
        a["frw"] += r["false_ready_wrong_value_in_other_submissions"]; a["acc"] += r["accepted_fields(acted_on)"]
        a["faa"] += r["false_auto_accepted_fields"]; a["rev"] += r["review_fields_total"]; a["wrong"] += r["machine_wrong"]
        a["unres"] += r["unresolved_fields_machine_null"]; a["ev"] += r["fields_evaluated"]
        a["auto"] += int(r["fully_automatic_submissions"] or 0)
    out = []
    for (pass_, policy, itype), a in acc.items():
        out.append({"corpus": label, "pass": pass_, "policy": policy, "family": a["family"], "tau": a["tau"], "input_type": itype,
                    "submissions": a["sub"], "not_ready_submissions(denominator)": a["nr"], "false_ready_in_not_ready": a["fr"],
                    "false_ready_ub95_onesided_pct": ub(a["fr"], a["nr"]), "false_ready_rule3_pct": r3(a["fr"], a["nr"]),
                    "false_ready_wrong_value_in_other_submissions": a["frw"], "fields_evaluated": a["ev"], "machine_wrong": a["wrong"],
                    "unresolved_fields_machine_null": a["unres"], "accepted_fields(acted_on)": a["acc"],
                    "false_auto_accepted_fields": a["faa"], "false_auto_accept_ub95_onesided_pct(of accepted)": ub(a["faa"], a["acc"]),
                    "false_auto_accept_rule3_pct": r3(a["faa"], a["acc"]), "review_fields_total": a["rev"],
                    "mean_review_fields_per_submission": f"{a['rev'] / a['sub']:.3f}" if a["sub"] else "",
                    "submissions_with_any_review_field": "", "fully_automatic_submissions": a["auto"] if itype in OCR or itype == "ocr_pooled" else "",
                    "fully_automatic_and_equal_to_digital_expectation": ""})
    return out


def pool_injected(rows: list[dict], corpora: list[str], label: str) -> list[dict]:
    acc: dict = {}
    for r in rows:
        if r["corpus"] not in corpora:
            continue
        key = (r["pass"], r["policy"], r["input_type"])
        a = acc.setdefault(key, {"family": r["family"], "tau": r["tau"], "n": 0, "eff": 0, "fa": 0, "fr": 0, "tf": 0, "fat": 0, "rev": 0.0, "auto": 0})
        n = r["cases(denominator)"]
        a["n"] += n; a["eff"] += r["effective_cases(error actually read)"]; a["fa"] += r["false_auto_accept_cases"]
        a["fr"] += r["false_ready_cases"]; a["tf"] += r["injected_target_fields(denominator)"]; a["fat"] += r["false_accepted_target_fields"]
        a["auto"] += r["fully_automatic_cases"]
        if r["mean_review_fields_per_case"] != "":
            a["rev"] += float(r["mean_review_fields_per_case"]) * n
    out = []
    for (pass_, policy, itype), a in acc.items():
        out.append({"corpus": label, "pass": pass_, "policy": policy, "family": a["family"], "tau": a["tau"], "input_type": itype,
                    "cases(denominator)": a["n"], "effective_cases(error actually read)": a["eff"], "false_auto_accept_cases": a["fa"],
                    "false_auto_accept_ub95_onesided_pct(of cases)": ub(a["fa"], a["n"]), "false_auto_accept_rule3_pct": r3(a["fa"], a["n"]),
                    "false_ready_cases": a["fr"], "false_ready_ub95_onesided_pct(of cases)": ub(a["fr"], a["n"]), "false_ready_rule3_pct": r3(a["fr"], a["n"]),
                    "injected_target_fields(denominator)": a["tf"], "false_accepted_target_fields": a["fat"],
                    "false_accepted_target_ub95_onesided_pct": ub(a["fat"], a["tf"]),
                    "mean_review_fields_per_case": f"{a['rev'] / a['n']:.3f}" if a["n"] else "", "fully_automatic_cases": a["auto"]})
    return out


# --------------------------------------------------------------------------- plots


def pick(rows, corpus, pass_, itype, policy):
    for r in rows:
        if r["corpus"] == corpus and r["pass"] == pass_ and r["input_type"] == itype and r["policy"] == policy:
            return r
    return None


def plots(clean, inj, corpora_labels):
    for corpus in corpora_labels:
        for kind in ("clean", "injected"):
            rows = clean if kind == "clean" else inj
            sel = [r for r in rows if r["corpus"] == corpus and r["pass"] == "P0" and r["input_type"] == ("ocr_pooled" if kind == "clean" else "all")]
            if not sel:
                continue
            xk = "mean_review_fields_per_submission" if kind == "clean" else "mean_review_fields_per_case"
            for ymetric, ycol_c, ycol_i, ylabel in (
                ("false_ready", "false_ready_in_not_ready" , "false_ready_cases", "false READY (count)"),
                ("false_auto_accept", "false_auto_accepted_fields", "false_auto_accept_cases", "false auto-accepted (count)"),
            ):
                ycol = ycol_c if kind == "clean" else ycol_i
                series, points = [], []
                for fam, color, nm in (("conf", "conf", "confidence >= tau (pure)"), ("conf_gated", "conf_gated", "confidence + extractor flags"),
                                       ("conf_fmt", "conf_fmt", "confidence + format checks (S2)")):
                    pts = sorted(((float(r[xk]), float(r[ycol])) for r in sel if r["family"] == fam and r[xk] != ""), key=lambda t: (t[0], t[1]))
                    if pts:
                        series.append({"name": nm, "color": svgplot.PALETTE[color], "xy": pts})
                for r in sel:
                    f = r["family"]
                    if f in ("advs", "ablation", "h14", "none", "conf_matched", "conf_gated_matched", "conf_fmt_matched") and r[xk] != "":
                        nm = {"advs": "ADVS (as reported)", "none": "all to human"}.get(f, r["policy"])
                        color = {"advs": "advs", "ablation": "ablation", "h14": "h14", "none": "none"}.get(f, "matched")
                        marker = {"advs": "s", "ablation": "d", "h14": "t", "none": "o"}.get(f, "o")
                        points.append({"name": nm, "color": svgplot.PALETTE[color], "x": float(r[xk]), "y": float(r[ycol]), "marker": marker})
                n_den = sel[0].get("submissions") if kind == "clean" else sel[0].get("cases(denominator)")
                note = f"{LABEL.get(corpus, corpus)}, {'clean OCR submissions (scans+photos), n=' if kind=='clean' else 'injected-error cases E1-E18, n='}{n_den}. Injected-line confidence is drawn from U(0.95, 0.999) by the frozen suite."
                svg = svgplot.chart(f"{ylabel} vs review burden - {LABEL.get(corpus, corpus)} ({kind})", "mean review fields per submission", ylabel, series, points, note)
                (FIGS / f"risk_vs_burden_{corpus}_{kind}_{ymetric}.svg").write_text(svg, encoding="utf-8")


# --------------------------------------------------------------------------- main


def main() -> int:
    summaries = load_summaries()
    if not summaries:
        print("no runs found")
        return 1
    clean = clean_rows(summaries)
    all_inj = {(c, p): load_injection(c, p) for (c, p) in summaries if (RUNS / f"inj_rows_{c}_{p}.csv.gz").exists()}
    inj = injected_rows(all_inj)
    holds = ["holdout", "holdout2", "holdout3"]
    have = [c for c in holds if any(r["corpus"] == c for r in clean)]
    clean_all = clean + pool_clean(clean, have, "HO123") if len(have) > 1 else clean
    inj_all = inj + pool_injected(inj, [c for c in holds if any(r["corpus"] == c for r in inj)], "HO123") if len([c for c in holds if any(r["corpus"] == c for r in inj)]) > 1 else inj
    write("step1_clean_all_policies.csv", clean_all)
    write("step1_injected_all_policies.csv", inj_all)
    matched = []
    for corpus in ["dev"] + holds + ["HO123"]:
        for pass_ in ("P0",):
            for itype_c, itype_i in (("ocr_pooled", "all"), ("scanned", "scanned"), ("images", "images")):
                advs_c = pick(clean_all, corpus, pass_, itype_c, "ADVS")
                advs_i = pick(inj_all, corpus, pass_, itype_i, "ADVS")
                for prefix in ("CONF", "CONFG", "CONFF"):
                    if prefix not in SEL:
                        continue
                    name = f"{prefix}*@{SEL[prefix]['tau']:g}"
                    for who, c_row, i_row in (("ADVS", advs_c, advs_i), (name, pick(clean_all, corpus, pass_, itype_c, name), pick(inj_all, corpus, pass_, itype_i, name))):
                        if c_row is None and i_row is None:
                            continue
                        matched.append({
                            "corpus": corpus, "input_type": itype_c, "baseline_family": prefix, "tau_selected_on_dev": SEL[prefix]["tau"], "system": who,
                            "clean_submissions": (c_row or {}).get("submissions"), "clean_not_ready_denominator": (c_row or {}).get("not_ready_submissions(denominator)"),
                            "clean_false_ready": (c_row or {}).get("false_ready_in_not_ready"),
                            "clean_false_ready_ub95_pct": (c_row or {}).get("false_ready_ub95_onesided_pct"),
                            "clean_accepted_fields": (c_row or {}).get("accepted_fields(acted_on)"),
                            "clean_false_auto_accepted_fields": (c_row or {}).get("false_auto_accepted_fields"),
                            "clean_false_auto_accept_ub95_pct": (c_row or {}).get("false_auto_accept_ub95_onesided_pct(of accepted)"),
                            "clean_unresolved_fields": (c_row or {}).get("unresolved_fields_machine_null"),
                            "clean_mean_review_fields_per_submission": (c_row or {}).get("mean_review_fields_per_submission"),
                            "clean_fully_automatic_submissions": (c_row or {}).get("fully_automatic_submissions"),
                            "inj_cases": (i_row or {}).get("cases(denominator)"),
                            "inj_false_auto_accept_cases": (i_row or {}).get("false_auto_accept_cases"),
                            "inj_false_auto_accept_ub95_pct": (i_row or {}).get("false_auto_accept_ub95_onesided_pct(of cases)"),
                            "inj_false_ready_cases": (i_row or {}).get("false_ready_cases"),
                            "inj_false_ready_ub95_pct": (i_row or {}).get("false_ready_ub95_onesided_pct(of cases)"),
                            "inj_false_accepted_target_fields": (i_row or {}).get("false_accepted_target_fields"),
                            "inj_injected_target_fields": (i_row or {}).get("injected_target_fields(denominator)"),
                            "inj_mean_review_fields_per_case": (i_row or {}).get("mean_review_fields_per_case"),
                            "inj_fully_automatic_cases": (i_row or {}).get("fully_automatic_cases"),
                        })
    write("step1_matched_burden.csv", matched)

    ablation_names = {"ADVS", "ABL-a_no_docs", "ABL-b_no_app", "ABL-c_no_second", "ABL-d_no_internal", "H14", "NONE"}
    write("step2_ablations_clean.csv", [r for r in clean_all if r["policy"] in ablation_names])
    write("step2_ablations_injected.csv", [r for r in inj_all if r["policy"] in ablation_names])
    write("step3_h14_clean.csv", [r for r in clean_all if r["policy"] in {"ADVS", "H14"}])
    write("step3_h14_injected.csv", [r for r in inj_all if r["policy"] in {"ADVS", "H14"}])
    names = ablation_names | {f"{p}*@{SEL[p]['tau']:g}" for p in SEL if p in ("CONF", "CONFG", "CONFF")}
    write("step1_injected_by_error_class.csv", injected_by_error(all_inj, names))

    # leaks of ADVS-type policies (reproduces the known hold-out 2 false READY)
    leaks_out = {}
    for (corpus, pass_), d in summaries.items():
        for pol_name, leaks in (d.get("injection_leaks") or {}).items():
            if pol_name in ablation_names and leaks:
                leaks_out[f"{corpus}/{pass_}/{pol_name}"] = leaks
    (TABLES / "leaks_advs_family.json").write_text(json.dumps(leaks_out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("leak lists:", {k: len(v) for k, v in leaks_out.items()})

    # runtimes
    write("runtimes.csv", [{"corpus": c, "pass": p, "clean_seconds": d.get("clean_seconds"), "injection_seconds": d.get("injection_seconds"),
                            "total_seconds": d.get("runtime_seconds"), "policies": len(d["policies"]), "verify_calls": d.get("verify_calls"),
                            "reused_calls": d.get("reuse_calls"), "ocr_cache_misses_computed": d.get("ocr_cache_misses_computed"), "git_head": d.get("git_head")}
                           for (c, p), d in summaries.items()])
    plots(clean_all, inj_all, ["dev"] + holds + ["HO123"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
