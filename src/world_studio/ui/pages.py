from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from world_studio.application.services import (
    HierarchyService,
    ImportExportService,
    SimulationService,
    WorldService,
)
from world_studio.domain.enums import NodeType, SettlementType, SimulationStep
from world_studio.domain.simulation import SimulationRequest
from world_studio.domain.world import World


class DashboardPage(QWidget):
    def __init__(self, world_service: WorldService) -> None:
        super().__init__()
        self._world_service = world_service

        layout = QVBoxLayout(self)
        title = QLabel("World Studio Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        self._summary = QLabel("")
        self._summary.setWordWrap(True)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        layout.addWidget(title)
        layout.addWidget(self._summary)
        layout.addWidget(refresh_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

        self.refresh()

    def refresh(self) -> None:
        worlds = self._world_service.list_worlds()
        self._summary.setText(
            "\n".join(
                [
                    f"Tracked worlds: {len(worlds)}",
                    "Use the World Browser to create and edit world records.",
                    "Use Simulation to advance time manually with previews.",
                ]
            )
        )


class WorldBrowserPage(QWidget):
    def __init__(self, world_service: WorldService) -> None:
        super().__init__()
        self._world_service = world_service

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        right = QVBoxLayout()

        self._world_list = QListWidget()
        self._world_list.currentTextChanged.connect(self._on_select)
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)

        self._name_input = QLineEdit()
        self._description_input = QTextEdit()
        self._create_button = QPushButton("Create World")
        self._create_button.clicked.connect(self._create_world)

        form_box = QGroupBox("Create World")
        form_layout = QFormLayout(form_box)
        form_layout.addRow("Name", self._name_input)
        form_layout.addRow("Description", self._description_input)
        form_layout.addRow("", self._create_button)

        left.addWidget(QLabel("Worlds"))
        left.addWidget(self._world_list)
        left.addWidget(form_box)

        right.addWidget(QLabel("Details"))
        right.addWidget(self._detail)

        root.addLayout(left, stretch=2)
        root.addLayout(right, stretch=3)

        self.refresh()

    def refresh(self) -> None:
        self._world_list.clear()
        for world in self._world_service.list_worlds():
            self._world_list.addItem(f"{world.name} ({world.ext_ref})")

    def _create_world(self) -> None:
        name = self._name_input.text().strip()
        description = self._description_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "World name is required.")
            return
        world = World(id=None, ext_ref=str(uuid4()), name=name, description=description)
        self._world_service.create_world(world)
        self._name_input.clear()
        self._description_input.clear()
        self.refresh()

    def _on_select(self, value: str) -> None:
        if not value:
            self._detail.clear()
            return
        ext_ref = value[value.rfind("(") + 1 : -1]
        world = self._world_service.get_world(ext_ref)
        if world is None:
            self._detail.setPlainText("Missing world.")
            return
        self._detail.setPlainText(
            "\n".join(
                [
                    f"Name: {world.name}",
                    f"Ref: {world.ext_ref}",
                    f"Locked: {'yes' if world.is_locked else 'no'}",
                    f"Active RuleSet: {world.active_ruleset_ref or 'none'}",
                    "",
                    world.description or "(no description)",
                ]
            )
        )


@dataclass(frozen=True)
class EntitySpec:
    key: str
    title: str
    list_method: str
    get_method: str
    create_method: str
    update_method: str
    delete_method: str
    fields: tuple[tuple[str, str], ...]


