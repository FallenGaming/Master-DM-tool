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