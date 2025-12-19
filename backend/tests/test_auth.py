
import pytest
from backend.auth import GOOGLE_CLIENT_ID

def test_google_client_id_is_set():
    assert GOOGLE_CLIENT_ID is not None
    assert isinstance(GOOGLE_CLIENT_ID, str)
    assert len(GOOGLE_CLIENT_ID) > 0
