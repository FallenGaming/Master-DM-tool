from __future__ import annotations

from dataclasses import dataclass, field
from random import Random


@dataclass(frozen=True)
class GenerationSettings:
    seed: int = 42
    continent_count: int = 2
    empires_per_continent: int = 1
    kingdoms_per_empire: int = 2
    regions_per_kingdom: int = 2
    settlements_per_region: int = 3
    npcs_per_settlement_min: int = 8
    npcs_per_settlement_max: int = 14
    relationship_density: float = 0.08
    lock_generated_political: bool = False
    lock_generated_leaders: bool = False

    def normalized(self) -> "GenerationSettings":
        min_npcs = max(1, self.npcs_per_settlement_min)
        max_npcs = max(min_npcs, self.npcs_per_settlement_max)
        return GenerationSettings(
            seed=self.seed,
            continent_count=max(1, self.continent_count),
            empires_per_continent=max(1, self.empires_per_continent),
            kingdoms_per_empire=max(1, self.kingdoms_per_empire),
            regions_per_kingdom=max(1, self.regions_per_kingdom),
            settlements_per_region=max(1, self.settlements_per_region),
            npcs_per_settlement_min=min_npcs,
            npcs_per_settlement_max=max_npcs,
            relationship_density=min(max(self.relationship_density, 0.0), 1.0),
            lock_generated_political=self.lock_generated_political,
            lock_generated_leaders=self.lock_generated_leaders,
        )


@dataclass(frozen=True)
class GenerationRequest:
    world_ref: str
    settings: GenerationSettings


@dataclass
class GenerationRunSummary:
    world_ref: str
    seed_used: int
    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class GenerationContext:
    world_ref: str
    settings: GenerationSettings
    rng: Random
    used_names: set[str] = field(default_factory=set)

    continent_refs: list[str] = field(default_factory=list)
    empire_refs: list[str] = field(default_factory=list)
    kingdom_refs: list[str] = field(default_factory=list)
    region_refs: list[str] = field(default_factory=list)
    settlement_refs: list[str] = field(default_factory=list)
    settlement_population: dict[str, int] = field(default_factory=dict)
    npc_refs: list[str] = field(default_factory=list)

    race_refs: list[str] = field(default_factory=list)
    occupation_refs: list[str] = field(default_factory=list)

    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def increment(self, key: str, amount: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + amount
