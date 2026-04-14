from __future__ import annotations

from pathlib import Path

from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import SocialRepository, WorldRepository
from world_studio.domain.enums import RelationshipType
from world_studio.domain.population import Npc, Occupation, Race, Relationship
from world_studio.domain.world import World


def _setup(tmp_path: Path) -> tuple[World, SocialRepository]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    social_repository = SocialRepository(database)
    world = world_repository.upsert_world(World(id=None, ext_ref="world-1", name="Eldoria"))
    return world, social_repository


def test_social_repository_npc_relationship_round_trip(tmp_path: Path) -> None:
    world, repository = _setup(tmp_path)

    race = repository.upsert_race(
        Race(id=None, ext_ref="race-human", name="Human", lifespan_years=80, is_default=True)
    )
    occupation = repository.upsert_occupation(
        Occupation(id=None, ext_ref="occ-smith", name="Blacksmith", category="craft")
    )

    npc_a = repository.upsert_npc(
        Npc(
            id=None,
            ext_ref="npc-a",
            world_ref=world.ext_ref,
            display_name="Ari",
            age_years=34,
            race_ref=race.ext_ref,
            subrace_ref=None,
            occupation_ref=occupation.ext_ref,
            residence_node_ref=None,
        )
    )
    npc_b = repository.upsert_npc(
        Npc(
            id=None,
            ext_ref="npc-b",
            world_ref=world.ext_ref,
            display_name="Borin",
            age_years=41,
            race_ref=race.ext_ref,
            subrace_ref=None,
            occupation_ref=None,
            residence_node_ref=None,
        )
    )

    relationship = repository.upsert_relationship(
        Relationship(
            id=None,
            ext_ref="rel-1",
            world_ref=world.ext_ref,
            source_npc_ref=npc_a.ext_ref,
            target_npc_ref=npc_b.ext_ref,
            relation_type=RelationshipType.FRIEND,
            weight=0.6,
            history=["Met during apprenticeship.", "Saved from a fire."],
        )
    )

    npcs = repository.list_npcs(world.ext_ref)
    relationships = repository.list_relationships(world.ext_ref)
    assert len(npcs) == 2
    assert len(relationships) == 1
    assert relationships[0].relation_type == RelationshipType.FRIEND
    assert relationships[0].history == ["Met during apprenticeship.", "Saved from a fire."]

    repository.delete_relationship(relationship.ext_ref)
    repository.delete_npc(npc_a.ext_ref)
    repository.delete_npc(npc_b.ext_ref)
    assert repository.list_relationships(world.ext_ref) == []
    assert repository.list_npcs(world.ext_ref) == []
