from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


class RouteGenerator:
    def generate(self, hierarchy_service: object, context: Any) -> None:
        settlements = hierarchy_service.list_settlements(context.world_ref)
        by_ref = {settlement.ext_ref: settlement for settlement in settlements}
        if len(settlements) < 2:
            return

        routes_created: set[tuple[str, str]] = set()
        route_degree: dict[str, int] = defaultdict(int)
        settlements_by_region: dict[str, list[Any]] = defaultdict(list)
        for settlement in settlements:
            if settlement.region_ref:
                settlements_by_region[settlement.region_ref].append(settlement)

        for region_ref, members in settlements_by_region.items():
            for settlement in members:
                nearest = self._nearest_neighbor(settlement, members)
                if nearest is None:
                    continue
                self._create_route(
                    hierarchy_service=hierarchy_service,
                    context=context,
                    source=settlement,
                    target=nearest,
                    routes_created=routes_created,
                    route_degree=route_degree,
                    route_type="road",
                    strategic_kind="intra_region",
                )

            if len(members) < 3:
                continue
            hub = max(members, key=lambda item: item.population)
            additional = sorted(
                [candidate for candidate in members if candidate.ext_ref != hub.ext_ref],
                key=lambda candidate: self._distance(hub, candidate),
            )[:2]
            for candidate in additional:
                self._create_route(
                    hierarchy_service=hierarchy_service,
                    context=context,
                    source=hub,
                    target=candidate,
                    routes_created=routes_created,
                    route_degree=route_degree,
                    route_type="trade_road",
                    strategic_kind="regional_hub",
                )

        regions_by_kingdom: dict[str, list[str]] = defaultdict(list)
        for region_ref, kingdom_ref in context.kingdom_ref_by_region.items():
            if kingdom_ref:
                regions_by_kingdom[kingdom_ref].append(region_ref)

        for kingdom_ref, region_refs in regions_by_kingdom.items():
            if len(region_refs) < 2:
                continue
            major_settlements: list[Any] = []
            for region_ref in region_refs:
                members = settlements_by_region.get(region_ref, [])
                if not members:
                    continue
                major_settlements.append(max(members, key=lambda item: item.population))
            for index in range(len(major_settlements) - 1):
                current = major_settlements[index]
                next_settlement = major_settlements[index + 1]
                self._create_route(
                    hierarchy_service=hierarchy_service,
                    context=context,
                    source=current,
                    target=next_settlement,
                    routes_created=routes_created,
                    route_degree=route_degree,
                    route_type="highway",
                    strategic_kind=f"kingdom_backbone:{kingdom_ref}",
                )

        context.route_degree_by_settlement.update(route_degree)
        for settlement_ref, degree in route_degree.items():
            context.settlement_route_density[settlement_ref] = degree
            settlement = by_ref.get(settlement_ref)
            if settlement is None:
                continue
            existing_map = self._map_section(settlement.metadata)
            existing_map["route_degree"] = degree
            hierarchy_service.update_settlement(
                settlement.ext_ref,
                {
                    "name": settlement.name,
                    "region_ref": settlement.region_ref,
                    "kind": settlement.kind.value,
                    "population": settlement.population,
                    "resource_index": settlement.resource_index,
                    "safety_index": settlement.safety_index,
                    "x": settlement.x,
                    "y": settlement.y,
                    "is_locked": settlement.is_locked,
                    "metadata": {**settlement.metadata, "map": existing_map},
                },
            )

    def _create_route(
        self,
        *,
        hierarchy_service: Any,
        context: Any,
        source: Any,
        target: Any,
        routes_created: set[tuple[str, str]],
        route_degree: dict[str, int],
        route_type: str,
        strategic_kind: str,
    ) -> None:
        pair = tuple(sorted((source.ext_ref, target.ext_ref)))
        if pair in routes_created:
            return
        routes_created.add(pair)
        distance = self._distance(source, target)
        travel_cost = max(0.5, round(distance / 70.0, 2))
        route = hierarchy_service.create_route(
            context.world_ref,
            {
                "name": f"{source.name} - {target.name}",
                "source_ref": source.ext_ref,
                "target_ref": target.ext_ref,
                "route_type": route_type,
                "travel_cost": travel_cost,
                "metadata": {
                    "map": {
                        "distance": round(distance, 2),
                        "strategic_kind": strategic_kind,
                        "source_region_ref": source.region_ref,
                        "target_region_ref": target.region_ref,
                    }
                },
                "is_locked": False,
            },
        )
        context.route_refs.append(route.ext_ref)
        context.increment("routes")
        route_degree[source.ext_ref] += 1
        route_degree[target.ext_ref] += 1

    def _nearest_neighbor(self, source: Any, candidates: list[Any]) -> Any | None:
        nearest: Any | None = None
        nearest_distance = float("inf")
        for candidate in candidates:
            if candidate.ext_ref == source.ext_ref:
                continue
            distance = self._distance(source, candidate)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = candidate
        return nearest

    @staticmethod
    def _distance(source: Any, target: Any) -> float:
        return math.dist((source.x, source.y), (target.x, target.y))

    @staticmethod
    def _map_section(metadata: dict[str, object]) -> dict[str, object]:
        raw = metadata.get("map")
        if isinstance(raw, dict):
            return dict(raw)
        return {}
