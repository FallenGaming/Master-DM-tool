from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import (
    FIRST_NAMES,
    GOAL_FRAGMENTS,
    FLAW_FRAGMENTS,
    SURNAME_ROOTS,
)


class NpcGenerator:
    def generate(self, social_service: object, context: GenerationContext) -> None:
        for settlement_ref in context.settlement_refs:
            population = context.settlement_population.get(settlement_ref, 200)
            min_npcs = context.settings.npcs_per_settlement_min
            max_npcs = context.settings.npcs_per_settlement_max
            target = max(min_npcs, min(max_npcs, max(3, population // 60)))

            for idx in range(target):
                race_ref = context.rng.choice(context.race_refs)
                occupation_ref = context.rng.choice(context.occupation_refs)
                display_name = f"{context.rng.choice(FIRST_NAMES)} {context.rng.choice(SURNAME_ROOTS)}"
                age_years = int(context.rng.triangular(16, 82, 34))
                notes = (
                    f"Generated resident. Goal: {context.rng.choice(GOAL_FRAGMENTS)}. "
                    f"Flaw: {context.rng.choice(FLAW_FRAGMENTS)}. "
                    f"Household seed: {settlement_ref}:{1 + idx // 4}."
                )

                npc = social_service.create_npc(
                    context.world_ref,
                    {
                        "display_name": display_name,
                        "age_years": age_years,
                        "race_ref": race_ref,
                        "occupation_ref": occupation_ref,
                        "residence_node_ref": settlement_ref,
                        "health_index": round(context.rng.uniform(0.62, 1.0), 2),
                        "wealth_index": round(context.rng.uniform(0.15, 0.95), 2),
                        "notes": notes,
                        "is_locked": False,
                    },
                )
                context.npc_refs.append(npc.ext_ref)
                context.increment("npcs")
