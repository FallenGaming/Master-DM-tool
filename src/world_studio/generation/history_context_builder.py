from __future__ import annotations

from dataclasses import dataclass, field

from world_studio.events.event_dsl_models import EventSeedInput
from world_studio.generation.generation_models import GenerationContext


@dataclass
class HistoryContext:
    active_events: list[EventSeedInput] = field(default_factory=list)
    historical_events: list[EventSeedInput] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class HistoryContextBuilder:
    def build(self, context: GenerationContext) -> HistoryContext:
        active_events = [event for event in context.settings.event_inputs if event.stage == "active"]
        historical_events = [
            *[event for event in context.settings.event_inputs if event.stage != "active"],
            *list(context.settings.historical_event_inputs),
        ]
        notes: list[str] = []
        if active_events or historical_events:
            notes.append(
                f"History context loaded: active={len(active_events)}, historical={len(historical_events)}."
            )
        if context.settings.world_tags:
            notes.append(f"World tags: {', '.join(context.settings.world_tags)}.")
        return HistoryContext(
            active_events=active_events,
            historical_events=historical_events,
            notes=notes,
        )
