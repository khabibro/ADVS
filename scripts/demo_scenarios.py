"""Demo scenarios D1-D8 for the midterm presentation, driven through the real HTTP API.

    python scripts/demo_scenarios.py preload     # create + process every scenario in the running API

Only the fictional test-variant set is used. Expected results are asserted by
scripts/demo_rehearsal; nothing here changes any logic to make a scenario pass.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"
API = os.environ.get("ADVS_API_URL", "http://localhost:8000/api/v1")
SUBMISSION_DATE = "2026-10-05"  # the date every test-variant document was built against
WORKFLOW_NAMES = {"business": "기업 제출서류 점검", "student": "학생 제출서류 점검"}
MIME = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


@dataclass(frozen=True)
class Scenario:
    code: str
    title: str  # Korean project name shown on screen
    set_id: str
    version: str  # digital | scanned | images
    workflow: str  # business | student
    expect_status: str
    expect_issues: tuple[str, ...] = ()  # issue codes that must be present
    review: bool = False  # D6: reviewer confirms the remaining fields


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("D1", "D1 정상 제출 (기업)", "B01", "digital", "business", "READY"),
    Scenario("D2", "D2 만료된 납세증명서", "B05", "digital", "business", "NEEDS_CORRECTION",
             ("EXPIRED_DOCUMENT",)),
    Scenario("D3", "D3 회사명 불일치", "B03", "digital", "business", "NEEDS_CORRECTION",
             ("INFORMATION_MISMATCH",)),
    Scenario("D4", "D4 회사명 표기 차이 (주식회사/(주)/㈜)", "B02", "digital", "business", "READY"),
    # Actual behaviour (verified): the 지방세 certificate is not recognised as a 국세
    # certificate, so the submission is held for review (확인 필요), never 제출 가능.
    Scenario("D5", "D5 유사 문서 (지방세 납세증명서)", "B11", "digital", "business",
             "REVIEW_REQUIRED", ("UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW",)),
    Scenario("D6", "D6 스캔본 제출 + 사람 확인", "B01", "scanned", "business", "REVIEW_REQUIRED",
             review=True),
    Scenario("D7", "D7 정상 제출 (학생)", "S01", "digital", "student", "READY"),
    Scenario("D8", "D8 필수 서류 누락", "B08", "digital", "business", "NEEDS_CORRECTION",
             ("MISSING_REQUIRED_DOCUMENT",)),
)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def scenario_files(scn: Scenario) -> list[Path]:
    manifest = json.loads((VARIANTS / "manifest.json").read_text(encoding="utf-8"))
    sets = manifest["business_sets"] + manifest["student_sets"]
    entry = next(s for s in sets if s["set_id"] == scn.set_id)
    paths = [VARIANTS / rel for rel in entry["files"][scn.version]]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"test documents missing (generate the set first): {missing[:2]}")
    return paths


@dataclass
class Outcome:
    scenario: Scenario
    project_id: str
    status: str | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)  # DocumentDetail per file
    seconds: float = 0.0
    review_items: list[dict[str, Any]] = field(default_factory=list)


class DemoClient:
    def __init__(self, base: str = API, timeout: float = 600.0) -> None:
        self.http = httpx.Client(base_url=base, timeout=timeout)

    def close(self) -> None:
        self.http.close()

    def workflow_id(self, workflow: str) -> str:
        rows = self.http.get("/workflows").raise_for_status().json()
        return next(w["id"] for w in rows if w["name"] == WORKFLOW_NAMES[workflow])

    def run(self, scn: Scenario, name: str | None = None) -> Outcome:
        started = time.perf_counter()
        project = self.http.post(
            "/projects",
            json={"name": name or scn.title, "workflow_id": self.workflow_id(scn.workflow)},
        ).raise_for_status().json()
        out = Outcome(scn, project["id"])
        for path in scenario_files(scn):
            ext = path.suffix.lower().lstrip(".")
            with path.open("rb") as handle:
                doc = self.http.post(
                    f"/projects/{project['id']}/documents",
                    files={"file": (_nfc(path.name), handle, MIME.get(ext, "application/octet-stream"))},
                ).raise_for_status().json()
            self.http.post(f"/documents/{doc['id']}/process").raise_for_status()
            out.documents.append(self.http.get(f"/documents/{doc['id']}").raise_for_status().json())
        self.verify(out)
        out.seconds = time.perf_counter() - started
        return out

    def verify(self, out: Outcome) -> None:
        body = self.http.post(
            f"/projects/{out.project_id}/verify", json={"evaluation_date": SUBMISSION_DATE}
        ).raise_for_status().json()
        out.status = body["status"]
        out.issues = body["issues"]
        out.review_items = self.http.get(
            f"/projects/{out.project_id}/review-items"
        ).raise_for_status().json()
        out.documents = [
            self.http.get(f"/documents/{d['id']}").raise_for_status().json() for d in out.documents
        ]

    def confirm_open_items(self, out: Outcome, reviewer: str = "데모 검토자") -> int:
        """Reviewer confirms every field still waiting for a human (what the screen's 확인 button does)."""
        confirmed = 0
        for item in out.review_items:
            if item["queue_status"] != "PENDING" or item["machine_normalized_value"] is None:
                continue
            self.http.post(
                f"/projects/{out.project_id}/documents/{item['document_id']}"
                f"/fields/{item['field_name']}/review",
                json={
                    "expected_processing_version": item["processing_version"],
                    "decision": "CONFIRMED",
                    "reviewer_label": reviewer,
                },
            ).raise_for_status()
            confirmed += 1
        self.verify(out)
        return confirmed

    def delete_project(self, project_id: str) -> None:
        self.http.delete(f"/projects/{project_id}").raise_for_status()


def preload() -> int:
    client = DemoClient()
    try:
        # seed.py creates an empty "Demo verification project"; keep the demo list to D1-D8.
        for project in client.http.get("/projects").json():
            if not project["name"][:2].startswith("D") or not project["name"][1:2].isdigit():
                client.delete_project(project["id"])
        # The project list shows newest first, so create D8 first and D1 last: D1 ends up on top.
        for scn in reversed(SCENARIOS):
            out = client.run(scn)
            print(f"  {scn.code} {out.status:<17} {out.seconds:5.1f}s  {scn.title}")
            time.sleep(1.1)  # created_at has one-second resolution; keep the list order stable
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["preload"]:
        raise SystemExit(preload())
    if len(sys.argv) == 4 and sys.argv[1] == "run":  # run <code> <project name>: prints the project id
        _client = DemoClient()
        print(_client.run(next(s for s in SCENARIOS if s.code == sys.argv[2]), sys.argv[3]).project_id)
        raise SystemExit(0)
    raise SystemExit(__doc__)
