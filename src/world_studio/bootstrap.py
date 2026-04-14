from __future__ import annotations

from dataclasses import dataclass

from world_studio.application.services import (
    GenerationAppService,
    HierarchyService,
    ImportExportService,
    SocialService,
    SimulationService,
    WorldService,
)
from world_studio.config import AppPaths, build_default_paths
from world_studio.data.database import Database
from world_studio.data.repositories import HierarchyRepository, SocialRepository, WorldRepository
from world_studio.infrastructure.json_io import JsonWorldCodec
from world_studio.infrastructure.pdf_export import PdfExporter


@dataclass
class ServiceContainer:
    paths: AppPaths
    database: Database
    world_repository: WorldRepository
    hierarchy_repository: HierarchyRepository
    social_repository: SocialRepository
    world_service: WorldService
    hierarchy_service: HierarchyService
    social_service: SocialService
    generation_service: GenerationAppService
    simulation_service: SimulationService
    import_export_service: ImportExportService


def build_container() -> ServiceContainer:
    paths = build_default_paths()
    database = Database(paths.database_path)
    world_repository = WorldRepository(database)
    hierarchy_repository = HierarchyRepository(database)
    social_repository = SocialRepository(database)
    world_service = WorldService(world_repository)
    hierarchy_service = HierarchyService(hierarchy_repository)
    social_service = SocialService(social_repository)
    generation_service = GenerationAppService(world_service, hierarchy_service, social_service)
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
        social_repository=social_repository,
        world_service=world_service,
        hierarchy_service=hierarchy_service,
        social_service=social_service,
        generation_service=generation_service,
        simulation_service=simulation_service,
        import_export_service=import_export_service,
    )
