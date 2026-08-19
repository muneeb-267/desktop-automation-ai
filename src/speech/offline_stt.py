"""Offline speech (Vosk) — works with no internet after the model is on disk."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen

from src.config import ROOT_DIR

VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_MODEL_URL = (
    f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
)


def default_model_dir(config: Optional[dict] = None) -> Path:
    rel = "data/models"
    if config:
        rel = str((config.get("paths") or {}).get("models_dir") or rel)
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path / VOSK_MODEL_NAME


def model_is_ready(model_dir: Path) -> bool:
    # Vosk models contain am/ + conf/ (or a nested folder with those)
    if (model_dir / "am").is_dir() and (model_dir / "conf").is_dir():
        return True
    if not model_dir.is_dir():
        return False
    for child in model_dir.iterdir():
        if child.is_dir() and (child / "am").is_dir() and (child / "conf").is_dir():
            return True
    return False


def resolve_model_path(model_dir: Path) -> Optional[Path]:
    if (model_dir / "am").is_dir():
        return model_dir
    if model_dir.is_dir():
        for child in model_dir.iterdir():
            if child.is_dir() and (child / "am").is_dir():
                return child
    return None


def ensure_model(
    model_dir: Path,
    *,
    status_cb: Optional[Callable[[str], None]] = None,
    allow_download: bool = True,
) -> Path:
    emit = status_cb or (lambda _m: None)
    ready = resolve_model_path(model_dir)
    if ready:
        return ready
    if not allow_download:
        raise RuntimeError(
            "Offline speech model is not installed. Connect once and run FIX_INSTALL.bat."
        )
    emit("Downloading offline speech model (one-time, ~40 MB)…")
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    zip_path = model_dir.parent / f"{VOSK_MODEL_NAME}.zip"
    try:
        with urlopen(VOSK_MODEL_URL, timeout=60) as resp, zip_path.open("wb") as fh:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
        emit("Unpacking speech model…")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(model_dir.parent)
    except Exception as exc:
        raise RuntimeError(
            "Could not download the offline speech model. "
            "Connect to the internet once, then retry. "
            f"({exc})"
        ) from exc
    finally:
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass
    ready = resolve_model_path(model_dir)
    if not ready:
        # extracted folder may already be named correctly
        ready = resolve_model_path(model_dir.parent / VOSK_MODEL_NAME)
    if not ready:
        raise RuntimeError("Speech model extract failed.")
    emit("Offline speech model ready.")
    return ready


def listen_utterance(
    model_dir: Path,
    *,
    seconds: float = 6.0,
    samplerate: int = 16000,
    status_cb: Optional[Callable[[str], None]] = None,
) -> str:
    """Capture one phrase offline (for the Speak button)."""
    import time

    emit = status_cb or (lambda _m: None)
    try:
        from vosk import KaldiRecognizer, Model
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "Offline speech packages missing. Run FIX_INSTALL.bat (vosk + sounddevice)."
        ) from exc

    path = resolve_model_path(model_dir)
    if not path:
        path = ensure_model(model_dir, status_cb=emit, allow_download=True)
    emit("Listening (offline)… speak now")
    model = Model(str(path))
    rec = KaldiRecognizer(model, samplerate)
    rec.SetWords(False)
    deadline = time.time() + max(2.5, float(seconds))
    last_partial = ""
    with sd.RawInputStream(
        samplerate=samplerate, blocksize=4000, dtype="int16", channels=1
    ) as stream:
        while time.time() < deadline:
            data, _overflow = stream.read(4000)
            raw = bytes(data)
            if rec.AcceptWaveform(raw):
                payload = json.loads(rec.Result() or "{}")
                text = " ".join(str(payload.get("text") or "").split())
                if text:
                    return text
            else:
                partial = json.loads(rec.PartialResult() or "{}").get("partial") or ""
                if partial and partial != last_partial:
                    last_partial = partial
                    emit(f"Hearing: {partial}")
    payload = json.loads(rec.FinalResult() or "{}")
    text = " ".join(str(payload.get("text") or "").split())
    if not text:
        raise RuntimeError("Didn’t catch speech. Say DAI, then your command.")
    return text
