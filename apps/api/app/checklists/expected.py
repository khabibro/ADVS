"""The documents a submission is expected to contain, from its pinned version."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.entities import Checklist, ChecklistVersion


@dataclass(frozen=True)
class ExpectedDocument:
    document_type: str
    required: bool


def expected_documents(
    checklist: Checklist | None, version: ChecklistVersion | None
) -> list[ExpectedDocument]:
    if version is not None:
        return [
            ExpectedDocument(item["type"], item["requirement"] == "REQUIRED")
            for item in version.document.get("documents", [])
        ]
    if checklist is None:
        return []
    return [ExpectedDocument(r.document_type, r.required) for r in checklist.requirements]
