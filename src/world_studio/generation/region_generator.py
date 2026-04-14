from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import REGION_NAMES, choose_biome, unique_name


class RegionGenerator:
    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        for kingdom_ref in context.kingdom_refs:
            for index in range(context.settings.regions_per_kingdom):
                name = unique_name(
                    context.rng,
                    context.used_names,
                    "Region",
                    index,
                    REGION_NAMES,
                )
                region = hierarchy_service.create_region(
                    context.world_ref,
                    {
                        "name": name,
                        "kingdom_ref": kingdom_ref,
                        "biome": choose_biome(context.rng),
                        "is_locked": context.settings.lock_generated_political,
                    },
                )
                context.region_refs.append(region.ext_ref)
                context.increment("regions")
