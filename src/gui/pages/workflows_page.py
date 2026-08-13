"""Workflow Management screen."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QScrollArea,
    QLineEdit,
    QMessageBox,
    QInputDialog,
)


class WorkflowsPage(QWidget):
    run_requested = pyqtSignal(int)
    create_requested = pyqtSignal(str, str)
    delete_requested = pyqtSignal(int)
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._workflows: List[Dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        t = QLabel("WORKFLOW MANAGEMENT")
        t.setObjectName("pageTitle")
        s = QLabel("Organize and trigger your automated desktop routines.")
        s.setObjectName("pageSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        head.addLayout(titles)
        head.addStretch()
        create = QPushButton("+ Create Workflow")
        create.clicked.connect(self._create)
        head.addWidget(create)
        root.addLayout(head)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.s_total = self._stat("Total Workflows", "0")
        self.s_voice = self._stat("Voice Shortcuts", "0")
        self.s_steps = self._stat("Average Steps", "0")
        self.s_today = self._stat("Executions Today", "0")
        for w in (self.s_total, self.s_voice, self.s_steps, self.s_today):
            stats.addWidget(w)
        root.addLayout(stats)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setSpacing(12)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        logs_card = QFrame()
        logs_card.setObjectName("panelCard")
        ll = QVBoxLayout(logs_card)
        ll.setContentsMargins(16, 12, 16, 12)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("Live Execution Logs"))
        lh.addStretch()
        refresh = QPushButton("Refresh")
        refresh.setObjectName("btnGhost")
        refresh.clicked.connect(self.refresh_requested.emit)
        lh.addWidget(refresh)
        ll.addLayout(lh)
        self.live_logs = QLabel("No recent workflow runs yet.")
        self.live_logs.setObjectName("pageSubtitle")
        self.live_logs.setWordWrap(True)
        ll.addWidget(self.live_logs)
        root.addWidget(logs_card)

        foot = QLabel("© 2026 AI Desktop Automation • Wireframe v1.0")
        foot.setObjectName("footerLabel")
        root.addWidget(foot)

    def _stat(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        v = QLabel(value)
        v.setObjectName("metricValue")
        l = QLabel(label)
        l.setObjectName("metricLabel")
        lay.addWidget(l)
        lay.addWidget(v)
        card.value_label = v  # type: ignore[attr-defined]
        return card

    def set_workflows(
        self,
        workflows: List[Dict[str, Any]],
        *,
        today_executions: int = 0,
        avg_steps: float = 0.0,
    ) -> None:
        self._workflows = workflows
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        voice_count = sum(1 for w in workflows if str(w.get("trigger_type", "")).lower() == "voice")
        self.s_total.value_label.setText(str(len(workflows)))  # type: ignore[attr-defined]
        self.s_voice.value_label.setText(str(voice_count))  # type: ignore[attr-defined]
        self.s_steps.value_label.setText(f"{avg_steps:.1f}")  # type: ignore[attr-defined]
        self.s_today.value_label.setText(str(today_executions))  # type: ignore[attr-defined]

        for idx, wf in enumerate(workflows):
            card = self._workflow_card(wf)
            self.grid.addWidget(card, idx // 3, idx % 3)

        add = QFrame()
        add.setObjectName("workflowCard")
        add.setStyleSheet("#workflowCard{border:2px dashed #d1d5db;}")
        al = QVBoxLayout(add)
        al.setContentsMargins(16, 20, 16, 20)
        plus = QLabel("+")
        plus.setAlignment(Qt.AlignCenter)
        plus.setStyleSheet("font-size:28px;font-weight:800;color:#9ca3af;")
        desc = QLabel("Design a custom automation chain for your desktop apps.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setObjectName("pageSubtitle")
        btn = QPushButton("Add New Module")
        btn.setObjectName("btnSecondary")
        btn.clicked.connect(self._create)
        al.addWidget(plus)
        al.addWidget(desc)
        al.addWidget(btn)
        self.grid.addWidget(add, len(workflows) // 3, len(workflows) % 3)

    def _workflow_card(self, wf: Dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("workflowCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        icon = QLabel("⧉")
        icon.setStyleSheet("font-size:20px;")
        title = QLabel(wf.get("name", "Workflow"))
        title.setStyleSheet("font-weight:800;font-size:14px;")
        meta = QLabel(
            f"Last created: {str(wf.get('created_at', ''))[:10]} · "
            f"{len(wf.get('tasks') or [])} steps · {wf.get('trigger_type', 'manual')}"
        )
        meta.setObjectName("pageSubtitle")
        meta.setWordWrap(True)
        row = QHBoxLayout()
        run = QPushButton("Run Workflow")
        run.clicked.connect(lambda _=False, i=wf["workflow_id"]: self.run_requested.emit(i))
        delete = QPushButton("Delete")
        delete.setObjectName("btnGhost")
        delete.clicked.connect(lambda _=False, i=wf["workflow_id"]: self.delete_requested.emit(i))
        row.addWidget(run)
        row.addWidget(delete)
        lay.addWidget(icon)
        lay.addWidget(title)
        lay.addWidget(meta)
        lay.addStretch()
        lay.addLayout(row)
        return card

    def _create(self) -> None:
        name, ok = QInputDialog.getText(self, "Create Workflow", "Workflow name:")
        if not ok or not name.strip():
            return
        desc, ok2 = QInputDialog.getText(self, "Create Workflow", "Description (optional):")
        if not ok2:
            desc = ""
        self.create_requested.emit(name.strip(), (desc or "").strip())

    def set_live_logs(self, lines: List[str]) -> None:
        if not lines:
            self.live_logs.setText("No recent workflow runs yet.")
        else:
            self.live_logs.setText("\n".join(lines[:6]))
