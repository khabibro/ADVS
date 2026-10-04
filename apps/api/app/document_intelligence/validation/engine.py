import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.core.domain import EXPECTED_FIELDS, DocumentType, OverallStatus, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.normalization.field_normalizer import strip_legal_entity_markers

VALIDATION_ENGINE_VERSION = "heuristic-v2"


@dataclass
class ValidationIssue:
    rule_type: RuleType
    passed: bool
    severity: Severity
    expected_value: str | None
    actual_value: str | None
    message: str
    code: str


@dataclass
class ConfiguredRule:
    """A DB-backed `ValidationRule` row, decoupled from SQLAlchemy so the
    engine stays independently testable. The engine knows *how* each
    rule_type works; the database decides *whether* and *with what
    parameters* it applies to a given document type."""

    rule_type: RuleType
    severity: Severity
    params: dict


def _explicit_required_fields(
    configured_rules: list[ConfiguredRule] | None, document_type: DocumentType
) -> set[str]:
    """Fields a configured REQUIRED_FIELD rule names explicitly.

    A rule with no `field` param names every field in this document type's
    own schema (mirrors `_handle_required_field`'s own default-target
    resolution, so a blanket rule and an explicit per-field rule agree on
    what "every field" means).

    Only REQUIRED_FIELD redefines "required". DATE_NOT_EXPIRED,
    ISSUE_DATE_MAX_AGE and the rest constrain values that were read; a
    checklist made only of those has expressed no opinion about missing
    fields, so it must not silence the missing-field net (R2-02).
    """
    names: set[str] = set()
    for rule in configured_rules or []:
        if rule.rule_type != RuleType.REQUIRED_FIELD:
            continue
        field_name = rule.params.get("field")
        names.update([field_name] if field_name else EXPECTED_FIELDS[document_type])
    return names


def comparable(value: str | None) -> str:
    return re.sub(r"[\s\W_]+", "", (value or "").lower())


def comparable_company_name(value: str | None) -> str:
    """Like `comparable`, but a leading/trailing legal-entity marker
    (주식회사 / (주) / ㈜ / ... -- audit F-002) is stripped first, so the
    same company written with a different one of these compares equal.
    Scoped to company_name/workplace_name comparisons only; business
    numbers and every other field keep using plain `comparable`."""
    return comparable(strip_legal_entity_markers(value))


