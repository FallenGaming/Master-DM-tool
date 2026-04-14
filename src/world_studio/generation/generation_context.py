from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenerationHistoryContext:
    active_event_refs: list[str] = field(default_factory=list)
    recent_event_refs: list[str] = field(default_factory=list)
    origin_notes: list[str] = field(default_factory=list)


@dataclass
class RegionNarrativeProfile:
    region_ref: str
    prosperity_tag: str = "stable"
    tension_tag: str = "calm"
    narrative_hooks: list[str] = field(default_factory=list)
    event_footprints: list[str] = field(default_factory=list)


@dataclass
class SettlementFlavor:
    settlement_ref: str
    identity: str = "general"
    prosperity_tag: str = "stable"
    decline_tag: str = "none"
    local_tension: str = "low"
    hooks: list[str] = field(default_factory=list)
    event_footprints: list[str] = field(default_factory=list)
