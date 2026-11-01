"""Impact preview: what would change if the draft replaced the published rules.

Two sources, neither of which runs OCR: the stored submissions of this checklist (their saved,
effective field values) and a built-in set of made-up scenarios derived from the documents and
rules themselves (ages around each limit, expiry edges, GPA by scale, each comparison broken in
turn). Both are evaluated under the published rules and under the draft with the same engine; only
the rules differ. Field-value snapshots of the fictional corpora (and, when present locally, of real documents)
are replayed too; see snapshots.py.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checklists.catalog import document_label
from app.checklists.compile import CompiledChecklist, compile_checklist
from app.checklists.schema import parse_document
from app.checklists.sentences import comparison_label
from app.core.domain import DocumentType, OverallStatus, ProcessingStatus
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RuleConfigurationError,
    SubmissionVerificationEngine,
)
from app.models.entities import Project
from app.services.verification import SubmissionVerificationService

REFERENCE_DATE = date(2026, 10, 5)
APPLICANT = "류하늘"
COMPANY = "주식회사 한국샘플"
MAX_LISTED = 200
MAX_STORED = 500
AGES = (45, 59, 60, 61, 89, 90, 91, 179, 181, 364, 366)
RANK = {OverallStatus.READY: 0, OverallStatus.REVIEW_REQUIRED: 1, OverallStatus.NEEDS_CORRECTION: 2}


@dataclass
class Case:
    id: str
    label: str
    documents: list[DocumentSnapshot]
    evaluation_date: date
    applicant_name: str | None = None
    company_name: str | None = None
    source: str = "scenario"


@dataclass
class PreviewResult:
    source: str
    total: int = 0
    unchanged: int = 0
    transitions: dict[str, int] = field(default_factory=dict)
    newly_ready: int = 0
    cases: list[dict[str, Any]] = field(default_factory=list)
    errors: int = 0
    duration_ms: int = 0
    note_ko: str = ""
    title_ko: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "total": self.total,
            "unchanged": self.unchanged,
            "changed": self.total - self.unchanged - self.errors,
            "transitions": [
                {"from": key.split(">")[0], "to": key.split(">")[1], "count": count}
                for key, count in sorted(self.transitions.items())
            ],
            "newly_ready": self.newly_ready,
            "cases": self.cases,
            "listed_cases": len(self.cases),
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "note_ko": self.note_ko,
            "title_ko": self.title_ko,
        }


# --- made-up scenarios ---------------------------------------------------------------------------


def _field(name: str, value: str) -> FieldSnapshot:
    return FieldSnapshot(
        uuid.uuid4(),
        name,
        value,
        False,
        True,
        assessment_state=EvidenceAssessmentState.SUFFICIENT,
    )


def _document(kind: str, values: dict[str, str]) -> DocumentSnapshot:
    return DocumentSnapshot(
        id=uuid.uuid4(),
        document_type=DocumentType(kind),
        processing_status=ProcessingStatus.COMPLETED,
        checksum_sha256=uuid.uuid4().hex,
        fields={name: _field(name, value) for name, value in values.items()},
    )


def _base_values(kind: str) -> dict[str, str]:
    recent = (REFERENCE_DATE - timedelta(days=10)).isoformat()
    later = (REFERENCE_DATE + timedelta(days=200)).isoformat()
    brn = "1048127382"
    return {
        "BUSINESS_REGISTRATION_CERTIFICATE": {
            "company_name": COMPANY,
            "business_registration_number": brn,
        },
        "SME_CONFIRMATION_CERTIFICATE": {
            "company_name": COMPANY,
            "business_registration_number": brn,
            "valid_from": "2026-01-01",
            "valid_until": later,
        },
        "NATIONAL_TAX_PAYMENT_CERTIFICATE": {
            "company_name": COMPANY,
            "business_registration_number": brn,
            "valid_until": later,
        },
        "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE": {
            "workplace_name": COMPANY,
            "business_registration_number": brn,
            "valid_until": later,
        },
        "ENROLLMENT_CERTIFICATE": {
            "student_name": APPLICANT,
            "university_name": "한국샘플대학교",
            "student_id": "2025123456",
            "birth_date": "2001-03-14",
            "department": "기계공학과",
            "issue_date": recent,
        },
        "TRANSCRIPT": {
            "student_name": APPLICANT,
            "university_name": "한국샘플대학교",
            "student_id": "2025123456",
            "birth_date": "2001-03-14",
            "issue_date": recent,
            "gpa": "3.5",
            "gpa_scale": "4.5",
        },
        "GRADUATION_CERTIFICATE": {
            "applicant_name": APPLICANT,
            "university_name": "한국샘플대학교",
            "department": "기계공학과",
            "degree": "학사",
            "graduation_date": "2025-02-20",
            "issue_date": recent,
        },
        "CAREER_CERTIFICATE": {
            "applicant_name": APPLICANT,
            "company_name": COMPANY,
            "position": "연구원",
            "employment_start_date": "2020-03-01",
            "employment_end_date": "2024-02-28",
            "issue_date": recent,
        },
    }[kind]


def _different(value: str) -> str:
    """A value that is clearly not the same: the last digit changed, or another name."""
    if value and value[-1].isdigit():
        return value[:-1] + str((int(value[-1]) + 1) % 10)
    return "전혀다른이름"


def scenarios(*documents: dict[str, Any]) -> list[Case]:
    """Made-up submissions covering the documents and rules of the given rule documents."""
    types: list[str] = []
    for document in documents:
        for item in document["documents"]:
            if item["type"] not in types:
                types.append(item["type"])

    def build(overrides: dict[str, dict[str, str]] | None = None, drop: str | None = None):
        overrides = overrides or {}
        return [
            _document(kind, {**_base_values(kind), **overrides.get(kind, {})})
            for kind in types
            if kind != drop
        ]

    cases: list[Case] = []

    def add(case_id: str, label: str, docs: list[DocumentSnapshot]) -> None:
        cases.append(Case(case_id, label, docs, REFERENCE_DATE, APPLICANT, COMPANY))

    add("clean", "모든 서류가 정상", build())
    for kind in types:
        if kind not in {"UNKNOWN"}:
            add(f"missing-{kind}", f"{document_label(kind)} 미제출", build(drop=kind))
    for kind in types:
        values = _base_values(kind)
        if "issue_date" in values:
            for age in AGES:
                issued = (REFERENCE_DATE - timedelta(days=age)).isoformat()
                add(
                    f"age-{kind}-{age}",
                    f"{document_label(kind)} 발급 {age}일 전",
                    build({kind: {"issue_date": issued}}),
                )
        if "valid_until" in values:
            for offset, name in ((-1, "만료 하루 지남"), (0, "만료일이 점검 기준일")):
                until = (REFERENCE_DATE + timedelta(days=offset)).isoformat()
                add(
                    f"valid-{kind}-{offset}",
                    f"{document_label(kind)} {name}",
                    build({kind: {"valid_until": until}}),
                )
    if "TRANSCRIPT" in types:
        for gpa, scale in (
            ("3.0", "4.5"),
            ("2.95", "4.3"),
            ("2.5", "4.5"),
            ("2.7", "4"),
            ("3.5", ""),
        ):
            overrides = {"gpa": gpa, "gpa_scale": scale}
            docs = build({"TRANSCRIPT": {k: v for k, v in overrides.items() if v}})
            if not scale:
                for item in docs:
                    if item.document_type == DocumentType.TRANSCRIPT:
                        item.fields.pop("gpa_scale", None)
            add(f"gpa-{gpa}-{scale or 'none'}", f"평점 {gpa} / 만점 {scale or '읽지 못함'}", docs)
    seen: set[str] = set()
    for document in documents:
        for item in document.get("comparisons", []):
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            target = item["target"]
            if target["document"] not in types or item["source"]["document"] not in types:
                continue
            current = _base_values(target["document"]).get(target["field"], "")
            add(
                f"cmp-{item['id']}",
                f"비교 불일치: {comparison_label(item)}",
                build({target["document"]: {target["field"]: _different(current)}}),
            )
    return cases


# --- evaluation ----------------------------------------------------------------------------------


def _evaluate(case: Case, compiled: CompiledChecklist) -> tuple[OverallStatus, frozenset[str]]:
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=compiled.requirements,
        documents=case.documents,
        context=compiled.context(case.evaluation_date, case.applicant_name, case.company_name),
    )
    return result.status, frozenset(issue.code for issue in result.issues)


def stored_cases(db: Session, checklist_id: uuid.UUID) -> list[Case]:
    service = SubmissionVerificationService()
    projects = db.scalars(
        select(Project)
        .where(Project.checklist_id == checklist_id)
        .order_by(Project.created_at.desc())
        .limit(MAX_STORED)
    ).all()
    out = []
    for project in projects:
        when = project.check_date or date.today()
        documents = service.document_snapshots(db, project.id, when)
        if not documents:
            continue
        out.append(
            Case(
                str(project.id),
                project.name,
                documents,
                when,
                project.applicant_name,
                project.company_name,
                "submission",
            )
        )
    return out


def run_preview(
    published: dict[str, Any],
    draft: dict[str, Any],
    cases: list[Case],
    source: str,
    note_ko: str = "",
    title_ko: str = "",
) -> PreviewResult:
    started = time.perf_counter()
    old_doc, _ = parse_document(published)
    new_doc, _ = parse_document(draft)
    assert old_doc is not None and new_doc is not None
    old, new = compile_checklist(old_doc), compile_checklist(new_doc)
    result = PreviewResult(source=source, note_ko=note_ko, title_ko=title_ko)
    for case in cases:
        result.total += 1
        try:
            before, before_codes = _evaluate(case, old)
            after, after_codes = _evaluate(case, new)
        except RuleConfigurationError:
            result.errors += 1
            continue
        if before == after and before_codes == after_codes:
            result.unchanged += 1
            continue
        if before != after:
            key = f"{before.value}>{after.value}"
            result.transitions[key] = result.transitions.get(key, 0) + 1
        if before != OverallStatus.READY and after == OverallStatus.READY:
            result.newly_ready += 1
        if len(result.cases) < MAX_LISTED:
            result.cases.append(
                {
                    "id": case.id,
                    "label": case.label,
                    "current": before.value,
                    "draft": after.value,
                    "current_issues": sorted(before_codes),
                    "draft_issues": sorted(after_codes),
                    "newly_ready": before != OverallStatus.READY and after == OverallStatus.READY,
                }
            )
    result.duration_ms = int((time.perf_counter() - started) * 1000)
    return result
