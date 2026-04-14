from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventScope(str, Enum):
    WORLD = "world"
    CONTINENT = "continent"
    EMPIRE = "empire"
    KINGDOM = "kingdom"
    REGION = "region"
    SETTLEMENT = "settlement"

    @classmethod
    def from_value(cls, value: str | "EventScope") -> "EventScope":
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())


class EffectOperation(str, Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    SET = "set"

    @classmethod
    def from_value(cls, value: str | "EffectOperation") -> "EffectOperation":
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())


class EffectType(str, Enum):
    MIGRATION = "migration"
    RESOURCE = "resource"
    CONFLICT = "conflict"
    DISEASE = "disease"
    FAMINE = "famine"
    PROSPERITY = "prosperity"
    TRADE = "trade"
    SECURITY = "security"
    RELATIONSHIP_DENSITY = "relationship_density"
    RELATIONSHIP_STRESS = "relationship_stress"
    AGE_SHIFT = "age_shift"
    OCCUPATION_LABOR = "occupation_labor"
    OCCUPATION_SECURITY = "occupation_security"
    OCCUPATION_TRADE = "occupation_trade"
    OCCUPATION_KNOWLEDGE = "occupation_knowledge"
    BIOME_OVERRIDE = "biome_override"
    NARRATIVE_HOOK = "narrative_hook"
    TENSION_LABEL = "tension_label"


class ChainPolicy(str, Enum):
    CASCADE = "cascade"
    STOP = "stop"


@dataclass(frozen=True)
class EventDslCondition:
    key: str
    operator: str
    value: Any

    def evaluate(self, context: dict[str, Any]) -> bool:
        current = context.get(self.key)
        if self.operator == "eq":
            return current == self.value
        if self.operator == "neq":
            return current != self.value
        if self.operator == "gt":
            return isinstance(current, (int, float)) and current > self.value
        if self.operator == "gte":
            return isinstance(current, (int, float)) and current >= self.value
        if self.operator == "lt":
            return isinstance(current, (int, float)) and current < self.value
        if self.operator == "lte":
            return isinstance(current, (int, float)) and current <= self.value
        if self.operator == "contains":
            return isinstance(current, (list, tuple, set, str)) and self.value in current
        return False


@dataclass(frozen=True)
class EventDslEffect:
    effect_type: str
    magnitude: float = 0.0
    operation: EffectOperation = EffectOperation.ADD
    chain: tuple["EventDslEffect", ...] = ()
    value: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EventDslEffect":
        chain_payload = payload.get("chain", ())
        chained: list[EventDslEffect] = []
        if isinstance(chain_payload, list):
            for item in chain_payload:
                if isinstance(item, dict):
                    chained.append(cls.from_dict(item))
        return cls(
            effect_type=str(payload.get("effect_type", "")).strip() or EffectType.PROSPERITY.value,
            magnitude=float(payload.get("magnitude", 0.0)),
            operation=EffectOperation.from_value(
                str(payload.get("operation", EffectOperation.ADD.value))
            ),
            chain=tuple(chained),
            value=(str(payload["value"]) if payload.get("value") is not None else None),
        )


@dataclass(frozen=True)
class EventChain:
    root: EventDslEffect
    policy: ChainPolicy = ChainPolicy.CASCADE


@dataclass(frozen=True)
class EventOccurrence:
    name: str
    scope: EventScope | str
    target_ref: str | None
    effects: tuple[EventDslEffect, ...] | list[EventDslEffect]
    tags: tuple[str, ...] = ()
    notes: str = ""
    stage: str = "active"


@dataclass(frozen=True)
class EventSeedInput:
    name: str
    scope: EventScope
    target_ref: str | None = None
    effects: tuple[EventDslEffect, ...] = ()
    tags: tuple[str, ...] = ()
    notes: str = ""
    stage: str = "active"

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, stage: str = "active") -> "EventSeedInput":
        effects_payload = payload.get("effects", ())
        effects: list[EventDslEffect] = []
        if isinstance(effects_payload, list):
            for item in effects_payload:
                if isinstance(item, dict):
                    effects.append(EventDslEffect.from_dict(item))
        tags_payload = payload.get("tags", ())
        tags: tuple[str, ...]
        if isinstance(tags_payload, str):
            tags = tuple(tag.strip() for tag in tags_payload.split(",") if tag.strip())
        elif isinstance(tags_payload, list):
            tags = tuple(str(tag).strip() for tag in tags_payload if str(tag).strip())
        else:
            tags = ()
        return cls(
            name=str(payload.get("name", "Generated Event")).strip() or "Generated Event",
            scope=EventScope.from_value(str(payload.get("scope", EventScope.WORLD.value))),
            target_ref=(str(payload["target_ref"]).strip() if payload.get("target_ref") else None),
            effects=tuple(effects),
            tags=tags,
            notes=str(payload.get("notes", "")).strip(),
            stage=str(payload.get("stage", stage)).strip() or stage,
        )

    def instantiate(self) -> EventOccurrence:
        return EventOccurrence(
            name=self.name,
            scope=self.scope,
            target_ref=self.target_ref,
            effects=self.effects,
            tags=self.tags,
            notes=self.notes,
            stage=self.stage,
        )


@dataclass(frozen=True)
class EventDslDefinition:
    name: str
    scope: EventScope | str
    default_effects: tuple[EventDslEffect, ...] = ()
    default_tags: tuple[str, ...] = ()
    default_notes: str = ""
    enabled: bool = True

    def instantiate(self, target_ref: str | None = None) -> EventOccurrence:
        return EventOccurrence(
            name=self.name,
            scope=EventScope.from_value(self.scope),
            target_ref=target_ref,
            effects=self.default_effects,
            tags=self.default_tags,
            notes=self.default_notes,
            stage="active",
        )


@dataclass(frozen=True)
class EventSeedTrigger:
    definition_ref: str
    scope: EventScope
    target_ref: str | None = None


@dataclass(frozen=True)
class EventDslNode:
    name: str
    scope: EventScope
    conditions: tuple[EventDslCondition, ...] = ()
    effects: tuple[EventDslEffect, ...] = ()
    chained_event_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EventDslBundle:
    nodes: tuple[EventDslNode, ...] = ()


@dataclass(frozen=True)
class WorldEventDslPayload:
    active_events: tuple[EventSeedInput, ...] = ()
    historical_events: tuple[EventSeedInput, ...] = ()
    definitions: tuple[EventDslDefinition, ...] = ()


@dataclass(frozen=True)
class ResolvedEventImpact:
    source_event: str
    scope: EventScope
    target_ref: str | None
    effect_type: str
    magnitude: float
    operation: EffectOperation
    value: str | None = None
    tags: tuple[str, ...] = ()
    notes: str = ""


# Backward-compatible aliases for older naming style.
Scope = EventScope
EventEffect = EventDslEffect
EventCondition = EventDslCondition
EventEffectType = EffectType
