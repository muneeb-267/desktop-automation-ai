"""Main dashboard window."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QMessageBox,
)

from src.db.repositories import UserConfRepository
from src.gui.components.controls_widget import ControlsWidget
from src.gui.components.feed_widget import FeedWidget
from src.gui.components.logs_widget import LogsWidget
from src.gui.components.workflows_widget import WorkflowsWidget
from src.gui.styles import LIGHT_THEME
from src.gui.workers import CaptureWorker, CommandWorker, SpeechWorker, WorkflowWorker


class MainWindow(QMainWindow):
    def __init__(self, app_context: Dict[str, Any]) -> None:
        super().__init__()
        self.ctx = app_context
        self.config = app_context["config"]
        self.db = app_context["db"]
        self.pipeline = app_context["pipeline"]
        self.speech = app_context["speech"]
        self.workflows = app_context["workflows"]
        self.user: Dict[str, Any] = app_context["user"]
        self.conf_repo = UserConfRepository(self.db)

        app_name = self.config.get("app", {}).get("name", "Desktop Automation Using AI")
        self.setWindowTitle(app_name)
        self.setMinimumSize(QSize(1100, 700))
        ui = self.config.get("ui", {})
        self.resize(int(ui.get("window_width", 1280)), int(ui.get("window_height", 800)))
        self.setStyleSheet(LIGHT_THEME)

        self._command_worker: Optional[CommandWorker] = None
        self._workflow_worker: Optional[WorkflowWorker] = None
        self._speech_worker: Optional[SpeechWorker] = None
        self._capture_worker: Optional[CaptureWorker] = None
        self._badge_anim: Optional[QPropertyAnimation] = None

        self._build_ui()
        self._wire()
        self._load_user_conf()
        self._refresh_workflows()
        self.set_status("idle")
        self.logs.append(
            f"Signed in as {self.user.get('display_name')} ({self.user.get('username')})",
            "success",
        )
        self.logs.append(
            "Dry-run is ON by default. Uncheck it only when you want real mouse/keyboard control.",
            "warn",
        )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(8)

        self.tabs = QTabWidget()
        dashboard = QWidget()
        dash_layout = QVBoxLayout(dashboard)
        dash_layout.setContentsMargins(8, 8, 8, 8)

        self.main_split = QSplitter(Qt.Horizontal)
        self.feed = FeedWidget()
        self.controls = ControlsWidget()
        self.main_split.addWidget(self.feed)
        self.main_split.addWidget(self.controls)
        self.main_split.setStretchFactor(0, 6)
        self.main_split.setStretchFactor(1, 4)
        self.main_split.setSizes([720, 480])

        self.vert_split = QSplitter(Qt.Vertical)
        self.vert_split.addWidget(self.main_split)
        self.logs = LogsWidget()
        self.vert_split.addWidget(self.logs)
        self.vert_split.setStretchFactor(0, 7)
        self.vert_split.setStretchFactor(1, 3)
        self.vert_split.setSizes([560, 220])

        dash_layout.addWidget(self.vert_split)
        self.workflows_widget = WorkflowsWidget()
        self.tabs.addTab(dashboard, "Dashboard")
        self.tabs.addTab(self.workflows_widget, "Workflows")
        body_layout.addWidget(self.tabs)
        root.addWidget(body, stretch=1)

        status = QStatusBar()
        status.showMessage("Ready — type a command or use the microphone")
        self.setStatusBar(status)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("headerBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        app_name = self.config.get("app", {}).get("name", "Desktop Automation Using AI")
        title = QLabel(app_name)
        title.setObjectName("appTitle")
        group = QLabel(self.config.get("app", {}).get("group_id", "S26CS089"))
        group.setObjectName("appSubtitle")

        self.status_badge = QLabel("● Idle")
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setProperty("status", "idle")
        self.status_badge.setAlignment(Qt.AlignCenter)

        self.btn_about = QPushButton("About")
        self.btn_about.setObjectName("btnQuick")
        self.btn_about.clicked.connect(self._show_about)

        layout.addWidget(title)
        layout.addWidget(group)
        layout.addSpacing(8)
        layout.addWidget(self.status_badge)
        layout.addStretch()
        layout.addWidget(QLabel(self.user.get("display_name", "")))
        layout.addWidget(self.btn_about)
        return bar

    def _wire(self) -> None:
        self.controls.start_requested.connect(self._run_command)
        self.controls.stop_requested.connect(self._stop_all)
        self.controls.mic_requested.connect(self._listen)
        self.controls.capture_requested.connect(self._capture)
        self.controls.settings_changed.connect(self._save_settings)

        self.workflows_widget.refresh_requested.connect(self._refresh_workflows)
        self.workflows_widget.replay_requested.connect(self._replay_workflow)
        self.workflows_widget.delete_requested.connect(self._delete_workflow)
        self.workflows_widget.rename_requested.connect(self._rename_workflow)
        self.workflows_widget.save_from_history_requested.connect(self._save_workflow_from_history)

    def _load_user_conf(self) -> None:
        conf = self.conf_repo.get_for_user(self.user["user_id"])
        if conf:
            self.controls.apply_user_conf(conf)
            self.pipeline.apply_user_settings(self.user["user_id"])

    def _save_settings(self, settings: dict) -> None:
        self.conf_repo.update(
            self.user["user_id"],
            dry_run=settings["dry_run"],
            failsafe=settings["failsafe"],
            pause_seconds=settings["pause_seconds"],
        )
        self.pipeline.automation.set_dry_run(settings["dry_run"])
        self.pipeline.automation.failsafe = settings["failsafe"]
        self.pipeline.automation.pause_seconds = settings["pause_seconds"]
        mode = "DRY-RUN" if settings["dry_run"] else "LIVE"
        self.logs.append(f"Settings updated — mode={mode}", "info")
        self.statusBar().showMessage(f"Mode: {mode}")

    def set_status(self, status: str) -> None:
        labels = {
            "idle": "● Idle",
            "running": "● Running",
            "error": "● Error",
            "success": "● Success",
        }
        self.status_badge.setText(labels.get(status, "● Idle"))
        self.status_badge.setProperty("status", status)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        # Subtle fade-in presence for status changes
        self._badge_anim = QPropertyAnimation(self.status_badge, b"windowOpacity")
        self._badge_anim.setDuration(220)
        self._badge_anim.setStartValue(0.45)
        self._badge_anim.setEndValue(1.0)
        self._badge_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._badge_anim.start()

    def _run_command(self, text: str) -> None:
        if self._busy():
            return
        self.controls.set_running(True)
        self.set_status("running")
        self.logs.append(f"Command: {text}", "info")
        self.pipeline.automation.clear_history()
        self._command_worker = CommandWorker(
            self.pipeline, text, self.user["user_id"], source="text", parent=self
        )
        self._command_worker.status.connect(lambda m: self.controls.set_status(m))
        self._command_worker.status.connect(lambda m: self.logs.append(m, "info"))
        self._command_worker.frame_ready.connect(self.feed.show_frame)
        self._command_worker.failed.connect(self._on_fail)
        self._command_worker.finished_ok.connect(self._on_command_done)
        self._command_worker.start()

    def _on_command_done(self, result: dict) -> None:
        self.controls.set_running(False)
        if result.get("ok"):
            self.set_status("success")
            mode = "dry-run" if result.get("dry_run") else "live"
            self.logs.append(f"Completed successfully ({mode})", "success")
        else:
            self.set_status("error")
            self.logs.append(result.get("error") or "Failed", "error")
        self.statusBar().showMessage("Ready")

    def _on_fail(self, message: str) -> None:
        self.controls.set_running(False)
        self.controls.set_listening(False)
        self.set_status("error")
        self.logs.append(message, "error")

    def _stop_all(self) -> None:
        if self._command_worker and self._command_worker.isRunning():
            self._command_worker.stop()
            self.logs.append("Stop requested…", "warn")
        if self._workflow_worker and self._workflow_worker.isRunning():
            self._workflow_worker.stop()
            self.logs.append("Stop requested for workflow…", "warn")

    def _listen(self) -> None:
        if self._busy():
            return
        if not self.speech.available:
            QMessageBox.information(
                self,
                "Microphone",
                "SpeechRecognition is not available. Type your command instead.",
            )
            return
        self.controls.set_listening(True)
        self.logs.append("Listening for voice command…", "info")
        self._speech_worker = SpeechWorker(self.speech, parent=self)
        self._speech_worker.status.connect(lambda m: self.controls.set_status(m))
        self._speech_worker.failed.connect(self._on_speech_fail)
        self._speech_worker.transcribed.connect(self._on_transcribed)
        self._speech_worker.start()

    def _on_speech_fail(self, message: str) -> None:
        self.controls.set_listening(False)
        self.logs.append(message, "error")
        QMessageBox.warning(self, "Voice input", message)

    def _on_transcribed(self, text: str) -> None:
        self.controls.set_listening(False)
        self.controls.set_command_text(text)
        self.logs.append(f"Heard: {text}", "success")
        self._run_command(text)

    def _capture(self) -> None:
        if self._capture_worker and self._capture_worker.isRunning():
            return
        self.logs.append("Capturing screen…", "info")
        self._capture_worker = CaptureWorker(self.pipeline, parent=self)
        self._capture_worker.frame_ready.connect(self.feed.show_frame)
        self._capture_worker.frame_ready.connect(
            lambda *_: self.logs.append("Capture ready", "success")
        )
        self._capture_worker.failed.connect(lambda m: self.logs.append(m, "error"))
        self._capture_worker.start()

    def _refresh_workflows(self) -> None:
        items = self.workflows.list_workflows(self.user["user_id"])
        self.workflows_widget.set_workflows(items)

    def _replay_workflow(self, workflow_id: int) -> None:
        if self._busy():
            return
        self.controls.set_running(True)
        self.set_status("running")
        self.logs.append(f"Replaying workflow #{workflow_id}", "info")
        self._workflow_worker = WorkflowWorker(
            self.pipeline, workflow_id, self.user["user_id"], parent=self
        )
        self._workflow_worker.status.connect(lambda m: self.logs.append(m, "info"))
        self._workflow_worker.failed.connect(self._on_fail)
        self._workflow_worker.finished_ok.connect(self._on_workflow_done)
        self._workflow_worker.start()

    def _on_workflow_done(self, result: dict) -> None:
        self.controls.set_running(False)
        if result.get("ok"):
            self.set_status("success")
            self.logs.append("Workflow finished", "success")
        else:
            self.set_status("error")
            self.logs.append(result.get("error") or "Workflow failed", "error")

    def _delete_workflow(self, workflow_id: int) -> None:
        self.workflows.delete_workflow(workflow_id)
        self.logs.append(f"Deleted workflow #{workflow_id}", "warn")
        self._refresh_workflows()

    def _rename_workflow(self, workflow_id: int, name: str) -> None:
        try:
            self.workflows.rename_workflow(workflow_id, name)
            self.logs.append(f"Renamed workflow to '{name}'", "success")
            self._refresh_workflows()
        except Exception as exc:
            QMessageBox.warning(self, "Rename failed", str(exc))

    def _save_workflow_from_history(self, name: str, description: str) -> None:
        history = self.pipeline.automation.history
        tasks = self.workflows.tasks_from_action_history(history)
        if not tasks:
            QMessageBox.information(
                self,
                "Nothing to save",
                "Run a command first, then save the actions as a workflow.",
            )
            return
        try:
            wid = self.workflows.create_workflow(
                self.user["user_id"], name, description, tasks=tasks
            )
            self.logs.append(f"Saved workflow '{name}' (#{wid}) with {len(tasks)} steps", "success")
            self._refresh_workflows()
        except Exception as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _busy(self) -> bool:
        for worker in (self._command_worker, self._workflow_worker, self._speech_worker):
            if worker is not None and worker.isRunning():
                return True
        return False

    def _show_about(self) -> None:
        app = self.config.get("app", {})
        QMessageBox.about(
            self,
            "About",
            f"<b>{app.get('name')}</b><br>"
            f"Group ID: {app.get('group_id')}<br>"
            f"Version: {app.get('version')}<br><br>"
            "No-code AI desktop assistant using NLP, Computer Vision, "
            "and local automation.<br>"
            "Product Owner: Mam Saadia Aslam",
        )

    def shutdown(self) -> None:
        self._stop_all()
        for worker in (
            self._command_worker,
            self._workflow_worker,
            self._speech_worker,
            self._capture_worker,
        ):
            if worker is not None and worker.isRunning():
                worker.wait(1500)
