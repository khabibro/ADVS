"""Structural difference between two rule documents, worded with the rule sentences."""

from __future__ import annotations

from typing import Any

from app.checklists.catalog import document_label
from app.checklists.sentences import (
    check_date_sentence,
    comparison_label,
    comparison_sentence,
    document_sentences,
    identity_sentence,
    threshold_label,
    threshold_sentence,
)


def _change(area: str, label: str, before: str | None, after: str | None) -> dict[str, Any]:
    kind = "ADDED" if before is None else "REMOVED" if after is None else "CHANGED"
    return {"area": area, "label": label, "kind": kind, "before": before, "after": after}


def _compare_keyed(
    area: str,
    old: dict[str, Any],
    new: dict[str, Any],
    sentence: Any,
    label: Any,
) -> list[dict[str, Any]]:
    out = []
    for key in list(old) + [k for k in new if k not in old]:
        before = sentence(old[key]) if key in old else None
        after = sentence(new[key]) if key in new else None
        if before != after:
            out.append(_change(area, label(old.get(key) or new[key]), before, after))
    return out


def diff_documents(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    old_docs = {item["type"]: item for item in old.get("documents", [])}
    new_docs = {item["type"]: item for item in new.get("documents", [])}
    for kind in list(old_docs) + [k for k in new_docs if k not in old_docs]:
        before = (
            {s["rule"]: s["text"] for s in document_sentences(old_docs[kind])}
            if kind in old_docs
            else {}
        )
        after = (
            {s["rule"]: s["text"] for s in document_sentences(new_docs[kind])}
            if kind in new_docs
            else {}
        )
        for rule in list(before) + [r for r in after if r not in before]:
            if before.get(rule) != after.get(rule):
                changes.append(
                    _change("documents", document_label(kind), before.get(rule), after.get(rule))
                )
    changes += _compare_keyed(
        "comparisons",
        {c["id"]: c for c in old.get("comparisons", [])},
        {c["id"]: c for c in new.get("comparisons", [])},
        comparison_sentence,
        comparison_label,
    )
    changes += _compare_keyed(
        "thresholds",
        {t["id"]: t for t in old.get("thresholds", [])},
        {t["id"]: t for t in new.get("thresholds", [])},
        threshold_sentence,
        threshold_label,
    )
    if old.get("check_date") != new.get("check_date"):
        changes.append(
            _change(
                "check_date",
                "점검 기준일",
                check_date_sentence(old.get("check_date", {})),
                check_date_sentence(new.get("check_date", {})),
            )
        )
    if old.get("identity_match") != new.get("identity_match"):
        changes.append(
            _change(
                "identity",
                "제출자 정보 비교",
                identity_sentence(old.get("identity_match", {})),
                identity_sentence(new.get("identity_match", {})),
            )
        )
    if (old.get("name_ko"), old.get("description_ko")) != (
        new.get("name_ko"),
        new.get("description_ko"),
    ):
        changes.append(_change("name", "업무 이름·설명", old.get("name_ko"), new.get("name_ko")))
    return changes
