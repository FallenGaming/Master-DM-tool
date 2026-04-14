from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from world_studio.application.services import HierarchyService
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, WorldRepository
from world_studio.domain.world import World


def _setup(tmp_path: Path) -> tuple[WorldRepository, HierarchyService, World]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    world = world_repository.upsert_world(
        World(id=None, ext_ref=str(uuid4()), name="Eldoria", description="Phase 2 world")
    )
    return world_repository, HierarchyService(hierarchy_repository), world


def test_hierarchy_service_create_and_update_settlement(tmp_path: Path) -> None:
    _, hierarchy_service, world = _setup(tmp_path)

    created = hierarchy_service.create_settlement(
        world.ext_ref,
        {
            "name": "Ravenford",
            "kind": "town",
            "population": "1450",
            "resource_index": "0.7",
            "safety_index": "0.6",
            "x": "12.5",
            "y": "-8.25",
        },
    )
    assert created.name == "Ravenford"
    assert created.population == 1450
    assert created.kind.value == "town"

    updated = hierarchy_service.update_settlement(
        created.ext_ref,
        {
            "population": "1600",
            "kind": "city",
            "is_locked": True,
        },
    )
    assert updated.population == 1600
    assert updated.kind.value == "city"
    assert updated.is_locked is True


def test_hierarchy_service_route_validation(tmp_path: Path) -> None:
    _, hierarchy_service, world = _setup(tmp_path)

    settlement_a = hierarchy_service.create_settlement(
        world.ext_ref,
        {"name": "Aster", "kind": "village"},
    )
    settlement_b = hierarchy_service.create_settlement(
        world.ext_ref,
        {"name": "Brighthold", "kind": "town"},
    )

    route = hierarchy_service.create_route(
        world.ext_ref,
        {
            "name": "Aster Road",
            "source_ref": settlement_a.ext_ref,
            "target_ref": settlement_b.ext_ref,
            "travel_cost": "2.5",
        },
    )
    assert route.route_type == "road"
    assert route.travel_cost == 2.5

