from __future__ import annotations

import json
from datetime import UTC, datetime
from sqlite3 import Row
from typing import Any

from world_studio.data.database import Database
from world_studio.domain.enums import NodeType, RelationshipType, SettlementType
from world_studio.domain.population import Npc, Occupation, Race, Relationship, SubRace, Trait
from world_studio.domain.world import (
    Continent,
    Empire,
    Kingdom,
    PointOfInterest,
    Region,
    RouteConnection,
    SnapshotRecord,
    SettlementNode,
    World,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


class _RepositoryBase:
    def __init__(self, database: Database) -> None:
        self._database = database

    def _upsert_row(self, table: str, ext_ref: str, values: dict[str, Any]) -> tuple[int, str, str]:
        now = utc_now_iso()
        with self._database.connect() as connection:
            existing = connection.execute(
                f"SELECT id, created_utc FROM {table} WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
            if existing:
                assignments = ", ".join(f"{column} = ?" for column in values)
                connection.execute(
                    f"UPDATE {table} SET {assignments}, updated_utc = ? WHERE ext_ref = ?",
                    (*values.values(), now, ext_ref),
                )
                return int(existing["id"]), str(existing["created_utc"]), now

            columns = ["ext_ref", *values.keys(), "created_utc", "updated_utc"]
            placeholders = ", ".join(["?"] * len(columns))
            cursor = connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                (ext_ref, *values.values(), now, now),
            )
        return int(cursor.lastrowid), now, now

    def _delete_row(self, table: str, ext_ref: str) -> None:
        with self._database.connect() as connection:
            connection.execute(f"DELETE FROM {table} WHERE ext_ref = ?", (ext_ref,))


class WorldRepository(_RepositoryBase):
    def upsert_world(self, world: World) -> World:
        row_id, created_utc, updated_utc = self._upsert_row(
            table="worlds",
            ext_ref=world.ext_ref,
            values={
                "name": world.name,
                "description": world.description,
                "active_ruleset_ref": world.active_ruleset_ref,
                "is_locked": int(world.is_locked),
                "metadata_json": json.dumps(world.metadata),
            },
        )
        world.id = row_id
        world.created_utc = _parse_datetime(created_utc)
        world.updated_utc = _parse_datetime(updated_utc)
        return world

    def get_world(self, ext_ref: str) -> World | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM worlds WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
        if row is None:
            return None
        return _world_from_row(row)

    def list_worlds(self) -> list[World]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM worlds ORDER BY updated_utc DESC, name ASC"
            ).fetchall()
        return [_world_from_row(row) for row in rows]

    def create_snapshot(self, snapshot: SnapshotRecord) -> SnapshotRecord:
        with self._database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO snapshots (
                    ext_ref,
                    world_ref,
                    name,
                    created_utc,
                    snapshot_json,
                    checksum
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.ext_ref,
                    snapshot.world_ref,
                    snapshot.name,
                    snapshot.created_utc.isoformat(),
                    snapshot.snapshot_json,
                    snapshot.checksum,
                ),
            )
        snapshot.id = int(cursor.lastrowid)
        return snapshot

    def get_snapshot(self, ext_ref: str) -> SnapshotRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
        if row is None:
            return None
        return _snapshot_from_row(row)

    def list_snapshots(self, world_ref: str) -> list[SnapshotRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE world_ref = ?
                ORDER BY created_utc DESC, name ASC
                """,
                (world_ref,),
            ).fetchall()
        return [_snapshot_from_row(row) for row in rows]

    def delete_snapshot(self, ext_ref: str) -> None:
        self._delete_row("snapshots", ext_ref)


class HierarchyRepository(_RepositoryBase):
    def upsert_continent(self, continent: Continent) -> Continent:
        row_id, created_utc, updated_utc = self._upsert_row(
            "continents",
            continent.ext_ref,
            {
                "world_ref": continent.world_ref,
                "name": continent.name,
                "climate_summary": continent.climate_summary,
                "is_locked": int(continent.is_locked),
                "metadata_json": json.dumps(continent.metadata),
            },
        )
        continent.id = row_id
        continent.created_utc = _parse_datetime(created_utc)
        continent.updated_utc = _parse_datetime(updated_utc)
        return continent

    def get_continent(self, ext_ref: str) -> Continent | None:
        return self._get_one(
            table="continents",
            ext_ref=ext_ref,
            mapper=_continent_from_row,
        )

    def list_continents(self, world_ref: str) -> list[Continent]:
        return self._list_by_world_ref("continents", world_ref, _continent_from_row)

    def delete_continent(self, ext_ref: str) -> None:
        self._delete_row("continents", ext_ref)

    def upsert_empire(self, empire: Empire) -> Empire:
        row_id, created_utc, updated_utc = self._upsert_row(
            "empires",
            empire.ext_ref,
            {
                "world_ref": empire.world_ref,
                "continent_ref": empire.continent_ref,
                "name": empire.name,
                "governing_style": empire.governing_style,
                "is_locked": int(empire.is_locked),
                "metadata_json": json.dumps(empire.metadata),
            },
        )
        empire.id = row_id
        empire.created_utc = _parse_datetime(created_utc)
        empire.updated_utc = _parse_datetime(updated_utc)
        return empire

    def get_empire(self, ext_ref: str) -> Empire | None:
        return self._get_one("empires", ext_ref, _empire_from_row)

    def list_empires(self, world_ref: str) -> list[Empire]:
        return self._list_by_world_ref("empires", world_ref, _empire_from_row)

    def delete_empire(self, ext_ref: str) -> None:
        self._delete_row("empires", ext_ref)

    def upsert_kingdom(self, kingdom: Kingdom) -> Kingdom:
        row_id, created_utc, updated_utc = self._upsert_row(
            "kingdoms",
            kingdom.ext_ref,
            {
                "world_ref": kingdom.world_ref,
                "empire_ref": kingdom.empire_ref,
                "name": kingdom.name,
                "stability_index": kingdom.stability_index,
                "is_locked": int(kingdom.is_locked),
                "metadata_json": json.dumps(kingdom.metadata),
            },
        )
        kingdom.id = row_id
        kingdom.created_utc = _parse_datetime(created_utc)
        kingdom.updated_utc = _parse_datetime(updated_utc)
        return kingdom

    def get_kingdom(self, ext_ref: str) -> Kingdom | None:
        return self._get_one("kingdoms", ext_ref, _kingdom_from_row)

    def list_kingdoms(self, world_ref: str) -> list[Kingdom]:
        return self._list_by_world_ref("kingdoms", world_ref, _kingdom_from_row)

    def delete_kingdom(self, ext_ref: str) -> None:
        self._delete_row("kingdoms", ext_ref)

    def upsert_region(self, region: Region) -> Region:
        row_id, created_utc, updated_utc = self._upsert_row(
            "regions",
            region.ext_ref,
            {
                "world_ref": region.world_ref,
                "kingdom_ref": region.kingdom_ref,
                "name": region.name,
                "biome": region.biome,
                "is_locked": int(region.is_locked),
                "metadata_json": json.dumps(region.metadata),
            },
        )
        region.id = row_id
        region.created_utc = _parse_datetime(created_utc)
        region.updated_utc = _parse_datetime(updated_utc)
        return region

    def get_region(self, ext_ref: str) -> Region | None:
        return self._get_one("regions", ext_ref, _region_from_row)

    def list_regions(self, world_ref: str) -> list[Region]:
        return self._list_by_world_ref("regions", world_ref, _region_from_row)

    def delete_region(self, ext_ref: str) -> None:
        self._delete_row("regions", ext_ref)

    def upsert_settlement(self, settlement: SettlementNode) -> SettlementNode:
        row_id, created_utc, updated_utc = self._upsert_row(
            "settlement_nodes",
            settlement.ext_ref,
            {
                "world_ref": settlement.world_ref,
                "region_ref": settlement.region_ref,
                "name": settlement.name,
                "kind": settlement.kind.value,
                "population": settlement.population,
                "resource_index": settlement.resource_index,
                "safety_index": settlement.safety_index,
                "x": settlement.x,
                "y": settlement.y,
                "is_locked": int(settlement.is_locked),
                "metadata_json": json.dumps(settlement.metadata),
            },
        )
        settlement.id = row_id
        settlement.created_utc = _parse_datetime(created_utc)
        settlement.updated_utc = _parse_datetime(updated_utc)
        return settlement

    def get_settlement(self, ext_ref: str) -> SettlementNode | None:
        return self._get_one("settlement_nodes", ext_ref, _settlement_from_row)

    def list_settlements(self, world_ref: str) -> list[SettlementNode]:
        return self._list_by_world_ref("settlement_nodes", world_ref, _settlement_from_row)

    def delete_settlement(self, ext_ref: str) -> None:
        self._delete_row("settlement_nodes", ext_ref)

    def upsert_point_of_interest(self, poi: PointOfInterest) -> PointOfInterest:
        row_id, created_utc, updated_utc = self._upsert_row(
            "points_of_interest",
            poi.ext_ref,
            {
                "world_ref": poi.world_ref,
                "region_ref": poi.region_ref,
                "name": poi.name,
                "node_type": poi.node_type.value,
                "x": poi.x,
                "y": poi.y,
                "description": poi.description,
                "is_locked": int(poi.is_locked),
                "metadata_json": json.dumps(poi.metadata),
            },
        )
        poi.id = row_id
        poi.created_utc = _parse_datetime(created_utc)
        poi.updated_utc = _parse_datetime(updated_utc)
        return poi

    def get_point_of_interest(self, ext_ref: str) -> PointOfInterest | None:
        return self._get_one("points_of_interest", ext_ref, _point_of_interest_from_row)

    def list_points_of_interest(self, world_ref: str) -> list[PointOfInterest]:
        return self._list_by_world_ref("points_of_interest", world_ref, _point_of_interest_from_row)

    def delete_point_of_interest(self, ext_ref: str) -> None:
        self._delete_row("points_of_interest", ext_ref)

    def upsert_route(self, route: RouteConnection) -> RouteConnection:
        row_id, created_utc, updated_utc = self._upsert_row(
            "route_connections",
            route.ext_ref,
            {
                "world_ref": route.world_ref,
                "name": route.name,
                "source_ref": route.source_ref,
                "target_ref": route.target_ref,
                "route_type": route.route_type,
                "travel_cost": route.travel_cost,
                "is_locked": int(route.is_locked),
                "metadata_json": json.dumps(route.metadata),
            },
        )
        route.id = row_id
        route.created_utc = _parse_datetime(created_utc)
        route.updated_utc = _parse_datetime(updated_utc)
        return route

    def get_route(self, ext_ref: str) -> RouteConnection | None:
        return self._get_one("route_connections", ext_ref, _route_from_row)

    def list_routes(self, world_ref: str) -> list[RouteConnection]:
        return self._list_by_world_ref("route_connections", world_ref, _route_from_row)

    def delete_route(self, ext_ref: str) -> None:
        self._delete_row("route_connections", ext_ref)

    def _get_one(self, table: str, ext_ref: str, mapper: Any) -> Any | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
        if row is None:
            return None
        return mapper(row)

    def _list_by_world_ref(self, table: str, world_ref: str, mapper: Any) -> list[Any]:
        with self._database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM {table}
                WHERE world_ref = ?
                ORDER BY updated_utc DESC, name ASC
                """,
                (world_ref,),
            ).fetchall()
        return [mapper(row) for row in rows]


