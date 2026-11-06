"""Item 11: the evaluation runner and the live API give identical decisions for the same files and the same typed
fields (empty / correct / short / Latin). The runner posts to the same FastAPI app, so any difference would mean the
two paths build the project or the check differently. Uses the fictional development corpus (digital files, no OCR);
skipped when the corpus is not on this machine."""

from __future__ import annotations

import importlib.util
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.entities import Checklist

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"
RUNNER = ROOT / "evaluation" / "harness" / "run_variants.py"
SETS = "B01,B02,B03,S01,S02,S05"

pytestmark = pytest.mark.skipif(
    not (CORPUS / "manifest.json").exists(), reason="fictional development corpus not present"
)


def _typed_values():
    spec = importlib.util.spec_from_file_location(
        "harness_core", ROOT / "evaluation" / "harness" / "harness_core.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["harness_core"] = module
    spec.loader.exec_module(module)
    return module.typed_values


def _runner_statuses(mode: str, tmp_path: Path) -> dict[str, str]:
    out = tmp_path / f"runner_{mode}.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--corpus",
            "dev",
            "--output",
            str(out),
            "--sets",
            SETS,
            "--versions",
            "digital",
            "--skip-ocr",
            "--skip-formats",
            "--input-mode",
            mode,
        ],
        cwd=ROOT / "apps" / "api",
        env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        check=True,
        capture_output=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    return {
        sid: item["versions"]["digital"]["actual_submission_status"]
        for sid, item in data["sets"].items()
    }


@pytest.mark.parametrize("mode", ["empty", "correct", "short", "latin"])
def test_the_runner_and_the_api_agree(mode: str, client, db_session, tmp_path) -> None:
    typed_values = _typed_values()
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    runpy.run_path(str(ROOT / "scripts" / "seed.py"))["main"]()
    workflows = {
        "business": db_session.scalar(
            select(Checklist).where(Checklist.name == "기업 제출서류 점검")
        ),
        "student": db_session.scalar(
            select(Checklist).where(Checklist.name == "학생 제출서류 점검")
        ),
    }
    expected = _runner_statuses(mode, tmp_path)
    assert set(expected) == set(SETS.split(","))
    sets = {item["set_id"]: item for item in manifest["business_sets"] + manifest["student_sets"]}
    for set_id, runner_status in expected.items():
        item = sets[set_id]
        body = {
            "name": f"parity {set_id} {mode}",
            "workflow_id": str(workflows[item["workflow"]].id),
        }
        body.update(typed_values(mode, item["workflow"], manifest.get("fictional_entities", {})))
        project = client.post("/api/v1/projects", json=body).json()
        for relative in item["files"]["digital"]:
            path = CORPUS / relative
            upload = client.post(
                f"/api/v1/projects/{project['id']}/documents",
                files={"file": (path.name, path.read_bytes(), "application/pdf")},
            ).json()
            assert client.post(f"/api/v1/documents/{upload['id']}/process").status_code == 200
        verified = client.post(
            f"/api/v1/projects/{project['id']}/verify",
            json={"evaluation_date": manifest["submission_date"]},
        ).json()
        assert verified["status"] == runner_status, (set_id, mode)