class EntityCrudPanel(QWidget):
    def __init__(
        self,
        world_service: WorldService,
        hierarchy_service: HierarchyService,
        spec: EntitySpec,
    ) -> None:
        super().__init__()
        self._world_service = world_service
        self._hierarchy_service = hierarchy_service
        self._spec = spec
        self._current_ext_ref: str | None = None
        self._active_world_ref: str = ""

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        right = QVBoxLayout()

        world_row = QHBoxLayout()
        self._world_ref_input = QLineEdit()
        self._world_ref_input.setPlaceholderText("world ext_ref")
        world_refresh = QPushButton("Load")
        world_refresh.clicked.connect(self.refresh)
        world_row.addWidget(QLabel("World Ref"))
        world_row.addWidget(self._world_ref_input)
        world_row.addWidget(world_refresh)

        self._list = QListWidget()
        self._list.currentTextChanged.connect(self._on_select)
        left.addLayout(world_row)
        left.addWidget(self._list)

        form_box = QGroupBox(f"{spec.title} Editor")
        form = QFormLayout(form_box)
        self._field_inputs: dict[str, QWidget] = {}

        for field_key, field_label in spec.fields:
            widget = self._build_field_widget(field_key)
            self._field_inputs[field_key] = widget
            form.addRow(field_label, widget)

        self._locked_input = QCheckBox("Locked against simulation")
        form.addRow("", self._locked_input)

        action_row = QHBoxLayout()
        self._create_button = QPushButton(f"Create {spec.title}")
        self._save_button = QPushButton("Save")
        self._delete_button = QPushButton("Delete")
        self._clear_button = QPushButton("Clear")
        self._create_button.clicked.connect(self._create)
        self._save_button.clicked.connect(self._save)
        self._delete_button.clicked.connect(self._delete)
        self._clear_button.clicked.connect(self._clear_form)
        action_row.addWidget(self._create_button)
        action_row.addWidget(self._save_button)
        action_row.addWidget(self._delete_button)
        action_row.addWidget(self._clear_button)
        action_row.addStretch()
        form.addRow("", action_row)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        right.addWidget(form_box)
        right.addWidget(QLabel("Selection Details"))
        right.addWidget(self._detail)

        root.addLayout(left, stretch=2)
        root.addLayout(right, stretch=3)

    def refresh(self) -> None:
        world_ref = self._resolve_world_ref()
        self._active_world_ref = world_ref
        self._list.clear()
        self._current_ext_ref = None
        self._detail.clear()
        if not world_ref:
            return
        list_method = getattr(self._hierarchy_service, self._spec.list_method)
        records = list_method(world_ref)
        for record in records:
            self._list.addItem(f"{record.name} ({record.ext_ref})")

    def _resolve_world_ref(self) -> str:
        world_ref = self._world_ref_input.text().strip()
        if world_ref:
            return world_ref
        worlds = self._world_service.list_worlds()
        if not worlds:
            return ""
        world_ref = worlds[0].ext_ref
        self._world_ref_input.setText(world_ref)
        return world_ref

    def _on_select(self, value: str) -> None:
        if not value:
            self._current_ext_ref = None
            self._detail.clear()
            return
        ext_ref = value[value.rfind("(") + 1 : -1]
        get_method = getattr(self._hierarchy_service, self._spec.get_method)
        record = get_method(ext_ref)
        if record is None:
            self._current_ext_ref = None
            self._detail.setPlainText(f"{self._spec.title} not found.")
            return
        self._current_ext_ref = ext_ref
        self._populate_form(record)
        self._detail.setPlainText(
            "\n".join(
                [
                    f"Type: {self._spec.title}",
                    f"Name: {record.name}",
                    f"Ref: {record.ext_ref}",
                    f"Locked: {'yes' if record.is_locked else 'no'}",
                ]
            )
        )

    def _populate_form(self, record: object) -> None:
        for field_key, _ in self._spec.fields:
            self._set_field_value(field_key, getattr(record, field_key, ""))
        self._locked_input.setChecked(bool(getattr(record, "is_locked", False)))

    def _collect_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for field_key, _ in self._spec.fields:
            payload[field_key] = self._get_field_value(field_key)
        payload["is_locked"] = self._locked_input.isChecked()
        return payload

    def _create(self) -> None:
        world_ref = self._resolve_world_ref()
        if not world_ref:
            QMessageBox.warning(self, self._spec.title, "Create a world first.")
            return
        create_method = getattr(self._hierarchy_service, self._spec.create_method)
        try:
            create_method(world_ref, self._collect_payload())
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, self._spec.title, str(exc))
            return
        self.refresh()
        self._clear_form()

    def _save(self) -> None:
        if not self._current_ext_ref:
            QMessageBox.warning(self, self._spec.title, f"Select a {self._spec.title.lower()} first.")
            return
        update_method = getattr(self._hierarchy_service, self._spec.update_method)
        try:
            update_method(self._current_ext_ref, self._collect_payload())
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, self._spec.title, str(exc))
            return
        self.refresh()

    def _delete(self) -> None:
        if not self._current_ext_ref:
            QMessageBox.warning(self, self._spec.title, f"Select a {self._spec.title.lower()} first.")
            return
        delete_method = getattr(self._hierarchy_service, self._spec.delete_method)
        delete_method(self._current_ext_ref)
        self.refresh()
        self._clear_form()

    def _clear_form(self) -> None:
        self._current_ext_ref = None
        for field_key, _ in self._spec.fields:
            self._set_field_value(field_key, "")
        self._locked_input.setChecked(False)
        self._detail.clear()

    def _build_field_widget(self, field_key: str) -> QWidget:
        if field_key == "kind":
            combo = QComboBox()
            combo.addItems([value.value for value in SettlementType])
            return combo
        if field_key == "node_type":
            combo = QComboBox()
            combo.addItems([value.value for value in NodeType])
            return combo
        if field_key in {"description", "climate_summary"}:
            text = QTextEdit()
            text.setFixedHeight(80)
            return text
        line = QLineEdit()
        return line

    def _get_field_value(self, field_key: str) -> object:
        widget = self._field_inputs[field_key]
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def _set_field_value(self, field_key: str, value: object) -> None:
        widget = self._field_inputs[field_key]
        text = str(value) if value is not None else ""
        if isinstance(widget, QComboBox):
            idx = widget.findText(text)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            return
        if isinstance(widget, QTextEdit):
            widget.setPlainText(text)
            return
        if isinstance(widget, QLineEdit):
            widget.setText(text)


