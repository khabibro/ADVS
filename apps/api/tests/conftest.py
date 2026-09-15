"""Test-session bootstrap for API integration tests.

Must set DATABASE_URL / STORAGE_PATH *before* app.db.session (which builds
the SQLAlchemy engine at import time) or app.core.config are imported by any
test module, so this runs at conftest collection time -- before pytest
imports the individual test files.
"""

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="advs_api_tests_")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DIR}/integration.db")
os.environ.setdefault("STORAGE_PATH", f"{_TMP_DIR}/storage")
os.environ.setdefault("OCR_PROVIDER", "mock")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.db.session import get_db as real_get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[real_get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
