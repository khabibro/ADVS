"""Field-value snapshots for the impact preview: extracted values only, never images or text.

A snapshot is one JSON file (`advs.field-snapshot/1`) holding, per case, the values the extractor
read from each document plus the submission date and applicant. Replaying it needs no OCR: the
draft and the published rules are both run over the same stored values.

Two kinds, kept apart on disk:
  * `fictional`: from the fictional dev/hold-out corpora. Committed under evaluation/snapshots/.
  * `private`: from real documents. Only read from data/private_real/snapshots/ (git-ignored) and
    never written anywhere else; the loader refuses a `private` file found in the committed folder.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.checklists.preview import Case
from app.core.domain import DocumentType, ProcessingStatus
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import DocumentSnapshot, FieldSnapshot

SCHEMA_ID = "advs.field-snapshot/1"
REPO_ROOT = Path(__file__).resolve().parents[4]
FICTIONAL_DIR = REPO_ROOT / "evaluation" / "snapshots" / "fictional"
PRIVATE_DIR = REPO_ROOT / "data" / "private_real" / "snapshots"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotField(_Strict):
    value: str | None
    # SUFFICIENT unless the extractor itself was unsure of the value.
    state: Literal["SUFFICIENT", "REVIEW_REQUIRED", "UNAVAILABLE"] = "SUFFICIENT"


class SnapshotDocument(_Strict):
    type: str
    fields: dict[str, str | SnapshotField]


class SnapshotCase(_Strict):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=200)
    workflow: str = Field(min_length=1, max_length=40)
    check_date: date
    applicant_name: str | None = None
    company_name: str | None = None
    # What the check said when the snapshot was taken; the replay must reproduce it.
    observed_status: str | None = None
    documents: list[SnapshotDocument]


class Snapshot(_Strict):
    schema_id: Literal["advs.field-snapshot/1"] = Field(alias="schema")
    kind: Literal["fictional", "private"]
    corpus: str = Field(min_length=1, max_length=60)
    title_ko: str = Field(min_length=1, max_length=120)
    created: date
    cases: list[SnapshotCase]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _dirs() -> tuple[Path, Path]:
    return (
        Path(os.environ.get("ADVS_SNAPSHOT_FICTIONAL_DIR", FICTIONAL_DIR)),
        Path(os.environ.get("ADVS_SNAPSHOT_PRIVATE_DIR", PRIVATE_DIR)),
    )


def parse_snapshot(raw: Any) -> Snapshot:
    return Snapshot.model_validate(raw)


def to_case(case: SnapshotCase, snapshot: Snapshot) -> Case:
    documents = []
    for item in case.documents:
        fields = {}
        for name, entry in item.fields.items():
            value, state = (
                (entry, "SUFFICIENT")
                if isinstance(entry, str)
                else (
                    entry.value,
                    entry.state,
                )
            )
            fields[name] = FieldSnapshot(
                uuid.uuid4(),
                name,
                value,
                state != "SUFFICIENT",
                True,
                assessment_state=EvidenceAssessmentState(state),
            )
        documents.append(
            DocumentSnapshot(
                id=uuid.uuid4(),
                document_type=DocumentType(item.type),
                processing_status=ProcessingStatus.COMPLETED,
                checksum_sha256=uuid.uuid4().hex,
                fields=fields,
            )
        )
    return Case(
        f"{snapshot.corpus}:{case.id}",
        case.label,
        documents,
        case.check_date,
        case.applicant_name,
        case.company_name,
        f"snapshot:{snapshot.kind}",
    )


def load_snapshots(workflow_key: str | None) -> list[tuple[Snapshot, list[Case]]]:
    """Every readable snapshot with the cases that belong to this workflow, oldest name first.

    Unreadable or misplaced files are skipped, not fatal: the preview must still open.
    """
    if not workflow_key:
        return []
    found: list[tuple[Snapshot, list[Case]]] = []
    for kind, folder in zip(("fictional", "private"), _dirs(), strict=True):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            try:
                snapshot = parse_snapshot(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, ValidationError):
                continue
            if snapshot.kind != kind:
                continue  # a private file in the committed folder (or the reverse) is ignored
            cases = [to_case(c, snapshot) for c in snapshot.cases if c.workflow == workflow_key]
            if cases:
                found.append((snapshot, cases))
    return found
