from __future__ import annotations

import json
from datetime import UTC, datetime

from world_studio.data.database import Database
from world_studio.domain.world import World


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


class WorldRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_world(self, world: World) -> World:
        now = utc_now_iso()
        with self._database.connect() as connection:
            existing = connection.execute(
                "SELECT id, created_utc FROM worlds WHERE ext_ref = ?",
                (world.ext_ref,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE worlds
                    SET name = ?, description = ?, active_ruleset_ref = ?, is_locked = ?,
                        metadata_json = ?, updated_utc = ?
                    WHERE ext_ref = ?
                    """,
                    (
                        world.name,
                        world.description,
                        world.active_ruleset_ref,
                        int(world.is_locked),
                        json.dumps(world.metadata),
                        now,
                        world.ext_ref,
                    ),
                )
                world.id = existing["id"]
                world.created_utc = _parse_datetime(existing["created_utc"])
                world.updated_utc = _parse_datetime(now)
                return world

            cursor = connection.execute(
                """
                INSERT INTO worlds (
                    ext_ref, name, description, active_ruleset_ref, is_locked, metadata_json,
                    created_utc, updated_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    world.ext_ref,
                    world.name,
                    world.description,
                    world.active_ruleset_ref,
                    int(world.is_locked),
                    json.dumps(world.metadata),
                    now,
                    now,
                ),
            )
        world.id = int(cursor.lastrowid)
        world.created_utc = _parse_datetime(now)
        world.updated_utc = _parse_datetime(now)
        return world

    def get_world(self, ext_ref: str) -> World | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM worlds WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
        if row is None:
            return None
        return World(
            id=row["id"],
            ext_ref=row["ext_ref"],
            name=row["name"],
            description=row["description"],
            active_ruleset_ref=row["active_ruleset_ref"],
            is_locked=bool(row["is_locked"]),
            metadata=json.loads(row["metadata_json"]),
            created_utc=_parse_datetime(row["created_utc"]),
            updated_utc=_parse_datetime(row["updated_utc"]),
        )

    def list_worlds(self) -> list[World]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM worlds ORDER BY updated_utc DESC, name ASC"
            ).fetchall()
        return [
            World(
                id=row["id"],
                ext_ref=row["ext_ref"],
                name=row["name"],
                description=row["description"],
                active_ruleset_ref=row["active_ruleset_ref"],
                is_locked=bool(row["is_locked"]),
                metadata=json.loads(row["metadata_json"]),
                created_utc=_parse_datetime(row["created_utc"]),
                updated_utc=_parse_datetime(row["updated_utc"]),
            )
            for row in rows
        ]
