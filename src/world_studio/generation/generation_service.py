from __future__ import annotations

from world_studio.events.event_dsl_models import EventSeedInput
from world_studio.generation.generation_models import (
    GenerationRequest,
    GenerationRunSummary,
    GenerationSettings,
)
from world_studio.generation.world_generator import WorldGenerationService


class WorldGenerationOrchestrator:
    def __init__(self) -> None:
        self._service: WorldGenerationService | None = None

    def bind(
        self,
        world_service: object,
        hierarchy_service: object,
        social_service: object,
    ) -> None:
        self._service = WorldGenerationService(world_service, hierarchy_service, social_service)

    def generate(self, request: GenerationRequest) -> GenerationRunSummary:
        if self._service is None:
            raise RuntimeError("WorldGenerationOrchestrator is not bound to services.")
        return self._service.generate(request)


def generate_with_payload(
    world_service: object,
    hierarchy_service: object,
    social_service: object,
    world_ref: str,
    payload: dict[str, object],
) -> GenerationRunSummary:
    event_inputs = tuple(parse_event_seed_inputs(payload.get("event_inputs")))
    historical_inputs = tuple(parse_event_seed_inputs(payload.get("historical_inputs"), stage="historical"))

    settings = GenerationSettings(
        seed=int(payload.get("seed", 42)),
        continent_count=int(payload.get("continent_count", 2)),
        empires_per_continent=int(payload.get("empires_per_continent", 1)),
        kingdoms_per_empire=int(payload.get("kingdoms_per_empire", 2)),
        regions_per_kingdom=int(payload.get("regions_per_kingdom", 2)),
        settlements_per_region=int(payload.get("settlements_per_region", 3)),
        npcs_per_settlement_min=int(payload.get("npcs_per_settlement_min", 8)),
        npcs_per_settlement_max=int(payload.get("npcs_per_settlement_max", 14)),
        relationship_density=float(payload.get("relationship_density", 0.08)),
        lock_generated_political=bool(payload.get("lock_generated_political", False)),
        lock_generated_leaders=bool(payload.get("lock_generated_leaders", False)),
        event_inputs=event_inputs,
        historical_event_inputs=historical_inputs,
        world_tags=tuple(_split_csv(payload.get("world_tags"))),
    )
    service = WorldGenerationService(world_service, hierarchy_service, social_service)
    return service.generate(GenerationRequest(world_ref=world_ref, settings=settings))


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_csv(value: object | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(segment).strip() for segment in value if str(segment).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [segment.strip() for segment in text.split(",") if segment.strip()]


def parse_event_seed_inputs(value: object | None, *, stage: str = "active") -> list[EventSeedInput]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Event inputs must be provided as a list of event objects.")
    parsed: list[EventSeedInput] = []
    for item in value:
        if isinstance(item, EventSeedInput):
            parsed.append(item)
            continue
        if isinstance(item, dict):
            parsed.append(EventSeedInput.from_dict(item, stage=stage))
    return parsed
