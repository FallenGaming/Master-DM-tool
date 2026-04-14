from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from world_studio.data.repositories import WorldRepository
from world_studio.domain.simulation import SimulationEngine, SimulationRequest, SimulationRun
from world_studio.domain.world import World
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
