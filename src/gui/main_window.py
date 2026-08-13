"""Main shell with sidebar navigation matching app flow wireframe."""

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
    QStackedWidget,
    QLineEdit,
    QMessageBox,
    QFrame,
)

from src.db.repositories import (
    ExecutionLogRepository,
    NLPCommandRepository,
    TaskRepository,
    UserConfRepository,
)
from src.gui.pages.dashboard_page import DashboardPage
from src.gui.pages.history_page import HistoryPage
from src.gui.pages.settings_page import SettingsPage
from src.gui.pages.voice_page import VoiceCommandPage
from src.gui.pages.workflows_page import WorkflowsPage
from src.gui.styles import APP_STYLE
from src.gui.workers import CommandWorker, SpeechWorker, WorkflowWorker


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
        self.log_repo = ExecutionLogRepository(self.db)
        self.nlp_repo = NLPCommandRepository(self.db)
        self.task_repo = TaskRepository(self.db)

        app_name = self.config.get("app", {}).get("name", "Automate AI")
        self.setWindowTitle(app_name)
        self.setMinimumSize(QSize(1180, 720))
        ui = self.config.get("ui", {})
        self.resize(int(ui.get("window_width", 1360)), int(ui.get("window_height", 860)))
        self.setStyleSheet(APP_STYLE)

        self._command_worker: Optional[CommandWorker] = None
        self._workflow_worker: Optional[WorkflowWorker] = None
        self._speech_worker: Optional[SpeechWorker] = None
        self._nav_buttons: Dict[str, QPushButton] = {}

        self._build_ui()
        self._wire()
        self._load_settings()
        self.refresh_all()
        self._show_page("dashboard")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        side = QFrame()
        side.setObjectName("sideBar")
        side.setFixedWidth(230)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 18, 16, 16)
        sl.setSpacing(6)

        brand_row = QHBoxLayout()
        mark = QLabel("⌁")
        mark.setStyleSheet(
            "background:#111827;color:white;border-radius:7px;padding:4px 8px;font-weight:800;"
        )
        brand = QLabel(self.config.get("app", {}).get("name", "Automate AI"))
        brand.setObjectName("sideBrand")
        brand_row.addWidget(mark)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        sl.addLayout(brand_row)
        sl.addSpacing(18)

        for key, label in (
            ("dashboard", "Dashboard"),
            ("voice", "Voice Command"),
            ("history", "Execution History"),
            ("workflows", "Workflow Management"),
            ("settings", "Settings"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("btnNav")
            btn.clicked.connect(lambda _=False, k=key: self._show_page(k))
            self._nav_buttons[key] = btn
            sl.addWidget(btn)

        sl.addStretch()
        ready = QLabel("● SYSTEM_READY")
        ready.setObjectName("statusChip")
        sl.addWidget(ready)
        signout = QPushButton("Sign Out")
        signout.setObjectName("btnSecondary")
        signout.clicked.connect(self.close)
        sl.addWidget(signout)

        # Main column
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        top = QFrame()
        top.setObjectName("topBar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 12, 20, 12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search commands or logs...")
        self.search.returnPressed.connect(self._search)
        user_lbl = QLabel(self.user.get("username", "user"))
        user_lbl.setStyleSheet(
            "background:#e5e7eb;border-radius:14px;padding:6px 10px;font-weight:700;"
        )
        tl.addWidget(self.search, 1)
        tl.addWidget(QLabel("🔔"))
        tl.addWidget(user_lbl)

        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_voice = VoiceCommandPage()
        self.page_history = HistoryPage()
        self.page_workflows = WorkflowsPage()
        self.page_settings = SettingsPage()
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_voice)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_workflows)
        self.stack.addWidget(self.page_settings)

        main.addWidget(top)
        main.addWidget(self.stack, 1)

        root.addWidget(side)
        root.addLayout(main, 1)

    def _wire(self) -> None:
        self.page_dashboard.open_voice.connect(lambda: self._show_page("voice"))
        self.page_dashboard.open_history.connect(lambda: self._show_page("history"))
        self.page_dashboard.open_workflows.connect(lambda: self._show_page("workflows"))
        self.page_dashboard.run_diagnostics.connect(
            lambda: self._run_command("Wait 1 seconds")
        )

        self.page_voice.execute_requested.connect(self._run_command)
        self.page_voice.mic_requested.connect(self._listen)
        self.page_voice.rerun_requested.connect(self._run_command)
        self.page_voice.sensitivity_changed.connect(self._set_sensitivity)

        self.page_workflows.run_requested.connect(self._run_workflow)
        self.page_workflows.create_requested.connect(self._create_workflow)
        self.page_workflows.delete_requested.connect(self._delete_workflow)
        self.page_workflows.refresh_requested.connect(self.refresh_all)

        self.page_settings.save_requested.connect(self._save_settings)

    def _show_page(self, key: str) -> None:
        mapping = {
            "dashboard": 0,
            "voice": 1,
            "history": 2,
            "workflows": 3,
            "settings": 4,
        }
        self.stack.setCurrentIndex(mapping.get(key, 0))
        for k, btn in self._nav_buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh_all()

    def _load_settings(self) -> None:
        conf = self.conf_repo.get_map(self.user["user_id"])
        self.page_settings.apply_conf(conf)
        self.pipeline.apply_user_settings(self.user["user_id"])
        sens = float(conf.get("voice_sensitivity", conf.get("mic_sensitivity", 0.7)))
        self.page_voice.sensitivity.setValue(int(sens * 100))

    def _save_settings(self, values: dict) -> None:
        self.conf_repo.update_many(self.user["user_id"], values)
        self.pipeline.apply_user_settings(self.user["user_id"])
        QMessageBox.information(self, "Settings", "Settings applied.")
        self._show_page("dashboard")

    def _set_sensitivity(self, value: float) -> None:
        self.conf_repo.set(self.user["user_id"], "voice_sensitivity", f"{value:.2f}")
        self.conf_repo.set(self.user["user_id"], "mic_sensitivity", f"{value:.2f}")
        self.speech.mic_sensitivity = value

    def refresh_all(self) -> None:
        uid = self.user["user_id"]
        stats = self.log_repo.stats(uid)
        conf = self.conf_repo.get_map(uid)
        dry = str(conf.get("dry_run", "1")) in ("1", "true", "True")
        logs = self.log_repo.recent(user_id=uid, limit=40)
        self.page_dashboard.update_stats(stats, dry_run=dry)
        self.page_dashboard.update_activity(logs)
        self.page_history.update_logs(logs)

        commands = self.nlp_repo.recent(user_id=uid, limit=20)
        status_map = {}
        for log in logs:
            cid = log.get("command_id")
            if cid:
                status_map[cid] = log.get("status", "")
        self.page_voice.update_recent(commands, status_map)

        wfs = self.workflows.list_workflows(uid)
        avg = self.task_repo.average_steps(uid)
        self.page_workflows.set_workflows(
            wfs, today_executions=stats.get("today", 0), avg_steps=avg
        )
        live = [
            f"{l.get('started_at', '')} · {l.get('status')} · {l.get('action_id') or 'command'}"
            for l in logs[:5]
        ]
        self.page_workflows.set_live_logs(live)

    def _search(self) -> None:
        q = self.search.text().strip()
        if q:
            self._show_page("voice")
            self.page_voice.set_command_text(q)

    def _busy(self) -> bool:
        for worker in (self._command_worker, self._workflow_worker, self._speech_worker):
            if worker is not None and worker.isRunning():
                return True
        return False

    def _run_command(self, text: str) -> None:
        if not text.strip() or self._busy():
            return
        self._show_page("voice")
        self.page_voice.set_command_text(text)
        self.page_voice.set_status_message("● Running…")
        self.pipeline.automation.clear_history()
        self._command_worker = CommandWorker(
            self.pipeline, text, self.user["user_id"], source="text", parent=self
        )
        self._command_worker.status.connect(self.page_voice.set_status_message)
        self._command_worker.failed.connect(lambda m: self.page_voice.set_status_message(f"✗ {m}"))
        self._command_worker.finished_ok.connect(self._on_command_done)
        self._command_worker.start()

    def _on_command_done(self, result: dict) -> None:
        if result.get("ok"):
            mode = "dry-run" if result.get("dry_run") else "live"
            self.page_voice.set_status_message(f"✓ Completed successfully ({mode})")
        else:
            self.page_voice.set_status_message(f"✗ {result.get('error') or 'Failed'}")
        self.refresh_all()

    def _listen(self) -> None:
        if self._busy():
            return
        if not self.speech.available:
            QMessageBox.information(
                self,
                "Microphone",
                "SpeechRecognition/PyAudio Microphone API is not available. Type a command instead.",
            )
            return
        self.page_voice.set_listening(True)
        self._speech_worker = SpeechWorker(self.speech, parent=self)
        self._speech_worker.failed.connect(self._on_speech_fail)
        self._speech_worker.transcribed.connect(self._on_transcribed)
        self._speech_worker.start()

    def _on_speech_fail(self, message: str) -> None:
        self.page_voice.set_listening(False)
        self.page_voice.set_status_message(f"✗ {message}")
        QMessageBox.warning(self, "Voice input", message)

    def _on_transcribed(self, text: str) -> None:
        self.page_voice.set_listening(False)
        self.page_voice.set_command_text(text)
        self._run_command(text)

    def _run_workflow(self, workflow_id: int) -> None:
        if self._busy():
            return
        self._workflow_worker = WorkflowWorker(
            self.pipeline, workflow_id, self.user["user_id"], parent=self
        )
        self._workflow_worker.failed.connect(
            lambda m: QMessageBox.warning(self, "Workflow", m)
        )
        self._workflow_worker.finished_ok.connect(lambda _r: self.refresh_all())
        self._workflow_worker.start()

    def _create_workflow(self, name: str, description: str) -> None:
        history = self.pipeline.automation.history
        tasks = self.workflows.tasks_from_action_history(history)
        if not tasks:
            tasks = [
                {
                    "intent": "wait",
                    "target_app": "",
                    "target_element": "",
                    "input_value": "1",
                    "params": {"seconds": 1},
                }
            ]
        try:
            self.workflows.create_workflow(
                self.user["user_id"], name, description, tasks=tasks
            )
            self.refresh_all()
        except Exception as exc:
            QMessageBox.warning(self, "Create failed", str(exc))

    def _delete_workflow(self, workflow_id: int) -> None:
        if QMessageBox.question(self, "Delete", "Delete this workflow?") != QMessageBox.Yes:
            return
        self.workflows.delete_workflow(workflow_id)
        self.refresh_all()

    def shutdown(self) -> None:
        for worker in (self._command_worker, self._workflow_worker, self._speech_worker):
            if worker is not None and worker.isRunning():
                if hasattr(worker, "stop"):
                    worker.stop()
                worker.wait(1200)
