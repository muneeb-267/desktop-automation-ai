"""Voice Command screen."""

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
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSlider,
)


class VoiceCommandPage(QWidget):
    execute_requested = pyqtSignal(str)
    mic_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    rerun_requested = pyqtSignal(str)
    sensitivity_changed = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._recent_bound = False
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        left = QVBoxLayout()
        head = QHBoxLayout()
        titles = QVBoxLayout()
        t = QLabel("Voice Command")
        t.setObjectName("pageTitle")
        s = QLabel("Control your automation ecosystem with natural language.")
        s.setObjectName("pageSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        head.addLayout(titles)
        head.addStretch()
        self.last_lbl = QLabel("Last Command: —")
        self.last_lbl.setObjectName("pageSubtitle")
        head.addWidget(self.last_lbl)
        left.addLayout(head)

        panel = QFrame()
        panel.setObjectName("voicePanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(28, 28, 28, 24)
        pl.setSpacing(14)
        self.status = QLabel("✓ Ready — click Mic (no USB mic needed)")
        self.status.setStyleSheet("font-weight:800;font-size:15px;")
        hint = QLabel(
            "Mic opens Chrome voice (laptop mic OK). Or type below and press Enter — same speed."
        )
        hint.setObjectName("pageSubtitle")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)

        mic_row = QHBoxLayout()
        mic_row.addStretch()
        self.btn_mic = QPushButton("🎙  Speak")
        self.btn_mic.setObjectName("btnMicBig")
        self.btn_mic.setToolTip("Chrome voice recognition — no USB microphone required")
        self.btn_mic.clicked.connect(self.mic_requested.emit)
        mic_row.addWidget(self.btn_mic)
        mic_row.addStretch()

        self.command = QLineEdit()
        self.command.setPlaceholderText(
            "> Open Chrome and search for latest AI trends…"
        )
        self.command.returnPressed.connect(self._emit_execute)

        actions = QHBoxLayout()
        clear = QPushButton("Clear")
        clear.setObjectName("btnGhost")
        clear.clicked.connect(self._clear)
        run = QPushButton("▶  Execute Command")
        run.clicked.connect(self._emit_execute)
        actions.addWidget(clear)
        actions.addStretch()
        actions.addWidget(run)

        pl.addWidget(self.status)
        pl.addWidget(hint)
        pl.addSpacing(8)
        pl.addLayout(mic_row)
        pl.addSpacing(8)
        pl.addWidget(self.command)
        pl.addLayout(actions)
        left.addWidget(panel)

        recent_title = QLabel("Recent Commands")
        recent_title.setStyleSheet("font-weight:800;font-size:14px;")
        left.addWidget(recent_title)
        self.recent = QListWidget()
        self.recent.setMinimumHeight(180)
        left.addWidget(self.recent, 1)

        # Right assistant panel
        right = QFrame()
        right.setObjectName("panelCard")
        right.setFixedWidth(300)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.addWidget(QLabel("AI Assistant"))
        help_lbl = QLabel("Always ready to help — suggestions based on desktop automation intents.")
        help_lbl.setWordWrap(True)
        help_lbl.setObjectName("pageSubtitle")
        rl.addWidget(help_lbl)
        rl.addWidget(QLabel("Suggested Actions"))
        for label, cmd in (
            ("SYSTEM: Open Chrome", "Open chrome"),
            ("REPORTING: Open Calculator", "Open calculator"),
            ("CONTROL: Open Notepad", "Open notepad"),
            ("PRODUCTIVITY: Search Google", "Search latest AI news"),
        ):
            b = QPushButton(label)
            b.setObjectName("btnSecondary")
            b.clicked.connect(lambda _=False, c=cmd: self._suggest(c))
            rl.addWidget(b)

        rl.addSpacing(10)
        rl.addWidget(QLabel("Voice Sensitivity"))
        self.sensitivity = QSlider(Qt.Horizontal)
        self.sensitivity.setRange(10, 100)
        self.sensitivity.setValue(70)
        self.sensitivity.valueChanged.connect(
            lambda v: self.sensitivity_changed.emit(v / 100.0)
        )
        rl.addWidget(self.sensitivity)
        self.conf_lbl = QLabel("Engine: Chrome voice · Whisper/Gemini if keyed")
        self.conf_lbl.setObjectName("pageSubtitle")
        self.conf_lbl.setWordWrap(True)
        rl.addWidget(self.conf_lbl)
        rl.addStretch()
        foot = QLabel("System Status: Online\nv0.1.4-alpha")
        foot.setObjectName("footerLabel")
        rl.addWidget(foot)

        root.addLayout(left, 7)
        root.addWidget(right, 3)

    def _emit_execute(self) -> None:
        text = self.command.text().strip()
        if text:
            self.execute_requested.emit(text)

    def _clear(self) -> None:
        self.command.clear()
        self.clear_requested.emit()

    def _suggest(self, cmd: str) -> None:
        self.command.setText(cmd)

    def set_listening(self, listening: bool) -> None:
        self.status.setText(
            "● Listening… speak now" if listening else "✓ Ready — click Mic (no USB mic needed)"
        )
        self.btn_mic.setEnabled(not listening)
        self.btn_mic.setText("…" if listening else "🎙  Speak")

    def set_command_text(self, text: str) -> None:
        self.command.setText(text)
        self.command.setFocus()
        self.command.selectAll()

    def set_status_message(self, message: str) -> None:
        self.status.setText(message)

    def focus_command(self) -> None:
        self.command.setFocus()
        self.command.selectAll()

    def set_engine_label(self, text: str) -> None:
        self.conf_lbl.setText(text)

    def update_recent(self, commands: List[Dict[str, Any]], logs_by_cmd: Dict[int, str] | None = None) -> None:
        self.recent.clear()
        logs_by_cmd = logs_by_cmd or {}
        if commands:
            self.last_lbl.setText(f"Last Command: {commands[0].get('executed_at', '—')}")
        for cmd in commands[:10]:
            status = logs_by_cmd.get(cmd.get("command_id"), "—")
            text = f"{cmd.get('raw_text', '')}   ·   {cmd.get('executed_at', '')}   ·   {status}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, cmd.get("raw_text", ""))
            self.recent.addItem(item)
        if not self._recent_bound:
            self.recent.itemDoubleClicked.connect(
                lambda it: self.rerun_requested.emit(it.data(Qt.UserRole) or "")
            )
            self._recent_bound = True
