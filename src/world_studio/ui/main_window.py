from __future__ import annotations

from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QStatusBar,
)

from world_studio.bootstrap import ServiceContainer
from world_studio.ui.pages import (
    DashboardPage,
    HierarchyEditorPage,
    ImportExportPage,
    MapPage,
    SimulationPage,
    WorldBrowserPage,
)


class MainWindow(QMainWindow):
    def __init__(self, container: ServiceContainer) -> None:
        super().__init__()
        self.setWindowTitle("World Studio")
        self.resize(1400, 900)

        splitter = QSplitter()
        self._nav = QListWidget()
        self._stack = QStackedWidget()
        splitter.addWidget(self._nav)
        splitter.addWidget(self._stack)
        splitter.setSizes([250, 1150])
        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

        self._pages = {
            "Dashboard": DashboardPage(container.world_service),
            "World Browser": WorldBrowserPage(container.world_service),
            "Hierarchy Editor": HierarchyEditorPage(
                container.world_service, container.hierarchy_service
            ),
            "Simulation": SimulationPage(container.world_service, container.simulation_service),
            "Import/Export": ImportExportPage(container.world_service, container.import_export_service),
            "Map": MapPage(),
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
