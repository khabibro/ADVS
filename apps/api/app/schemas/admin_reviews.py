from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.api import FieldReviewRead, PageInfoRead, ReviewItemRead


class QueueItemRead(BaseModel):
    project_id: uuid.UUID
    project_name: str
    applicant_name: str | None
    company_name: str | None
    workflow_key: str | None
    workflow_name: str | None
    version_number: int | None
    document_id: uuid.UUID
    document_type: str
    document_label: str
    field_name: str
    field_label: str
    machine_value: str | None
    confidence: float | None
    queue_status: str
    issue_code: str
    one_click: bool
    confirmation: str | None = None
    waiting_since: datetime
    finalised: bool


class FacetValue(BaseModel):
    value: str
    label: str
    count: int


class QueueFacets(BaseModel):
    workflows: list[FacetValue]
    documents: list[FacetValue]
    fields: list[FacetValue]
    status: dict[str, int]


class QueueRead(BaseModel):
    total: int
    items: list[QueueItemRead]
    facets: QueueFacets


class SiblingRead(BaseModel):
    document_id: uuid.UUID
    document_label: str
    field_name: str
    field_label: str
    queue_status: str


class ReviewDetailRead(BaseModel):
    project_id: uuid.UUID
    project_name: str
    applicant_name: str | None
    company_name: str | None
    document_id: uuid.UUID
    document_label: str
    field_name: str
    field_label: str
    # False when the value was decided or is now sufficient: only the history remains.
    open: bool
    one_click: bool = False
    # Other values of this submission still waiting for a person, and whether every one of them
    # (this one included) can be settled with one keystroke.
    project_open_items: int = 0
    project_only_one_click: bool = False
    item: ReviewItemRead | None
    pages: list[PageInfoRead]
    siblings: list[SiblingRead]
    history: list[FieldReviewRead]


class ReviewLogItemRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str | None
    document_id: uuid.UUID
    document_label: str
    field_name: str
    field_label: str
    decision: str
    machine_value: str | None
    reviewed_value: str | None
    reviewer_label: str | None
    note: str | None
    reviewed_at: datetime
    is_current: bool
    stale: bool
    superseded: bool


class ReviewLogRead(BaseModel):
    total: int
    items: list[ReviewLogItemRead]
