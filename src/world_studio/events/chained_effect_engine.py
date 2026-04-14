from __future__ import annotations

from world_studio.events.event_dsl_models import EventDslDefinition, EventDslEffect, EventOccurrence


class ChainedEffectEngine:
    """Flatten chained effects into linear impacts."""

    def resolve_occurrence(self, event: EventOccurrence) -> list[EventDslEffect]:
        resolved: list[EventDslEffect] = []
        for effect in event.effects:
            self._walk(effect, resolved, depth=0)
        return resolved

    def resolve_definition(
        self,
        definition: EventDslDefinition,
        *,
        target_ref: str | None = None,
    ) -> list[EventDslEffect]:
        return self.resolve_occurrence(definition.instantiate(target_ref=target_ref))

    def _walk(
        self,
        effect: EventDslEffect,
        sink: list[EventDslEffect],
        *,
        depth: int,
    ) -> None:
        if depth > 8:
            return
        sink.append(effect)
        for chained in effect.chain:
            self._walk(chained, sink, depth=depth + 1)

