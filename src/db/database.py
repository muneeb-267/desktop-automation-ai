"""SQLite connection helpers and schema bootstrap."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import ROOT_DIR, ensure_runtime_dirs, load_config, resolve_path

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_db_singleton: Optional["Database"] = None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self._conn.execute(sql, params).fetchall())

    def close(self) -> None:
        self._conn.close()

    def initialize_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._conn.commit()

    def seed_defaults(self, config: Dict[str, Any]) -> None:
        auth = config.get("auth", {})
        username = auth.get("default_username", "demo")
        password = auth.get("default_password", "demo123")
        display = auth.get("default_display_name", "Demo User")
        existing = self.fetchone("SELECT user_id FROM User WHERE username = ?", (username,))
        if existing:
            return
        cur = self.execute(
            "INSERT INTO User (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username, hash_password(password), display),
        )
        user_id = cur.lastrowid
        ui = config.get("ui", {})
        speech = config.get("speech", {})
        auto = config.get("automation", {})
        self.execute(
            """
            INSERT INTO User_Conf (
                user_id, theme, mic_sensitivity, dry_run, failsafe, pause_seconds
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                ui.get("theme", "light"),
                float(speech.get("mic_sensitivity", 0.7)),
                1 if auto.get("dry_run", True) else 0,
                1 if auto.get("failsafe", True) else 0,
                float(auto.get("pause_seconds", 0.35)),
            ),
        )
        # Sample workflow for demos
        self.execute(
            """
            INSERT INTO Workflow (user_id, name, description)
            VALUES (?, ?, ?)
            """,
            (user_id, "Open Notepad Demo", "Sample multi-step workflow"),
        )
        wf = self.fetchone(
            "SELECT workflow_id FROM Workflow WHERE user_id = ? AND name = ?",
            (user_id, "Open Notepad Demo"),
        )
        if wf:
            wid = wf["workflow_id"]
            self.execute(
                """
                INSERT INTO AutomationRule (workflow_id, name, condition_json, priority)
                VALUES (?, ?, ?, ?)
                """,
                (wid, "Always run", '{"when":"manual"}', 10),
            )
            steps = [
                (1, "open_app", "notepad", "", "", "{}"),
                (2, "wait", "", "", "1", '{"seconds":1}'),
                (3, "type_text", "notepad", "", "Hello from Desktop Automation AI", "{}"),
            ]
            for order, intent, app, element, value, params in steps:
                self.execute(
                    """
                    INSERT INTO Task (
                        workflow_id, step_order, intent, target_app,
                        target_element, input_value, params_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (wid, order, intent, app, element, value, params),
                )


def get_database(config: Optional[Dict[str, Any]] = None) -> Database:
    global _db_singleton
    if _db_singleton is not None:
        return _db_singleton
    cfg = config or load_config()
    ensure_runtime_dirs(cfg)
    db_path = resolve_path(cfg["paths"]["db_file"])
    db = Database(db_path)
    db.initialize_schema()
    db.seed_defaults(cfg)
    _db_singleton = db
    return db


def reset_database_singleton() -> None:
    global _db_singleton
    if _db_singleton is not None:
        _db_singleton.close()
    _db_singleton = None
