"""
PM Agent Performance Cache

Implements caching strategies for:
- Intent classification results
- Workflow metadata
- API responses
"""

import time
import logging
import hashlib
import json
from typing import Optional, Dict, Any, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Intent, IntentType

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL"""
    value: T
    timestamp: float
    ttl: int = 300  # Time to live in seconds (default 5 minutes)
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """Update timestamp and increment hit count"""
        self.timestamp = time.time()
        self.hit_count += 1


class IntentCache:
    """
    Cache for intent classification results

    Caches recently seen inputs to their intent classifications
    to avoid redundant LLM calls.
    """

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize intent cache

        Args:
            max_size: Maximum number of cached entries
            ttl: Time to live for entries in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry[Intent]] = {}

        # Metrics
        self._hits = 0
        self._misses = 0

    def _normalize_input(self, user_input: str) -> str:
        """Normalize input for cache key generation"""
        # Lowercase and strip
        normalized = user_input.lower().strip()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _generate_key(self, user_input: str) -> str:
        """Generate cache key from input"""
        normalized = self._normalize_input(user_input)

        # Use hash for shorter keys
        key_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"intent:{key_hash}"

    def get(self, user_input: str) -> Optional[Intent]:
        """
        Get cached intent classification

        Args:
            user_input: User input text

        Returns:
            Cached Intent or None
        """
        key = self._generate_key(user_input)

        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            entry.touch()
            self._hits += 1
            logger.debug(f"Intent cache hit for: {user_input[:50]}...")
            return entry.value

        self._misses += 1
        return None

    def put(self, user_input: str, intent: Intent):
        """
        Store intent classification in cache

        Args:
            user_input: User input text
            intent: Classified intent
        """
        key = self._generate_key(user_input)

        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        self._cache[key] = CacheEntry(
            value=intent,
            timestamp=time.time(),
            ttl=self.ttl
        )

    def _evict_oldest(self):
        """Evict oldest entry from cache"""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].timestamp
        )
        del self._cache[oldest_key]

    def cleanup_expired(self):
        """Remove expired entries from cache"""
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


class WorkflowMetadataCache:
    """
    Cache for workflow metadata

    Caches workflow definitions, steps, and other metadata
    to avoid repeated template loading.
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize workflow metadata cache

        Args:
            ttl: Time to live for entries in seconds
        """
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry[Dict[str, Any]]] = {}

        # Metrics
        self._hits = 0
        self._misses = 0

    def get(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow metadata

        Args:
            workflow_id: Workflow identifier

        Returns:
            Cached workflow metadata or None
        """
        entry = self._cache.get(workflow_id)
        if entry and not entry.is_expired():
            entry.touch()
            self._hits += 1
            return entry.value

        self._misses += 1
        return None

    def put(self, workflow_id: str, metadata: Dict[str, Any]):
        """
        Store workflow metadata in cache

        Args:
            workflow_id: Workflow identifier
            metadata: Workflow metadata
        """
        self._cache[workflow_id] = CacheEntry(
            value=metadata,
            timestamp=time.time(),
            ttl=self.ttl
        )

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


class APIResponseCache:
    """
    Cache for API responses

    Caches API responses for idempotent operations like
    status queries to reduce Orchestrator load.
    """

    def __init__(self, ttl: int = 10):
        """
        Initialize API response cache

        Args:
            ttl: Time to live for entries in seconds (default 10s for freshness)
        """
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry[Dict[str, Any]]] = {}

        # Only cache read operations
        self._cacheable_actions = {'get_state', 'list_workflows'}

        # Metrics
        self._hits = 0
        self._misses = 0

    def _generate_key(self, action: str, params: Dict[str, Any]) -> str:
        """Generate cache key from action and params"""
        # Create deterministic string from params
        params_str = json.dumps(params, sort_keys=True)

        # Hash for shorter keys
        key_hash = hashlib.md5(f"{action}:{params_str}".encode()).hexdigest()
        return f"api:{key_hash}"

    def get(self, action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached API response

        Args:
            action: API action
            params: API parameters

        Returns:
            Cached response or None
        """
        # Only cache idempotent operations
        if action not in self._cacheable_actions:
            return None

        key = self._generate_key(action, params)

        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            entry.touch()
            self._hits += 1
            return entry.value

        self._misses += 1
        return None

    def put(self, action: str, params: Dict[str, Any], response: Dict[str, Any]):
        """
        Store API response in cache

        Args:
            action: API action
            params: API parameters
            response: API response
        """
        # Only cache idempotent operations
        if action not in self._cacheable_actions:
            return

        key = self._generate_key(action, params)

        self._cache[key] = CacheEntry(
            value=response,
            timestamp=time.time(),
            ttl=self.ttl
        )

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


class CompositeCache:
    """
    Composite cache manager

    Manages all cache layers and provides unified interface.
    """

    def __init__(
        self,
        intent_cache_size: int = 1000,
        intent_cache_ttl: int = 300,
        workflow_cache_ttl: int = 300,
        api_cache_ttl: int = 10
    ):
        """
        Initialize composite cache

        Args:
            intent_cache_size: Max size of intent cache
            intent_cache_ttl: TTL for intent cache entries
            workflow_cache_ttl: TTL for workflow cache entries
            api_cache_ttl: TTL for API cache entries
        """
        self.intent_cache = IntentCache(
            max_size=intent_cache_size,
            ttl=intent_cache_ttl
        )
        self.workflow_cache = WorkflowMetadataCache(
            ttl=workflow_cache_ttl
        )
        self.api_cache = APIResponseCache(
            ttl=api_cache_ttl
        )

    def cleanup_expired(self):
        """Cleanup expired entries across all caches"""
        self.intent_cache.cleanup_expired()

    def clear_all(self):
        """Clear all caches"""
        self.intent_cache.clear()
        self.workflow_cache.clear()
        self.api_cache.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all caches"""
        return {
            "intent_cache": self.intent_cache.get_metrics(),
            "workflow_cache": self.workflow_cache.get_metrics(),
            "api_cache": self.api_cache.get_metrics(),
        }
