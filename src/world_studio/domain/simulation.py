from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from world_studio.domain.enums import SimulationStep
from world_studio.domain.world import World


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SimulationRequest:
    world_ref: str
    step: SimulationStep
    quantity: int = 1
    custom_days: int | None = None
    create_snapshot: bool = True
    preview_only: bool = False

    def duration_days(self) -> int:
        if self.step == SimulationStep.DAY:
            return self.quantity
        if self.step == SimulationStep.WEEK:
            return self.quantity * 7
        if self.step == SimulationStep.MONTH:
            return self.quantity * 30
        if self.step == SimulationStep.SEASON:
            return self.quantity * 90
        if self.step == SimulationStep.YEAR:
            return self.quantity * 365
        if self.step == SimulationStep.CUSTOM_DAYS:
            if not self.custom_days or self.custom_days <= 0:
                raise ValueError("custom_days must be positive for custom simulation steps.")
            return self.custom_days
        raise ValueError(f"Unsupported simulation step: {self.step}")


@dataclass
class SimulationChange:
    entity_type: str
    entity_ref: str
    field_name: str
    previous_value: str
    new_value: str
    reason: str


@dataclass
class SimulationRun:
    id: int | None
    world_ref: str
    ext_ref: str | None = None
    started_utc: datetime = field(default_factory=utc_now)
    finished_utc: datetime | None = None
    simulated_days: int = 0
    snapshot_ref: str | None = None
    preview_only: bool = False
    changes: list[SimulationChange] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def close(self) -> None:
        self.finished_utc = utc_now()

    @property
    def elapsed(self) -> timedelta | None:
        if self.finished_utc is None:
            return None
        return self.finished_utc - self.started_utc


class SimulationPass(Protocol):
    name: str

    def apply(self, run: SimulationRun, context: object | None = None) -> None:
        """Apply pass side-effects into simulation run change log."""


class NoOpPass:
    def __init__(self, name: str, note: str) -> None:
        self.name = name
        self.note = note

    def apply(self, run: SimulationRun, context: object | None = None) -> None:
        run.notes.append(f"{self.name}: {self.note}")


class SimulationEngine:
    """Coordinates deterministic simulation passes in fixed order."""

    def __init__(self, passes: list[SimulationPass] | None = None) -> None:
        self._passes = passes or [
            NoOpPass("precheck", "Validated locks, snapshots, and active rules."),
            NoOpPass("demography", "Aging and mortality pass pending phase 4."),
            NoOpPass("economy", "Occupation/economy pass pending phase 4."),
            NoOpPass("migration", "Migration route scoring pass pending phase 4."),
            NoOpPass("settlements", "Settlement transition pass pending phase 4."),
            NoOpPass("relationships", "Relationship drift pass pending phase 4."),
            NoOpPass("events", "Event resolution pass pending phase 5."),
            NoOpPass("post", "Run summary and audit persistence pending phase 4."),
        ]

    def run(self, request: SimulationRequest, world: World, context: object | None = None) -> SimulationRun:
        result = SimulationRun(
            id=None,
            ext_ref=str(uuid4()),
            world_ref=world.ext_ref,
            simulated_days=request.duration_days(),
            preview_only=request.preview_only,
        )
        for stage in self._passes:
            stage.apply(result, context)
        result.close()
        return result
