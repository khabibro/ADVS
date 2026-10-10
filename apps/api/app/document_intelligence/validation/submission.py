from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.domain import (
    EXPECTED_FIELDS,
    REVIEWABLE_FIELDS,
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    RuleOperator,
    RuleOutcome,
    RuleType,
    Severity,
)
from app.document_intelligence.evidence_sufficiency import (
    EffectiveValueSource,
    EvidenceAssessmentReason,
    EvidenceAssessmentState,
)
from app.document_intelligence.extraction.base import BRN_CHECKSUM_FAILED_METHOD
from app.document_intelligence.normalization.field_normalizer import (
    normalize_lexical_text,
    strip_legal_entity_markers,
)

# Fields where a leading/trailing legal-entity marker (주식회사 / (주) / ㈜ /
# ...) is noise, not a real difference (audit F-002) -- the same company
# routinely carries a different one of these across different certificate
# types. Scoped narrowly: business numbers and every other compared field
# are unaffected.
_COMPANY_NAME_FIELDS = frozenset({"company_name", "workplace_name"})

SUBMISSION_VERIFICATION_VERSION = "rules-v2"


class RuleConfigurationError(ValueError):
    """A persisted workflow rule cannot be evaluated safely."""


@dataclass(frozen=True)
class VerificationContext:
    evaluation_date: date
    applicant_name: str | None = None
    company_name: str | None = None


@dataclass(frozen=True)
class FieldSnapshot:
    id: uuid.UUID | None
    field_name: str
    normalized_value: str | None
    needs_review: bool
    evidence_available: bool
    assessment_state: EvidenceAssessmentState | None = None
    assessment_reasons: tuple[EvidenceAssessmentReason, ...] = ()
    effective_source: EffectiveValueSource = EffectiveValueSource.MACHINE
    review_id: uuid.UUID | None = None
    extraction_method: str | None = None


@dataclass(frozen=True)
class DocumentSnapshot:
    id: uuid.UUID
    document_type: DocumentType
    processing_status: ProcessingStatus
    checksum_sha256: str
    fields: dict[str, FieldSnapshot] = field(default_factory=dict)
    processing_version: int = 0
    classification_needs_review: bool = False
    created_at: str = ""
    multiple_documents_in_file: bool = False
    # Hidden PDF text disagrees with what the page shows (preprocessing/text_layer.py).
    text_layer_mismatch: bool = False


@dataclass(frozen=True)
class SubmissionRule:
    id: uuid.UUID
    rule_type: RuleType
    severity: Severity
    params: dict[str, Any]


@dataclass(frozen=True)
class RequirementSnapshot:
    id: uuid.UUID
    document_type: DocumentType
    required: bool
    rules: tuple[SubmissionRule, ...] = ()
    required_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    status_effect: OverallStatus
    message: str
    document_id: uuid.UUID | None = None
    document_type: DocumentType | None = None
    field_name: str | None = None
    related_document_id: uuid.UUID | None = None
    related_document_type: DocumentType | None = None
    related_field_name: str | None = None
    rule_id: uuid.UUID | None = None
    field_id: uuid.UUID | None = None
    related_field_id: uuid.UUID | None = None


@dataclass(frozen=True)
class RuleEvaluationResult:
    rule_id: uuid.UUID | None
    rule_type: RuleType
    outcome: RuleOutcome
    issue: VerificationIssue | None = None
    document_id: uuid.UUID | None = None
    document_type: DocumentType | None = None
    field_name: str | None = None
    related_document_id: uuid.UUID | None = None
    related_document_type: DocumentType | None = None
    related_field_name: str | None = None


@dataclass(frozen=True)
class SubmissionVerificationResult:
    project_id: uuid.UUID
    workflow_id: uuid.UUID
    status: OverallStatus
    evaluation_date: date
    issues: tuple[VerificationIssue, ...]
    rule_results: tuple[RuleEvaluationResult, ...]
    notices: tuple[VerificationIssue, ...] = ()


