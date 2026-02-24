
import os
import importlib
from unittest.mock import patch

def test_cors_config_default():
    """Test that default CORS origins are used when env var is not set."""
    with patch.dict(os.environ, {}, clear=True):
        import backend.config
        importlib.reload(backend.config)

        expected_defaults = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ]
        assert backend.config.CORS_ALLOWED_ORIGINS == expected_defaults

def test_cors_config_custom():
    """Test that custom CORS origins are parsed correctly."""
    custom_origins = "https://example.com, https://api.example.com"
    with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": custom_origins}):
        import backend.config
        importlib.reload(backend.config)

        expected_custom = [
            "https://example.com",
            "https://api.example.com"
        ]
        assert backend.config.CORS_ALLOWED_ORIGINS == expected_custom

def test_cors_config_empty_string():
    """Test that empty string results in default."""
    # If the env var is set but empty, it might be interpreted as "no origins" or "default".
    # In my implementation: if _cors_origins_raw: ... else: default
    # So empty string means default.
    with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": ""}):
        import backend.config
        importlib.reload(backend.config)

        expected_defaults = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ]
        assert backend.config.CORS_ALLOWED_ORIGINS == expected_defaults
