"""Small TTL cache helpers for QA entry validation."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """A small ordered TTL cache for hot validation results."""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 128) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._items: "OrderedDict[str, tuple[float, T]]" = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        """Return a cached value when it is still fresh."""

        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= time.time():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        """Store a value and evict the oldest entry when the cache is full."""

        self._items[key] = (time.time() + self.ttl_seconds, value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)
