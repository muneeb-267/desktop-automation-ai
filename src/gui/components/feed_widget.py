"""Live screen / vision display widget with target bounding-box overlays."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)

from src.gui.workers import VisionWorker


class FeedCanvas(QWidget):
    """Paints an RGB frame plus detection boxes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._targets: List[dict] = []
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #0a0c10;")

    def set_frame(self, frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            return
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        # Ensure contiguous RGB buffer for QImage
        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg.copy())
        self.update()

    def set_targets(self, targets: List[dict]) -> None:
        self._targets = targets or []
        self.update()

    def clear_feed(self) -> None:
        self._pixmap = None
        self._targets = []
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0a0c10"))

        if self._pixmap is None:
            painter.setPen(QColor("#4a5160"))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Live Preview — waiting for vision feed\n"
                "Start capture to begin OpenCV stream",
            )
            painter.end()
            return

        # Letterbox-scale the frame into the widget
        scaled = self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        ox = (self.width() - scaled.width()) // 2
        oy = (self.height() - scaled.height()) // 2
        painter.drawPixmap(ox, oy, scaled)

        sx = scaled.width() / self._pixmap.width()
        sy = scaled.height() / self._pixmap.height()

        for box in self._targets:
            x = int(ox + box["x"] * sx)
            y = int(oy + box["y"] * sy)
            w = int(box["w"] * sx)
            h = int(box["h"] * sy)
            conf = float(box.get("confidence", 0.0))
            label = box.get("label", "target")

            pen = QPen(QColor("#3ddeaa"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(QRect(x, y, w, h))

            # Corner accents
            corner = 10
            painter.drawLine(x, y, x + corner, y)
            painter.drawLine(x, y, x, y + corner)
            painter.drawLine(x + w, y, x + w - corner, y)
            painter.drawLine(x + w, y, x + w, y + corner)

            caption = f"{label}  {conf:.0%}"
            painter.fillRect(x, y - 18, max(w, 120), 18, QColor(13, 46, 36, 210))
            painter.setPen(QColor("#3ddeaa"))
            font = QFont("Consolas", 9)
            painter.setFont(font)
            painter.drawText(x + 4, y - 5, caption)

        painter.end()


class FeedWidget(QWidget):
    """Left-panel live preview: OpenCV feed + target overlays."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("feedPanel")
        self._worker: Optional[VisionWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("LIVE VISION FEED")
        title.setObjectName("panelHeader")
        self._fps_label = QLabel("FPS: —")
        self._fps_label.setObjectName("targetInfo")
        self._target_label = QLabel("Targets: 0")
        self._target_label.setObjectName("targetInfo")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._target_label)
        header.addSpacing(16)
        header.addWidget(self._fps_label)
        root.addLayout(header)

        self.canvas = FeedCanvas()
        root.addWidget(self.canvas, stretch=1)

        footer = QHBoxLayout()
        self._hint = QLabel("Source: Simulated OpenCV capture  ·  Overlay: OCR / CV targets")
        self._hint.setObjectName("feedPlaceholder")
        footer.addWidget(self._hint)
        footer.addStretch()
        root.addLayout(footer)

        self._frame_count = 0
        self._fps_timer = QTimer(self)
        self._fps_timer.setInterval(1000)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start()

    # ── Public API ────────────────────────────────────────────

    def start_capture(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._worker = VisionWorker(self, fps=15.0)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.targets_ready.connect(self._on_targets)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def stop_capture(self) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        if self._worker.isRunning():
            self._worker.wait(3000)
        self._worker = None
        self.canvas.clear_feed()
        self._target_label.setText("Targets: 0")
        self._fps_label.setText("FPS: —")

    def is_capturing(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    # ── Slots ─────────────────────────────────────────────────

    def _on_frame(self, frame: object) -> None:
        self.canvas.set_frame(frame)
        self._frame_count += 1

    def _on_targets(self, targets: list) -> None:
        self.canvas.set_targets(targets)
        self._target_label.setText(f"Targets: {len(targets)}")

    def _on_error(self, message: str) -> None:
        self._hint.setText(f"Vision error: {message}")

    def _update_fps(self) -> None:
        if self.is_capturing():
            self._fps_label.setText(f"FPS: {self._frame_count}")
        self._frame_count = 0

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_capture()
        super().closeEvent(event)
