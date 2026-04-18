from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from world_studio.domain.enums import RelationshipType
from world_studio.domain.population import Npc, Occupation, Relationship
from world_studio.domain.simulation import (
    SimulationChange,
    SimulationEngine,
    SimulationPass,
    SimulationRequest,
    SimulationRun,
)
from world_studio.domain.world import Region, SettlementNode, World
from world_studio.events.event_dsl_models import EventOccurrence, EventSeedInput
from world_studio.events.event_effect_resolver import EventEffectResolver
from world_studio.generation.generation_modifiers import GenerationModifierBundle, ScopedModifier
from world_studio.generation.settlement_promotion_rules import MapAwareSettlementPass


@dataclass(frozen=True)
class RegionCondition:
    prosperity: float
    danger: float
    resource: float
    political_tension: float
    disease: float


@dataclass(frozen=True)
class SettlementCondition:
    prosperity: float
    danger: float
    resource: float
    political_tension: float
    disease: float


@dataclass
class SimulationContext:
    world: World
    request: SimulationRequest
    duration_days: int
    preview_only: bool
    rng: random.Random
    modifiers: GenerationModifierBundle = field(default_factory=GenerationModifierBundle)
    route_degree_by_settlement: dict[str, int] = field(default_factory=dict)
    settlement_population: dict[str, int] = field(default_factory=dict)
    region_conditions: dict[str, RegionCondition] = field(default_factory=dict)
    settlement_conditions: dict[str, SettlementCondition] = field(default_factory=dict)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _stable_seed(world_ref: str, request: SimulationRequest) -> int:
    digest = hashlib.sha256(
        f"{world_ref}:{request.step.value}:{request.quantity}:{request.custom_days}:{request.preview_only}".encode(
            "utf-8"
        )
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


class PrecheckPass(SimulationPass):
    name = "precheck"

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        if context.world.is_locked:
            run.notes.append("precheck: world is locked, simulation changes are limited.")
        run.notes.append(
            f"precheck: world {context.world.ext_ref} validated for {context.duration_days} days."
        )


class EventResolutionPass(SimulationPass):
    name = "events"

    def __init__(self, resolver: EventEffectResolver | None = None) -> None:
        self._resolver = resolver or EventEffectResolver()

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        raw_events = context.world.metadata.get("active_events", ())
        events: list[EventOccurrence] = []
        for raw_event in tuple(raw_events):
            if isinstance(raw_event, EventOccurrence):
                events.append(raw_event)
            elif isinstance(raw_event, EventSeedInput):
                events.append(raw_event.instantiate())
            elif isinstance(raw_event, dict):
                events.append(EventSeedInput.from_dict(raw_event).instantiate())

        if not events:
            run.notes.append("events: no active events found.")
            return

        total_impacts = 0
        for occurrence in events:
            impacts = self._resolver.resolve_occurrence(occurrence)
            if not impacts:
                continue
            context.modifiers.apply_event_impacts(impacts)
            run.notes.append(
                f"events: resolved {occurrence.name} into {len(impacts)} impacts."
            )
            total_impacts += len(impacts)

        run.notes.append(
            f"events: applied {total_impacts} event impacts across {len(events)} occurrences."
        )


class RegionConditionPass(SimulationPass):
    name = "conditions"

    def __init__(self, hierarchy_service: Any) -> None:
        self._hierarchy_service = hierarchy_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        settlements = self._hierarchy_service.list_settlements(context.world.ext_ref)
        settlement_map = {settlement.ext_ref: settlement for settlement in settlements}
        routes = self._hierarchy_service.list_routes(context.world.ext_ref)

        route_degree: dict[str, int] = {}
        for settlement in settlements:
            route_degree[settlement.ext_ref] = 0
        for route in routes:
            if route.source_ref in route_degree:
                route_degree[route.source_ref] += 1
            if route.target_ref in route_degree:
                route_degree[route.target_ref] += 1

        context.route_degree_by_settlement = route_degree
        context.settlement_population = {settlement.ext_ref: settlement.population for settlement in settlements}

        world_modifier = context.modifiers.for_world()
        for region in self._hierarchy_service.list_regions(context.world.ext_ref):
            modifier = context.modifiers.for_region(region.ext_ref)
            prosperity = _clamp(0.45 + modifier.prosperity_delta + modifier.resource_bonus * 0.2)
            danger = _clamp(
                0.35 + max(0.0, -modifier.health_delta) * 0.3 + abs(modifier.relationship_stress) * 0.2
                - modifier.safety_delta * 0.2
            )
            resource = _clamp(0.45 + modifier.resource_bonus * 0.25)
            political_tension = _clamp(
                0.35 + modifier.relationship_stress * 0.3 + (0.2 if modifier.tension_label != "stable" else 0.0)
            )
            disease = _clamp(max(0.0, -modifier.health_delta) + (0.3 if "disease" in modifier.tags else 0.0))
            context.region_conditions[region.ext_ref] = RegionCondition(
                prosperity=prosperity,
                danger=danger,
                resource=resource,
                political_tension=political_tension,
                disease=disease,
            )

        for settlement in settlements:
            modifier = context.modifiers.for_settlement(settlement.ext_ref)
            region_condition = context.region_conditions.get(settlement.region_ref) if settlement.region_ref else None
            prosperity = _clamp(
                0.45
                + modifier.prosperity_delta
                + modifier.resource_bonus * 0.2
                + (region_condition.prosperity * 0.15 if region_condition else 0.0)
            )
            danger = _clamp(
                0.35
                + max(0.0, -modifier.health_delta) * 0.25
                + abs(modifier.relationship_stress) * 0.2
                - modifier.safety_delta * 0.2
                + (region_condition.danger * 0.15 if region_condition else 0.0)
            )
            resource = _clamp(
                0.45
                + modifier.resource_bonus * 0.25
                + (region_condition.resource * 0.15 if region_condition else 0.0)
            )
            political_tension = _clamp(
                0.35
                + modifier.relationship_stress * 0.2
                + (0.15 if modifier.tension_label != "stable" else 0.0)
                + (region_condition.political_tension * 0.15 if region_condition else 0.0)
            )
            disease = _clamp(
                max(0.0, -modifier.health_delta) + (0.25 if "disease" in modifier.tags else 0.0)
                + (region_condition.disease * 0.1 if region_condition else 0.0)
            )
            context.settlement_conditions[settlement.ext_ref] = SettlementCondition(
                prosperity=prosperity,
                danger=danger,
                resource=resource,
                political_tension=political_tension,
                disease=disease,
            )

        run.notes.append(
            f"conditions: aggregated conditions for {len(context.region_conditions)} regions and {len(context.settlement_conditions)} settlements."
        )


class NpcSimulationPass(SimulationPass):
    name = "npcs"

    def __init__(self, hierarchy_service: Any, social_service: Any) -> None:
        self._hierarchy_service = hierarchy_service
        self._social_service = social_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        occupations = tuple(self._social_service.list_occupations())
        races = tuple(self._social_service.list_races())
        settlement_map = {settlement.ext_ref: settlement for settlement in self._hierarchy_service.list_settlements(context.world.ext_ref)}
        npcs = list(self._social_service.list_npcs(context.world.ext_ref))
        deaths = 0
        updates = 0

        for npc in npcs:
            if npc.is_locked:
                run.notes.append(f"npcs: skipped locked npc {npc.ext_ref}")
                continue

            settlement = settlement_map.get(npc.residence_node_ref)
            condition = (
                context.settlement_conditions.get(npc.residence_node_ref)
                if npc.residence_node_ref
                else None
            )
            modifier = context.modifiers.for_settlement(npc.residence_node_ref)
            age_delta = self._age_increment(context, modifier)
            npc.age_years += age_delta

            if condition is not None:
                npc.health_index = _clamp(
                    npc.health_index
                    + modifier.health_delta * 0.08
                    - condition.disease * 0.2
                    + (condition.resource - 0.5) * 0.12
                )
            else:
                npc.health_index = _clamp(npc.health_index + modifier.health_delta * 0.05)

            npc.wealth_index = _clamp(
                npc.wealth_index
                + (condition.prosperity - 0.5) * 0.05 if condition is not None else npc.wealth_index
            )

            if self._should_die(npc, modifier, condition):
                self._social_service.delete_npc(npc.ext_ref)
                deaths += 1
                run.changes.append(
                    SimulationChange(
                        entity_type="npc",
                        entity_ref=npc.ext_ref,
                        field_name="alive",
                        previous_value="alive",
                        new_value="dead",
                        reason="NPC death due to health, age, or disease.",
                    )
                )
                continue

            payload: dict[str, object] = {
                "age_years": npc.age_years,
                "health_index": npc.health_index,
                "wealth_index": npc.wealth_index,
            }

            if npc.occupation_ref is None and occupations:
                occupation = self._select_occupation(occupations, modifier)
                if occupation is not None:
                    payload["occupation_ref"] = occupation.ext_ref
                    run.changes.append(
                        SimulationChange(
                            entity_type="npc",
                            entity_ref=npc.ext_ref,
                            field_name="occupation_ref",
                            previous_value="",
                            new_value=occupation.ext_ref,
                            reason="Assigned occupation from local economic conditions.",
                        )
                    )

            if settlement and self._should_relocate(npc, settlement, condition, context):
                target = self._best_migration_target(settlement, context, settlement_map)
                if target is not None and target.ext_ref != settlement.ext_ref:
                    payload["residence_node_ref"] = target.ext_ref
                    run.changes.append(
                        SimulationChange(
                            entity_type="npc",
                            entity_ref=npc.ext_ref,
                            field_name="residence_node_ref",
                            previous_value=str(npc.residence_node_ref or ""),
                            new_value=target.ext_ref,
                            reason="Relocated NPC to a more stable settlement.",
                        )
                    )

            self._social_service.update_npc(npc.ext_ref, payload)
            updates += 1

        run.notes.append(
            f"npcs: processed {len(npcs)} NPCs, removed {deaths}, updated {updates}."
        )

    def _age_increment(self, context: SimulationContext, modifier: ScopedModifier) -> int:
        years = int(round(context.duration_days / 365.0))
        years += modifier.age_shift_years
        return max(0, years)

    def _should_die(
        self,
        npc: Npc,
        modifier: ScopedModifier,
        condition: SettlementCondition | None,
    ) -> bool:
        lifespan = 80
        if npc.age_years > lifespan + 15:
            return True
        if npc.health_index <= 0.15:
            return True
        if condition and condition.disease > 0.75:
            return npc.health_index < 0.45
        return False

    def _select_occupation(self, occupations: tuple[Occupation, ...], modifier: ScopedModifier) -> Occupation | None:
        scores: list[tuple[float, Occupation]] = []
        for occupation in occupations:
            score = 1.0 / max(0.01, occupation.rarity)
            if occupation.category == "labor":
                score *= modifier.occupation_labor_bias
            elif occupation.category == "security":
                score *= modifier.occupation_security_bias
            elif occupation.category == "trade":
                score *= modifier.occupation_trade_bias
            elif occupation.category == "knowledge":
                score *= modifier.occupation_knowledge_bias
            scores.append((score, occupation))
        if not scores:
            return None
        return sorted(scores, key=lambda item: (-item[0], item[1].ext_ref))[0][1]

    def _should_relocate(
        self,
        npc: Npc,
        settlement: SettlementNode,
        condition: SettlementCondition | None,
        context: SimulationContext,
    ) -> bool:
        if condition is None:
            return False
        if condition.danger < 0.4:
            return False
        if settlement.is_locked:
            return False
        if context.rng.random() > 0.2:
            return False
        return True

    def _best_migration_target(
        self,
        settlement: SettlementNode,
        context: SimulationContext,
        settlement_map: dict[str, SettlementNode],
    ) -> SettlementNode | None:
        candidates = [
            candidate
            for candidate in settlement_map.values()
            if candidate.ext_ref != settlement.ext_ref and not candidate.is_locked
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda candidate: (
                context.settlement_conditions.get(candidate.ext_ref, SettlementCondition(0.5, 0.5, 0.5, 0.5, 0.0)).prosperity,
                candidate.resource_index,
                candidate.population,
            ),
            reverse=True,
        )
        return candidates[0] if candidates else None


class RelationshipUpdatePass(SimulationPass):
    name = "relationships"

    def __init__(self, social_service: Any) -> None:
        self._social_service = social_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        npcs = {npc.ext_ref: npc for npc in self._social_service.list_npcs(context.world.ext_ref)}
        relationships = list(self._social_service.list_relationships(context.world.ext_ref))
        tension = context.modifiers.for_world().relationship_stress
        adjusted = 0
        removed = 0
        added = 0

        for relationship in relationships:
            if relationship.is_locked:
                continue
            if relationship.source_npc_ref not in npcs or relationship.target_npc_ref not in npcs:
                self._social_service.delete_relationship(relationship.ext_ref)
                removed += 1
                continue

            delta = 0.003 if tension <= 0.25 else -0.004
            if relationship.relation_type in {RelationshipType.RIVAL, RelationshipType.ENEMY}:
                delta *= -1.0
            updated_weight = _clamp(relationship.weight + delta, -1.0, 1.0)
            if updated_weight != relationship.weight:
                relationship.weight = updated_weight
                relationship.history.append(f"adjusted by {delta:+.3f} during simulation")
                self._social_service.update_relationship(
                    relationship.ext_ref,
                    {
                        "weight": relationship.weight,
                        "history": relationship.history,
                    },
                )
                adjusted += 1

            if relationship.weight < -0.9:
                self._social_service.delete_relationship(relationship.ext_ref)
                removed += 1

        settlement_matches: dict[str, list[Npc]] = {}
        for npc in npcs.values():
            if npc.residence_node_ref:
                settlement_matches.setdefault(npc.residence_node_ref, []).append(npc)

        for settlement_ref, members in settlement_matches.items():
            if len(members) < 3:
                continue
            sources = [m for m in members if not m.is_locked]
            if not sources:
                continue
            pair = self._choose_pair(sources, context)
            if pair and context.rng.random() < 0.04:
                source, target = pair
                if not self._relationship_exists(source.ext_ref, target.ext_ref, relationships):
                    self._social_service.create_relationship(
                        context.world.ext_ref,
                        {
                            "source_npc_ref": source.ext_ref,
                            "target_npc_ref": target.ext_ref,
                            "relation_type": RelationshipType.FRIEND.value,
                            "weight": 0.1,
                            "history": ["formed during simulation"],
                        },
                    )
                    added += 1

        run.notes.append(
            f"relationships: adjusted {adjusted}, removed {removed}, created {added}."
        )

    def _choose_pair(self, npcs: list[Npc], context: SimulationContext) -> tuple[Npc, Npc] | None:
        if len(npcs) < 2:
            return None
        first = context.rng.choice(npcs)
        second = context.rng.choice([npc for npc in npcs if npc.ext_ref != first.ext_ref])
        return (first, second)

    def _relationship_exists(self, source_ref: str, target_ref: str, relationships: list[Relationship]) -> bool:
        for relationship in relationships:
            if {
                relationship.source_npc_ref,
                relationship.target_npc_ref,
            } == {source_ref, target_ref}:
                return True
        return False


class PopulationMigrationPass(SimulationPass):
    name = "migration"

    def __init__(self, hierarchy_service: Any, social_service: Any) -> None:
        self._hierarchy_service = hierarchy_service
        self._social_service = social_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        settlements = self._hierarchy_service.list_settlements(context.world.ext_ref)
        settlement_map = {settlement.ext_ref: settlement for settlement in settlements}
        npcs = list(self._social_service.list_npcs(context.world.ext_ref))
        births = 0
        migrations = 0

        npcs_by_settlement: dict[str, list[Npc]] = {}
        for npc in npcs:
            if npc.residence_node_ref:
                npcs_by_settlement.setdefault(npc.residence_node_ref, []).append(npc)

        races = self._social_service.list_races()
        default_race = races[0] if races else None

        for settlement in settlements:
            if settlement.is_locked:
                continue
            actual_population = len(npcs_by_settlement.get(settlement.ext_ref, []))
            if actual_population != settlement.population:
                self._hierarchy_service.update_settlement(
                    settlement.ext_ref,
                    {
                        "population": actual_population,
                        "kind": settlement.kind.value,
                        "region_ref": settlement.region_ref,
                        "name": settlement.name,
                        "resource_index": settlement.resource_index,
                        "safety_index": settlement.safety_index,
                        "x": settlement.x,
                        "y": settlement.y,
                        "metadata": settlement.metadata,
                        "is_locked": settlement.is_locked,
                    },
                )
                run.changes.append(
                    SimulationChange(
                        entity_type="settlement",
                        entity_ref=settlement.ext_ref,
                        field_name="population",
                        previous_value=str(settlement.population),
                        new_value=str(actual_population),
                        reason="Reconciled NPC population to settlement population.",
                    )
                )

            condition = context.settlement_conditions.get(settlement.ext_ref)
            if (
                default_race
                and condition is not None
                and condition.prosperity > 0.55
                and condition.resource > 0.45
                and len(npcs_by_settlement.get(settlement.ext_ref, [])) >= 2
                and context.rng.random() < 0.2
            ):
                newborn = self._create_newborn(settlement, default_race, context)
                births += 1
                run.changes.append(
                    SimulationChange(
                        entity_type="npc",
                        entity_ref=newborn.ext_ref,
                        field_name="created",
                        previous_value="",
                        new_value=newborn.display_name,
                        reason="Birth event under favorable settlement conditions.",
                    )
                )
                npcs_by_settlement.setdefault(settlement.ext_ref, []).append(newborn)

        for npc in [npc for npc in npcs if npc.residence_node_ref and npc.residence_node_ref in settlement_map]:
            settlement = settlement_map[npc.residence_node_ref]
            condition = context.settlement_conditions.get(settlement.ext_ref)
            if condition and condition.danger > 0.6 and not settlement.is_locked:
                target = self._best_migration_target(settlement, context, settlement_map)
                if target is not None and target.ext_ref != settlement.ext_ref and context.rng.random() < 0.2:
                    self._social_service.update_npc(
                        npc.ext_ref,
                        {
                            "residence_node_ref": target.ext_ref,
                        },
                    )
                    migrations += 1
                    run.changes.append(
                        SimulationChange(
                            entity_type="npc",
                            entity_ref=npc.ext_ref,
                            field_name="residence_node_ref",
                            previous_value=settlement.ext_ref,
                            new_value=target.ext_ref,
                            reason="Migrated NPC away from dangerous settlement.",
                        )
                    )

        run.notes.append(
            f"migration: reconciled populations, births={births}, migrations={migrations}."
        )

    def _create_newborn(self, settlement: SettlementNode, race: Any, context: SimulationContext) -> Npc:
        newborn = Npc(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=context.world.ext_ref,
            display_name=f"Newborn of {settlement.name}",
            age_years=0,
            race_ref=race.ext_ref,
            subrace_ref=None,
            occupation_ref=None,
            residence_node_ref=settlement.ext_ref,
            health_index=1.0,
            wealth_index=0.1,
            notes="Born during deterministic simulation.",
        )
        return self._social_service.create_npc(settlement.world_ref, {
            "display_name": newborn.display_name,
            "age_years": newborn.age_years,
            "race_ref": newborn.race_ref,
            "subrace_ref": newborn.subrace_ref,
            "occupation_ref": newborn.occupation_ref,
            "residence_node_ref": newborn.residence_node_ref,
            "health_index": newborn.health_index,
            "wealth_index": newborn.wealth_index,
            "notes": newborn.notes,
        })

    def _best_migration_target(
        self,
        settlement: SettlementNode,
        context: SimulationContext,
        settlement_map: dict[str, SettlementNode],
    ) -> SettlementNode | None:
        candidates = [
            candidate
            for candidate in settlement_map.values()
            if candidate.ext_ref != settlement.ext_ref and not candidate.is_locked
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda candidate: (
                context.settlement_conditions.get(candidate.ext_ref, SettlementCondition(0.5, 0.5, 0.5, 0.5, 0.0)).prosperity,
                candidate.resource_index,
                candidate.safety_index,
            ),
            reverse=True,
        )
        return candidates[0]


class EconomicOccupationPass(SimulationPass):
    name = "economy"

    def __init__(self, social_service: Any) -> None:
        self._social_service = social_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        occupations = tuple(self._social_service.list_occupations())
        if not occupations:
            run.notes.append("economy: no occupations configured for assignment.")
            return

        npcs = list(self._social_service.list_npcs(context.world.ext_ref))
        updates = 0
        for npc in npcs:
            if npc.is_locked:
                continue
            condition = context.settlement_conditions.get(npc.residence_node_ref) if npc.residence_node_ref else None
            payload: dict[str, object] = {}
            if npc.occupation_ref is None:
                occupation = self._choose_occupation(occupations, condition)
                if occupation is not None:
                    payload["occupation_ref"] = occupation.ext_ref
                    run.changes.append(
                        SimulationChange(
                            entity_type="npc",
                            entity_ref=npc.ext_ref,
                            field_name="occupation_ref",
                            previous_value="",
                            new_value=occupation.ext_ref,
                            reason="Assigned economic occupation based on local conditions.",
                        )
                    )
            if condition is not None:
                wealth = _clamp(npc.wealth_index + (condition.prosperity - 0.5) * 0.05 + (condition.resource - 0.5) * 0.03)
                if wealth != npc.wealth_index:
                    payload["wealth_index"] = wealth
            if payload:
                self._social_service.update_npc(npc.ext_ref, payload)
                updates += 1

        run.notes.append(f"economy: updated {updates} NPCs with occupation and wealth balance.")

    def _choose_occupation(self, occupations: tuple[Occupation, ...], condition: SettlementCondition | None) -> Occupation | None:
        ranked = []
        for occupation in occupations:
            score = 1.0 / max(0.01, occupation.rarity)
            if condition is not None:
                if occupation.category == "trade":
                    score *= 1.0 + (condition.prosperity - 0.5)
                elif occupation.category == "labor":
                    score *= 1.0 + (condition.resource - 0.5)
            ranked.append((score, occupation))
        if not ranked:
            return None
        return sorted(ranked, key=lambda item: (-item[0], item[1].ext_ref))[0][1]


class CleanupPass(SimulationPass):
    name = "cleanup"

    def __init__(self, hierarchy_service: Any, social_service: Any) -> None:
        self._hierarchy_service = hierarchy_service
        self._social_service = social_service

    def apply(self, run: SimulationRun, context: SimulationContext) -> None:
        settlement_map = {settlement.ext_ref: settlement for settlement in self._hierarchy_service.list_settlements(context.world.ext_ref)}
        npcs = list(self._social_service.list_npcs(context.world.ext_ref))
        deleted_relationships = 0
        corrected_npcs = 0

        for npc in npcs:
            if npc.residence_node_ref and npc.residence_node_ref not in settlement_map:
                self._social_service.update_npc(npc.ext_ref, {"residence_node_ref": None})
                corrected_npcs += 1
                run.changes.append(
                    SimulationChange(
                        entity_type="npc",
                        entity_ref=npc.ext_ref,
                        field_name="residence_node_ref",
                        previous_value=str(npc.residence_node_ref),
                        new_value="",
                        reason="Removed invalid settlement reference.",
                    )
                )

        relationships = list(self._social_service.list_relationships(context.world.ext_ref))
        for relationship in relationships:
            if relationship.is_locked:
                continue
            if (
                relationship.source_npc_ref == relationship.target_npc_ref
                or relationship.source_npc_ref not in {npc.ext_ref for npc in npcs}
                or relationship.target_npc_ref not in {npc.ext_ref for npc in npcs}
            ):
                self._social_service.delete_relationship(relationship.ext_ref)
                deleted_relationships += 1

        run.notes.append(
            f"cleanup: corrected {corrected_npcs} NPC references and removed {deleted_relationships} invalid relationships."
        )


def build_simulation_engine(
    hierarchy_service: Any,
    social_service: Any,
    event_resolver: EventEffectResolver | None = None,
) -> SimulationEngine:
    return SimulationEngine(
        [
            PrecheckPass(),
            EventResolutionPass(event_resolver),
            RegionConditionPass(hierarchy_service),
            NpcSimulationPass(hierarchy_service, social_service),
            RelationshipUpdatePass(social_service),
            MapAwareSettlementPass(hierarchy_service),
            PopulationMigrationPass(hierarchy_service, social_service),
            EconomicOccupationPass(social_service),
            CleanupPass(hierarchy_service, social_service),
        ]
    )


def build_simulation_context(world: World, request: SimulationRequest) -> SimulationContext:
    seed = _stable_seed(world.ext_ref, request)
    rng = random.Random(seed)
    return SimulationContext(
        world=world,
        request=request,
        duration_days=request.duration_days(),
        preview_only=request.preview_only,
        rng=rng,
    )
