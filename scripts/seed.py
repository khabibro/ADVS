from app.core.domain import DocumentType, RuleType, Severity
from app.db.session import Base, SessionLocal, engine
from app.models.entities import Checklist, DocumentRequirement, Project, Submission, User, ValidationRule


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter_by(email="demo@advs.local").one_or_none()
    if not user:
        user = User(email="demo@advs.local", display_name="Demo User")
        db.add(user)
        db.flush()
    checklist = db.query(Checklist).filter_by(name="Demo four-document checklist").one_or_none()
    if not checklist:
        checklist = Checklist(name="Demo four-document checklist", description="Phase 1A checklist for the four MVP document types.")
        db.add(checklist)
        db.flush()
        for doc_type in [
            DocumentType.GRADUATION_CERTIFICATE,
            DocumentType.CAREER_CERTIFICATE,
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
            DocumentType.SME_CONFIRMATION_CERTIFICATE,
        ]:
            req = DocumentRequirement(checklist_id=checklist.id, document_type=doc_type, required=True)
            db.add(req)
            db.flush()
            db.add(ValidationRule(requirement_id=req.id, rule_type=RuleType.REQUIRED_DOCUMENT, severity=Severity.ERROR, params={}))
            db.add(ValidationRule(requirement_id=req.id, rule_type=RuleType.REQUIRED_FIELD, severity=Severity.WARNING, params={}))
    if not db.query(Project).filter_by(name="Demo verification project").one_or_none():
        project = Project(owner_id=user.id, checklist_id=checklist.id, name="Demo verification project", applicant_name="홍길동", company_name="한국테크")
        db.add(project)
        db.flush()
        db.add(Submission(project_id=project.id))
    db.commit()
    db.close()
    print("Seed data ready.")


if __name__ == "__main__":
    main()

