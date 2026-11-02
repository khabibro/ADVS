"""The optional applicant-entered GPA (route B): parsing and the project API. Values are invented."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.applicant_gpa import ApplicantGpaError, parse_applicant_gpa
from tests.test_workflows_api import _workflow


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.4", ("3.40", None)),
        ("3,40", ("3.40", None)),
        (" 3.40 / 4.3 ", ("3.40", "4.3")),
        ("3.40／4.5", ("3.40", "4.5")),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_accepts_plausible_entries(text, expected) -> None:
    assert parse_applicant_gpa(text) == expected


@pytest.mark.parametrize(
    "text", ["abc", "3.456", "5.0", "4.4 / 4.3", "3.4 / 100", "0", "3.4 / 4.3 / 4.5"]
)
def test_parse_rejects_implausible_entries(text: str) -> None:
    with pytest.raises(ApplicantGpaError):
        parse_applicant_gpa(text)


def test_project_stores_and_returns_the_entry(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session)
    created = client.post(
        "/api/v1/projects",
        json={"name": "p", "workflow_id": str(workflow.id), "applicant_gpa": "3.4 / 4.3"},
    )
    assert created.status_code == 201
    assert created.json()["applicant_gpa"] == "3.40 / 4.3"
    updated = client.patch(
        f"/api/v1/projects/{created.json()['id']}",
        json={"name": "p", "workflow_id": str(workflow.id)},
    )
    assert updated.json()["applicant_gpa"] is None  # an update without the entry clears it


def test_project_rejects_a_bad_entry(client: TestClient, db_session) -> None:
    workflow = _workflow(db_session)
    response = client.post(
        "/api/v1/projects",
        json={"name": "p", "workflow_id": str(workflow.id), "applicant_gpa": "9.9"},
    )
    assert response.status_code == 422
