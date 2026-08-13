"""Persist execution logs and screen capture metadata."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.db.database import Database
from src.db.repositories import ExecutionLogRepository, ScreenCaptureRepository


class AuditService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.logs = ExecutionLogRepository(db)
        self.captures = ScreenCaptureRepository(db)

    def log_execution(
        self,
        status: str,
        duration_ms: int,
        error_message: str = "",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        command_id: Optional[int] = None,
        capture_paths: Optional[List[str]] = None,
    ) -> int:
        log_id = self.logs.create(
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            details=details,
            user_id=user_id,
            workflow_id=workflow_id,
            command_id=command_id,
        )
        for path in capture_paths or []:
            self.captures.create(file_path=path, log_id=log_id, label=status)
        return log_id

    def recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.logs.recent(limit=limit)
