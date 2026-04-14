from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from world_studio.application.services import (
    GenerationAppService,
    HierarchyService,
    SocialService,
    WorldService,
)
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import HierarchyRepository, SocialRepository, WorldRepository
from world_studio.domain.world import World
from world_studio.generation.generation_models import GenerationSettings
def _setup(tmp_path: Path) -> tuple[
    WorldService, HierarchyService, SocialService, GenerationAppService, World
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
            name="Generated Realm",
            description="Phase 4 generation test world",
        )
    )
    return world_service, hierarchy_service, social_service, generation_service, world


def test_generation_pipeline_persists_hierarchy_and_social_graph(tmp_path: Path) -> None:
    _, hierarchy_service, social_service, generation_service, world = _setup(tmp_path)

    result = generation_service.generate_initial_state(
        world.ext_ref,
        {
            "seed": 4242,
            "continent_count": 2,
            "empires_per_continent": 1,
            "kingdoms_per_empire": 2,
            "regions_per_kingdom": 2,
            "settlements_per_region": 2,
            "npcs_per_settlement_min": 4,
            "npcs_per_settlement_max": 6,
            "relationship_density": 0.1,
        },
    )

    assert result.counts["continents"] == 2
    assert result.counts["empires"] == 2
    assert result.counts["kingdoms"] == 4
    assert result.counts["regions"] == 8
    assert result.counts["settlements"] == 16
    assert result.counts["routes"] > 0
    assert result.counts["npcs"] > 0
    assert result.counts["relationships"] > 0

    assert len(hierarchy_service.list_continents(world.ext_ref)) == 2
    assert len(hierarchy_service.list_settlements(world.ext_ref)) == 16
    assert len(hierarchy_service.list_routes(world.ext_ref)) == result.counts["routes"]
    assert len(social_service.list_npcs(world.ext_ref)) == result.counts["npcs"]
    assert len(social_service.list_relationships(world.ext_ref)) == result.counts["relationships"]

    regions = hierarchy_service.list_regions(world.ext_ref)
    settlements = hierarchy_service.list_settlements(world.ext_ref)
    assert all(isinstance(region.metadata.get("map"), dict) for region in regions)
    assert all(isinstance(settlement.metadata.get("map"), dict) for settlement in settlements)
    assert all("cluster_id" in settlement.metadata["map"] for settlement in settlements)


def test_generation_lock_and_override_compatibility(tmp_path: Path) -> None:
    _, _, social_service, generation_service, world = _setup(tmp_path)
    generation_service.generate_initial_state(
        world.ext_ref,
        {
            "seed": 9001,
            "continent_count": 1,
            "empires_per_continent": 1,
            "kingdoms_per_empire": 1,
            "regions_per_kingdom": 1,
            "settlements_per_region": 1,
            "npcs_per_settlement_min": 4,
            "npcs_per_settlement_max": 4,
        },
    )

    npc = social_service.list_npcs(world.ext_ref)[0]
    social_service.update_npc(npc.ext_ref, {"is_locked": True}, force=True)

    try:
        social_service.update_npc(npc.ext_ref, {"notes": "blocked update"}, force=False)
        assert False, "Expected locked update without force to fail."
    except ValueError:
        pass

    updated = social_service.update_npc(
        npc.ext_ref, {"notes": "override update works"}, force=True
    )
    assert updated.notes == "override update works"


def test_generation_settings_normalization_bounds() -> None:
    settings = GenerationSettings(
        continent_count=0,
        empires_per_continent=0,
        kingdoms_per_empire=0,
        regions_per_kingdom=0,
        settlements_per_region=0,
        npcs_per_settlement_min=10,
        npcs_per_settlement_max=2,
        relationship_density=9.0,
    )
    normalized = settings.normalized()
    assert normalized.continent_count >= 1
    assert normalized.empires_per_continent >= 1
    assert normalized.kingdoms_per_empire >= 1
    assert normalized.regions_per_kingdom >= 1
    assert normalized.settlements_per_region >= 1
    assert normalized.npcs_per_settlement_max >= normalized.npcs_per_settlement_min
    assert 0.0 <= normalized.relationship_density <= 1.0

