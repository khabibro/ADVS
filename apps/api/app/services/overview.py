"""Read model for the submission screen.

Everything the web app shows about a submission's state is aggregated here from decisions that
already exist: the stored verification result, the review queue, the documents and their
processing status. Nothing in this module decides a status or an issue; it counts, groups and
names the next step so that the UI never has to derive any of it.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    DocumentType,
    OverallStatus,
    ProcessingStatus,
)
from app.document_intelligence.evidence_sufficiency import FieldReviewDecision
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    FieldReview,
    Project,
    Submission,
    ValidationRule,
)
from app.schemas.api import (
    CheckState,
    NextStep,
    OtherDocumentOverview,
    OverviewCounts,
    OverviewDocumentRef,
    OverviewIssue,
    ProjectOverviewRead,
    RequirementOverview,
    RequirementState,
    VerificationIssueRead,
)
from app.services.reviews import FieldReviewService
from app.services.verification import SubmissionVerificationService

_IN_FLIGHT = {
    ProcessingStatus.UPLOADED.value,
    ProcessingStatus.PREPROCESSING.value,
    ProcessingStatus.OCR_PENDING.value,
    ProcessingStatus.OCR_PROCESSING.value,
    ProcessingStatus.OCR_COMPLETED.value,
    ProcessingStatus.CLASSIFYING.value,
    ProcessingStatus.EXTRACTING.value,
    ProcessingStatus.VALIDATING.value,
}
_RANK = {
    OverallStatus.READY: 0,
    OverallStatus.REVIEW_REQUIRED: 1,
    OverallStatus.NEEDS_CORRECTION: 2,
}
_DATE_RULE_CODES = {"EXPIRED_DOCUMENT", "ISSUE_DATE_TOO_OLD"}


def _issue_key(issue: Any) -> tuple[Any, ...]:
    return (issue.code, issue.document_id, issue.field_name, issue.related_document_id)


def _unique(issues: list[Any]) -> list[Any]:
    """The same finding can be reported by two rules; it is one finding to the reader."""
    seen: set[tuple[Any, ...]] = set()
    out = []
    for issue in issues:
        key = _issue_key(issue)
        if key not in seen:
            seen.add(key)
            out.append(issue)
    return out


def _ref(document: Document) -> OverviewDocumentRef:
    return OverviewDocumentRef(
        id=document.id,
        original_filename=document.original_filename,
        processing_status=document.processing_status,
        document_type=DocumentType(document.document_type),
        error_message=document.error_message,
    )


class ProjectOverviewService:
    def __init__(self) -> None:
        self.verification = SubmissionVerificationService()
        self.reviews = FieldReviewService()

    def build(self, db: Session, project_id: uuid.UUID) -> ProjectOverviewRead | None:
        project = db.scalar(
            select(Project)
            .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
            .where(Project.id == project_id)
        )
        if project is None:
            return None
        stored = self.verification.get_latest(db, project_id)
        result = stored.result if stored.is_current else None
        documents = list(
            db.scalars(
                select(Document)
                .join(Submission)
                .where(Submission.project_id == project_id)
                .order_by(Document.created_at, Document.id)
            ).all()
        )
        review_items = self.reviews.review_items(db, project_id) or []
        review_done = (
            db.query(FieldReview)
            .filter(
                FieldReview.project_id == project_id,
                FieldReview.is_current.is_(True),
                FieldReview.decision.in_(
                    [FieldReviewDecision.CONFIRMED.value, FieldReviewDecision.CORRECTED.value]
                ),
            )
            .count()
        )

        issues = _unique(list(result.issues)) if result else []
        requirements = self._requirements(project, documents, issues, result is not None)
        other = self._other_documents(project, documents)
        enriched = self._enrich(db, project_id, issues, result.evaluation_date if result else None)

        nc = sum(1 for i in issues if i.status_effect == OverallStatus.NEEDS_CORRECTION)
        rr = sum(1 for i in issues if i.status_effect == OverallStatus.REVIEW_REQUIRED)
        required = [r for r in requirements if r.required]
        counts = OverviewCounts(
            requirements_total=len(requirements),
            required_total=len(required),
            required_ok=sum(1 for r in required if r.state == RequirementState.OK),
            required_missing=sum(1 for r in required if r.state == RequirementState.MISSING),
            issues_needs_correction=nc,
            issues_review_required=rr,
            review_open=len(review_items),
            review_done=review_done,
            documents_total=len(documents),
            documents_processing=sum(1 for d in documents if d.processing_status in _IN_FLIGHT),
            documents_failed=sum(
                1 for d in documents if d.processing_status == ProcessingStatus.FAILED.value
            ),
        )
        status = result.status if result else None
        item_count: int | None = None
        if status == OverallStatus.NEEDS_CORRECTION:
            item_count = nc
        elif status == OverallStatus.REVIEW_REQUIRED:
            item_count = counts.review_open or rr
        elif status == OverallStatus.READY:
            item_count = 0
        return ProjectOverviewRead(
            project_id=project.id,
            check_state=CheckState.CURRENT if result else CheckState.NOT_CURRENT,
            status=status,
            evaluation_date=result.evaluation_date if result else None,
            evaluated_at=stored.evaluated_at if result else None,
            suggested_evaluation_date=result.evaluation_date if result else date.today(),
            status_item_count=item_count,
            next_step=self._next_step(counts, status, issues),
            counts=counts,
            requirements=requirements,
            other_documents=other,
            issues=enriched,
            notices=[
                VerificationIssueRead.model_validate(n, from_attributes=True)
                for n in (result.notices if result else ())
            ],
        )

    @staticmethod
    def _next_step(
        counts: OverviewCounts, status: OverallStatus | None, issues: list[Any]
    ) -> NextStep:
        if counts.documents_processing:
            return NextStep.WAIT_PROCESSING
        if counts.documents_total == 0:
            return NextStep.UPLOAD_DOCUMENTS
        if status is None:
            if counts.required_missing:
                return NextStep.UPLOAD_DOCUMENTS
            return NextStep.REVIEW_FIELDS if counts.review_open else NextStep.RUN_CHECK
        if status == OverallStatus.READY:
            return NextStep.DONE
        if any(i.code == "MISSING_REQUIRED_DOCUMENT" for i in issues):
            return NextStep.UPLOAD_DOCUMENTS
        if status == OverallStatus.REVIEW_REQUIRED and counts.review_open:
            return NextStep.REVIEW_FIELDS
        return NextStep.FIX_ISSUES

    @staticmethod
    def _requirements(
        project: Project, documents: list[Document], issues: list[Any], checked: bool
    ) -> list[RequirementOverview]:
        out: list[RequirementOverview] = []
        checklist = project.checklist
        reqs: list[DocumentRequirement] = list(checklist.requirements) if checklist else []
        for requirement in reqs:
            doc_type = DocumentType(requirement.document_type)
            mine = [d for d in documents if d.document_type == doc_type.value]
            touching = [
                i
                for i in issues
                if i.code != "MISSING_REQUIRED_DOCUMENT"
                and (i.document_type == doc_type or i.related_document_type == doc_type)
            ]
            if not mine:
                state = RequirementState.MISSING
            elif any(d.processing_status in _IN_FLIGHT for d in mine):
                state = RequirementState.PROCESSING
            elif not any(d.processing_status == ProcessingStatus.COMPLETED.value for d in mine):
                state = RequirementState.FAILED
            elif not checked:
                state = RequirementState.NOT_CHECKED
            elif touching:
                worst = max((i.status_effect for i in touching), key=lambda s: _RANK[s])
                state = RequirementState(worst.value)
            else:
                state = RequirementState.OK
            out.append(
                RequirementOverview(
                    document_type=doc_type,
                    display_name=DOCUMENT_TYPE_DISPLAY_NAMES[doc_type],
                    required=requirement.required,
                    state=state,
                    documents=[_ref(d) for d in reversed(mine)],
                    issue_codes=sorted({i.code for i in touching}),
                )
            )
        return out

    @staticmethod
    def _other_documents(
        project: Project, documents: list[Document]
    ) -> list[OtherDocumentOverview]:
        checklist = project.checklist
        wanted = {r.document_type for r in (checklist.requirements if checklist else [])}
        out = []
        for document in reversed(documents):
            if document.document_type in wanted:
                continue
            reason = "UNKNOWN_TYPE" if document.document_type == "UNKNOWN" else "NOT_IN_WORKFLOW"
            out.append(OtherDocumentOverview(document=_ref(document), reason=reason))
        return out

    def _enrich(
        self,
        db: Session,
        project_id: uuid.UUID,
        issues: list[Any],
        evaluation_date: date | None,
    ) -> list[OverviewIssue]:
        if not issues:
            return []
        snapshots = {
            d.id: d for d in self.verification.document_snapshots(db, project_id, evaluation_date)
        }

        def value(document_id: uuid.UUID | None, field: str | None) -> str | None:
            if document_id is None or field is None or document_id not in snapshots:
                return None
            snapshot = snapshots[document_id].fields.get(field)
            return snapshot.normalized_value if snapshot else None

        rule_ids = [i.rule_id for i in issues if i.rule_id]
        rules = (
            {
                r.id: r.params or {}
                for r in db.scalars(select(ValidationRule).where(ValidationRule.id.in_(rule_ids)))
            }
            if rule_ids
            else {}
        )
        out = []
        for issue in issues:
            params = rules.get(issue.rule_id, {}) if issue.rule_id else {}
            max_age = params.get("max_age_days")
            expected = params.get("expected_value")
            out.append(
                OverviewIssue(
                    **VerificationIssueRead.model_validate(
                        issue, from_attributes=True
                    ).model_dump(),
                    value=value(issue.document_id, issue.field_name),
                    related_value=value(issue.related_document_id, issue.related_field_name),
                    reference_date=(
                        evaluation_date
                        if issue.code in _DATE_RULE_CODES
                        or max_age is not None
                        or params.get("comparison_source") == "EVALUATION_DATE"
                        else None
                    ),
                    expected_value=str(expected) if expected is not None else None,
                    max_age_days=int(max_age) if isinstance(max_age, int | float) else None,
                )
            )
        return out
