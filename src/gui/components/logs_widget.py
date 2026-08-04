"""Execution log terminal with colored status indicators."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QSizePolicy,
)


LEVEL_COLORS = {
    "info": "#8b95a8",
    "success": "#3ddeaa",
    "warning": "#e6b84d",
    "error": "#ff6b6b",
    "debug": "#6b7a99",
}

LEVEL_TAGS = {
    "info": "INFO",
    "success": " OK ",
    "warning": "WARN",
    "error": "ERR ",
    "debug": "DBG ",
}


class LogsWidget(QWidget):
    """Bottom-panel real-time scrolling log window."""

    def __init__(self, parent=None, max_lines: int = 2000) -> None:
        super().__init__(parent)
        self.setObjectName("logsPanel")
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._max_lines = max_lines
        self._filter = "all"
        self._build_ui()
        self._seed_dummy_logs()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("EXECUTION LOG")
        title.setObjectName("panelHeader")

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Info", "Success", "Warning", "Error"])
        self.filter_combo.setMaximumWidth(110)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("btnQuick")
        self.btn_clear.setMaximumWidth(72)
        self.btn_clear.clicked.connect(self.clear)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("btnQuick")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setMaximumWidth(72)
        self.btn_pause.toggled.connect(self._on_pause_toggled)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("Filter"))
        header.addWidget(self.filter_combo)
        header.addWidget(self.btn_pause)
        header.addWidget(self.btn_clear)
        root.addLayout(header)

        self.output = QTextEdit()
        self.output.setObjectName("logOutput")
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.output.setFont(font)
        root.addWidget(self.output)

        self._paused = False
        self._buffer: list[tuple[str, str]] = []  # (message, level) while paused

    # ── Public API ────────────────────────────────────────────

    def append(self, message: str, level: str = "info") -> None:
        level = (level or "info").lower()
        if level not in LEVEL_COLORS:
            level = "info"

        if self._paused:
            self._buffer.append((message, level))
            return

        if self._filter != "all" and level != self._filter:
            # Still accept but skip render — keep simple: only filter live view
            # by checking against current filter
            pass

        if self._filter != "all" and level != self._filter:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        tag = LEVEL_TAGS[level]
        color = LEVEL_COLORS[level]
        line = f"[{ts}]  {tag}  {message}"

        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(line + "\n", fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()
        self._trim()

    def clear(self) -> None:
        self.output.clear()
        self._buffer.clear()
        self.append("Log cleared", "debug")

    def info(self, message: str) -> None:
        self.append(message, "info")

    def success(self, message: str) -> None:
        self.append(message, "success")

    def warning(self, message: str) -> None:
        self.append(message, "warning")

    def error(self, message: str) -> None:
        self.append(message, "error")

    # ── Internals ─────────────────────────────────────────────

    def _trim(self) -> None:
        doc = self.output.document()
        while doc.blockCount() > self._max_lines:
            cursor = QTextCursor(doc.firstBlock())
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # remove trailing newline

    def _on_filter_changed(self, text: str) -> None:
        self._filter = text.lower()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._paused = paused
        self.btn_pause.setText("Resume" if paused else "Pause")
        if not paused and self._buffer:
            pending = self._buffer[:]
            self._buffer.clear()
            for msg, level in pending:
                self.append(msg, level)

    def _seed_dummy_logs(self) -> None:
        self.append("AI Desktop Automation Suite initialized", "success")
        self.append("Loading UI modules…", "info")
        self.append("Vision worker ready (placeholder)", "info")
        self.append("OCR engine stub loaded — pytesseract not invoked yet", "debug")
        self.append("Awaiting user action", "info")
