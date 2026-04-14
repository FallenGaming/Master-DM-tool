from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    data_dir: Path
    database_path: Path
    exports_dir: Path
    logs_dir: Path


def build_default_paths(root: Path | None = None) -> AppPaths:
    base = root or Path.home() / ".world_studio"
    data_dir = base / "data"
    exports_dir = base / "exports"
    logs_dir = base / "logs"
    return AppPaths(
        root=base,
        data_dir=data_dir,
        database_path=data_dir / "world_studio.sqlite3",
        exports_dir=exports_dir,
        logs_dir=logs_dir,
    )
