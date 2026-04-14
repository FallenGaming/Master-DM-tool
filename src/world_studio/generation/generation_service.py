from __future__ import annotations

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
    )
    service = WorldGenerationService(world_service, hierarchy_service, social_service)
    return service.generate(GenerationRequest(world_ref=world_ref, settings=settings))
