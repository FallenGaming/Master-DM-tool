from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_rules import pick_relation_type


class RelationshipSeedGenerator:
    def generate(self, social_service: object, context: GenerationContext) -> None:
        npc_records = [social_service.get_npc(ref) for ref in context.npc_refs]
        npcs = [npc for npc in npc_records if npc is not None]
        if len(npcs) < 2:
            return

        target = max(1, int(len(npcs) * context.settings.relationship_density))
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
            social_service.create_relationship(
                context.world_ref,
                {
                    "source_npc_ref": source.ext_ref,
                    "target_npc_ref": target_npc.ext_ref,
                    "relation_type": relation_type.value,
                    "weight": round(context.rng.uniform(-0.7, 0.95), 2),
                    "history": (
                        f"Seeded tie between {source.display_name} and {target_npc.display_name}."
                    ),
                    "is_locked": False,
                },
            )
            seen_pairs.add(pair)
            context.increment("relationships")
