from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import (
    POI_NAMES,
    SETTLEMENT_NAMES,
    choose_population,
    pick_settlement_type,
    unique_name,
)
from world_studio.generation.settlement_flavor_builder import SettlementFlavorBuilder


class SettlementGenerator:
    def __init__(self) -> None:
        self._flavor_builder = SettlementFlavorBuilder()

    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        world_mod = context.modifiers.for_world()
        for region_ref in context.region_refs:
            for index in range(context.settings.settlements_per_region):
                kind = pick_settlement_type(context.rng)
                population = choose_population(context.rng, kind)
                region_modifier = context.modifiers.region.get(region_ref)
                if region_modifier is not None:
                    population = int(population * region_modifier.population_multiplier())
                    population = max(40, population)
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
                        "resource_index": round(
                            max(
                                0.05,
                                min(
                                    1.0,
                                    context.rng.uniform(0.2, 0.95)
                                    + world_mod.prosperity_delta * 0.2
                                    + (region_modifier.resource_bonus if region_modifier else 0.0) * 0.35,
                                ),
                            ),
                            2,
                        ),
                        "safety_index": round(
                            max(
                                0.05,
                                min(
                                    1.0,
                                    context.rng.uniform(0.15, 0.9)
                                    + world_mod.safety_delta * 0.3
                                    + (region_modifier.safety_delta if region_modifier else 0.0) * 0.25,
                                ),
                            ),
                            2,
                        ),
                        "x": round(context.rng.uniform(-500, 500), 2),
                        "y": round(context.rng.uniform(-500, 500), 2),
                        "is_locked": False,
                    },
                )
                context.settlement_refs.append(settlement.ext_ref)
                context.settlement_population[settlement.ext_ref] = population
                context.increment("settlements")
                context.modifiers.settlement[settlement.ext_ref] = context.modifiers.derive_settlement_modifier(
                    region_ref,
                    settlement.ext_ref,
                )

                flavor = self._flavor_builder.build(
                    settlement_name=name,
                    settlement_ref=settlement.ext_ref,
                    context=context,
                    region_ref=region_ref,
                    population=population,
                )
                context.settlement_themes[settlement.ext_ref] = flavor.theme
                context.settlement_tensions[settlement.ext_ref] = flavor.tension
                context.settlement_hooks[settlement.ext_ref] = flavor.hooks
                context.settlement_tags[settlement.ext_ref] = flavor.tags
                context.notes.append(
                    f"{name}: {flavor.theme}; tension={flavor.tension}; tags={','.join(flavor.tags)}"
                )

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
