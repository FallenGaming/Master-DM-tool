# World Studio Architecture and Delivery Plan

## 1) Full Project Architecture

World Studio uses a layered modular architecture with explicit boundaries:

1. **UI Layer (`world_studio.ui`)**
   - PySide6 windows, pages, dialogs, and reusable widgets.
   - Binds view-state to application services.
   - No direct SQL or simulation algorithm code.

2. **Application Layer (`world_studio.application`)**
   - Use-case orchestration services:
     - world generation
     - simulation runs
     - snapshot creation/restore
     - import/export
     - PDF export
   - Coordinates repositories and domain services.
   - Applies transaction boundaries and audit logging.

3. **Domain Layer (`world_studio.domain`)**
   - Core entities and value objects.
   - RuleSet definitions.
   - Simulation engine and event resolution engine.
   - Relationship evolution logic.
   - Entity lock and override semantics.

4. **Data Layer (`world_studio.data`)**
   - SQLite gateway and schema migrations.
   - Repositories for aggregate roots and projections.
   - Snapshot persistence and restore pipeline.
   - Query models for filters/search.

5. **Infrastructure Layer (`world_studio.infrastructure`)**
   - JSON serialization/import/export.
   - PDF rendering adapters.
   - Node graph projection for map view.
   - Logging, filesystem, backup helpers.

Cross-cutting:
- `world_studio.config` for app settings and paths.
- `world_studio.bootstrap` for dependency wiring.

---

## 2) Proposed Folder/File Structure

```text
src/world_studio/
  __init__.py
  main.py
  config.py
  bootstrap.py
  application/
    __init__.py
    services.py
  domain/
    __init__.py
    enums.py
    world.py
    population.py
    events.py
    simulation.py
  data/
    __init__.py
    database.py
    migrations.py
    repositories.py
  infrastructure/
    __init__.py
    json_io.py
    pdf_export.py
    map_graph.py
  ui/
    __init__.py
    main_window.py
    pages.py
tests/
  test_migrations.py
  test_json_round_trip.py
docs/
  architecture.md
```

This structure keeps use-cases, rules, persistence, and UI cleanly separated while remaining practical for iterative growth.

---

## 3) Domain Model

### Geographic / political hierarchy
- `World`
- `Continent`
- `Empire`
- `Kingdom`
- `Region`
- `SettlementNode` (village/town/city/outpost)
- `PointOfInterest`
- `RouteConnection`

### Population and social
- `NPC`
- `Household`
- `Relationship` (weighted, typed, temporal history)
- `Occupation`
- `Race`
- `SubRace`
- `Trait`
- `NamePool`
- `Monster`

### Simulation and governance
- `RuleSet`
- `EventDefinition`
- `EventInstance`
- `Snapshot`
- `SimulationRun`
- `TagMetadata`

### Domain invariants
- Lockable entities (`is_locked`) are immutable for simulation unless a forced override is used.
- Manual edits always win over generated defaults.
- Simulation time only advances through explicit user actions.
- Snapshot restore is authoritative and transaction-safe.

---

## 4) SQLite Schema Design

### Core tables (current phase starts these)
- `schema_migrations(version, applied_utc)`
- `worlds`
- `continents`
- `empires`
- `kingdoms`
- `regions`
- `settlement_nodes`
- `route_connections`
- `points_of_interest`

### Population and social tables
- `npcs`
- `households`
- `household_members`
- `relationships`
- `relationship_history`
- `occupations`
- `races`
- `subraces`
- `traits`
- `npc_traits`
- `name_pools`
- `name_entries`
- `monsters`

### Rules, events, simulation
- `rule_sets`
- `event_definitions`
- `event_instances`
- `simulation_runs`
- `simulation_changes`
- `entity_locks`

### Snapshot and audit
- `snapshots`
- `snapshot_blobs` (JSON payload and checksum)
- `change_log`

### Schema strategy
- Integer primary keys for internal joins.
- UUID text fields for external stable references/import IDs.
- JSON text columns where extensible metadata is needed.
- Every table tracks `created_utc`, `updated_utc`.
- Migration versions are forward-only SQL scripts coordinated in Python migration registry.

---

## 5) JSON Import/Export Schema Strategy

### Envelope
```json
{
  "schema_version": "1.0.0",
  "exported_utc": "2026-04-14T12:00:00Z",
  "kind": "full_world|partial|npcs|settlements|rules|events|templates",
  "world_ref": "uuid",
  "payload": { "...": "kind specific body" }
}
```

### Rules
- Stable UUID references across files.
- Explicit entity type and dependency lists for partial imports.
- Validation via pydantic models before persistence.
- Import modes:
  - `merge`
  - `replace`
  - `preview_only`
- Conflict policy:
  - keep_local
  - keep_imported
  - prompt_per_entity (UI-driven)

---

## 6) Simulation Engine Design

Simulation uses deterministic staged passes:

