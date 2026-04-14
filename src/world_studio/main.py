from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from world_studio.bootstrap import build_container
from world_studio.data.migrations import run_migrations
from world_studio.ui.main_window import MainWindow


def main() -> int:
    container = build_container()
    run_migrations(container.database)

    app = QApplication(sys.argv)
    window = MainWindow(container)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