class HierarchyEditorPage(QWidget):
    def __init__(self, world_service: WorldService, hierarchy_service: HierarchyService) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(QLabel("Hierarchy Editor"))
        layout.addWidget(tabs)

        specs = (
            EntitySpec(
                key="continents",
                title="Continent",
                list_method="list_continents",
                get_method="get_continent",
                create_method="create_continent",
                update_method="update_continent",
                delete_method="delete_continent",
                fields=(("name", "Name"), ("climate_summary", "Climate Summary")),
            ),
            EntitySpec(
                key="empires",
                title="Empire",
                list_method="list_empires",
                get_method="get_empire",
                create_method="create_empire",
                update_method="update_empire",
                delete_method="delete_empire",
                fields=(
                    ("name", "Name"),
                    ("continent_ref", "Continent Ref"),
                    ("governing_style", "Governing Style"),
                ),
            ),
            EntitySpec(
                key="kingdoms",
                title="Kingdom",
                list_method="list_kingdoms",
                get_method="get_kingdom",
                create_method="create_kingdom",
                update_method="update_kingdom",
                delete_method="delete_kingdom",
                fields=(("name", "Name"), ("empire_ref", "Empire Ref"), ("stability_index", "Stability")),
            ),
            EntitySpec(
                key="regions",
                title="Region",
                list_method="list_regions",
                get_method="get_region",
                create_method="create_region",
                update_method="update_region",
                delete_method="delete_region",
                fields=(("name", "Name"), ("kingdom_ref", "Kingdom Ref"), ("biome", "Biome")),
            ),
            EntitySpec(
                key="settlements",
                title="Settlement",
                list_method="list_settlements",
                get_method="get_settlement",
                create_method="create_settlement",
                update_method="update_settlement",
                delete_method="delete_settlement",
                fields=(
                    ("name", "Name"),
                    ("region_ref", "Region Ref"),
                    ("kind", "Kind"),
                    ("population", "Population"),
                    ("resource_index", "Resource Index"),
                    ("safety_index", "Safety Index"),
                    ("x", "Map X"),
                    ("y", "Map Y"),
                ),
            ),
            EntitySpec(
                key="pois",
                title="Point of Interest",
                list_method="list_points_of_interest",
                get_method="get_point_of_interest",
                create_method="create_point_of_interest",
                update_method="update_point_of_interest",
                delete_method="delete_point_of_interest",
                fields=(
                    ("name", "Name"),
                    ("region_ref", "Region Ref"),
                    ("node_type", "Node Type"),
                    ("x", "Map X"),
                    ("y", "Map Y"),
                    ("description", "Description"),
                ),
            ),
            EntitySpec(
                key="routes",
                title="Route",
                list_method="list_routes",
                get_method="get_route",
                create_method="create_route",
                update_method="update_route",
                delete_method="delete_route",
                fields=(
                    ("name", "Name"),
                    ("source_ref", "Source Ref"),
                    ("target_ref", "Target Ref"),
                    ("route_type", "Route Type"),
                    ("travel_cost", "Travel Cost"),
                ),
            ),
        )

        for spec in specs:
            panel = EntityCrudPanel(world_service, hierarchy_service, spec)
            tabs.addTab(panel, spec.title)


