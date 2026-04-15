from __future__ import annotations

from pathlib import Path

from world_studio.application.services import (
    PDF_PACK_DM,
    PDF_PACK_PLAYER,
    PDF_PACK_SUMMARY,
    ImportExportService,
)
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, SocialRepository, WorldRepository
from world_studio.domain.enums import NodeType, SettlementType
from world_studio.domain.world import (
    Continent,
    Empire,
    Kingdom,
    PointOfInterest,
    Region,
    SettlementNode,
    World,
)
from world_studio.infrastructure.json_io import JsonWorldCodec
from world_studio.infrastructure.pdf_export import PdfExporter


def _setup(tmp_path: Path) -> tuple[ImportExportService, HierarchyRepository, World]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    social_repository = SocialRepository(database)
    world = world_repository.upsert_world(
        World(id=None, ext_ref="world-1", name="Phase 8 Realm", description="Snapshot/PDF test")
    )
    hierarchy_repository.upsert_continent(
        Continent(
            id=None,
            ext_ref="cont-1",
            world_ref=world.ext_ref,
            name="Northreach",
            climate_summary="cold",
        )
    )
    hierarchy_repository.upsert_empire(
        Empire(
            id=None,
            ext_ref="emp-1",
            world_ref=world.ext_ref,
            continent_ref="cont-1",
            name="Iron Crown",
            governing_style="council",
        )
    )
    hierarchy_repository.upsert_kingdom(
        Kingdom(
            id=None,
            ext_ref="king-1",
            world_ref=world.ext_ref,
            empire_ref="emp-1",
            name="Ravenmark",
            stability_index=0.61,
        )
    )
    hierarchy_repository.upsert_region(
        Region(
            id=None,
            ext_ref="reg-1",
            world_ref=world.ext_ref,
            kingdom_ref="king-1",
            name="Ashen Vale",
            biome="forest",
        )
    )
    hierarchy_repository.upsert_settlement(
        SettlementNode(
            id=None,
            ext_ref="set-1",
            world_ref=world.ext_ref,
            region_ref="reg-1",
            name="Oakrest",
            kind=SettlementType.VILLAGE,
            population=120,
            resource_index=0.6,
            safety_index=0.7,
            x=10.0,
            y=6.0,
        )
    )
    service = ImportExportService(
        world_repository=world_repository,
        hierarchy_repository=hierarchy_repository,
        social_repository=social_repository,
        json_codec=JsonWorldCodec(),
        pdf_exporter=PdfExporter(),
        exports_dir=tmp_path / "exports",
    )
    return service, hierarchy_repository, world


def test_snapshot_compare_and_restore(tmp_path: Path) -> None:
    service, hierarchy_repository, world = _setup(tmp_path)

    base_snapshot = service.create_snapshot(world.ext_ref, name="Base")
    settlement = hierarchy_repository.get_settlement("set-1")
    assert settlement is not None
    settlement.population = 360
    hierarchy_repository.upsert_settlement(settlement)
    hierarchy_repository.upsert_point_of_interest(
        PointOfInterest(
            id=None,
            ext_ref="poi-1",
            world_ref=world.ext_ref,
            region_ref="reg-1",
            name="Old Shrine",
            node_type=NodeType.POINT_OF_INTEREST,
            x=12.0,
            y=8.0,
            description="A forgotten shrine.",
        )
    )
    target_snapshot = service.create_snapshot(world.ext_ref, name="After growth")

    compare = service.compare_snapshots(base_snapshot.ext_ref, target_snapshot.ext_ref)
    assert compare.total_changed > 0
    assert any(diff.entity_type == "settlements" and diff.changed > 0 for diff in compare.entity_diffs)
    assert any(
        diff.entity_type == "points_of_interest" and diff.added > 0 for diff in compare.entity_diffs
    )

    restore = service.restore_snapshot(base_snapshot.ext_ref)
    assert restore.world_ref == world.ext_ref
    restored_settlement = hierarchy_repository.get_settlement("set-1")
    assert restored_settlement is not None
    assert restored_settlement.population == 120
    assert hierarchy_repository.list_points_of_interest(world.ext_ref) == []


def test_pdf_pack_exports(tmp_path: Path) -> None:
    service, _, world = _setup(tmp_path)

    for pack_kind in (PDF_PACK_SUMMARY, PDF_PACK_DM, PDF_PACK_PLAYER):
        target = service.export_world_pdf(world.ext_ref, pack_kind=pack_kind)
        assert target.exists()
        assert target.stat().st_size > 500