def _status_for_severity(severity: Severity) -> OverallStatus:
    return (
        OverallStatus.NEEDS_CORRECTION
        if severity == Severity.ERROR
        else OverallStatus.REVIEW_REQUIRED
    )


def aggregate_status(issues: list[VerificationIssue]) -> OverallStatus:
    if any(issue.status_effect == OverallStatus.NEEDS_CORRECTION for issue in issues):
        return OverallStatus.NEEDS_CORRECTION
    if any(issue.status_effect == OverallStatus.REVIEW_REQUIRED for issue in issues):
        return OverallStatus.REVIEW_REQUIRED
    return OverallStatus.READY


def _same_name(actual: str, expected: str, rule_type: RuleType) -> bool:
    """Exact equality of the submitter's own name/company against a document value, after
    canonicalisation only (NFKC, whitespace; for companies also the legal-entity marker, so
    주식회사 X / (주)X / ㈜X / X(주) are one company). No similarity measure."""

    def key(value: str) -> str:
        text = normalize_lexical_text(value)
        if rule_type == RuleType.COMPANY_NAME_MATCH:
            text = strip_legal_entity_markers(text)
        return "".join(text.split())

    return key(actual) == key(expected)


def _comparison_key(value: str, value_type: str) -> str:
    """Comparison-only key.

    This never rewrites the stored evidence or extracted normalized value. It
    only removes formatting differences that are safe for equality checks.
    """
    normalized = normalize_lexical_text(value)
    if value_type == "identifier":
        return "".join(character for character in normalized if character.isalnum())
    return re.sub(r"\s+", "", normalized)


