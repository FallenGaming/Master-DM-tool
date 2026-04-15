from __future__ import annotations

from datetime import UTC, datetime

from world_studio.infrastructure.json_io import JsonWorldCodec


def test_world_json_round_trip() -> None:
    codec = JsonWorldCodec()
    source = {
        "id": None,
        "ext_ref": "world-1",
        "name": "Eldoria",
        "description": "A realm of shifting alliances.",
        "active_ruleset_ref": None,
        "is_locked": False,
        "metadata": {},
        "created_utc": datetime.now(UTC).isoformat(),
        "updated_utc": datetime.now(UTC).isoformat(),
    }
    serialized = codec.serialize_world(source)
    deserialized = codec.deserialize_world(serialized)
    assert deserialized["ext_ref"] == "world-1"
    assert deserialized["name"] == "Eldoria"


def test_world_bundle_round_trip() -> None:
    codec = JsonWorldCodec()
    bundle = codec.serialize_world_bundle(
        world_ref="world-1",
        payload={
            "world": {
                "ext_ref": "world-1",
                "name": "Eldoria",
                "description": "Bundle test.",
            },
            "hierarchy": {
                "continents": [{"ext_ref": "cont-1", "name": "Northreach", "world_ref": "world-1"}],
                "settlements": [{"ext_ref": "set-1", "name": "Ravenford", "world_ref": "world-1"}],
            },
            "social": {"npcs": [{"ext_ref": "npc-1", "display_name": "Aelar", "race_ref": "race-1"}]},
        },
    )
    parsed = codec.deserialize_world_bundle(bundle)
    assert parsed["world_ref"] == "world-1"
    assert parsed["world"]["name"] == "Eldoria"
    assert len(parsed["hierarchy"]["continents"]) == 1
    assert len(parsed["social"]["npcs"]) == 1
