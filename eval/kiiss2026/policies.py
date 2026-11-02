"""Evaluation-only acceptance policies for the KIISS 2026 experiments.

Nothing in apps/api is modified. `install()` replaces the module-level name `decide` that
`app.services.auto_acceptance.decisions_for_project` calls, inside the evaluation process only.
Every policy returns the same `{(document_id, field): AutoDecision}` mapping the production code
returns, so verification, review items and effective values run through the unchanged pipeline.

Policy kinds
------------
advs        production acceptance (strategy S8 = the default on main) with optional switches:
              off_docs     cross-document agreement/disagreement is not used at all
              off_app      application-entered values are not used (acceptance evidence only)
              off_second   second OCR read (different preprocessing) is not used (no confirm, no veto)
              off_internal S7 instead of S8 (document-internal confirmations removed)
              h14          agreement between documents alone does not confirm; it needs the
                           application value, or a valid check digit (business registration number)
conf        pure confidence baseline: an OCR-read field with a value is accepted iff conf >= tau
conf_gated  conf + the extractor's own review/semantic flags (so extraction doubts are respected)
conf_fmt    production strategy S2 (format validators + extraction flags) with the floor set to tau
none        every OCR field goes to a person (all-to-human point)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, replace
from typing import Any

core: Any = None  # app.document_intelligence.auto_acceptance (imported by install(), after the
svc: Any = None  # harness has pointed DATABASE_URL at its scratch database)
_ORIGINAL_DECIDE: Any = None
_ORIGINAL_GROUP_VALUES: Any = None


@dataclass(frozen=True)
class Policy:
    name: str
    kind: str = "advs"
    tau: float | None = None
    off_docs: bool = False
    off_app: bool = False
    off_second: bool = False
    off_internal: bool = False
    h14: bool = False


ACTIVE: Policy = Policy("ADVS")


def set_active(policy: Policy) -> None:
    global ACTIVE
    ACTIVE = policy


def _no(reason: str) -> Any:
    return core.AutoDecision(False, "EVAL", rule_id=None, reason=reason)


def _conf_decide(fields: Any, tau: float, gated: bool) -> dict[Any, Any]:
    out: dict[Any, Any] = {}
    for item in fields:
        if not item.ocr or item.value is None or item.has_current_review:
            continue
        key = (item.document_id, item.field_name)
        if gated:
            semantic = bool(item.extraction_method and "semantic" in item.extraction_method)
            if item.needs_review or semantic:
                out[key] = _no("EXTRACTION_FLAG")
                continue
        if item.confidence is None or item.confidence < tau:
            out[key] = _no("CONFIDENCE_BELOW_TAU")
            continue
        out[key] = core.AutoDecision(True, "EVAL", rule_id=f"CONF>={tau}")
    return out


def eval_decide(fields: Any, context: Any, strategy: Any) -> dict[Any, Any]:
    p = ACTIVE
    fields = list(fields)
    if p.kind == "none":
        return {}
    if p.kind == "conf":
        return _conf_decide(fields, float(p.tau), gated=False)
    if p.kind == "conf_gated":
        return _conf_decide(fields, float(p.tau), gated=True)
    if p.kind == "conf_fmt":
        saved = dict(core.FIELD_RULES)
        try:
            for name, rule in saved.items():
                core.FIELD_RULES[name] = replace(rule, floor=float(p.tau))
            return _ORIGINAL_DECIDE(fields, context, core.Strategy.S2)
        finally:
            core.FIELD_RULES.clear()
            core.FIELD_RULES.update(saved)
    assert p.kind == "advs", p.kind
    if p.off_second:
        fields = [replace(item, second_pass=None) for item in fields]
    if p.off_app:
        context = replace(context, company_name=None, applicant_name=None)
    chosen = core.Strategy.S7 if p.off_internal else core.Strategy.S8
    if p.off_docs:
        core._group_values = lambda *a, **k: ([], [])  # type: ignore[assignment]
    try:
        decisions = _ORIGINAL_DECIDE(fields, context, chosen)
    finally:
        core._group_values = _ORIGINAL_GROUP_VALUES  # type: ignore[assignment]
    if p.h14:
        for key, decision in list(decisions.items()):
            if not decision.accepted or tuple(decision.sources) != ("documents",):
                continue
            rule = core.FIELD_RULES.get(key[1])
            if rule is not None and rule.group == "business_number":
                continue  # the validated check digit also confirms it
            decisions[key] = dataclasses.replace(
                decision, accepted=False, reason="AGREEMENT_ONLY_NOT_CONFIRMING", sources=()
            )
    return decisions


def install() -> None:
    global core, svc, _ORIGINAL_DECIDE, _ORIGINAL_GROUP_VALUES
    import app.document_intelligence.auto_acceptance as core_module
    import app.services.auto_acceptance as svc_module

    core, svc = core_module, svc_module
    _ORIGINAL_DECIDE = core.decide
    _ORIGINAL_GROUP_VALUES = core._group_values
    svc.decide = eval_decide


def signature(decisions: dict[Any, Any]) -> frozenset:
    """Memo key: the complete decision map (everything downstream code could read), not only the accepted set."""
    return frozenset(
        (key, d.accepted, d.robust, d.reason, d.repair_candidate, tuple(d.sources), d.rule_id,
         tuple(d.corroborating_document_ids), d.second_pass_value)
        for key, d in decisions.items()
    )
