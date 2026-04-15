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
    _HIERARCHY_KEYS: tuple[str, ...] = (
        "continents",
        "empires",
        "kingdoms",
        "regions",
        "settlements",
        "points_of_interest",
        "routes",
    )
    _SOCIAL_KEYS: tuple[str, ...] = (
        "races",
        "subraces",
        "occupations",
        "traits",
        "npcs",
        "relationships",
    )

    def serialize_world(self, world_payload: dict[str, Any]) -> str:
        world_ref = str(world_payload.get("ext_ref", "unknown"))
        return self.serialize_world_bundle(
            world_ref=world_ref,
            payload={
                "world": world_payload,
                "hierarchy": self._empty_section(self._HIERARCHY_KEYS),
                "social": self._empty_section(self._SOCIAL_KEYS),
            },
        )

    def serialize_world_bundle(
        self,
        *,
        world_ref: str,
        payload: dict[str, Any],
        kind: str = "full_world",
    ) -> str:
        envelope = ExportEnvelope(
            kind=kind,
            world_ref=world_ref,
            payload=payload,
        )
        return json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True)

    def deserialize_world(self, raw: str) -> dict[str, Any]:
        bundle = self.deserialize_world_bundle(raw)
        return bundle["world"]

    def deserialize_world_bundle(self, raw: str) -> dict[str, Any]:
        envelope = ExportEnvelope.model_validate_json(raw)
        if envelope.kind not in {"full_world", "partial_world"}:
            raise ValueError(f"Unsupported world import kind: {envelope.kind}")
        if "world" not in envelope.payload:
            raise ValueError("Invalid payload: missing world object.")
        world = envelope.payload["world"]
        if not isinstance(world, dict):
            raise ValueError("Invalid payload: world must be an object.")
        hierarchy = self._normalize_section(
            envelope.payload.get("hierarchy"),
            allowed_keys=self._HIERARCHY_KEYS,
            section_name="hierarchy",
        )
        social = self._normalize_section(
            envelope.payload.get("social"),
            allowed_keys=self._SOCIAL_KEYS,
            section_name="social",
        )
        return {
            "world_ref": envelope.world_ref,
            "kind": envelope.kind,
            "world": world,
            "hierarchy": hierarchy,
            "social": social,
        }

    def _normalize_section(
        self,
        raw_section: object | None,
        *,
        allowed_keys: tuple[str, ...],
        section_name: str,
    ) -> dict[str, list[dict[str, Any]]]:
        if raw_section is None:
            return self._empty_section(allowed_keys)
        if not isinstance(raw_section, dict):
            raise ValueError(f"Invalid payload: {section_name} must be an object.")
        normalized = self._empty_section(allowed_keys)
        for key, value in raw_section.items():
            if key not in allowed_keys:
                raise ValueError(f"Invalid payload: unsupported {section_name} key '{key}'.")
            if not isinstance(value, list):
                raise ValueError(f"Invalid payload: {section_name}.{key} must be a list.")
            entries: list[dict[str, Any]] = []
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError(f"Invalid payload: {section_name}.{key} entries must be objects.")
                entries.append(item)
            normalized[key] = entries
        return normalized

    @staticmethod
    def _empty_section(keys: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
        return {key: [] for key in keys}
