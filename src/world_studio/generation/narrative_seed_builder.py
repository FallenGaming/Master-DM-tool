from __future__ import annotations

from world_studio.generation.generation_models import GenerationContext


class NarrativeSeedBuilder:
    def build(self, context: GenerationContext) -> None:
        for settlement_ref in context.settlement_refs:
            hooks = context.settlement_hooks.setdefault(settlement_ref, [])
            tags = context.settlement_tags.get(settlement_ref, [])
            theme = context.settlement_themes.get(settlement_ref, "resilient settlement")
            tension = context.settlement_tensions.get(settlement_ref, "steady")

            if "migration" in tags:
                hooks.append("New arrivals are straining old governance traditions.")
            if "conflict" in tags:
                hooks.append("Local leaders fear escalation from nearby political tensions.")
            if "disease" in tags:
                hooks.append("Healers and temples quietly track recurring outbreaks.")
            if "resource-boom" in tags:
                hooks.append("Competing interests maneuver for rights over new resources.")

            hooks.append(f"Settlement identity: {theme}; social climate: {tension}.")
            context.settlement_hooks[settlement_ref] = hooks[:8]
