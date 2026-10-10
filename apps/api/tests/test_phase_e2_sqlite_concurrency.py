"""The SQLite deployment must let the screen's polling read while a document is being analysed."""

from sqlalchemy import text

from app.db.session import engine


def test_sqlite_uses_wal_and_waits_for_a_busy_database() -> None:
    assert engine.dialect.name == "sqlite"
    with engine.connect() as connection:
        assert str(connection.exec_driver_sql("PRAGMA journal_mode").scalar()).lower() == "wal"
        assert int(connection.exec_driver_sql("PRAGMA busy_timeout").scalar()) >= 30000


def test_a_reader_is_not_blocked_by_an_open_writer() -> None:
    with engine.connect() as setup:
        setup.execute(text("CREATE TABLE IF NOT EXISTS _wal_probe (id INTEGER)"))
        setup.execute(text("DELETE FROM _wal_probe"))
        setup.execute(text("INSERT INTO _wal_probe VALUES (1)"))
        setup.commit()
    writer = engine.connect()
    reader = engine.connect()
    try:
        writer.execute(text("INSERT INTO _wal_probe VALUES (2)"))  # open write transaction
        count = reader.execute(text("SELECT count(*) FROM _wal_probe")).scalar()
        assert count == 1  # reads the committed state immediately, does not wait or fail
    finally:
        writer.rollback()
        writer.close()
        reader.close()
        with engine.connect() as cleanup:
            cleanup.execute(text("DROP TABLE IF EXISTS _wal_probe"))
            cleanup.commit()
