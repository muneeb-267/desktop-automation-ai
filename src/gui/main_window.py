"""Main shell with sidebar navigation matching app flow wireframe."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QKeySequence
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
    QApplication,
    QShortcut,
    QInputDialog,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
)

from src.db.repositories import (
    ExecutionLogRepository,
    NLPCommandRepository,
    ScreenCaptureRepository,
    TaskRepository,
    UserConfRepository,
)
from src.gui.pages.dashboard_page import DashboardPage
from src.gui.pages.history_page import HistoryPage
from src.gui.pages.settings_page import SettingsPage
from src.gui.pages.voice_page import VoiceCommandPage
from src.gui.pages.workflows_page import WorkflowsPage
from src.gui.styles import get_app_style
from src.gui.window_fit import apply_standard_window_chrome, fit_to_screen
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
        self.capture_repo = ScreenCaptureRepository(self.db)

        app_name = self.config.get("app", {}).get("name", "Automate AI")
        self.setWindowTitle(app_name)
        apply_standard_window_chrome(self)
        ui = self.config.get("ui", {})
        fit_to_screen(
            self,
            preferred_w=int(ui.get("window_width", 1080)),
            preferred_h=int(ui.get("window_height", 680)),
            min_w=int(ui.get("min_width", 860)),
            min_h=int(ui.get("min_height", 560)),
        )
        self.setStyleSheet(get_app_style(ui.get("theme", "light")))

        self._command_worker: Optional[CommandWorker] = None
        self._workflow_worker: Optional[WorkflowWorker] = None
        self._speech_worker: Optional[SpeechWorker] = None
        self._nav_buttons: Dict[str, QPushButton] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_all_now)
        self._current_page = "dashboard"

        self._build_ui()
        self._wire()
        self._load_settings()
        # Fast voice hotkey
        QShortcut(QKeySequence("Ctrl+Space"), self, activated=self._listen)
        self._show_page("dashboard")
        self.schedule_refresh(immediate=True)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        side = QFrame()
        side.setObjectName("sideBar")
        side.setFixedWidth(190)
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
        self.page_voice.stop_requested.connect(self._stop_workers)

        self.page_workflows.run_requested.connect(self._run_workflow)
        self.page_workflows.create_requested.connect(self._create_workflow)
        self.page_workflows.delete_requested.connect(self._delete_workflow)
        self.page_workflows.edit_requested.connect(self._edit_workflow)
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
        self._current_page = key
        self.stack.setCurrentIndex(mapping.get(key, 0))
        for k, btn in self._nav_buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if key == "voice":
            # Pre-open mic path so first listen feels instant
            QTimer.singleShot(0, self.speech.warm_up)
        # Light refresh only for the visible page (keeps UI smooth)
        self.schedule_refresh()

    def _load_settings(self) -> None:
        conf = self.conf_repo.get_map(self.user["user_id"])
        # Merge optional cloud keys from config file defaults
        speech_cfg = self.config.get("speech", {})
        if not conf.get("openai_api_key") and speech_cfg.get("openai_api_key"):
            conf = {**conf, "openai_api_key": speech_cfg.get("openai_api_key")}
        if not conf.get("gemini_api_key") and speech_cfg.get("gemini_api_key"):
            conf = {**conf, "gemini_api_key": speech_cfg.get("gemini_api_key")}
        self.page_settings.apply_conf(conf)
        self.pipeline.apply_user_settings(self.user["user_id"])
        sens = float(conf.get("voice_sensitivity", conf.get("mic_sensitivity", 0.9)))
        self.page_voice.sensitivity.blockSignals(True)
        self.page_voice.sensitivity.setValue(int(sens * 100))
        self.page_voice.sensitivity.blockSignals(False)
        self.speech.set_sensitivity(sens)
        self.speech.set_api_keys(
            openai_key=str(conf.get("openai_api_key") or speech_cfg.get("openai_api_key") or ""),
            gemini_key=str(conf.get("gemini_api_key") or speech_cfg.get("gemini_api_key") or ""),
        )
        cloud = self.speech.cloud_status()
        bits = ["Chrome voice"]
        if cloud["openai"]:
            bits.append("Whisper")
        if cloud["gemini"]:
            bits.append("Gemini")
        self.page_voice.set_engine_label("Engine: " + " · ".join(bits))
        self._apply_theme(str(conf.get("theme") or self.config.get("ui", {}).get("theme", "light")))

    def _apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        style = get_app_style(theme)
        if app is not None:
            app.setStyleSheet(style)
        self.setStyleSheet(style)
        self.conf_repo.set(self.user["user_id"], "theme", theme)

    def _save_settings(self, values: dict) -> None:
        self.conf_repo.update_many(self.user["user_id"], values)
        self.pipeline.apply_user_settings(self.user["user_id"])
        self.speech.set_sensitivity(float(values.get("mic_sensitivity", 0.9)))
        self.speech.set_api_keys(
            openai_key=str(values.get("openai_api_key") or ""),
            gemini_key=str(values.get("gemini_api_key") or ""),
        )
        if values.get("theme"):
            self._apply_theme(str(values["theme"]))
        cloud = self.speech.cloud_status()
        bits = ["Chrome voice"]
        if cloud["openai"]:
            bits.append("Whisper")
        if cloud["gemini"]:
            bits.append("Gemini")
        self.page_voice.set_engine_label("Engine: " + " · ".join(bits))
        QMessageBox.information(self, "Settings", "Settings applied.")
        self._show_page("dashboard")

    def _set_sensitivity(self, value: float) -> None:
        self.conf_repo.set(self.user["user_id"], "voice_sensitivity", f"{value:.2f}")
        self.conf_repo.set(self.user["user_id"], "mic_sensitivity", f"{value:.2f}")
        self.speech.set_sensitivity(value)

    def schedule_refresh(self, immediate: bool = False) -> None:
        if immediate:
            self._refresh_timer.stop()
            self._refresh_all_now()
        else:
            self._refresh_timer.start(60)

    def refresh_all(self) -> None:
        self.schedule_refresh(immediate=True)

    def _refresh_all_now(self) -> None:
        uid = self.user["user_id"]
        conf = self.conf_repo.get_map(uid)
        dry = str(conf.get("dry_run", "0")) in ("1", "true", "True")
        page = self._current_page

        if page in ("dashboard", "history", "workflows", "voice"):
            logs = self.log_repo.recent(user_id=uid, limit=30)
        else:
            logs = []

        if page == "dashboard":
            stats = self.log_repo.stats(uid)
            self.page_dashboard.update_stats(stats, dry_run=dry)
            self.page_dashboard.update_activity(logs)
        elif page == "history":
            captures_by_log = {}
            for log in logs:
                lid = log.get("log_id")
                if lid:
                    captures_by_log[int(lid)] = self.capture_repo.list_for_log(int(lid))
            self.page_history.update_logs(logs, captures_by_log)
        elif page == "voice":
            commands = self.nlp_repo.recent(user_id=uid, limit=12)
            status_map = {}
            for log in logs:
                cid = log.get("command_id")
                if cid:
                    status_map[cid] = log.get("status", "")
            self.page_voice.update_recent(commands, status_map)
        elif page == "workflows":
            stats = self.log_repo.stats(uid)
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
        QApplication.processEvents()

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

    def _needs_desktop_focus(self, text: str) -> bool:
        """URL/app launches don't need minimizing; clicks/typing do."""
        t = text.lower()
        if any(k in t for k in ("click", "type", "write", "press", "scroll", "fill")):
            return True
        return False

    def _run_command(self, text: str, *, source: str = "text") -> None:
        if not text.strip() or self._busy():
            return
        if self._current_page != "voice":
            self._show_page("voice")
        self.page_voice.set_command_text(text)
        mode = "LIVE" if not self.pipeline.automation.dry_run else "dry-run"
        self.page_voice.set_busy(True)
        self.page_voice.set_status_message(f"● Running ({mode})…")
        # Only minimize when we must interact with on-screen UI
        if not self.pipeline.automation.dry_run and self._needs_desktop_focus(text):
            self.showMinimized()
            QApplication.processEvents()
        self.pipeline.automation.clear_history()
        self._command_worker = CommandWorker(
            self.pipeline, text, self.user["user_id"], source=source, parent=self
        )
        self._command_worker.status.connect(self.page_voice.set_status_message)
        self._command_worker.failed.connect(lambda m: self.page_voice.set_status_message(f"✗ {m}"))
        self._command_worker.finished_ok.connect(self._on_command_done)
        self._command_worker.start()

    def _on_command_done(self, result: dict) -> None:
        self.page_voice.set_busy(False)
        if self.isMinimized():
            self.showNormal()
            self.raise_()
            self.activateWindow()
        if result.get("ok"):
            mode = "dry-run" if result.get("dry_run") else "live"
            self.page_voice.set_status_message(f"✓ Completed successfully ({mode})")
        else:
            self.page_voice.set_status_message(f"✗ {result.get('error') or 'Failed'}")
        self.schedule_refresh()

    def _stop_workers(self) -> None:
        self.pipeline.request_stop()
        for worker in (self._command_worker, self._workflow_worker):
            if worker is not None and worker.isRunning() and hasattr(worker, "stop"):
                worker.stop()
        self.page_voice.set_status_message("● Stop requested…")
        self.page_voice.set_busy(False)

    def _listen(self) -> None:
        if self._busy():
            return
        self._show_page("voice")
        self.page_voice.set_listening(True)
        self.page_voice.set_status_message("● Starting Chrome voice…")
        self._speech_worker = SpeechWorker(self.speech, parent=self)
        self._speech_worker.status.connect(self.page_voice.set_status_message)
        self._speech_worker.failed.connect(self._on_speech_fail)
        self._speech_worker.transcribed.connect(self._on_transcribed)
        self._speech_worker.start()

    def _on_speech_fail(self, message: str) -> None:
        self.page_voice.set_listening(False)
        self.page_voice.set_status_message(f"✗ {message}")
        self.page_voice.focus_command()
        if self.statusBar():
            self.statusBar().showMessage(message, 5000)

    def _on_transcribed(self, text: str) -> None:
        self.page_voice.set_listening(False)
        self.page_voice.set_command_text(text)
        backend = getattr(self.speech, "last_backend", "") or "voice"
        self.page_voice.set_status_message(f"Heard ({backend}): {text}")
        self._run_command(text, source="voice")

    def _run_workflow(self, workflow_id: int) -> None:
        if self._busy():
            return
        self._workflow_worker = WorkflowWorker(
            self.pipeline, workflow_id, self.user["user_id"], parent=self
        )
        self._workflow_worker.failed.connect(self._on_workflow_fail)
        self._workflow_worker.finished_ok.connect(self._on_workflow_done)
        if not self.pipeline.automation.dry_run:
            self.showMinimized()
            QApplication.processEvents()
        self._workflow_worker.start()

    def _on_workflow_fail(self, message: str) -> None:
        if self.isMinimized():
            self.showNormal()
        QMessageBox.warning(self, "Workflow", message)

    def _on_workflow_done(self, _result: dict) -> None:
        if self.isMinimized():
            self.showNormal()
            self.raise_()
        self.schedule_refresh()

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

    def _edit_workflow(self, workflow_id: int) -> None:
        wf = self.workflows.get_workflow(workflow_id)
        if not wf:
            QMessageBox.warning(self, "Edit", "Workflow not found.")
            return
        name, ok = QInputDialog.getText(
            self, "Rename Workflow", "Workflow name:", text=wf.get("name", "")
        )
        if not ok or not name.strip():
            return
        self.workflows.rename_workflow(workflow_id, name.strip())

        # Optional step editor — one intent per line: intent|element_or_app|value
        current_tasks = wf.get("tasks") or []
        lines = []
        for t in current_tasks:
            lines.append(
                f"{t.get('intent','wait')}|{t.get('target_app','')}|{t.get('target_element','')}|{t.get('input_value','')}"
            )
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit workflow steps")
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel("One step per line: intent|target_app|target_element|input_value")
        )
        editor = QTextEdit()
        editor.setPlainText("\n".join(lines) or "open_app|chrome||\nwait|||1")
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec_() == QDialog.Accepted:
            tasks = []
            for i, raw in enumerate(editor.toPlainText().splitlines(), start=1):
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                parts = [p.strip() for p in raw.split("|")]
                while len(parts) < 4:
                    parts.append("")
                intent, app, element, value = parts[:4]
                params: Dict[str, Any] = {}
                if intent == "wait":
                    try:
                        params["seconds"] = float(value or 1)
                    except ValueError:
                        params["seconds"] = 1.0
                elif intent == "search_web":
                    params["query"] = value
                elif intent == "scroll":
                    params["direction"] = value or "down"
                    params["amount"] = 3
                elif intent == "fill_form":
                    params["field"] = element
                    params["text"] = value
                tasks.append(
                    {
                        "intent": intent or "wait",
                        "target_app": app,
                        "target_element": element,
                        "input_value": value,
                        "params": params,
                        "step_order": i,
                    }
                )
            if tasks:
                self.workflows.save_tasks(workflow_id, tasks)
        self.refresh_all()

    def shutdown(self) -> None:
        for worker in (self._command_worker, self._workflow_worker, self._speech_worker):
            if worker is not None and worker.isRunning():
                if hasattr(worker, "stop"):
                    worker.stop()
                worker.wait(1200)
