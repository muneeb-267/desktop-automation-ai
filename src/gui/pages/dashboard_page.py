"""System Dashboard screen."""

from __future__ import annotations

from typing import Any, Dict, List

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGridLayout,
)


class DashboardPage(QWidget):
    open_voice = pyqtSignal()
    open_history = pyqtSignal()
    open_workflows = pyqtSignal()
    run_diagnostics = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        head = QVBoxLayout()
        title = QLabel("System Dashboard")
        title.setObjectName("pageTitle")
        sub = QLabel("Monitor your desktop automation ecosystem and system performance.")
        sub.setObjectName("pageSubtitle")
        head.addWidget(title)
        head.addWidget(sub)
        root.addLayout(head)

        # Metrics
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.m_total = self._metric("Total Automations", "0", "+ from your history")
        self.m_rate = self._metric("Success Rate", "100%", "Across all executions")
        self.m_active = self._metric("Active Processes", "0", "Ready")
        self.m_today = self._metric("Executions Today", "0", "Local SQLite logs")
        for w in (self.m_total, self.m_rate, self.m_active, self.m_today):
            metrics.addWidget(w)
        root.addLayout(metrics)

        mid = QHBoxLayout()
        mid.setSpacing(12)

        trend = QFrame()
        trend.setObjectName("panelCard")
        tl = QVBoxLayout(trend)
        tl.setContentsMargins(18, 16, 18, 16)
        tt = QLabel("Automation Trend")
        tt.setStyleSheet("font-weight:800;font-size:15px;")
        ts = QLabel("Execution volume from local history.")
        ts.setObjectName("pageSubtitle")
        self.trend_label = QLabel("Run commands to populate trend data.")
        self.trend_label.setAlignment(Qt.AlignCenter)
        self.trend_label.setMinimumHeight(180)
        self.trend_label.setStyleSheet("background:#f9fafb;border-radius:10px;color:#6b7280;")
        tl.addWidget(tt)
        tl.addWidget(ts)
        tl.addWidget(self.trend_label, 1)

        side = QVBoxLayout()
        side.setSpacing(12)
        actions = QFrame()
        actions.setObjectName("panelCard")
        al = QVBoxLayout(actions)
        al.setContentsMargins(16, 14, 16, 14)
        al.addWidget(self._section("Quick Actions"))
        b1 = QPushButton("New Automation Workflow")
        b1.clicked.connect(self.open_workflows.emit)
        b2 = QPushButton("Run System Diagnostics")
        b2.setObjectName("btnSecondary")
        b2.clicked.connect(self.run_diagnostics.emit)
        b3 = QPushButton("Launch Voice Assistant")
        b3.setObjectName("btnSecondary")
        b3.clicked.connect(self.open_voice.emit)
        al.addWidget(b1)
        al.addWidget(b2)
        al.addWidget(b3)

        resources = QFrame()
        resources.setObjectName("panelCard")
        rl = QVBoxLayout(resources)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.addWidget(self._section("System Resources"))
        self.res_cpu = QLabel("Mode: Dry-run safe")
        self.res_ram = QLabel("Vision: OpenCV + Tesseract")
        self.res_api = QLabel("API Connection: Local")
        self.res_lat = QLabel("Engine: spaCy / NLTK + PyAutoGUI")
        for lab in (self.res_cpu, self.res_ram, self.res_api, self.res_lat):
            lab.setObjectName("pageSubtitle")
            rl.addWidget(lab)

        side.addWidget(actions)
        side.addWidget(resources)
        side.addStretch()

        mid.addWidget(trend, 7)
        mid.addLayout(side, 3)
        root.addLayout(mid, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        table_wrap = QFrame()
        table_wrap.setObjectName("panelCard")
        twl = QVBoxLayout(table_wrap)
        twl.setContentsMargins(16, 14, 16, 14)
        thr = QHBoxLayout()
        thr.addWidget(self._section("Recent Automation Activity"))
        thr.addStretch()
        view_all = QPushButton("View All History")
        view_all.setObjectName("btnGhost")
        view_all.clicked.connect(self.open_history.emit)
        thr.addWidget(view_all)
        twl.addLayout(thr)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Task ID", "Automation Name", "Category", "Execution Time", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(190)
        twl.addWidget(self.table)

        voice = QFrame()
        voice.setObjectName("panelCard")
        voice.setMaximumWidth(280)
        vl = QVBoxLayout(voice)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.addWidget(QLabel("🎙"))
        vl.addWidget(self._section("Try Voice Commands."))
        tip = QLabel("Control your desktop using natural language. Try saying 'Open notepad'.")
        tip.setWordWrap(True)
        tip.setObjectName("pageSubtitle")
        vl.addWidget(tip)
        launch = QPushButton("Launch Assistant")
        launch.clicked.connect(self.open_voice.emit)
        vl.addWidget(launch)
        vl.addStretch()

        bottom.addWidget(table_wrap, 7)
        bottom.addWidget(voice, 3)
        root.addLayout(bottom)

        foot = QLabel("© 2026 Automate AI • System Status: Online")
        foot.setObjectName("footerLabel")
        root.addWidget(foot)

    def _section(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet("font-weight:800;font-size:14px;")
        return lab

    def _metric(self, label: str, value: str, hint: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        v = QLabel(value)
        v.setObjectName("metricValue")
        l = QLabel(label)
        l.setObjectName("metricLabel")
        h = QLabel(hint)
        h.setObjectName("metricHint")
        lay.addWidget(l)
        lay.addWidget(v)
        lay.addWidget(h)
        card.value_label = v  # type: ignore[attr-defined]
        card.hint_label = h  # type: ignore[attr-defined]
        return card

    def update_stats(self, stats: Dict[str, Any], dry_run: bool = True) -> None:
        self.m_total.value_label.setText(str(stats.get("total", 0)))  # type: ignore[attr-defined]
        self.m_rate.value_label.setText(f"{stats.get('success_rate', 100)}%")  # type: ignore[attr-defined]
        self.m_active.value_label.setText("1" if dry_run else "Live")  # type: ignore[attr-defined]
        self.m_today.value_label.setText(str(stats.get("today", 0)))  # type: ignore[attr-defined]
        self.res_cpu.setText(f"Mode: {'Dry-run safe' if dry_run else 'LIVE automation'}")

    def update_activity(self, rows: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for item in rows[:8]:
            r = self.table.rowCount()
            self.table.insertRow(r)
            log_id = str(item.get("log_id", ""))
            details = item.get("details_json") or {}
            if isinstance(details, str):
                import json

                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            name = (
                (details.get("parsed") or {}).get("intent")
                or item.get("action_id")
                or "Command"
            )
            vals = [
                f"TX-{log_id}",
                str(name),
                "Automation",
                str(item.get("started_at", ""))[-8:],
                str(item.get("status", "")),
            ]
            for c, val in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(val))
        count = len(rows)
        self.trend_label.setText(f"Recent executions tracked: {count}\nPeak activity updates as you run commands.")
