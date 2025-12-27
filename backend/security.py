"""Security utilities for the LLM Council backend."""

from fastapi import Request, HTTPException, status
import time
from collections import defaultdict
from typing import Callable, Coroutine, Any

# Simple in-memory rate limiter
# Map: IP -> list of timestamps
_limiter_store = defaultdict(list)

def rate_limiter(requests_limit: int = 5, time_window: int = 60) -> Callable[[Request], Coroutine[Any, Any, bool]]:
    """
    Dependency factory for rate limiting.

    Args:
        requests_limit: Max number of requests allowed in the time window.
        time_window: Time window in seconds.

    Returns:
        Async dependency function.
    """
    async def dependency(request: Request) -> bool:
        # Use client IP as identifier
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Get history for this IP
        history = _limiter_store[client_ip]

        # Filter out old requests (cleanup)
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
