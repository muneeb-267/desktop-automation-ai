from src.nlp.engine import NLPEngine
from src.nlp.planner import CommandPlanner, suggest_commands


def test_planner_expands_search_and_first_result():
    nlp = NLPEngine()
    parsed = nlp.parse(
        "Open Chrome, search for today's weather, then open the first result"
    )
    plan = CommandPlanner().plan(parsed, parsed.raw_text)
    intents = [s.intent for s in plan.steps]
    assert "open_app" in intents
    assert "search_web" in intents
    assert "click_text" in intents
    assert "verify_screen" in intents
    assert plan.estimated_s > 0
    assert 0 <= plan.confidence <= 1


def test_planner_unknown_offers_suggestions():
    nlp = NLPEngine()
    parsed = nlp.parse("do the thing from yesterday please")
    plan = CommandPlanner().plan(parsed, parsed.raw_text)
    assert plan.needs_clarification
    assert plan.suggestions
    assert any("Chrome" in s or "Open" in s for s in plan.suggestions)


def test_suggest_commands_ranks_overlap():
    hits = suggest_commands("open chrome search")
    assert hits[0].lower().startswith("open chrome") or "chrome" in hits[0].lower()


def test_planner_wait_after_open():
    nlp = NLPEngine()
    parsed = nlp.parse("Open notepad")
    plan = CommandPlanner().plan(parsed)
    kinds = [s.kind for s in plan.steps]
    assert "wait" in kinds or any(s.intent == "wait" for s in plan.steps)
