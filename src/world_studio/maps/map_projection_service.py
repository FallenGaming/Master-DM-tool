from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from world_studio.infrastructure.map_graph import MapEdgeView, MapGraphProjection, MapNodeView
from world_studio.maps.graph_layout_service import GraphLayoutService
from world_studio.maps.node_positioning_models import MapScale


@dataclass(frozen=True)
class _MapEntityNode:
    ref: str
    label: str
    node_type: str
    level: MapScale
    parent_ref: str | None
    x: float
    y: float
    size_hint: float
    metadata: dict[str, object]


class MapProjectionService:
    def __init__(
        self,
        hierarchy_service: Any,
        layout_service: GraphLayoutService | None = None,
    ) -> None:
        self._hierarchy_service = hierarchy_service
        self._layout = layout_service or GraphLayoutService()

    def build_projection(
        self,
        world_ref: str,
        *,
        scale: MapScale,
        focus_ref: str | None = None,
    ) -> MapGraphProjection:
        continents = self._hierarchy_service.list_continents(world_ref)
        empires = self._hierarchy_service.list_empires(world_ref)
        kingdoms = self._hierarchy_service.list_kingdoms(world_ref)
        regions = self._hierarchy_service.list_regions(world_ref)
        settlements = self._hierarchy_service.list_settlements(world_ref)
        pois = self._hierarchy_service.list_points_of_interest(world_ref)
        routes = self._hierarchy_service.list_routes(world_ref)

        regions_by_kingdom: dict[str, list[Any]] = defaultdict(list)
        for region in regions:
            if region.kingdom_ref:
                regions_by_kingdom[region.kingdom_ref].append(region)

        kingdoms_by_empire: dict[str, list[Any]] = defaultdict(list)
        for kingdom in kingdoms:
            if kingdom.empire_ref:
                kingdoms_by_empire[kingdom.empire_ref].append(kingdom)

        empires_by_continent: dict[str, list[Any]] = defaultdict(list)
        for empire in empires:
            if empire.continent_ref:
                empires_by_continent[empire.continent_ref].append(empire)

        settlements_by_region: dict[str, list[Any]] = defaultdict(list)
        for settlement in settlements:
            if settlement.region_ref:
                settlements_by_region[settlement.region_ref].append(settlement)

        pois_by_region: dict[str, list[Any]] = defaultdict(list)
        for poi in pois:
            if poi.region_ref:
                pois_by_region[poi.region_ref].append(poi)

        region_centers: dict[str, tuple[float, float]] = {}
        for region in regions:
            points = [
                (settlement.x, settlement.y)
                for settlement in settlements_by_region.get(region.ext_ref, [])
            ] + [(poi.x, poi.y) for poi in pois_by_region.get(region.ext_ref, [])]
            if points:
                region_centers[region.ext_ref] = (
                    round(sum(point[0] for point in points) / len(points), 2),
                    round(sum(point[1] for point in points) / len(points), 2),
                )
                continue
            region_map = self._map_metadata(region.metadata)
            anchor = region_map.get("anchor")
            if isinstance(anchor, dict):
                region_centers[region.ext_ref] = (
                    float(anchor.get("x", 0.0)),
                    float(anchor.get("y", 0.0)),
                )

        kingdom_centers = self._aggregate_centers(
            kingdoms,
            lambda kingdom: regions_by_kingdom.get(kingdom.ext_ref, []),
            region_centers,
            key_attr="ext_ref",
        )
        empire_centers = self._aggregate_centers(
            empires,
            lambda empire: kingdoms_by_empire.get(empire.ext_ref, []),
            kingdom_centers,
            key_attr="ext_ref",
        )
        continent_centers = self._aggregate_centers(
            continents,
            lambda continent: empires_by_continent.get(continent.ext_ref, []),
            empire_centers,
            key_attr="ext_ref",
        )

        nodes: dict[str, _MapEntityNode] = {}
        for continent in continents:
            x, y = continent_centers.get(continent.ext_ref, (0.0, 0.0))
            nodes[continent.ext_ref] = _MapEntityNode(
                ref=continent.ext_ref,
                label=continent.name,
                node_type="continent",
                level=MapScale.CONTINENT,
                parent_ref=None,
                x=x,
                y=y,
                size_hint=2.4,
                metadata=self._map_metadata(continent.metadata),
            )

        for empire in empires:
            x, y = empire_centers.get(empire.ext_ref, continent_centers.get(empire.continent_ref or "", (0.0, 0.0)))
            nodes[empire.ext_ref] = _MapEntityNode(
                ref=empire.ext_ref,
                label=empire.name,
                node_type="empire",
                level=MapScale.EMPIRE,
                parent_ref=empire.continent_ref,
                x=x,
                y=y,
                size_hint=2.0,
                metadata=self._map_metadata(empire.metadata),
            )

        for kingdom in kingdoms:
            x, y = kingdom_centers.get(kingdom.ext_ref, empire_centers.get(kingdom.empire_ref or "", (0.0, 0.0)))
            nodes[kingdom.ext_ref] = _MapEntityNode(
                ref=kingdom.ext_ref,
                label=kingdom.name,
                node_type="kingdom",
                level=MapScale.KINGDOM,
                parent_ref=kingdom.empire_ref,
                x=x,
                y=y,
                size_hint=1.7,
                metadata=self._map_metadata(kingdom.metadata),
            )

        for region in regions:
            x, y = region_centers.get(region.ext_ref, kingdom_centers.get(region.kingdom_ref or "", (0.0, 0.0)))
            nodes[region.ext_ref] = _MapEntityNode(
                ref=region.ext_ref,
                label=region.name,
                node_type="region",
                level=MapScale.REGION,
                parent_ref=region.kingdom_ref,
                x=x,
                y=y,
                size_hint=1.35,
                metadata=self._map_metadata(region.metadata),
            )

        for settlement in settlements:
            nodes[settlement.ext_ref] = _MapEntityNode(
                ref=settlement.ext_ref,
                label=settlement.name,
                node_type="settlement",
                level=MapScale.LOCAL,
                parent_ref=settlement.region_ref,
                x=settlement.x,
                y=settlement.y,
                size_hint=max(0.7, min(2.8, 0.7 + settlement.population / 18000.0)),
                metadata=self._map_metadata(settlement.metadata),
            )

        for poi in pois:
            nodes[poi.ext_ref] = _MapEntityNode(
                ref=poi.ext_ref,
                label=poi.name,
                node_type=poi.node_type.value,
                level=MapScale.LOCAL,
                parent_ref=poi.region_ref,
                x=poi.x,
                y=poi.y,
                size_hint=0.8,
                metadata=self._map_metadata(poi.metadata),
            )

        allowed_refs = self._allowed_refs(
            scale=scale,
            focus_ref=focus_ref,
            nodes=nodes,
            empires=empires,
            kingdoms=kingdoms,
            regions=regions,
            settlements=settlements,
            pois=pois,
        )
        raw_points = {ref: (node.x, node.y) for ref, node in nodes.items() if ref in allowed_refs}
        normalized = self._layout.normalize_coordinates(raw_points)

        node_views: list[MapNodeView] = []
        for ref in allowed_refs:
            node = nodes.get(ref)
            if node is None:
                continue
            nx, ny = normalized.get(ref, (node.x, node.y))
            node_views.append(
                MapNodeView(
                    ext_ref=node.ref,
                    label=node.label,
                    node_type=node.node_type,
                    x=nx,
                    y=ny,
                    size_hint=node.size_hint,
                    metadata={
                        **node.metadata,
                        "level": node.level.value,
                        "parent_ref": node.parent_ref,
                    },
                )
            )

        edge_views: list[MapEdgeView] = []
        for route in routes:
            if route.source_ref not in allowed_refs or route.target_ref not in allowed_refs:
                continue
            source = normalized.get(route.source_ref)
            target = normalized.get(route.target_ref)
            if source is None or target is None:
                continue
            edge_views.append(
                MapEdgeView(
                    ext_ref=route.ext_ref,
                    source_ref=route.source_ref,
                    target_ref=route.target_ref,
                    route_type=route.route_type,
                    weight=max(0.1, route.travel_cost),
                    metadata={"kind": "route", **self._map_metadata(route.metadata)},
                )
            )

        for node in node_views:
            parent_ref = str(node.metadata.get("parent_ref") or "")
            if not parent_ref or parent_ref not in allowed_refs:
                continue
            edge_views.append(
                MapEdgeView(
                    ext_ref=f"{parent_ref}->{node.ext_ref}",
                    source_ref=parent_ref,
                    target_ref=node.ext_ref,
                    route_type="contains",
                    weight=0.35,
                    metadata={"kind": "containment"},
                )
            )

        return MapGraphProjection(world_ref=world_ref, nodes=node_views, edges=edge_views)

    def _aggregate_centers(
        self,
        parents: list[Any],
        children_getter: Any,
        source_centers: dict[str, tuple[float, float]],
        *,
        key_attr: str,
    ) -> dict[str, tuple[float, float]]:
        result: dict[str, tuple[float, float]] = {}
        for parent in parents:
            children = children_getter(parent)
            points = [source_centers.get(getattr(child, key_attr)) for child in children]
            concrete = [point for point in points if point is not None]
            if concrete:
                result[parent.ext_ref] = (
                    round(sum(point[0] for point in concrete) / len(concrete), 2),
                    round(sum(point[1] for point in concrete) / len(concrete), 2),
                )
                continue
            map_data = self._map_metadata(parent.metadata)
            anchor = map_data.get("anchor")
            if isinstance(anchor, dict):
                result[parent.ext_ref] = (
                    float(anchor.get("x", 0.0)),
                    float(anchor.get("y", 0.0)),
                )
        return result

    def _allowed_refs(
        self,
        *,
        scale: MapScale,
        focus_ref: str | None,
        nodes: dict[str, _MapEntityNode],
        empires: list[Any],
        kingdoms: list[Any],
        regions: list[Any],
        settlements: list[Any],
        pois: list[Any],
    ) -> set[str]:
        if scale == MapScale.WORLD:
            return {
                ref
                for ref, node in nodes.items()
                if node.level in {MapScale.CONTINENT, MapScale.EMPIRE}
            }
        if scale == MapScale.CONTINENT:
            if not focus_ref:
                return {
                    ref
                    for ref, node in nodes.items()
                    if node.level in {MapScale.EMPIRE, MapScale.KINGDOM}
                }
            empire_refs = {empire.ext_ref for empire in empires if empire.continent_ref == focus_ref}
            kingdom_refs = {
                kingdom.ext_ref
                for kingdom in kingdoms
                if kingdom.empire_ref in empire_refs
            }
            return {focus_ref, *empire_refs, *kingdom_refs}
        if scale == MapScale.EMPIRE:
            if not focus_ref:
                return {
                    ref
                    for ref, node in nodes.items()
                    if node.level in {MapScale.KINGDOM, MapScale.REGION}
                }
            kingdom_refs = {
                kingdom.ext_ref
                for kingdom in kingdoms
                if kingdom.empire_ref == focus_ref
            }
            region_refs = {
                region.ext_ref
                for region in regions
                if region.kingdom_ref in kingdom_refs
            }
            return {focus_ref, *kingdom_refs, *region_refs}
        if scale == MapScale.KINGDOM:
            if not focus_ref:
                return {
                    ref
                    for ref, node in nodes.items()
                    if node.level in {MapScale.REGION, MapScale.LOCAL}
                }
            region_refs = {
                region.ext_ref
                for region in regions
                if region.kingdom_ref == focus_ref
            }
            settlement_refs = {
                settlement.ext_ref
                for settlement in settlements
                if settlement.region_ref in region_refs
            }
            return {focus_ref, *region_refs, *settlement_refs}
        if scale == MapScale.REGION:
            if not focus_ref:
                return {ref for ref, node in nodes.items() if node.level == MapScale.LOCAL}
            settlement_refs = {
                settlement.ext_ref
                for settlement in settlements
                if settlement.region_ref == focus_ref
            }
            poi_refs = {poi.ext_ref for poi in pois if poi.region_ref == focus_ref}
            return {focus_ref, *settlement_refs, *poi_refs}
        if scale == MapScale.LOCAL and focus_ref:
            nearby = {focus_ref}
            for settlement in settlements:
                if settlement.ext_ref == focus_ref:
                    focus_region = settlement.region_ref
                    nearby.add(settlement.ext_ref)
                    for candidate in settlements:
                        if candidate.region_ref == focus_region:
                            nearby.add(candidate.ext_ref)
                    for poi in pois:
                        if poi.region_ref == focus_region:
                            nearby.add(poi.ext_ref)
                    break
            return nearby
        return set(nodes.keys())

    @staticmethod
    def _map_metadata(metadata: dict[str, Any]) -> dict[str, object]:
        raw = metadata.get("map")
        if isinstance(raw, dict):
            return dict(raw)
        return {}
