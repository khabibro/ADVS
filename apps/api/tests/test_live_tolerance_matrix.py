"""Item 9: what the applicant types and what the documents print may differ in notation, never in substance. Every
notation difference below is tolerated; every real difference is still caught. Fictional corpus (digital files);
skipped when it is not on this machine. Invented values."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest
from sqlalchemy import select

from app.document_intelligence.normalization.field_normalizer import (
    is_valid_business_number,
    normalize_business_number,
    normalize_date,
)
from app.models.entities import Checklist
from app.services.applicant_gpa import ApplicantGpaError, parse_applicant_gpa

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"
needs_corpus = pytest.mark.skipif(
    not (CORPUS / "manifest.json").exists(), reason="fictional development corpus not present"
)

# (typed company name, expected: tolerated?)
COMPANY = [
    ("주식회사 테스트상사", True),
    ("(주)테스트상사", True),
    ("㈜테스트상사", True),
    ("테스트상사(주)", True),
    ("테스트상사 주식회사", True),
    ("테스트상사", True),
    ("테스트 상사", True),
    ("주식회사테스트상사", True),
    ("테스트상사 ", True),
    ("(주) 테스트상사", True),
    ("주식회사 테스트상사코리아", False),  # another company
    ("주식회사 테스트상서", False),  # one syllable different: no fuzzy matching
    ("주식회사 가나다솔루션", False),
]
STUDENT = [
    ("김테스트", True),
    ("김 테스트", True),
    ("김테스트 ", True),
    ("김테스터", False),
    ("이테스트", False),
]


def _run(client, db_session, set_id: str, kind: str, typed: dict) -> str:
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    runpy.run_path(str(ROOT / "scripts" / "seed.py"))["main"]()
    sets = {item["set_id"]: item for item in manifest["business_sets"] + manifest["student_sets"]}
    item = sets[set_id]
    name = "기업 제출서류 점검" if kind == "business" else "학생 제출서류 점검"
    workflow = db_session.scalar(select(Checklist).where(Checklist.name == name))
    project = client.post(
        "/api/v1/projects", json={"name": f"m {set_id}", "workflow_id": str(workflow.id), **typed}
    ).json()
    for relative in item["files"]["digital"]:
        path = CORPUS / relative
        upload = client.post(
            f"/api/v1/projects/{project['id']}/documents",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
        ).json()
        client.post(f"/api/v1/documents/{upload['id']}/process")
    return client.post(
        f"/api/v1/projects/{project['id']}/verify",
        json={"evaluation_date": manifest["submission_date"]},
    ).json()


@needs_corpus
@pytest.mark.parametrize(("typed", "tolerated"), COMPANY)
def test_company_name_notation(typed: str, tolerated: bool, client, db_session) -> None:
    result = _run(client, db_session, "B01", "business", {"company_name": typed})
    codes = {issue["code"] for issue in result["issues"]}
    if tolerated:
        assert result["status"] == "READY", (typed, codes)
    else:
        assert result["status"] != "READY", typed
        assert (
            "COMPANY_NAME_MISMATCH" not in codes
        )  # a typed name alone never sends a submission to correction


@needs_corpus
@pytest.mark.parametrize(("typed", "tolerated"), STUDENT)
def test_applicant_name_notation(typed: str, tolerated: bool, client, db_session) -> None:
    result = _run(client, db_session, "S01", "student", {"applicant_name": typed})
    assert (result["status"] == "READY") is tolerated, typed


@pytest.mark.parametrize(
    "typed", ["3.4", "3.40", "3,40", " 3.40 ", "3.40/4.3", "3.40 / 4.3", "3.40 / 4.30"]
)
def test_gpa_notation_is_one_value(typed: str) -> None:
    gpa, scale = parse_applicant_gpa(typed)
    assert gpa == "3.40" and scale in (None, "4.3")


@pytest.mark.parametrize("typed", ["3.04", "3.41", "34.0", "3.40 / 4.4", "abc", "3.40 / 4"])
def test_a_different_or_malformed_gpa_is_never_the_same_value(typed: str) -> None:
    try:
        gpa, scale = parse_applicant_gpa(typed)
    except ApplicantGpaError:
        return
    assert (gpa, scale) != ("3.40", "4.3")
    if typed in ("3.04", "3.41"):
        assert gpa != "3.40"


@pytest.mark.parametrize(
    "text", ["123-45-67891", "1234567891", "123 45 67891", "123.45.67891", "123-45-67891."]
)
def test_business_number_formats_are_one_number(text: str) -> None:
    assert (
        normalize_business_number(text) == "1234567891"
        or normalize_business_number(text) == "123-45-67891"
    )
    assert is_valid_business_number("1234567891")


def test_a_different_business_number_is_not_the_same() -> None:
    assert normalize_business_number("123-45-67892") != normalize_business_number("123-45-67891")


@pytest.mark.parametrize(
    "text", ["1999-03-07", "1999.3.7", "1999. 3. 7.", "1999년 3월 7일", "1999/03/07", "1999-3-7"]
)
def test_date_formats_are_one_date(text: str) -> None:
    assert normalize_date(text) == "1999-03-07"


def test_a_different_date_is_not_the_same() -> None:
    assert normalize_date("1999-03-17") != "1999-03-07"
