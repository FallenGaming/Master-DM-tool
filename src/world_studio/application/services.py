from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from world_studio.data.repositories import HierarchyRepository, WorldRepository
from world_studio.domain.enums import NodeType, SettlementType
from world_studio.domain.simulation import SimulationEngine, SimulationRequest, SimulationRun
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
        )
        if not continent.name:
            raise ValueError("Continent name is required.")
        return self._hierarchy_repository.upsert_continent(continent)

    def update_continent(self, ext_ref: str, payload: dict[str, object]) -> Continent:
        continent = self._require_entity(self._hierarchy_repository.get_continent(ext_ref), "Continent")
        continent.name = str(payload.get("name", continent.name)).strip() or continent.name
        continent.climate_summary = str(payload.get("climate_summary", continent.climate_summary)).strip()
        continent.is_locked = bool(payload.get("is_locked", continent.is_locked))
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
    def _require_entity(entity: object | None, label: str) -> object:
        if entity is None:
            raise ValueError(f"{label} does not exist.")
        return entity


class SimulationService:
    def __init__(self, world_repository: WorldRepository) -> None:
        self._world_repository = world_repository
        self._engine = SimulationEngine()

    def simulate(self, request: SimulationRequest) -> SimulationRun:
        if self._world_repository.get_world(request.world_ref) is None:
            msg = f"world_ref does not exist: {request.world_ref}"
            raise ValueError(msg)
        return self._engine.run(request)


class ImportExportService:
    def __init__(
        self,
        world_repository: WorldRepository,
        json_codec: JsonWorldCodec,
        pdf_exporter: PdfExporter,
        exports_dir: Path,
    ) -> None:
        self._world_repository = world_repository
        self._json_codec = json_codec
        self._pdf_exporter = pdf_exporter
        self._exports_dir = exports_dir
        self._exports_dir.mkdir(parents=True, exist_ok=True)

    def export_world_json(self, world_ref: str) -> Path:
        world = self._world_repository.get_world(world_ref)
        if world is None:
            raise ValueError(f"Unknown world: {world_ref}")
        payload = self._json_codec.serialize_world(asdict(world))
        target = self._exports_dir / f"world-{world_ref}.json"
        target.write_text(payload, encoding="utf-8")
        return target

    def import_world_json(self, source: Path) -> World:
        model = self._json_codec.deserialize_world(source.read_text(encoding="utf-8"))
        world = World(**model)
        return self._world_repository.upsert_world(world)

    def export_world_pdf(self, world_ref: str) -> Path:
        world = self._world_repository.get_world(world_ref)
        if world is None:
            raise ValueError(f"Unknown world: {world_ref}")
        target = self._exports_dir / f"world-{world_ref}.pdf"
        self._pdf_exporter.export_world_summary(world, target)
        return target