class SimulationPage(QWidget):
    def __init__(self, world_service: WorldService, simulation_service: SimulationService) -> None:
        super().__init__()
        self._world_service = world_service
        self._simulation_service = simulation_service

        layout = QVBoxLayout(self)
        self._world_ref_input = QLineEdit()
        self._world_ref_input.setPlaceholderText("world ext_ref")
        run_button = QPushButton("Run 1 Month Preview")
        run_button.clicked.connect(self._run_preview)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        layout.addWidget(QLabel("Simulation"))
        layout.addWidget(self._world_ref_input)
        layout.addWidget(run_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._output)

    def _run_preview(self) -> None:
        world_ref = self._world_ref_input.text().strip()
        if not world_ref:
            worlds = self._world_service.list_worlds()
            if worlds:
                world_ref = worlds[0].ext_ref
                self._world_ref_input.setText(world_ref)
        if not world_ref:
            QMessageBox.warning(self, "Simulation", "Create a world first.")
            return
        try:
            run = self._simulation_service.simulate(
                SimulationRequest(
                    world_ref=world_ref,
                    step=SimulationStep.MONTH,
                    quantity=1,
                    preview_only=True,
                )
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Simulation", str(exc))
            return
        self._output.setPlainText(
            "\n".join(
                [
                    f"Preview run for world: {run.world_ref}",
                    f"Simulated days: {run.simulated_days}",
                    f"Pass notes: {len(run.notes)}",
                    "",
                    *run.notes,
                ]
            )
        )


class ImportExportPage(QWidget):
    def __init__(self, world_service: WorldService, import_export_service: ImportExportService) -> None:
        super().__init__()
        self._world_service = world_service
        self._import_export_service = import_export_service

        layout = QVBoxLayout(self)
        self._world_ref_input = QLineEdit()
        self._world_ref_input.setPlaceholderText("world ext_ref")
        self._output = QTextEdit()
        self._output.setReadOnly(True)

        export_json = QPushButton("Export World JSON")
        export_json.clicked.connect(self._export_json)
        export_pdf = QPushButton("Export World PDF")
        export_pdf.clicked.connect(self._export_pdf)

        button_row = QHBoxLayout()
        button_row.addWidget(export_json)
        button_row.addWidget(export_pdf)
        button_row.addStretch()

        layout.addWidget(QLabel("Import / Export"))
        layout.addWidget(self._world_ref_input)
        layout.addLayout(button_row)
        layout.addWidget(self._output)

    def _target_world_ref(self) -> str:
        world_ref = self._world_ref_input.text().strip()
        if world_ref:
            return world_ref
        worlds = self._world_service.list_worlds()
        if worlds:
            world_ref = worlds[0].ext_ref
            self._world_ref_input.setText(world_ref)
        return world_ref

    def _export_json(self) -> None:
        world_ref = self._target_world_ref()
        if not world_ref:
            QMessageBox.warning(self, "Export", "Create a world first.")
            return
        try:
            target = self._import_export_service.export_world_json(world_ref)
            self._output.setPlainText(f"Exported JSON:\n{target}")
        except ValueError as exc:
            QMessageBox.warning(self, "Export", str(exc))

    def _export_pdf(self) -> None:
        world_ref = self._target_world_ref()
        if not world_ref:
            QMessageBox.warning(self, "Export", "Create a world first.")
            return
        try:
            target = self._import_export_service.export_world_pdf(world_ref)
            self._output.setPlainText(f"Exported PDF:\n{target}")
        except ValueError as exc:
            QMessageBox.warning(self, "Export", str(exc))


class MapPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Node Map View"))
        placeholder = QLabel(
            "Graph rendering foundation is reserved for phase 6.\n"
            "This page is intentionally in place for stable navigation contracts."
        )
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)
        layout.addStretch()
