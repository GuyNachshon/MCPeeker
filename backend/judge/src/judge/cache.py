"""Redis-backed cache for Judge service.

Reference: FR-020 (≤400ms p95 latency), FR-027 (Redis caching)
"""
import json
from datetime import timedelta
from typing import Any, Dict, Optional

import redis


class ClassificationCache:
    """Redis cache for classification results."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "judge:classification:",
    ):
        """Initialize cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix

        # Stats
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result.

        Args:
            key: Cache key

        Returns:
            Cached result or None
        """
        full_key = self.key_prefix + key

        try:
            cached = self.redis_client.get(full_key)
            if cached:
                self.hits += 1
                return json.loads(cached)

            self.misses += 1
            return None

        except Exception as e:
            print(f"Cache get error: {e}")
            self.misses += 1
            return None

    def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Set cached result.

        Args:
            key: Cache key
            value: Result to cache
            ttl: Time to live

        Returns:
            True if successful
        """
        full_key = self.key_prefix + key

        try:
            serialized = json.dumps(value)

            if ttl:
                self.redis_client.setex(
                    full_key,
                    int(ttl.total_seconds()),
                    serialized,
                )
            else:
                self.redis_client.set(full_key, serialized)

            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete cached result.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        full_key = self.key_prefix + key

        try:
            return bool(self.redis_client.delete(full_key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def clear_all(self) -> int:
        """Clear all cached results.

        Returns:
            Number of keys deleted
        """
        try:
            pattern = self.key_prefix + "*"
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache hit rate and other metrics
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        # Get Redis info
        try:
            info = self.redis_client.info()
            memory_used = info.get("used_memory_human", "unknown")
            connected = True
        except Exception:
            memory_used = "unknown"
            connected = False

        return {
            "cache_enabled": True,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "redis_connected": connected,
            "redis_memory": memory_used,
        }

    def health_check(self) -> bool:
        """Check if Redis is healthy.

        Returns:
            True if Redis is accessible
        """
        try:
            return self.redis_client.ping()
        except Exception:
            return False
