from src.vision.search_result import (
    FIRST_RESULT_ELEMENT,
    is_first_result_phrase,
    pick_first_search_result,
    text_matches_query,
)


def test_first_result_phrases():
    assert is_first_result_phrase("click on the first result")
    assert is_first_result_phrase("open the first result")
    assert is_first_result_phrase("first result")
    assert is_first_result_phrase(FIRST_RESULT_ELEMENT)
    assert not is_first_result_phrase("click login")


def test_short_ocr_words_do_not_match_long_query():
    assert text_matches_query("the", "the first result") is False
    assert text_matches_query("Login", "login") is True
    assert text_matches_query("Login With Odoo", "login with odoo") is True
    assert text_matches_query("login With Microsoft", "login with microsoft") is True
    assert text_matches_query("Microsoft", "login with microsoft") is True


def test_pick_first_google_result_title():
    words = [
        {"x": 40, "y": 40, "w": 80, "h": 18, "label": "Google", "line": 1, "block": 1, "conf": 90},
        {"x": 80, "y": 90, "w": 220, "h": 20, "label": "horizon.up.edu.k", "line": 2, "block": 1, "conf": 90},
        {"x": 80, "y": 210, "w": 90, "h": 16, "label": "AI", "line": 3, "block": 2, "conf": 80},
        {"x": 175, "y": 210, "w": 90, "h": 16, "label": "Overview", "line": 3, "block": 2, "conf": 80},
        {"x": 90, "y": 280, "w": 70, "h": 22, "label": "Login", "line": 4, "block": 3, "conf": 90},
        {"x": 165, "y": 280, "w": 50, "h": 22, "label": "With", "line": 4, "block": 3, "conf": 90},
        {"x": 220, "y": 280, "w": 70, "h": 22, "label": "Odoo", "line": 4, "block": 3, "conf": 90},
        {"x": 90, "y": 310, "w": 240, "h": 16, "label": "horizon.ucp.edu.pk", "line": 5, "block": 3, "conf": 88},
    ]
    hit = pick_first_search_result(words, width=1280, height=720)
    assert hit is not None
    assert "login" in hit["label"].lower()
    assert "odoo" in hit["label"].lower()
