"""
Redis Caching Service

Provides fast caching for API responses to reduce database load.
Cache invalidation happens on:
- New scrape completion
- Manual cache clear
- TTL expiration
"""
import json
import hashlib
from typing import Optional, Any, Callable
from datetime import timedelta
import logging
from functools import wraps

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Cache key prefixes
PREFIX_SPECIALS = "specials:"
PREFIX_STATS = "stats:"
PREFIX_CATEGORIES = "categories:"
PREFIX_PRODUCTS = "products:"

# Default TTLs
TTL_SPECIALS_LIST = timedelta(minutes=5)  # Short TTL for listings
TTL_STATS = timedelta(minutes=10)  # Stats can be slightly stale
TTL_CATEGORIES = timedelta(hours=1)  # Categories rarely change
TTL_PRODUCT = timedelta(hours=24)  # Individual products rarely change


class CacheService:
    """Redis-based caching service with fallback to no-cache."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Initialize Redis connection."""
        if self._connected:
            return

        try:
            settings = get_settings()
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis cache connected")
        except (RedisConnectionError, Exception) as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self._client = None
            self._connected = False

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False

    def _make_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from prefix and parameters."""
        # Sort params for consistent key generation
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"{prefix}{hash_val}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta = TTL_SPECIALS_LIST
    ):
        """Set value in cache with TTL."""
        if not self._client:
            return

        try:
            await self._client.setex(
                key,
                int(ttl.total_seconds()),
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def delete(self, key: str):
        """Delete a specific key."""
        if not self._client:
            return

        try:
            await self._client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        if not self._client:
            return

        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"Cleared cache keys matching: {pattern}")
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")

    async def invalidate_specials(self):
        """Invalidate all specials-related caches."""
        await self.delete_pattern(f"{PREFIX_SPECIALS}*")
        await self.delete_pattern(f"{PREFIX_STATS}*")
        await self.delete_pattern(f"{PREFIX_CATEGORIES}*")
        logger.info("Invalidated all specials caches")

    async def invalidate_store(self, store_slug: str):
        """Invalidate cache for a specific store."""
        # Store-specific keys include store in params, so we clear all specials
        await self.invalidate_specials()

    # Convenience methods for specific cache operations

    async def get_specials(self, params: dict) -> Optional[dict]:
        """Get cached specials list."""
        key = self._make_key(PREFIX_SPECIALS, params)
        return await self.get(key)

    async def set_specials(self, params: dict, data: dict):
        """Cache specials list."""
        key = self._make_key(PREFIX_SPECIALS, params)
        await self.set(key, data, TTL_SPECIALS_LIST)

    async def get_stats(self) -> Optional[dict]:
        """Get cached stats."""
        return await self.get(f"{PREFIX_STATS}all")

    async def set_stats(self, data: dict):
        """Cache stats."""
        await self.set(f"{PREFIX_STATS}all", data, TTL_STATS)

    async def get_categories(self) -> Optional[list]:
        """Get cached categories."""
        return await self.get(f"{PREFIX_CATEGORIES}all")

    async def set_categories(self, data: list):
        """Cache categories."""
        await self.set(f"{PREFIX_CATEGORIES}all", data, TTL_CATEGORIES)

    @property
    def is_connected(self) -> bool:
        """Check if cache is available."""
        return self._connected


# Singleton instance
cache = CacheService()


def cached(
    prefix: str,
    ttl: timedelta = TTL_SPECIALS_LIST,
    key_params: Optional[list[str]] = None
):
    """
    Decorator for caching async function results.

    Usage:
        @cached(PREFIX_SPECIALS, TTL_SPECIALS_LIST, ["store", "page"])
        async def get_specials(store: str, page: int, db: Session):
            ...

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live for cached data
        key_params: List of parameter names to include in cache key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip caching if Redis not available
            if not cache.is_connected:
                return await func(*args, **kwargs)

            # Build cache key from specified params
            if key_params:
                cache_params = {k: kwargs.get(k) for k in key_params if k in kwargs}
            else:
                cache_params = {}

            cache_key = cache._make_key(prefix, cache_params)

            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss, stored: {cache_key}")

            return result

        return wrapper
    return decorator
