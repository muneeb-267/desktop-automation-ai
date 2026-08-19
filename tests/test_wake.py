from src.speech.wake import classify_utterance, is_close_phrase, is_wake_phrase, strip_wake


def test_wake_variants():
    assert is_wake_phrase("DAI")
    assert is_wake_phrase("hey dai")
    assert is_wake_phrase("die")
    assert not is_wake_phrase("open chrome")
    assert not is_wake_phrase("have a nice day")
    assert is_wake_phrase("they")
    assert not is_wake_phrase("copy file they sent to desktop")


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


def test_minimize_and_repeat():
    kind, _ = classify_utterance("DAI minimize the screen", session_active=False)
    assert kind == "minimize"
    kind, _ = classify_utterance("minimize", session_active=True)
    assert kind == "minimize"
    kind, _ = classify_utterance("again", session_active=True)
    assert kind == "repeat"


def test_clean_fillers():
    from src.speech.wake import clean_spoken_command

    assert clean_spoken_command("please open chrome") == "open chrome"
    assert "click" in clean_spoken_command("can you click login")


def test_complete_command():
    from src.speech.wake import looks_complete_command

    assert looks_complete_command("click login")
    assert looks_complete_command("open notepad")
    assert looks_complete_command("minimize the screen")
    assert not looks_complete_command("click")
