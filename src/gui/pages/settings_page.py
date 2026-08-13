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
        self.dry_run.setChecked(True)
        self.failsafe = QCheckBox("Fail-safe (move mouse to corner to abort)")
        self.failsafe.setChecked(True)

        pause_row = QHBoxLayout()
        pause_row.addWidget(QLabel("Action pause (sec)"))
        self.pause = QDoubleSpinBox()
        self.pause.setRange(0.05, 3.0)
        self.pause.setSingleStep(0.05)
        self.pause.setValue(0.35)
        pause_row.addWidget(self.pause)
        pause_row.addStretch()

        cl.addWidget(self.dry_run)
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

        save = QPushButton("Apply & Return")
        save.clicked.connect(self._save)
        cl.addWidget(save)
        root.addWidget(card)
        root.addStretch()

        chip = QLabel("● SYSTEM_READY")
        chip.setObjectName("statusChip")
        root.addWidget(chip, 0, Qt.AlignLeft)

    def apply_conf(self, conf: Dict[str, Any]) -> None:
        self.dry_run.setChecked(str(conf.get("dry_run", "1")) in ("1", "true", "True"))
        self.failsafe.setChecked(str(conf.get("failsafe", "1")) in ("1", "true", "True"))
        self.pause.setValue(float(conf.get("pause_seconds", 0.35)))
        sens = float(conf.get("voice_sensitivity", conf.get("mic_sensitivity", 0.7)))
        self.voice.setValue(int(sens * 100))

    def _save(self) -> None:
        self.save_requested.emit(
            {
                "dry_run": "1" if self.dry_run.isChecked() else "0",
                "failsafe": "1" if self.failsafe.isChecked() else "0",
                "pause_seconds": str(self.pause.value()),
                "voice_sensitivity": f"{self.voice.value()/100:.2f}",
                "mic_sensitivity": f"{self.voice.value()/100:.2f}",
            }
        )
