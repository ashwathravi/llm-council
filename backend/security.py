"""Security utilities for the LLM Council backend."""

from fastapi import Request, HTTPException, status
import time
from collections import defaultdict
from typing import Callable, Coroutine, Any

# Simple in-memory rate limiter
# Map: scope -> IP -> list of timestamps
_limiter_store = defaultdict(lambda: defaultdict(list))

# Maximum number of IPs to track per scope to prevent memory exhaustion
MAX_STORE_SIZE = 10000

def _cleanup_stale_entries(scope: str, time_window: int):
    """
    Remove IPs from the store that have no requests within the time window.
    """
    current_time = time.time()
    store = _limiter_store[scope]

    # Identify keys to remove
    to_remove = []
    for ip, history in list(store.items()):
        # Remove expired timestamps
        while history and history[0] < current_time - time_window:
            history.pop(0)

        # If history is empty, mark for removal
        if not history:
            to_remove.append(ip)

    # Remove empty keys
    for ip in to_remove:
        del store[ip]

    # Emergency cleanup if still over capacity
    # Evict oldest entries until we are back under the limit
    # This prevents a total reset of all rate limits
    while len(store) > MAX_STORE_SIZE:
        # Remove the oldest inserted item (FIFO eviction)
        # In Python 3.7+, dicts preserve insertion order, so next(iter(store)) is the first key
        del store[next(iter(store))]

def rate_limiter(requests_limit: int = 5, time_window: int = 60, scope: str = "default") -> Callable[[Request], Coroutine[Any, Any, bool]]:
    """
    Dependency factory for rate limiting.

    Args:
        requests_limit: Max number of requests allowed in the time window.
        time_window: Time window in seconds.
        scope: The scope/bucket name for the rate limit.

    Returns:
        Async dependency function.
    """
    async def dependency(request: Request) -> bool:
        # Use client IP as identifier
        # Prioritize X-Forwarded-For header for use behind proxies (e.g. Render)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For: <client>, <proxy1>, <proxy2>
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        current_time = time.time()

        # Check store size and cleanup if necessary
        # We check before inserting to prevent growth beyond limit
        if len(_limiter_store[scope]) >= MAX_STORE_SIZE:
             _cleanup_stale_entries(scope, time_window)

        # Get history for this scope and IP
        history = _limiter_store[scope][client_ip]

        # Filter out old requests (cleanup for active user)
        # We modify the list in place
        while history and history[0] < current_time - time_window:
            history.pop(0)

        if len(history) >= requests_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )

        history.append(current_time)
        return True

    return dependency
