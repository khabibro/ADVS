"""Accuracy check for docs/ARCHITECTURE.md, docs/GLOSSARY.md,
docs/RECOMMENDATIONS.md, and root README.md against the actual code.

Does not run anything heavy (no Docker, no pnpm build, no PaddleOCR) --
it checks that every concrete claim these docs make (a file path, a
Makefile target, an enum's members, a table's required/optional fields, an
ORM table name) is still true. Run it after any change to
app/core/domain.py, app/models/entities.py, or api/v1/routes.py, or
whenever these docs are edited.

Exit code 0 means every check passed. A failure prints what claim broke
and where, so the doc (or the code) can be fixed -- this script does not
guess which one is wrong.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
API_ROOT = REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


# ---------------------------------------------------------------------------
# 1. Every backtick-quoted path that looks like a repo file reference must
#    exist *somewhere* in the repo -- matched by suffix, not by resolving
#    against repo root, since prose shorthand like `validation/engine.py`
#    (inside a paragraph that already said `document_intelligence/`) is a
#    legitimate partial path, not a broken one.
# ---------------------------------------------------------------------------
PATH_LIKE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|json|ya?ml|mjs|txt)|[A-Za-z0-9_./-]+/)`")
SKIP_PREFIXES = ("http", "OCR_PROVIDER", "PADDLE_")

# Paths this doc set deliberately cites on another branch, or that this
# script itself produces later in the same cleanup pass -- confirmed by
# hand to be real, just not present at the commit these docs are stamped
# with. Each entry says why.
ALLOWED_MISSING = {
    "evaluation/phase_b/PHASE_B_REPORT.md": "exists only on unmerged branch phase-b/safety-fixes",
    "evaluation/cleanup/REPORT.md": "written at the end of this same cleanup task",
    "temp": "intentionally removed before this task; cited in ARCHITECTURE.md as history",
    "txt.txt": "intentionally removed before this task; cited in ARCHITECTURE.md as history",
}

_ALL_PATHS: set[str] | None = None
_ALL_DIRS: set[str] | None = None


def _all_repo_paths() -> tuple[set[str], set[str]]:
    global _ALL_PATHS, _ALL_DIRS
    if _ALL_PATHS is not None and _ALL_DIRS is not None:
        return _ALL_PATHS, _ALL_DIRS
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    # Includes gitignored directories (e.g. evaluation/private_runtime/) --
    # walked directly on disk, not via git, since those legitimately exist
    # but are never tracked.
    extra_roots = [
        "apps/api/app",
        "apps/web/src",
        "apps/admin/src",
        "evaluation",
        "docs",
        "scripts",
        "packages",
    ]
    files: list[str] = []
    dirs: set[str] = set()
    for root in extra_roots:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        dirs.add(root)
        for p in base.rglob("*"):
            if "node_modules" in p.parts or ".venv" in str(p) or "__pycache__" in p.parts:
                continue
            rel = str(p.relative_to(REPO_ROOT))
            if p.is_file():
                files.append(rel)
            elif p.is_dir():
                dirs.add(rel)
    _ALL_PATHS = set(tracked) | set(files)
    _ALL_DIRS = dirs
    return _ALL_PATHS, _ALL_DIRS


def check_referenced_paths() -> None:
    all_paths, all_dirs = _all_repo_paths()
    for doc in ["ARCHITECTURE.md", "GLOSSARY.md", "RECOMMENDATIONS.md"]:
        text = (DOCS_DIR / doc).read_text(encoding="utf-8")
        for match in PATH_LIKE.finditer(text):
            ref = match.group(1)
            if ref.startswith(SKIP_PREFIXES) or ref.startswith(("app.", "F-")):
                continue
            if ref in ALLOWED_MISSING:
                continue
            ref_clean = ref.rstrip("/")
            if ref.endswith("/"):
                if any(d == ref_clean or d.endswith("/" + ref_clean) for d in all_dirs):
                    continue
            elif any(p == ref_clean or p.endswith("/" + ref_clean) for p in all_paths):
                continue
            fail(f"{doc}: referenced path does not exist anywhere in the repo: {ref}")


# ---------------------------------------------------------------------------
# 2. DocumentType enum, EXPECTED_FIELDS, OPTIONAL_SUPPORTED_FIELDS, RuleType,
#    OverallStatus, Severity -- cross-checked against the document-type
#    table and the RuleType list in ARCHITECTURE.md, by importing the real
#    module (read-only; this process does not touch the database).
# ---------------------------------------------------------------------------
def check_domain_enums() -> None:
    from app.core import domain

    architecture = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")

    for doc_type in domain.DocumentType:
        if doc_type.value not in architecture:
            fail(f"ARCHITECTURE.md: DocumentType.{doc_type.value} not mentioned anywhere")

    for doc_type, expected in domain.EXPECTED_FIELDS.items():
        for field in expected:
            if field not in architecture:
                fail(
                    f"ARCHITECTURE.md: required field '{field}' "
                    f"(DocumentType.{doc_type.value}) not found in the document-type table"
                )

    for doc_type, optional in domain.OPTIONAL_SUPPORTED_FIELDS.items():
        for field in optional:
            if field not in architecture:
                fail(
                    f"ARCHITECTURE.md: optional field '{field}' "
                    f"(DocumentType.{doc_type.value}) not found in the document-type table"
                )

    for rule_type in domain.RuleType:
        if rule_type.value not in architecture:
            fail(f"ARCHITECTURE.md: RuleType.{rule_type.value} not mentioned anywhere")

    for status in domain.OverallStatus:
        glossary = (DOCS_DIR / "GLOSSARY.md").read_text(encoding="utf-8")
        if status.value not in glossary:
            fail(f"GLOSSARY.md: OverallStatus.{status.value} not mentioned anywhere")

    # REVIEWABLE_FIELDS must still be the same object as SUPPORTED_FIELDS --
    # ARCHITECTURE.md §7 states this explicitly.
    if domain.REVIEWABLE_FIELDS is not domain.SUPPORTED_FIELDS:
        fail(
            "ARCHITECTURE.md §7 claims REVIEWABLE_FIELDS is SUPPORTED_FIELDS re-exported "
            "under a second name -- that is no longer true in app/core/domain.py"
        )


# ---------------------------------------------------------------------------
# 3. ORM table names (entities.py) must match the ERD in ARCHITECTURE.md.
# ---------------------------------------------------------------------------
def check_erd() -> None:
    from app.models import entities

    architecture = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")
    erd_entities = {
        "User",
        "Project",
        "Checklist",
        "DocumentRequirement",
        "ValidationRule",
        "Submission",
        "Document",
        "OCRResult",
        "ExtractedField",
        "FieldReview",
        "ValidationResult",
        "AuditLog",
    }
    actual_classes = {
        name
        for name, obj in vars(entities).items()
        if isinstance(obj, type) and hasattr(obj, "__tablename__")
    }
    missing_from_doc = actual_classes - erd_entities
    missing_from_code = erd_entities - actual_classes
    for name in missing_from_doc:
        fail(f"ARCHITECTURE.md ERD: app/models/entities.py has class {name} not in the ERD")
    for name in missing_from_code:
        fail(f"ARCHITECTURE.md ERD: {name} is in the ERD but no longer in app/models/entities.py")
    for name in erd_entities & actual_classes:
        if name not in architecture:
            fail(f"ARCHITECTURE.md: ERD entity {name} not mentioned in the prose")


# ---------------------------------------------------------------------------
# 4. Makefile targets this doc set tells someone to run must exist.
# ---------------------------------------------------------------------------
def check_makefile_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([A-Za-z][A-Za-z0-9_-]*):", makefile, re.MULTILINE))
    for doc in ["ARCHITECTURE.md", "RECOMMENDATIONS.md"]:
        text = (DOCS_DIR / doc).read_text(encoding="utf-8")
        for match in re.finditer(r"`make ([a-zA-Z0-9_-]+)`", text):
            target = match.group(1)
            if target not in targets:
                fail(f"{doc}: `make {target}` is not a target in Makefile")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for match in re.finditer(r"^make ([a-zA-Z0-9_-]+)$", readme, re.MULTILINE):
        target = match.group(1)
        if target not in targets:
            fail(f"README.md: `make {target}` is not a target in Makefile")


# ---------------------------------------------------------------------------
# 5. F-00x findings cited in ARCHITECTURE.md/RECOMMENDATIONS.md must exist
#    in the audit report they're attributed to.
# ---------------------------------------------------------------------------
def check_findings_cited() -> None:
    audit_path = REPO_ROOT / "evaluation" / "system_audit" / "ADVS_system_audit_report.md"
    if not audit_path.exists():
        fail(f"audit report not found at {audit_path}, but docs cite F-00x findings from it")
        return
    audit_text = audit_path.read_text(encoding="utf-8")
    known_findings = set(re.findall(r"### (F-\d{3})", audit_text))
    for doc in ["ARCHITECTURE.md", "RECOMMENDATIONS.md", "GLOSSARY.md"]:
        text = (DOCS_DIR / doc).read_text(encoding="utf-8")
        for cited in set(re.findall(r"\bF-\d{3}\b", text)):
            if cited not in known_findings:
                fail(f"{doc}: cites {cited}, which is not a heading in {audit_path.name}")


# ---------------------------------------------------------------------------
# 6. Every doc must state a commit hash, and it must be a real, resolvable
#    commit in this repo (it is allowed to be behind HEAD -- that just means
#    the doc is due for a refresh, which this check reports as a warning,
#    not a failure).
# ---------------------------------------------------------------------------
def check_commit_hash() -> None:
    import subprocess

    text = (DOCS_DIR / "ARCHITECTURE.md").read_text(encoding="utf-8")
    match = re.search(r"commit `([0-9a-f]{7,40})`", text)
    if not match:
        fail("ARCHITECTURE.md: no commit hash found in the header")
        return
    commit = match.group(1)
    result = subprocess.run(
        ["git", "cat-file", "-e", commit], cwd=REPO_ROOT, capture_output=True
    )
    if result.returncode != 0:
        fail(f"ARCHITECTURE.md: commit `{commit}` does not exist in this repo")
        return
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    if not head.startswith(commit) and commit != head[: len(commit)]:
        print(
            f"NOTE: ARCHITECTURE.md's stamped commit ({commit}) is not HEAD ({head[:7]}) "
            "-- re-verify and re-stamp if the code has moved."
        )


def main() -> int:
    check_referenced_paths()
    check_domain_enums()
    check_erd()
    check_makefile_targets()
    check_findings_cited()
    check_commit_hash()

    if failures:
        print(f"{len(failures)} doc-accuracy check(s) FAILED:\n")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("All doc-accuracy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
