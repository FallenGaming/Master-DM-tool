from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from world_studio.data.database import Database


@dataclass(frozen=True)
class Migration:
    version: str
    sql: str


MIGRATIONS: list[Migration] = [
    Migration(
        version="0001_initial_schema",
        sql="""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS worlds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            active_ruleset_ref TEXT,
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS continents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            name TEXT NOT NULL,
            climate_summary TEXT NOT NULL DEFAULT '',
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS empires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            continent_ref TEXT,
            name TEXT NOT NULL,
            governing_style TEXT NOT NULL DEFAULT '',
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kingdoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            empire_ref TEXT,
            name TEXT NOT NULL,
            stability_index REAL NOT NULL DEFAULT 0.5,
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            kingdom_ref TEXT,
            name TEXT NOT NULL,
            biome TEXT NOT NULL DEFAULT '',
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settlement_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            region_ref TEXT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            population INTEGER NOT NULL DEFAULT 100,
            resource_index REAL NOT NULL DEFAULT 0.5,
            safety_index REAL NOT NULL DEFAULT 0.5,
            x REAL NOT NULL DEFAULT 0,
            y REAL NOT NULL DEFAULT 0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS route_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            name TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            route_type TEXT NOT NULL DEFAULT 'road',
            travel_cost REAL NOT NULL DEFAULT 1.0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS points_of_interest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            region_ref TEXT,
            name TEXT NOT NULL,
            node_type TEXT NOT NULL,
            x REAL NOT NULL DEFAULT 0,
            y REAL NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT '',
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            lifespan_years INTEGER NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subraces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            race_ref TEXT NOT NULL,
            name TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS occupations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            rarity REAL NOT NULL DEFAULT 1.0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS traits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            polarity REAL NOT NULL DEFAULT 0.0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS npcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            display_name TEXT NOT NULL,
            age_years INTEGER NOT NULL,
            race_ref TEXT NOT NULL,
            subrace_ref TEXT,
            occupation_ref TEXT,
            residence_node_ref TEXT,
            health_index REAL NOT NULL DEFAULT 1.0,
            wealth_index REAL NOT NULL DEFAULT 0.5,
            is_locked INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            source_npc_ref TEXT NOT NULL,
            target_npc_ref TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            weight REAL NOT NULL,
            history_json TEXT NOT NULL DEFAULT '[]',
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS event_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            scope TEXT NOT NULL,
            trigger_mode TEXT NOT NULL,
            condition_expression_json TEXT NOT NULL DEFAULT '{}',
            modifiers_json TEXT NOT NULL DEFAULT '{}',
            chain_event_refs_json TEXT NOT NULL DEFAULT '[]',
            enabled INTEGER NOT NULL DEFAULT 1,
            is_locked INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS event_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            definition_ref TEXT NOT NULL,
            scope TEXT NOT NULL,
            target_ref TEXT,
            started_utc TEXT NOT NULL,
            ends_utc TEXT,
            resolved INTEGER NOT NULL DEFAULT 0,
            outcome_summary TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS rule_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            name TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            is_active INTEGER NOT NULL DEFAULT 0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            name TEXT NOT NULL,
            created_utc TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            checksum TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS simulation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_ref TEXT NOT NULL UNIQUE,
            world_ref TEXT NOT NULL,
            started_utc TEXT NOT NULL,
            finished_utc TEXT,
            simulated_days INTEGER NOT NULL,
            snapshot_ref TEXT,
            preview_only INTEGER NOT NULL DEFAULT 0,
            notes_json TEXT NOT NULL DEFAULT '[]'
        );
        """,
    )
]


def _ensure_migration_table(database: Database) -> None:
    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_utc TEXT NOT NULL
            )
            """
        )


def applied_versions(database: Database) -> set[str]:
    _ensure_migration_table(database)
    with database.connect() as connection:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def run_migrations(database: Database) -> list[str]:
    done = applied_versions(database)
    applied_now: list[str] = []
    now = datetime.now(UTC).isoformat()

    for migration in MIGRATIONS:
        if migration.version in done:
            continue
        with database.connect() as connection:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_utc) VALUES (?, ?)",
                (migration.version, now),
            )
        applied_now.append(migration.version)
    return applied_now


def run_cli_migrations() -> int:
    from world_studio.config import build_default_paths

    paths = build_default_paths()
    database = Database(paths.database_path)
    applied = run_migrations(database)
    if not applied:
        print("No new migrations.")
    else:
        print("Applied migrations:")
        for version in applied:
            print(f" - {version}")
    return 0
