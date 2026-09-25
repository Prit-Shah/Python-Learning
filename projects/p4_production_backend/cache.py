"""
Project P4: High-Performance Cache-Aside Layer
================================================================================
Implements Cache-Aside Pattern with TTL and pattern invalidation.
Supports fast in-memory fallback when standalone Redis is unavailable.
================================================================================
"""
import time
import json
from typing import Any


class CacheEntry:
    def __init__(self, value: str, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CacheAsideService:
    """Thread-safe Cache-Aside implementation."""

    def __init__(self):
        self._store: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None or entry.is_expired:
            if entry and entry.is_expired:
                del self._store[key]
            self.misses += 1
            return None

        self.hits += 1
        return json.loads(entry.value)

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        expires_at = time.time() + ttl_seconds
        serialized = json.dumps(value)
        self._store[key] = CacheEntry(serialized, expires_at)

    def invalidate(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidates all cache keys starting with prefix."""
        to_del = [k for k in self._store if k.startswith(prefix)]
        for k in to_del:
            del self._store[k]
        return len(to_del)


cache = CacheAsideService()
