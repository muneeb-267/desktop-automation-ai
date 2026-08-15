"""Settings screen."""

from __future__ import annotations

from typing import Any, Dict

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QCheckBox,
    QDoubleSpinBox,
    QSlider,
    QPushButton,
    QLineEdit,
    QFormLayout,
)


class SettingsPage(QWidget):
    save_requested = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)

        title = QLabel("System Settings")
        title.setObjectName("pageTitle")
        sub = QLabel("Configure safety, speech sensitivity, and local execution options.")
        sub.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(sub)

        card = QFrame()
        card.setObjectName("panelCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(12)

        self.dry_run = QCheckBox("Dry-run (safe mode — no real mouse/keyboard)")
        self.dry_run.setChecked(False)
        self.failsafe = QCheckBox("Fail-safe (move mouse to corner to abort)")
        self.failsafe.setChecked(True)
        tip = QLabel("Leave dry-run OFF to actually open Chrome, click, type, and search.")
        tip.setObjectName("pageSubtitle")

        pause_row = QHBoxLayout()
        pause_row.addWidget(QLabel("Action pause (sec)"))
        self.pause = QDoubleSpinBox()
        self.pause.setRange(0.02, 3.0)
        self.pause.setSingleStep(0.02)
        self.pause.setValue(0.12)
        pause_row.addWidget(self.pause)
        pause_row.addStretch()

        cl.addWidget(self.dry_run)
        cl.addWidget(tip)
        cl.addWidget(self.failsafe)
        cl.addLayout(pause_row)
        cl.addWidget(QLabel("Voice Sensitivity"))
        self.voice = QSlider(Qt.Horizontal)
        self.voice.setRange(10, 100)
        self.voice.setValue(70)
        cl.addWidget(self.voice)
        self.voice_lbl = QLabel("0.70")
        self.voice.valueChanged.connect(lambda v: self.voice_lbl.setText(f"{v/100:.2f}"))
        cl.addWidget(self.voice_lbl)

        cl.addWidget(QLabel("Cloud speech (optional — faster/accurate mic transcription)"))
        keys = QFormLayout()
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("OPENAI_API_KEY for Whisper")
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        self.gemini_key.setPlaceholderText("GEMINI_API_KEY for Gemini audio")
        keys.addRow("OpenAI", self.openai_key)
        keys.addRow("Gemini", self.gemini_key)
        cl.addLayout(keys)
        key_tip = QLabel(
            "Leave blank to use Chrome voice (default). Keys also work via environment variables."
        )
        key_tip.setObjectName("pageSubtitle")
        key_tip.setWordWrap(True)
        cl.addWidget(key_tip)

        save = QPushButton("Apply & Return")
        save.clicked.connect(self._save)
        cl.addWidget(save)
        root.addWidget(card)
        root.addStretch()

        chip = QLabel("● SYSTEM_READY")
        chip.setObjectName("statusChip")
        root.addWidget(chip, 0, Qt.AlignLeft)

    def apply_conf(self, conf: Dict[str, Any]) -> None:
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
            "dry_run": "1" if self.dry_run.isChecked() else "0",
            "failsafe": "1" if self.failsafe.isChecked() else "0",
            "pause_seconds": str(self.pause.value()),
            "voice_sensitivity": f"{self.voice.value()/100:.2f}",
            "mic_sensitivity": f"{self.voice.value()/100:.2f}",
        }
        if self.openai_key.text().strip():
            payload["openai_api_key"] = self.openai_key.text().strip()
        if self.gemini_key.text().strip():
            payload["gemini_api_key"] = self.gemini_key.text().strip()
        self.save_requested.emit(payload)
