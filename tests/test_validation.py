
import pytest
from pydantic import ValidationError
from backend.main import CreateConversationRequest

def test_valid_frameworks():
    """Test that all allowed frameworks are accepted."""
    for framework in ["standard", "six_hats", "debate", "ensemble"]:
        req = CreateConversationRequest(framework=framework)
        assert req.framework == framework

def test_invalid_framework():
    """Test that an invalid framework raises a ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(framework="invalid_framework")
    assert "Framework must be one of" in str(excinfo.value)

def test_valid_council_models():
    """Test that a valid list of council models is accepted."""
    models = ["openai/gpt-4", "anthropic/claude-3-opus", "google/gemini-pro"]
    req = CreateConversationRequest(council_models=models)
    assert req.council_models == models

def test_too_many_council_models():
    """Test that more than 10 council models raises a ValidationError."""
    models = [f"model{i}" for i in range(11)]
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(council_models=models)
    # The max_length=10 in Field might trigger first, or the custom validator.
    # Pydantic V2 usually reports "List should have at most 10 items"
    assert "at most 10 items" in str(excinfo.value) or "Too many models" in str(excinfo.value)

def test_model_name_too_long():
    """Test that a model name longer than 100 characters raises a ValidationError."""
    long_model_name = "a" * 101
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(council_models=[long_model_name])
    assert "Model name too long" in str(excinfo.value)

def test_default_values():
    """Test the default values of CreateConversationRequest."""
    req = CreateConversationRequest()
    assert req.framework == "standard"
    assert req.council_models == []
    assert req.chairman_model is None
