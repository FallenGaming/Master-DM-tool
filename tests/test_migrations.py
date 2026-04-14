from __future__ import annotations

from pathlib import Path

from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations


def test_migrations_create_worlds_table(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    applied = run_migrations(db)
    assert "0001_initial_schema" in applied

    with db.connect() as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='worlds'"
        ).fetchone()
    assert row is not None


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    run_migrations(db)
    applied_second = run_migrations(db)
    assert applied_second == []
