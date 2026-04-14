from __future__ import annotations

from dataclasses import dataclass, field

from world_studio.generation.generation_models import GenerationContext
from world_studio.generation.generation_modifiers import ScopedModifier


@dataclass(frozen=True)
class SettlementFlavor:
    theme: str
    tension: str
    tags: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)


class SettlementFlavorBuilder:
    def build(
        self,
        settlement_name: str,
        settlement_ref: str,
        context: GenerationContext,
        region_ref: str,
        population: int,
    ) -> SettlementFlavor:
        modifier = context.modifiers.settlement.get(settlement_ref) or context.modifiers.scope(
            "region", region_ref
        )
        theme = self._theme(modifier, population)
        tension = self._tension(modifier)
        tags = sorted(set([*modifier.tags, tension]))
        hooks = self._hooks(settlement_name, theme, modifier)
        return SettlementFlavor(theme=theme, tension=tension, tags=tags, hooks=hooks)

    @staticmethod
    def _theme(modifier: ScopedModifier, population: int) -> str:
        if modifier.resource_bonus > 0.25:
            return "resource boom frontier"
        if modifier.migration_pressure > 0.25:
            return "migration crossroads"
        if modifier.safety_delta < -0.18:
            return "fortified border hold"
        if modifier.health_delta < -0.15:
            return "post-crisis recovery town"
        if population > 7000:
            return "dense urban market"
        if population > 1800:
            return "growing trade town"
        return "agricultural local hub"

    @staticmethod
    def _tension(modifier: ScopedModifier) -> str:
        if modifier.safety_delta < -0.22:
            return "warfront"
        if modifier.health_delta < -0.2:
            return "health-crisis"
        if modifier.relationship_stress > 0.2:
            return "civil-unrest"
        if modifier.prosperity_delta < -0.15:
            return "decline"
        if modifier.prosperity_delta > 0.2:
            return "ascendant"
        return "stable"

    @staticmethod
    def _hooks(settlement_name: str, theme: str, modifier: ScopedModifier) -> list[str]:
        hooks = [f"{settlement_name} is known as a {theme}."]
        hooks.extend(modifier.hooks[:2])
        if modifier.resource_bonus > 0.2:
            hooks.append(
                f"Competing interests in {settlement_name} seek control of newly valuable assets."
            )
        if modifier.migration_pressure > 0.2:
            hooks.append(
                f"Recent arrivals in {settlement_name} are reshaping local alliances and rivalries."
            )
        if modifier.health_delta < -0.15:
            hooks.append(
                f"Strained healers and elders in {settlement_name} guard records of past outbreaks."
            )
        if modifier.safety_delta < -0.15:
            hooks.append(
                f"{settlement_name} requests escorts and militias for nearby roads and outposts."
            )
        return hooks[:4]
