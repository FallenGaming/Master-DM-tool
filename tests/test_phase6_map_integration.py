from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from world_studio.application.services import (
    GenerationAppService,
    HierarchyService,
    SimulationService,
    SocialService,
    WorldService,
)
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, SocialRepository, WorldRepository
from world_studio.domain.enums import SimulationStep
from world_studio.domain.simulation import SimulationRequest
from world_studio.domain.world import World
from world_studio.maps.map_projection_service import MapProjectionService
from world_studio.maps.multi_scale_map_service import MultiScaleMapService
from world_studio.maps.node_positioning_models import MapScale


def _setup(tmp_path: Path) -> tuple[
    WorldRepository,
    HierarchyRepository,
    WorldService,
    HierarchyService,
    GenerationAppService,
    World,
]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    social_repository = SocialRepository(database)

    world_service = WorldService(world_repository)
    hierarchy_service = HierarchyService(hierarchy_repository)
    social_service = SocialService(social_repository)
    generation_service = GenerationAppService(
        world_service=world_service,
        hierarchy_service=hierarchy_service,
        social_service=social_service,
    )
    world = world_service.create_world(
        World(
            id=None,
            ext_ref=str(uuid4()),
            name="Phase 6 Spatial Test",
            description="Map integration test world",
        )
    )
    return (
        world_repository,
        hierarchy_repository,
        world_service,
        hierarchy_service,
        generation_service,
        world,
    )


def test_map_projection_respects_multi_scale_hierarchy(tmp_path: Path) -> None:
    _, _, _, hierarchy_service, generation_service, world = _setup(tmp_path)
    generation_service.generate_initial_state(
        world.ext_ref,
        {
            "seed": 31337,
            "continent_count": 1,
            "empires_per_continent": 1,
            "kingdoms_per_empire": 2,
            "regions_per_kingdom": 2,
            "settlements_per_region": 2,
            "npcs_per_settlement_min": 3,
            "npcs_per_settlement_max": 5,
        },
    )

    map_service = MultiScaleMapService(MapProjectionService(hierarchy_service))
    world_projection = map_service.project(world.ext_ref, scale=MapScale.WORLD)
    assert world_projection.node_count() > 0
    assert any(node.node_type == "continent" for node in world_projection.nodes)
    assert any(edge.route_type == "contains" for edge in world_projection.edges)

    region = hierarchy_service.list_regions(world.ext_ref)[0]
    region_projection = map_service.project(
        world.ext_ref,
        scale=MapScale.REGION,
        focus_ref=region.ext_ref,
    )
    assert any(node.node_type == "settlement" for node in region_projection.nodes)
    assert any(edge.route_type != "contains" for edge in region_projection.edges)


def test_simulation_settlement_pass_persists_map_growth_state(tmp_path: Path) -> None:
    (
        world_repository,
        hierarchy_repository,
        _world_service,
        hierarchy_service,
        generation_service,
        world,
    ) = _setup(tmp_path)
    generation_service.generate_initial_state(
        world.ext_ref,
        {
            "seed": 41414,
            "continent_count": 1,
            "empires_per_continent": 1,
            "kingdoms_per_empire": 1,
            "regions_per_kingdom": 1,
            "settlements_per_region": 3,
            "npcs_per_settlement_min": 2,
            "npcs_per_settlement_max": 3,
        },
    )
    simulation_service = SimulationService(world_repository, hierarchy_repository)
    run = simulation_service.simulate(
        SimulationRequest(
            world_ref=world.ext_ref,
            step=SimulationStep.YEAR,
            quantity=1,
            preview_only=False,
        )
    )
    settlements = hierarchy_service.list_settlements(world.ext_ref)
    assert run.changes
    assert any("growth_pressure" in settlement.metadata.get("map", {}) for settlement in settlements)
    assert any(note.startswith("settlements: evaluated") for note in run.notes)
