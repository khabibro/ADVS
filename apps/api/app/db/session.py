from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_concurrency(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        """Readers must not block the analysis writer (and vice versa) on the SQLite deployment."""
        cursor = dbapi_connection.cursor()
        try:
            if ":memory:" not in str(engine.url):
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
