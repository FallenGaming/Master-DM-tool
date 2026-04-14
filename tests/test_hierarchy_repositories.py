from __future__ import annotations

from pathlib import Path

from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, WorldRepository
from world_studio.domain.enums import NodeType, SettlementType
from world_studio.domain.world import (
    Continent,
    Empire,
    Kingdom,
    PointOfInterest,
    Region,
    RouteConnection,
    SettlementNode,
    World,
)


def _setup_repositories(tmp_path: Path) -> tuple[WorldRepository, HierarchyRepository]:
    db = Database(tmp_path / "test.sqlite3")
    run_migrations(db)
    return WorldRepository(db), HierarchyRepository(db)


def test_hierarchy_repository_crud_flow(tmp_path: Path) -> None:
    world_repo, hierarchy_repo = _setup_repositories(tmp_path)
    world = world_repo.upsert_world(World(id=None, ext_ref="world-1", name="Asterra"))

    continent = hierarchy_repo.upsert_continent(
        Continent(
            id=None,
            ext_ref="cont-1",
            world_ref=world.ext_ref,
            name="Northreach",
            climate_summary="Cold and mountainous.",
        )
    )
    empire = hierarchy_repo.upsert_empire(
        Empire(
            id=None,
            ext_ref="emp-1",
            world_ref=world.ext_ref,
            continent_ref=continent.ext_ref,
            name="Frostbound Imperium",
            governing_style="Imperial senate",
        )
    )
    kingdom = hierarchy_repo.upsert_kingdom(
        Kingdom(
            id=None,
            ext_ref="king-1",
            world_ref=world.ext_ref,
            empire_ref=empire.ext_ref,
            name="Skall",
            stability_index=0.63,
        )
    )
    region = hierarchy_repo.upsert_region(
        Region(
            id=None,
            ext_ref="reg-1",
            world_ref=world.ext_ref,
            kingdom_ref=kingdom.ext_ref,
            name="Icewater Basin",
            biome="tundra",
        )
    )
    settlement = hierarchy_repo.upsert_settlement(
        SettlementNode(
            id=None,
            ext_ref="set-1",
            world_ref=world.ext_ref,
            region_ref=region.ext_ref,
            name="Stonehollow",
            kind=SettlementType.TOWN,
            population=1800,
            resource_index=0.71,
            safety_index=0.44,
            x=14.2,
            y=8.6,
        )
    )
    poi = hierarchy_repo.upsert_point_of_interest(
        PointOfInterest(
            id=None,
            ext_ref="poi-1",
            world_ref=world.ext_ref,
            region_ref=region.ext_ref,
            name="Mirror Obelisk",
            node_type=NodeType.NATURAL_FEATURE,
            x=13.7,
            y=8.0,
            description="Ancient crystal pillar.",
        )
    )
    route = hierarchy_repo.upsert_route(
        RouteConnection(
            id=None,
            ext_ref="route-1",
            world_ref=world.ext_ref,
            name="Obelisk Trail",
            source_ref=settlement.ext_ref,
            target_ref=poi.ext_ref,
            route_type="road",
            travel_cost=1.8,
        )
    )

    assert hierarchy_repo.get_continent(continent.ext_ref) is not None
    assert hierarchy_repo.get_empire(empire.ext_ref) is not None
    assert hierarchy_repo.get_kingdom(kingdom.ext_ref) is not None
    assert hierarchy_repo.get_region(region.ext_ref) is not None
    assert hierarchy_repo.get_settlement(settlement.ext_ref) is not None
    assert hierarchy_repo.get_point_of_interest(poi.ext_ref) is not None
    assert hierarchy_repo.get_route(route.ext_ref) is not None

    assert len(hierarchy_repo.list_continents(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_empires(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_kingdoms(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_regions(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_settlements(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_points_of_interest(world.ext_ref)) == 1
    assert len(hierarchy_repo.list_routes(world.ext_ref)) == 1

    hierarchy_repo.delete_route(route.ext_ref)
    hierarchy_repo.delete_point_of_interest(poi.ext_ref)
    hierarchy_repo.delete_settlement(settlement.ext_ref)
    hierarchy_repo.delete_region(region.ext_ref)
    hierarchy_repo.delete_kingdom(kingdom.ext_ref)
    hierarchy_repo.delete_empire(empire.ext_ref)
    hierarchy_repo.delete_continent(continent.ext_ref)

    assert hierarchy_repo.list_continents(world.ext_ref) == []
