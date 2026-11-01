"""Draft, publish, roll back and read checklist versions; every change is written to the audit log.

Nothing here touches a submission: a submission keeps the version it was created under.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from importlib import resources
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.checklists.guardrails import Warning_, guardrails
from app.checklists.preview import PreviewResult, run_preview, scenarios, stored_cases
from app.checklists.schema import (
    SCHEMA_ID,
    ChecklistDocument,
    Problem,
    document_sha256,
    parse_document,
)
from app.models.entities import AuditLog, Checklist, ChecklistVersion

DRAFT, PUBLISHED, SUPERSEDED = "DRAFT", "PUBLISHED", "SUPERSEDED"
TEMPLATE_FILES = {"business": "business.v1.json", "student": "student.v1.json"}
# Rows seeded before checklists were versioned are matched to their v1 template by name.
LEGACY_NAME_TO_KEY = {"기업 제출서류 점검": "business", "학생 제출서류 점검": "student"}
ACTOR_NO_LOGIN = "admin (no login yet)"


class ChecklistError(Exception):
    def __init__(
        self, code: str, message_ko: str, status: int = 400, problems: list[Problem] | None = None
    ) -> None:
        super().__init__(message_ko)
        self.code, self.message_ko, self.status = code, message_ko, status
        self.problems = problems or []


@dataclass
class DraftResult:
    version: ChecklistVersion
    problems: list[Problem] = field(default_factory=list)
    warnings: list[Warning_] = field(default_factory=list)


def load_template(key: str) -> dict[str, Any]:
    text = (
        resources.files("app.checklists.templates").joinpath(TEMPLATE_FILES[key]).read_text("utf-8")
    )
    return json.loads(text)


def _canonical(document: ChecklistDocument) -> dict[str, Any]:
    return document.to_json()


def _audit(
    db: Session,
    checklist: Checklist,
    version: ChecklistVersion | None,
    event: str,
    actor: str,
    **metadata: Any,
) -> None:
    db.add(
        AuditLog(
            created_at=datetime.now(UTC),  # microseconds, so events of one request keep their order
            checklist_id=checklist.id,
            version_id=version.id if version else None,
            event_name=event,
            metadata_json={"actor": actor, **metadata},
        )
    )


class ChecklistService:
    # -- reading ---------------------------------------------------------------------------
    def get_by_key(self, db: Session, key: str) -> Checklist | None:
        return db.scalar(select(Checklist).where(Checklist.key == key))

    def published(self, db: Session, checklist_id: uuid.UUID) -> ChecklistVersion | None:
        return db.scalar(
            select(ChecklistVersion).where(
                ChecklistVersion.checklist_id == checklist_id, ChecklistVersion.status == PUBLISHED
            )
        )

    def draft(self, db: Session, checklist_id: uuid.UUID) -> ChecklistVersion | None:
        return db.scalar(
            select(ChecklistVersion).where(
                ChecklistVersion.checklist_id == checklist_id, ChecklistVersion.status == DRAFT
            )
        )

    def version(self, db: Session, checklist_id: uuid.UUID, number: int) -> ChecklistVersion:
        found = db.scalar(
            select(ChecklistVersion).where(
                ChecklistVersion.checklist_id == checklist_id, ChecklistVersion.number == number
            )
        )
        if found is None:
            raise ChecklistError("VERSION_NOT_FOUND", "그 버전을 찾을 수 없습니다.", 404)
        return found

    def history(self, db: Session, checklist_id: uuid.UUID) -> list[ChecklistVersion]:
        rows = db.scalars(
            select(ChecklistVersion).where(
                ChecklistVersion.checklist_id == checklist_id, ChecklistVersion.number.is_not(None)
            )
        ).all()
        return sorted(rows, key=lambda row: row.number or 0, reverse=True)

    # -- version 1 -------------------------------------------------------------------------
    def import_template(self, db: Session, key: str, actor: str = "system") -> Checklist:
        """Create a checklist with the template as its published version 1 (once)."""
        existing = self.get_by_key(db, key)
        if existing is not None and self.published(db, existing.id) is not None:
            return existing
        document, problems = parse_document(load_template(key))
        assert document is not None and not problems, problems
        checklist = existing or Checklist(
            key=key, name=document.name_ko, description=document.description_ko, is_active=True
        )
        if existing is None:
            db.add(checklist)
            db.flush()
        self._publish_document(
            db, checklist, document, None, "기존 점검 기준을 1번째 버전으로 등록", actor
        )
        return checklist

    def create(self, db: Session, raw: object, actor: str, note: str = "새 점검 업무") -> Checklist:
        """A new checklist whose first version is published at once."""
        document, problems = parse_document(raw)
        if document is None or problems:
            raise ChecklistError("CHECKLIST_INVALID", "고쳐야 할 항목이 있습니다.", 422, problems)
        if self.get_by_key(db, document.key) is not None:
            raise ChecklistError("KEY_TAKEN", "이미 있는 업무 식별자입니다.", 409)
        checklist = Checklist(
            key=document.key,
            name=document.name_ko,
            description=document.description_ko,
            is_active=True,
        )
        db.add(checklist)
        db.flush()
        self._publish_document(db, checklist, document, None, note, actor)
        return checklist

    # -- draft -----------------------------------------------------------------------------
    def save_draft(
        self,
        db: Session,
        checklist: Checklist,
        raw: object,
        expected_revision: int | None,
        actor: str,
    ) -> DraftResult:
        """Store the draft if it is well-formed; otherwise return the problems and store nothing."""
        document, problems = parse_document(raw)
        base = self.published(db, checklist.id)
        draft = self.draft(db, checklist.id)
        if draft is not None and expected_revision != draft.revision:
            raise ChecklistError(
                "DRAFT_CONFLICT",
                "다른 관리자가 초안을 수정했습니다. 새로고침해 최신 초안을 확인해 주세요.",
                409,
            )
        if draft is None and expected_revision not in (None, 0):
            raise ChecklistError("DRAFT_CONFLICT", "초안이 삭제되었거나 이미 게시되었습니다.", 409)
        if document is None or problems:
            return DraftResult(draft or self._ephemeral(checklist, raw), problems)
        if document.key != checklist.key:
            raise ChecklistError("KEY_CHANGED", "업무 식별자는 바꿀 수 없습니다.", 422)
        content = _canonical(document)
        digest = document_sha256(content)
        if draft is None:
            draft = ChecklistVersion(
                checklist_id=checklist.id,
                status=DRAFT,
                document=content,
                document_sha256=digest,
                schema_version=SCHEMA_ID,
                revision=1,
                created_by=actor,
                parent_version_id=base.id if base else None,
            )
            db.add(draft)
            event = "checklist_draft_created"
        else:
            draft.document, draft.document_sha256 = content, digest
            draft.revision += 1
            event = "checklist_draft_saved"
        try:
            db.flush()
        except IntegrityError as exc:  # two admins created a draft at once
            db.rollback()
            raise ChecklistError(
                "DRAFT_CONFLICT", "다른 관리자가 초안을 만들었습니다.", 409
            ) from exc
        _audit(db, checklist, draft, event, actor, sha256=digest)
        db.commit()
        db.refresh(draft)
        return DraftResult(draft, [], guardrails(content, base.document if base else None))

    def discard_draft(self, db: Session, checklist: Checklist, actor: str) -> None:
        draft = self.draft(db, checklist.id)
        if draft is None:
            raise ChecklistError("NO_DRAFT", "초안이 없습니다.", 404)
        _audit(db, checklist, draft, "checklist_draft_discarded", actor)
        db.delete(draft)
        db.commit()

    @staticmethod
    def _ephemeral(checklist: Checklist, raw: object) -> ChecklistVersion:
        return ChecklistVersion(
            checklist_id=checklist.id,
            status=DRAFT,
            document=raw if isinstance(raw, dict) else {},
            document_sha256="",
            schema_version=SCHEMA_ID,
            revision=0,
        )

    # -- impact preview --------------------------------------------------------------------
    def preview(self, db: Session, checklist: Checklist) -> dict[str, PreviewResult]:
        """The draft against the published rules, on made-up scenarios and on stored submissions."""
        draft, published = self.draft(db, checklist.id), self.published(db, checklist.id)
        if draft is None or published is None:
            raise ChecklistError("NO_DRAFT", "미리 볼 초안이 없습니다.", 404)
        document, problems = parse_document(draft.document)
        if document is None or problems:
            raise ChecklistError(
                "DRAFT_INVALID", "초안에 고쳐야 할 항목이 있습니다.", 422, problems
            )
        cases = scenarios(published.document, draft.document)
        stored = stored_cases(db, checklist.id)
        return {
            "scenarios": run_preview(
                published.document,
                draft.document,
                cases,
                "scenarios",
                "이 업무의 서류·규칙에서 만든 가상 사례입니다. 실제 서류 모음은 이 서버에서 사용할 수 없습니다.",
            ),
            "submissions": run_preview(
                published.document,
                draft.document,
                stored,
                "submissions",
                "이 서버에 저장된 제출 건의 읽은 값으로 다시 계산한 결과입니다.",
            ),
        }

    # -- publish / roll back ---------------------------------------------------------------
    def publish(
        self,
        db: Session,
        checklist: Checklist,
        change_note: str,
        acknowledged: list[str],
        actor: str,
        expected_revision: int | None = None,
    ) -> ChecklistVersion:
        draft = self.draft(db, checklist.id)
        if draft is None:
            raise ChecklistError("NO_DRAFT", "게시할 초안이 없습니다.", 404)
        if expected_revision is not None and expected_revision != draft.revision:
            raise ChecklistError("DRAFT_CONFLICT", "초안이 바뀌었습니다. 다시 확인해 주세요.", 409)
        note = change_note.strip()
        if len(note) < 3:
            raise ChecklistError("CHANGE_NOTE_REQUIRED", "변경 사유를 3자 이상 적어 주세요.", 422)
        document, problems = parse_document(draft.document)
        if document is None or problems:
            raise ChecklistError(
                "DRAFT_INVALID", "초안에 고쳐야 할 항목이 있습니다.", 422, problems
            )
        base = self.published(db, checklist.id)
        content = _canonical(document)
        if base is not None and base.document_sha256 == document_sha256(content):
            raise ChecklistError("NO_CHANGE", "게시된 버전과 달라진 내용이 없습니다.", 422)
        needs_ack = [
            w for w in guardrails(content, base.document if base else None) if w.level == "ACK"
        ]
        if base is not None:
            newly = sum(r.newly_ready for r in self.preview(db, checklist).values())
            if newly:
                needs_ack.append(
                    Warning_(
                        key="PREVIEW_NEWLY_READY:preview",
                        level="ACK",
                        path="preview",
                        message_ko=(
                            f"이 변경으로 지금은 '제출 가능'이 아닌 {newly}건이 '제출 가능'으로 바뀝니다."
                        ),
                    )
                )
        missing = [w for w in needs_ack if w.key not in set(acknowledged)]
        if missing:
            raise ChecklistError(
                "ACKNOWLEDGEMENT_REQUIRED",
                "확인이 필요한 경고가 있습니다: " + " / ".join(w.message_ko for w in missing),
                422,
                [Problem(path=w.path, code=w.key, message_ko=w.message_ko) for w in missing],
            )
        return self._publish_document(
            db, checklist, document, draft, note, actor, acknowledged=[w.key for w in needs_ack]
        )

    def rollback(
        self, db: Session, checklist: Checklist, to_number: int, change_note: str, actor: str
    ) -> ChecklistVersion:
        target = self.version(db, checklist.id, to_number)
        base = self.published(db, checklist.id)
        if base is not None and base.id == target.id:
            raise ChecklistError("NO_CHANGE", "이미 게시 중인 버전입니다.", 422)
        note = change_note.strip()
        if len(note) < 3:
            raise ChecklistError(
                "CHANGE_NOTE_REQUIRED", "되돌리는 사유를 3자 이상 적어 주세요.", 422
            )
        document, problems = parse_document(target.document)
        if document is None or problems:
            raise ChecklistError(
                "VERSION_INVALID", "그 버전은 지금의 규칙 형식과 맞지 않습니다.", 422, problems
            )
        return self._publish_document(
            db, checklist, document, None, note, actor, rolled_back_to=to_number, parent=target
        )

    def _publish_document(
        self,
        db: Session,
        checklist: Checklist,
        document: ChecklistDocument,
        draft: ChecklistVersion | None,
        note: str,
        actor: str,
        *,
        acknowledged: list[str] | None = None,
        rolled_back_to: int | None = None,
        parent: ChecklistVersion | None = None,
    ) -> ChecklistVersion:
        content = _canonical(document)
        current = self.published(db, checklist.id)
        number = (
            db.scalar(
                select(func.max(ChecklistVersion.number)).where(
                    ChecklistVersion.checklist_id == checklist.id
                )
            )
            or 0
        ) + 1
        now = datetime.now(UTC)
        if current is not None:
            current.status = SUPERSEDED
            db.flush()  # free the "one published" slot before the new one takes it
        version = draft or ChecklistVersion(
            checklist_id=checklist.id, schema_version=SCHEMA_ID, created_by=actor
        )
        version.document, version.document_sha256 = content, document_sha256(content)
        version.status, version.number = PUBLISHED, number
        version.change_note, version.published_by, version.published_at = note, actor, now
        origin = parent or current
        version.parent_version_id = origin.id if origin else None
        version.rolled_back_to_number = rolled_back_to
        if draft is None:
            db.add(version)
        checklist.name, checklist.description = document.name_ko, document.description_ko
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ChecklistError(
                "PUBLISH_CONFLICT", "다른 관리자가 동시에 게시했습니다.", 409
            ) from exc
        _audit(
            db,
            checklist,
            version,
            "checklist_rolled_back" if rolled_back_to else "checklist_published",
            actor,
            number=number,
            previous=current.number if current else None,
            rolled_back_to=rolled_back_to,
            change_note=note,
            acknowledged=acknowledged or [],
            sha256=version.document_sha256,
        )
        db.commit()
        db.refresh(version)
        return version


def evaluation_date_for(document: dict[str, Any], today: date) -> date | None:
    """The check date a version's policy fixes, or None when the server's date applies."""
    policy = document.get("check_date", {})
    if policy.get("policy") == "FIXED" and policy.get("fixed_date"):
        return date.fromisoformat(str(policy["fixed_date"]))
    return None
