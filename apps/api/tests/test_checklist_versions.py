"""Draft -> publish -> pinned submissions, rollback, guardrails and the audit log (made-up values)."""

from __future__ import annotations

import copy
import uuid

import fitz
import pytest
from sqlalchemy import select

from app.checklists.schema import parse_document
from app.checklists.service import ChecklistError, ChecklistService, load_template
from app.models.entities import AuditLog, Project

service = ChecklistService()
ACTOR = "tester"


def student_document(key: str) -> dict:
    document = load_template("student")
    document["key"] = key
    document["name_ko"] = f"테스트 학생 {key}"
    return document


@pytest.fixture
def checklist(db_session):
    key = f"t-{uuid.uuid4().hex[:8]}"
    return service.create(db_session, student_document(key), ACTOR)


def edited(checklist, **changes) -> dict:
    document = copy.deepcopy(checklist.versions[-1].document)
    for path, value in changes.items():
        target = document
        *parents, last = path.split("__")
        for part in parents:
            target = target[int(part)] if part.isdigit() else target[part]
        target[int(last) if last.isdigit() else last] = value
    return document


# --- schema: the save-time rules -----------------------------------------------------------------


def problems_of(document: dict) -> set[str]:
    _, problems = parse_document(document)
    return {p.code for p in problems}


def test_v1_templates_are_valid():
    for key in ("business", "student"):
        assert problems_of(load_template(key)) == set()


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda d: d["documents"][0]["issue_date"].update(max_age_days=366), "MAX_AGE_RANGE"),
        (lambda d: d["documents"][0]["issue_date"].update(max_age_days=0), "MAX_AGE_RANGE"),
        (lambda d: d["documents"][0].update(extra_required_fields=["gpa"]), "FIELD_UNKNOWN"),
        (lambda d: d["documents"][1].update(validity={"severity": "ERROR"}), "FIELD_UNKNOWN"),
        (lambda d: d["comparisons"][0]["source"].update(field="nope"), "FIELD_UNKNOWN"),
        (lambda d: d["documents"].pop(1), "DOCUMENT_NOT_IN_CHECKLIST"),
        (lambda d: d["check_date"].update(policy="FIXED"), "FIXED_DATE_REQUIRED"),
        (lambda d: d["thresholds"][0].update(value="abc"), "VALUE_INVALID"),
        (lambda d: d["thresholds"][0].update(field="student_id"), "FIELD_NOT_NUMERIC"),
        (lambda d: d["thresholds"][0].update(scale=None), "SCALE_REQUIRED"),
        (lambda d: d["comparisons"][1].update(id=d["comparisons"][0]["id"]), "ID_INVALID"),
    ],
)
def test_save_time_rules(change, code):
    document = student_document("t-x")
    change(document)
    assert code in problems_of(document)


def test_applicant_can_never_change_the_check_date():
    document = student_document("t-x")
    document["check_date"]["applicant_can_change"] = True
    assert problems_of(document)


def test_unknown_keys_are_refused():
    document = student_document("t-x")
    document["surprise"] = 1
    assert problems_of(document)


# --- draft and publish ---------------------------------------------------------------------------


def test_publish_creates_the_next_version_and_supersedes_the_old(db_session, checklist):
    draft = service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=60),
        None,
        ACTOR,
    )
    assert draft.problems == [] and draft.version.revision == 1
    published = service.publish(db_session, checklist, "발급일 90→60일", [], ACTOR)
    assert published.number == 2 and published.status == "PUBLISHED"
    assert service.version(db_session, checklist.id, 1).status == "SUPERSEDED"
    assert service.draft(db_session, checklist.id) is None


def test_invalid_draft_is_not_stored(db_session, checklist):
    result = service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=999),
        None,
        ACTOR,
    )
    assert result.problems and service.draft(db_session, checklist.id) is None


def test_two_editors_cannot_overwrite_each_other(db_session, checklist):
    first = service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=80),
        None,
        ACTOR,
    )
    with pytest.raises(ChecklistError) as stale:
        service.save_draft(
            db_session,
            checklist,
            edited(checklist, documents__0__issue_date__max_age_days=70),
            first.version.revision + 5,
            ACTOR,
        )
    assert stale.value.code == "DRAFT_CONFLICT" and stale.value.status == 409
    again = service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=70),
        first.version.revision,
        ACTOR,
    )
    assert again.version.revision == 2


