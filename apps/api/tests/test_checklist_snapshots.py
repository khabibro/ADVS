"""Field-value snapshots in the impact preview (made-up values; no OCR, no images)."""

from __future__ import annotations

import copy
import json
import subprocess
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.checklists import snapshots
from app.checklists.service import ChecklistService, load_template

service = ChecklistService()
ACTOR = "tester"


def case(case_id: str, gpa: str, scale: str, workflow: str) -> dict:
    return {
        "id": case_id,
        "label": f"가상 학생 {case_id}",
        "workflow": workflow,
        "check_date": "2026-10-05",
        "applicant_name": "류하늘",
        "documents": [
            {
                "type": "ENROLLMENT_CERTIFICATE",
                "fields": {
                    "student_name": "류하늘",
                    "university_name": "한국샘플대학교",
                    "student_id": "2025123456",
                    "birth_date": "2001-03-14",
                    "department": "기계공학과",
                    "issue_date": "2026-09-25",
                },
            },
            {
                "type": "TRANSCRIPT",
                "fields": {
                    "student_name": "류하늘",
                    "university_name": "한국샘플대학교",
                    "student_id": "2025123456",
                    "birth_date": "2001-03-14",
                    "issue_date": "2026-09-25",
                    "gpa": gpa,
                    "gpa_scale": {"value": scale, "state": "SUFFICIENT"},
                },
            },
        ],
    }


def snapshot(kind: str, corpus: str, workflow: str) -> dict:
    return {
        "schema": "advs.field-snapshot/1",
        "kind": kind,
        "corpus": corpus,
        "title_ko": f"{corpus} 가상 모음",
        "created": "2026-11-01",
        "cases": [
            case("a", "2.8", "4.5", workflow),
            case("b", "3.4", "4.5", workflow),
            case("other", "2.8", "4.5", "business"),
        ],
    }


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    fictional, private = tmp_path / "fictional", tmp_path / "private"
    fictional.mkdir()
    private.mkdir()
    monkeypatch.setenv("ADVS_SNAPSHOT_FICTIONAL_DIR", str(fictional))
    monkeypatch.setenv("ADVS_SNAPSHOT_PRIVATE_DIR", str(private))
    return fictional, private


@pytest.fixture
def checklist(db_session):
    key = f"snap-{uuid.uuid4().hex[:8]}"
    document = load_template("student")
    document["key"] = key
    document["name_ko"] = f"스냅샷 {key}"
    return service.create(db_session, document, ACTOR)


def loosen_gpa(db_session, checklist):
    document = copy.deepcopy(checklist.versions[-1].document)
    document["thresholds"][0]["value"] = "2.5"
    service.save_draft(db_session, checklist, document, None, ACTOR)


def test_replay_shows_real_would_change_counts(db_session, checklist, dirs):
    fictional, _ = dirs
    (fictional / "dev.json").write_text(
        json.dumps(snapshot("fictional", "dev", checklist.key)), encoding="utf-8"
    )
    loosen_gpa(db_session, checklist)
    result = service.preview(db_session, checklist)
    (corpus,) = result["corpora"]
    assert corpus.source == "corpus:fictional:dev"
    assert corpus.title_ko == "dev 가상 모음"
    assert corpus.total == 2  # the other workflow's case is not replayed
    assert corpus.unchanged == 1  # 3.4 passes both ways
    assert corpus.newly_ready == 1  # 2.8 passes only the loosened limit
    shown = corpus.to_json()
    assert shown["changed"] == 1
    assert shown["cases"][0]["label"] == "가상 학생 a"


def test_corpus_counts_gate_publishing(db_session, checklist, dirs):
    fictional, _ = dirs
    (fictional / "dev.json").write_text(
        json.dumps(snapshot("fictional", "dev", checklist.key)), encoding="utf-8"
    )
    loosen_gpa(db_session, checklist)
    from app.checklists.service import ChecklistError

    with pytest.raises(ChecklistError) as blocked:
        service.publish(db_session, checklist, "기준 낮춤", [], ACTOR)
    assert "PREVIEW_NEWLY_READY:preview" in {p.code for p in blocked.value.problems}


def test_private_snapshot_is_read_only_from_the_private_folder(db_session, checklist, dirs):
    fictional, private = dirs
    (private / "real.json").write_text(
        json.dumps(snapshot("private", "real-seed-b", checklist.key)), encoding="utf-8"
    )
    # A private file dropped into the committed folder, and a fictional one in the private folder,
    # are both ignored.
    (fictional / "oops.json").write_text(
        json.dumps(snapshot("private", "leak", checklist.key)), encoding="utf-8"
    )
    (private / "wrong.json").write_text(
        json.dumps(snapshot("fictional", "wrong", checklist.key)), encoding="utf-8"
    )
    loosen_gpa(db_session, checklist)
    sources = [c.source for c in service.preview(db_session, checklist)["corpora"]]
    assert sources == ["corpus:private:real-seed-b"]


def test_no_snapshots_is_fine(db_session, checklist, dirs):
    loosen_gpa(db_session, checklist)
    assert service.preview(db_session, checklist)["corpora"] == []


def test_broken_files_do_not_break_the_preview(db_session, checklist, dirs):
    fictional, _ = dirs
    (fictional / "broken.json").write_text("{not json", encoding="utf-8")
    (fictional / "bad.json").write_text(json.dumps({"schema": "x"}), encoding="utf-8")
    loosen_gpa(db_session, checklist)
    assert service.preview(db_session, checklist)["corpora"] == []


def test_snapshot_format_is_values_only():
    good = snapshot("fictional", "dev", "student")
    snapshots.parse_snapshot(good)
    for sneaky in ({"image_path": "x.png"}, {"ocr_text": "전문"}, {"bytes": "AAAA"}):
        bad = copy.deepcopy(good)
        bad["cases"][0]["documents"][0].update(sneaky)
        with pytest.raises(ValidationError):
            snapshots.parse_snapshot(bad)


def test_committed_folder_holds_only_fictional_snapshots():
    for path in snapshots.FICTIONAL_DIR.glob("*.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["kind"] == "fictional", path


def test_private_snapshot_folder_is_git_ignored():
    probe = snapshots.PRIVATE_DIR / "probe.json"
    done = subprocess.run(
        ["git", "check-ignore", "-q", str(probe)],
        cwd=Path(snapshots.REPO_ROOT),
        check=False,
    )
    assert done.returncode == 0
