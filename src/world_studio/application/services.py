from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from world_studio.data.repositories import (
    HierarchyRepository,
    SocialRepository,
    WorldRepository,
)
from world_studio.domain.enums import NodeType, RelationshipType, SettlementType
from world_studio.domain.population import Npc, Occupation, Race, Relationship, SubRace, Trait
from world_studio.domain.simulation import NoOpPass, SimulationEngine, SimulationRequest, SimulationRun
from world_studio.domain.world import (
    Continent,
    Empire,
    Kingdom,
    PointOfInterest,
    Region,
    RouteConnection,
    SettlementNode,
    World,
)
from world_studio.generation.generation_models import GenerationRequest, GenerationRunSummary
from world_studio.generation.generation_service import (
    parse_event_seed_inputs,
    WorldGenerationOrchestrator,
    generate_with_payload,
)
from world_studio.generation.settlement_promotion_rules import MapAwareSettlementPass
from world_studio.infrastructure.json_io import JsonWorldCodec
from world_studio.infrastructure.pdf_export import PdfExporter


class WorldService:
    def __init__(self, world_repository: WorldRepository) -> None:
        self._world_repository = world_repository

    def create_world(self, world: World) -> World:
        return self._world_repository.upsert_world(world)

    def list_worlds(self) -> list[World]:
        return self._world_repository.list_worlds()

    def get_world(self, ext_ref: str) -> World | None:
        return self._world_repository.get_world(ext_ref)


