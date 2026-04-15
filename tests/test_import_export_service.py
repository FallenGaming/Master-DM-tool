from __future__ import annotations

from pathlib import Path

from world_studio.application.services import (
    CONFLICT_KEEP_IMPORTED,
    CONFLICT_KEEP_LOCAL,
    IMPORT_MODE_MERGE,
    IMPORT_MODE_REPLACE,
    ImportExportService,
)
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, SocialRepository, WorldRepository
from world_studio.domain.enums import RelationshipType, SettlementType
from world_studio.domain.population import Npc, Occupation, Race, Relationship
from world_studio.domain.world import Continent, SettlementNode, World
from world_studio.infrastructure.json_io import JsonWorldCodec
from world_studio.infrastructure.pdf_export import PdfExporter


def _setup(
    tmp_path: Path,
) -> tuple[WorldRepository, HierarchyRepository, SocialRepository, ImportExportService]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    social_repository = SocialRepository(database)
    service = ImportExportService(
        world_repository=world_repository,
        hierarchy_repository=hierarchy_repository,
        social_repository=social_repository,
        json_codec=JsonWorldCodec(),
        pdf_exporter=PdfExporter(),
        exports_dir=tmp_path / "exports",
    )
    return world_repository, hierarchy_repository, social_repository, service


def test_export_world_json_includes_hierarchy_and_social_sections(tmp_path: Path) -> None:
    world_repository, hierarchy_repository, social_repository, service = _setup(tmp_path)
    world_repository.upsert_world(World(id=None, ext_ref="world-1", name="Eldoria"))
    hierarchy_repository.upsert_continent(
        Continent(id=None, ext_ref="cont-1", world_ref="world-1", name="Northreach")
    )
    hierarchy_repository.upsert_settlement(
        SettlementNode(
            id=None,
            ext_ref="set-1",
            world_ref="world-1",
            name="Ravenford",
            kind=SettlementType.TOWN,
            population=1200,
            x=10.0,
            y=-5.0,
        )
    )
    social_repository.upsert_race(Race(id=None, ext_ref="race-1", name="Human", lifespan_years=80))
    social_repository.upsert_occupation(
        Occupation(id=None, ext_ref="occ-1", name="Guard", category="security")
    )
    social_repository.upsert_npc(
        Npc(
            id=None,
            ext_ref="npc-1",
            world_ref="world-1",
            display_name="Aelar Stone",
            age_years=30,
            race_ref="race-1",
            occupation_ref="occ-1",
            subrace_ref=None,
            residence_node_ref="set-1",
        )
    )
    social_repository.upsert_relationship(
        Relationship(
            id=None,
            ext_ref="rel-1",
            world_ref="world-1",
            source_npc_ref="npc-1",
            target_npc_ref="npc-1",
            relation_type=RelationshipType.FRIEND,
            weight=0.1,
        )
    )

    exported = service.export_world_json("world-1")
    payload = JsonWorldCodec().deserialize_world_bundle(exported.read_text(encoding="utf-8"))

    assert payload["world"]["ext_ref"] == "world-1"
    assert len(payload["hierarchy"]["continents"]) == 1
    assert len(payload["hierarchy"]["settlements"]) == 1
    assert len(payload["social"]["npcs"]) == 1


def test_import_merge_conflict_policy_controls_updates(tmp_path: Path) -> None:
    world_repository, hierarchy_repository, _, service = _setup(tmp_path)
    world_repository.upsert_world(World(id=None, ext_ref="world-1", name="Local World"))
    hierarchy_repository.upsert_settlement(
        SettlementNode(
            id=None,
            ext_ref="set-1",
            world_ref="world-1",
            name="Local Haven",
            kind=SettlementType.VILLAGE,
            population=220,
            x=1.0,
            y=1.0,
        )
    )

    raw = JsonWorldCodec().serialize_world_bundle(
        world_ref="world-1",
        payload={
            "world": {"ext_ref": "world-1", "name": "Imported World"},
            "hierarchy": {
                "settlements": [
                    {
                        "ext_ref": "set-1",
                        "world_ref": "world-1",
                        "name": "Imported Haven",
                        "kind": "town",
                        "population": 1450,
                        "x": 2.0,
                        "y": -4.0,
                    }
                ]
            },
            "social": {},
        },
    )
    source = tmp_path / "import.json"
    source.write_text(raw, encoding="utf-8")

    summary_local = service.import_world_json(
        source,
        mode=IMPORT_MODE_MERGE,
        conflict_policy=CONFLICT_KEEP_LOCAL,
        preview_only=False,
    )
    settlement_after_local = hierarchy_repository.get_settlement("set-1")
    assert settlement_after_local is not None
    assert settlement_after_local.name == "Local Haven"
    assert summary_local.skipped.get("settlements", 0) == 1

    summary_imported = service.import_world_json(
        source,
        mode=IMPORT_MODE_MERGE,
        conflict_policy=CONFLICT_KEEP_IMPORTED,
        preview_only=False,
    )
    settlement_after_import = hierarchy_repository.get_settlement("set-1")
    assert settlement_after_import is not None
    assert settlement_after_import.name == "Imported Haven"
    assert summary_imported.updated.get("settlements", 0) == 1


def test_import_replace_mode_rebuilds_world_scoped_entities(tmp_path: Path) -> None:
    world_repository, hierarchy_repository, _, service = _setup(tmp_path)
    world_repository.upsert_world(World(id=None, ext_ref="world-1", name="Replace Test"))
    hierarchy_repository.upsert_settlement(
        SettlementNode(
            id=None,
            ext_ref="old-settlement",
            world_ref="world-1",
            name="Oldford",
            kind=SettlementType.VILLAGE,
            population=120,
            x=0.0,
            y=0.0,
        )
    )

    raw = JsonWorldCodec().serialize_world_bundle(
        world_ref="world-1",
        payload={
            "world": {"ext_ref": "world-1", "name": "Replace Test Imported"},
            "hierarchy": {
                "settlements": [
                    {
                        "ext_ref": "new-settlement",
                        "world_ref": "world-1",
                        "name": "Newford",
                        "kind": "town",
                        "population": 900,
                        "x": 5.0,
                        "y": 6.0,
                    }
                ]
            },
            "social": {},
        },
    )
    source = tmp_path / "replace.json"
    source.write_text(raw, encoding="utf-8")

    summary = service.import_world_json(
        source,
        mode=IMPORT_MODE_REPLACE,
        conflict_policy=CONFLICT_KEEP_IMPORTED,
        preview_only=False,
    )

    assert hierarchy_repository.get_settlement("old-settlement") is None
    assert hierarchy_repository.get_settlement("new-settlement") is not None
    assert summary.created.get("settlements", 0) == 1
