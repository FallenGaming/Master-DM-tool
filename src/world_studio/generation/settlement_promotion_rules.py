from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from world_studio.domain.enums import SettlementType
from world_studio.domain.simulation import SimulationChange, SimulationPass, SimulationRun


@dataclass(frozen=True)
class SettlementSpatialMetrics:
    route_degree: int
    nearby_settlement_count: int
    nearest_neighbor_distance: float
    strategic_score: float


@dataclass(frozen=True)
class SettlementTransition:
    kind: SettlementType
    population: int
    prominence: str
    growth_pressure: float


class SettlementPromotionRules:
    _ORDER: tuple[SettlementType, ...] = (
        SettlementType.HAMLET,
        SettlementType.VILLAGE,
        SettlementType.TOWN,
        SettlementType.CITY,
        SettlementType.METROPOLIS,
    )
    _POP_THRESHOLDS: dict[SettlementType, int] = {
        SettlementType.HAMLET: 120,
        SettlementType.VILLAGE: 420,
        SettlementType.TOWN: 1700,
        SettlementType.CITY: 8200,
        SettlementType.METROPOLIS: 28000,
    }

    def evaluate_transition(
        self,
        *,
        settlement: Any,
        metrics: SettlementSpatialMetrics,
        days: int,
    ) -> SettlementTransition:
        route_bonus = min(0.45, metrics.route_degree * 0.06)
        clustering_bonus = min(0.25, metrics.nearby_settlement_count * 0.03)
        isolation_penalty = min(0.25, metrics.nearest_neighbor_distance / 650.0)
        resource_bias = (settlement.resource_index - 0.5) * 0.5
        safety_bias = (settlement.safety_index - 0.5) * 0.35
        strategic_bias = min(0.55, metrics.strategic_score * 0.55)
        daily_growth = (
            0.00035
            + route_bonus * 0.0007
            + clustering_bonus * 0.0005
            + resource_bias * 0.0008
            + safety_bias * 0.0005
            + strategic_bias * 0.0008
            - isolation_penalty * 0.0009
        )
        projected_population = max(20, int(round(settlement.population * (1.0 + daily_growth * days))))
        target_kind = self.kind_for_population(
            population=projected_population,
            route_degree=metrics.route_degree,
            strategic_score=metrics.strategic_score,
        )
        prominence = self.prominence_label(metrics)
        growth_pressure = round(daily_growth * 100.0, 3)
        return SettlementTransition(
            kind=target_kind,
            population=projected_population,
            prominence=prominence,
            growth_pressure=growth_pressure,
        )

    def kind_for_population(
        self,
        *,
        population: int,
        route_degree: int,
        strategic_score: float,
    ) -> SettlementType:
        adjusted = population + (route_degree * 180) + int(strategic_score * 2600)
        target = SettlementType.HAMLET
        for candidate in self._ORDER:
            if adjusted >= self._POP_THRESHOLDS[candidate]:
                target = candidate
        return target

    def prominence_label(self, metrics: SettlementSpatialMetrics) -> str:
        if metrics.route_degree >= 4 and metrics.strategic_score >= 0.65:
            return "trade_hub"
        if metrics.route_degree <= 1 and metrics.nearest_neighbor_distance >= 180:
            return "isolated_outpost"
        if metrics.nearby_settlement_count >= 4:
            return "dense_cluster"
        return "frontier"


class SettlementPromotionGenerator:
    def __init__(self, rules: SettlementPromotionRules | None = None) -> None:
        self._rules = rules or SettlementPromotionRules()

    def apply(self, hierarchy_service: object, context: Any) -> None:
        settlements = hierarchy_service.list_settlements(context.world_ref)
        by_region: dict[str, list[Any]] = defaultdict(list)
        for settlement in settlements:
            if settlement.region_ref:
                by_region[settlement.region_ref].append(settlement)
        for settlement in settlements:
            metrics = self._metrics_for(settlement, by_region.get(settlement.region_ref or "", []), context)
            transition = self._rules.evaluate_transition(
                settlement=settlement,
                metrics=metrics,
                days=120,
            )
            existing_map = self._map_section(settlement.metadata)
            existing_map.update(
                {
                    "route_degree": metrics.route_degree,
                    "nearby_settlement_count": metrics.nearby_settlement_count,
                    "nearest_neighbor_distance": round(metrics.nearest_neighbor_distance, 2),
                    "strategic_score": round(metrics.strategic_score, 3),
                    "prominence": transition.prominence,
                    "growth_pressure": transition.growth_pressure,
                }
            )
            updated = hierarchy_service.update_settlement(
                settlement.ext_ref,
                {
                    "name": settlement.name,
                    "region_ref": settlement.region_ref,
                    "kind": transition.kind.value,
                    "population": transition.population,
                    "resource_index": settlement.resource_index,
                    "safety_index": settlement.safety_index,
                    "x": settlement.x,
                    "y": settlement.y,
                    "metadata": {**settlement.metadata, "map": existing_map},
                    "is_locked": settlement.is_locked,
                },
            )
            context.settlement_population[settlement.ext_ref] = transition.population
            context.settlement_route_density[settlement.ext_ref] = metrics.route_degree
            if updated.kind != settlement.kind:
                context.notes.append(
                    f"{updated.name} shifted {settlement.kind.value}->{updated.kind.value} "
                    f"(routes={metrics.route_degree}, prominence={transition.prominence})."
                )

    def _metrics_for(
        self,
        settlement: Any,
        neighbors: list[Any],
        context: Any,
    ) -> SettlementSpatialMetrics:
        closest = float("inf")
        nearby = 0
        for neighbor in neighbors:
            if neighbor.ext_ref == settlement.ext_ref:
                continue
            distance = math.dist((settlement.x, settlement.y), (neighbor.x, neighbor.y))
            closest = min(closest, distance)
            if distance <= 110:
                nearby += 1
        if closest == float("inf"):
            closest = 9999.0
        route_degree = context.route_degree_by_settlement.get(settlement.ext_ref, 0)
        strategic_score = self._strategic_score(settlement, route_degree, nearby, closest)
        return SettlementSpatialMetrics(
            route_degree=route_degree,
            nearby_settlement_count=nearby,
            nearest_neighbor_distance=closest,
            strategic_score=strategic_score,
        )

    @staticmethod
    def _strategic_score(settlement: Any, route_degree: int, nearby: int, nearest: float) -> float:
        score = (
            (settlement.resource_index * 0.35)
            + (settlement.safety_index * 0.2)
            + min(0.4, route_degree * 0.09)
            + min(0.22, nearby * 0.04)
            - min(0.25, nearest / 900.0)
        )
        return max(0.0, min(1.0, round(score, 3)))

    @staticmethod
    def _map_section(metadata: dict[str, object]) -> dict[str, object]:
        raw = metadata.get("map")
        if isinstance(raw, dict):
            return dict(raw)
        return {}


