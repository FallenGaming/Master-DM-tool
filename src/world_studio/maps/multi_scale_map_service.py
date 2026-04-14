from __future__ import annotations

from world_studio.infrastructure.map_graph import MapGraphProjection
from world_studio.maps.map_projection_service import MapProjectionService
from world_studio.maps.node_positioning_models import MapScale


class MultiScaleMapService:
    def __init__(self, projection_service: MapProjectionService) -> None:
        self._projection_service = projection_service

    def project(
        self,
        world_ref: str,
        *,
        scale: MapScale,
        focus_ref: str | None = None,
    ) -> MapGraphProjection:
        return self._projection_service.build_projection(
            world_ref=world_ref,
            scale=scale,
            focus_ref=focus_ref,
        )
