from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from world_studio.domain.enums import EventScope


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EventDefinition:
    id: int | None
    ext_ref: str
    name: str
    scope: EventScope
    trigger_mode: str
    condition_expression: dict[str, Any]
    modifiers: dict[str, Any]
    chain_event_refs: list[str] = field(default_factory=list)
    enabled: bool = True
    is_locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventInstance:
    id: int | None
    ext_ref: str
    world_ref: str
    definition_ref: str
    scope: EventScope
    target_ref: str | None
    started_utc: datetime = field(default_factory=utc_now)
    ends_utc: datetime | None = None
    resolved: bool = False
    outcome_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
