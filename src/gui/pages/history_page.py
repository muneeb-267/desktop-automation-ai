"""Execution History screen."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
)


class HistoryPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)

        title = QLabel("Execution History")
        title.setObjectName("pageTitle")
        sub = QLabel("Review run details, durations, and error messages from local logs.")
        sub.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(sub)

        card = QFrame()
        card.setObjectName("panelCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Log ID", "Status", "Duration (ms)", "Action", "Started", "Error"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        cl.addWidget(self.table)
        root.addWidget(card, 1)

        self.detail = QLabel("Select a row to inspect details.")
        self.detail.setObjectName("pageSubtitle")
        self.detail.setWordWrap(True)
        root.addWidget(self.detail)
        self.table.itemSelectionChanged.connect(self._on_select)
        self._rows: List[Dict[str, Any]] = []

    def update_logs(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows
        self.table.setRowCount(0)
        for item in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            vals = [
                str(item.get("log_id", "")),
                str(item.get("status", "")),
                str(item.get("duration_ms", 0)),
                str(item.get("action_id", "")),
                str(item.get("started_at", "")),
                str(item.get("error_message", "") or "—"),
            ]
            for c, val in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(val))

    def _on_select(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < 0 or idx >= len(self._rows):
            return
        item = self._rows[idx]
        details = item.get("details_json") or {}
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}
        self.detail.setText(
            f"Status: {item.get('status')} | Duration: {item.get('duration_ms')} ms\n"
            f"Details: {json.dumps(details)[:500]}"
        )
