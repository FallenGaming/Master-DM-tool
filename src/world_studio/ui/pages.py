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
    GenerationAppService,
    HierarchyService,
    ImportExportService,
    SocialService,
    SimulationService,
    WorldService,
)
from world_studio.domain.enums import NodeType, RelationshipType, SettlementType, SimulationStep
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


class NpcRelationshipPage(QWidget):
    def __init__(self, world_service: WorldService, social_service: SocialService) -> None:
        super().__init__()
        self._world_service = world_service
        self._social_service = social_service
        self._selected_npc_ref: str | None = None
        self._selected_relationship_ref: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("NPC & Relationship Manager"))

        world_row = QHBoxLayout()
        self._world_ref_input = QLineEdit()
        self._world_ref_input.setPlaceholderText("world ext_ref")
        load_button = QPushButton("Load World")
        load_button.clicked.connect(self.refresh)
        world_row.addWidget(QLabel("World Ref"))
        world_row.addWidget(self._world_ref_input)
        world_row.addWidget(load_button)
        layout.addLayout(world_row)

        split_row = QHBoxLayout()
        split_row.addWidget(self._build_npc_panel(), stretch=1)
        split_row.addWidget(self._build_relationship_panel(), stretch=1)
        layout.addLayout(split_row)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        layout.addStretch()

    def _build_npc_panel(self) -> QWidget:
        panel = QGroupBox("NPC Editor")
        root = QVBoxLayout(panel)
        self._npc_list = QListWidget()
        self._npc_list.currentTextChanged.connect(self._on_select_npc)
        root.addWidget(self._npc_list)

        form = QFormLayout()
        self._npc_display_name = QLineEdit()
        self._npc_age_years = QLineEdit()
        self._npc_race_ref = QLineEdit()
        self._npc_subrace_ref = QLineEdit()
        self._npc_occupation_ref = QLineEdit()
        self._npc_residence_node_ref = QLineEdit()
        self._npc_health_index = QLineEdit()
        self._npc_wealth_index = QLineEdit()
        self._npc_notes = QTextEdit()
        self._npc_notes.setFixedHeight(70)
        self._npc_is_locked = QCheckBox("Locked")
        form.addRow("Name", self._npc_display_name)
        form.addRow("Age", self._npc_age_years)
        form.addRow("Race Ref", self._npc_race_ref)
        form.addRow("Subrace Ref", self._npc_subrace_ref)
        form.addRow("Occupation Ref", self._npc_occupation_ref)
        form.addRow("Residence Ref", self._npc_residence_node_ref)
        form.addRow("Health Index", self._npc_health_index)
        form.addRow("Wealth Index", self._npc_wealth_index)
        form.addRow("Notes", self._npc_notes)
        form.addRow("", self._npc_is_locked)
        root.addLayout(form)

        buttons = QHBoxLayout()
        create_button = QPushButton("Create")
        save_button = QPushButton("Save")
        save_force_button = QPushButton("Save (Force Override)")
        delete_button = QPushButton("Delete")
        delete_force_button = QPushButton("Delete (Force)")
        clear_button = QPushButton("Clear")
        create_button.clicked.connect(self._create_npc)
        save_button.clicked.connect(lambda: self._save_npc(force=False))
        save_force_button.clicked.connect(lambda: self._save_npc(force=True))
        delete_button.clicked.connect(lambda: self._delete_npc(force=False))
        delete_force_button.clicked.connect(lambda: self._delete_npc(force=True))
        clear_button.clicked.connect(self._clear_npc_form)
        buttons.addWidget(create_button)
        buttons.addWidget(save_button)
        buttons.addWidget(save_force_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(delete_force_button)
        buttons.addWidget(clear_button)
        root.addLayout(buttons)
        return panel

    def _build_relationship_panel(self) -> QWidget:
        panel = QGroupBox("Relationship Editor")
        root = QVBoxLayout(panel)
        self._relationship_list = QListWidget()
        self._relationship_list.currentTextChanged.connect(self._on_select_relationship)
        root.addWidget(self._relationship_list)

        form = QFormLayout()
        self._rel_source_ref = QLineEdit()
        self._rel_target_ref = QLineEdit()
        self._rel_type = QComboBox()
        self._rel_type.addItems([value.value for value in RelationshipType])
        self._rel_weight = QLineEdit()
        self._rel_history = QTextEdit()
        self._rel_history.setFixedHeight(70)
        self._rel_is_locked = QCheckBox("Locked")
        form.addRow("Source NPC Ref", self._rel_source_ref)
        form.addRow("Target NPC Ref", self._rel_target_ref)
        form.addRow("Relation Type", self._rel_type)
        form.addRow("Weight", self._rel_weight)
        form.addRow("History (line-separated)", self._rel_history)
        form.addRow("", self._rel_is_locked)
        root.addLayout(form)

        buttons = QHBoxLayout()
        create_button = QPushButton("Create")
        save_button = QPushButton("Save")
        save_force_button = QPushButton("Save (Force Override)")
        delete_button = QPushButton("Delete")
        delete_force_button = QPushButton("Delete (Force)")
        clear_button = QPushButton("Clear")
        create_button.clicked.connect(self._create_relationship)
        save_button.clicked.connect(lambda: self._save_relationship(force=False))
        save_force_button.clicked.connect(lambda: self._save_relationship(force=True))
        delete_button.clicked.connect(lambda: self._delete_relationship(force=False))
        delete_force_button.clicked.connect(lambda: self._delete_relationship(force=True))
        clear_button.clicked.connect(self._clear_relationship_form)
        buttons.addWidget(create_button)
        buttons.addWidget(save_button)
        buttons.addWidget(save_force_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(delete_force_button)
        buttons.addWidget(clear_button)
        root.addLayout(buttons)
        return panel

    def refresh(self) -> None:
        world_ref = self._resolve_world_ref()
        self._npc_list.clear()
        self._relationship_list.clear()
        self._selected_npc_ref = None
        self._selected_relationship_ref = None
        if not world_ref:
            self._set_status("Create or select a world first.")
            return

        npcs = self._social_service.list_npcs(world_ref)
        relationships = self._social_service.list_relationships(world_ref)
        for npc in npcs:
            lock_marker = " [locked]" if npc.is_locked else ""
            self._npc_list.addItem(f"{npc.display_name}{lock_marker} ({npc.ext_ref})")
        for rel in relationships:
            lock_marker = " [locked]" if rel.is_locked else ""
            label = (
                f"{rel.relation_type.value}: {rel.source_npc_ref[:8]} -> {rel.target_npc_ref[:8]}"
                f"{lock_marker} ({rel.ext_ref})"
            )
            self._relationship_list.addItem(label)

        self._set_status(
            f"Loaded {len(npcs)} NPC(s) and {len(relationships)} relationship(s) for world {world_ref}."
        )

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

    def _create_npc(self) -> None:
        world_ref = self._resolve_world_ref()
        if not world_ref:
            self._set_status("Cannot create NPC without a world.")
            return
        try:
            self._social_service.create_npc(world_ref, self._npc_payload())
        except (ValueError, TypeError) as exc:
            self._set_status(f"NPC create failed: {exc}")
            return
        self.refresh()
        self._clear_npc_form()

    def _save_npc(self, *, force: bool) -> None:
        if not self._selected_npc_ref:
            self._set_status("Select an NPC first.")
            return
        try:
            self._social_service.update_npc(self._selected_npc_ref, self._npc_payload(), force=force)
        except (ValueError, TypeError) as exc:
            self._set_status(f"NPC save failed: {exc}")
            return
        self.refresh()
        self._set_status("NPC saved.")

    def _delete_npc(self, *, force: bool) -> None:
        if not self._selected_npc_ref:
            self._set_status("Select an NPC first.")
            return
        try:
            self._social_service.delete_npc(self._selected_npc_ref, force=force)
        except ValueError as exc:
            self._set_status(f"NPC delete failed: {exc}")
            return
        self.refresh()
        self._clear_npc_form()
        self._set_status("NPC deleted.")

    def _on_select_npc(self, value: str) -> None:
        if not value:
            self._selected_npc_ref = None
            return
        ext_ref = value[value.rfind("(") + 1 : -1]
        npc = self._social_service.get_npc(ext_ref)
        if npc is None:
            self._selected_npc_ref = None
            return
        self._selected_npc_ref = npc.ext_ref
        self._npc_display_name.setText(npc.display_name)
        self._npc_age_years.setText(str(npc.age_years))
        self._npc_race_ref.setText(npc.race_ref)
        self._npc_subrace_ref.setText(npc.subrace_ref or "")
        self._npc_occupation_ref.setText(npc.occupation_ref or "")
        self._npc_residence_node_ref.setText(npc.residence_node_ref or "")
        self._npc_health_index.setText(str(npc.health_index))
        self._npc_wealth_index.setText(str(npc.wealth_index))
        self._npc_notes.setPlainText(npc.notes)
        self._npc_is_locked.setChecked(npc.is_locked)

    def _npc_payload(self) -> dict[str, object]:
        return {
            "display_name": self._npc_display_name.text().strip(),
            "age_years": self._npc_age_years.text().strip(),
            "race_ref": self._npc_race_ref.text().strip(),
            "subrace_ref": self._npc_subrace_ref.text().strip(),
            "occupation_ref": self._npc_occupation_ref.text().strip(),
            "residence_node_ref": self._npc_residence_node_ref.text().strip(),
            "health_index": self._npc_health_index.text().strip(),
            "wealth_index": self._npc_wealth_index.text().strip(),
            "notes": self._npc_notes.toPlainText().strip(),
            "is_locked": self._npc_is_locked.isChecked(),
        }

    def _clear_npc_form(self) -> None:
        self._selected_npc_ref = None
        self._npc_display_name.clear()
        self._npc_age_years.clear()
        self._npc_race_ref.clear()
        self._npc_subrace_ref.clear()
        self._npc_occupation_ref.clear()
        self._npc_residence_node_ref.clear()
        self._npc_health_index.clear()
        self._npc_wealth_index.clear()
        self._npc_notes.clear()
        self._npc_is_locked.setChecked(False)

    def _create_relationship(self) -> None:
        world_ref = self._resolve_world_ref()
        if not world_ref:
            self._set_status("Cannot create relationship without a world.")
            return
        try:
            self._social_service.create_relationship(world_ref, self._relationship_payload())
        except (ValueError, TypeError) as exc:
            self._set_status(f"Relationship create failed: {exc}")
            return
        self.refresh()
        self._clear_relationship_form()

    def _save_relationship(self, *, force: bool) -> None:
        if not self._selected_relationship_ref:
            self._set_status("Select a relationship first.")
            return
        try:
            self._social_service.update_relationship(
                self._selected_relationship_ref, self._relationship_payload(), force=force
            )
        except (ValueError, TypeError) as exc:
            self._set_status(f"Relationship save failed: {exc}")
            return
        self.refresh()
        self._set_status("Relationship saved.")

    def _delete_relationship(self, *, force: bool) -> None:
        if not self._selected_relationship_ref:
            self._set_status("Select a relationship first.")
            return
        try:
            self._social_service.delete_relationship(self._selected_relationship_ref, force=force)
        except ValueError as exc:
            self._set_status(f"Relationship delete failed: {exc}")
            return
        self.refresh()
        self._clear_relationship_form()
        self._set_status("Relationship deleted.")

    def _on_select_relationship(self, value: str) -> None:
        if not value:
            self._selected_relationship_ref = None
            return
        ext_ref = value[value.rfind("(") + 1 : -1]
        relationship = self._social_service.get_relationship(ext_ref)
        if relationship is None:
            self._selected_relationship_ref = None
            return
        self._selected_relationship_ref = relationship.ext_ref
        self._rel_source_ref.setText(relationship.source_npc_ref)
        self._rel_target_ref.setText(relationship.target_npc_ref)
        idx = self._rel_type.findText(relationship.relation_type.value)
        if idx >= 0:
            self._rel_type.setCurrentIndex(idx)
        self._rel_weight.setText(str(relationship.weight))
        self._rel_history.setPlainText("\n".join(relationship.history))
        self._rel_is_locked.setChecked(relationship.is_locked)

    def _relationship_payload(self) -> dict[str, object]:
        return {
            "source_npc_ref": self._rel_source_ref.text().strip(),
            "target_npc_ref": self._rel_target_ref.text().strip(),
            "relation_type": self._rel_type.currentText(),
            "weight": self._rel_weight.text().strip(),
            "history": self._rel_history.toPlainText(),
            "is_locked": self._rel_is_locked.isChecked(),
        }

    def _clear_relationship_form(self) -> None:
        self._selected_relationship_ref = None
        self._rel_source_ref.clear()
        self._rel_target_ref.clear()
        self._rel_weight.clear()
        self._rel_history.clear()
        self._rel_is_locked.setChecked(False)
        self._rel_type.setCurrentIndex(0)

    def _set_status(self, message: str) -> None:
        self._status.setText(message)


class GenerationPage(QWidget):
    def __init__(
        self,
        world_service: WorldService,
        generation_service: GenerationAppService,
    ) -> None:
        super().__init__()
        self._world_service = world_service
        self._generation_service = generation_service

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("World Auto-Population & Generation"))

        world_row = QHBoxLayout()
        self._world_ref_input = QLineEdit()
        self._world_ref_input.setPlaceholderText("world ext_ref")
        world_row.addWidget(QLabel("World Ref"))
        world_row.addWidget(self._world_ref_input)
        layout.addLayout(world_row)

        settings = QGroupBox("Generation Settings")
        settings_form = QFormLayout(settings)
        self._seed = QLineEdit()
        self._seed.setPlaceholderText("optional integer seed")
        self._continents = QLineEdit("2")
        self._empires = QLineEdit("2")
        self._kingdoms = QLineEdit("5")
        self._regions = QLineEdit("10")
        self._settlement_density = QLineEdit("0.7")
        self._target_population = QLineEdit("1200")
        self._npcs_per_100 = QLineEdit("2.0")
        self._relationship_density = QLineEdit("0.08")
        self._min_settlements_region = QLineEdit("1")
        self._max_settlements_region = QLineEdit("4")
        self._race_mode = QComboBox()
        self._race_mode.addItems(["hardcoded_only", "custom_only", "mixed"])
        self._size_tendency = QComboBox()
        self._size_tendency.addItems(["hamlet", "village", "town", "city", "mixed"])
        self._occupation_variance = QLineEdit("0.2")
        self._auto_seed_catalogs = QCheckBox("Auto-seed default races and occupations")
        self._auto_seed_catalogs.setChecked(True)

        settings_form.addRow("Seed", self._seed)
        settings_form.addRow("Continents", self._continents)
        settings_form.addRow("Empires", self._empires)
        settings_form.addRow("Kingdoms", self._kingdoms)
        settings_form.addRow("Regions", self._regions)
        settings_form.addRow("Settlement Density", self._settlement_density)
        settings_form.addRow("Target Settlement Population", self._target_population)
        settings_form.addRow("NPCs per 100 population", self._npcs_per_100)
        settings_form.addRow("Relationship Density", self._relationship_density)
        settings_form.addRow("Min Settlements/Region", self._min_settlements_region)
        settings_form.addRow("Max Settlements/Region", self._max_settlements_region)
        settings_form.addRow("Race Usage Mode", self._race_mode)
        settings_form.addRow("Settlement Size Tendency", self._size_tendency)
        settings_form.addRow("Occupation Variance", self._occupation_variance)
        settings_form.addRow("", self._auto_seed_catalogs)

        layout.addWidget(settings)

        run_row = QHBoxLayout()
        run_button = QPushButton("Generate Initial World State")
        run_button.clicked.connect(self._run_generation)
        run_row.addWidget(run_button)
        run_row.addStretch()
        layout.addLayout(run_row)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
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

    def _run_generation(self) -> None:
        world_ref = self._target_world_ref()
        if not world_ref:
            QMessageBox.warning(self, "Generation", "Create a world first.")
            return
        try:
            result = self._generation_service.generate_initial_state(
                world_ref,
                {
                    "seed": self._optional_int(self._seed.text()),
                    "continent_count": self._required_int(self._continents.text(), "Continents"),
                    "empire_count": self._required_int(self._empires.text(), "Empires"),
                    "kingdom_count": self._required_int(self._kingdoms.text(), "Kingdoms"),
                    "region_count": self._required_int(self._regions.text(), "Regions"),
                    "settlement_density": self._required_float(
                        self._settlement_density.text(), "Settlement Density"
                    ),
                    "target_settlement_population": self._required_int(
                        self._target_population.text(), "Target Settlement Population"
                    ),
                    "npc_per_100_population": self._required_float(
                        self._npcs_per_100.text(), "NPCs per 100 population"
                    ),
                    "relationship_density": self._required_float(
                        self._relationship_density.text(), "Relationship Density"
                    ),
                    "min_settlements_per_region": self._required_int(
                        self._min_settlements_region.text(), "Min Settlements/Region"
                    ),
                    "max_settlements_per_region": self._required_int(
                        self._max_settlements_region.text(), "Max Settlements/Region"
                    ),
                    "race_mode": self._race_mode.currentText(),
                    "settlement_size_tendency": self._size_tendency.currentText(),
                    "occupation_variance": self._required_float(
                        self._occupation_variance.text(), "Occupation Variance"
                    ),
                    "auto_seed_catalogs": self._auto_seed_catalogs.isChecked(),
                },
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Generation", str(exc))
            return

        counts = "\n".join(f"- {k}: {v}" for k, v in sorted(result.counts.items()))
        notes = "\n".join(f"- {n}" for n in result.notes) if result.notes else "- none"
        self._output.setPlainText(
            "\n".join(
                [
                    f"Generation complete for world: {result.world_ref}",
                    f"Seed used: {result.seed_used}",
                    "",
                    "Created records:",
                    counts,
                    "",
                    "Generation notes:",
                    notes,
                ]
            )
        )

    @staticmethod
    def _required_int(raw: str, label: str) -> int:
        text = raw.strip()
        if not text:
            raise ValueError(f"{label} is required.")
        return int(text)

    @staticmethod
    def _required_float(raw: str, label: str) -> float:
        text = raw.strip()
        if not text:
            raise ValueError(f"{label} is required.")
        return float(text)

    @staticmethod
    def _optional_int(raw: str) -> int | None:
        text = raw.strip()
        if not text:
            return None
        return int(text)


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
