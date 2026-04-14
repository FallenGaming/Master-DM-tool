from __future__ import annotations

from world_studio.events.event_dsl_models import (
    EffectOperation,
    EventDslDefinition,
    EventDslEffect,
    EventOccurrence,
)
from world_studio.events.event_effect_resolver import EventEffectResolver
from world_studio.generation.generation_modifiers import GenerationModifierBundle


def test_chained_event_effects_resolve_and_accumulate() -> None:
    resolver = EventEffectResolver()
    event = EventOccurrence(
        name="Mineral Discovery",
        scope="region",
        target_ref="reg-1",
        effects=[
            EventDslEffect(
                effect_type="resource",
                magnitude=0.4,
                operation=EffectOperation.ADD,
                chain=(
                    EventDslEffect(
                        effect_type="migration",
                        magnitude=0.3,
                        operation=EffectOperation.ADD,
                        chain=(
                            EventDslEffect(
                                effect_type="occupation_trade",
                                magnitude=0.2,
                                operation=EffectOperation.ADD,
                            ),
                        ),
                    ),
                ),
            ),
        ],
    )

    impacts = resolver.resolve_occurrence(event)
    assert len(impacts) == 3
    assert sum(1 for effect in impacts if effect.effect_type == "resource") == 1
    assert sum(1 for effect in impacts if effect.effect_type == "migration") == 1
    assert sum(1 for effect in impacts if effect.effect_type == "occupation_trade") == 1

    bundle = GenerationModifierBundle()
    bundle.apply_event_impacts(impacts)
    assert bundle.scope("region", "reg-1").resource_bonus > 0
    assert bundle.scope("region", "reg-1").migration_pressure > 0
    assert bundle.scope("region", "reg-1").occupation_trade_bias > 0


def test_event_definition_compiles_to_occurrence() -> None:
    definition = EventDslDefinition(
        name="Plague Wave",
        scope="region",
        default_effects=(
            EventDslEffect(effect_type="disease", magnitude=0.5),
            EventDslEffect(effect_type="prosperity", magnitude=-0.2),
        ),
        default_tags=("plague", "decline"),
    )
    occurrence = definition.instantiate(target_ref="reg-2")
    assert occurrence.name == "Plague Wave"
    assert occurrence.scope == "region"
    assert occurrence.target_ref == "reg-2"
    assert len(occurrence.effects) == 2
    assert set(occurrence.tags) == {"plague", "decline"}