class HierarchyService:
    def __init__(self, hierarchy_repository: HierarchyRepository) -> None:
        self._hierarchy_repository = hierarchy_repository

    def list_continents(self, world_ref: str) -> list[Continent]:
        return self._hierarchy_repository.list_continents(world_ref)

    def get_continent(self, ext_ref: str) -> Continent | None:
        return self._hierarchy_repository.get_continent(ext_ref)

    def create_continent(self, world_ref: str, payload: dict[str, object]) -> Continent:
        continent = Continent(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            name=str(payload.get("name", "")).strip(),
            climate_summary=str(payload.get("climate_summary", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not continent.name:
            raise ValueError("Continent name is required.")
        return self._hierarchy_repository.upsert_continent(continent)

    def update_continent(self, ext_ref: str, payload: dict[str, object]) -> Continent:
        continent = self._require_entity(self._hierarchy_repository.get_continent(ext_ref), "Continent")
        continent.name = str(payload.get("name", continent.name)).strip() or continent.name
        continent.climate_summary = str(payload.get("climate_summary", continent.climate_summary)).strip()
        continent.is_locked = bool(payload.get("is_locked", continent.is_locked))
        if "metadata" in payload:
            continent.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_continent(continent)

    def delete_continent(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_continent(ext_ref)

    def list_empires(self, world_ref: str) -> list[Empire]:
        return self._hierarchy_repository.list_empires(world_ref)

    def get_empire(self, ext_ref: str) -> Empire | None:
        return self._hierarchy_repository.get_empire(ext_ref)

    def create_empire(self, world_ref: str, payload: dict[str, object]) -> Empire:
        empire = Empire(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            continent_ref=self._optional_text(payload.get("continent_ref")),
            name=str(payload.get("name", "")).strip(),
            governing_style=str(payload.get("governing_style", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not empire.name:
            raise ValueError("Empire name is required.")
        return self._hierarchy_repository.upsert_empire(empire)

    def update_empire(self, ext_ref: str, payload: dict[str, object]) -> Empire:
        empire = self._require_entity(self._hierarchy_repository.get_empire(ext_ref), "Empire")
        empire.name = str(payload.get("name", empire.name)).strip() or empire.name
        empire.continent_ref = self._optional_text(payload.get("continent_ref")) or None
        empire.governing_style = str(payload.get("governing_style", empire.governing_style)).strip()
        empire.is_locked = bool(payload.get("is_locked", empire.is_locked))
        if "metadata" in payload:
            empire.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_empire(empire)

    def delete_empire(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_empire(ext_ref)

    def list_kingdoms(self, world_ref: str) -> list[Kingdom]:
        return self._hierarchy_repository.list_kingdoms(world_ref)

    def get_kingdom(self, ext_ref: str) -> Kingdom | None:
        return self._hierarchy_repository.get_kingdom(ext_ref)

    def create_kingdom(self, world_ref: str, payload: dict[str, object]) -> Kingdom:
        kingdom = Kingdom(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            empire_ref=self._optional_text(payload.get("empire_ref")),
            name=str(payload.get("name", "")).strip(),
            stability_index=self._to_float(payload.get("stability_index"), 0.5),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not kingdom.name:
            raise ValueError("Kingdom name is required.")
        return self._hierarchy_repository.upsert_kingdom(kingdom)

    def update_kingdom(self, ext_ref: str, payload: dict[str, object]) -> Kingdom:
        kingdom = self._require_entity(self._hierarchy_repository.get_kingdom(ext_ref), "Kingdom")
        kingdom.name = str(payload.get("name", kingdom.name)).strip() or kingdom.name
        kingdom.empire_ref = self._optional_text(payload.get("empire_ref")) or None
        kingdom.stability_index = self._to_float(payload.get("stability_index"), kingdom.stability_index)
        kingdom.is_locked = bool(payload.get("is_locked", kingdom.is_locked))
        if "metadata" in payload:
            kingdom.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_kingdom(kingdom)

    def delete_kingdom(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_kingdom(ext_ref)

    def list_regions(self, world_ref: str) -> list[Region]:
        return self._hierarchy_repository.list_regions(world_ref)

    def get_region(self, ext_ref: str) -> Region | None:
        return self._hierarchy_repository.get_region(ext_ref)

    def create_region(self, world_ref: str, payload: dict[str, object]) -> Region:
        region = Region(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            kingdom_ref=self._optional_text(payload.get("kingdom_ref")),
            name=str(payload.get("name", "")).strip(),
            biome=str(payload.get("biome", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not region.name:
            raise ValueError("Region name is required.")
        return self._hierarchy_repository.upsert_region(region)

    def update_region(self, ext_ref: str, payload: dict[str, object]) -> Region:
        region = self._require_entity(self._hierarchy_repository.get_region(ext_ref), "Region")
        region.name = str(payload.get("name", region.name)).strip() or region.name
        region.kingdom_ref = self._optional_text(payload.get("kingdom_ref")) or None
        region.biome = str(payload.get("biome", region.biome)).strip()
        region.is_locked = bool(payload.get("is_locked", region.is_locked))
        if "metadata" in payload:
            region.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_region(region)

    def delete_region(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_region(ext_ref)

    def list_settlements(self, world_ref: str) -> list[SettlementNode]:
        return self._hierarchy_repository.list_settlements(world_ref)

    def get_settlement(self, ext_ref: str) -> SettlementNode | None:
        return self._hierarchy_repository.get_settlement(ext_ref)

    def create_settlement(self, world_ref: str, payload: dict[str, object]) -> SettlementNode:
        settlement = SettlementNode(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            region_ref=self._optional_text(payload.get("region_ref")),
            name=str(payload.get("name", "")).strip(),
            kind=SettlementType(str(payload.get("kind", SettlementType.VILLAGE.value))),
            population=self._to_int(payload.get("population"), 100),
            resource_index=self._to_float(payload.get("resource_index"), 0.5),
            safety_index=self._to_float(payload.get("safety_index"), 0.5),
            x=self._to_float(payload.get("x"), 0.0),
            y=self._to_float(payload.get("y"), 0.0),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not settlement.name:
            raise ValueError("Settlement name is required.")
        return self._hierarchy_repository.upsert_settlement(settlement)

    def update_settlement(self, ext_ref: str, payload: dict[str, object]) -> SettlementNode:
        settlement = self._require_entity(self._hierarchy_repository.get_settlement(ext_ref), "Settlement")
        settlement.name = str(payload.get("name", settlement.name)).strip() or settlement.name
        settlement.region_ref = self._optional_text(payload.get("region_ref")) or None
        settlement.kind = SettlementType(str(payload.get("kind", settlement.kind.value)))
        settlement.population = self._to_int(payload.get("population"), settlement.population)
        settlement.resource_index = self._to_float(
            payload.get("resource_index"), settlement.resource_index
        )
        settlement.safety_index = self._to_float(payload.get("safety_index"), settlement.safety_index)
        settlement.x = self._to_float(payload.get("x"), settlement.x)
        settlement.y = self._to_float(payload.get("y"), settlement.y)
        settlement.is_locked = bool(payload.get("is_locked", settlement.is_locked))
        if "metadata" in payload:
            settlement.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_settlement(settlement)

    def delete_settlement(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_settlement(ext_ref)

    def list_points_of_interest(self, world_ref: str) -> list[PointOfInterest]:
        return self._hierarchy_repository.list_points_of_interest(world_ref)

    def get_point_of_interest(self, ext_ref: str) -> PointOfInterest | None:
        return self._hierarchy_repository.get_point_of_interest(ext_ref)

    def create_point_of_interest(
        self, world_ref: str, payload: dict[str, object]
    ) -> PointOfInterest:
        poi = PointOfInterest(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            region_ref=self._optional_text(payload.get("region_ref")),
            name=str(payload.get("name", "")).strip(),
            node_type=NodeType(str(payload.get("node_type", NodeType.POINT_OF_INTEREST.value))),
            x=self._to_float(payload.get("x"), 0.0),
            y=self._to_float(payload.get("y"), 0.0),
            description=str(payload.get("description", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not poi.name:
            raise ValueError("Point of interest name is required.")
        return self._hierarchy_repository.upsert_point_of_interest(poi)

    def update_point_of_interest(self, ext_ref: str, payload: dict[str, object]) -> PointOfInterest:
        poi = self._require_entity(
            self._hierarchy_repository.get_point_of_interest(ext_ref), "Point of interest"
        )
        poi.name = str(payload.get("name", poi.name)).strip() or poi.name
        poi.region_ref = self._optional_text(payload.get("region_ref")) or None
        poi.node_type = NodeType(str(payload.get("node_type", poi.node_type.value)))
        poi.x = self._to_float(payload.get("x"), poi.x)
        poi.y = self._to_float(payload.get("y"), poi.y)
        poi.description = str(payload.get("description", poi.description)).strip()
        poi.is_locked = bool(payload.get("is_locked", poi.is_locked))
        if "metadata" in payload:
            poi.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_point_of_interest(poi)

    def delete_point_of_interest(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_point_of_interest(ext_ref)

    def list_routes(self, world_ref: str) -> list[RouteConnection]:
        return self._hierarchy_repository.list_routes(world_ref)

    def get_route(self, ext_ref: str) -> RouteConnection | None:
        return self._hierarchy_repository.get_route(ext_ref)

    def create_route(self, world_ref: str, payload: dict[str, object]) -> RouteConnection:
        route = RouteConnection(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            name=str(payload.get("name", "")).strip(),
            source_ref=str(payload.get("source_ref", "")).strip(),
            target_ref=str(payload.get("target_ref", "")).strip(),
            route_type=str(payload.get("route_type", "road")).strip() or "road",
            travel_cost=self._to_float(payload.get("travel_cost"), 1.0),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not route.name or not route.source_ref or not route.target_ref:
            raise ValueError("Route requires name, source_ref, and target_ref.")
        return self._hierarchy_repository.upsert_route(route)

    def update_route(self, ext_ref: str, payload: dict[str, object]) -> RouteConnection:
        route = self._require_entity(self._hierarchy_repository.get_route(ext_ref), "Route")
        route.name = str(payload.get("name", route.name)).strip() or route.name
        route.source_ref = str(payload.get("source_ref", route.source_ref)).strip() or route.source_ref
        route.target_ref = str(payload.get("target_ref", route.target_ref)).strip() or route.target_ref
        route.route_type = str(payload.get("route_type", route.route_type)).strip() or route.route_type
        route.travel_cost = self._to_float(payload.get("travel_cost"), route.travel_cost)
        route.is_locked = bool(payload.get("is_locked", route.is_locked))
        if "metadata" in payload:
            route.metadata = self._to_metadata(payload.get("metadata"))
        return self._hierarchy_repository.upsert_route(route)

    def delete_route(self, ext_ref: str) -> None:
        self._hierarchy_repository.delete_route(ext_ref)

    @staticmethod
    def _optional_text(value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: object | None, default: int) -> int:
        if value is None or value == "":
            return default
        return int(value)

    @staticmethod
    def _to_float(value: object | None, default: float) -> float:
        if value is None or value == "":
            return default
        return float(value)

    @staticmethod
    def _to_metadata(value: object | None) -> dict[str, object]:
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _require_entity(entity: object | None, label: str) -> object:
        if entity is None:
            raise ValueError(f"{label} does not exist.")
        return entity


class SimulationService:
    def __init__(
        self,
        world_repository: WorldRepository,
        hierarchy_repository: HierarchyRepository,
    ) -> None:
        self._world_repository = world_repository
        self._engine = SimulationEngine(
            [
                NoOpPass("precheck", "Validated locks, snapshots, and active rules."),
                NoOpPass("demography", "Aging and mortality pass pending phase 4."),
                NoOpPass("economy", "Occupation/economy pass pending phase 4."),
                NoOpPass("migration", "Migration route scoring pass pending phase 4."),
                MapAwareSettlementPass(hierarchy_repository),
                NoOpPass("relationships", "Relationship drift pass pending phase 4."),
                NoOpPass("events", "Event resolution pass pending phase 5."),
                NoOpPass("post", "Run summary and audit persistence pending phase 4."),
            ]
        )

    def simulate(self, request: SimulationRequest) -> SimulationRun:
        if self._world_repository.get_world(request.world_ref) is None:
            msg = f"world_ref does not exist: {request.world_ref}"
            raise ValueError(msg)
        return self._engine.run(request)


class SocialService:
    def __init__(self, social_repository: SocialRepository) -> None:
        self._social_repository = social_repository

    def list_races(self) -> list[Race]:
        return self._social_repository.list_races()

    def create_race(self, payload: dict[str, object]) -> Race:
        race = Race(
            id=None,
            ext_ref=str(uuid4()),
            name=str(payload.get("name", "")).strip(),
            lifespan_years=self._to_int(payload.get("lifespan_years"), 80),
            is_default=bool(payload.get("is_default", False)),
        )
        if not race.name:
            raise ValueError("Race name is required.")
        return self._social_repository.upsert_race(race)

    def list_occupations(self) -> list[Occupation]:
        return self._social_repository.list_occupations()

    def create_occupation(self, payload: dict[str, object]) -> Occupation:
        occupation = Occupation(
            id=None,
            ext_ref=str(uuid4()),
            name=str(payload.get("name", "")).strip(),
            category=str(payload.get("category", "")).strip(),
            rarity=self._to_float(payload.get("rarity"), 1.0),
        )
        if not occupation.name:
            raise ValueError("Occupation name is required.")
        return self._social_repository.upsert_occupation(occupation)

    def list_npcs(self, world_ref: str) -> list[Npc]:
        return self._social_repository.list_npcs(world_ref)

    def get_npc(self, ext_ref: str) -> Npc | None:
        return self._social_repository.get_npc(ext_ref)

    def create_npc(self, world_ref: str, payload: dict[str, object]) -> Npc:
        race_ref = self._optional_text(payload.get("race_ref"))
        if not race_ref:
            raise ValueError("NPC race_ref is required.")
        npc = Npc(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            display_name=str(payload.get("display_name", "")).strip(),
            age_years=self._to_int(payload.get("age_years"), 20),
            race_ref=race_ref,
            subrace_ref=self._optional_text(payload.get("subrace_ref")),
            occupation_ref=self._optional_text(payload.get("occupation_ref")),
            residence_node_ref=self._optional_text(payload.get("residence_node_ref")),
            health_index=self._to_float(payload.get("health_index"), 1.0),
            wealth_index=self._to_float(payload.get("wealth_index"), 0.5),
            notes=str(payload.get("notes", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        if not npc.display_name:
            raise ValueError("NPC display_name is required.")
        return self._social_repository.upsert_npc(npc)

    def update_npc(self, ext_ref: str, payload: dict[str, object], *, force: bool = False) -> Npc:
        npc = self._require_entity(self._social_repository.get_npc(ext_ref), "NPC")
        if npc.is_locked and not force:
            raise ValueError("NPC is locked. Use override to force update.")
        npc.display_name = str(payload.get("display_name", npc.display_name)).strip() or npc.display_name
        npc.age_years = self._to_int(payload.get("age_years"), npc.age_years)
        npc.race_ref = self._optional_text(payload.get("race_ref")) or npc.race_ref
        npc.subrace_ref = self._optional_text(payload.get("subrace_ref"))
        npc.occupation_ref = self._optional_text(payload.get("occupation_ref"))
        npc.residence_node_ref = self._optional_text(payload.get("residence_node_ref"))
        npc.health_index = self._to_float(payload.get("health_index"), npc.health_index)
        npc.wealth_index = self._to_float(payload.get("wealth_index"), npc.wealth_index)
        npc.notes = str(payload.get("notes", npc.notes)).strip()
        if "is_locked" in payload:
            npc.is_locked = bool(payload["is_locked"])
        if "metadata" in payload:
            npc.metadata = self._to_metadata(payload.get("metadata"))
        return self._social_repository.upsert_npc(npc)

    def delete_npc(self, ext_ref: str, *, force: bool = False) -> None:
        npc = self._require_entity(self._social_repository.get_npc(ext_ref), "NPC")
        if npc.is_locked and not force:
            raise ValueError("NPC is locked. Use override to force delete.")
        self._social_repository.delete_npc(ext_ref)

    def list_relationships(self, world_ref: str) -> list[Relationship]:
        return self._social_repository.list_relationships(world_ref)

    def get_relationship(self, ext_ref: str) -> Relationship | None:
        return self._social_repository.get_relationship(ext_ref)

    def create_relationship(self, world_ref: str, payload: dict[str, object]) -> Relationship:
        source = self._optional_text(payload.get("source_npc_ref"))
        target = self._optional_text(payload.get("target_npc_ref"))
        if not source or not target:
            raise ValueError("Relationship requires source_npc_ref and target_npc_ref.")
        relationship = Relationship(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world_ref,
            source_npc_ref=source,
            target_npc_ref=target,
            relation_type=RelationshipType(str(payload.get("relation_type", RelationshipType.FRIEND.value))),
            weight=self._to_float(payload.get("weight"), 0.0),
            history=self._parse_history(payload.get("history", "")),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )
        return self._social_repository.upsert_relationship(relationship)

    def update_relationship(
        self, ext_ref: str, payload: dict[str, object], *, force: bool = False
    ) -> Relationship:
        relationship = self._require_entity(
            self._social_repository.get_relationship(ext_ref), "Relationship"
        )
        if relationship.is_locked and not force:
            raise ValueError("Relationship is locked. Use override to force update.")
        relationship.source_npc_ref = (
            self._optional_text(payload.get("source_npc_ref")) or relationship.source_npc_ref
        )
        relationship.target_npc_ref = (
            self._optional_text(payload.get("target_npc_ref")) or relationship.target_npc_ref
        )
        relationship.relation_type = RelationshipType(
            str(payload.get("relation_type", relationship.relation_type.value))
        )
        relationship.weight = self._to_float(payload.get("weight"), relationship.weight)
        if "history" in payload:
            relationship.history = self._parse_history(payload.get("history"))
        if "is_locked" in payload:
            relationship.is_locked = bool(payload["is_locked"])
        if "metadata" in payload:
            relationship.metadata = self._to_metadata(payload.get("metadata"))
        return self._social_repository.upsert_relationship(relationship)

    def delete_relationship(self, ext_ref: str, *, force: bool = False) -> None:
        relationship = self._require_entity(
            self._social_repository.get_relationship(ext_ref), "Relationship"
        )
        if relationship.is_locked and not force:
            raise ValueError("Relationship is locked. Use override to force delete.")
        self._social_repository.delete_relationship(ext_ref)

    @staticmethod
    def _optional_text(value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: object | None, default: int) -> int:
        if value is None or value == "":
            return default
        return int(value)

    @staticmethod
    def _to_float(value: object | None, default: float) -> float:
        if value is None or value == "":
            return default
        return float(value)

    @staticmethod
    def _to_metadata(value: object | None) -> dict[str, object]:
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _parse_history(value: object | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]

    @staticmethod
    def _require_entity(entity: object | None, label: str) -> object:
        if entity is None:
            raise ValueError(f"{label} does not exist.")
        return entity


class GenerationAppService:
    def __init__(
        self,
        world_service: WorldService,
        hierarchy_service: HierarchyService,
        social_service: SocialService,
        orchestrator: WorldGenerationOrchestrator | None = None,
    ) -> None:
        self._world_service = world_service
        self._hierarchy_service = hierarchy_service
        self._social_service = social_service
        self._orchestrator = orchestrator or WorldGenerationOrchestrator()
        self._orchestrator.bind(world_service, hierarchy_service, social_service)

    def generate(self, request: GenerationRequest) -> GenerationRunSummary:
        return self._orchestrator.generate(request)

    def generate_initial_state(
        self,
        world_ref: str,
        payload: dict[str, object],
    ) -> GenerationRunSummary:
        normalized_payload = dict(payload)
        for payload_key in ("event_inputs", "historical_inputs"):
            raw_value = normalized_payload.get(payload_key)
            if isinstance(raw_value, str):
                text = raw_value.strip()
                if text:
                    try:
                        decoded = json.loads(text)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid {payload_key} JSON: {exc.msg}") from exc
                    normalized_payload[payload_key] = decoded
                else:
                    normalized_payload[payload_key] = []
            elif raw_value is None:
                normalized_payload[payload_key] = []

        normalized_payload["event_inputs"] = parse_event_seed_inputs(
            normalized_payload.get("event_inputs"),
            stage="active",
        )
        normalized_payload["historical_inputs"] = parse_event_seed_inputs(
            normalized_payload.get("historical_inputs"),
            stage="historical",
        )
        return generate_with_payload(
            world_service=self._world_service,
            hierarchy_service=self._hierarchy_service,
            social_service=self._social_service,
            world_ref=world_ref,
            payload=normalized_payload,
        )


IMPORT_MODE_MERGE = "merge"
IMPORT_MODE_REPLACE = "replace"
CONFLICT_KEEP_IMPORTED = "keep_imported"
CONFLICT_KEEP_LOCAL = "keep_local"


@dataclass
class ImportRunSummary:
    world_ref: str
    mode: str
    conflict_policy: str
    preview_only: bool
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)

    def bump_created(self, entity_type: str) -> None:
        self.created[entity_type] = self.created.get(entity_type, 0) + 1

    def bump_updated(self, entity_type: str) -> None:
        self.updated[entity_type] = self.updated.get(entity_type, 0) + 1

    def bump_skipped(self, entity_type: str, reason: str) -> None:
        self.skipped[entity_type] = self.skipped.get(entity_type, 0) + 1
        self.conflicts.append(reason)


class ImportExportService:
    def __init__(
        self,
        world_repository: WorldRepository,
        hierarchy_repository: HierarchyRepository,
        social_repository: SocialRepository,
        json_codec: JsonWorldCodec,
        pdf_exporter: PdfExporter,
        exports_dir: Path,
    ) -> None:
        self._world_repository = world_repository
        self._hierarchy_repository = hierarchy_repository
        self._social_repository = social_repository
        self._json_codec = json_codec
        self._pdf_exporter = pdf_exporter
        self._exports_dir = exports_dir
        self._exports_dir.mkdir(parents=True, exist_ok=True)

    def export_world_json(self, world_ref: str) -> Path:
        world = self._world_repository.get_world(world_ref)
        if world is None:
            raise ValueError(f"Unknown world: {world_ref}")
        hierarchy_payload = {
            "continents": [asdict(item) for item in self._hierarchy_repository.list_continents(world_ref)],
            "empires": [asdict(item) for item in self._hierarchy_repository.list_empires(world_ref)],
            "kingdoms": [asdict(item) for item in self._hierarchy_repository.list_kingdoms(world_ref)],
            "regions": [asdict(item) for item in self._hierarchy_repository.list_regions(world_ref)],
            "settlements": [asdict(item) for item in self._hierarchy_repository.list_settlements(world_ref)],
            "points_of_interest": [
                asdict(item) for item in self._hierarchy_repository.list_points_of_interest(world_ref)
            ],
            "routes": [asdict(item) for item in self._hierarchy_repository.list_routes(world_ref)],
        }
        social_payload = {
            "races": [asdict(item) for item in self._social_repository.list_races()],
            "subraces": [asdict(item) for item in self._social_repository.list_subraces()],
            "occupations": [asdict(item) for item in self._social_repository.list_occupations()],
            "traits": [asdict(item) for item in self._social_repository.list_traits()],
            "npcs": [asdict(item) for item in self._social_repository.list_npcs(world_ref)],
            "relationships": [
                asdict(item) for item in self._social_repository.list_relationships(world_ref)
            ],
        }
        payload = self._json_codec.serialize_world_bundle(
            world_ref=world_ref,
            payload={
                "world": asdict(world),
                "hierarchy": hierarchy_payload,
                "social": social_payload,
            },
            kind="full_world",
        )
        target = self._exports_dir / f"world-{world_ref}.json"
        target.write_text(payload, encoding="utf-8")
        return target

    def import_world_json(
        self,
        source: Path,
        *,
        mode: str = IMPORT_MODE_MERGE,
        conflict_policy: str = CONFLICT_KEEP_IMPORTED,
        preview_only: bool = False,
    ) -> ImportRunSummary:
        if mode not in {IMPORT_MODE_MERGE, IMPORT_MODE_REPLACE}:
            raise ValueError(f"Unsupported import mode: {mode}")
        if conflict_policy not in {CONFLICT_KEEP_IMPORTED, CONFLICT_KEEP_LOCAL}:
            raise ValueError(f"Unsupported conflict policy: {conflict_policy}")

        bundle = self._json_codec.deserialize_world_bundle(source.read_text(encoding="utf-8"))
        world_payload = bundle["world"]
        world_ref = self._required_text(world_payload, "ext_ref", "world")
        summary = ImportRunSummary(
            world_ref=world_ref,
            mode=mode,
            conflict_policy=conflict_policy,
            preview_only=preview_only,
        )

        if mode == IMPORT_MODE_REPLACE:
            self._replace_world_entities(world_ref, preview_only=preview_only)

        self._upsert_entity(
            entity_type="worlds",
            ext_ref=world_ref,
            existing_lookup=self._world_repository.get_world,
            perform_upsert=lambda: self._world_repository.upsert_world(
                self._world_from_payload(world_payload)
            ),
            conflict_policy=conflict_policy,
            summary=summary,
            assume_missing=False,
            preview_only=preview_only,
        )

        hierarchy = bundle["hierarchy"]
        social = bundle["social"]
        assume_hierarchy_missing = mode == IMPORT_MODE_REPLACE

        for payload in hierarchy["continents"]:
            entity = self._continent_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="continents",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_continent,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_continent(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["empires"]:
            entity = self._empire_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="empires",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_empire,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_empire(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["kingdoms"]:
            entity = self._kingdom_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="kingdoms",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_kingdom,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_kingdom(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["regions"]:
            entity = self._region_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="regions",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_region,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_region(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["settlements"]:
            entity = self._settlement_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="settlements",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_settlement,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_settlement(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["points_of_interest"]:
            entity = self._point_of_interest_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="points_of_interest",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_point_of_interest,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_point_of_interest(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in hierarchy["routes"]:
            entity = self._route_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="routes",
                ext_ref=entity.ext_ref,
                existing_lookup=self._hierarchy_repository.get_route,
                perform_upsert=lambda item=entity: self._hierarchy_repository.upsert_route(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )

        for payload in social["races"]:
            entity = self._race_from_payload(payload)
            self._upsert_entity(
                entity_type="races",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_race,
                perform_upsert=lambda item=entity: self._social_repository.upsert_race(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=False,
                preview_only=preview_only,
            )
        for payload in social["subraces"]:
            entity = self._subrace_from_payload(payload)
            self._upsert_entity(
                entity_type="subraces",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_subrace,
                perform_upsert=lambda item=entity: self._social_repository.upsert_subrace(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=False,
                preview_only=preview_only,
            )
        for payload in social["occupations"]:
            entity = self._occupation_from_payload(payload)
            self._upsert_entity(
                entity_type="occupations",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_occupation,
                perform_upsert=lambda item=entity: self._social_repository.upsert_occupation(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=False,
                preview_only=preview_only,
            )
        for payload in social["traits"]:
            entity = self._trait_from_payload(payload)
            self._upsert_entity(
                entity_type="traits",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_trait,
                perform_upsert=lambda item=entity: self._social_repository.upsert_trait(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=False,
                preview_only=preview_only,
            )
        for payload in social["npcs"]:
            entity = self._npc_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="npcs",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_npc,
                perform_upsert=lambda item=entity: self._social_repository.upsert_npc(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )
        for payload in social["relationships"]:
            entity = self._relationship_from_payload(payload, world_ref=world_ref)
            self._upsert_entity(
                entity_type="relationships",
                ext_ref=entity.ext_ref,
                existing_lookup=self._social_repository.get_relationship,
                perform_upsert=lambda item=entity: self._social_repository.upsert_relationship(item),
                conflict_policy=conflict_policy,
                summary=summary,
                assume_missing=assume_hierarchy_missing,
                preview_only=preview_only,
            )

        return summary

    def export_world_pdf(self, world_ref: str) -> Path:
        world = self._world_repository.get_world(world_ref)
        if world is None:
            raise ValueError(f"Unknown world: {world_ref}")
        target = self._exports_dir / f"world-{world_ref}.pdf"
        self._pdf_exporter.export_world_summary(world, target)
        return target

    def _upsert_entity(
        self,
        *,
        entity_type: str,
        ext_ref: str,
        existing_lookup: Callable[[str], object | None],
        perform_upsert: Callable[[], object],
        conflict_policy: str,
        summary: ImportRunSummary,
        assume_missing: bool,
        preview_only: bool,
    ) -> None:
        existing = None if assume_missing else existing_lookup(ext_ref)
        if existing is None:
            summary.bump_created(entity_type)
            if not preview_only:
                perform_upsert()
            return
        if conflict_policy == CONFLICT_KEEP_LOCAL:
            summary.bump_skipped(entity_type, f"{entity_type}:{ext_ref}:kept local")
            return
        summary.bump_updated(entity_type)
        if not preview_only:
            perform_upsert()

    def _replace_world_entities(self, world_ref: str, *, preview_only: bool) -> None:
        if preview_only:
            return
        for route in self._hierarchy_repository.list_routes(world_ref):
            self._hierarchy_repository.delete_route(route.ext_ref)
        for poi in self._hierarchy_repository.list_points_of_interest(world_ref):
            self._hierarchy_repository.delete_point_of_interest(poi.ext_ref)
        for settlement in self._hierarchy_repository.list_settlements(world_ref):
            self._hierarchy_repository.delete_settlement(settlement.ext_ref)
        for region in self._hierarchy_repository.list_regions(world_ref):
            self._hierarchy_repository.delete_region(region.ext_ref)
        for kingdom in self._hierarchy_repository.list_kingdoms(world_ref):
            self._hierarchy_repository.delete_kingdom(kingdom.ext_ref)
        for empire in self._hierarchy_repository.list_empires(world_ref):
            self._hierarchy_repository.delete_empire(empire.ext_ref)
        for continent in self._hierarchy_repository.list_continents(world_ref):
            self._hierarchy_repository.delete_continent(continent.ext_ref)
        for relationship in self._social_repository.list_relationships(world_ref):
            self._social_repository.delete_relationship(relationship.ext_ref)
        for npc in self._social_repository.list_npcs(world_ref):
            self._social_repository.delete_npc(npc.ext_ref)

    def _world_from_payload(self, payload: dict[str, object]) -> World:
        return World(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "world"),
            name=self._required_text(payload, "name", "world"),
            description=str(payload.get("description", "")).strip(),
            active_ruleset_ref=self._optional_text(payload.get("active_ruleset_ref")),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _continent_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Continent:
        return Continent(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "continent"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            name=self._required_text(payload, "name", "continent"),
            climate_summary=str(payload.get("climate_summary", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _empire_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Empire:
        return Empire(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "empire"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            continent_ref=self._optional_text(payload.get("continent_ref")),
            name=self._required_text(payload, "name", "empire"),
            governing_style=str(payload.get("governing_style", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _kingdom_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Kingdom:
        return Kingdom(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "kingdom"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            empire_ref=self._optional_text(payload.get("empire_ref")),
            name=self._required_text(payload, "name", "kingdom"),
            stability_index=self._to_float(payload.get("stability_index"), 0.5),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _region_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Region:
        return Region(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "region"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            kingdom_ref=self._optional_text(payload.get("kingdom_ref")),
            name=self._required_text(payload, "name", "region"),
            biome=str(payload.get("biome", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _settlement_from_payload(self, payload: dict[str, object], *, world_ref: str) -> SettlementNode:
        return SettlementNode(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "settlement"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            region_ref=self._optional_text(payload.get("region_ref")),
            name=self._required_text(payload, "name", "settlement"),
            kind=SettlementType(str(payload.get("kind", SettlementType.VILLAGE.value))),
            population=self._to_int(payload.get("population"), 100),
            resource_index=self._to_float(payload.get("resource_index"), 0.5),
            safety_index=self._to_float(payload.get("safety_index"), 0.5),
            x=self._to_float(payload.get("x"), 0.0),
            y=self._to_float(payload.get("y"), 0.0),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _point_of_interest_from_payload(
        self,
        payload: dict[str, object],
        *,
        world_ref: str,
    ) -> PointOfInterest:
        return PointOfInterest(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "point_of_interest"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            region_ref=self._optional_text(payload.get("region_ref")),
            name=self._required_text(payload, "name", "point_of_interest"),
            node_type=NodeType(str(payload.get("node_type", NodeType.POINT_OF_INTEREST.value))),
            x=self._to_float(payload.get("x"), 0.0),
            y=self._to_float(payload.get("y"), 0.0),
            description=str(payload.get("description", "")).strip(),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _route_from_payload(self, payload: dict[str, object], *, world_ref: str) -> RouteConnection:
        return RouteConnection(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "route"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            name=self._required_text(payload, "name", "route"),
            source_ref=self._required_text(payload, "source_ref", "route"),
            target_ref=self._required_text(payload, "target_ref", "route"),
            route_type=str(payload.get("route_type", "road")).strip() or "road",
            travel_cost=self._to_float(payload.get("travel_cost"), 1.0),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _race_from_payload(self, payload: dict[str, object]) -> Race:
        return Race(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "race"),
            name=self._required_text(payload, "name", "race"),
            lifespan_years=self._to_int(payload.get("lifespan_years"), 80),
            is_default=bool(payload.get("is_default", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _subrace_from_payload(self, payload: dict[str, object]) -> SubRace:
        return SubRace(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "subrace"),
            race_ref=self._required_text(payload, "race_ref", "subrace"),
            name=self._required_text(payload, "name", "subrace"),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _occupation_from_payload(self, payload: dict[str, object]) -> Occupation:
        return Occupation(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "occupation"),
            name=self._required_text(payload, "name", "occupation"),
            category=str(payload.get("category", "")).strip(),
            rarity=self._to_float(payload.get("rarity"), 1.0),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _trait_from_payload(self, payload: dict[str, object]) -> Trait:
        return Trait(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "trait"),
            name=self._required_text(payload, "name", "trait"),
            polarity=self._to_float(payload.get("polarity"), 0.0),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _npc_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Npc:
        return Npc(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "npc"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            display_name=self._required_text(payload, "display_name", "npc"),
            age_years=self._to_int(payload.get("age_years"), 20),
            race_ref=self._required_text(payload, "race_ref", "npc"),
            subrace_ref=self._optional_text(payload.get("subrace_ref")),
            occupation_ref=self._optional_text(payload.get("occupation_ref")),
            residence_node_ref=self._optional_text(payload.get("residence_node_ref")),
            health_index=self._to_float(payload.get("health_index"), 1.0),
            wealth_index=self._to_float(payload.get("wealth_index"), 0.5),
            is_locked=bool(payload.get("is_locked", False)),
            notes=str(payload.get("notes", "")).strip(),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    def _relationship_from_payload(self, payload: dict[str, object], *, world_ref: str) -> Relationship:
        return Relationship(
            id=None,
            ext_ref=self._required_text(payload, "ext_ref", "relationship"),
            world_ref=self._optional_text(payload.get("world_ref")) or world_ref,
            source_npc_ref=self._required_text(payload, "source_npc_ref", "relationship"),
            target_npc_ref=self._required_text(payload, "target_npc_ref", "relationship"),
            relation_type=RelationshipType(
                str(payload.get("relation_type", RelationshipType.FRIEND.value))
            ),
            weight=self._to_float(payload.get("weight"), 0.0),
            history=self._to_history(payload.get("history")),
            is_locked=bool(payload.get("is_locked", False)),
            metadata=self._to_metadata(payload.get("metadata")),
        )

    @staticmethod
    def _required_text(payload: dict[str, object], key: str, entity_label: str) -> str:
        raw = payload.get(key)
        if raw is None:
            raise ValueError(f"Invalid {entity_label} payload: missing '{key}'.")
        text = str(raw).strip()
        if not text:
            raise ValueError(f"Invalid {entity_label} payload: empty '{key}'.")
        return text

    @staticmethod
    def _optional_text(value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: object | None, default: int) -> int:
        if value is None or value == "":
            return default
        return int(value)

    @staticmethod
    def _to_float(value: object | None, default: float) -> float:
        if value is None or value == "":
            return default
        return float(value)

    @staticmethod
    def _to_metadata(value: object | None) -> dict[str, object]:
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _to_history(value: object | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]