class SubmissionVerificationEngine:
    """Deterministic rules over persisted canonical document fields.

    The engine never reads files or OCR text. A missing or review-marked field
    produces UNRESOLVED, never a deterministic failed condition.
    """

    version = SUBMISSION_VERIFICATION_VERSION

    def verify(
        self,
        *,
        project_id: uuid.UUID,
        workflow_id: uuid.UUID,
        requirements: list[RequirementSnapshot],
        documents: list[DocumentSnapshot],
        context: VerificationContext,
    ) -> SubmissionVerificationResult:
        self.validate_configuration(requirements)
        selected, availability_results = self._resolve_documents(requirements, documents)
        results = list(availability_results)
        for requirement in sorted(requirements, key=lambda item: item.document_type.value):
            document = selected.get(requirement.document_type)
            if document is not None:
                for name in requirement.required_fields:
                    rule = SubmissionRule(
                        requirement.id, RuleType.REQUIRED_FIELD, Severity.WARNING, {}
                    )
                    unresolved = self._unresolved_field(
                        rule, document, document.fields.get(name), name
                    )
                    if unresolved:
                        results.append(unresolved)
                results.extend(self._document_conditions(document, requirement, context))
            for rule in sorted(
                requirement.rules,
                key=lambda item: (item.rule_type.value, str(sorted(item.params.items()))),
            ):
                results.append(self._evaluate_rule(rule, selected, context))
        issues = [
            result.issue
            for result in results
            if result.issue is not None and result.outcome != RuleOutcome.NOTICE
        ]
        notices = [
            result.issue
            for result in results
            if result.issue is not None and result.outcome == RuleOutcome.NOTICE
        ]
        return SubmissionVerificationResult(
            project_id=project_id,
            workflow_id=workflow_id,
            status=aggregate_status(issues),
            evaluation_date=context.evaluation_date,
            issues=tuple(issues),
            rule_results=tuple(results),
            notices=tuple(notices),
        )

    def validate_configuration(self, requirements: list[RequirementSnapshot]) -> None:
        requirement_types = {item.document_type for item in requirements}
        for requirement in requirements:
            if any(
                name not in REVIEWABLE_FIELDS[requirement.document_type]
                for name in requirement.required_fields
            ):
                raise RuleConfigurationError("Unknown workflow-required field")
            for rule in requirement.rules:
                if rule.rule_type == RuleType.FIELD_COMPARISON:
                    self._validate_field_comparison(rule, requirement_types)
                elif rule.rule_type == RuleType.DATE_COMPARISON:
                    self._validate_value_rule(
                        rule,
                        requirement_types,
                        {RuleOperator.ON_OR_BEFORE, RuleOperator.ON_OR_AFTER},
                        "date",
                    )
                elif rule.rule_type == RuleType.NUMERIC_COMPARISON:
                    self._validate_value_rule(
                        rule,
                        requirement_types,
                        {
                            RuleOperator.GREATER_THAN_OR_EQUAL,
                            RuleOperator.LESS_THAN_OR_EQUAL,
                            RuleOperator.EQUALS,
                        },
                        "decimal",
                    )
                elif rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE:
                    document_type = self._document_type_param(rule, "document_type")
                    self._field_param(rule, "field", document_type)
                    days = rule.params.get("max_age_days", 90)
                    if (
                        document_type not in requirement_types
                        or type(days) is not int
                        or not 0 <= days <= 36500
                    ):
                        raise RuleConfigurationError(
                            "Issue-date age must be an integer from 0 to 36500 days for a workflow document"
                        )
                else:
                    raise RuleConfigurationError(
                        f"Unsupported submission rule type: {rule.rule_type}"
                    )

    def _validate_field_comparison(
        self, rule: SubmissionRule, requirement_types: set[DocumentType]
    ) -> None:
        source_type = self._document_type_param(rule, "source_document_type")
        target_type = self._document_type_param(rule, "target_document_type")
        if source_type not in requirement_types or target_type not in requirement_types:
            raise RuleConfigurationError("Comparison document type is not in the workflow")
        source_field = self._field_param(rule, "source_field", source_type)
        target_field = self._field_param(rule, "target_field", target_type)
        if not source_field or not target_field:
            raise RuleConfigurationError("Comparison fields are required")
        operator = self._operator_param(rule)
        if operator != RuleOperator.EQUALS:
            raise RuleConfigurationError("FIELD_COMPARISON only supports EQUALS")
        value_type = rule.params.get("value_type", "string")
        if value_type not in {"string", "identifier"}:
            raise RuleConfigurationError("Unsupported field-comparison value type")

    def _validate_value_rule(
        self,
        rule: SubmissionRule,
        requirement_types: set[DocumentType],
        operators: set[RuleOperator],
        value_type: str,
    ) -> None:
        document_type = self._document_type_param(rule, "document_type")
        if document_type not in requirement_types:
            raise RuleConfigurationError("Rule document type is not in the workflow")
        self._field_param(rule, "field", document_type)
        operator = self._operator_param(rule)
        if operator not in operators:
            raise RuleConfigurationError(f"Unsupported {value_type} operator: {operator}")
        comparison_source = rule.params.get("comparison_source")
        expected = rule.params.get("expected_value")
        if value_type == "date":
            if comparison_source == "EVALUATION_DATE":
                if expected is not None:
                    raise RuleConfigurationError(
                        "Evaluation-date rules cannot also have expected_value"
                    )
            elif expected is None:
                raise RuleConfigurationError("Date rule requires an expected value")
            else:
                try:
                    date.fromisoformat(str(expected))
                except ValueError as exc:
                    raise RuleConfigurationError("Invalid configured date") from exc
        elif expected is None:
            raise RuleConfigurationError("Numeric rule requires an expected value")
        else:
            try:
                configured_decimal = Decimal(str(expected))
            except InvalidOperation as exc:
                raise RuleConfigurationError("Invalid configured decimal") from exc
            if not configured_decimal.is_finite():
                raise RuleConfigurationError("Configured decimal must be finite")

    def _document_type_param(self, rule: SubmissionRule, key: str) -> DocumentType:
        try:
            return DocumentType(rule.params[key])
        except (KeyError, ValueError) as exc:
            raise RuleConfigurationError(f"Invalid or missing {key}") from exc

    def _operator_param(self, rule: SubmissionRule) -> RuleOperator:
        try:
            return RuleOperator(rule.params["operator"])
        except (KeyError, ValueError) as exc:
            raise RuleConfigurationError("Invalid or missing operator") from exc

    def _field_param(self, rule: SubmissionRule, key: str, document_type: DocumentType) -> str:
        value = rule.params.get(key)
        if not isinstance(value, str) or value not in REVIEWABLE_FIELDS[document_type]:
            raise RuleConfigurationError(f"Unknown {key} for {document_type.value}")
        return value

    def _resolve_documents(
        self,
        requirements: list[RequirementSnapshot],
        documents: list[DocumentSnapshot],
    ) -> tuple[dict[DocumentType, DocumentSnapshot | None], list[RuleEvaluationResult]]:
        selected: dict[DocumentType, DocumentSnapshot | None] = {}
        results: list[RuleEvaluationResult] = []
        for requirement in sorted(requirements, key=lambda item: item.document_type.value):
            typed = [doc for doc in documents if doc.document_type == requirement.document_type]
            if (
                not requirement.required
                and not requirement.rules
                and not requirement.required_fields
            ):
                selected[requirement.document_type] = None
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.NOT_APPLICABLE,
                        document_type=requirement.document_type,
                    )
                )
                continue
            uncertain = [
                doc for doc in typed if doc.classification_needs_review or doc.text_layer_mismatch
            ]
            if uncertain:
                selected[requirement.document_type] = None
                multiple = any(doc.multiple_documents_in_file for doc in uncertain)
                mismatch = any(doc.text_layer_mismatch for doc in uncertain)
                if multiple:
                    code, message = (
                        "MULTIPLE_DOCUMENTS_IN_FILE",
                        "한 파일에 서로 다른 서류가 들어 있어 확인해야 합니다.",
                    )
                elif mismatch:
                    code, message = (
                        "TEXT_LAYER_MISMATCH",
                        "PDF 안의 숨은 글자가 화면에 보이는 내용과 달라 확인해야 합니다.",
                    )
                else:
                    code, message = "CLASSIFICATION_REQUIRES_REVIEW", "서류 유형을 확인해야 합니다."
                issue = VerificationIssue(
                    code,
                    OverallStatus.REVIEW_REQUIRED,
                    message,
                    document_type=requirement.document_type,
                )
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.UNRESOLVED,
                        issue,
                        document_type=requirement.document_type,
                    )
                )
                continue
            completed = [
                doc for doc in typed if doc.processing_status == ProcessingStatus.COMPLETED
            ]
            if len(completed) != len(typed):
                # Do not choose an older completed upload while a competing
                # document of that workflow type is running or has failed.
                completed = []
            unique_checksums = {doc.checksum_sha256 for doc in completed}
            if len(completed) > 1 and len(unique_checksums) > 1:
                issue = VerificationIssue(
                    code="MULTIPLE_DOCUMENTS_REQUIRE_REVIEW",
                    status_effect=OverallStatus.REVIEW_REQUIRED,
                    message="동일 유형의 여러 서류를 확인해야 합니다.",
                    document_type=requirement.document_type,
                )
                selected[requirement.document_type] = None
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.UNRESOLVED,
                        issue,
                        document_type=requirement.document_type,
                    )
                )
                continue
            if completed:
                # Even byte-identical documents can have competing reviewed values.
                signatures = {
                    tuple(
                        sorted(
                            (name, item.normalized_value, str(item.assessment_state))
                            for name, item in doc.fields.items()
                        )
                    )
                    for doc in completed
                }
                if len(signatures) > 1:
                    selected[requirement.document_type] = None
                    issue = VerificationIssue(
                        "DUPLICATE_RESULTS_CONFLICT",
                        OverallStatus.REVIEW_REQUIRED,
                        "중복 서류의 검토 결과가 달라 확인이 필요합니다.",
                        document_type=requirement.document_type,
                    )
                    results.append(
                        RuleEvaluationResult(
                            None,
                            RuleType.DUPLICATE_DOCUMENT,
                            RuleOutcome.UNRESOLVED,
                            issue,
                            document_type=requirement.document_type,
                        )
                    )
                    continue
                chosen = min(completed, key=lambda item: item.created_at)
                selected[requirement.document_type] = chosen
                if len(completed) > 1:
                    results.append(
                        RuleEvaluationResult(
                            None,
                            RuleType.DUPLICATE_DOCUMENT,
                            RuleOutcome.NOTICE,
                            VerificationIssue(
                                "DUPLICATE_UPLOAD_IGNORED",
                                OverallStatus.READY,
                                f"동일한 파일이 {len(completed)}번 업로드되어 한 번만 점검했습니다.",
                                document_id=chosen.id,
                                document_type=requirement.document_type,
                            ),
                            document_id=chosen.id,
                            document_type=requirement.document_type,
                        )
                    )
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.PASS,
                        document_id=chosen.id,
                        document_type=requirement.document_type,
                    )
                )
                continue
            failed = [doc for doc in typed if doc.processing_status == ProcessingStatus.FAILED]
            in_progress = [
                doc
                for doc in typed
                if doc.processing_status
                not in {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED}
            ]
            if failed or in_progress:
                document = sorted(failed or in_progress, key=lambda item: str(item.id))[0]
                code = "DOCUMENT_PROCESSING_FAILED" if failed else "DOCUMENT_PROCESSING_IN_PROGRESS"
                message = (
                    "서류 처리에 실패하여 검토가 필요합니다."
                    if failed
                    else "서류 처리가 완료되지 않았습니다."
                )
                issue = VerificationIssue(
                    code=code,
                    status_effect=OverallStatus.REVIEW_REQUIRED,
                    message=message,
                    document_id=document.id,
                    document_type=requirement.document_type,
                )
                selected[requirement.document_type] = None
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.UNRESOLVED,
                        issue,
                        document_id=document.id,
                        document_type=requirement.document_type,
                    )
                )
                continue
            selected[requirement.document_type] = None
            if requirement.required:
                unknown_present = any(
                    doc.document_type == DocumentType.UNKNOWN for doc in documents
                )
                issue = VerificationIssue(
                    code="UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW"
                    if unknown_present
                    else "MISSING_REQUIRED_DOCUMENT",
                    status_effect=OverallStatus.REVIEW_REQUIRED
                    if unknown_present
                    else OverallStatus.NEEDS_CORRECTION,
                    message="미분류 서류가 있어 필수서류 여부를 확인해야 합니다."
                    if unknown_present
                    else "필수서류가 누락되었습니다.",
                    document_type=requirement.document_type,
                )
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.UNRESOLVED if unknown_present else RuleOutcome.FAIL,
                        issue,
                        document_type=requirement.document_type,
                    )
                )
            else:
                results.append(
                    RuleEvaluationResult(
                        None,
                        RuleType.REQUIRED_DOCUMENT,
                        RuleOutcome.NOT_APPLICABLE,
                        document_type=requirement.document_type,
                    )
                )
        return selected, results

    def _document_conditions(
        self,
        document: DocumentSnapshot,
        requirement: RequirementSnapshot,
        context: VerificationContext,
    ) -> list[RuleEvaluationResult]:
        """Re-evaluate applicable conditions using effective evidence, not stale machine issues."""
        results: list[RuleEvaluationResult] = []
        for name, expected, rule_type, code in (
            (
                "student_name"
                if document.document_type
                in {DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT}
                else "applicant_name",
                context.applicant_name,
                RuleType.APPLICANT_NAME_MATCH,
                "APPLICANT_NAME_MISMATCH",
            ),
            (
                "workplace_name"
                if document.document_type == DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
                else "company_name",
                context.company_name,
                RuleType.COMPANY_NAME_MATCH,
                "COMPANY_NAME_MISMATCH",
            ),
        ):
            if not expected or name not in EXPECTED_FIELDS[document.document_type]:
                continue
            rule = SubmissionRule(requirement.id, rule_type, Severity.ERROR, {})
            snapshot = document.fields.get(name)
            unresolved = self._unresolved_field(rule, document, snapshot, name)
            if unresolved:
                results.append(unresolved)
            elif (
                snapshot
                and snapshot.normalized_value is not None
                and not _same_name(snapshot.normalized_value, expected, rule_type)
            ):
                issue = VerificationIssue(
                    code,
                    OverallStatus.NEEDS_CORRECTION,
                    "제출자 정보와 일치하지 않습니다.",
                    document.id,
                    document.document_type,
                    name,
                )
                results.append(
                    RuleEvaluationResult(
                        requirement.id,
                        rule_type,
                        RuleOutcome.FAIL,
                        issue,
                        document.id,
                        document.document_type,
                        name,
                    )
                )
        if (
            requirement.required
            and "valid_until" in requirement.required_fields
            and not any(
                rule.rule_type == RuleType.DATE_COMPARISON
                and rule.params.get("field") == "valid_until"
                for rule in requirement.rules
            )
        ):
            results.append(
                self._date_comparison(
                    SubmissionRule(
                        requirement.id,
                        RuleType.DATE_COMPARISON,
                        Severity.ERROR,
                        {
                            "document_type": document.document_type.value,
                            "field": "valid_until",
                            "operator": "ON_OR_AFTER",
                            "comparison_source": "EVALUATION_DATE",
                        },
                    ),
                    {document.document_type: document},
                    context,
                )
            )
        return results

    def _evaluate_rule(
        self,
        rule: SubmissionRule,
        selected: dict[DocumentType, DocumentSnapshot | None],
        context: VerificationContext,
    ) -> RuleEvaluationResult:
        if rule.rule_type == RuleType.FIELD_COMPARISON:
            return self._field_comparison(rule, selected)
        if rule.rule_type == RuleType.DATE_COMPARISON:
            return self._date_comparison(rule, selected, context)
        if rule.rule_type == RuleType.NUMERIC_COMPARISON:
            return self._numeric_comparison(rule, selected)
        if rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE:
            lower = context.evaluation_date - timedelta(days=rule.params.get("max_age_days", 90))
            for operator, expected in (
                ("ON_OR_AFTER", lower),
                ("ON_OR_BEFORE", context.evaluation_date),
            ):
                bound = SubmissionRule(
                    rule.id,
                    rule.rule_type,
                    rule.severity,
                    {**rule.params, "operator": operator, "expected_value": expected.isoformat()},
                )
                result = self._date_comparison(bound, selected, context)
                if result.outcome != RuleOutcome.PASS:
                    return result
            return result
        raise RuleConfigurationError(f"Unsupported submission rule type: {rule.rule_type}")

    def _field_comparison(
        self,
        rule: SubmissionRule,
        selected: dict[DocumentType, DocumentSnapshot | None],
    ) -> RuleEvaluationResult:
        source_type = DocumentType(rule.params["source_document_type"])
        target_type = DocumentType(rule.params["target_document_type"])
        source_name = str(rule.params["source_field"])
        target_name = str(rule.params["target_field"])
        source = selected.get(source_type)
        target = selected.get(target_type)
        if source is None or target is None:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.NOT_APPLICABLE,
                document_type=source_type,
                field_name=source_name,
                related_document_type=target_type,
                related_field_name=target_name,
            )
        source_field = source.fields.get(source_name)
        target_field = target.fields.get(target_name)
        unresolved = self._unresolved_field(
            rule,
            source,
            source_field,
            source_name,
            related=target,
            related_field_name=target_name,
        ) or self._unresolved_field(
            rule,
            target,
            target_field,
            target_name,
            related=source,
            related_field_name=source_name,
        )
        if unresolved:
            return unresolved
        assert source_field is not None and source_field.normalized_value is not None
        assert target_field is not None and target_field.normalized_value is not None
        value_type = str(rule.params.get("value_type", "string"))
        source_value, target_value = source_field.normalized_value, target_field.normalized_value
        if source_name in _COMPANY_NAME_FIELDS or target_name in _COMPANY_NAME_FIELDS:
            source_value = strip_legal_entity_markers(source_value)
            target_value = strip_legal_entity_markers(target_value)
        passed = _comparison_key(source_value, value_type) == _comparison_key(
            target_value, value_type
        )
        if passed:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.PASS,
                document_id=source.id,
                document_type=source_type,
                field_name=source_name,
                related_document_id=target.id,
                related_document_type=target_type,
                related_field_name=target_name,
            )
        issue = VerificationIssue(
            code="INFORMATION_MISMATCH",
            status_effect=_status_for_severity(rule.severity),
            message="기준 서류와 정보가 일치하지 않습니다.",
            document_id=source.id,
            document_type=source_type,
            field_name=source_name,
            related_document_id=target.id,
            related_document_type=target_type,
            related_field_name=target_name,
            rule_id=rule.id,
            field_id=source_field.id,
            related_field_id=target_field.id,
        )
        return RuleEvaluationResult(
            rule.id,
            rule.rule_type,
            RuleOutcome.FAIL,
            issue,
            source.id,
            source_type,
            source_name,
            target.id,
            target_type,
            target_name,
        )

    def _date_comparison(
        self,
        rule: SubmissionRule,
        selected: dict[DocumentType, DocumentSnapshot | None],
        context: VerificationContext,
    ) -> RuleEvaluationResult:
        document_type = DocumentType(rule.params["document_type"])
        field_name = str(rule.params["field"])
        document = selected.get(document_type)
        if document is None:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.NOT_APPLICABLE,
                document_type=document_type,
                field_name=field_name,
            )
        snapshot = document.fields.get(field_name)
        unresolved = self._unresolved_field(rule, document, snapshot, field_name)
        if unresolved:
            return unresolved
        assert snapshot is not None and snapshot.normalized_value is not None
        try:
            actual = date.fromisoformat(snapshot.normalized_value)
        except ValueError:
            unresolved = self._unresolved_field(rule, document, None, field_name, snapshot.id)
            assert unresolved is not None
            return unresolved
        expected = (
            context.evaluation_date
            if rule.params.get("comparison_source") == "EVALUATION_DATE"
            else date.fromisoformat(str(rule.params["expected_value"]))
        )
        operator = RuleOperator(rule.params["operator"])
        passed = actual <= expected if operator == RuleOperator.ON_OR_BEFORE else actual >= expected
        if passed:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.PASS,
                document_id=document.id,
                document_type=document_type,
                field_name=field_name,
            )
        is_expired = (
            field_name == "valid_until"
            and operator == RuleOperator.ON_OR_AFTER
            and rule.params.get("comparison_source") == "EVALUATION_DATE"
        )
        issue = VerificationIssue(
            code="EXPIRED_DOCUMENT" if is_expired else "RULE_CONDITION_NOT_MET",
            status_effect=_status_for_severity(rule.severity),
            message=(
                "서류의 유효기간이 만료되었습니다."
                if is_expired
                else "설정된 날짜 조건을 충족하지 않습니다."
            ),
            document_id=document.id,
            document_type=document_type,
            field_name=field_name,
            rule_id=rule.id,
            field_id=snapshot.id,
        )
        return RuleEvaluationResult(
            rule.id,
            rule.rule_type,
            RuleOutcome.FAIL,
            issue,
            document.id,
            document_type,
            field_name,
        )

    def _numeric_comparison(
        self,
        rule: SubmissionRule,
        selected: dict[DocumentType, DocumentSnapshot | None],
    ) -> RuleEvaluationResult:
        document_type = DocumentType(rule.params["document_type"])
        field_name = str(rule.params["field"])
        document = selected.get(document_type)
        if document is None:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.NOT_APPLICABLE,
                document_type=document_type,
                field_name=field_name,
            )
        snapshot = document.fields.get(field_name)
        unresolved = self._unresolved_field(rule, document, snapshot, field_name)
        if unresolved:
            return unresolved
        assert snapshot is not None and snapshot.normalized_value is not None
        try:
            actual = Decimal(snapshot.normalized_value)
            expected = Decimal(str(rule.params["expected_value"]))
            if not actual.is_finite() or not expected.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            unresolved = self._unresolved_field(rule, document, None, field_name, snapshot.id)
            assert unresolved is not None
            return unresolved
        operator = RuleOperator(rule.params["operator"])
        if operator == RuleOperator.GREATER_THAN_OR_EQUAL:
            passed = actual >= expected
        elif operator == RuleOperator.LESS_THAN_OR_EQUAL:
            passed = actual <= expected
        else:
            passed = actual == expected
        if passed:
            return RuleEvaluationResult(
                rule.id,
                rule.rule_type,
                RuleOutcome.PASS,
                document_id=document.id,
                document_type=document_type,
                field_name=field_name,
            )
        issue = VerificationIssue(
            code="RULE_CONDITION_NOT_MET",
            status_effect=_status_for_severity(rule.severity),
            message="설정된 수치 조건을 충족하지 않습니다.",
            document_id=document.id,
            document_type=document_type,
            field_name=field_name,
            rule_id=rule.id,
            field_id=snapshot.id,
        )
        return RuleEvaluationResult(
            rule.id,
            rule.rule_type,
            RuleOutcome.FAIL,
            issue,
            document.id,
            document_type,
            field_name,
        )

    def _unresolved_field(
        self,
        rule: SubmissionRule,
        document: DocumentSnapshot,
        snapshot: FieldSnapshot | None,
        field_name: str,
        field_id: uuid.UUID | None = None,
        *,
        related: DocumentSnapshot | None = None,
        related_field_name: str | None = None,
    ) -> RuleEvaluationResult | None:
        if (
            snapshot is not None
            and snapshot.normalized_value is not None
            and (
                snapshot.assessment_state == EvidenceAssessmentState.SUFFICIENT
                or (
                    snapshot.assessment_state is None
                    and not snapshot.needs_review
                    and snapshot.evidence_available
                )
            )
        ):
            return None
        checksum_failed = (
            snapshot is not None
            and snapshot.extraction_method == BRN_CHECKSUM_FAILED_METHOD
            and snapshot.effective_source
            not in (EffectiveValueSource.HUMAN_CONFIRMED, EffectiveValueSource.HUMAN_CORRECTED)
        )
        issue = VerificationIssue(
            code=(
                "BUSINESS_NUMBER_CHECKSUM_FAILED"
                if checksum_failed
                else "OCR_UNCERTAIN"
                if snapshot is not None
                and (
                    snapshot.assessment_state == EvidenceAssessmentState.REVIEW_REQUIRED
                    or (snapshot.assessment_state is None and snapshot.needs_review)
                )
                else "REQUIRED_FIELD_UNRESOLVED"
            ),
            status_effect=OverallStatus.REVIEW_REQUIRED,
            message="일부 정보를 확인할 수 없어 검토가 필요합니다.",
            document_id=document.id,
            document_type=document.document_type,
            field_name=field_name,
            related_document_id=related.id if related else None,
            related_document_type=related.document_type if related else None,
            related_field_name=related_field_name,
            rule_id=rule.id,
            field_id=snapshot.id if snapshot else field_id,
        )
        return RuleEvaluationResult(
            rule.id,
            rule.rule_type,
            RuleOutcome.UNRESOLVED,
            issue,
            document.id,
            document.document_type,
            field_name,
            related.id if related else None,
            related.document_type if related else None,
            related_field_name,
        )
