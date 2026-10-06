from collections.abc import Iterable
from typing import Any

from app.core.domain import DocumentType, RuleOperator, RuleType, Severity
from app.db.session import Base, SessionLocal, engine
from app.models.entities import (
    Checklist,
    DocumentRequirement,
    Project,
    Submission,
    User,
    ValidationRule,
)
from app.services.verification import invalidate_submission_verification

BUSINESS_WORKFLOW = "기업 제출서류 점검"
STUDENT_WORKFLOW = "학생 제출서류 점검"
LEGACY_DEMO_WORKFLOWS = (
    "Demo four-document checklist",
    "기업 제출서류 점검 (Phase 1 데모)",
)


def upsert_workflow(
    db,
    name: str,
    description: str,
    requirements: Iterable[
        tuple[DocumentType, bool, list[tuple[RuleType, Severity, dict[str, Any]]]]
    ],
) -> Checklist:
    workflow = db.query(Checklist).filter_by(name=name).one_or_none()
    if workflow is None:
        workflow = Checklist(name=name, description=description, is_active=True)
        db.add(workflow)
        db.flush()
    else:
        workflow.description = description
        workflow.is_active = True
        project_ids = [
            row[0] for row in db.query(Project.id).filter(Project.checklist_id == workflow.id).all()
        ]
        for project_id in sorted(project_ids, key=str):
            invalidate_submission_verification(db, project_id)

    workflow.requirements.clear()
    db.flush()
    for document_type, required, rules in requirements:
        requirement = DocumentRequirement(document_type=document_type.value, required=required)
        requirement.rules.extend(
            ValidationRule(rule_type=rule_type.value, severity=severity.value, params=params)
            for rule_type, severity, params in rules
        )
        workflow.requirements.append(requirement)
    return workflow


def comparison_rule(
    target_type: DocumentType,
    source_field: str,
    target_field: str,
    *,
    value_type: str = "string",
) -> tuple[RuleType, Severity, dict[str, Any]]:
    return (
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
            "source_field": source_field,
            "target_document_type": target_type.value,
            "target_field": target_field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": value_type,
        },
    )


def student_identity_rule(
    field: str, *, value_type: str = "string"
) -> tuple[RuleType, Severity, dict[str, Any]]:
    """The 재학증명서 and 성적증명서 must name the same student (Phase D2)."""
    return (
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
            "source_field": field,
            "target_document_type": DocumentType.TRANSCRIPT.value,
            "target_field": field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": value_type,
        },
    )


def validity_rule(
    document_type: DocumentType,
) -> tuple[RuleType, Severity, dict[str, Any]]:
    return (
        RuleType.DATE_COMPARISON,
        Severity.ERROR,
        {
            "document_type": document_type.value,
            "field": "valid_until",
            "operator": RuleOperator.ON_OR_AFTER.value,
            "comparison_source": "EVALUATION_DATE",
        },
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="demo@advs.local").one_or_none()
        if user is None:
            user = User(email="demo@advs.local", display_name="Demo User")
            db.add(user)
            db.flush()

        business = upsert_workflow(
            db,
            BUSINESS_WORKFLOW,
            "기업 제출에 필요한 문서 종류를 확인하는 사전 점검 업무입니다.",
            [
                (DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, []),
                (
                    DocumentType.SME_CONFIRMATION_CERTIFICATE,
                    True,
                    [
                        comparison_rule(
                            DocumentType.SME_CONFIRMATION_CERTIFICATE,
                            "business_registration_number",
                            "business_registration_number",
                            value_type="identifier",
                        ),
                        comparison_rule(
                            DocumentType.SME_CONFIRMATION_CERTIFICATE,
                            "company_name",
                            "company_name",
                        ),
                        validity_rule(DocumentType.SME_CONFIRMATION_CERTIFICATE),
                    ],
                ),
                (
                    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
                    True,
                    [
                        comparison_rule(
                            DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
                            "business_registration_number",
                            "business_registration_number",
                            value_type="identifier",
                        ),
                        comparison_rule(
                            DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
                            "company_name",
                            "company_name",
                        ),
                        validity_rule(DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE),
                    ],
                ),
                (
                    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
                    True,
                    [
                        comparison_rule(
                            DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
                            "business_registration_number",
                            "business_registration_number",
                            value_type="identifier",
                        ),
                        comparison_rule(
                            DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
                            "company_name",
                            "workplace_name",
                        ),
                        validity_rule(DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE),
                    ],
                ),
            ],
        )
        upsert_workflow(
            db,
            STUDENT_WORKFLOW,
            "학생 제출 문서의 구조화 정보 기반을 확인하는 사전 점검 업무입니다.",
            [
                (
                    DocumentType.ENROLLMENT_CERTIFICATE,
                    True,
                    [
                        (
                            RuleType.DATE_COMPARISON,
                            Severity.ERROR,
                            {
                                "document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
                                "field": "issue_date",
                                "operator": RuleOperator.ON_OR_BEFORE.value,
                                "expected_value": "2026-12-31",
                            },
                        ),
                        # 재학증명서 rules (Phase D2 decision D-1): issued within the last
                        # 90 days (configurable) and the student number must be present.
                        (RuleType.ISSUE_DATE_MAX_AGE, Severity.ERROR, {"max_age_days": 90}),
                        (RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "student_id"}),
                    ],
                ),
                (
                    DocumentType.TRANSCRIPT,
                    False,
                    [
                        student_identity_rule("student_id", value_type="identifier"),
                        student_identity_rule("student_name"),
                        (
                            RuleType.DATE_COMPARISON,
                            Severity.ERROR,
                            {
                                "document_type": DocumentType.TRANSCRIPT.value,
                                "field": "issue_date",
                                "operator": RuleOperator.ON_OR_BEFORE.value,
                                "expected_value": "2026-12-31",
                            },
                        ),
                        (
                            RuleType.NUMERIC_COMPARISON,
                            Severity.ERROR,
                            {
                                "document_type": DocumentType.TRANSCRIPT.value,
                                "field": "gpa",
                                "operator": RuleOperator.GREATER_THAN_OR_EQUAL.value,
                                "expected_value": "3.0",
                            },
                        ),
                    ],
                ),
            ],
        )

        for legacy_name in LEGACY_DEMO_WORKFLOWS:
            legacy = db.query(Checklist).filter_by(name=legacy_name).one_or_none()
            if legacy is not None:
                legacy.is_active = False

        if not db.query(Project).filter_by(name="Demo verification project").one_or_none():
            project = Project(
                owner_id=user.id,
                checklist_id=business.id,
                name="Demo verification project",
                applicant_name="홍길동",
                company_name="한국테크",
            )
            db.add(project)
            db.flush()
            db.add(Submission(project_id=project.id))
        db.commit()
    finally:
        db.close()
    print("Seed data ready.")


if __name__ == "__main__":
    main()
