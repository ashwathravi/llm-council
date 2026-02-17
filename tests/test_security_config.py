
import pytest
from backend import auth

def test_google_client_id_is_not_hardcoded():
    """Ensure that the Google Client ID is not hardcoded to the previously known default."""
    HARDCODED_ID = "154618380883-hlmnd78sufsgvrmvk39ht872brk4o32r.apps.googleusercontent.com"
    assert auth.GOOGLE_CLIENT_ID != HARDCODED_ID, "GOOGLE_CLIENT_ID should not be hardcoded to the insecure default"

def test_google_client_id_is_none_by_default_in_test_env():
    """Ensure that in the test environment (without env var), it defaults to None."""
    # This assumes checking in an environment where GOOGLE_CLIENT_ID is not set.
    # If CI sets it, this test might fail, so we should be careful.
    # But for this task, we know it's not set.
    import os
    if "GOOGLE_CLIENT_ID" not in os.environ:
        assert auth.GOOGLE_CLIENT_ID is None
