from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import OCCUPATION_TEMPLATES


class OccupationAllocator:
    def ensure_occupations(self, social_service: object, context: GenerationContext) -> None:
        existing = social_service.list_occupations()
        by_name = {occupation.name: occupation for occupation in existing}

        for name, category, rarity in OCCUPATION_TEMPLATES:
            occupation = by_name.get(name)
            if occupation is None:
                occupation = social_service.create_occupation(
                    {
                        "name": name,
                        "category": category,
                        "rarity": rarity,
                    }
                )
            context.occupation_refs.append(occupation.ext_ref)

        if not context.occupation_refs:
            raise ValueError("No occupations available for generation.")
