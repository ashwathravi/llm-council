import pytest
from backend.council import parse_ranking_from_text

def test_standard_ranking():
    text = """
    Evaluation of responses:
    Response A is good.
    Response B is okay.

    FINAL RANKING:
    1. Response A
    2. Response B
    """
    assert parse_ranking_from_text(text) == ["Response A", "Response B"]

def test_unnumbered_ranking_section():
    text = """
    FINAL RANKING:
    Response B, Response A
    """
    assert parse_ranking_from_text(text) == ["Response B", "Response A"]

def test_no_final_ranking_section():
    text = "I prefer Response C over Response A and Response B."
    assert parse_ranking_from_text(text) == ["Response C", "Response A", "Response B"]

def test_extra_text_before_ranking():
    text = """
    Response A is first mentioned here.
    Now the official part:
    FINAL RANKING:
    1. Response B
    2. Response A
    """
    assert parse_ranking_from_text(text) == ["Response B", "Response A"]

def test_no_matches():
    text = "Everything was bad."
    assert parse_ranking_from_text(text) == []

def test_multiple_digits():
    text = """
    FINAL RANKING:
    1. Response A
    2. Response B
    3. Response C
    4. Response D
    5. Response E
    6. Response F
    7. Response G
    8. Response H
    9. Response I
    10. Response J
    """
    result = parse_ranking_from_text(text)
    assert "Response J" in result
    assert result[-1] == "Response J"

def test_case_sensitivity():
    text = """
    final ranking:
    1. response A
    2. response B
    """
    # Verify that parsing is case-insensitive and normalizes to "Response X"
    assert parse_ranking_from_text(text) == ["Response A", "Response B"]

def test_varied_whitespace():
    text = "FINAL RANKING: 1.Response A, 2.  Response B"
    assert parse_ranking_from_text(text) == ["Response A", "Response B"]
