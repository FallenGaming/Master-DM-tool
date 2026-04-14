from __future__ import annotations

from dataclasses import dataclass, field

from world_studio.events.event_dsl_models import EffectOperation, EventScope, ResolvedEventImpact

ScopeKey = tuple[str, str | None]


@dataclass
class ScopedModifier:
    migration_delta: float = 0.0
    prosperity_delta: float = 0.0
    health_delta: float = 0.0
    safety_delta: float = 0.0
    resource_delta: float = 0.0
    relationship_tension: float = 0.0
    relationship_density_multiplier: float = 1.0
    occupation_bias: dict[str, float] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    hooks: list[str] = field(default_factory=list)
    tension_label: str = "stable"
    age_shift_years: int = 0

    def population_multiplier(self) -> float:
        base = 1.0 + self.migration_delta + (self.prosperity_delta * 0.3) + (self.resource_delta * 0.2)
        return max(0.35, min(2.4, base))

    @property
    def migration_pressure(self) -> float:
        return self.migration_delta

    @property
    def resource_bonus(self) -> float:
        return self.resource_delta

    @property
    def relationship_stress(self) -> float:
        return self.relationship_tension

    @property
    def occupation_labor_bias(self) -> float:
        return self.occupation_bias.get("labor", 1.0)

    @property
    def occupation_security_bias(self) -> float:
        return self.occupation_bias.get("security", 1.0)

    @property
    def occupation_trade_bias(self) -> float:
        return self.occupation_bias.get("trade", 1.0)

    @property
    def occupation_knowledge_bias(self) -> float:
        return self.occupation_bias.get("knowledge", 1.0)

    def merge(self, other: "ScopedModifier") -> "ScopedModifier":
        merged = ScopedModifier(
            migration_delta=self.migration_delta + other.migration_delta,
            prosperity_delta=self.prosperity_delta + other.prosperity_delta,
            health_delta=self.health_delta + other.health_delta,
            safety_delta=self.safety_delta + other.safety_delta,
            resource_delta=self.resource_delta + other.resource_delta,
            relationship_tension=self.relationship_tension + other.relationship_tension,
            relationship_density_multiplier=(
                self.relationship_density_multiplier * other.relationship_density_multiplier
            ),
            occupation_bias=dict(self.occupation_bias),
            tags=set(self.tags),
            hooks=[*self.hooks, *other.hooks],
            tension_label=other.tension_label if other.tension_label != "stable" else self.tension_label,
            age_shift_years=self.age_shift_years + other.age_shift_years,
        )
        merged.tags.update(other.tags)
        for key, value in other.occupation_bias.items():
            merged.occupation_bias[key] = merged.occupation_bias.get(key, 1.0) * value
        return merged


