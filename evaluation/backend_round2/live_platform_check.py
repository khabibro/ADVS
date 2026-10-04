"""Live-platform end-to-end test against the running ADVS stack.

Drives exactly the calls the browser makes, in order, against
http://localhost:8000:

    POST /projects                 -> createProject
    POST /projects/{id}/documents  -> upload (multipart)
    POST /documents/{id}/process   -> process
    GET  /documents/{id}           -> detail (what the review panel renders)
    POST /projects/{id}/verify     -> submission verification
    GET  /projects/{id}/reviews    -> review items
    GET  /documents/{id}           -> detail again, to prove refresh is stable

Purpose: prove the deployed container behaves like the in-process harness, and
that the UI is not shown a state the backend does not hold.

Prints safe summaries only. No document values are written to disk or stdout
beyond the fields listed under FIELDS, which the caller chooses.

    ./live_platform_check.py --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_round2 import DATASET, WORK_DIR, resolve_source  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--only", default=None, help="sample id, e.g. R2-05")
    parser.add_argument("--show-values", action="store_true")
    args = parser.parse_args()
    base = f"http://localhost:{args.port}/api/v1"

    ground_truth = json.loads((WORK_DIR / "ground_truth.json").read_text(encoding="utf-8"))[
        "samples"
    ]
    client = httpx.Client(timeout=600.0)
    failures = 0

    health = client.get(f"{base}/health")
    print("health:", health.status_code, health.text.strip()[:80])

    checklists = client.get(f"{base}/checklists").json()
    by_name = {item["name"]: item["id"] for item in checklists}
    student = next((v for k, v in by_name.items() if "학생" in k), None)
    business = next((v for k, v in by_name.items() if "기업" in k), None)
    if not student or not business:
        print("BLOCKED: seeded checklists not visible:", list(by_name))
        return 2

    for sample_id, filename, content_type in DATASET:
        if args.only and sample_id != args.only:
            continue
        truth = ground_truth[sample_id]
        expected_type = truth["document_type"]
        workflow = student if "STUDENT" in expected_type or expected_type in {
            "ENROLLMENT_CERTIFICATE",
            "TRANSCRIPT",
            "GRADUATION_CERTIFICATE",
            "CAREER_CERTIFICATE",
        } else business

        print("=" * 78)
        print(f"{sample_id}  {unicodedata.normalize('NFC', filename)}")
        project = client.post(
            f"{base}/projects",
            json={"name": f"live-{sample_id}-{uuid.uuid4().hex[:6]}", "workflow_id": workflow},
        )
        project.raise_for_status()
        project_id = project.json()["id"]

        source = resolve_source(filename)
        with source.open("rb") as handle:
            upload = client.post(
                f"{base}/projects/{project_id}/documents",
                files={"file": (filename, handle, content_type)},
            )
        if upload.status_code != 201:
            print("  UPLOAD REJECTED:", upload.status_code, upload.text[:200])
            failures += 1
            continue
        document_id = upload.json()["id"]

        started = time.perf_counter()
        process = client.post(f"{base}/documents/{document_id}/process")
        elapsed = time.perf_counter() - started
        if process.status_code != 200:
            print("  PROCESS FAILED:", process.status_code, process.text[:200])
            failures += 1
            continue
        processed = process.json()

        detail = client.get(f"{base}/documents/{document_id}").json()
        print(f"  status        : {processed['processing_status']} in {elapsed:.1f}s")
        print(f"  type          : {detail['document_type']} (expected {expected_type})")
        print(f"  overall       : {detail['overall_status']}")
        print(f"  missing fields: {detail['missing_expected_fields']}")
        print("  FIELDS")
        for field in detail["extracted_fields"]:
            name = field["field_name"]
            value = field.get("normalized_value")
            marker = "" if value else "  (unresolved)"
            shown = value if args.show_values else ("SET" if value else "-")
            print(
                f"    {name:34s} {shown:>8s}{marker}  review={field['needs_review']} "
                f"evidence={len(field.get('evidence') or [])} "
                f"assessment={field.get('evidence_assessment')}"
            )

        verify = client.post(
            f"{base}/projects/{project_id}/verify", json={"evaluation_date": "2026-09-29"}
        )
        if verify.status_code == 200:
            result = verify.json()
            codes = sorted({issue["code"] for issue in result["issues"]})
            print(f"  verify status : {result['status']}")
            print(f"  verify codes  : {codes}")
            unresolved = sum(
                1 for issue in result["issues"] if issue.get("outcome") == "UNRESOLVED"
            )
            print(f"  unresolved    : {unresolved}")
        else:
            print("  VERIFY FAILED:", verify.status_code, verify.text[:200])
            failures += 1

        reviews = client.get(f"{base}/projects/{project_id}/reviews")
        if reviews.status_code == 200:
            print(f"  review items  : {len(reviews.json())}")

        refreshed = client.get(f"{base}/documents/{document_id}").json()
        stable = [
            (f["field_name"], f.get("normalized_value"))
            for f in refreshed["extracted_fields"]
        ] == [
            (f["field_name"], f.get("normalized_value")) for f in detail["extracted_fields"]
        ]
        print(f"  refresh stable: {stable}  type stable: {refreshed['document_type'] == detail['document_type']}")
        if not stable:
            failures += 1

    client.close()
    print("=" * 78)
    print("LIVE PLATFORM FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
