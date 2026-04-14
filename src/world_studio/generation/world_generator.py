from __future__ import annotations

from typing import Any

from random import Random

from world_studio.generation.continent_generator import ContinentGenerator
from world_studio.generation.demographics_generator import DemographicsGenerator
from world_studio.generation.event_aware_generation import EventAwareGenerationResolver
from world_studio.generation.generation_models import (
    GenerationContext,
    GenerationRequest,
    GenerationRunSummary,
)
from world_studio.generation.history_context_builder import HistoryContextBuilder
from world_studio.generation.narrative_seed_builder import NarrativeSeedBuilder
from world_studio.generation.npc_generator import NpcGenerator
from world_studio.generation.occupation_allocator import OccupationAllocator
from world_studio.generation.political_generator import PoliticalGenerator
from world_studio.generation.region_generator import RegionGenerator
from world_studio.generation.relationship_seed_generator import RelationshipSeedGenerator
from world_studio.generation.settlement_generator import SettlementGenerator


class WorldGenerationService:
    def __init__(
        self,
        world_service: Any,
        hierarchy_service: Any,
        social_service: Any,
    ) -> None:
        self._world_service = world_service
        self._hierarchy_service = hierarchy_service
        self._social_service = social_service

    def generate(self, request: GenerationRequest) -> GenerationRunSummary:
        settings = request.settings.normalized()
        world = self._world_service.get_world(request.world_ref)
        if world is None:
            raise ValueError(f"Unknown world: {request.world_ref}")

        context = GenerationContext(
            world_ref=request.world_ref,
            settings=settings,
            rng=Random(settings.seed),
        )

        history_context = HistoryContextBuilder().build(context)
        context.notes.extend(history_context.notes)
        context.modifiers = EventAwareGenerationResolver().resolve(context, history_context)

        DemographicsGenerator().ensure_races(self._social_service, context)
        OccupationAllocator().ensure_occupations(self._social_service, context)
        ContinentGenerator().generate(self._hierarchy_service, context)
        PoliticalGenerator().generate(self._hierarchy_service, context)
        RegionGenerator().generate(self._hierarchy_service, context)
        SettlementGenerator().generate(self._hierarchy_service, context)
        NpcGenerator().generate(self._social_service, context)
        RelationshipSeedGenerator().generate(self._social_service, context)
        NarrativeSeedBuilder().build(context)

        counts = {
            "continents": context.counts.get("continents", 0),
            "empires": context.counts.get("empires", 0),
            "kingdoms": context.counts.get("kingdoms", 0),
            "regions": context.counts.get("regions", 0),
            "settlements": context.counts.get("settlements", 0),
            "points_of_interest": context.counts.get("points_of_interest", 0),
            "npcs": context.counts.get("npcs", 0),
            "relationships": context.counts.get("relationships", 0),
            "event_footprints": len(context.modifiers.event_footprints),
            "dm_hooks": context.counts.get("dm_hooks", 0),
        }
        notes = [
            f"Catalog references seeded: races={len(context.race_refs)}, occupations={len(context.occupation_refs)}",
            f"Event footprints applied: {len(context.modifiers.event_footprints)}",
            "Generation completed through application/repository services.",
            *context.notes,
        ]
        for settlement_ref in context.settlement_refs:
            hooks = context.settlement_hooks.get(settlement_ref, [])
            if hooks:
                context.increment("dm_hooks", len(hooks))
        return GenerationRunSummary(
            world_ref=request.world_ref,
            seed_used=settings.seed,
            counts=counts,
            notes=notes,
        )
