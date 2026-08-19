"""Always-on Vosk microphone thread (offline)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal


class DaiSetupThread(QThread):
    """Load or download the offline model, then report the folder path."""

    ready = pyqtSignal(str)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, config: Optional[dict] = None, parent=None) -> None:
        super().__init__(parent)
        self.config = config or {}

    def run(self) -> None:
        try:
            from src.speech.offline_stt import (
                default_model_dir,
                ensure_model,
                ensure_offline_packages,
            )

            ensure_offline_packages(status_cb=self.status.emit)
            path = ensure_model(
                default_model_dir(self.config),
                status_cb=self.status.emit,
                allow_download=True,
            )
            self.ready.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class DaiMicThread(QThread):
    """Continuously listen and emit finalized phrases (and wake-ish partials)."""

    heard = pyqtSignal(str)
    partial = pyqtSignal(str)
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.model_path = Path(model_path)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        from src.speech.mic_device import (
            friendly_mic_error,
            open_best_input_stream,
            read_vosk_chunk,
        )

        try:
            from vosk import KaldiRecognizer, Model
            import sounddevice as sd
        except ImportError:
            self.failed.emit(
                "Offline mic packages missing (vosk/sounddevice). Run FIX_INSTALL.bat."
            )
            return

        stream = None
        try:
            self.status.emit("Loading offline speech…")
            model = Model(str(self.model_path))
            rec = KaldiRecognizer(model, 16000)
            rec.SetWords(False)
            self.status.emit("Opening microphone…")
            stream, cap_rate, channels = open_best_input_stream(sd)
            self.status.emit("Mic on — say DAI")
            last_partial = ""
            while not self._stop:
                raw = read_vosk_chunk(stream, cap_rate, channels)
                if rec.AcceptWaveform(raw):
                    payload = json.loads(rec.Result() or "{}")
                    text = " ".join(str(payload.get("text") or "").split())
                    if text:
                        self.heard.emit(text)
                    last_partial = ""
                else:
                    partial = json.loads(rec.PartialResult() or "{}").get("partial") or ""
                    partial = " ".join(str(partial).split())
                    if partial and partial != last_partial:
                        last_partial = partial
                        self.partial.emit(partial)
        except Exception as exc:
            self.failed.emit(friendly_mic_error(exc))
        finally:
            if stream is not None:
                try:
                    stream.stop()
                except Exception:
                    pass
                try:
                    stream.close()
                except Exception:
                    pass