class SocialRepository(_RepositoryBase):
    def upsert_race(self, race: Race) -> Race:
        row_id, _, _ = self._upsert_row(
            "races",
            race.ext_ref,
            {
                "name": race.name,
                "lifespan_years": race.lifespan_years,
                "is_default": int(race.is_default),
                "metadata_json": json.dumps(race.metadata),
            },
        )
        race.id = row_id
        return race

    def get_race(self, ext_ref: str) -> Race | None:
        return self._get_one("races", ext_ref, _race_from_row)

    def list_races(self) -> list[Race]:
        return self._list_simple("races", _race_from_row)

    def delete_race(self, ext_ref: str) -> None:
        self._delete_row("races", ext_ref)

    def upsert_subrace(self, subrace: SubRace) -> SubRace:
        row_id, _, _ = self._upsert_row(
            "subraces",
            subrace.ext_ref,
            {
                "race_ref": subrace.race_ref,
                "name": subrace.name,
                "metadata_json": json.dumps(subrace.metadata),
            },
        )
        subrace.id = row_id
        return subrace

    def get_subrace(self, ext_ref: str) -> SubRace | None:
        return self._get_one("subraces", ext_ref, _subrace_from_row)

    def list_subraces(self, race_ref: str | None = None) -> list[SubRace]:
        if race_ref:
            return self._list_by_column("subraces", "race_ref", race_ref, _subrace_from_row)
        return self._list_simple("subraces", _subrace_from_row)

    def delete_subrace(self, ext_ref: str) -> None:
        self._delete_row("subraces", ext_ref)

    def upsert_occupation(self, occupation: Occupation) -> Occupation:
        row_id, _, _ = self._upsert_row(
            "occupations",
            occupation.ext_ref,
            {
                "name": occupation.name,
                "category": occupation.category,
                "rarity": occupation.rarity,
                "metadata_json": json.dumps(occupation.metadata),
            },
        )
        occupation.id = row_id
        return occupation

    def get_occupation(self, ext_ref: str) -> Occupation | None:
        return self._get_one("occupations", ext_ref, _occupation_from_row)

    def list_occupations(self) -> list[Occupation]:
        return self._list_simple("occupations", _occupation_from_row)

    def delete_occupation(self, ext_ref: str) -> None:
        self._delete_row("occupations", ext_ref)

    def upsert_trait(self, trait: Trait) -> Trait:
        row_id, _, _ = self._upsert_row(
            "traits",
            trait.ext_ref,
            {
                "name": trait.name,
                "polarity": trait.polarity,
                "metadata_json": json.dumps(trait.metadata),
            },
        )
        trait.id = row_id
        return trait

    def get_trait(self, ext_ref: str) -> Trait | None:
        return self._get_one("traits", ext_ref, _trait_from_row)

    def list_traits(self) -> list[Trait]:
        return self._list_simple("traits", _trait_from_row)

    def delete_trait(self, ext_ref: str) -> None:
        self._delete_row("traits", ext_ref)

    def upsert_npc(self, npc: Npc) -> Npc:
        row_id, created_utc, updated_utc = self._upsert_row(
            "npcs",
            npc.ext_ref,
            {
                "world_ref": npc.world_ref,
                "display_name": npc.display_name,
                "age_years": npc.age_years,
                "race_ref": npc.race_ref,
                "subrace_ref": npc.subrace_ref,
                "occupation_ref": npc.occupation_ref,
                "residence_node_ref": npc.residence_node_ref,
                "health_index": npc.health_index,
                "wealth_index": npc.wealth_index,
                "is_locked": int(npc.is_locked),
                "notes": npc.notes,
                "metadata_json": json.dumps(npc.metadata),
            },
        )
        npc.id = row_id
        npc.created_utc = _parse_datetime(created_utc)
        npc.updated_utc = _parse_datetime(updated_utc)
        return npc

    def get_npc(self, ext_ref: str) -> Npc | None:
        return self._get_one("npcs", ext_ref, _npc_from_row)

    def list_npcs(self, world_ref: str) -> list[Npc]:
        return self._list_by_column("npcs", "world_ref", world_ref, _npc_from_row)

    def delete_npc(self, ext_ref: str) -> None:
        self._delete_row("npcs", ext_ref)

    def upsert_relationship(self, relationship: Relationship) -> Relationship:
        row_id, created_utc, updated_utc = self._upsert_row(
            "relationships",
            relationship.ext_ref,
            {
                "world_ref": relationship.world_ref,
                "source_npc_ref": relationship.source_npc_ref,
                "target_npc_ref": relationship.target_npc_ref,
                "relation_type": relationship.relation_type.value,
                "weight": relationship.weight,
                "history_json": json.dumps(relationship.history),
                "is_locked": int(relationship.is_locked),
                "metadata_json": json.dumps(relationship.metadata),
            },
        )
        relationship.id = row_id
        relationship.created_utc = _parse_datetime(created_utc)
        relationship.updated_utc = _parse_datetime(updated_utc)
        return relationship

    def get_relationship(self, ext_ref: str) -> Relationship | None:
        return self._get_one("relationships", ext_ref, _relationship_from_row)

    def list_relationships(self, world_ref: str, npc_ref: str | None = None) -> list[Relationship]:
        with self._database.connect() as connection:
            if npc_ref:
                rows = connection.execute(
                    """
                    SELECT * FROM relationships
                    WHERE world_ref = ? AND (source_npc_ref = ? OR target_npc_ref = ?)
                    ORDER BY updated_utc DESC, relation_type ASC
                    """,
                    (world_ref, npc_ref, npc_ref),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM relationships
                    WHERE world_ref = ?
                    ORDER BY updated_utc DESC, relation_type ASC
                    """,
                    (world_ref,),
                ).fetchall()
        return [_relationship_from_row(row) for row in rows]

    def delete_relationship(self, ext_ref: str) -> None:
        self._delete_row("relationships", ext_ref)

    def _get_one(self, table: str, ext_ref: str, mapper: Any) -> Any | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE ext_ref = ?",
                (ext_ref,),
            ).fetchone()
        if row is None:
            return None
        return mapper(row)

    def _list_simple(self, table: str, mapper: Any) -> list[Any]:
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} ORDER BY name ASC, ext_ref ASC"
            ).fetchall()
        return [mapper(row) for row in rows]

    def _list_by_column(self, table: str, column: str, value: str, mapper: Any) -> list[Any]:
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE {column} = ? ORDER BY updated_utc DESC, ext_ref ASC",
                (value,),
            ).fetchall()
        return [mapper(row) for row in rows]


def _world_from_row(row: Row) -> World:
    return World(
        id=row["id"],
        ext_ref=row["ext_ref"],
        name=row["name"],
        description=row["description"],
        active_ruleset_ref=row["active_ruleset_ref"],
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _snapshot_from_row(row: Row) -> SnapshotRecord:
    return SnapshotRecord(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        name=row["name"],
        snapshot_json=row["snapshot_json"],
        checksum=row["checksum"],
        created_utc=_parse_datetime(row["created_utc"]),
    )


def _continent_from_row(row: Row) -> Continent:
    return Continent(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        name=row["name"],
        climate_summary=row["climate_summary"],
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _empire_from_row(row: Row) -> Empire:
    return Empire(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        continent_ref=row["continent_ref"],
        name=row["name"],
        governing_style=row["governing_style"],
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _kingdom_from_row(row: Row) -> Kingdom:
    return Kingdom(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        empire_ref=row["empire_ref"],
        name=row["name"],
        stability_index=float(row["stability_index"]),
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _region_from_row(row: Row) -> Region:
    return Region(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        kingdom_ref=row["kingdom_ref"],
        name=row["name"],
        biome=row["biome"],
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _settlement_from_row(row: Row) -> SettlementNode:
    return SettlementNode(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        region_ref=row["region_ref"],
        name=row["name"],
        kind=SettlementType(row["kind"]),
        population=int(row["population"]),
        resource_index=float(row["resource_index"]),
        safety_index=float(row["safety_index"]),
        x=float(row["x"]),
        y=float(row["y"]),
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _point_of_interest_from_row(row: Row) -> PointOfInterest:
    return PointOfInterest(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        region_ref=row["region_ref"],
        name=row["name"],
        node_type=NodeType(row["node_type"]),
        x=float(row["x"]),
        y=float(row["y"]),
        description=row["description"],
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _route_from_row(row: Row) -> RouteConnection:
    return RouteConnection(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        name=row["name"],
        source_ref=row["source_ref"],
        target_ref=row["target_ref"],
        route_type=row["route_type"],
        travel_cost=float(row["travel_cost"]),
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _race_from_row(row: Row) -> Race:
    return Race(
        id=row["id"],
        ext_ref=row["ext_ref"],
        name=row["name"],
        lifespan_years=int(row["lifespan_years"]),
        is_default=bool(row["is_default"]),
        metadata=_parse_json_object(row["metadata_json"]),
    )


def _subrace_from_row(row: Row) -> SubRace:
    return SubRace(
        id=row["id"],
        ext_ref=row["ext_ref"],
        race_ref=row["race_ref"],
        name=row["name"],
        metadata=_parse_json_object(row["metadata_json"]),
    )


def _occupation_from_row(row: Row) -> Occupation:
    return Occupation(
        id=row["id"],
        ext_ref=row["ext_ref"],
        name=row["name"],
        category=row["category"],
        rarity=float(row["rarity"]),
        metadata=_parse_json_object(row["metadata_json"]),
    )


def _trait_from_row(row: Row) -> Trait:
    return Trait(
        id=row["id"],
        ext_ref=row["ext_ref"],
        name=row["name"],
        polarity=float(row["polarity"]),
        metadata=_parse_json_object(row["metadata_json"]),
    )


def _npc_from_row(row: Row) -> Npc:
    return Npc(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        display_name=row["display_name"],
        age_years=int(row["age_years"]),
        race_ref=row["race_ref"],
        subrace_ref=row["subrace_ref"],
        occupation_ref=row["occupation_ref"],
        residence_node_ref=row["residence_node_ref"],
        health_index=float(row["health_index"]),
        wealth_index=float(row["wealth_index"]),
        is_locked=bool(row["is_locked"]),
        notes=row["notes"],
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )


def _relationship_from_row(row: Row) -> Relationship:
    return Relationship(
        id=row["id"],
        ext_ref=row["ext_ref"],
        world_ref=row["world_ref"],
        source_npc_ref=row["source_npc_ref"],
        target_npc_ref=row["target_npc_ref"],
        relation_type=RelationshipType(row["relation_type"]),
        weight=float(row["weight"]),
        history=_parse_json_list(row["history_json"]),
        is_locked=bool(row["is_locked"]),
        metadata=_parse_json_object(row["metadata_json"]),
        created_utc=_parse_datetime(row["created_utc"]),
        updated_utc=_parse_datetime(row["updated_utc"]),
    )
