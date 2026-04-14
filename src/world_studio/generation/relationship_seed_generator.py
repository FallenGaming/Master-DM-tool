from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import pick_relation_type


class RelationshipSeedGenerator:
    def generate(self, social_service: object, context: GenerationContext) -> None:
        npc_records = [social_service.get_npc(ref) for ref in context.npc_refs]
        npcs = [npc for npc in npc_records if npc is not None]
        if len(npcs) < 2:
            return

        target = max(
            1,
            int(
                len(npcs)
                * context.settings.relationship_density
                * context.modifiers.world.relationship_density_multiplier
            ),
        )
        seen_pairs: set[tuple[str, str]] = set()

        attempts = 0
        while context.counts.get("relationships", 0) < target and attempts < target * 12:
            attempts += 1
            source = context.rng.choice(npcs)
            target_npc = context.rng.choice(npcs)
            if source.ext_ref == target_npc.ext_ref:
                continue
            pair = (source.ext_ref, target_npc.ext_ref)
            reverse = (target_npc.ext_ref, source.ext_ref)
            if pair in seen_pairs or reverse in seen_pairs:
                continue

            relation_type = pick_relation_type(context.rng)
            tension_label = context.modifiers.world.tension_label
            weight_min = -0.7
            weight_max = 0.95
            if tension_label in {"warfront", "civil-unrest", "raider-threat"}:
                weight_min = -0.95
                weight_max = 0.7
            social_service.create_relationship(
                context.world_ref,
                {
                    "source_npc_ref": source.ext_ref,
                    "target_npc_ref": target_npc.ext_ref,
                    "relation_type": relation_type.value,
                    "weight": round(context.rng.uniform(weight_min, weight_max), 2),
                    "history": (
                        f"Seeded tie between {source.display_name} and {target_npc.display_name}. "
                        f"Regional pressure profile: {tension_label}."
                    ),
                    "is_locked": False,
                },
            )
            seen_pairs.add(pair)
            context.increment("relationships")
