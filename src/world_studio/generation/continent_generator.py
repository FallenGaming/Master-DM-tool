from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import CONTINENT_NAMES, choose_climate, unique_name


class ContinentGenerator:
    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        for index in range(context.settings.continent_count):
            name = unique_name(
                context.rng,
                context.used_names,
                "Continent",
                index,
                CONTINENT_NAMES,
            )
            continent = hierarchy_service.create_continent(
                context.world_ref,
                {
                    "name": name,
                    "climate_summary": choose_climate(context.rng),
                    "is_locked": context.settings.lock_generated_political,
                },
            )
            context.continent_refs.append(continent.ext_ref)
            context.increment("continents")
