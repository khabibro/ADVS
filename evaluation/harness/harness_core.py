"""Shared machinery for the evaluation harness (variant runs and error injection).

Everything runs through the real production service path (the FastAPI routes
the frontend calls) against a scratch SQLite database created for the run.

Corpora
-------
`dev`      evaluation/datasets/synthetic/test_variants/   (development set)
`holdout`  evaluation/datasets/synthetic/holdout/         (final judgement only)

The hold-out corpus is refused unless ADVS_FINAL_JUDGEMENT=1 is set, and every
hold-out run is appended to evaluation/phase_d/holdout_runs.log.

OCR record / replay
-------------------
`ocr_mode="record"` runs the real OCR and stores each document's pages under
`ocr_cache/<sha256>.json`; `ocr_mode="replay"` serves them back (optionally
through an injector that edits observations). Everything downstream of the OCR
provider runs unchanged in both modes.
"""

from __future__ import annotations

import asyncio
import dataclasses
import datetime as _dt
import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC = REPO_ROOT / "evaluation" / "datasets" / "synthetic"
CORPORA = {"dev": SYNTHETIC / "test_variants", "holdout": SYNTHETIC / "holdout"}
HOLDOUT_LOG = REPO_ROOT / "evaluation" / "phase_d" / "holdout_runs.log"

EXT_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def guard_corpus(corpus: str, argv: list[str] | None = None) -> Path:
    """Return the corpus root, refusing the hold-out set outside final judgement."""
    root = CORPORA[corpus]
    if corpus == "holdout":
        if os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
            raise SystemExit(
                "Refusing to touch the hold-out set: it is for final judgement only "
                "(set ADVS_FINAL_JUDGEMENT=1)."
            )
        HOLDOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HOLDOUT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "at": _dt.datetime.now(_dt.UTC).isoformat(),
                        "git_head": git_head(),
                        "argv": argv if argv is not None else sys.argv,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return root


