from __future__ import annotations

from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
)

from world_studio.bootstrap import ServiceContainer
from world_studio.ui.pages import (
    DashboardPage,
    GenerationPage,
    HierarchyEditorPage,
    ImportExportPage,
    MapPage,
    NpcRelationshipPage,
    SimulationPage,
    WorldBrowserPage,
)


class MainWindow(QMainWindow):
    def __init__(self, container: ServiceContainer) -> None:
        super().__init__()
        self.setWindowTitle("World Studio - Dungeon Master's Forge")
        self.resize(1400, 900)

        # Set D&D style stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f4e4bc;
                color: #2c1810;
            }
            QListWidget {
                background-color: #e8d5b7;
                border: 2px solid #8b4513;
                border-radius: 5px;
                font-family: "Times New Roman", serif;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #d2b48c;
            }
            QListWidget::item:selected {
                background-color: #daa520;
                color: #2c1810;
            }
            QComboBox {
                background-color: #e8d5b7;
                border: 2px solid #8b4513;
                border-radius: 5px;
                padding: 5px;
                font-family: "Times New Roman", serif;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c1810;
                margin-right: 5px;
            }
            QLabel {
                font-family: "Times New Roman", serif;
                font-size: 16px;
                color: #2c1810;
            }
            QPushButton {
                background-color: #daa520;
                border: 2px solid #8b4513;
                border-radius: 5px;
                padding: 5px 10px;
                font-family: "Times New Roman", serif;
                font-size: 14px;
                color: #2c1810;
            }
            QPushButton:hover {
                background-color: #ffd700;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #f5f5dc;
                border: 2px solid #8b4513;
                border-radius: 5px;
                font-family: "Times New Roman", serif;
                font-size: 14px;
            }
            QGroupBox {
                font-family: "Times New Roman", serif;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #8b4513;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 2px solid #8b4513;
                border-radius: 5px;
                background-color: #f4e4bc;
            }
            QTabBar::tab {
                background-color: #e8d5b7;
                border: 2px solid #8b4513;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
                padding: 5px 10px;
                font-family: "Times New Roman", serif;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #daa520;
                color: #2c1810;
            }
        """)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # World selector
        world_layout = QHBoxLayout()
        world_layout.addWidget(QLabel("Selected World:"))
        self._world_combo = QComboBox()
        self._world_combo.addItem("None", "")
        self._world_combo.currentIndexChanged.connect(self._on_world_changed)
        world_layout.addWidget(self._world_combo)
        world_layout.addStretch()
        main_layout.addLayout(world_layout)

        splitter = QSplitter()
        self._nav = QListWidget()
        self._stack = QStackedWidget()
        splitter.addWidget(self._nav)
        splitter.addWidget(self._stack)
        splitter.setSizes([250, 1150])
        main_layout.addWidget(splitter)

        self.setCentralWidget(central_widget)
        self.setStatusBar(QStatusBar())

        self._pages = {
            "Dashboard": DashboardPage(container.world_service),
            "World Browser": WorldBrowserPage(container.world_service, self._refresh_worlds),
            "Generation": GenerationPage(container.world_service, container.generation_service),
            "Hierarchy Editor": HierarchyEditorPage(
                container.world_service, container.hierarchy_service
            ),
            "NPCs & Relationships": NpcRelationshipPage(
                container.world_service, container.social_service
            ),
            "Simulation": SimulationPage(container.world_service, container.simulation_service),
            "Import/Export": ImportExportPage(container.world_service, container.import_export_service),
            "Map": MapPage(container.world_service, container.multi_scale_map_service),
        }

        for title, widget in self._pages.items():
            self._nav.addItem(QListWidgetItem(title))
            self._stack.addWidget(widget)

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)
        self.statusBar().showMessage(
            f"Database: {container.database.database_path}",
            10_000,
        )

        self._container = container
        self._refresh_worlds()

    def _refresh_worlds(self) -> None:
        self._world_combo.clear()
        self._world_combo.addItem("Select a World", "")
        worlds = self._container.world_service.list_worlds()
        for world in worlds:
            self._world_combo.addItem(f"{world.name}", world.ext_ref)

    def _on_world_changed(self) -> None:
        selected_ref = self._world_combo.currentData()
        # Update pages that need the selected world
        for page in [self._pages["Generation"], self._pages["Hierarchy Editor"], 
                     self._pages["NPCs & Relationships"], self._pages["Simulation"], 
                     self._pages["Import/Export"], self._pages["Map"]]:
            if hasattr(page, 'set_world'):
                page.set_world(selected_ref)
