from __future__ import annotations

import math
from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class RegionLayoutSpec:
    center_x: float
    center_y: float
    radius: float
    settlement_count: int
    cluster_count: int


class NodeLayoutGenerator:
    def generate_settlement_positions(
        self,
        *,
        rng: Random,
        region_ref: str,
        center_x: float,
        center_y: float,
        radius: float,
        settlement_count: int,
    ) -> list[tuple[float, float, str]]:
        if settlement_count <= 0:
            return []
        cluster_count = max(1, min(3, settlement_count // 2 if settlement_count > 2 else 1))
        spec = RegionLayoutSpec(
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            settlement_count=settlement_count,
            cluster_count=cluster_count,
        )
        cluster_centers = self._cluster_centers(rng, spec)
        min_spacing = max(12.0, radius * 0.18 / max(1, settlement_count))
        points: list[tuple[float, float, str]] = []
        for index in range(settlement_count):
            cluster_index = index % cluster_count
            cluster_x, cluster_y = cluster_centers[cluster_index]
            x, y = self._point_near_cluster(rng, cluster_x, cluster_y, radius)
            x, y = self._separate_from_neighbors(
                rng=rng,
                x=x,
                y=y,
                neighbors=[(px, py) for px, py, _ in points],
                min_spacing=min_spacing,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
            )
            points.append((round(x, 2), round(y, 2), f"{region_ref}:cluster-{cluster_index + 1}"))
        return points

    def generate_poi_position(
        self,
        *,
        rng: Random,
        anchor_x: float,
        anchor_y: float,
        spread: float,
    ) -> tuple[float, float]:
        angle = rng.uniform(0.0, math.tau)
        distance = rng.uniform(spread * 0.2, spread)
        return (
            round(anchor_x + math.cos(angle) * distance, 2),
            round(anchor_y + math.sin(angle) * distance, 2),
        )

    def _cluster_centers(self, rng: Random, spec: RegionLayoutSpec) -> list[tuple[float, float]]:
        centers: list[tuple[float, float]] = []
        ring_radius = max(8.0, spec.radius * 0.45)
        for idx in range(spec.cluster_count):
            angle = (math.tau * idx / spec.cluster_count) + rng.uniform(-0.35, 0.35)
            radial = ring_radius * rng.uniform(0.45, 1.0)
            centers.append(
                (
                    spec.center_x + math.cos(angle) * radial,
                    spec.center_y + math.sin(angle) * radial,
                )
            )
        return centers

    def _point_near_cluster(
        self,
        rng: Random,
        cluster_x: float,
        cluster_y: float,
        region_radius: float,
    ) -> tuple[float, float]:
        angle = rng.uniform(0.0, math.tau)
        local_radius = max(4.0, region_radius * 0.25)
        distance = rng.uniform(1.5, local_radius)
        return (
            cluster_x + math.cos(angle) * distance,
            cluster_y + math.sin(angle) * distance,
        )

    def _separate_from_neighbors(
        self,
        *,
        rng: Random,
        x: float,
        y: float,
        neighbors: list[tuple[float, float]],
        min_spacing: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> tuple[float, float]:
        px, py = x, y
        for _ in range(8):
            too_close = False
            for nx, ny in neighbors:
                distance = math.dist((px, py), (nx, ny))
                if distance >= min_spacing:
                    continue
                too_close = True
                angle = math.atan2(py - ny, px - nx)
                push = min_spacing - distance + rng.uniform(1.0, 4.5)
                px += math.cos(angle) * push
                py += math.sin(angle) * push
            if not too_close:
                break
        return self._clamp_to_region(px, py, center_x, center_y, radius)

    def _clamp_to_region(
        self,
        x: float,
        y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> tuple[float, float]:
        distance = math.dist((x, y), (center_x, center_y))
        if distance <= radius:
            return x, y
        if distance == 0:
            return center_x, center_y
        scale = radius / distance
        return (
            center_x + (x - center_x) * scale,
            center_y + (y - center_y) * scale,
        )
