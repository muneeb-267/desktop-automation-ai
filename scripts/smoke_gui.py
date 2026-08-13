#!/usr/bin/env python3
"""Non-interactive GUI smoke test: login bypass + short dashboard run."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from src.config import ensure_runtime_dirs, load_config
from src.db.database import get_database
from src.db.repositories import UserRepository
from src.gui.main_window import MainWindow
from src.gui.styles import LIGHT_THEME
from main import build_context


def main() -> int:
    config = load_config()
    ensure_runtime_dirs(config)
    db = get_database(config)
    user = UserRepository(db).authenticate("demo", "demo123")
    if not user:
        print("FAIL: demo user missing")
        return 1

    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_THEME)
    ctx = build_context(user)
    window = MainWindow(ctx)
    window.show()

    # Exercise a dry-run command shortly after show
    def run_cmd() -> None:
        window.controls.set_command_text("Open notepad and type hello")
        window._run_command("Open notepad and type hello")

    def finish() -> None:
        out = Path("/tmp/cursor/artifacts/screenshots")
        out.mkdir(parents=True, exist_ok=True)
        path = out / "desktop_automation_dashboard.png"
        pix = window.grab()
        pix.save(str(path))
        print(f"SMOKE_OK screenshot={path}")
        window.shutdown()
        app.quit()

    QTimer.singleShot(400, run_cmd)
    QTimer.singleShot(3500, finish)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