def guard_path(path: Path) -> Path:
    if "holdout" in path.resolve().parts and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
        raise SystemExit(f"Refusing to open a hold-out path outside final judgement: {path}")
    return path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(guard_path(path).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------
# OCR record / replay
# ----------------------------------------------------------------------------


def page_to_dict(page: Any) -> dict[str, Any]:
    return dataclasses.asdict(page)


def page_from_dict(data: dict[str, Any]) -> Any:
    from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

    lines = []
    for item in data.get("lines", []):
        box = item.get("bounding_box")
        polygon = item.get("polygon")
        lines.append(
            OCRLine(
                text=item["text"],
                confidence=item.get("confidence"),
                bounding_box=BoundingBox(**box) if box else None,
                polygon=tuple(tuple(point) for point in polygon) if polygon else None,
                detection_confidence=item.get("detection_confidence"),
                orientation_degrees=item.get("orientation_degrees"),
            )
        )
    return OCRPage(
        page_number=data["page_number"],
        text=data["text"],
        lines=lines,
        confidence=data.get("confidence"),
        duration_ms=data.get("duration_ms", 0),
        metadata=data.get("metadata", {}),
    )


class OCRCacheProvider:
    """Wraps the real provider (record) or serves cached pages (replay)."""

    def __init__(
        self,
        real_provider_factory: Callable[[Any], Any],
        cache_dir: Path,
        mode: str,
        injector: Callable[[str, list[Any]], list[Any]] | None = None,
    ) -> None:
        self.factory = real_provider_factory
        self.cache_dir = cache_dir
        self.mode = mode
        self.injector = injector
        self.reading_editor: Callable[[str, str, str | None], str | None] | None = None
        self.stats = {"hits": 0, "recorded": 0, "second_pass_hits": 0, "second_pass_computed": 0}
        cache_dir.mkdir(parents=True, exist_ok=True)

    def provider_for(self, settings: Any) -> Any:
        return self

    async def extract_document(self, path: Path, mime_type: str, original_filename: str = "") -> Any:
        from app.document_intelligence.ocr.models import OCRProviderError
        from app.core.errors import ProcessingErrorCode

        digest = sha256_file(path)
        cache_file = self.cache_dir / f"{digest}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            self.stats["hits"] += 1
        elif self.mode == "record":
            real = self.factory(None)
            try:
                pages = await real.extract_document(path, mime_type, original_filename)
                data = {"pages": [page_to_dict(page) for page in pages]}
            except OCRProviderError as exc:
                data = {"error": exc.code.value}
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.stats["recorded"] += 1
        else:
            raise RuntimeError(f"OCR cache miss in replay mode: {path.name}")
        if "error" in data:
            raise OCRProviderError(ProcessingErrorCode(data["error"]))
        pages = [page_from_dict(item) for item in data["pages"]]
        if self.injector is not None:
            pages = self.injector(digest, pages)
        return pages

    async def read_regions(self, path: Path, mime_type: str, requests: list[Any]) -> list[Any]:
        """Second-pass region reads: served from / stored in the cache (a miss runs the real
        provider once). `reading_editor` lets the injection suite corrupt a reading."""
        from app.document_intelligence.ocr.models import RegionReading

        digest = sha256_file(path)
        folder = self.cache_dir / "second_pass"
        folder.mkdir(parents=True, exist_ok=True)
        readings = []
        for request in requests:
            box = request.bbox
            token = f"{digest}|{request.field_name}|{request.page_number}|{round(box.x)},{round(box.y)},{round(box.width)},{round(box.height)}"
            file = folder / (hashlib.sha256(token.encode()).hexdigest() + ".json")
            if file.exists():
                data = json.loads(file.read_text(encoding="utf-8"))
                self.stats["second_pass_hits"] += 1
            else:
                real = self.factory(None)
                reading = (await real.read_regions(path, mime_type, [request]))[0]
                data = dataclasses.asdict(reading)
                file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                self.stats["second_pass_computed"] += 1
            text = data.get("text")
            if self.reading_editor is not None:
                text = self.reading_editor(digest, request.field_name, text)
            readings.append(
                RegionReading(
                    field_name=request.field_name,
                    page_number=data.get("page_number", request.page_number),
                    text=text,
                    confidence=data.get("confidence"),
                    preprocess=data.get("preprocess", ""),
                )
            )
        return readings

    async def health_check(self) -> bool:
        return True


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------


class Runner:
    def __init__(
        self,
        corpus: str,
        *,
        ocr_mode: str = "live",
        ocr_cache_dir: Path | None = None,
        injector: Callable[[str, list[Any]], list[Any]] | None = None,
        project_values: bool = False,
        extra_env: dict[str, str] | None = None,
        skip_ocr: bool = False,
    ) -> None:
        self.corpus = corpus
        self.root = guard_corpus(corpus)
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.submission_date = self.manifest["submission_date"]
        self.project_values = project_values
        self.skip_ocr = skip_ocr
        self.by_file = {entry["file"]: entry for entry in self.manifest["files"]}
        self.temp_root = Path(tempfile.mkdtemp(prefix="advs_harness_", dir=str(REPO_ROOT / "evaluation" / "harness")))
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_root / 'harness.db'}"
        os.environ["STORAGE_PATH"] = str(self.temp_root / "storage")
        os.environ["OCR_PROVIDER"] = "paddle"
        os.environ["APP_ENV"] = "test"
        os.environ["LOG_LEVEL"] = "WARNING"
        os.environ.setdefault(
            "PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps" / "api" / "storage" / "paddleocr-cache")
        )
        for key, value in (extra_env or {}).items():
            os.environ[key.removeprefix("ADVS_")] = value  # ADVS_AUTO_ACCEPT_STRATEGY -> AUTO_ACCEPT_STRATEGY
        sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from app.db.session import Base, SessionLocal
        from app.db.session import engine as db_engine
        from app.main import app
        from app.models.entities import Checklist

        self._select = select
        self.SessionLocal = SessionLocal
        self.Checklist = Checklist
        Base.metadata.create_all(db_engine)
        seed = runpy.run_path(str(REPO_ROOT / "scripts" / "seed.py"))
        seed["main"]()
        with SessionLocal() as db:
            self.business_id = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검")).id
            self.student_id = db.scalar(select(Checklist).where(Checklist.name == "학생 제출서류 점검")).id
        self.partial_id = self._make_partial_checklist()

        self.ocr_cache: OCRCacheProvider | None = None
        if ocr_cache_dir is not None and ocr_mode in ("record", "replay"):
            import app.services.processing as processing_module
            from app.document_intelligence.ocr.providers import get_ocr_provider as real_factory

            self.ocr_cache = OCRCacheProvider(
                lambda settings: real_factory(processing_module.get_settings()),
                ocr_cache_dir,
                ocr_mode,
                injector,
            )
            processing_module.get_ocr_provider = lambda settings: self.ocr_cache  # type: ignore[assignment]
        self.client = TestClient(app, raise_server_exceptions=False)
        self.client.__enter__()

    # -- setup helpers -----------------------------------------------------

    def _make_partial_checklist(self) -> Any:
        """Default business checklist plus one REQUIRED_FIELD(workplace_name) rule on the
        social-insurance requirement (the F-001 probe used by the 'run twice' sets)."""
        from sqlalchemy import select

        from app.core.domain import DocumentType, RuleType, Severity
        from app.models.entities import Checklist, DocumentRequirement, ValidationRule

        with self.SessionLocal() as db:
            base = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검"))
            scratch = Checklist(
                name="scratch: single REQUIRED_FIELD(workplace_name) on social insurance",
                description="Harness probe for F-001, not used in production.",
                is_active=True,
            )
            db.add(scratch)
            db.flush()
            for requirement in base.requirements:
                new_requirement = DocumentRequirement(
                    checklist_id=scratch.id,
                    document_type=requirement.document_type,
                    required=requirement.required,
                )
                db.add(new_requirement)
                db.flush()
                for rule in requirement.rules:
                    db.add(
                        ValidationRule(
                            requirement_id=new_requirement.id,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            params=dict(rule.params),
                        )
                    )
                if requirement.document_type == DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE.value:
                    db.add(
                        ValidationRule(
                            requirement_id=new_requirement.id,
                            rule_type=RuleType.REQUIRED_FIELD.value,
                            severity=Severity.WARNING.value,
                            params={"field": "workplace_name"},
                        )
                    )
            db.commit()
            return scratch.id

    def project_payload(self, workflow: str, checklist_id: Any, name: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "workflow_id": str(checklist_id)}
        if self.project_values:
            entities = self.manifest.get("fictional_entities", {})
            if workflow == "business":
                payload["company_name"] = entities.get("company_A", {}).get("full")
            else:
                payload["applicant_name"] = entities.get("student", {}).get("name")
        return payload

    def make_project(self, workflow: str, checklist_id: Any, name: str) -> str:
        response = self.client.post("/api/v1/projects", json=self.project_payload(workflow, checklist_id, name))
        response.raise_for_status()
        return response.json()["id"]

    # -- processing ---------------------------------------------------------

    def upload_and_process(self, project_id: str, files: list[tuple[str, Path]]) -> list[dict[str, Any]]:
        """files: (relative-path-for-the-record, absolute path)."""
        results = []
        for rel, path in files:
            started = time.perf_counter()
            guard_path(path)
            mime = EXT_MIME.get(path.suffix.lower().lstrip("."), "application/octet-stream")
            with path.open("rb") as handle:
                upload = self.client.post(
                    f"/api/v1/projects/{project_id}/documents",
                    files={"file": (nfc(path.name), handle, mime)},
                )
            record: dict[str, Any] = {"file": rel, "upload_status": upload.status_code}
            if upload.status_code != 201:
                try:
                    record["upload_error"] = upload.json()
                except Exception:
                    record["upload_error"] = upload.text
                results.append(record)
                continue
            document_id = upload.json()["id"]
            record["document_id"] = document_id
            record["sha256"] = sha256_file(path)
            process = self.client.post(f"/api/v1/documents/{document_id}/process")
            record["process_status_code"] = process.status_code
            if process.status_code == 200:
                body = process.json()
                record["processing_status"] = body.get("processing_status")
                record["processing_error_code"] = body.get("processing_error_code")
                record["predicted_document_type"] = body.get("document_type")
            record["process_ms"] = round((time.perf_counter() - started) * 1000, 1)
            results.append(record)
        return results

    def capture_details(self, file_results: list[dict[str, Any]]) -> None:
        """Document details are read after *every* document of the submission is processed (and
        verified), because auto-acceptance corroborates across documents."""
        for record in file_results:
            document_id = record.get("document_id")
            if not document_id:
                continue
            detail = self.client.get(f"/api/v1/documents/{document_id}")
            if detail.status_code == 200:
                self._capture_detail(record, detail.json())

    @staticmethod
    def _capture_detail(record: dict[str, Any], detail: dict[str, Any]) -> None:
        record["classification_confidence"] = detail.get("classification_confidence")
        record["classification_needs_review"] = (detail.get("classification_meta") or {}).get(
            "needs_review"
        )
        record["classification_meta"] = detail.get("classification_meta")
        record["overall_status"] = detail.get("overall_status")
        record["page_count"] = detail.get("page_count")
        fields: dict[str, Any] = {}
        for item in detail.get("extracted_fields", []):
            evidence = item.get("evidence") or []
            fields[item["field_name"]] = {
                "value": item.get("effective_normalized_value"),
                "machine_value": item.get("normalized_value"),
                "confidence": item.get("confidence"),
                "source": item.get("effective_source"),
                "evidence_state": item.get("evidence_assessment"),
                "needs_review": item.get("needs_review"),
                "evidence_kinds": sorted({e.get("source_kind") for e in evidence}),
                "auto_acceptance": item.get("auto_acceptance"),
                "extraction_method": item.get("extraction_method"),
            }
        record["fields"] = fields
        record["issues"] = [r["code"] for r in detail.get("validation_results", []) if not r["passed"]]

    def verify(self, project_id: str, evaluation_date: str | None = None) -> dict[str, Any]:
        response = self.client.post(
            f"/api/v1/projects/{project_id}/verify",
            json={"evaluation_date": evaluation_date or self.submission_date},
        )
        if response.status_code != 200:
            return {"error": response.text}
        body = response.json()
        return {
            "status": body.get("status"),
            "issue_codes": [issue.get("code") for issue in body.get("issues", [])],
            "issues": body.get("issues", []),
            "notices": body.get("notices", []),
        }

    def run_submission(
        self, workflow: str, checklist_id: Any, name: str, files: list[tuple[str, Path]]
    ) -> dict[str, Any]:
        started = time.perf_counter()
        project_id = self.make_project(workflow, checklist_id, name)
        file_results = self.upload_and_process(project_id, files)
        verification = self.verify(project_id)
        self.capture_details(file_results)
        return {
            "project_id": project_id,
            "actual_submission_status": verification.get("status"),
            "actual_issue_codes": verification.get("issue_codes"),
            "notices": verification.get("notices"),
            "files": file_results,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }

    # -- corpus ------------------------------------------------------------

    def run_corpus(
        self,
        versions: list[str],
        wanted_sets: set[str] | None = None,
        include_formats: bool = True,
        log: Callable[[str], None] = print,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {
            "corpus": self.corpus,
            "manifest_submission_date": self.submission_date,
            "versions_run": versions,
            "project_values": self.project_values,
            "git_head": git_head(),
            "sets": {},
            "format_sets": {},
        }
        scenarios = self.manifest["business_sets"] + self.manifest["student_sets"]
        for scenario in scenarios:
            set_id = scenario["set_id"]
            if wanted_sets is not None and set_id not in wanted_sets:
                continue
            workflow = scenario["workflow"]
            checklist_id = self.business_id if workflow == "business" else self.student_id
            results["sets"][set_id] = {"title": scenario["title"], "versions": {}}
            log(f"=== {set_id} — {scenario['title']} ===")
            for version in versions:
                rels = scenario["files"].get(version, [])
                if not rels:
                    continue
                files = [(rel, self.root / rel) for rel in rels]
                entry = self.run_submission(workflow, checklist_id, f"{set_id}-{version}", files)
                results["sets"][set_id]["versions"][version] = entry
                log(f"  {version}: actual={entry['actual_submission_status']} ({entry['elapsed_seconds']}s)")
            if "run twice" in str(scenario.get("checklist_condition", "")) and "digital" in versions:
                files = [(rel, self.root / rel) for rel in scenario["files"]["digital"]]
                entry = self.run_submission(workflow, self.partial_id, f"{set_id}-partial", files)
                entry["checklist"] = "single REQUIRED_FIELD(workplace_name) on social insurance"
                results["sets"][set_id]["versions"]["digital_partial_checklist"] = entry
                log(f"  digital_partial_checklist: actual={entry['actual_submission_status']}")
        if include_formats:
            for fset in self.manifest["format_sets"]:
                set_id = fset["set_id"]
                if wanted_sets is not None and set_id not in wanted_sets:
                    continue
                log(f"=== {set_id} (format) ===")
                started = time.perf_counter()
                project_id = self.make_project("business", self.business_id, f"{set_id}-format")
                file_results = self.upload_and_process(project_id, [(r, self.root / r) for r in fset["files"]])
                self.capture_details(file_results)
                results["format_sets"][set_id] = {
                    "title": fset["title"],
                    "expected": fset["expected"],
                    "files": file_results,
                    "elapsed_seconds": round(time.perf_counter() - started, 1),
                }
        return results

    def close(self) -> None:
        import shutil

        self.client.__exit__(None, None, None)
        shutil.rmtree(self.temp_root, ignore_errors=True)


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)
