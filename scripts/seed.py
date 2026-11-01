"""Demo data: the demo user, the two checklists as published version 1, one demo submission.

The two real checklists live in ``apps/api/app/checklists/templates/*.v1.json``
(``advs.checklist/1``), not in code, and running this on a database that already has a published
version changes nothing: a checklist is edited in the admin app, never by re-seeding.

``upsert_workflow`` and the rule helpers below only build scratch, row-based workflows for tests
and evaluation harnesses (the legacy path, which a checklist without a version still takes).
"""

from collections.abc import Iterable
from typing import Any

from app.checklists.service import LEGACY_NAME_TO_KEY, ChecklistService
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


def ensure_checklist(db, key: str) -> Checklist:
    service = ChecklistService()
    if service.get_by_key(db, key) is None:
        # a database seeded before checklists were versioned: adopt the row of the same name
        legacy = db.query(Checklist).filter(Checklist.key.is_(None)).all()
        for row in legacy:
            if LEGACY_NAME_TO_KEY.get(row.name) == key:
                row.key = key
                db.flush()
                break
    checklist = service.import_template(db, key)
    published = service.published(db, checklist.id)
    assert published is not None
    for project in db.query(Project).filter(
        Project.checklist_id == checklist.id, Project.checklist_version_id.is_(None)
    ):
        project.checklist_version_id = published.id
    db.commit()
    return checklist


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="demo@advs.local").one_or_none()
        if user is None:
            user = User(email="demo@advs.local", display_name="Demo User")
            db.add(user)
            db.flush()

        business = ensure_checklist(db, "business")
        ensure_checklist(db, "student")

        for legacy_name in LEGACY_DEMO_WORKFLOWS:
            legacy = db.query(Checklist).filter_by(name=legacy_name).one_or_none()
            if legacy is not None:
                legacy.is_active = False

        if not db.query(Project).filter_by(name="Demo verification project").one_or_none():
            published = ChecklistService().published(db, business.id)
            project = Project(
                owner_id=user.id,
                checklist_id=business.id,
                checklist_version_id=published.id if published else None,
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
