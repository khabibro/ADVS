import re
from dataclasses import dataclass
from datetime import date

from app.core.domain import DocumentType, OverallStatus, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue

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


def comparable(value: str | None) -> str:
    return re.sub(r"[\s\W_]+", "", (value or "").lower())


class ValidationEngine:
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
    ) -> list[ValidationIssue]:
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
            actual = by_name["applicant_name"].normalized_value
            passed = comparable(applicant_name) == comparable(actual)
            issues.append(
                ValidationIssue(
                    RuleType.APPLICANT_NAME_MATCH,
                    passed,
                    Severity.ERROR,
                    applicant_name,
                    actual,
                    "신청인 이름 일치 여부",
                    "APPLICANT_NAME_MISMATCH" if not passed else "APPLICANT_NAME_MATCH",
                )
            )
        if company_name and by_name.get("company_name"):
            actual = by_name["company_name"].normalized_value
            passed = comparable(company_name) == comparable(actual)
            issues.append(
                ValidationIssue(
                    RuleType.COMPANY_NAME_MATCH,
                    passed,
                    Severity.ERROR,
                    company_name,
                    actual,
                    "회사명 일치 여부",
                    "COMPANY_NAME_MISMATCH" if not passed else "COMPANY_NAME_MATCH",
                )
            )

        issues.extend(self._always_on_expiration_issues(by_name, configured_rules))

        if configured_rules is None:
            # No checklist/requirement matched this document: fall back to
            # the MVP default of flagging every uncertain/missing field.
            issues.extend(self._default_required_field_issues(by_name))
        else:
            for rule in configured_rules:
                issues.extend(self._apply_configured_rule(rule, by_name))
        return issues

    def _always_on_expiration_issues(
        self,
        by_name: dict[str, ExtractedValue],
        configured_rules: list[ConfiguredRule] | None,
    ) -> list[ValidationIssue]:
        """An expired document is invalid regardless of whether an admin
        remembered to configure a checklist rule for it -- unlike
        REQUIRED_FIELD/CUSTOM_TEXT_RULE/etc, this one check is unconditional
        whenever the document carries an `expiration_date`. A DB-configured
        DATE_NOT_EXPIRED rule for the same field takes over instead of
        duplicating it."""
        field = by_name.get("expiration_date")
        if field is None or field.normalized_value is None:
            return []
        already_configured = any(
            rule.rule_type == RuleType.DATE_NOT_EXPIRED
            and rule.params.get("field", "expiration_date") == "expiration_date"
            for rule in (configured_rules or [])
        )
        if already_configured:
            return []
        passed = date.fromisoformat(field.normalized_value) >= date.today()
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
        self, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
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
            for name, field in by_name.items()
            if field.needs_review and field.normalized_value is None
        ]

    def _apply_configured_rule(
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        handler = _RULE_HANDLERS.get(rule.rule_type)
        return handler(self, rule, by_name) if handler else []

    def _handle_required_field(
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field")
        targets = [field_name] if field_name else list(by_name.keys())
        issues = []
        for name in targets:
            field = by_name.get(name)
            if field is None or (field.needs_review and field.normalized_value is None):
                issues.append(
                    ValidationIssue(
                        RuleType.REQUIRED_FIELD,
                        False,
                        rule.severity,
                        name,
                        None,
                        f"{name} 필드를 확인해야 합니다.",
                        "MISSING_REQUIRED_FIELD",
                    )
                )
        return issues

    def _handle_date_not_expired(
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "expiration_date")
        field = by_name.get(field_name)
        value = field.normalized_value if field else None
        if value is None:
            return [
                ValidationIssue(
                    RuleType.DATE_NOT_EXPIRED,
                    False,
                    rule.severity,
                    "not expired",
                    None,
                    f"{field_name} 값을 확인할 수 없습니다.",
                    "MISSING_EXPIRATION_DATE",
                )
            ]
        passed = date.fromisoformat(value) >= date.today()
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
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "issue_date")
        max_age_days = int(rule.params.get("max_age_days", 90))
        field = by_name.get(field_name)
        value = field.normalized_value if field else None
        if value is None:
            return [
                ValidationIssue(
                    RuleType.ISSUE_DATE_MAX_AGE,
                    False,
                    rule.severity,
                    f"<= {max_age_days}d",
                    None,
                    f"{field_name} 값을 확인할 수 없습니다.",
                    "MISSING_ISSUE_DATE",
                )
            ]
        age_days = (date.today() - date.fromisoformat(value)).days
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
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field")
        field = by_name.get(field_name) if field_name else None
        actual = field.normalized_value if field else None
        expected = rule.params.get("equals") or rule.params.get("contains")
        if not expected or actual is None:
            return [
                ValidationIssue(
                    RuleType.CUSTOM_TEXT_RULE,
                    False,
                    rule.severity,
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
        self, rule: ConfiguredRule, by_name: dict[str, ExtractedValue]
    ) -> list[ValidationIssue]:
        field_name = rule.params.get("field", "business_registration_number")
        expected = rule.params.get("expected_value")
        field = by_name.get(field_name)
        actual = field.normalized_value if field else None
        if not expected:
            # Not enough configuration to compare against -- skip rather
            # than guess at a match.
            return []
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


_RULE_HANDLERS = {
    RuleType.REQUIRED_FIELD: ValidationEngine._handle_required_field,
    RuleType.DATE_NOT_EXPIRED: ValidationEngine._handle_date_not_expired,
    RuleType.ISSUE_DATE_MAX_AGE: ValidationEngine._handle_issue_date_max_age,
    RuleType.CUSTOM_TEXT_RULE: ValidationEngine._handle_custom_text_rule,
    RuleType.BUSINESS_REGISTRATION_NUMBER_MATCH: ValidationEngine._handle_business_number_match,
}
