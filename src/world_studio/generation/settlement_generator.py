from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import (
    POI_NAMES,
    SETTLEMENT_NAMES,
    choose_population,
    pick_settlement_type,
    unique_name,
)
from world_studio.generation.node_layout_generator import NodeLayoutGenerator
from world_studio.generation.settlement_flavor_builder import SettlementFlavorBuilder


class SettlementGenerator:
    def __init__(self) -> None:
        self._flavor_builder = SettlementFlavorBuilder()
        self._layout = NodeLayoutGenerator()

    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        world_mod = context.modifiers.for_world()
        for region_ref in context.region_refs:
            center_x, center_y = context.region_centers.get(
                region_ref,
                (context.rng.uniform(-300.0, 300.0), context.rng.uniform(-300.0, 300.0)),
            )
            region_radius = context.region_radii.get(region_ref, 85.0)
            placements = self._layout.generate_settlement_positions(
                rng=context.rng,
                region_ref=region_ref,
                center_x=center_x,
                center_y=center_y,
                radius=region_radius,
                settlement_count=context.settings.settlements_per_region,
            )
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
                        "x": placements[index][0],
                        "y": placements[index][1],
                        "metadata": {
                            "map": {
                                "level": "settlement",
                                "cluster_id": placements[index][2],
                                "region_ref": region_ref,
                                "kingdom_ref": context.kingdom_ref_by_region.get(region_ref),
                                "empire_ref": context.empire_ref_by_kingdom.get(
                                    context.kingdom_ref_by_region.get(region_ref, "")
                                ),
                                "continent_ref": context.continent_ref_by_empire.get(
                                    context.empire_ref_by_kingdom.get(
                                        context.kingdom_ref_by_region.get(region_ref, ""),
                                        "",
                                    ),
                                ),
                                "distance_to_region_center": round(
                                    (
                                        (placements[index][0] - center_x) ** 2
                                        + (placements[index][1] - center_y) ** 2
                                    )
                                    ** 0.5,
                                    2,
                                ),
                            }
                        },
                        "is_locked": False,
                    },
                )
                context.settlement_refs.append(settlement.ext_ref)
                context.settlement_population[settlement.ext_ref] = population
                context.region_ref_by_settlement[settlement.ext_ref] = region_ref
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
                poi_x, poi_y = self._layout.generate_poi_position(
                    rng=context.rng,
                    anchor_x=placements[index][0],
                    anchor_y=placements[index][1],
                    spread=max(8.0, region_radius * 0.22),
                )
                hierarchy_service.create_point_of_interest(
                    context.world_ref,
                    {
                        "name": poi_name,
                        "region_ref": region_ref,
                        "node_type": "point_of_interest",
                        "x": poi_x,
                        "y": poi_y,
                        "metadata": {
                            "map": {
                                "level": "local_poi",
                                "cluster_id": placements[index][2],
                                "near_settlement_ref": settlement.ext_ref,
                                "region_ref": region_ref,
                            }
                        },
                        "description": "Generated landmark tied to local settlement growth.",
                        "is_locked": False,
                    },
                )
                context.increment("points_of_interest")
