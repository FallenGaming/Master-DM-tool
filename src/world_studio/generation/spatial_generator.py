from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from world_studio.maps.node_positioning_models import MapScale, SpatialAnchor


class SpatialGenerator:
    def generate(self, hierarchy_service: object, context: Any) -> None:
        continents = {item.ext_ref: item for item in hierarchy_service.list_continents(context.world_ref)}
        empires = {item.ext_ref: item for item in hierarchy_service.list_empires(context.world_ref)}
        kingdoms = {item.ext_ref: item for item in hierarchy_service.list_kingdoms(context.world_ref)}
        regions = {item.ext_ref: item for item in hierarchy_service.list_regions(context.world_ref)}

        continent_anchors = self._scatter_on_ring(
            refs=context.continent_refs,
            center=(0.0, 0.0),
            base_radius=780.0,
            spread=180.0,
            rng=context.rng,
            level=MapScale.CONTINENT,
            parent_ref=None,
        )
        for ref, anchor in continent_anchors.items():
            context.continent_centers[ref] = (anchor.x, anchor.y)
            if ref in continents:
                self._persist_anchor(
                    update_method=hierarchy_service.update_continent,
                    entity=continents[ref],
                    anchor=anchor,
                    extras={"world_ref": context.world_ref},
                )

        empires_by_continent: dict[str, list[str]] = defaultdict(list)
        for empire_ref in context.empire_refs:
            continent_ref = context.continent_ref_by_empire.get(empire_ref)
            if continent_ref:
                empires_by_continent[continent_ref].append(empire_ref)

        empire_anchors: dict[str, SpatialAnchor] = {}
        for continent_ref, empire_refs in empires_by_continent.items():
            center = context.continent_centers.get(continent_ref, (0.0, 0.0))
            empire_anchors.update(
                self._scatter_on_ring(
                    refs=empire_refs,
                    center=center,
                    base_radius=260.0,
                    spread=90.0,
                    rng=context.rng,
                    level=MapScale.EMPIRE,
                    parent_ref=continent_ref,
                )
            )
        for ref, anchor in empire_anchors.items():
            context.empire_centers[ref] = (anchor.x, anchor.y)
            if ref in empires:
                self._persist_anchor(
                    update_method=hierarchy_service.update_empire,
                    entity=empires[ref],
                    anchor=anchor,
                    extras={
                        "world_ref": context.world_ref,
                        "continent_ref": context.continent_ref_by_empire.get(ref),
                    },
                )

        kingdoms_by_empire: dict[str, list[str]] = defaultdict(list)
        for kingdom_ref in context.kingdom_refs:
            empire_ref = context.empire_ref_by_kingdom.get(kingdom_ref)
            if empire_ref:
                kingdoms_by_empire[empire_ref].append(kingdom_ref)

        kingdom_anchors: dict[str, SpatialAnchor] = {}
        for empire_ref, kingdom_refs in kingdoms_by_empire.items():
            center = context.empire_centers.get(empire_ref, (0.0, 0.0))
            kingdom_anchors.update(
                self._scatter_on_ring(
                    refs=kingdom_refs,
                    center=center,
                    base_radius=180.0,
                    spread=75.0,
                    rng=context.rng,
                    level=MapScale.KINGDOM,
                    parent_ref=empire_ref,
                )
            )
        for ref, anchor in kingdom_anchors.items():
            context.kingdom_centers[ref] = (anchor.x, anchor.y)
            if ref in kingdoms:
                self._persist_anchor(
                    update_method=hierarchy_service.update_kingdom,
                    entity=kingdoms[ref],
                    anchor=anchor,
                    extras={
                        "world_ref": context.world_ref,
                        "empire_ref": context.empire_ref_by_kingdom.get(ref),
                    },
                )

        regions_by_kingdom: dict[str, list[str]] = defaultdict(list)
        for region_ref in context.region_refs:
            kingdom_ref = context.kingdom_ref_by_region.get(region_ref)
            if kingdom_ref:
                regions_by_kingdom[kingdom_ref].append(region_ref)

        region_anchors: dict[str, SpatialAnchor] = {}
        for kingdom_ref, region_refs in regions_by_kingdom.items():
            center = context.kingdom_centers.get(kingdom_ref, (0.0, 0.0))
            region_anchors.update(
                self._scatter_on_ring(
                    refs=region_refs,
                    center=center,
                    base_radius=120.0,
                    spread=55.0,
                    rng=context.rng,
                    level=MapScale.REGION,
                    parent_ref=kingdom_ref,
                )
            )
        for ref, anchor in region_anchors.items():
            context.region_centers[ref] = (anchor.x, anchor.y)
            context.region_radii[ref] = anchor.radius
            if ref in regions:
                self._persist_anchor(
                    update_method=hierarchy_service.update_region,
                    entity=regions[ref],
                    anchor=anchor,
                    extras={
                        "world_ref": context.world_ref,
                        "kingdom_ref": context.kingdom_ref_by_region.get(ref),
                    },
                )

    def _scatter_on_ring(
        self,
        *,
        refs: list[str],
        center: tuple[float, float],
        base_radius: float,
        spread: float,
        rng: Any,
        level: MapScale,
        parent_ref: str | None,
    ) -> dict[str, SpatialAnchor]:
        if not refs:
            return {}
        cx, cy = center
        anchors: dict[str, SpatialAnchor] = {}
        count = len(refs)
        for index, ref in enumerate(refs):
            angle = (math.tau * index / count) + rng.uniform(-0.35, 0.35)
            distance = base_radius + rng.uniform(-spread, spread)
            radius = max(30.0, spread * 0.9)
            anchors[ref] = SpatialAnchor(
                x=round(cx + math.cos(angle) * distance, 2),
                y=round(cy + math.sin(angle) * distance, 2),
                radius=round(radius, 2),
                level=level,
                parent_ref=parent_ref,
            )
        return anchors

    def _persist_anchor(
        self,
        *,
        update_method: Any,
        entity: Any,
        anchor: SpatialAnchor,
        extras: dict[str, object],
    ) -> None:
        map_metadata = {
            **self._map_section(entity.metadata),
            "level": anchor.level.value,
            "anchor": {
                "x": anchor.x,
                "y": anchor.y,
                "radius": anchor.radius,
            },
            "parent_ref": anchor.parent_ref,
        }
        update_method(
            entity.ext_ref,
            {
                "name": entity.name,
                "is_locked": entity.is_locked,
                "metadata": {**entity.metadata, "map": map_metadata},
                **extras,
            },
        )

    @staticmethod
    def _map_section(metadata: dict[str, object]) -> dict[str, object]:
        raw = metadata.get("map")
        if isinstance(raw, dict):
            return dict(raw)
        return {}