def test_publish_needs_a_reason_and_a_change(db_session, checklist):
    service.save_draft(db_session, checklist, edited(checklist), None, ACTOR)
    with pytest.raises(ChecklistError) as nothing:
        service.publish(db_session, checklist, "아무것도 안 바꿈", [], ACTOR)
    assert nothing.value.code == "NO_CHANGE"
    service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=30),
        1,
        ACTOR,
    )
    with pytest.raises(ChecklistError) as no_reason:
        service.publish(db_session, checklist, " ", [], ACTOR)
    assert no_reason.value.code == "CHANGE_NOTE_REQUIRED"


def test_loosening_a_check_must_be_acknowledged(db_session, checklist):
    document = edited(checklist, documents__0__issue_date__max_age_days=200)
    service.save_draft(db_session, checklist, document, None, ACTOR)
    with pytest.raises(ChecklistError) as blocked:
        service.publish(db_session, checklist, "기간을 늘림", [], ACTOR)
    assert blocked.value.code == "ACKNOWLEDGEMENT_REQUIRED"
    keys = sorted(p.code for p in blocked.value.problems)
    assert keys[0].startswith("ISSUE_AGE_RAISED:")
    assert "PREVIEW_NEWLY_READY:preview" in keys  # cases that were not 제출 가능 now are
    published = service.publish(db_session, checklist, "기간을 늘림", keys, ACTOR)
    assert published.number == 2
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.version_id == published.id, AuditLog.event_name == "checklist_published"
        )
    )
    assert sorted(audit.metadata_json["acknowledged"]) == keys
    assert audit.metadata_json["change_note"] == "기간을 늘림"


def test_removing_a_comparison_must_be_acknowledged(db_session, checklist):
    document = edited(checklist)
    document["comparisons"] = document["comparisons"][1:]
    service.save_draft(db_session, checklist, document, None, ACTOR)
    with pytest.raises(ChecklistError) as blocked:
        service.publish(db_session, checklist, "비교 삭제", [], ACTOR)
    assert blocked.value.problems[0].code.startswith("COMPARISON_REMOVED:")


def test_tightening_needs_no_acknowledgement(db_session, checklist):
    service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=30),
        None,
        ACTOR,
    )
    assert service.publish(db_session, checklist, "더 엄격하게", [], ACTOR).number == 2


# --- rollback and history ------------------------------------------------------------------------


def test_rollback_publishes_the_old_rules_as_a_new_version(db_session, checklist):
    service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=30),
        None,
        ACTOR,
    )
    service.publish(db_session, checklist, "30일로", [], ACTOR)
    rolled = service.rollback(db_session, checklist, 1, "되돌림", ACTOR)
    assert rolled.number == 3 and rolled.rolled_back_to_number == 1
    assert rolled.document_sha256 == service.version(db_session, checklist.id, 1).document_sha256
    assert [v.number for v in service.history(db_session, checklist.id)] == [3, 2, 1]
    with pytest.raises(ChecklistError):
        service.rollback(db_session, checklist, 3, "이미 게시 중", ACTOR)


def test_every_change_is_in_the_audit_log(db_session, checklist):
    service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=30),
        None,
        ACTOR,
    )
    service.publish(db_session, checklist, "30일로", [], ACTOR)
    service.rollback(db_session, checklist, 1, "되돌림", ACTOR)
    events = [
        row.event_name
        for row in db_session.scalars(
            select(AuditLog)
            .where(AuditLog.checklist_id == checklist.id)
            .order_by(AuditLog.created_at)
        )
    ]
    assert events == [
        "checklist_published",
        "checklist_draft_created",
        "checklist_published",
        "checklist_rolled_back",
    ]


# --- submissions are pinned to their version -----------------------------------------------------


