
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
        # With LRU eviction, size should never exceed MAX_STORE_SIZE significantly
        # (It checks len >= MAX before adding, so max size is MAX)
        assert len(security._limiter_store[scope]) <= 50, \
            f"Store size {len(security._limiter_store[scope])} exceeded expected limit"

        # Now wait for window to expire
        time.sleep(window + 1.5)

        # Trigger requests to force cleanup/eviction
        # We need to hit the threshold (50) to trigger eviction.
        # Currently size is 50.

        # Request 1: Size is 50. Should trigger eviction of LRU item.
        request = MagicMock(spec=Request)
        request.client.host = "trigger_1"
        request.headers.get.return_value = None
        await dependency(request)

        # Request 2: Size is 50. Should trigger eviction again.
        request = MagicMock(spec=Request)
        request.client.host = "trigger_2"
        request.headers.get.return_value = None
        await dependency(request)

        # Assert that size is still bounded
        current_size = len(security._limiter_store[scope])
        assert current_size <= 50, \
             f"Store size {current_size} indicates unbounded growth"

        # Verify trigger_1 and trigger_2 are present (LRU logic keeps recent items)
        assert "trigger_1" in security._limiter_store[scope]
        assert "trigger_2" in security._limiter_store[scope]

        # Verify oldest items (1.2.3.0, 1.2.3.1) were evicted
        assert "1.2.3.0" not in security._limiter_store[scope]
        assert "1.2.3.1" not in security._limiter_store[scope]

    # Verify patch is reverted
    assert security.MAX_STORE_SIZE == original_max
