"""P2.1 multipage and concurrency validation.

Multipage: 1, 3 and 6 page PDFs built by repeating one real page, pushed
through the production upload/process path.

Concurrency: two different documents processed simultaneously, in two
different projects, from two threads.

Both write only to the gitignored runtime directory. Neither private content
nor filenames leave this process.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = REPO_ROOT / "evaluation/private_runtime/p2_1"
WORK_DIR = REPO_ROOT / "evaluation/backend_round2/work"

sys.path.insert(0, str(REPO_ROOT / "apps/api"))
sys.path.insert(0, str(REPO_ROOT / "evaluation/p2_1_ocr_diagnosis"))


def source_pdf() -> Path:
    """A real multi-text PDF from the private corpus, located by content hash."""
    import hashlib

    fingerprints = json.loads((WORK_DIR / "p2_original_fingerprints.json").read_text())[
        "records"
    ]
    root = Path("~/Desktop/Samples").expanduser()
    for row in fingerprints:
        for path in root.iterdir():
            if path.suffix.lower() != ".pdf" or not path.is_file():
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]:
                return path
    raise SystemExit("no real PDF found in the private corpus")


def build_pdf(pages: int, out: Path) -> Path:
    import pymupdf

    original = pymupdf.open(source_pdf())
    target = pymupdf.open()
    for index in range(pages):
        target.insert_pdf(original, from_page=0, to_page=0)
    target.save(out)
    target.close()
    original.close()
    return out


def main() -> int:
    from fastapi.testclient import TestClient
    from run_workflow_probe import boot

    results: dict = {"multipage": [], "concurrency": []}
    root = Path(tempfile.mkdtemp(prefix="advs_p21_mp_"))
    try:
        storage = root / "app"
        storage.mkdir()
        app = boot("paddle", storage)
        client = TestClient(app)
        workflow_id = client.get("/api/v1/workflows").json()[0]["id"]

        for pages in (1, 3, 6):
            pdf = build_pdf(pages, root / f"mp{pages}.pdf")
            project_id = client.post(
                "/api/v1/projects",
                json={"name": f"p21-mp-{pages}", "workflow_id": str(workflow_id)},
            ).json()["id"]
            upload_started = time.perf_counter()
            with pdf.open("rb") as handle:
                response = client.post(
                    f"/api/v1/projects/{project_id}/documents",
                    files={"file": (f"probe{pages}p.pdf", handle, "application/pdf")},
                )
            upload_ms = int((time.perf_counter() - upload_started) * 1000)
            entry: dict = {
                "page_count": pages,
                "upload_status": response.status_code,
                "upload_ms": upload_ms,
            }
            if response.status_code < 400:
                document_id = response.json()["id"]
                started = time.perf_counter()
                processed = client.post(f"/api/v1/documents/{document_id}/process")
                elapsed = time.perf_counter() - started
                detail = client.get(f"/api/v1/documents/{document_id}").json()
                entry.update(
                    {
                        "process_ms": int(elapsed * 1000),
                        "ms_per_page": round(elapsed * 1000 / pages, 1),
                        "process_status_code": processed.status_code,
                        "processing_status": detail.get("processing_status"),
                        "error_code": detail.get("error_code"),
                        "document_type": detail.get("document_type"),
                        "field_count": len(detail.get("extracted_fields", [])),
                        "non_null_fields": sum(
                            1
                            for f in detail.get("extracted_fields", [])
                            if f.get("normalized_value")
                        ),
                    }
                )
                entry["completed"] = detail.get("processing_status") == "COMPLETED"
            results["multipage"].append(entry)
            print(f"multipage {pages}p -> {entry}", flush=True)

        # ---------------- concurrency: two documents, two projects ----------
        files = sorted(
            p
            for p in Path("~/Desktop/Samples").expanduser().iterdir()
            if p.is_file()
            and p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        )
        pair = files[:2]
        results["concurrency"].append(run_concurrent_pair(client, workflow_id, pair))
        print(f"concurrency -> {results['concurrency'][0]}", flush=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    (RUNTIME / "multipage_concurrency_private.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


def run_concurrent_pair(client, workflow_id, pair) -> dict:
    """Two documents, two projects, two threads, measured end to end."""
    from fastapi.testclient import TestClient

    outcomes: dict = {}
    barrier = threading.Barrier(len(pair))

    def worker(index: int, path: Path) -> None:
        local = TestClient(client.app)
        project_id = local.post(
            "/api/v1/projects",
            json={
                "name": f"p21-conc-{index}-{uuid.uuid4().hex[:6]}",
                "workflow_id": str(workflow_id),
            },
        ).json()["id"]
        barrier.wait()
        with path.open("rb") as handle:
            response = local.post(
                f"/api/v1/projects/{project_id}/documents",
                files={
                    "file": (
                        f"conc{index}{path.suffix}",
                        handle,
                        "application/octet-stream",
                    )
                },
            )
        if response.status_code >= 400:
            outcomes[index] = {"upload_status": response.status_code}
            return
        document_id = response.json()["id"]
        started = time.perf_counter()
        processed = local.post(f"/api/v1/documents/{document_id}/process")
        elapsed = time.perf_counter() - started
        detail = local.get(f"/api/v1/documents/{document_id}").json()
        rows = local.get(f"/api/v1/projects/{project_id}/documents").json()
        outcomes[index] = {
            "upload_status": response.status_code,
            "process_status_code": processed.status_code,
            "processing_status": detail.get("processing_status"),
            "document_type": detail.get("document_type"),
            "error_code": detail.get("error_code"),
            "ms": int(elapsed * 1000),
            "field_count": len(detail.get("extracted_fields", [])),
            "non_null_fields": sum(
                1
                for f in detail.get("extracted_fields", [])
                if f.get("normalized_value")
            ),
            "documents_in_project": len(rows) if isinstance(rows, list) else -1,
        }

    threads = [threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(pair)]
    overall = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall = time.perf_counter() - overall

    sequential_estimate = sum(entry.get("ms", 0) for entry in outcomes.values())
    statuses = [entry.get("processing_status") for entry in outcomes.values()]
    return {
        "documents": len(pair),
        "projects": len(pair),
        "wall_ms": int(wall * 1000),
        "sum_of_individual_ms": sequential_estimate,
        "overlap_observed": wall * 1000 < sequential_estimate * 0.95,
        "outcomes": outcomes,
        "all_completed": bool(statuses)
        and all(status == "COMPLETED" for status in statuses),
        "worker_count": len(outcomes),
        "duplicate_rows": any(
            entry.get("documents_in_project", 0) != 1 for entry in outcomes.values()
        ),
        "errors": [
            entry.get("error_code")
            for entry in outcomes.values()
            if entry.get("error_code")
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
