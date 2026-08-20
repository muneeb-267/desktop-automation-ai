"""AI Agent — plan, confirm, speak, screen understanding."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.components.screen_view import ScreenView


class AgentPage(QWidget):
    execute_requested = pyqtSignal(str)
    plan_requested = pyqtSignal(str)
    mic_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    suggestion_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._plan: Dict[str, Any] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        root = QVBoxLayout(host)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(14)

        title = QLabel("AI Desktop Agent")
        title.setObjectName("pageTitle")
        sub = QLabel(
            "Your desktop. Your commands. Automated. — Understand → Plan → Verify → Result"
        )
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(sub)

        ask = QFrame()
        ask.setObjectName("panelCard")
        al = QVBoxLayout(ask)
        al.setContentsMargins(18, 16, 18, 16)
        al.setSpacing(10)
        prompt = QLabel("What would you like me to do?")
        prompt.setObjectName("sectionTitle")
        self.command = QLineEdit()
        self.command.setPlaceholderText('Open Chrome, search for today\'s weather, then open the first result')
        self.command.setMinimumHeight(40)
        self.command.returnPressed.connect(self._plan)
        row = QHBoxLayout()
        speak = QPushButton("🎙 Speak")
        speak.setObjectName("btnMicBig")
        speak.clicked.connect(self.mic_requested.emit)
        plan_btn = QPushButton("Explain plan")
        plan_btn.setObjectName("btnSecondary")
        plan_btn.setMinimumHeight(40)
        plan_btn.clicked.connect(self._plan)
        run_btn = QPushButton("Execute")
        run_btn.setObjectName("btnPrimary")
        run_btn.setMinimumHeight(40)
        run_btn.clicked.connect(self._run)
        stop = QPushButton("STOP AUTOMATION")
        stop.setObjectName("btnDanger")
        stop.setMinimumHeight(40)
        stop.clicked.connect(self.stop_requested.emit)
        row.addWidget(speak)
        row.addWidget(plan_btn, 1)
        row.addWidget(run_btn, 1)
        row.addWidget(stop)
        al.addWidget(prompt)
        al.addWidget(self.command)
        al.addLayout(row)
        self.meta = QLabel("Confidence —  ·  Mode: Local AI planner")
        self.meta.setObjectName("pageSubtitle")
        al.addWidget(self.meta)
        root.addWidget(ask)

        chips = QHBoxLayout()
        for text in (
            "Open Chrome",
            "Search YouTube for Python tutorials",
            "Open my Downloads folder",
            "Copy report.pdf to Desktop",
            "Run my study workflow",
        ):
            chip = QPushButton(text)
            chip.setObjectName("btnGhost")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _=False, t=text: self._use_suggestion(t))
            chips.addWidget(chip)
        chips.addStretch(1)
        root.addLayout(chips)

        mid = QHBoxLayout()
        mid.setSpacing(12)

        plan_card = QFrame()
        plan_card.setObjectName("panelCard")
        pl = QVBoxLayout(plan_card)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.addWidget(self._section("AI PLAN"))
        self.plan_list = QListWidget()
        self.plan_list.setMinimumHeight(220)
        pl.addWidget(self.plan_list, 1)
        self.explain = QTextEdit()
        self.explain.setReadOnly(True)
        self.explain.setMaximumHeight(90)
        self.explain.setPlaceholderText("I’ll explain the plan here before I touch the desktop.")
        pl.addWidget(self.explain)

        vision_card = QFrame()
        vision_card.setObjectName("panelCard")
        vl = QVBoxLayout(vision_card)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.addWidget(self._section("Screen understanding"))
        self.screen = ScreenView()
        vl.addWidget(self.screen, 1)
        self.vision_meta = QLabel("Bounding boxes show what OCR/template matching found.")
        self.vision_meta.setObjectName("pageSubtitle")
        self.vision_meta.setWordWrap(True)
        vl.addWidget(self.vision_meta)

        mid.addWidget(plan_card, 5)
        mid.addWidget(vision_card, 5)
        root.addLayout(mid, 1)

        self.status = QLabel("Ready — type a goal or say DAI")
        self.status.setObjectName("pageSubtitle")
        root.addWidget(self.status)

        scroll.setWidget(host)
        outer.addWidget(scroll)

    def _section(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("sectionTitle")
        return lab

    def _use_suggestion(self, text: str) -> None:
        self.command.setText(text)
        self.suggestion_requested.emit(text)
        self.plan_requested.emit(text)

    def _plan(self) -> None:
        text = self.command.text().strip()
        if text:
            self.plan_requested.emit(text)

    def _run(self) -> None:
        text = self.command.text().strip()
        if text:
            self.execute_requested.emit(text)

    def set_command_text(self, text: str) -> None:
        self.command.setText(text)

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def show_plan(self, plan: Dict[str, Any]) -> None:
        self._plan = plan or {}
        self.plan_list.clear()
        conf = int(float(plan.get("confidence") or 0) * 100)
        mode = plan.get("mode") or "local"
        est = plan.get("estimated_s") or 0
        self.meta.setText(
            f"Intent: {plan.get('intent') or '—'}   ·   Confidence {conf}%   ·   "
            f"~{est:.0f}s   ·   Mode: {mode} planner"
        )
        lines = [
            f"I understood your request as: {plan.get('summary') or ''}",
            f"Estimated execution time: ~{est:.0f} seconds.",
        ]
        if plan.get("needs_clarification"):
            lines.append("⚠ I’m not completely sure — review the plan or pick a suggestion.")
        if plan.get("suggestions") and plan.get("needs_clarification"):
            lines.append("Did you mean: " + "  ·  ".join(plan.get("suggestions")[:4]))
        self.explain.setPlainText("\n".join(lines))
        for step in plan.get("steps") or []:
            mark = {"done": "✓", "running": "●", "failed": "✕"}.get(step.get("status"), "○")
            item = QListWidgetItem(f"{mark}  {step.get('title')}")
            self.plan_list.addItem(item)

    def mark_status(self, message: str) -> None:
        self.status.setText(message)
        # Tick matching running/done lines from live status prefixes
        text = message.strip()
        prefix = ""
        title = text
        if text.startswith("✓ "):
            prefix, title = "✓", text[2:]
        elif text.startswith("● "):
            prefix, title = "●", text[2:]
        elif text.startswith("⚠ "):
            prefix, title = "⚠", text[2:]
        if not prefix:
            return
        for i in range(self.plan_list.count()):
            item = self.plan_list.item(i)
            raw = item.text()[2:].strip() if len(item.text()) > 2 else item.text()
            if raw == title or title.startswith(raw) or raw.startswith(title):
                item.setText(f"{prefix}  {raw}")
                break

    def show_vision(self, frame=None, boxes: Optional[List[Dict[str, Any]]] = None, path: str = "") -> None:
        self.screen.set_frame(frame, boxes=boxes, path=path)
        n = len(boxes or [])
        self.vision_meta.setText(
            f"{n} detected region(s). Purple boxes are OCR/template matches."
            if n
            else "No elements boxed yet — run a click or inspect step."
        )