@dataclass
class GenerationModifierBundle:
    world: ScopedModifier = field(default_factory=ScopedModifier)
    continent: dict[str, ScopedModifier] = field(default_factory=dict)
    empire: dict[str, ScopedModifier] = field(default_factory=dict)
    kingdom: dict[str, ScopedModifier] = field(default_factory=dict)
    region: dict[str, ScopedModifier] = field(default_factory=dict)
    settlement: dict[str, ScopedModifier] = field(default_factory=dict)
    event_footprints: list[str] = field(default_factory=list)
    biome_override: str | None = None

    def for_world(self) -> ScopedModifier:
        return self.world

    def for_continent(self, continent_ref: str) -> ScopedModifier:
        return self.world.merge(self.continent.get(continent_ref, ScopedModifier()))

    def for_region(self, region_ref: str) -> ScopedModifier:
        return self.world.merge(self.region.get(region_ref, ScopedModifier()))

    def for_settlement(self, settlement_ref: str | None) -> ScopedModifier:
        if not settlement_ref:
            return self.world
        regional = self.world
        specific = self.settlement.get(settlement_ref, ScopedModifier())
        return regional.merge(specific)

    def derive_settlement_modifier(self, region_ref: str, settlement_ref: str) -> ScopedModifier:
        regional = self.for_region(region_ref)
        existing = self.settlement.get(settlement_ref, ScopedModifier())
        merged = regional.merge(existing)
        self.settlement[settlement_ref] = merged
        return merged

    def scope(self, scope: str, target_ref: str | None) -> ScopedModifier:
        resolved_scope = EventScope.from_value(scope)
        if resolved_scope == EventScope.WORLD:
            return self.world
        if resolved_scope == EventScope.CONTINENT and target_ref:
            return self.for_continent(target_ref)
        if resolved_scope == EventScope.REGION and target_ref:
            return self.for_region(target_ref)
        if resolved_scope == EventScope.SETTLEMENT:
            return self.for_settlement(target_ref)
        if resolved_scope == EventScope.EMPIRE and target_ref:
            return self.world.merge(self.empire.get(target_ref, ScopedModifier()))
        if resolved_scope == EventScope.KINGDOM and target_ref:
            return self.world.merge(self.kingdom.get(target_ref, ScopedModifier()))
        return self.world

    def add_modifier(self, scope: EventScope, target_ref: str | None, modifier: ScopedModifier) -> None:
        if scope == EventScope.WORLD:
            self.world = self.world.merge(modifier)
            return
        if not target_ref:
            return
        bucket: dict[str, ScopedModifier]
        if scope == EventScope.CONTINENT:
            bucket = self.continent
        elif scope == EventScope.EMPIRE:
            bucket = self.empire
        elif scope == EventScope.KINGDOM:
            bucket = self.kingdom
        elif scope == EventScope.REGION:
            bucket = self.region
        elif scope == EventScope.SETTLEMENT:
            bucket = self.settlement
        else:
            return
        bucket[target_ref] = bucket.get(target_ref, ScopedModifier()).merge(modifier)

    def apply_event_impacts(self, impacts: list[ResolvedEventImpact]) -> None:
        for impact in impacts:
            scope = EventScope.from_value(impact.scope)
            target_ref = impact.target_ref
            modifier = ScopedModifier(tags=set(impact.tags))
            effect_type = str(impact.effect_type).strip().lower()
            operation = EffectOperation.from_value(impact.operation)

            if effect_type == "migration":
                modifier.migration_delta = self._apply_numeric(0.0, impact.magnitude, operation)
            elif effect_type == "resource":
                modifier.resource_delta = self._apply_numeric(0.0, impact.magnitude, operation)
                if impact.magnitude > 0:
                    modifier.tags.add("resource-boom")
            elif effect_type == "prosperity":
                modifier.prosperity_delta = self._apply_numeric(0.0, impact.magnitude, operation)
            elif effect_type == "trade":
                modifier.prosperity_delta = self._apply_numeric(0.0, impact.magnitude * 0.5, operation)
                modifier.occupation_bias["trade"] = self._apply_numeric(1.0, impact.magnitude, operation)
            elif effect_type == "security":
                modifier.safety_delta = self._apply_numeric(0.0, impact.magnitude, operation)
            elif effect_type == "conflict":
                modifier.safety_delta = self._apply_numeric(0.0, -abs(impact.magnitude), EffectOperation.ADD)
                modifier.relationship_tension = self._apply_numeric(
                    0.0, abs(impact.magnitude), EffectOperation.ADD
                )
                modifier.tags.add("conflict")
            elif effect_type in {"disease", "famine"}:
                modifier.health_delta = self._apply_numeric(0.0, -abs(impact.magnitude), EffectOperation.ADD)
                modifier.tags.add(effect_type)
            elif effect_type == "relationship_density":
                modifier.relationship_density_multiplier = max(
                    0.1,
                    self._apply_numeric(1.0, impact.magnitude, operation),
                )
            elif effect_type == "relationship_stress":
                modifier.relationship_tension = self._apply_numeric(0.0, impact.magnitude, operation)
            elif effect_type == "age_shift":
                modifier.age_shift_years = int(round(impact.magnitude))
            elif effect_type == "occupation_labor":
                modifier.occupation_bias["labor"] = self._apply_numeric(1.0, impact.magnitude, operation)
            elif effect_type == "occupation_security":
                modifier.occupation_bias["security"] = self._apply_numeric(1.0, impact.magnitude, operation)
            elif effect_type == "occupation_trade":
                modifier.occupation_bias["trade"] = self._apply_numeric(1.0, impact.magnitude, operation)
            elif effect_type == "occupation_knowledge":
                modifier.occupation_bias["knowledge"] = self._apply_numeric(1.0, impact.magnitude, operation)
            elif effect_type == "biome_override":
                if impact.value:
                    self.biome_override = impact.value
            elif effect_type == "narrative_hook":
                modifier.hooks.append(impact.value or f"Event pressure from {impact.source_event}")
            elif effect_type == "tension_label":
                modifier.tension_label = impact.value or modifier.tension_label

            if effect_type:
                modifier.tags.add(effect_type)
            self.add_modifier(scope, target_ref, modifier)
            location = target_ref or "global"
            self.event_footprints.append(f"{impact.source_event}:{scope.value}:{location}:{effect_type}")

    @staticmethod
    def _apply_numeric(current: float, value: float, operation: EffectOperation) -> float:
        if operation == EffectOperation.SET:
            return value
        if operation == EffectOperation.MULTIPLY:
            if current == 0.0:
                return value
            return current * value
        return current + value

