from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import (
    POI_NAMES,
    SETTLEMENT_NAMES,
    choose_population,
    pick_settlement_type,
    unique_name,
)


class SettlementGenerator:
    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        for region_ref in context.region_refs:
            for index in range(context.settings.settlements_per_region):
                kind = pick_settlement_type(context.rng)
                population = choose_population(context.rng, kind)
                name = unique_name(
                    context.rng,
                    context.used_names,
                    "Settlement",
                    index,
                    SETTLEMENT_NAMES,
                )
                settlement = hierarchy_service.create_settlement(
                    context.world_ref,
                    {
                        "name": name,
                        "region_ref": region_ref,
                        "kind": kind.value,
                        "population": population,
                        "resource_index": round(context.rng.uniform(0.2, 0.95), 2),
                        "safety_index": round(context.rng.uniform(0.15, 0.9), 2),
                        "x": round(context.rng.uniform(-500, 500), 2),
                        "y": round(context.rng.uniform(-500, 500), 2),
                        "is_locked": False,
                    },
                )
                context.settlement_refs.append(settlement.ext_ref)
                context.settlement_population[settlement.ext_ref] = population
                context.increment("settlements")

                poi_name = unique_name(
                    context.rng,
                    context.used_names,
                    "POI",
                    index,
                    POI_NAMES,
                )
                hierarchy_service.create_point_of_interest(
                    context.world_ref,
                    {
                        "name": poi_name,
                        "region_ref": region_ref,
                        "node_type": "point_of_interest",
                        "x": round(context.rng.uniform(-500, 500), 2),
                        "y": round(context.rng.uniform(-500, 500), 2),
                        "description": "Generated landmark tied to local settlement growth.",
                        "is_locked": False,
                    },
                )
                context.increment("points_of_interest")
