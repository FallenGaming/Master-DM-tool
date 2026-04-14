# World Studio

Offline-first desktop application for long-term D&D world simulation, editing, and export workflows.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
world-studio-migrate
world-studio
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for:
- layered architecture
- domain model
- SQLite schema strategy
- JSON import/export strategy
- simulation and event engine design
- node map design
- phased implementation roadmap

## Current implemented slices

- Phase 1: architecture baseline, migrations, world CRUD, shell UI, JSON/PDF export adapters
- Phase 2: full hierarchy CRUD services/repositories and a tabbed hierarchy editor for:
  - continents
  - empires
  - kingdoms
  - regions
  - settlements
  - points of interest
  - routes