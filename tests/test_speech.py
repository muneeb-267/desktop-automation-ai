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
