"""Automation start/stop & parameter configuration panel."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QSlider,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QTabWidget,
    QSpinBox,
    QDoubleSpinBox,
    QSizePolicy,
)


class ControlsWidget(QWidget):
    """Right-panel control tabs for tasks, OCR, and execution triggers."""

    start_requested = pyqtSignal(dict)  # config payload
    stop_requested = pyqtSignal()
    capture_toggled = pyqtSignal(bool)
    config_changed = pyqtSignal(dict)

    TASKS = [
        "Click Target",
        "Type Text",
        "OCR Search & Click",
        "Wait for Element",
        "Screenshot Region",
        "Hotkey Sequence",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("controlsPanel")
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._running = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("CONTROLS")
        title.setObjectName("panelHeader")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_task_tab(), "Task")
        self.tabs.addTab(self._build_ocr_tab(), "OCR")
        self.tabs.addTab(self._build_params_tab(), "Params")
        root.addWidget(self.tabs, stretch=1)

        # Execution triggers
        triggers = QHBoxLayout()
        triggers.setSpacing(8)

        self.btn_capture = QPushButton("Start Capture")
        self.btn_capture.setObjectName("btnQuick")
        self.btn_capture.setCheckable(True)
        self.btn_capture.clicked.connect(self._on_capture_toggle)

        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._on_start)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)

        triggers.addWidget(self.btn_capture)
        triggers.addWidget(self.btn_start, stretch=1)
        triggers.addWidget(self.btn_stop, stretch=1)
        root.addLayout(triggers)

        self._progress_label = QLabel("Ready")
        self._progress_label.setObjectName("targetInfo")
        self._progress_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self._progress_label)

    def _build_task_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.task_combo = QComboBox()
        self.task_combo.addItems(self.TASKS)
        self.task_combo.setCurrentIndex(2)  # OCR Search & Click
        self.task_combo.currentTextChanged.connect(self._emit_config)
        form.addRow("Task", self.task_combo)

        self.region_combo = QComboBox()
        self.region_combo.addItems(
            ["Full Screen", "Active Window", "Custom Region", "Primary Monitor"]
        )
        self.region_combo.currentTextChanged.connect(self._emit_config)
        form.addRow("Region", self.region_combo)

        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        self.repeat_spin.valueChanged.connect(self._emit_config)
        form.addRow("Repeat", self.repeat_spin)

        layout.addLayout(form)

        opts = QGroupBox("Options")
        opts_layout = QVBoxLayout(opts)
        self.chk_dry_run = QCheckBox("Dry run (no mouse/keyboard)")
        self.chk_dry_run.setChecked(True)
        self.chk_dry_run.toggled.connect(self._emit_config)
        self.chk_highlight = QCheckBox("Highlight matches on feed")
        self.chk_highlight.setChecked(True)
        self.chk_highlight.toggled.connect(self._emit_config)
        self.chk_fail_safe = QCheckBox("Fail-safe (corner abort)")
        self.chk_fail_safe.setChecked(True)
        self.chk_fail_safe.toggled.connect(self._emit_config)
        opts_layout.addWidget(self.chk_dry_run)
        opts_layout.addWidget(self.chk_highlight)
        opts_layout.addWidget(self.chk_fail_safe)
        layout.addWidget(opts)

        layout.addStretch()
        return page

    def _build_ocr_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.ocr_input = QLineEdit()
        self.ocr_input.setPlaceholderText("Search target string…")
        self.ocr_input.setText("Submit")
        self.ocr_input.textChanged.connect(self._emit_config)
        form.addRow("Target", self.ocr_input)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["eng", "eng+osd", "fra", "deu", "spa"])
        self.lang_combo.currentTextChanged.connect(self._emit_config)
        form.addRow("Language", self.lang_combo)

        self.match_mode = QComboBox()
        self.match_mode.addItems(["Contains", "Exact", "Regex", "Fuzzy"])
        self.match_mode.currentTextChanged.connect(self._emit_config)
        form.addRow("Match", self.match_mode)

        layout.addLayout(form)

        conf_group = QGroupBox("Confidence Threshold")
        conf_layout = QVBoxLayout(conf_group)

        row = QHBoxLayout()
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(10, 100)
        self.conf_slider.setValue(80)
        self.conf_slider.setTickInterval(10)
        self.conf_slider.setTickPosition(QSlider.TicksBelow)
        self.conf_value = QLabel("0.80")
        self.conf_value.setObjectName("targetInfo")
        self.conf_value.setMinimumWidth(36)
        self.conf_slider.valueChanged.connect(self._on_conf_changed)
        row.addWidget(self.conf_slider)
        row.addWidget(self.conf_value)
        conf_layout.addLayout(row)

        layout.addWidget(conf_group)

        hint = QLabel(
            "OCR will scan the selected region for the target string "
            "and click the best match above the confidence floor."
        )
        hint.setWordWrap(True)
        hint.setObjectName("feedPlaceholder")
        layout.addWidget(hint)
        layout.addStretch()
        return page

    def _build_params_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.5)
        self.delay_spin.setSuffix(" s")
        self.delay_spin.valueChanged.connect(self._emit_config)
        form.addRow("Action delay", self.delay_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" s")
        self.timeout_spin.valueChanged.connect(self._emit_config)
        form.addRow("Timeout", self.timeout_spin)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 20)
        self.retry_spin.setValue(3)
        self.retry_spin.valueChanged.connect(self._emit_config)
        form.addRow("Retries", self.retry_spin)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(100)
        self.scale_value = QLabel("100%")
        self.scale_value.setObjectName("targetInfo")
        self.scale_slider.valueChanged.connect(self._on_scale_changed)

        scale_row = QHBoxLayout()
        scale_row.addWidget(self.scale_slider)
        scale_row.addWidget(self.scale_value)
        form.addRow("UI scale", scale_row)

        layout.addLayout(form)
        layout.addStretch()
        return page

    # ── Public helpers ────────────────────────────────────────

    def get_config(self) -> dict:
        return {
            "task": self.task_combo.currentText(),
            "region": self.region_combo.currentText(),
            "repeat": self.repeat_spin.value(),
            "dry_run": self.chk_dry_run.isChecked(),
            "highlight": self.chk_highlight.isChecked(),
            "fail_safe": self.chk_fail_safe.isChecked(),
            "ocr_target": self.ocr_input.text().strip(),
            "ocr_lang": self.lang_combo.currentText(),
            "match_mode": self.match_mode.currentText(),
            "confidence": self.conf_slider.value() / 100.0,
            "action_delay": self.delay_spin.value(),
            "timeout": self.timeout_spin.value(),
            "retries": self.retry_spin.value(),
            "ui_scale": self.scale_slider.value() / 100.0,
        }

    def set_running(self, running: bool) -> None:
        self._running = running
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.tabs.setEnabled(not running)
        if running:
            self._progress_label.setText("Running…")
        else:
            self._progress_label.setText("Ready")

    def set_progress(self, pct: int) -> None:
        self._progress_label.setText(f"Progress: {pct}%")

    # ── Internal slots ────────────────────────────────────────

    def _on_conf_changed(self, value: int) -> None:
        self.conf_value.setText(f"{value / 100:.2f}")
        self._emit_config()

    def _on_scale_changed(self, value: int) -> None:
        self.scale_value.setText(f"{value}%")
        self._emit_config()

    def _emit_config(self, *_args) -> None:
        self.config_changed.emit(self.get_config())

    def _on_capture_toggle(self, checked: bool) -> None:
        self.btn_capture.setText("Stop Capture" if checked else "Start Capture")
        self.btn_capture.setProperty("active", "true" if checked else "false")
        self.btn_capture.style().unpolish(self.btn_capture)
        self.btn_capture.style().polish(self.btn_capture)
        self.capture_toggled.emit(checked)

    def _on_start(self) -> None:
        self.start_requested.emit(self.get_config())

    def _on_stop(self) -> None:
        self.stop_requested.emit()
