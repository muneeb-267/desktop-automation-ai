"""Tiny always-on-top DAI listener on the desktop."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class DaiOverlay(QWidget):
    close_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("daiOverlay")
        self.setWindowTitle("DAI")
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(320, 140)
        self._drag: QPoint | None = None
        self._hidden_for_action = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(4)

        top = QHBoxLayout()
        self.dot = QLabel("●")
        self.dot.setObjectName("daiDot")
        self.title = QLabel("DAI")
        self.title.setObjectName("daiTitle")
        hide = QPushButton("×")
        hide.setObjectName("daiHide")
        hide.setFixedSize(22, 22)
        hide.setCursor(Qt.PointingHandCursor)
        hide.clicked.connect(self.close_requested.emit)
        top.addWidget(self.dot)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(hide)

        self.line = QLabel("Say “DAI” to start")
        self.line.setObjectName("daiLine")
        self.line.setWordWrap(True)

        self.hint = QLabel("Then click / open / type until “DAI close now”")
        self.hint.setObjectName("daiHint")
        self.hint.setWordWrap(True)

        self.retry = QPushButton("Retry mic")
        self.retry.setObjectName("daiRetry")
        self.retry.setMinimumHeight(26)
        self.retry.clicked.connect(self.retry_requested.emit)
        self.retry.hide()

        root.addLayout(top)
        root.addWidget(self.line)
        root.addWidget(self.hint)
        root.addWidget(self.retry)
        self.set_mode("sleep")

    def place_corner(self) -> None:
        screen = self.screen()
        if screen is None:
            from PyQt5.QtWidgets import QApplication

            screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 18, geo.bottom() - self.height() - 18)

    def set_mode(self, mode: str, detail: str = "") -> None:
        mode = (mode or "sleep").lower()
        if mode == "sleep":
            self.dot.setStyleSheet("color:#94a3b8;font-size:14px;")
            self.line.setText(detail or "Say “DAI” to start")
        elif mode == "active":
            self.dot.setStyleSheet("color:#16a34a;font-size:14px;")
            self.line.setText(detail or "Listening — speak commands")
        elif mode == "busy":
            self.dot.setStyleSheet("color:#d97706;font-size:14px;")
            self.line.setText(detail or "Working…")
        elif mode == "error":
            self.dot.setStyleSheet("color:#dc2626;font-size:14px;")
            self.line.setText(detail or "Mic error")
            self.retry.show()
        else:
            self.line.setText(detail or mode)
            self.retry.hide()
        if mode != "error" and hasattr(self, "retry"):
            self.retry.hide()

    def hide_for_action(self) -> None:
        self._hidden_for_action = True
        self.hide()

    def show_after_action(self) -> None:
        if self._hidden_for_action:
            self._hidden_for_action = False
            self.show()
            self.raise_()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag = None
        super().mouseReleaseEvent(event)
