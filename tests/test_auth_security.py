
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from backend.auth import verify_google_token

def test_verify_google_token_missing_client_id():
    """
    Test that verify_google_token raises 503 Service Unavailable
    when GOOGLE_CLIENT_ID is not configured.
    """
    # Patch GOOGLE_CLIENT_ID to be None in backend.auth module
    with patch("backend.auth.GOOGLE_CLIENT_ID", None):
        with pytest.raises(HTTPException) as exc_info:
            verify_google_token("dummy_token")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Google Sign-In is not configured on the server."

def test_verify_google_token_invalid_token():
    """
    Test that verify_google_token raises 401 Unauthorized
    when GOOGLE_CLIENT_ID is configured but token is invalid.
    """
    # Patch GOOGLE_CLIENT_ID to be a dummy value
    with patch("backend.auth.GOOGLE_CLIENT_ID", "dummy_client_id"):
        # We also need to mock id_token.verify_oauth2_token to raise ValueError
        # because we don't want to make real network calls or verify real tokens here
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                verify_google_token("invalid_token")

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid Google token"
