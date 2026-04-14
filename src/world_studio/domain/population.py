from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from world_studio.domain.enums import RelationshipType


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Race:
    id: int | None
    ext_ref: str
    name: str
    lifespan_years: int
    is_default: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubRace:
    id: int | None
    ext_ref: str
    race_ref: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Occupation:
    id: int | None
    ext_ref: str
    name: str
    category: str
    rarity: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trait:
    id: int | None
    ext_ref: str
    name: str
    polarity: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Npc:
    id: int | None
    ext_ref: str
    world_ref: str
    display_name: str
    age_years: int
    race_ref: str
    subrace_ref: str | None
    occupation_ref: str | None
    residence_node_ref: str | None
    health_index: float = 1.0
    wealth_index: float = 0.5
    is_locked: bool = False
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_utc: datetime = field(default_factory=utc_now)
    updated_utc: datetime = field(default_factory=utc_now)


@dataclass
class Relationship:
    id: int | None
    ext_ref: str
    world_ref: str
    source_npc_ref: str
    target_npc_ref: str
    relation_type: RelationshipType
    weight: float
    history: list[str] = field(default_factory=list)
    is_locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
