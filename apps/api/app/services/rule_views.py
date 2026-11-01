"""One reading of "the rules this submission is judged by", whatever stores them.

A submission pinned to a checklist version reads that version, compiled exactly as the
verification compiles it; an old row-based workflow reads its rows. Everything that needs to know
which fields and thresholds matter (review dependencies, document validation, the acceptance
boundaries) goes through here, so an edited rule moves all of them together.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.checklists.compile import compile_checklist
from app.checklists.schema import parse_document
from app.core.domain import DocumentType
from app.models.entities import Project
from app.services.requirements import required_fields


@dataclass(frozen=True)
class ViewRule:
    rule_type: str
    severity: str
    params: dict


@dataclass(frozen=True)
class DocumentRulesView:
    document_type: DocumentType
    required: bool
    required_fields: tuple[str, ...]
    rules: tuple[ViewRule, ...]


def rule_views(project: Project) -> list[DocumentRulesView]:
    version = project.checklist_version
    if version is not None:
        document, problems = parse_document(version.document)
        if document is None or problems:
            return []
        return [
            DocumentRulesView(
                item.document_type,
                item.required,
                item.required_fields,
                tuple(ViewRule(r.rule_type.value, r.severity.value, r.params) for r in item.rules),
            )
            for item in compile_checklist(document).requirements
        ]
    if project.checklist is None:
        return []
    out: list[DocumentRulesView] = []
    for requirement in project.checklist.requirements:
        try:
            document_type = DocumentType(requirement.document_type)
        except ValueError:
            continue
        out.append(
            DocumentRulesView(
                document_type,
                requirement.required,
                required_fields(requirement),
                tuple(ViewRule(r.rule_type, r.severity, r.params or {}) for r in requirement.rules),
            )
        )
    return out
