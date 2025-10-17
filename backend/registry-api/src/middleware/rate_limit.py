"""
Rate limiting middleware for API endpoints

Reference: T118 (Security hardening), best practices
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse.

    Implements sliding window rate limiting with per-user and per-IP limits.
    Reference: 100 req/min per user, 1000 req/min per IP
    """

    def __init__(self, app, user_limit: int = 100, ip_limit: int = 1000, window_seconds: int = 60):
        super().__init__(app)
        self.user_limit = user_limit  # Requests per window per authenticated user
        self.ip_limit = ip_limit  # Requests per window per IP address
        self.window_seconds = window_seconds

        # Storage: {key: [(timestamp, count), ...]}
        self.user_requests = defaultdict(list)
        self.ip_requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = self._get_client_ip(request)

        # Get user ID from auth (if authenticated)
        user_id = self._get_user_id(request)

        # Check IP rate limit
        if not self._check_rate_limit(client_ip, self.ip_requests, self.ip_limit):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"IP rate limit exceeded: {self.ip_limit} requests per {self.window_seconds} seconds",
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Check user rate limit (if authenticated)
        if user_id:
            if not self._check_rate_limit(user_id, self.user_requests, self.user_limit):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"User rate limit exceeded: {self.user_limit} requests per {self.window_seconds} seconds",
                    headers={"Retry-After": str(self.window_seconds)},
                )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        if user_id:
            remaining = self._get_remaining(user_id, self.user_requests, self.user_limit)
            response.headers["X-RateLimit-Limit"] = str(self.user_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)

        return response

    def _check_rate_limit(self, key: str, storage: dict, limit: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean up old requests
        storage[key] = [(ts, count) for ts, count in storage[key] if ts > cutoff]

        # Count requests in window
        total_requests = sum(count for _, count in storage[key])

        # Check limit
        if total_requests >= limit:
            return False

        # Record this request
        storage[key].append((now, 1))
        return True

    def _get_remaining(self, key: str, storage: dict, limit: int) -> int:
        """Get remaining requests in current window"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Count requests in window
        total_requests = sum(
            count for ts, count in storage[key] if ts > cutoff
        )

        return max(0, limit - total_requests)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Try X-Forwarded-For header first (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Try X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        """Extract user ID from authenticated request"""
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user:
            return str(user.id)

        return None


# Helper function to add middleware to FastAPI app
def add_rate_limiting(app, user_limit: int = 100, ip_limit: int = 1000, window_seconds: int = 60):
    """Add rate limiting middleware to FastAPI application"""
    app.add_middleware(
        RateLimitMiddleware,
        user_limit=user_limit,
        ip_limit=ip_limit,
        window_seconds=window_seconds,
    )
