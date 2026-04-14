from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import (
    EMPIRE_NAMES,
    KINGDOM_NAMES,
    choose_governing_style,
    unique_name,
)


class PoliticalGenerator:
    def generate(self, hierarchy_service: object, context: GenerationContext) -> None:
        for continent_ref in context.continent_refs:
            for emp_index in range(context.settings.empires_per_continent):
                emp_name = unique_name(
                    context.rng,
                    context.used_names,
                    "Empire",
                    emp_index,
                    EMPIRE_NAMES,
                )
                empire = hierarchy_service.create_empire(
                    context.world_ref,
                    {
                        "name": emp_name,
                        "continent_ref": continent_ref,
                        "governing_style": choose_governing_style(context.rng),
                        "is_locked": context.settings.lock_generated_political,
                    },
                )
                context.empire_refs.append(empire.ext_ref)
                context.increment("empires")

                for k_index in range(context.settings.kingdoms_per_empire):
                    k_name = unique_name(
                        context.rng,
                        context.used_names,
                        "Kingdom",
                        k_index,
                        KINGDOM_NAMES,
                    )
                    kingdom = hierarchy_service.create_kingdom(
                        context.world_ref,
                        {
                            "name": k_name,
                            "empire_ref": empire.ext_ref,
                            "stability_index": round(context.rng.uniform(0.35, 0.9), 2),
                            "is_locked": context.settings.lock_generated_political,
                        },
                    )
                    context.kingdom_refs.append(kingdom.ext_ref)
                    context.increment("kingdoms")
