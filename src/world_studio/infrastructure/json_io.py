from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExportEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    exported_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    kind: str
    world_ref: str
    payload: dict[str, Any]


class JsonWorldCodec:
    def serialize_world(self, world_payload: dict[str, Any]) -> str:
        world_ref = str(world_payload.get("ext_ref", "unknown"))
        envelope = ExportEnvelope(
            kind="full_world",
            world_ref=world_ref,
            payload={"world": world_payload},
        )
        return json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True)

    def deserialize_world(self, raw: str) -> dict[str, Any]:
        envelope = ExportEnvelope.model_validate_json(raw)
        if envelope.kind not in {"full_world", "partial_world"}:
            raise ValueError(f"Unsupported world import kind: {envelope.kind}")
        if "world" not in envelope.payload:
            raise ValueError("Invalid payload: missing world object.")
        world = envelope.payload["world"]
        if not isinstance(world, dict):
            raise ValueError("Invalid payload: world must be an object.")
        return world
