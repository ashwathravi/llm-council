
import pytest
from backend import security
from fastapi import Request, HTTPException
from unittest.mock import MagicMock, patch
import time

@pytest.mark.asyncio
async def test_rate_limiter_memory_protection():
    # Setup
    scope = "test_cleanup"
    limit = 5
    window = 1
    # Create dependency with cleanup logic active
    dependency = security.rate_limiter(requests_limit=limit, time_window=window, scope=scope)

    # Verify MAX_STORE_SIZE before patching
    original_max = security.MAX_STORE_SIZE

    # Set a small store size for testing
    with patch("backend.security.MAX_STORE_SIZE", 50):
        # Verify patch is active
        assert security.MAX_STORE_SIZE == 50

        # Simulate attacker sending requests from many different IPs
        # Send 100 requests (2x MAX_STORE_SIZE)
        attacker_ips = [f"1.2.3.{i}" for i in range(100)]

        for ip in attacker_ips:
            request = MagicMock(spec=Request)
            request.client.host = ip
            request.headers.get.return_value = None

            # Make a request
            await dependency(request)

        # Assert valid bounded growth
        assert len(security._limiter_store[scope]) <= 51, \
            f"Store size {len(security._limiter_store[scope])} exceeded expected limit"

        # Now wait for window to expire
        time.sleep(window + 1.5)

        # Trigger requests to force cleanup
        # We need to hit the threshold (50) to trigger cleanup.
        # Currently size is likely 49.

        # Request 1: Should push size to 50
        request = MagicMock(spec=Request)
        request.client.host = "trigger_1"
        request.headers.get.return_value = None
        await dependency(request)

        # Request 2: Size is 50. Should trigger cleanup.
        # Cleanup should remove the 49 stale entries.
        request = MagicMock(spec=Request)
        request.client.host = "trigger_2"
        request.headers.get.return_value = None
        await dependency(request)

        # Assert that we cleaned up
        # We expect "trigger_1", "trigger_2" to be present. Stale entries removed.
        current_size = len(security._limiter_store[scope])
        assert current_size <= 5, \
             f"Store size {current_size} indicates stale entries were not removed"

    # Verify patch is reverted
    assert security.MAX_STORE_SIZE == original_max
