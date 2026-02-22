
import pytest
from backend import security
from fastapi import Request, HTTPException
from unittest.mock import MagicMock, patch
import time

@pytest.mark.asyncio
async def test_rate_limiter_eviction_strategy():
    # Setup
    scope = "test_eviction"
    limit = 2  # Low limit to easily hit
    window = 60 # Long window so entries stay active

    # Create dependency
    dependency = security.rate_limiter(requests_limit=limit, time_window=window, scope=scope)

    # Patch MAX_STORE_SIZE to 5 (small)
    # Store capacity: 5
    with patch("backend.security.MAX_STORE_SIZE", 5):
        # 1. Victim Old (inserted first)
        victim_old_ip = "192.168.1.100"
        victim_old_req = MagicMock(spec=Request)
        victim_old_req.client.host = victim_old_ip
        victim_old_req.headers.get.return_value = None

        # Hit limit
        await dependency(victim_old_req)
        await dependency(victim_old_req)
        # Verify blocked
        with pytest.raises(HTTPException) as exc:
            await dependency(victim_old_req)
        assert exc.value.status_code == 429

        # 2. Victim New (inserted second)
        victim_new_ip = "192.168.1.101"
        victim_new_req = MagicMock(spec=Request)
        victim_new_req.client.host = victim_new_ip
        victim_new_req.headers.get.return_value = None

        # Hit limit
        await dependency(victim_new_req)
        await dependency(victim_new_req)
        # Verify blocked
        with pytest.raises(HTTPException) as exc:
            await dependency(victim_new_req)
        assert exc.value.status_code == 429

        # Current Store: [Old, New] (Size 2)
        print(f"Store size before flood: {len(security._limiter_store[scope])}")

        # 3. Attacker floods to trigger cleanup
        # We need to fill up to MAX_STORE_SIZE (5) + 1 to trigger cleanup.
        # Currently size 2.
        # Add 3 attackers -> Size 5.
        # Add 1 more -> Size 6 -> Cleanup.

        attacker_ips = [f"10.0.0.{i}" for i in range(4)]
        for ip in attacker_ips:
            req = MagicMock(spec=Request)
            req.client.host = ip
            req.headers.get.return_value = None
            try:
                await dependency(req)
            except HTTPException:
                pass

        # Now cleanup should have happened.
        # IF clear() strategy: Both Old and New are evicted.
        # IF FIFO strategy: Old is evicted, New remains (at index 0).
        # Store should have size <= 5.

        print(f"Store size after flood: {len(security._limiter_store[scope])}")

        # 4. Verify Victim New status
        # Should still be blocked if FIFO strategy worked and New wasn't evicted.
        try:
            await dependency(victim_new_req)
            # If we reach here, Victim New was allowed -> FAILED protection
            victim_new_blocked = False
        except HTTPException as e:
            if e.status_code == 429:
                victim_new_blocked = True
            else:
                raise e

        # 5. Verify Victim Old status (informational)
        try:
            await dependency(victim_old_req)
            victim_old_blocked = False
        except HTTPException:
            victim_old_blocked = True

        print(f"Victim New Blocked: {victim_new_blocked}")
        print(f"Victim Old Blocked: {victim_old_blocked}")

        # Assertions
        # Victim New MUST be blocked (history preserved).
        # If clear() was used, this assertion will FAIL.
        assert victim_new_blocked, "Vulnerability: Newer user was unblocked by store flood (likely due to full store clear)"

        # Victim Old SHOULD be unblocked (evicted), unless store wasn't full enough
        # But here we added enough to trigger cleanup (size 6 > 5).
        # So Old should be evicted.
        assert not victim_old_blocked, "Victim Old should have been evicted (FIFO behavior)"

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(test_rate_limiter_eviction_strategy())
    except AssertionError as e:
        print(f"Assertion failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