1. `precheck`: verify locks, snapshot readiness, and active RuleSet.
2. `demography_pass`: aging, mortality, births, health progression.
3. `economy_pass`: occupation shifts, trade pressure modifiers.
4. `migration_pass`: movement based on safety/resources/routes.
5. `settlement_pass`: settlement growth/shrinkage/type transitions.
6. `relationship_pass`: bond drift, new ties, rivalry shifts.
7. `event_pass`: execute scheduled and conditional events.
8. `post_pass`: write summary log, produce `SimulationRun`.

Design principles:
- Manual advance by `day|week|month|season|year|custom_days`.
- Dry-run preview mode returns projected changes without committing.
- Forced GM override commands can alter entities regardless of simulation suggestions.

---

## 7) Event Engine Design

### EventDefinition
- scope: world/continent/empire/kingdom/region/settlement/npc
- trigger type: scheduled, probabilistic, conditional
- condition expression (JSON DSL)
- modifiers list (e.g., `population_delta`, `wealth_delta`, `health_risk`)
- duration model
- optional chained events

### Event evaluation flow
1. Collect candidate events by scope and active ruleset.
2. Evaluate conditions against world state projection.
3. Roll weighted probability where applicable.
4. Emit EventInstance + downstream changes.
5. Persist and attach to simulation run report.

---

## 8) Node-Based Map System Design

Map model is graph-first:
- Node types: settlement, POI, natural feature, route junction.
- Edge types: road, river, sea lane, mountain pass, portal.
- Node stores strategic attributes:
  - population
  - safety
  - resource index
  - political owner
  - growth potential

Rendering approach:
- `QGraphicsScene` + custom `QGraphicsItem` node/edge elements.
- Zoom level controls label density and detail overlays.
- Context panel reflects selected node/entity.
- Simulation updates map graph projection after each run.

---

## 9) UI Page Structure

- **Dashboard**: world summary, recent events, pending actions.
- **World Browser**: hierarchical tree (world -> continent -> ... -> settlement).
- **Map View**: graph visualization with filters and inspect panel.
- **NPC Browser**: searchable table + detail editor.
- **Relationships**: graph/list editor with history timeline.
- **Events**: definitions, triggers, active instances.
- **Simulation**: advance controls, preview, apply, result log.
- **Snapshots**: create, list, compare, restore.
- **Rules & Templates**: editable rule sets and content libraries.
- **Import/Export**: JSON package manager and PDF export actions.

---

## 10) Phased Implementation Milestones

### Phase 1 (implemented now)
Goal:
- Foundational architecture, core models, migrations, shell UI, and basic services.

### Phase 2
Goal:
- Complete CRUD repositories for full hierarchy and base editors in UI.

Status:
- implemented hierarchy CRUD repositories and services for:
  - continents
  - empires
  - kingdoms
  - regions
  - settlement nodes
  - points of interest
  - route connections
- implemented reusable tabbed hierarchy editor UI with create/update/delete workflows.
- added automated tests for hierarchy repositories and services.

### Phase 3
Goal:
- Rich NPC/relationship models and editors with lock/override semantics.

Status:
- implemented social repository support for:
  - races
  - subraces
  - occupations
  - traits
  - NPCs
  - relationships
- implemented `SocialService` with lock enforcement and explicit force-override paths for GM control.
- implemented an `NPCs & Relationships` desktop page with:
  - NPC create/update/delete
  - relationship create/update/delete
  - lock toggles
  - force-override actions for locked entities
- added automated tests for social repositories and lock override behavior.

### Phase 4
Goal:
- Simulation pipeline passes, preview support, run logging, result inspection.

Status (generation subsystem delivered in this phase):
- implemented modular initial-state generation subsystem under `world_studio.generation`:
  - configuration and result models
  - deterministic seeded rules and naming support
  - continent/political/region/settlement generators
  - demographics + occupation allocation + NPC generation
  - relationship seeding
  - orchestration service for full world auto-population
- implemented `GenerationAppService` in the application layer and container wiring.
- integrated generation trigger UI page using application services only (no UI-embedded generation logic).
- generated output persists through existing hierarchy/social services, remaining lock/override compatible and simulation-ready.
- added integration tests validating hierarchy + social graph generation and lock override compatibility.

### Phase 5
Goal:
- Event DSL editor, event execution graph, chained consequences.

### Phase 6
Goal:
- Node-based map renderer with multi-scale interactions and route editing.

### Phase 7
Goal:
- JSON import/export breadth (full + partial), conflict resolution UI.

### Phase 8
Goal:
- PDF export packs (DM/player variants), snapshots comparison and backups.

### Phase 9
Goal:
- Hardening: tests, data migration fixtures, performance profiling, packaging.

---

## 11) Implementation Start

This repository now begins with a production-oriented baseline:
- Layered package layout under `src/world_studio`.
- Migration-ready SQLite gateway.
- Core domain entities and simulation/event service scaffolding.
- PySide6 desktop shell with multi-page navigation.
- JSON and PDF infrastructure adapters.
- Initial tests for migration and JSON round-trip.
