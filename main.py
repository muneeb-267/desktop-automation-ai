#!/usr/bin/env python3
"""Application entry point for Automate AI / AI Desktop Automation."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QApplication

from src.config import ensure_runtime_dirs, load_config
from src.db.database import get_database
from src.db.repositories import UserConfRepository, UserRepository
from src.gui.login_dialog import LoginDialog
from src.gui.main_window import MainWindow
from src.gui.styles import APP_STYLE
from src.pipeline import AutomationPipeline
from src.speech.recognizer import SpeechService
from src.workflows.service import WorkflowService


def build_context(user: dict):
    config = load_config()
    ensure_runtime_dirs(config)
    db = get_database(config)
    pipeline = AutomationPipeline(config, db)
    pipeline.apply_user_settings(user["user_id"])
    return {
        "config": config,
        "db": db,
        "pipeline": pipeline,
        "speech": SpeechService(config),
        "workflows": WorkflowService(db),
        "user": user,
    }


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    config = load_config()
    ensure_runtime_dirs(config)
    db = get_database(config)

    app = QApplication(sys.argv)
    app_name = config.get("app", {}).get("name", "Automate AI")
    product = config.get("app", {}).get("product_name", "AI Desktop Automation")
    app.setApplicationName(app_name)
    app.setOrganizationName("S26CS089")
    app.setStyleSheet(APP_STYLE)

    login = LoginDialog(
        UserRepository(db),
        conf_repo=UserConfRepository(db),
        app_name=app_name,
        product_name=product,
    )
    if login.exec_() != login.Accepted or not login.user:
        return 0

    ctx = build_context(login.user)
    window = MainWindow(ctx)
    window.show()
    window.setWindowOpacity(0.0)
    anim = QPropertyAnimation(window, b"windowOpacity")
    anim.setDuration(260)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()
    window._open_anim = anim  # type: ignore[attr-defined]

    code = app.exec_()
    window.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
