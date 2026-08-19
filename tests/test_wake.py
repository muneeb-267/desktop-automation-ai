from src.speech.wake import classify_utterance, is_close_phrase, is_wake_phrase, strip_wake


def test_wake_variants():
    assert is_wake_phrase("DAI")
    assert is_wake_phrase("hey dai")
    assert is_wake_phrase("die")
    assert not is_wake_phrase("open chrome")
    assert not is_wake_phrase("have a nice day")


def test_close_phrase():
    assert is_close_phrase("DAI close now")
    assert is_close_phrase("die close now")
    assert is_close_phrase("close now", session_active=True)
    assert not is_close_phrase("close the window")


def test_classify_session():
    kind, cmd = classify_utterance("DAI", session_active=False)
    assert kind == "wake"
    assert cmd == ""

    kind, cmd = classify_utterance("DAI click login", session_active=False)
    assert kind == "wake"
    assert "click" in cmd and "login" in cmd

    kind, cmd = classify_utterance("click submit", session_active=True)
    assert kind == "command"
    assert cmd.startswith("click")

    kind, cmd = classify_utterance("click submit", session_active=False)
    assert kind == "ignore"

    kind, cmd = classify_utterance("DAI close now", session_active=True)
    assert kind == "close"


def test_strip_wake():
    assert strip_wake("DAI open notepad") == "open notepad"
    assert strip_wake("hey dai click login") == "click login"
