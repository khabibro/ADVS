"""Rule document -> the verification engine's existing inputs.

The engine is unchanged by this module; it only receives what the seeded rows used to give it. Ids
are derived from the checklist key and the rule slug, so a rule keeps its id across versions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.checklists.schema import ChecklistDocument, Comparison, DocumentRule, Threshold
from app.core.domain import DocumentType, RuleOperator, RuleType, Severity
from app.document_intelligence.validation.submission import (
    RequirementSnapshot,
    SubmissionRule,
    VerificationContext,
)
from app.services.requirements import required_field_names

_NAMESPACE = uuid.UUID("5b0c3a4e-6a52-4e0b-9d1c-2b6b6b0f8a11")
_OPERATORS = {
    "GTE": RuleOperator.GREATER_THAN_OR_EQUAL,
    "LTE": RuleOperator.LESS_THAN_OR_EQUAL,
    "EQ": RuleOperator.EQUALS,
}
_VALUE_TYPES = {"IDENTIFIER": "identifier", "TEXT": "string", "INSTITUTION": "institution"}


@dataclass(frozen=True)
class CompiledChecklist:
    requirements: list[RequirementSnapshot]
    identity_applicant_name: bool
    identity_company_name: bool

    def context(self, evaluation_date, applicant_name, company_name) -> VerificationContext:
        return VerificationContext(
            evaluation_date=evaluation_date,
            applicant_name=applicant_name if self.identity_applicant_name else None,
            company_name=company_name if self.identity_company_name else None,
        )


def rule_uuid(key: str, slug: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{key}:{slug}")


def _comparison_rule(key: str, item: Comparison) -> SubmissionRule:
    params: dict = {
        "source_document_type": item.source.document,
        "source_field": item.source.field,
        "target_document_type": item.target.document,
        "target_field": item.target.field,
        "operator": RuleOperator.EQUALS.value,
        "value_type": _VALUE_TYPES[item.match],
    }
    if not item.normalise.is_default():
        params["normalise"] = item.normalise.model_dump()
    return SubmissionRule(
        rule_uuid(key, f"cmp:{item.id}"), RuleType.FIELD_COMPARISON, Severity(item.severity), params
    )


def _threshold_rule(key: str, item: Threshold) -> SubmissionRule:
    params: dict = {
        "document_type": item.document,
        "field": item.field,
        "operator": _OPERATORS[item.operator].value,
    }
    if item.scale is not None and item.scale.mode == "PER_SCALE":
        params["per_scale"] = {
            "scale_field": item.scale.field,
            "values": dict(item.scale.per_scale or {}),
        }
    else:
        params["expected_value"] = item.value
    return SubmissionRule(
        rule_uuid(key, f"thr:{item.id}"),
        RuleType.NUMERIC_COMPARISON,
        Severity(item.severity),
        params,
    )


def _own_rules(key: str, item: DocumentRule) -> list[SubmissionRule]:
    rules: list[SubmissionRule] = []
    if item.issue_date is not None:
        rules.append(
            SubmissionRule(
                rule_uuid(key, f"age:{item.type}"),
                RuleType.ISSUE_DATE_MAX_AGE,
                Severity(item.issue_date.severity),
                {
                    "max_age_days": item.issue_date.max_age_days,
                    "document_type": item.type,
                    "field": item.issue_date.field,
                },
            )
        )
    if item.validity is not None:
        rules.append(
            SubmissionRule(
                rule_uuid(key, f"valid:{item.type}"),
                RuleType.DATE_COMPARISON,
                Severity(item.validity.severity),
                {
                    "document_type": item.type,
                    "field": item.validity.field,
                    "operator": RuleOperator.ON_OR_AFTER.value,
                    "comparison_source": "EVALUATION_DATE",
                },
            )
        )
    return rules


def compile_checklist(document: ChecklistDocument) -> CompiledChecklist:
    key = document.key
    by_document: dict[str, list[SubmissionRule]] = {
        item.type: _own_rules(key, item) for item in document.documents
    }
    # A comparison is evaluated with the document it is checked against, as the seeded rows did.
    for comparison in document.comparisons:
        by_document[comparison.target.document].append(_comparison_rule(key, comparison))
    for threshold in document.thresholds:
        by_document[threshold.document].append(_threshold_rule(key, threshold))
    requirements = [
        RequirementSnapshot(
            id=rule_uuid(key, f"doc:{item.type}"),
            document_type=DocumentType(item.type),
            required=item.requirement == "REQUIRED",
            rules=tuple(by_document[item.type]),
            required_fields=required_field_names(
                DocumentType(item.type), item.requirement == "REQUIRED", item.extra_required_fields
            ),
        )
        for item in document.documents
    ]
    return CompiledChecklist(
        requirements=requirements,
        identity_applicant_name=document.identity_match.applicant_name,
        identity_company_name=document.identity_match.company_name,
    )
