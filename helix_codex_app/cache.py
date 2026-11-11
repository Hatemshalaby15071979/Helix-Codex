"""A bounded, process-local TTL cache for read-heavy calendar reads.

Why: `list_events` parses a range, runs a tenant-scoped query, expands
recurrences and sorts. On a busy calendar the same range is read repeatedly
between writes. The expansion is pure work on top of an indexed query, so it is
a cacheable read.

Correctness rules, in order of importance:

1. A write through the repository invalidates that tenant cache in the same
   process, so a read after a write is never stale.
2. The TTL (2 s by default) bounds staleness for a write from another process
   or another connection that this cache cannot see.
3. The key includes the database identity, so two databases in one process
   (tests, two tenants on separate files) can never share an entry.

This is NOT a distributed cache. A multi-worker deployment needs a shared
store (Redis or similar); adding that dependency without a deployment that
uses it would be decoration (C21). `stats()` exposes hits/misses so the
value can be measured before that decision is made.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Hashable


class TTLCache:
    """Thread-safe, size-bounded cache with per-entry expiry."""

    def __init__(
        self,
        *,
        maxsize: int = 256,
        ttl_seconds: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: dict[Hashable, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at <= self._clock():
                del self._items[key]
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if key not in self._items and len(self._items) >= self._maxsize:
                # Evict the entry that expires soonest: it is the least useful.
                soonest = min(self._items, key=lambda item: self._items[item][0])
                del self._items[soonest]
                self.evictions += 1
            self._items[key] = (self._clock() + self._ttl, value)

    def invalidate_prefix(self, prefix: tuple[Any, ...]) -> int:
        """Drop every entry whose key starts with `prefix`. Returns the count."""
        with self._lock:
            doomed = [
                key
                for key in self._items
                if isinstance(key, tuple) and key[: len(prefix)] == prefix
            ]
            for key in doomed:
                del self._items[key]
            self.invalidations += len(doomed)
            return len(doomed)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "size": len(self._items),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "invalidations": self.invalidations,
            }
