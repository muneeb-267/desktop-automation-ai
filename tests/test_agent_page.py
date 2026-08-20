from src.gui.pages.agent_page import AgentPage


def test_agent_page_plan_slot_is_not_shadowed():
    """Regression: storing the plan in self._plan hid the Qt slot and crashed startup."""
    assert callable(AgentPage._emit_plan)
    assert callable(AgentPage._emit_run)
    names = AgentPage.__init__.__code__.co_names
    assert "_plan_data" in names
    assert "_emit_plan" in names
    assert "_emit_run" in names
