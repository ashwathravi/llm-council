
import pytest
from pydantic import ValidationError
from backend.main import CreateConversationRequest, SendMessageRequest

def test_valid_frameworks():
    """Test that all allowed frameworks are accepted."""
    for framework in ["standard", "six_hats", "debate", "ensemble", "heterogeneous"]:
        req = CreateConversationRequest(framework=framework)
        assert req.framework == framework

def test_valid_session_types():
    """Test that all allowed session types are accepted."""
    for session_type in ["general", "visual_review", "code_review", "build_spec", "research_docs"]:
        req = CreateConversationRequest(session_type=session_type)
        assert req.session_type == session_type

def test_valid_execution_modes():
    """Test that allowed execution modes are accepted for code review sessions."""
    for execution_mode in ["disabled", "safe_patch_checks"]:
        req = CreateConversationRequest(session_type="code_review", execution_mode=execution_mode)
        assert req.execution_mode == execution_mode

def test_invalid_framework():
    """Test that an invalid framework raises a ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(framework="invalid_framework")
    assert "Framework must be one of" in str(excinfo.value)

def test_invalid_session_type():
    """Test that an invalid session type raises a ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(session_type="invalid_session")
    assert "Session type must be one of" in str(excinfo.value)

def test_invalid_execution_mode():
    """Test that an invalid execution mode raises a ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(session_type="code_review", execution_mode="run_everything")
    assert "Execution mode must be one of" in str(excinfo.value)

def test_execution_mode_requires_code_review():
    """Test that non-code-review sessions cannot enable the execution loop."""
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(session_type="general", execution_mode="safe_patch_checks")
    assert "Execution mode is only available for code review sessions." in str(excinfo.value)

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
    assert req.session_type == "general"
    assert req.execution_mode == "disabled"
    assert req.council_models == []
    assert req.chairman_model is None
    assert req.primary_artifacts == []

def test_message_content_length_limit():
    """Test that message content exceeding 50KB raises a ValidationError."""
    large_content = "a" * 50001
    with pytest.raises(ValidationError) as excinfo:
        SendMessageRequest(content=large_content)
    assert "String should have at most 50000 characters" in str(excinfo.value)

def test_chairman_model_length_limit():
    """Test that chairman_model exceeding 100 characters raises a ValidationError."""
    long_model = "a" * 101
    with pytest.raises(ValidationError) as excinfo:
        CreateConversationRequest(chairman_model=long_model)
    assert "String should have at most 100 characters" in str(excinfo.value)
