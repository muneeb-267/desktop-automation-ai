"""Settings — theme, safety, voice, cloud STT."""

from __future__ import annotations

from typing import Any, Dict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SettingsPage(QWidget):
    save_requested = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        root = QVBoxLayout(host)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(14)

        title = QLabel("System Settings")
        title.setObjectName("pageTitle")
        sub = QLabel(
            "Configure theme, microphone sensitivity, and automation safety protocols."
        )
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(sub)

        card = QFrame()
        card.setObjectName("panelCard")
        card.setMaximumWidth(720)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 22, 24, 22)
        cl.setSpacing(18)

        # Appearance
        cl.addWidget(self._section("Appearance"))
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        theme_lbl = QLabel("Theme")
        theme_lbl.setMinimumWidth(140)
        self.theme = QComboBox()
        self.theme.addItems(["light", "dark"])
        self.theme.setMinimumWidth(160)
        self.theme.setMinimumHeight(34)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme)
        theme_row.addStretch(1)
        cl.addLayout(theme_row)

        # Safety
        cl.addWidget(self._section("Automation safety"))
        self.dry_run = QCheckBox("Dry-run (safe mode — no real mouse/keyboard)")
        self.dry_run.setChecked(False)
        tip = QLabel(
            "Leave dry-run OFF to actually open Chrome, click, type, and search."
        )
        tip.setObjectName("pageSubtitle")
        tip.setWordWrap(True)
        tip.setContentsMargins(24, 0, 0, 0)
        self.failsafe = QCheckBox("Fail-safe (move mouse to corner to abort)")
        self.failsafe.setChecked(True)

        pause_row = QHBoxLayout()
        pause_row.setSpacing(12)
        pause_lbl = QLabel("Action pause (sec)")
        pause_lbl.setMinimumWidth(140)
        self.pause = QDoubleSpinBox()
        self.pause.setRange(0.02, 3.0)
        self.pause.setSingleStep(0.02)
        self.pause.setValue(0.04)
        self.pause.setMinimumWidth(100)
        self.pause.setMinimumHeight(34)
        pause_row.addWidget(pause_lbl)
        pause_row.addWidget(self.pause)
        pause_row.addStretch(1)

        cl.addWidget(self.dry_run)
        cl.addWidget(tip)
        cl.addWidget(self.failsafe)
        cl.addLayout(pause_row)

        # Voice
        cl.addWidget(self._section("Voice / microphone"))
        sens_head = QHBoxLayout()
        sens_head.addWidget(QLabel("Sensitivity"))
        sens_head.addStretch(1)
        self.voice_lbl = QLabel("0.70")
        self.voice_lbl.setObjectName("pageSubtitle")
        sens_head.addWidget(self.voice_lbl)
        cl.addLayout(sens_head)

        self.voice = QSlider(Qt.Horizontal)
        self.voice.setRange(10, 100)
        self.voice.setValue(70)
        self.voice.setMinimumHeight(28)
        self.voice.valueChanged.connect(
            lambda v: self.voice_lbl.setText(f"{v / 100:.2f}")
        )
        cl.addWidget(self.voice)
        range_row = QHBoxLayout()
        lo = QLabel("0.10")
        lo.setObjectName("pageSubtitle")
        hi = QLabel("1.00")
        hi.setObjectName("pageSubtitle")
        range_row.addWidget(lo)
        range_row.addStretch(1)
        range_row.addWidget(hi)
        cl.addLayout(range_row)

        # Cloud
        cl.addWidget(self._section("Cloud speech (optional)"))
        cloud_tip = QLabel(
            "Leave blank to use Chrome voice (default). Keys also work via environment variables."
        )
        cloud_tip.setObjectName("pageSubtitle")
        cloud_tip.setWordWrap(True)
        cl.addWidget(cloud_tip)

        keys = QFormLayout()
        keys.setSpacing(10)
        keys.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("OPENAI_API_KEY for Whisper")
        self.openai_key.setMinimumHeight(34)
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        self.gemini_key.setPlaceholderText("GEMINI_API_KEY for Gemini audio")
        self.gemini_key.setMinimumHeight(34)
        keys.addRow("OpenAI", self.openai_key)
        keys.addRow("Gemini", self.gemini_key)
        cl.addLayout(keys)

        # Actions — avoid bare "&" (Qt mnemonic); use separate buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        save = QPushButton("Apply and return")
        save.setObjectName("btnPrimary")
        save.setMinimumHeight(38)
        save.setMinimumWidth(140)
        save.clicked.connect(self._save)
        actions.addWidget(save)
        actions.addStretch(1)
        cl.addLayout(actions)

        root.addWidget(card)
        root.addStretch(1)

        scroll.setWidget(host)
        outer.addWidget(scroll)

    def _section(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("sectionTitle")
        return lab

    def apply_conf(self, conf: Dict[str, Any]) -> None:
        theme = str(conf.get("theme", "light")).lower()
        idx = self.theme.findText(theme)
        self.theme.setCurrentIndex(idx if idx >= 0 else 0)
        self.dry_run.setChecked(str(conf.get("dry_run", "0")) in ("1", "true", "True"))
        self.failsafe.setChecked(str(conf.get("failsafe", "1")) in ("1", "true", "True"))
        self.pause.setValue(float(conf.get("pause_seconds", 0.04)))
        sens = float(conf.get("voice_sensitivity", conf.get("mic_sensitivity", 0.9)))
        self.voice.setValue(int(sens * 100))
        if conf.get("openai_api_key"):
            self.openai_key.setText(str(conf.get("openai_api_key")))
        if conf.get("gemini_api_key"):
            self.gemini_key.setText(str(conf.get("gemini_api_key")))

    def _save(self) -> None:
        payload = {
            "theme": self.theme.currentText(),
            "dry_run": "1" if self.dry_run.isChecked() else "0",
            "failsafe": "1" if self.failsafe.isChecked() else "0",
            "pause_seconds": str(self.pause.value()),
            "voice_sensitivity": f"{self.voice.value() / 100:.2f}",
            "mic_sensitivity": f"{self.voice.value() / 100:.2f}",
        }
        if self.openai_key.text().strip():
            payload["openai_api_key"] = self.openai_key.text().strip()
        if self.gemini_key.text().strip():
            payload["gemini_api_key"] = self.gemini_key.text().strip()
        self.save_requested.emit(payload)
