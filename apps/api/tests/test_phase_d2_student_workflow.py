"""Phase D2 (decision D-1): the default student workflow carries the 재학증명서 rules --
90-day issue-date age (configurable) and a required student number. Made-up values."""

from __future__ import annotations

import runpy
from pathlib import Path

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.entities import Checklist

SEED = Path(__file__).resolve().parents[3] / "scripts" / "seed.py"


def _pdf(lines: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page()
    for index, line in enumerate(lines):
        page.insert_text((60, 60 + index * 26), line, fontsize=12, fontname="korea")
    data = document.tobytes()
    document.close()
    return data


def _enrollment(issue: str, student_id: str | None) -> list[str]:
    lines = ["재 학 증 명 서", "성          명 : 류하늘", "소          속 : 공과대학 기계공학과"]
    if student_id:
        lines.append(f"학          번 : {student_id}")
    return [*lines, "위의 사실을 증명합니다.", issue, "한국샘플대학교 총장"]


def _verify(client: TestClient, db_session, lines: list[str], evaluation_date: str) -> dict:
    runpy.run_path(str(SEED))["main"]()
    workflow = db_session.scalar(select(Checklist).where(Checklist.name == "학생 제출서류 점검"))
    project = client.post(
        "/api/v1/projects", json={"name": "s", "workflow_id": str(workflow.id)}
    ).json()
    upload = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("e.pdf", _pdf(lines), "application/pdf")},
    ).json()
    assert client.post(f"/api/v1/documents/{upload['id']}/process").status_code == 200
    return client.post(
        f"/api/v1/projects/{project['id']}/verify", json={"evaluation_date": evaluation_date}
    ).json()


def test_recent_certificate_with_student_number_is_ready(client, db_session) -> None:
    verdict = _verify(
        client, db_session, _enrollment("2026년 09월 20일", "2025123456"), "2026-10-05"
    )
    assert verdict["status"] == "READY", verdict["issues"]


def test_certificate_older_than_ninety_days_needs_correction(client, db_session) -> None:
    verdict = _verify(
        client, db_session, _enrollment("2026년 06월 01일", "2025123456"), "2026-10-05"
    )
    assert verdict["status"] == "NEEDS_CORRECTION"
    assert "RULE_CONDITION_NOT_MET" in {issue["code"] for issue in verdict["issues"]}


def test_certificate_without_a_student_number_goes_to_review(client, db_session) -> None:
    verdict = _verify(
        client, db_session, _enrollment("2026年 09월 20일".replace("年", "년"), None), "2026-10-05"
    )
    assert verdict["status"] == "REVIEW_REQUIRED"


def test_certificate_with_no_issue_date_goes_to_review(client, db_session) -> None:
    lines = [
        line for line in _enrollment("2026년 09월 20일", "2025123456") if "2026년 09월" not in line
    ]
    verdict = _verify(client, db_session, lines, "2026-10-05")
    assert verdict["status"] == "REVIEW_REQUIRED"
