"""Always-on Vosk microphone thread (offline)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

from src.speech.wake import WAKE_GRAMMAR, looks_complete_command


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
    """Continuously listen and emit finalized phrases (and stable command partials)."""

    heard = pyqtSignal(str)
    partial = pyqtSignal(str)
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.model_path = Path(model_path)
        self._stop = False
        self._session_active = False

    def stop(self) -> None:
        self._stop = True

    def set_session_active(self, active: bool) -> None:
        self._session_active = bool(active)

    def run(self) -> None:
        from src.speech.mic_device import (
            friendly_mic_error,
            open_best_input_stream,
            read_vosk_chunk,
        )

        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
            import sounddevice as sd

            SetLogLevel(-1)
        except ImportError:
            self.failed.emit(
                "Offline mic packages missing (vosk/sounddevice). Run FIX_INSTALL.bat."
            )
            return

        stream = None
        try:
            self.status.emit("Loading offline speech…")
            model = Model(str(self.model_path))

            def make_recs():
                wake = KaldiRecognizer(model, 16000, WAKE_GRAMMAR)
                cmd = KaldiRecognizer(model, 16000)
                wake.SetWords(False)
                cmd.SetWords(False)
                try:
                    cmd.SetMaxAlternatives(3)
                except Exception:
                    pass
                return wake, cmd

            def pick_text(payload):
                texts = []
                for alt in payload.get("alternatives") or []:
                    piece = " ".join(str((alt or {}).get("text") or "").split())
                    if piece:
                        texts.append(piece)
                main = " ".join(str(payload.get("text") or "").split())
                if main:
                    texts.insert(0, main)
                seen = set()
                uniq = []
                for piece in texts:
                    key = piece.lower()
                    if key not in seen:
                        seen.add(key)
                        uniq.append(piece)
                return uniq[0] if uniq else ""

            rec_wake, rec_cmd = make_recs()
            self.status.emit("Opening microphone…")
            stream, cap_rate, channels = open_best_input_stream(sd)
            self.status.emit("Mic on — say DAI")
            last_partial = ""
            last_emitted = ""
            stable_text = ""
            stable_n = 0
            last_session = False
            while not self._stop:
                session = self._session_active
                if session != last_session:
                    rec_wake, rec_cmd = make_recs()
                    last_session = session
                    last_partial = ""
                    stable_n = 0
                    last_emitted = ""
                rec = rec_cmd if session else rec_wake
                raw = read_vosk_chunk(stream, cap_rate, channels, seconds=0.08)
                if rec.AcceptWaveform(raw):
                    payload = json.loads(rec.Result() or "{}")
                    text = pick_text(payload)
                    if text and text.lower() != last_emitted.lower():
                        last_emitted = text
                        self.heard.emit(text)
                    last_partial = ""
                    stable_n = 0
                else:
                    partial = json.loads(rec.PartialResult() or "{}").get("partial") or ""
                    partial = " ".join(str(partial).split())
                    if partial and partial != last_partial:
                        last_partial = partial
                        self.partial.emit(partial)
                    if session and partial and looks_complete_command(partial):
                        if partial == stable_text:
                            stable_n += 1
                        else:
                            stable_text = partial
                            stable_n = 1
                        # ~160ms of the same complete phrase → run without waiting for silence
                        if stable_n >= 2 and partial.lower() != last_emitted.lower():
                            last_emitted = partial
                            self.heard.emit(partial)
                            rec_wake, rec_cmd = make_recs()
                            last_session = session
                            stable_n = 0
                    else:
                        stable_n = 0
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
