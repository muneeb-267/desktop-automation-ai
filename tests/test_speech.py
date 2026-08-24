"""Speech helpers tests (no mic required)."""

from src.speech.cloud_stt import resolve_api_keys, pcm_to_wav_bytes
from src.speech.recognizer import SpeechService


def test_resolve_api_keys_empty():
    keys = resolve_api_keys({"speech": {}})
    assert keys["openai"] == ""
    assert keys["gemini"] == ""


def test_pcm_to_wav_roundtrip_header():
    wav = pcm_to_wav_bytes(b"\x00\x00" * 160, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    assert b"WAVE" in wav[:16]


def test_speech_service_always_available():
    svc = SpeechService({"speech": {"engine": "browser"}})
    assert svc.available is True


def test_listen_does_not_require_pyaudio(monkeypatch):
    svc = SpeechService({"speech": {"engine": "auto"}})
    svc._has_pyaudio = False

    def chrome_fail(*_a, **_k):
        raise RuntimeError("Allow microphone in Chrome")

    monkeypatch.setattr(svc, "_listen_browser", chrome_fail)
    try:
        svc.listen_once()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        msg = str(exc).lower()
        assert "no microphone library" not in msg
        assert "chrome" in msg or "edge" in msg or "execute" in msg


def test_dai_chrome_page_is_continuous():
    from src.speech.dai_chrome import _HTML

    assert "continuous = true" in _HTML
    assert "maxAlternatives = 5" in _HTML
    assert "DAI wakeup" in _HTML
