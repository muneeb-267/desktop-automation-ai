"""CRUD helpers for the eight SDS tables."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.db.database import Database, hash_password


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone(
            "SELECT * FROM User WHERE username = ? AND password_hash = ?",
            (username, hash_password(password)),
        )
        return dict(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM User WHERE user_id = ?", (user_id,))
        return dict(row) if row else None


class UserConfRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM User_Conf WHERE user_id = ?", (user_id,))
        return dict(row) if row else None

    def update(
        self,
        user_id: int,
        *,
        theme: Optional[str] = None,
        mic_sensitivity: Optional[float] = None,
        dry_run: Optional[bool] = None,
        failsafe: Optional[bool] = None,
        pause_seconds: Optional[float] = None,
    ) -> None:
        current = self.get_for_user(user_id)
        if not current:
            return
        self.db.execute(
            """
            UPDATE User_Conf
            SET theme = ?, mic_sensitivity = ?, dry_run = ?, failsafe = ?, pause_seconds = ?
            WHERE user_id = ?
            """,
            (
                theme if theme is not None else current["theme"],
                mic_sensitivity if mic_sensitivity is not None else current["mic_sensitivity"],
                int(dry_run) if dry_run is not None else current["dry_run"],
                int(failsafe) if failsafe is not None else current["failsafe"],
                pause_seconds if pause_seconds is not None else current["pause_seconds"],
                user_id,
            ),
        )


class WorkflowRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM Workflow WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]

    def get(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM Workflow WHERE workflow_id = ?", (workflow_id,))
        return dict(row) if row else None

    def create(self, user_id: int, name: str, description: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO Workflow (user_id, name, description) VALUES (?, ?, ?)",
            (user_id, name, description),
        )
        return int(cur.lastrowid)

    def rename(self, workflow_id: int, name: str) -> None:
        self.db.execute(
            "UPDATE Workflow SET name = ?, updated_at = datetime('now') WHERE workflow_id = ?",
            (name, workflow_id),
        )

    def delete(self, workflow_id: int) -> None:
        self.db.execute("DELETE FROM Workflow WHERE workflow_id = ?", (workflow_id,))

    def touch(self, workflow_id: int) -> None:
        self.db.execute(
            "UPDATE Workflow SET updated_at = datetime('now') WHERE workflow_id = ?",
            (workflow_id,),
        )


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_for_workflow(self, workflow_id: int) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM Task WHERE workflow_id = ? ORDER BY step_order ASC",
            (workflow_id,),
        )
        return [dict(r) for r in rows]

    def replace_tasks(self, workflow_id: int, tasks: List[Dict[str, Any]]) -> None:
        self.db.execute("DELETE FROM Task WHERE workflow_id = ?", (workflow_id,))
        for idx, task in enumerate(tasks, start=1):
            params = task.get("params") or task.get("params_json") or {}
            if isinstance(params, dict):
                params_json = json.dumps(params)
            else:
                params_json = str(params)
            self.db.execute(
                """
                INSERT INTO Task (
                    workflow_id, step_order, intent, target_app,
                    target_element, input_value, params_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    idx,
                    task.get("intent", "wait"),
                    task.get("target_app", ""),
                    task.get("target_element", ""),
                    task.get("input_value", ""),
                    params_json,
                ),
            )


class AutomationRuleRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_for_workflow(self, workflow_id: int) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT * FROM AutomationRule
            WHERE workflow_id = ?
            ORDER BY priority ASC
            """,
            (workflow_id,),
        )
        return [dict(r) for r in rows]

    def add(
        self,
        workflow_id: int,
        name: str,
        condition: Dict[str, Any] | None = None,
        priority: int = 100,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO AutomationRule (workflow_id, name, condition_json, priority)
            VALUES (?, ?, ?, ?)
            """,
            (workflow_id, name, json.dumps(condition or {}), priority),
        )
        return int(cur.lastrowid)


class NLPCommandRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        raw_text: str,
        intent: str,
        entities: Dict[str, Any],
        confidence: float,
        source: str = "text",
        user_id: Optional[int] = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO NLP_Command (
                user_id, raw_text, intent, entities_json, confidence, source
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, raw_text, intent, json.dumps(entities), confidence, source),
        )
        return int(cur.lastrowid)

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM NLP_Command ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]


class ExecutionLogRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        status: str,
        duration_ms: int,
        error_message: str = "",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        command_id: Optional[int] = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO Execution_log (
                user_id, workflow_id, command_id, status,
                duration_ms, error_message, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                workflow_id,
                command_id,
                status,
                duration_ms,
                error_message,
                json.dumps(details or {}),
            ),
        )
        return int(cur.lastrowid)

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM Execution_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]


class ScreenCaptureRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, file_path: str, log_id: Optional[int] = None, label: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO Screen_capture (log_id, file_path, label) VALUES (?, ?, ?)",
            (log_id, file_path, label),
        )
        return int(cur.lastrowid)

    def list_for_log(self, log_id: int) -> List[Dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM Screen_capture WHERE log_id = ? ORDER BY created_at DESC",
            (log_id,),
        )
        return [dict(r) for r in rows]
