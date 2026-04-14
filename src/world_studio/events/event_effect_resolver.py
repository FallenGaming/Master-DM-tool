from __future__ import annotations

from world_studio.events.event_dsl_models import EventEffectType, ResolvedEventImpact


class EventEffectResolver:
    """Resolve one event occurrence into direct and chained impacts."""

    def resolve_occurrence(self, occurrence: object) -> list[ResolvedEventImpact]:
        if not hasattr(occurrence, "effects"):
            return []
        impacts: list[ResolvedEventImpact] = []
        for effect in list(getattr(occurrence, "effects")):
            impacts.extend(self._resolve_effect(effect, occurrence, depth=0))
        return impacts

    def _resolve_effect(
        self,
        effect: object,
        occurrence: object,
        *,
        depth: int,
    ) -> list[ResolvedEventImpact]:
        if depth > 8:
            return []
        raw_type = str(getattr(effect, "effect_type", "")).strip().lower()
        try:
            effect_type = EventEffectType(raw_type).value
        except ValueError:
            effect_type = raw_type or EventEffectType.PROSPERITY.value
        magnitude = float(getattr(effect, "magnitude", 0.0))
        impacts: list[ResolvedEventImpact] = [
            ResolvedEventImpact(
                source_event=str(getattr(occurrence, "name", "Generated Event")),
                scope=getattr(occurrence, "scope"),
                target_ref=getattr(occurrence, "target_ref"),
                effect_type=effect_type,
                magnitude=magnitude,
                operation=getattr(effect, "operation"),
                value=getattr(effect, "value", None),
                tags=tuple(getattr(occurrence, "tags", ())),
                notes=str(getattr(occurrence, "notes", "")),
            )
        ]
        for chained in tuple(getattr(effect, "chain", ())):
            impacts.extend(self._resolve_effect(chained, occurrence, depth=depth + 1))
        return impacts
