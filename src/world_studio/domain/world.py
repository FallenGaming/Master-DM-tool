from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from world_studio.domain.enums import NodeType, SettlementType


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EntityBase:
    id: int | None
    ext_ref: str
    name: str
    is_locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_utc: datetime = field(default_factory=utc_now)
    updated_utc: datetime = field(default_factory=utc_now)


@dataclass
class World(EntityBase):
    description: str = ""
    active_ruleset_ref: str | None = None


@dataclass
class Continent(EntityBase):
    world_ref: str = ""
    climate_summary: str = ""


@dataclass
class Empire(EntityBase):
    world_ref: str = ""
    continent_ref: str | None = None
    governing_style: str = ""


@dataclass
class Kingdom(EntityBase):
    world_ref: str = ""
    empire_ref: str | None = None
    stability_index: float = 0.5


@dataclass
class Region(EntityBase):
    world_ref: str = ""
    kingdom_ref: str | None = None
    biome: str = ""


@dataclass
class SettlementNode(EntityBase):
    world_ref: str = ""
    region_ref: str | None = None
    kind: SettlementType = SettlementType.VILLAGE
    population: int = 100
    resource_index: float = 0.5
    safety_index: float = 0.5
    x: float = 0.0
    y: float = 0.0


@dataclass
class PointOfInterest(EntityBase):
    world_ref: str = ""
    region_ref: str | None = None
    node_type: NodeType = NodeType.POINT_OF_INTEREST
    x: float = 0.0
    y: float = 0.0
    description: str = ""


@dataclass
class RouteConnection(EntityBase):
    world_ref: str = ""
    source_ref: str = ""
    target_ref: str = ""
    route_type: str = "road"
    travel_cost: float = 1.0


@dataclass
class SnapshotRecord:
    id: int | None
    ext_ref: str
    world_ref: str
    name: str
    snapshot_json: str
    checksum: str
    created_utc: datetime = field(default_factory=utc_now)
