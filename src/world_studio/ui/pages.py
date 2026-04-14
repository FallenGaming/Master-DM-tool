from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from world_studio.application.services import ImportExportService, SimulationService, WorldService
from world_studio.domain.enums import SimulationStep
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
