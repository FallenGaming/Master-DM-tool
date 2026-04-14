from __future__ import annotations

from dataclasses import replace

from world_studio.events.event_effect_resolver import EventEffectResolver
from world_studio.generation.history_context_builder import HistoryContext
from world_studio.generation.generation_modifiers import GenerationModifierBundle


class EventAwareGenerationResolver:
    def resolve(
        self,
        context: object,
        history_context: HistoryContext,
    ) -> GenerationModifierBundle:
        bundle = GenerationModifierBundle()
        resolver = EventEffectResolver()
        for event_input in history_context.active_events:
            event = event_input.instantiate()
            bundle.apply_event_impacts(resolver.resolve_occurrence(event))
        for event_input in history_context.historical_events:
            event = event_input.instantiate()
            historical_impacts = resolver.resolve_occurrence(event)
            damped_impacts = [replace(impact, magnitude=impact.magnitude * 0.6) for impact in historical_impacts]
            bundle.apply_event_impacts(damped_impacts)
        return bundle
