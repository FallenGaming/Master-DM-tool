from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MapNodeView:
    ext_ref: str
    label: str
    node_type: str
    x: float
    y: float
    size_hint: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class MapEdgeView:
    ext_ref: str
    source_ref: str
    target_ref: str
    route_type: str
    weight: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class MapGraphProjection:
    world_ref: str
    nodes: list[MapNodeView]
    edges: list[MapEdgeView]

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)