class MapAwareSettlementPass(SimulationPass):
    name = "settlements"

    def __init__(self, hierarchy_repository: Any, rules: SettlementPromotionRules | None = None) -> None:
        self._hierarchy_repository = hierarchy_repository
        self._rules = rules or SettlementPromotionRules()

    def apply(self, run: SimulationRun, context: object | None = None) -> None:
        settlements = self._hierarchy_repository.list_settlements(run.world_ref)
        routes = self._hierarchy_repository.list_routes(run.world_ref)
        by_ref = {settlement.ext_ref: settlement for settlement in settlements}
        by_region: dict[str, list[Any]] = defaultdict(list)
        for settlement in settlements:
            if settlement.region_ref:
                by_region[settlement.region_ref].append(settlement)

        route_degree: dict[str, int] = defaultdict(int)
        for route in routes:
            if route.source_ref in by_ref:
                route_degree[route.source_ref] += 1
            if route.target_ref in by_ref:
                route_degree[route.target_ref] += 1

        for settlement in settlements:
            if settlement.is_locked:
                run.notes.append(f"settlements: skipped locked settlement {settlement.ext_ref}")
                continue
            metrics = self._metrics(settlement, by_region.get(settlement.region_ref or "", []), route_degree)
            transition = self._rules.evaluate_transition(
                settlement=settlement,
                metrics=metrics,
                days=run.simulated_days,
            )
            map_payload = self._map_section(settlement.metadata)
            map_payload.update(
                {
                    "route_degree": metrics.route_degree,
                    "nearby_settlement_count": metrics.nearby_settlement_count,
                    "nearest_neighbor_distance": round(metrics.nearest_neighbor_distance, 2),
                    "strategic_score": round(metrics.strategic_score, 3),
                    "prominence": transition.prominence,
                    "growth_pressure": transition.growth_pressure,
                    "status": "abandoned" if transition.population < 70 else "active",
                }
            )

            changed = False
            if transition.population != settlement.population:
                run.changes.append(
                    SimulationChange(
                        entity_type="settlement",
                        entity_ref=settlement.ext_ref,
                        field_name="population",
                        previous_value=str(settlement.population),
                        new_value=str(transition.population),
                        reason="map-aware growth pressure",
                    )
                )
                settlement.population = transition.population
                changed = True
            if transition.kind != settlement.kind:
                run.changes.append(
                    SimulationChange(
                        entity_type="settlement",
                        entity_ref=settlement.ext_ref,
                        field_name="kind",
                        previous_value=settlement.kind.value,
                        new_value=transition.kind.value,
                        reason="route-density and proximity promotion rules",
                    )
                )
                settlement.kind = transition.kind
                changed = True
            settlement.metadata = {**settlement.metadata, "map": map_payload}
            if changed and not run.preview_only:
                self._hierarchy_repository.upsert_settlement(settlement)
        run.notes.append(
            f"settlements: evaluated {len(settlements)} nodes with map-aware promotion rules."
        )

    def _metrics(
        self,
        settlement: Any,
        neighbors: list[Any],
        route_degree: dict[str, int],
    ) -> SettlementSpatialMetrics:
        closest = float("inf")
        nearby = 0
        for neighbor in neighbors:
            if neighbor.ext_ref == settlement.ext_ref:
                continue
            distance = math.dist((settlement.x, settlement.y), (neighbor.x, neighbor.y))
            closest = min(closest, distance)
            if distance <= 110:
                nearby += 1
        if closest == float("inf"):
            closest = 9999.0
        degree = route_degree.get(settlement.ext_ref, 0)
        strategic = SettlementPromotionGenerator._strategic_score(settlement, degree, nearby, closest)
        return SettlementSpatialMetrics(
            route_degree=degree,
            nearby_settlement_count=nearby,
            nearest_neighbor_distance=closest,
            strategic_score=strategic,
        )

    @staticmethod
    def _map_section(metadata: dict[str, object]) -> dict[str, object]:
        raw = metadata.get("map")
        if isinstance(raw, dict):
            return dict(raw)
        return {}
