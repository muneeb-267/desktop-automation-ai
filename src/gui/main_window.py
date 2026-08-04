"""Main dashboard window for AI Desktop Automation Suite."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStatusBar,
    QMessageBox,
)

from src.gui.components.feed_widget import FeedWidget
from src.gui.components.controls_widget import ControlsWidget
from src.gui.components.logs_widget import LogsWidget
from src.gui.styles import DARK_THEME
from src.gui.workers import AutomationWorker, DummyLogFeeder


class MainWindow(QMainWindow):
    """Primary application shell: header, split feed/controls, log console."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Desktop Automation Suite")
        self.setMinimumSize(QSize(1100, 700))
        self.resize(1280, 800)
        self.setStyleSheet(DARK_THEME)

        self._automation: Optional[AutomationWorker] = None
        self._heartbeat: Optional[DummyLogFeeder] = None

        self._build_ui()
        self._wire_signals()
        self._start_heartbeat()
        self.set_status("idle")

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(8)

        # Main split: feed (60%) | controls (40%)
        self.main_split = QSplitter(Qt.Horizontal)
        self.feed = FeedWidget()
        self.controls = ControlsWidget()
        self.main_split.addWidget(self.feed)
        self.main_split.addWidget(self.controls)
        self.main_split.setStretchFactor(0, 6)
        self.main_split.setStretchFactor(1, 4)
        self.main_split.setSizes([720, 480])

        # Vertical: main area | logs
        self.vert_split = QSplitter(Qt.Vertical)
        self.vert_split.addWidget(self.main_split)
        self.logs = LogsWidget()
        self.vert_split.addWidget(self.logs)
        self.vert_split.setStretchFactor(0, 7)
        self.vert_split.setStretchFactor(1, 3)
        self.vert_split.setSizes([560, 200])

        body_layout.addWidget(self.vert_split)
        root.addWidget(body, stretch=1)

        status = QStatusBar()
        status.showMessage("Ready — configure a task and press Start")
        self.setStatusBar(status)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("headerBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        title = QLabel("AI Desktop Automation Suite")
        title.setObjectName("appTitle")

        self.status_badge = QLabel("● Idle")
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setProperty("status", "idle")
        self.status_badge.setAlignment(Qt.AlignCenter)

        self.btn_quick_capture = QPushButton("Capture")
        self.btn_quick_capture.setObjectName("btnQuick")
        self.btn_quick_capture.setCheckable(True)
        self.btn_quick_capture.clicked.connect(self._on_header_capture)

        self.btn_quick_run = QPushButton("Run Task")
        self.btn_quick_run.setObjectName("btnQuick")
        self.btn_quick_run.clicked.connect(
            lambda: self.controls.start_requested.emit(self.controls.get_config())
        )

        self.btn_about = QPushButton("About")
        self.btn_about.setObjectName("btnQuick")
        self.btn_about.clicked.connect(self._show_about)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.status_badge)
        layout.addStretch()
        layout.addWidget(self.btn_quick_capture)
        layout.addWidget(self.btn_quick_run)
        layout.addWidget(self.btn_about)
        return bar

    # ── Signal wiring ─────────────────────────────────────────

    def _wire_signals(self) -> None:
        self.controls.start_requested.connect(self._on_start)
        self.controls.stop_requested.connect(self._on_stop)
        self.controls.capture_toggled.connect(self._on_capture_toggled)
        self.controls.config_changed.connect(self._on_config_changed)

    def _start_heartbeat(self) -> None:
        self._heartbeat = DummyLogFeeder(self, interval=18.0)
        self._heartbeat.log.connect(self.logs.append)
        self._heartbeat.start()

    # ── Status helpers ────────────────────────────────────────

    def set_status(self, state: str) -> None:
        """Update header badge: idle | active | error."""
        labels = {
            "idle": "● Idle",
            "active": "● Active",
            "error": "● Error",
        }
        self.status_badge.setText(labels.get(state, "● Idle"))
        self.status_badge.setProperty("status", state)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.status_badge.update()

    # ── Slots ─────────────────────────────────────────────────

    def _on_config_changed(self, config: dict) -> None:
        target = config.get("ocr_target") or "—"
        self.statusBar().showMessage(
            f"Task: {config.get('task')}  ·  Target: {target}  ·  "
            f"Confidence ≥ {config.get('confidence', 0):.2f}"
        )

    def _on_capture_toggled(self, enabled: bool) -> None:
        self.btn_quick_capture.blockSignals(True)
        self.btn_quick_capture.setChecked(enabled)
        self.btn_quick_capture.blockSignals(False)

        if enabled:
            self.feed.start_capture()
            self.logs.info("Live vision capture started")
            self.statusBar().showMessage("Vision feed active")
        else:
            self.feed.stop_capture()
            self.logs.info("Live vision capture stopped")
            self.statusBar().showMessage("Vision feed stopped")

    def _on_header_capture(self, checked: bool) -> None:
        # Mirror into the controls panel button
        self.controls.btn_capture.blockSignals(True)
        self.controls.btn_capture.setChecked(checked)
        self.controls.btn_capture.setText(
            "Stop Capture" if checked else "Start Capture"
        )
        self.controls.btn_capture.setProperty(
            "active", "true" if checked else "false"
        )
        self.controls.btn_capture.style().unpolish(self.controls.btn_capture)
        self.controls.btn_capture.style().polish(self.controls.btn_capture)
        self.controls.btn_capture.blockSignals(False)
        self._on_capture_toggled(checked)

    def _on_start(self, config: dict) -> None:
        if self._automation and self._automation.isRunning():
            self.logs.warning("Automation already running")
            return

        # Auto-start capture if highlighting is on
        if config.get("highlight") and not self.feed.is_capturing():
            self.controls.btn_capture.setChecked(True)
            self._on_capture_toggled(True)

        self.logs.info(f"Dispatching task '{config['task']}'")
        self.controls.set_running(True)
        self.btn_quick_run.setEnabled(False)

        self._automation = AutomationWorker(
            task=config.get("task", "Click Target"),
            ocr_target=config.get("ocr_target", ""),
            confidence=float(config.get("confidence", 0.8)),
            parent=self,
        )
        self._automation.log.connect(self.logs.append)
        self._automation.status_changed.connect(self.set_status)
        self._automation.progress.connect(self.controls.set_progress)
        self._automation.finished_ok.connect(self._on_automation_finished)
        self._automation.failed.connect(self._on_automation_failed)
        self._automation.start()

    def _on_stop(self) -> None:
        if self._automation and self._automation.isRunning():
            self.logs.warning("Stop requested — cancelling worker")
            self._automation.stop()
            self._automation.wait(3000)
        self._reset_run_ui()
        self.set_status("idle")

    def _on_automation_finished(self, result: dict) -> None:
        self.logs.success(
            f"Finished '{result.get('task')}' "
            f"(matched={result.get('matched')}, "
            f"{result.get('duration_s')}s)"
        )
        self._reset_run_ui()
        self.statusBar().showMessage("Task completed successfully")

    def _on_automation_failed(self, message: str) -> None:
        self.logs.error(message)
        self._reset_run_ui()
        self.set_status("error")
        self.statusBar().showMessage("Task failed")

    def _reset_run_ui(self) -> None:
        self.controls.set_running(False)
        self.btn_quick_run.setEnabled(True)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About",
            "<b>AI Desktop Automation Suite</b><br><br>"
            "Modular PyQt5 frontend for computer-vision driven "
            "desktop automation.<br><br>"
            "Vision / OCR / input backends are stubbed with "
            "background <code>QThread</code> workers — swap in "
            "OpenCV, pytesseract, and pyautogui when ready.",
        )

    def shutdown(self) -> None:
        """Stop all background threads before the window is destroyed."""
        if self._automation is not None:
            self._automation.stop()
            if self._automation.isRunning():
                self._automation.wait(3000)
            self._automation = None
        if self._heartbeat is not None:
            self._heartbeat.stop()
            if self._heartbeat.isRunning():
                self._heartbeat.wait(3000)
            self._heartbeat = None
        self.feed.stop_capture()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
