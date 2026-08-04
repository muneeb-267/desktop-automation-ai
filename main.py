#!/usr/bin/env python3
"""Application entry point for AI Desktop Automation Suite."""

import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.gui.main_window import MainWindow


def main() -> int:
    # High-DPI support before QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AI Desktop Automation Suite")
    app.setOrganizationName("DesktopAutomationAI")

    window = MainWindow()
    window.show()

    exit_code = app.exec_()
    window.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
