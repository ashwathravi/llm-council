import httpx
import pytest
from backend.openrouter import _extract_error_message, _normalize_message_content

def test_extract_error_message_with_dict_message():
    """Test extracting error message from a standard dict error structure."""
    response = httpx.Response(400, json={"error": {"message": "Specific error message"}})
    assert _extract_error_message(response) == "Specific error message"

def test_extract_error_message_with_dict_error_key():
    """Test extracting error message when 'error' key is inside 'error' dict."""
    response = httpx.Response(400, json={"error": {"error": "Alternative error message"}})
    assert _extract_error_message(response) == "Alternative error message"

def test_extract_error_message_with_dict_fallback():
    """Test fallback to string representation of error dict if no message/error key exists."""
    response = httpx.Response(400, json={"error": {"code": 400}})
    assert _extract_error_message(response) == "{'code': 400}"

def test_extract_error_message_with_string_error():
    """Test extracting error message when 'error' is a simple string."""
    response = httpx.Response(400, json={"error": "String error message"})
    assert _extract_error_message(response) == "String error message"

def test_extract_error_message_with_top_level_message():
    """Test extracting message from top-level 'message' key."""
    response = httpx.Response(400, json={"message": "Top-level message"})
    assert _extract_error_message(response) == "Top-level message"

def test_extract_error_message_with_no_relevant_keys():
    """Test fallback to response text when JSON has no expected error fields."""
    content = b'{"foo": "bar"}'
    response = httpx.Response(400, content=content)
    assert _extract_error_message(response) == content.decode()

def test_extract_error_message_non_json():
    """Test fallback to response text when response is not valid JSON."""
    content = b"Non-JSON response"
    response = httpx.Response(400, content=content)
    assert _extract_error_message(response) == content.decode()

def test_extract_error_message_empty_body():
    """Test fallback to 'Unknown error' when response body is empty."""
    response = httpx.Response(400, content=b"")
    assert _extract_error_message(response) == "Unknown error"

def test_normalize_message_content_string():
    """Test normalization of simple string content."""
    assert _normalize_message_content({"content": "Hello world"}) == "Hello world"

def test_normalize_message_content_none():
    """Test normalization of None content to empty string."""
    assert _normalize_message_content({"content": None}) == ""

def test_normalize_message_content_list():
    """Test normalization of list content with various block structures."""
    message = {
        "content": [
            {"text": "Part 1"},
            {"text": {"value": "Part 2"}},
            {"text": {"text": "Part 3"}},
            {"other": "ignored"}
        ]
    }
    assert _normalize_message_content(message) == "Part 1\nPart 2\nPart 3"

def test_normalize_message_content_other_type():
    """Test normalization of non-string, non-list, non-None content to string."""
    assert _normalize_message_content({"content": 123}) == "123"

def test_normalize_message_content_empty_list():
    """Test normalization of an empty list to an empty string."""
    assert _normalize_message_content({"content": []}) == ""