def _pdf(lines: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page()
    for index, line in enumerate(lines):
        page.insert_text((60, 60 + index * 26), line, fontsize=12, fontname="korea")
    data = document.tobytes()
    document.close()
    return data


def _submit(client, workflow_id, issue_line: str) -> dict:
    project = client.post(
        "/api/v1/projects", json={"name": "s", "workflow_id": str(workflow_id)}
    ).json()
    lines = [
        "재 학 증 명 서",
        "성          명 : 류하늘",
        "소          속 : 공과대학 기계공학과",
        "학          번 : 2025123456",
        "위의 사실을 증명합니다.",
        issue_line,
        "한국샘플대학교 총장",
    ]
    upload = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("e.pdf", _pdf(lines), "application/pdf")},
    ).json()
    assert client.post(f"/api/v1/documents/{upload['id']}/process").status_code == 200
    return project


def test_a_submission_keeps_the_version_it_was_created_under(client, db_session, checklist):
    old = _submit(client, checklist.id, "2026년 08월 10일")  # 56 days before 2026-10-05
    service.save_draft(
        db_session,
        checklist,
        edited(checklist, documents__0__issue_date__max_age_days=30),
        None,
        ACTOR,
    )
    service.publish(db_session, checklist, "30일로", [], ACTOR)
    new = _submit(client, checklist.id, "2026년 08월 10일")

    def verdict(project) -> str:
        return client.post(
            f"/api/v1/projects/{project['id']}/verify", json={"evaluation_date": "2026-10-05"}
        ).json()["status"]

    assert verdict(old) == "READY"  # still judged by v1 (90 days)
    assert verdict(new) == "NEEDS_CORRECTION"  # judged by v2 (30 days)
    pins = {
        p.id: (p.checklist_version.number, p.verified_version_id == p.checklist_version_id)
        for p in db_session.scalars(select(Project).where(Project.checklist_id == checklist.id))
    }
    assert sorted(pins.values()) == [(1, True), (2, True)]


def test_stored_result_records_the_version(client, db_session, checklist):
    project = _submit(client, checklist.id, "2026년 09월 20일")
    client.post(f"/api/v1/projects/{project['id']}/verify", json={"evaluation_date": "2026-10-05"})
    from app.models.entities import ValidationResult

    details = db_session.scalars(
        select(ValidationResult.details).where(
            ValidationResult.project_id == uuid.UUID(project["id"]),
            ValidationResult.scope == "SUBMISSION",
        )
    ).all()
    assert details and {d["checklist_version_number"] for d in details} == {1}


# --- per-scale limits: wording and the loosening check ------------------------------------------


def _per_scale(document: dict, **limits: str) -> dict:
    document = copy.deepcopy(document)
    threshold = document["thresholds"][0]
    threshold.pop("value", None)
    threshold["scale"] = {"field": "gpa_scale", "mode": "PER_SCALE", "per_scale": limits}
    return document


def test_splitting_a_limit_by_scale_without_lowering_it_is_not_a_loosening(db_session, checklist):
    from app.checklists.guardrails import guardrails

    base = checklist.versions[-1].document
    same = _per_scale(base, **{"4.5": "3.0", "4.3": "3.0", "4": "3.0"})
    assert not [w for w in guardrails(same, base) if w.key.startswith("THRESHOLD_LOWERED")]
    lower = _per_scale(base, **{"4.5": "3.0", "4.3": "2.9", "4": "3.0"})
    assert [w.key for w in guardrails(lower, base) if w.key.startswith("THRESHOLD_LOWERED")]
    raised = _per_scale(base, **{"4.5": "3.2", "4.3": "3.0", "4": "3.0"})
    assert not [w for w in guardrails(raised, base) if w.key.startswith("THRESHOLD_LOWERED")]


def test_per_scale_sentence_lists_the_largest_scale_first():
    from app.checklists.sentences import threshold_sentence

    text = threshold_sentence(
        {
            "document": "TRANSCRIPT",
            "field": "gpa",
            "operator": "GTE",
            "severity": "ERROR",
            "scale": {"mode": "PER_SCALE", "per_scale": {"4": "2.7", "4.5": "3.0", "4.3": "2.9"}},
        }
    )
    assert text.index("4.5점") < text.index("4.3점") < text.index("4점")
