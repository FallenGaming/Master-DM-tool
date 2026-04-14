from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutBounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return max(1.0, self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return max(1.0, self.max_y - self.min_y)


class GraphLayoutService:
    def distance(self, source: tuple[float, float], target: tuple[float, float]) -> float:
        return math.dist(source, target)

    def normalize_coordinates(
        self,
        points: dict[str, tuple[float, float]],
        *,
        target_extent: float = 900.0,
    ) -> dict[str, tuple[float, float]]:
        if not points:
            return {}
        xs = [point[0] for point in points.values()]
        ys = [point[1] for point in points.values()]
        bounds = LayoutBounds(min(xs), min(ys), max(xs), max(ys))
        max_dim = max(bounds.width, bounds.height)
        if max_dim <= 0:
            max_dim = 1.0
        scale = target_extent / max_dim
        center_x = (bounds.min_x + bounds.max_x) / 2.0
        center_y = (bounds.min_y + bounds.max_y) / 2.0
        normalized: dict[str, tuple[float, float]] = {}
        for ref, (x, y) in points.items():
            normalized[ref] = (
                round((x - center_x) * scale, 2),
                round((y - center_y) * scale, 2),
            )
        return normalized
