import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProblemRead(BaseModel):
    path: str
    code: str
    message_ko: str


class WarningRead(BaseModel):
    key: str
    level: str
    path: str
    message_ko: str


class VersionSummary(BaseModel):
    number: int | None
    status: str
    revision: int
    change_note: str | None = None
    created_by: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    rolled_back_to_number: int | None = None
    document_sha256: str


class VersionRead(VersionSummary):
    id: uuid.UUID
    document: dict[str, Any]
    sentences: dict[str, Any]
    warnings: list[WarningRead] = []


class AdminWorkflowSummary(BaseModel):
    id: uuid.UUID
    key: str | None
    name: str
    published_number: int | None
    has_draft: bool
    projects: int
    last_changed_at: datetime | None = None


class AdminWorkflowRead(BaseModel):
    id: uuid.UUID
    key: str | None
    name: str
    published: VersionRead | None
    draft: VersionRead | None


class DraftSave(BaseModel):
    document: dict[str, Any]
    # Revision of the draft the editor loaded; omit (or 0) when there is no draft yet.
    expected_revision: int | None = None


class DraftSaved(BaseModel):
    saved: bool
    problems: list[ProblemRead] = []
    draft: VersionRead | None = None


class PublishRequest(BaseModel):
    change_note: str = Field(min_length=3, max_length=500)
    acknowledged_warnings: list[str] = []
    expected_revision: int | None = None


class RollbackRequest(BaseModel):
    to_version: int = Field(ge=1)
    change_note: str = Field(min_length=3, max_length=500)


class ChangeRead(BaseModel):
    area: str
    label: str
    kind: str
    before: str | None
    after: str | None


class DiffRead(BaseModel):
    from_number: int | None
    to_number: int | None
    changes: list[ChangeRead]


class AuditRead(BaseModel):
    id: uuid.UUID
    at: datetime
    event: str
    actor: str | None
    checklist_id: uuid.UUID | None
    checklist_name: str | None
    version_number: int | None
    detail: dict[str, Any]


class TransitionRead(BaseModel):
    from_: str = Field(alias="from")
    to: str
    count: int

    model_config = {"populate_by_name": True}


class PreviewCaseRead(BaseModel):
    id: str
    label: str
    current: str
    draft: str
    current_issues: list[str]
    draft_issues: list[str]
    newly_ready: bool


class PreviewSourceRead(BaseModel):
    source: str
    total: int
    unchanged: int
    changed: int
    transitions: list[TransitionRead]
    newly_ready: int
    cases: list[PreviewCaseRead]
    listed_cases: int
    errors: int
    duration_ms: int
    note_ko: str


class PreviewRead(BaseModel):
    scenarios: PreviewSourceRead
    submissions: PreviewSourceRead


class DocumentCheck(BaseModel):
    document: dict[str, Any]


class ChecklistCheckRead(BaseModel):
    problems: list[ProblemRead] = []
    sentences: dict[str, Any] = {}
    warnings: list[WarningRead] = []
