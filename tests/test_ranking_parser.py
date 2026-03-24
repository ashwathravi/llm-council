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

def test_missing_colon_in_marker():
    # If colon is missing, marker "FINAL RANKING:" isn't found, should fallback to whole text search
    text = """
    FINAL RANKING
    1. Response B
    2. Response A
    """
    # Since "FINAL RANKING:" (with colon) is not found, it uses the fallback which finds all Response [A-Z]
    assert parse_ranking_from_text(text) == ["Response B", "Response A"]

def test_duplicate_responses():
    # Test that duplicate mentions are preserved in the order they appear
    text = "FINAL RANKING: 1. Response A, 2. Response A, 3. Response B"
    assert parse_ranking_from_text(text) == ["Response A", "Response A", "Response B"]

def test_multiple_markers():
    # Test that the parser starts from the first "FINAL RANKING:" marker
    text = """
    FINAL RANKING:
    1. Response A

    Wait, I changed my mind.
    FINAL RANKING:
    1. Response B
    """
    # It finds everything after the FIRST "FINAL RANKING:"
    # numbered_matches will find "1. Response A" and "1. Response B"
    assert parse_ranking_from_text(text) == ["Response A", "Response B"]

def test_empty_ranking_section():
    # Ensure the parser returns an empty list if no "Response X" patterns are found after the marker
    text = "FINAL RANKING: No responses were good enough to rank."
    assert parse_ranking_from_text(text) == []

def test_lowercase_response_label():
    # Ensure "response a" is correctly normalized to "Response A"
    text = "FINAL RANKING: 1. response a, 2. Response B"
    assert parse_ranking_from_text(text) == ["Response A", "Response B"]
