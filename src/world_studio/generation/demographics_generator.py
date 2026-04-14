from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import RACE_TEMPLATES


class DemographicsGenerator:
    def ensure_races(self, social_service: object, context: GenerationContext) -> None:
        existing = social_service.list_races()
        by_name = {race.name: race for race in existing}

        for name, lifespan, is_default in RACE_TEMPLATES:
            race = by_name.get(name)
            if race is None:
                race = social_service.create_race(
                    {
                        "name": name,
                        "lifespan_years": lifespan,
                        "is_default": is_default,
                    }
                )
            context.race_refs.append(race.ext_ref)

        if not context.race_refs:
            raise ValueError("No races available for generation.")
