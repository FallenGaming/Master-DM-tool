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
    serialized = codec.serialize_world_bundle(
        world_ref="world-42",
        payload={
            "world": {"ext_ref": "world-42", "name": "Moonreach"},
            "hierarchy": {
                "continents": [{"ext_ref": "cont-1", "name": "Auric Span"}],
                "empires": [],
                "kingdoms": [],
                "regions": [],
                "settlements": [],
                "points_of_interest": [],
                "routes": [],
            },
            "social": {
                "races": [],
                "subraces": [],
                "occupations": [],
                "traits": [],
                "npcs": [],
                "relationships": [],
            },
        },
        kind="full_world",
    )
    bundle = codec.deserialize_world_bundle(serialized)
    assert bundle["world_ref"] == "world-42"
    assert bundle["world"]["name"] == "Moonreach"
    assert bundle["hierarchy"]["continents"][0]["ext_ref"] == "cont-1"
