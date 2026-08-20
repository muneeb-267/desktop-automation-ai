"""Main shell with sidebar navigation matching app flow wireframe."""

from __future__ import annotations

import time
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
from src.diagnostics import probe_all
from src.gui.dai_listener import DaiMicThread, DaiSetupThread
from src.gui.dai_overlay import DaiOverlay
from src.gui.components.toast import ToastHost
from src.gui.pages.agent_page import AgentPage
from src.gui.pages.dashboard_page import DashboardPage
from src.gui.pages.diagnostics_page import DiagnosticsPage
from src.gui.pages.history_page import HistoryPage
from src.gui.pages.settings_page import SettingsPage
from src.gui.pages.voice_page import VoiceCommandPage
from src.gui.pages.workflows_page import WorkflowsPage
from src.gui.setup_wizard import SetupWizard
from src.gui.styles import get_app_style
from src.gui.window_fit import apply_standard_window_chrome, fit_to_screen
from src.gui.workflow_editor import WorkflowEditorDialog
from src.gui.workers import CommandWorker, SpeechWorker, WorkflowWorker
from src.speech.wake import classify_utterance, clean_spoken_command


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
        self._dai_thread = None
        self._dai_setup = None
        self._dai_overlay = None
        self._dai_active = False
        self._dai_queue: list = []
        self._live_desktop = False
        self._dai_last_cmd = ""
        self._dai_last_at = 0.0
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
        QShortcut(QKeySequence("Ctrl+Shift+Esc"), self, activated=self._emergency_stop)
        self._show_page("dashboard")
        self.schedule_refresh(immediate=True)
        QTimer.singleShot(600, self._start_dai_listener)
        QTimer.singleShot(800, self._maybe_setup_wizard)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar — wide enough for full nav labels
        side = QFrame()
        side.setObjectName("sideBar")
        side.setFixedWidth(228)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 16)
        sl.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("A")
        mark.setFixedSize(32, 32)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(
            "background:#4f46e5;color:#ffffff;border-radius:8px;"
            "font-weight:800;font-size:16px;"
        )
        brand_col = QVBoxLayout()
        brand = QLabel(self.config.get("app", {}).get("name", "Automate AI"))
        brand.setObjectName("sideBrand")
        brand.setWordWrap(True)
        tag = QLabel("Your desktop. Automated.")
        tag.setObjectName("pageSubtitle")
        tag.setWordWrap(True)
        brand_col.addWidget(brand)
        brand_col.addWidget(tag)
        brand_row.addWidget(mark, 0, Qt.AlignTop)
        brand_row.addLayout(brand_col, 1)
        sl.addLayout(brand_row)
        sl.addSpacing(16)

        for key, label in (
            ("dashboard", "Dashboard"),
            ("agent", "AI Agent"),
            ("voice", "Voice Command"),
            ("history", "Execution History"),
            ("workflows", "Workflows"),
            ("diagnostics", "Diagnostics"),
            ("settings", "Settings"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("btnNav")
            btn.setMinimumHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self._show_page(k))
            self._nav_buttons[key] = btn
            sl.addWidget(btn)

        sl.addStretch()
        ready = QLabel("● SYSTEM_READY")
        ready.setObjectName("statusChip")
        ready.setAlignment(Qt.AlignCenter)
        sl.addWidget(ready)
        sl.addSpacing(8)
        signout = QPushButton("Sign Out")
        signout.setObjectName("btnSecondary")
        signout.setMinimumHeight(36)
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
        tl.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search commands or logs…")
        self.search.setMinimumHeight(36)
        self.search.returnPressed.connect(self._search)
        user_lbl = QLabel(self.user.get("username", "user"))
        user_lbl.setStyleSheet(
            "background:#eef2f7;color:#0f172a;border-radius:16px;"
            "padding:8px 14px;font-weight:600;"
        )
        stop = QPushButton("STOP")
        stop.setObjectName("btnDanger")
        stop.setMinimumHeight(36)
        stop.setToolTip("Emergency stop (Ctrl+Shift+Esc)")
        stop.clicked.connect(self._emergency_stop)
        tl.addWidget(self.search, 1)
        tl.addWidget(stop)
        tl.addWidget(user_lbl)

        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_agent = AgentPage()
        self.page_voice = VoiceCommandPage()
        self.page_history = HistoryPage()
        self.page_workflows = WorkflowsPage()
        self.page_diagnostics = DiagnosticsPage()
        self.page_settings = SettingsPage()
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_agent)
        self.stack.addWidget(self.page_voice)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_workflows)
        self.stack.addWidget(self.page_diagnostics)
        self.stack.addWidget(self.page_settings)

        main.addWidget(top)
        main.addWidget(self.stack, 1)

        root.addWidget(side)
        root.addLayout(main, 1)
        self.toast = ToastHost(self)

    def _wire(self) -> None:
        self.page_dashboard.open_voice.connect(lambda: self._show_page("voice"))
        self.page_dashboard.open_agent.connect(lambda: self._show_page("agent"))
        self.page_dashboard.open_history.connect(lambda: self._show_page("history"))
        self.page_dashboard.open_workflows.connect(lambda: self._show_page("workflows"))
        self.page_dashboard.run_diagnostics.connect(lambda: self._show_page("diagnostics"))

        self.page_agent.execute_requested.connect(self._run_command)
        self.page_agent.plan_requested.connect(self._preview_plan)
        self.page_agent.mic_requested.connect(self._listen)
        self.page_agent.stop_requested.connect(self._emergency_stop)
        self.page_agent.suggestion_requested.connect(self.page_agent.set_command_text)

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
        self.page_workflows.record_start_requested.connect(self._start_workflow_recording)
        self.page_workflows.record_stop_save_requested.connect(self._stop_workflow_recording)

        self.page_settings.save_requested.connect(self._save_settings)
        self.page_voice.show_dai_requested.connect(self._start_dai_listener)

        self.page_diagnostics.refresh_requested.connect(self._refresh_diagnostics)
        self.page_diagnostics.test_capture_requested.connect(self._test_capture)
        self.page_diagnostics.test_ocr_requested.connect(self._test_ocr)
        self.page_diagnostics.test_mouse_requested.connect(self._test_mouse)
        self.page_diagnostics.test_keyboard_requested.connect(self._test_keyboard)
        self.page_diagnostics.test_mic_requested.connect(self._test_mic)

    def _show_page(self, key: str) -> None:
        mapping = {
            "dashboard": 0,
            "agent": 1,
            "voice": 2,
            "history": 3,
            "workflows": 4,
            "diagnostics": 5,
            "settings": 6,
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
        cloud_on = str(conf.get("cloud_ai", "0")) in ("1", "true", "True")
        self.speech.set_api_keys(
            openai_key=str(conf.get("openai_api_key") or speech_cfg.get("openai_api_key") or "") if cloud_on else "",
            gemini_key=str(conf.get("gemini_api_key") or speech_cfg.get("gemini_api_key") or "") if cloud_on else "",
        )
        cloud = self.speech.cloud_status()
        bits = ["Offline DAI (say DAI)"]
        if cloud["openai"]:
            bits.append("Whisper")
        if cloud["gemini"]:
            bits.append("Gemini")
        bits.append("Chrome fallback")
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
        if str(values.get("cloud_ai", "0")) in ("1", "true", "True"):
            self.speech.set_api_keys(
                openai_key=str(values.get("openai_api_key") or ""),
                gemini_key=str(values.get("gemini_api_key") or ""),
            )
        else:
            self.speech.set_api_keys(openai_key="", gemini_key="")
        if values.get("theme"):
            self._apply_theme(str(values["theme"]))
        cloud = self.speech.cloud_status()
        bits = ["Offline DAI (say DAI)"]
        if cloud["openai"]:
            bits.append("Whisper")
        if cloud["gemini"]:
            bits.append("Gemini")
        bits.append("Chrome fallback")
        if cloud["openai"]:
            bits.append("Whisper")
        if cloud["gemini"]:
            bits.append("Gemini")
        self.page_voice.set_engine_label("Engine: " + " · ".join(bits))
        QMessageBox.information(self, "Settings", "Settings applied.")
        self.toast.show("Settings saved", "success")
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

        if page in ("dashboard", "history", "workflows", "voice", "agent"):
            logs = self.log_repo.recent(user_id=uid, limit=30)
        else:
            logs = []

        if page == "dashboard":
            stats = self.log_repo.stats(uid)
            self.page_dashboard.update_stats(stats, dry_run=dry)
            self.page_dashboard.update_activity(logs)
        elif page == "agent":
            pass
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
        elif page == "diagnostics":
            self._refresh_diagnostics()
        QApplication.processEvents()

    def _search(self) -> None:
        q = self.search.text().strip()
        if q:
            self._show_page("agent")
            self.page_agent.set_command_text(q)
            self._preview_plan(q)

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

    def _run_command(self, text: str, *, source: str = "text", live_desktop: bool = False) -> None:
        if not text.strip():
            return
        spoken = clean_spoken_command(text)
        kind, payload = classify_utterance(spoken, session_active=True)
        if kind == "minimize":
            if self._dai_overlay:
                self._dai_overlay.show()
                self._dai_overlay.set_mode("active", "Minimized — still listening")
            self.showMinimized()
            QApplication.processEvents()
            self.page_voice.set_status_message("✓ Minimized (DAI still listening)")
            return
        if kind == "restore":
            self.showNormal()
            self.raise_()
            self.activateWindow()
            if self._dai_overlay:
                self._dai_overlay.show()
                self._dai_overlay.set_mode("active", "Window restored")
            return
        if kind == "repeat":
            if not self._dai_last_cmd:
                if self._dai_overlay:
                    self._dai_overlay.set_mode("active", "Nothing to repeat")
                return
            text = self._dai_last_cmd
        elif kind in ("command", "wake") and payload:
            text = payload
        else:
            text = spoken or text

        if self._busy():
            if live_desktop:
                self._dai_queue.append(text)
                if self._dai_overlay:
                    self._dai_overlay.set_mode("busy", f"Queued: {text}")
            return
        self._live_desktop = live_desktop
        self._dai_last_cmd = text
        if not live_desktop and self._current_page not in ("voice", "agent"):
            self._show_page("agent")
        self.page_voice.set_command_text(text)
        self.page_agent.set_command_text(text)
        try:
            plan = self.pipeline.preview_plan(text, source=source)
            self.page_agent.show_plan(plan.to_dict())
        except Exception:
            pass
        mode = "LIVE" if not self.pipeline.automation.dry_run else "dry-run"
        self.page_voice.set_busy(True)
        self.page_voice.set_status_message(f"STT: {text}  ·  Running ({mode})…")
        self.page_agent.set_status(f"STT: {text}  ·  Running ({mode})…")
        if self._dai_overlay and live_desktop:
            self._dai_overlay.set_mode("busy", f"STT → {text}")
        # Hide chrome so live clicks land on the real desktop
        if not self.pipeline.automation.dry_run and (
            live_desktop or self._needs_desktop_focus(text)
        ):
            if self._dai_overlay:
                self._dai_overlay.hide_for_action()
            self.showMinimized()
            QApplication.processEvents()
        if not self.pipeline.automation.recording:
            self.pipeline.automation.clear_history()
        self._command_worker = CommandWorker(
            self.pipeline, text, self.user["user_id"], source=source, parent=self
        )
        self._command_worker.status.connect(self.page_voice.set_status_message)
        self._command_worker.status.connect(self.page_agent.mark_status)
        self._command_worker.failed.connect(lambda m: self.page_voice.set_status_message(f"✗ {m}"))
        self._command_worker.finished_ok.connect(self._on_command_done)
        self._command_worker.start()

    def _on_command_done(self, result: dict) -> None:
        self.page_voice.set_busy(False)
        live = self._live_desktop
        self._live_desktop = False
        if self._dai_overlay:
            self._dai_overlay.show_after_action()
        if self.isMinimized() and not live:
            self.showNormal()
            self.raise_()
            self.activateWindow()
        if result.get("ok"):
            mode = "dry-run" if result.get("dry_run") else "live"
            self.page_voice.set_status_message(f"✓ Completed successfully ({mode})")
            self.toast.show("✓ Workflow / command completed successfully", "success")
            if self._dai_overlay and self._dai_active:
                self._dai_overlay.set_mode("active", "Listening — next command")
        else:
            err = result.get("error") or "Failed"
            self.page_voice.set_status_message(f"✗ {err}")
            kind = "safety" if "Safety limit" in err or "emergency" in err.lower() else "error"
            self.toast.show(err.split("\n")[0][:160], kind)
            if result.get("suggestions"):
                self.page_agent.show_plan(result.get("plan") or {})
            if self._dai_overlay:
                self._dai_overlay.set_mode(
                    "active" if self._dai_active else "sleep",
                    err.split("\n")[0][:80],
                )
        if result.get("plan"):
            self.page_agent.show_plan(result["plan"])
        self.page_agent.show_vision(
            self.pipeline.last_frame,
            boxes=result.get("boxes") or self.pipeline.last_boxes,
            path=getattr(self.pipeline, "last_capture_path", "") or "",
        )
        if self.pipeline.automation.recording:
            n = len(self.pipeline.automation.session_history)
            self.page_workflows.set_recording(True, step_count=n)
        self.schedule_refresh()
        if live and self._dai_queue:
            nxt = self._dai_queue.pop(0)
            QTimer.singleShot(80, lambda: self._run_command(nxt, source="voice", live_desktop=True))

    def _stop_workers(self) -> None:
        self.pipeline.request_stop("Stopped by user")
        for worker in (self._command_worker, self._workflow_worker):
            if worker is not None and worker.isRunning() and hasattr(worker, "stop"):
                worker.stop()
        self.page_voice.set_status_message("● Stop requested…")
        self.page_voice.set_busy(False)
        self.page_agent.set_status("● Stop requested…")

    def _listen(self) -> None:
        if self._busy():
            return
        self._show_page("voice")
        self.page_voice.set_listening(True)
        self.page_voice.set_status_message("● Starting voice…")
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
        self.page_agent.set_command_text(text)
        backend = getattr(self.speech, "last_backend", "") or "voice"
        self.page_voice.set_status_message(f"Heard ({backend}): {text}")
        self.page_agent.set_status(f"Heard ({backend}): {text}")
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

    def _start_workflow_recording(self) -> None:
        self.pipeline.automation.start_recording()
        self.page_workflows.set_recording(True, step_count=0)
        self._show_page("voice")
        self.page_voice.set_status_message(
            "● Recording workflow — speak or type each step, then Save as workflow"
        )
        QMessageBox.information(
            self,
            "Recording",
            "Recording started.\n\n"
            "1. Go to Voice Command (already opened)\n"
            "2. Speak or type each step (open apps, copy files, click…)\n"
            "3. Open Workflows → Save as workflow and give it a name\n\n"
            "Later say: Run <your workflow name>",
        )

    def _stop_workflow_recording(self) -> None:
        steps = self.pipeline.automation.stop_recording()
        self.page_workflows.set_recording(False, step_count=len(steps))
        if steps:
            QMessageBox.information(
                self,
                "Recording stopped",
                f"Captured {len(steps)} actions.\nClick Save as workflow to name and keep them.",
            )
        else:
            # Resume empty session cleared — user can still save last history
            self.page_workflows.set_recording(False, step_count=0)

    def _create_workflow(self, name: str, description: str) -> None:
        # Prefer full recording session; fall back to last command history
        history = self.pipeline.automation.session_history or self.pipeline.automation.history
        if self.pipeline.automation.recording:
            history = self.pipeline.automation.session_history
            self.pipeline.automation.stop_recording()
            self.page_workflows.set_recording(False, step_count=len(history))

        tasks = self.workflows.tasks_from_action_history(history)
        if not tasks:
            QMessageBox.warning(
                self,
                "No steps to save",
                "Do some actions first (Record steps, then speak/type commands), "
                "then Save as workflow.\n\n"
                "Example: Open Chrome → Search weather → Copy file report to Desktop",
            )
            return
        try:
            self.workflows.create_workflow(
                self.user["user_id"],
                name,
                description,
                tasks=tasks,
                trigger_type="voice",
            )
            self.pipeline.automation.clear_session()
            self.pipeline.automation.clear_history()
            QMessageBox.information(
                self,
                "Workflow saved",
                f"Saved “{name}” with {len(tasks)} steps.\n\n"
                f"Say: Run {name}",
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
        dlg = WorkflowEditorDialog(wf, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        payload = dlg.result_payload()
        if payload.get("name"):
            self.workflows.rename_workflow(workflow_id, payload["name"])
        if payload.get("tasks"):
            self.workflows.save_tasks(workflow_id, payload["tasks"])
        self.toast.show("Workflow updated", "success")
        self.refresh_all()

    def _preview_plan(self, text: str) -> None:
        if not text.strip():
            return
        try:
            plan = self.pipeline.preview_plan(text)
            self.page_agent.show_plan(plan.to_dict())
            self.page_agent.set_status("Plan ready — click Execute when it looks right.")
            if plan.needs_clarification:
                self.toast.show("Low confidence — check suggestions", "warning")
        except Exception as exc:
            self.toast.show(str(exc), "error")

    def _emergency_stop(self) -> None:
        self.pipeline.request_stop("User requested emergency stop.")
        self._stop_workers()
        self.showNormal()
        self.toast.show("🛑 AUTOMATION STOPPED", "safety")
        self.page_agent.set_status("🛑 Emergency stop — remaining actions cancelled.")
        if self._dai_overlay:
            self._dai_overlay.set_mode("sleep" if not self._dai_active else "active", "Stopped")

    def _maybe_setup_wizard(self) -> None:
        conf = self.conf_repo.get_map(self.user["user_id"])
        if str(conf.get("setup_complete", "0")) in ("1", "true", "True"):
            return
        dlg = SetupWizard(self.config, self)
        dlg.exec_()
        self.conf_repo.set(self.user["user_id"], "setup_complete", "1")

    def _refresh_diagnostics(self) -> None:
        self.page_diagnostics.set_results(probe_all(self.config))

    def _test_capture(self) -> None:
        result = self.pipeline.capture_preview()
        ok = result.get("ok")
        self.page_diagnostics.set_test_output(
            "Screen capture OK" if ok else f"Capture issue: {self.pipeline.vision.last_capture_error}"
        )
        self.page_agent.show_vision(result.get("frame"), path=result.get("path") or "")
        self.toast.show("Screen capture tested", "success" if ok else "error")

    def _test_ocr(self) -> None:
        frame = self.pipeline.vision.capture_screen()
        preview = self.pipeline.vision.ocr_preview(frame)
        self.page_agent.show_vision(frame, boxes=preview.boxes)
        self.page_diagnostics.set_test_output(f"OCR boxes: {len(preview.boxes or [])}")
        self.toast.show("OCR test finished", "info")

    def _test_mouse(self) -> None:
        if self.pipeline.automation.dry_run:
            self.page_diagnostics.set_test_output("Dry-run on — mouse not moved.")
            return
        ready = self.pipeline.automation.mouse_ready
        self.page_diagnostics.set_test_output(
            "PyAutoGUI ready" if ready else "PyAutoGUI unavailable"
        )

    def _test_keyboard(self) -> None:
        self.page_diagnostics.set_test_output(
            "Keyboard path uses PyAutoGUI type_text (enable live mode to send keys)."
        )

    def _test_mic(self) -> None:
        self.speech.warm_up()
        self.page_diagnostics.set_test_output("Microphone warm-up requested. Say DAI or use Speak.")
        self.toast.show("Mic warm-up started", "info")

    def shutdown(self) -> None:
        self._stop_dai_listener()
        for worker in (self._command_worker, self._workflow_worker, self._speech_worker):
            if worker is not None and worker.isRunning():
                if hasattr(worker, "stop"):
                    worker.stop()
                worker.wait(1200)

    def _start_dai_listener(self) -> None:
        if self._dai_thread is not None and self._dai_thread.isRunning():
            if self._dai_overlay:
                self._dai_overlay.show()
                self._dai_overlay.raise_()
            return
        self._dai_thread = None
        if self._dai_overlay is None:
            self._dai_overlay = DaiOverlay()
            self._dai_overlay.close_requested.connect(self._hide_dai_overlay)
            self._dai_overlay.retry_requested.connect(self._start_dai_listener)
            self._dai_overlay.place_corner()
        self._dai_overlay.show()
        self._dai_overlay.set_mode("sleep", "Preparing offline speech…")
        self._dai_setup = DaiSetupThread(self.config, parent=self)
        self._dai_setup.status.connect(
            lambda m: self._dai_overlay.set_mode("sleep", m) if self._dai_overlay else None
        )
        self._dai_setup.failed.connect(self._on_dai_setup_fail)
        self._dai_setup.ready.connect(self._on_dai_model_ready)
        self._dai_setup.start()

    def _on_dai_setup_fail(self, message: str) -> None:
        if self._dai_overlay:
            self._dai_overlay.set_mode("error", message)
        self.page_voice.set_status_message(f"DAI overlay: {message}")

    def _on_dai_model_ready(self, model_path: str) -> None:
        self._dai_thread = DaiMicThread(model_path, parent=self)
        self._dai_thread.heard.connect(self._on_dai_heard)
        self._dai_thread.partial.connect(self._on_dai_partial)
        self._dai_thread.status.connect(
            lambda m: self._dai_overlay.set_mode(
                "active" if self._dai_active else "sleep", m
            )
            if self._dai_overlay
            else None
        )
        self._dai_thread.failed.connect(self._on_dai_setup_fail)
        self._dai_thread.start()
        if self._dai_overlay:
            self._dai_overlay.set_mode("sleep", "Say “DAI” to start")
        self.page_voice.set_engine_label("Engine: Offline DAI — say DAI (no internet)")

    def _on_dai_partial(self, text: str) -> None:
        if self._dai_overlay and text:
            if self._dai_active:
                self._dai_overlay.set_mode("active", f"STT: {text}")
            elif classify_utterance(text, session_active=False)[0] == "wake":
                self._dai_overlay.set_mode("sleep", "Hearing DAI…")

    def _on_dai_heard(self, text: str) -> None:
        now = time.monotonic()
        kind, command = classify_utterance(text, session_active=self._dai_active)
        if self._dai_overlay and kind != "ignore":
            self._dai_overlay.hint.setText(f"Heard: {text}")
        if kind == "ignore":
            return
        if command and command == self._dai_last_cmd and (now - self._dai_last_at) < 1.1:
            return
        self._dai_last_at = now
        if kind == "close":
            self._dai_active = False
            self._dai_queue.clear()
            if self._dai_thread is not None:
                self._dai_thread.set_session_active(False)
            if self._dai_overlay:
                self._dai_overlay.set_mode("sleep", "Session closed. Say “DAI” to start")
            self.page_voice.set_status_message("DAI session closed")
            return
        if kind == "minimize":
            self._dai_active = True
            if self._dai_thread is not None:
                self._dai_thread.set_session_active(True)
            self.showMinimized()
            if self._dai_overlay:
                self._dai_overlay.show()
                self._dai_overlay.set_mode("active", "Minimized — say commands")
            return
        if kind == "restore":
            self._dai_active = True
            if self._dai_thread is not None:
                self._dai_thread.set_session_active(True)
            self.showNormal()
            self.raise_()
            if self._dai_overlay:
                self._dai_overlay.set_mode("active", "Restored")
            return
        if kind == "repeat":
            if self._dai_last_cmd:
                self._run_command(self._dai_last_cmd, source="voice", live_desktop=True)
            return
        if kind == "wake":
            self._dai_active = True
            if self._dai_thread is not None:
                self._dai_thread.set_session_active(True)
            if self._dai_overlay:
                self._dai_overlay.set_mode(
                    "active",
                    f"STT → {command}" if command else "Listening — speak, I will STT + execute",
                )
            if command:
                self._run_command(command, source="voice", live_desktop=True)
            return
        if kind == "command" and command:
            self._run_command(command, source="voice", live_desktop=True)

    def _hide_dai_overlay(self) -> None:
        if self._dai_overlay:
            self._dai_overlay.hide()

    def _stop_dai_listener(self) -> None:
        self._dai_active = False
        if self._dai_thread is not None:
            self._dai_thread.stop()
            self._dai_thread.wait(1500)
            self._dai_thread = None
        if self._dai_overlay is not None:
            self._dai_overlay.close()
            self._dai_overlay = None
