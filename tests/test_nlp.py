from src.nlp.engine import NLPEngine


def test_open_app_and_search():
    engine = NLPEngine()
    parsed = engine.parse("Open Chrome and search weather")
    assert parsed.intent == "open_app"
    assert parsed.entities.get("app") == "chrome"
    assert len(parsed.steps) >= 2
    assert parsed.steps[1]["intent"] == "search_web"


def test_click_and_type():
    engine = NLPEngine()
    click = engine.parse("Click Login")
    assert click.intent == "click_text"
    assert "login" in click.entities.get("element", "").lower()

    typed = engine.parse('Type "hello world"')
    assert typed.intent == "type_text"
    assert "hello" in typed.entities.get("text", "").lower()


def test_wait_scroll_workflow():
    engine = NLPEngine()
    assert engine.parse("wait 2 seconds").intent == "wait"
    assert engine.parse("scroll down 5").entities.get("amount") == 5
    assert engine.parse("run workflow Open Notepad Demo").intent == "run_workflow"