class ValidationEngine:
    """Deterministic rules over policy-gated fields; uncertainty is not failure."""

    engine_version = VALIDATION_ENGINE_VERSION

    def validate_document(
        self,
        expected_type: DocumentType | None,
        actual_type: DocumentType,
        fields: list[ExtractedValue],
        applicant_name: str | None = None,
        company_name: str | None = None,
        duplicate: bool = False,
        configured_rules: list[ConfiguredRule] | None = None,
        reference_date: date | None = None,
    ) -> list[ValidationIssue]:
        """`reference_date` is the submission's own date (Asia/Seoul),
        never the server clock (audit: validity/issue-date-age was measured
        against `date.today()`, so re-checking the same submission on a
        later day could flip the result). `None` means genuinely unknown --
        every date-dependent check below returns REVIEW_REQUIRED rather
        than guessing, never a comparison against the server's local date."""
        by_name = {field.field_name: field for field in fields}
        issues: list[ValidationIssue] = []
        if expected_type and actual_type != expected_type:
            issues.append(
                ValidationIssue(
                    RuleType.EXPECTED_DOCUMENT_TYPE,
                    False,
                    Severity.ERROR,
                    expected_type,
                    actual_type,
                    "문서 유형이 요구사항과 다릅니다.",
                    "WRONG_DOCUMENT_TYPE",
                )
            )
        if duplicate:
            issues.append(
                ValidationIssue(
                    RuleType.DUPLICATE_DOCUMENT,
                    False,
                    Severity.WARNING,
                    None,
                    None,
                    "동일한 파일이 이미 업로드되었습니다.",
                    "DUPLICATE_UPLOAD",
                )
            )
        if applicant_name and by_name.get("applicant_name"):
            actual = self._supported_value(by_name.get("applicant_name"))
            passed = comparable(applicant_name) == comparable(actual)
            issues.append(
                ValidationIssue(
                    RuleType.APPLICANT_NAME_MATCH,
                    passed,
                    Severity.ERROR if actual is not None else Severity.WARNING,
                    applicant_name,
                    actual,
                    "신청인 이름 일치 여부",
                    "REQUIRED_FIELD_UNRESOLVED"
                    if actual is None
                    else "APPLICANT_NAME_MISMATCH"
                    if not passed
                    else "APPLICANT_NAME_MATCH",
                )
            )
        if company_name and by_name.get("company_name"):
            actual = self._supported_value(by_name.get("company_name"))
            passed = comparable_company_name(company_name) == comparable_company_name(actual)
            issues.append(
                ValidationIssue(
                    RuleType.COMPANY_NAME_MATCH,
                    passed,
                    Severity.ERROR if actual is not None else Severity.WARNING,
                    company_name,
                    actual,
                    "회사명 일치 여부",
                    "REQUIRED_FIELD_UNRESOLVED"
                    if actual is None
                    else "COMPANY_NAME_MISMATCH"
                    if not passed
                    else "COMPANY_NAME_MATCH",
                )
            )

        issues.extend(self._always_on_expiration_issues(by_name, configured_rules, reference_date))

        # A checklist that says nothing about required fields must not switch
        # the "this field could not be read" net off. Previously *any*
        # configured rule replaced the net, so a checklist built only from
        # rules this engine cannot execute at document scope -- DATE_COMPARISON
        # and NUMERIC_COMPARISON are submission-scope types -- produced zero
        # issues, and a document with every field unresolved was reported
        # READY (R2-02).
        #
        # And a checklist that DOES express a REQUIRED_FIELD opinion must not
        # have that opinion silently replace the net for every field it
        # doesn't name (audit F-001): one REQUIRED_FIELD(company_name) rule
        # used to disable the check for every other field of the document,
        # including a missing valid_until with no other protection. An
        # explicit rule now only ever *adds* to what's required -- the
        # fields it names are checked below with their own configured
        # severity; every other field in this document type's own schema
        # stays covered by the default net, narrowed to that schema (not
        # every extracted field) so optional fields still don't silently
        # become required just because the checklist has *an* opinion.
        explicit_required = _explicit_required_fields(configured_rules, actual_type)
        if explicit_required:
            issues.extend(
                self._default_required_field_issues(
                    by_name, restrict_to=set(EXPECTED_FIELDS[actual_type]) - explicit_required
                )
            )
        else:
            issues.extend(self._default_required_field_issues(by_name))
        if configured_rules is not None:
            for rule in configured_rules:
                issues.extend(
                    self._apply_configured_rule(rule, by_name, actual_type, reference_date)
                )
        return issues

    def _always_on_expiration_issues(
        self,
        by_name: dict[str, ExtractedValue],
        configured_rules: list[ConfiguredRule] | None,
        reference_date: date | None,
    ) -> list[ValidationIssue]:
        """An expired document is invalid regardless of whether an admin
        remembered to configure a checklist rule for it -- unlike
        REQUIRED_FIELD/CUSTOM_TEXT_RULE/etc, this one check is unconditional
        whenever the document carries a `valid_until`. A DB-configured
        DATE_NOT_EXPIRED rule for the same field takes over instead of
        duplicating it."""
        field = by_name.get("valid_until")
        if self._supported_value(field) is None:
            return []
        already_configured = any(
            rule.rule_type == RuleType.DATE_NOT_EXPIRED
            and rule.params.get("field", "valid_until") == "valid_until"
            for rule in (configured_rules or [])
        )
        if already_configured:
            return []
        assert field is not None and field.normalized_value is not None
        if reference_date is None:
            return [
                ValidationIssue(
                    RuleType.DATE_NOT_EXPIRED,
                    False,
                    Severity.WARNING,
                    "not expired",
                    field.normalized_value,
                    "제출일을 확인할 수 없어 유효기간을 판단할 수 없습니다.",
                    "REFERENCE_DATE_UNAVAILABLE",
                )
            ]
        passed = date.fromisoformat(field.normalized_value) >= reference_date
        return [
            ValidationIssue(
                RuleType.DATE_NOT_EXPIRED,
                passed,
                Severity.ERROR,
                "not expired",
                field.normalized_value,
                "유효기간 만료 여부",
                "EXPIRED_DOCUMENT" if not passed else "NOT_EXPIRED",
            )
        ]

    def validate_required_documents(
        self, required_types: list[DocumentType], present_types: set[DocumentType]
    ) -> list[ValidationIssue]:
        """Submission-level check: is each required document type present
        at all? (Per-document validation cannot answer this on its own.)"""
        return [
            ValidationIssue(
                RuleType.REQUIRED_DOCUMENT,
                False,
                Severity.ERROR,
                str(doc_type),
                None,
                f"{doc_type} 문서가 필요합니다.",
                "MISSING_REQUIRED_DOCUMENT",
            )
            for doc_type in required_types
            if doc_type not in present_types
        ]

    def overall_status(self, issues: list[ValidationIssue]) -> OverallStatus:
        failed = [i for i in issues if not i.passed]
        if any(i.severity == Severity.ERROR for i in failed):
            return OverallStatus.NEEDS_CORRECTION
        if any(i.severity == Severity.WARNING for i in failed):
            return OverallStatus.REVIEW_REQUIRED
        return OverallStatus.READY

    def _default_required_field_issues(
        self, by_name: dict[str, ExtractedValue], restrict_to: set[str] | None = None
    ) -> list[ValidationIssue]:
        names = (
            by_name.items() if restrict_to is None else ((n, by_name.get(n)) for n in restrict_to)
        )
        return [
            ValidationIssue(
                RuleType.REQUIRED_FIELD,
                False,
                Severity.WARNING,
                name,
                None,
                f"{name} 필드를 확인해야 합니다.",
                "MISSING_REQUIRED_FIELD",
            )
            for name, field in names
            if self._supported_value(field) is None
        ]

    def _apply_configured_rule(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        document_type: DocumentType,
        reference_date: date | None,
    ) -> list[ValidationIssue]:
        if rule.rule_type == RuleType.REQUIRED_FIELD:
            return self._handle_required_field(rule, by_name, EXPECTED_FIELDS[document_type])
        handler = _RULE_HANDLERS.get(rule.rule_type)
        return handler(self, rule, by_name, reference_date) if handler else []

    def _handle_required_field(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        default_fields: list[str] | None = None,
        reference_date: date | None = None,
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field")
        targets = [field_name] if field_name else (default_fields or list(by_name.keys()))
        issues = []
        for name in targets:
            field = by_name.get(name)
            if self._supported_value(field) is None:
                # Always WARNING, never the rule's own configured severity:
                # a *missing* value is a review signal, not a deterministic
                # failure, no matter how an admin configured this rule --
                # see test_missing_or_uncertain_value_never_becomes_deterministic_failure.
                # "An explicit rule may change severity... for the field it
                # names" (B-1) refers to other rule types (DATE_NOT_EXPIRED,
                # ISSUE_DATE_MAX_AGE, ...) that already honor configured
                # severity for a value that *was* read; REQUIRED_FIELD's own
                # missing-value severity stays fixed.
                issues.append(
                    ValidationIssue(
                        RuleType.REQUIRED_FIELD,
                        False,
                        Severity.WARNING,
                        name,
                        None,
                        f"{name} 필드를 확인해야 합니다.",
                        "MISSING_REQUIRED_FIELD",
                    )
                )
        return issues

    def _handle_date_not_expired(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        reference_date: date | None,
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "valid_until")
        field = by_name.get(field_name)
        value = self._supported_value(field)
        if value is None:
            return [
                ValidationIssue(
                    RuleType.DATE_NOT_EXPIRED,
                    False,
                    Severity.WARNING,
                    "not expired",
                    None,
                    f"{field_name} 값을 확인할 수 없습니다.",
                    "MISSING_EXPIRATION_DATE",
                )
            ]
        if reference_date is None:
            return [
                ValidationIssue(
                    RuleType.DATE_NOT_EXPIRED,
                    False,
                    Severity.WARNING,
                    "not expired",
                    value,
                    "제출일을 확인할 수 없어 유효기간을 판단할 수 없습니다.",
                    "REFERENCE_DATE_UNAVAILABLE",
                )
            ]
        passed = date.fromisoformat(value) >= reference_date
        return [
            ValidationIssue(
                RuleType.DATE_NOT_EXPIRED,
                passed,
                rule.severity,
                "not expired",
                value,
                "유효기간 만료 여부",
                "EXPIRED_DOCUMENT" if not passed else "NOT_EXPIRED",
            )
        ]

    def _handle_issue_date_max_age(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        reference_date: date | None,
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "issue_date")
        max_age_days = int(rule.params.get("max_age_days", 90))
        field = by_name.get(field_name)
        value = self._supported_value(field)
        if value is None:
            return [
                ValidationIssue(
                    RuleType.ISSUE_DATE_MAX_AGE,
                    False,
                    Severity.WARNING,
                    f"<= {max_age_days}d",
                    None,
                    f"{field_name} 값을 확인할 수 없습니다.",
                    "MISSING_ISSUE_DATE",
                )
            ]
        if reference_date is None:
            return [
                ValidationIssue(
                    RuleType.ISSUE_DATE_MAX_AGE,
                    False,
                    Severity.WARNING,
                    f"<= {max_age_days}d",
                    value,
                    "제출일을 확인할 수 없어 경과 기간을 판단할 수 없습니다.",
                    "REFERENCE_DATE_UNAVAILABLE",
                )
            ]
        age_days = (reference_date - date.fromisoformat(value)).days
        passed = 0 <= age_days <= max_age_days
        return [
            ValidationIssue(
                RuleType.ISSUE_DATE_MAX_AGE,
                passed,
                rule.severity,
                f"<= {max_age_days}d",
                value,
                "발급일자 경과 기간 확인",
                "ISSUE_DATE_TOO_OLD" if not passed else "ISSUE_DATE_VALID",
            )
        ]

    def _handle_custom_text_rule(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        reference_date: date | None = None,
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field")
        field = by_name.get(field_name) if field_name else None
        actual = self._supported_value(field)
        expected = rule.params.get("equals") or rule.params.get("contains")
        if not expected or actual is None:
            return [
                ValidationIssue(
                    RuleType.CUSTOM_TEXT_RULE,
                    False,
                    Severity.WARNING,
                    expected,
                    actual,
                    "사용자 정의 규칙을 확인해야 합니다.",
                    "CUSTOM_RULE_REVIEW",
                )
            ]
        passed = (
            comparable(actual) == comparable(expected)
            if "equals" in rule.params
            else comparable(expected) in comparable(actual)
        )
        return [
            ValidationIssue(
                RuleType.CUSTOM_TEXT_RULE,
                passed,
                rule.severity,
                expected,
                actual,
                "사용자 정의 규칙 확인",
                "CUSTOM_RULE_FAILED" if not passed else "CUSTOM_RULE_PASSED",
            )
        ]

    def _handle_business_number_match(
        self,
        rule: ConfiguredRule,
        by_name: dict[str, ExtractedValue],
        reference_date: date | None = None,
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "business_registration_number")
        expected = rule.params.get("expected_value")
        field = by_name.get(field_name)
        actual = self._supported_value(field)
        if not expected:
            # Not enough configuration to compare against -- skip rather
            # than guess at a match.
            return []
        if actual is None:
            return [
                ValidationIssue(
                    rule.rule_type,
                    False,
                    Severity.WARNING,
                    None,
                    None,
                    "비교할 값을 확인해야 합니다.",
                    "REQUIRED_FIELD_UNRESOLVED",
                )
            ]
        passed = comparable(actual) == comparable(expected)
        return [
            ValidationIssue(
                RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH,
                passed,
                rule.severity,
                expected,
                actual,
                "사업자등록번호 일치 여부",
                "BUSINESS_NUMBER_MISMATCH" if not passed else "BUSINESS_NUMBER_MATCH",
            )
        ]

    @staticmethod
    def _supported_value(field: ExtractedValue | None) -> str | None:
        if field is None or field.needs_review or field.normalized_value is None:
            return None
        value = field.normalized_value
        if field.field_name.endswith("_date") or field.field_name in {"valid_from", "valid_until"}:
            try:
                date.fromisoformat(value)
            except ValueError:
                return None
        return value


_RULE_HANDLERS: dict[RuleType, Callable[..., list[ValidationIssue]]] = {
    RuleType.REQUIRED_FIELD: ValidationEngine._handle_required_field,
    RuleType.DATE_NOT_EXPIRED: ValidationEngine._handle_date_not_expired,
    RuleType.ISSUE_DATE_MAX_AGE: ValidationEngine._handle_issue_date_max_age,
    RuleType.CUSTOM_TEXT_RULE: ValidationEngine._handle_custom_text_rule,
    RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH: ValidationEngine._handle_business_number_match,
}
