from __future__ import annotations

from dataclasses import dataclass

from world_studio.application.services import (
    HierarchyService,
    ImportExportService,
    SimulationService,
    WorldService,
)
from world_studio.config import AppPaths, build_default_paths
from world_studio.data.database import Database
from world_studio.data.repositories import HierarchyRepository, WorldRepository
from world_studio.infrastructure.json_io import JsonWorldCodec
from world_studio.infrastructure.pdf_export import PdfExporter


@dataclass
class ServiceContainer:
    paths: AppPaths
    database: Database
    world_repository: WorldRepository
    hierarchy_repository: HierarchyRepository
    world_service: WorldService
    hierarchy_service: HierarchyService
    simulation_service: SimulationService
    import_export_service: ImportExportService


def build_container() -> ServiceContainer:
    paths = build_default_paths()
    database = Database(paths.database_path)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    world_service = WorldService(world_repository)
    hierarchy_service = HierarchyService(hierarchy_repository)
    simulation_service = SimulationService(world_repository)
    import_export_service = ImportExportService(
        world_repository=world_repository,
        json_codec=JsonWorldCodec(),
        pdf_exporter=PdfExporter(),
        exports_dir=paths.exports_dir,
    )
    return ServiceContainer(
        paths=paths,
        database=database,
        world_repository=world_repository,
        hierarchy_repository=hierarchy_repository,
        world_service=world_service,
        hierarchy_service=hierarchy_service,
        simulation_service=simulation_service,
        import_export_service=import_export_service,
    )
