from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MapScale(str, Enum):
    WORLD = "world"
    CONTINENT = "continent"
    EMPIRE = "empire"
    KINGDOM = "kingdom"
    REGION = "region"
    LOCAL = "local"


@dataclass(frozen=True)
class SpatialAnchor:
    x: float
    y: float
    radius: float
    level: MapScale
    parent_ref: str | None = None


@dataclass
class SettlementSpatialState:
    settlement_ref: str
    region_ref: str | None
    x: float
    y: float
    route_degree: int = 0
    strategic_score: float = 0.0
    nearest_neighbor_distance: float = 0.0
    nearby_settlement_count: int = 0
    cluster_id: str = ""
    attraction_tags: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "route_degree": self.route_degree,
            "strategic_score": round(self.strategic_score, 3),
            "nearest_neighbor_distance": round(self.nearest_neighbor_distance, 2),
            "nearby_settlement_count": self.nearby_settlement_count,
            "attraction_tags": list(self.attraction_tags),
        }
