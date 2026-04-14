from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from world_studio.application.services import SocialService
from world_studio.data.database import Database
from world_studio.data.migrations import run_migrations
from world_studio.data.repositories import SocialRepository, WorldRepository
from world_studio.domain.world import World


def _setup(tmp_path: Path) -> tuple[World, SocialService]:
    database = Database(tmp_path / "test.sqlite3")
    run_migrations(database)
    world_repository = WorldRepository(database)
    social_repository = SocialRepository(database)
    world = world_repository.upsert_world(
        World(id=None, ext_ref=str(uuid4()), name="Nyxterra", description="phase 3 test world")
    )
    service = SocialService(social_repository)
    return world, service


def test_social_service_lock_override_for_npc(tmp_path: Path) -> None:
    world, service = _setup(tmp_path)
    race = service.create_race({"name": "Human", "lifespan_years": 80, "is_default": True})

    npc = service.create_npc(
        world.ext_ref,
        {
            "display_name": "Lysa Darn",
            "age_years": 28,
            "race_ref": race.ext_ref,
            "is_locked": True,
        },
    )

    with pytest.raises(ValueError, match="locked"):
        service.update_npc(npc.ext_ref, {"notes": "updated without override"})

    updated = service.update_npc(
        npc.ext_ref, {"notes": "updated with override", "is_locked": True}, force=True
    )
    assert updated.notes == "updated with override"
    assert updated.is_locked is True


def test_social_service_lock_override_for_relationship(tmp_path: Path) -> None:
    world, service = _setup(tmp_path)
    race = service.create_race({"name": "Elf", "lifespan_years": 320, "is_default": True})
    npc_a = service.create_npc(
        world.ext_ref, {"display_name": "Aelar", "age_years": 120, "race_ref": race.ext_ref}
    )
    npc_b = service.create_npc(
        world.ext_ref, {"display_name": "Brynn", "age_years": 87, "race_ref": race.ext_ref}
    )

    rel = service.create_relationship(
        world.ext_ref,
        {
            "source_npc_ref": npc_a.ext_ref,
            "target_npc_ref": npc_b.ext_ref,
            "relation_type": "ally",
            "weight": "0.8",
            "history": "United against raiders",
            "is_locked": True,
        },
    )

    with pytest.raises(ValueError, match="locked"):
        service.update_relationship(rel.ext_ref, {"weight": "0.2"})

    changed = service.update_relationship(
        rel.ext_ref, {"weight": "0.2", "history": "Alliance strained"}, force=True
    )
    assert changed.weight == 0.2
    assert changed.history == ["Alliance strained"]
