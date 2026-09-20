from collections.abc import Iterable

from app.core.domain import DocumentType
from app.db.session import Base, SessionLocal, engine
from app.models.entities import Checklist, DocumentRequirement, Project, Submission, User

BUSINESS_WORKFLOW = "기업 제출서류 점검"
STUDENT_WORKFLOW = "학생 제출서류 점검"
LEGACY_DEMO_WORKFLOWS = (
    "Demo four-document checklist",
    "기업 제출서류 점검 (Phase 1 데모)",
)


def upsert_workflow(
    db, name: str, description: str, requirements: Iterable[tuple[DocumentType, bool]]
) -> Checklist:
    workflow = db.query(Checklist).filter_by(name=name).one_or_none()
    if workflow is None:
        workflow = Checklist(name=name, description=description, is_active=True)
        db.add(workflow)
        db.flush()
    else:
        workflow.description = description
        workflow.is_active = True

    workflow.requirements.clear()
    db.flush()
    workflow.requirements.extend(
        DocumentRequirement(document_type=document_type.value, required=required)
        for document_type, required in requirements
    )
    return workflow


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
                (DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True),
                (DocumentType.SME_CONFIRMATION_CERTIFICATE, True),
                (DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, True),
                (DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE, True),
            ],
        )
        upsert_workflow(
            db,
            STUDENT_WORKFLOW,
            "학생 제출 문서의 구조화 정보 기반을 확인하는 사전 점검 업무입니다.",
            [
                (DocumentType.ENROLLMENT_CERTIFICATE, True),
                (DocumentType.TRANSCRIPT, False),
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
