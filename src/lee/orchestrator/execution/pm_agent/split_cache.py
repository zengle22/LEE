"""PMA Split Result Cache.

Caches task split results based on phase description and PRD hash to avoid
redundant LLM calls for similar phases.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from lee.orchestrator.storage.models import Point, Complexity


logger = logging.getLogger(__name__)


class SplitCache:
    """Cache for PMA task split results.

    Cache key is computed from:
    - phase_id
    - phase_description hash
    - PRD content hash
    - repo_context hash

    This ensures identical inputs get cached results while allowing
    variations to produce new splits.
    """

    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24):
        """Initialize the split cache.

        Args:
            cache_dir: Directory to store cache files (default: .lee/split_cache)
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".lee/split_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def _compute_key(
        self,
        phase_id: str,
        phase_description: str,
        prd_content: str,
        repo_context: Dict[str, Any]
    ) -> str:
        """Compute cache key from inputs.

        Args:
            phase_id: Phase identifier
            phase_description: Phase description
            prd_content: PRD document content
            repo_context: Repository context

        Returns:
            Cache key (hash string)
        """
        # Normalize inputs
        normalized = {
            "phase_id": phase_id,
            "phase_description": phase_description.strip(),
            # Use first 1000 chars of PRD for hashing (full PRD may be large)
            "prd_preview": prd_content[:1000] if prd_content else "",
            "repo_type": repo_context.get("type", ""),
            "repo_language": repo_context.get("language", ""),
        }

        # Compute hash
        content = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self,
        phase_id: str,
        phase_description: str,
        prd_content: str,
        repo_context: Dict[str, Any]
    ) -> Optional[List[Point]]:
        """Get cached split result if available and not expired.

        Args:
            phase_id: Phase identifier
            phase_description: Phase description
            prd_content: PRD document content
            repo_context: Repository context

        Returns:
            List of Points if cache hit and valid, None otherwise
        """
        key = self._compute_key(phase_id, phase_description, prd_content, repo_context)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cache_entry = json.load(f)

            # Check TTL
            cached_at = datetime.fromisoformat(cache_entry["cached_at"])
            if self.ttl <= timedelta(0) or datetime.now() - cached_at >= self.ttl:
                logger.info(f"Split cache expired for {phase_id}")
                cache_file.unlink()  # Remove expired cache
                return None

            # Reconstruct Points
            points = []
            for p_data in cache_entry["points"]:
                points.append(Point(
                    id=p_data["id"],
                    title=p_data["title"],
                    desc=p_data["desc"],
                    layer=p_data["layer"],
                    estimated_complexity=Complexity(p_data["estimated_complexity"]),
                    files_hint=p_data.get("files_hint", []),
                    depends_on=p_data.get("depends_on", []),
                ))

            logger.info(f"Split cache hit for {phase_id} ({len(points)} points)")
            return points

        except Exception as e:
            logger.warning(f"Failed to load split cache: {e}")
            return None

    def set(
        self,
        phase_id: str,
        phase_description: str,
        prd_content: str,
        repo_context: Dict[str, Any],
        points: List[Point],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store split result in cache.

        Args:
            phase_id: Phase identifier
            phase_description: Phase description
            prd_content: PRD document content
            repo_context: Repository context
            points: List of Points to cache
            metadata: Optional metadata (confidence, estimates, etc.)
        """
        key = self._compute_key(phase_id, phase_description, prd_content, repo_context)
        cache_file = self.cache_dir / f"{key}.json"

        cache_entry = {
            "cached_at": datetime.now().isoformat(),
            "phase_id": phase_id,
            "points": [p.__dict__ for p in points],
            "metadata": metadata or {},
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f, indent=2)
            logger.info(f"Cached split result for {phase_id} ({len(points)} points)")
        except Exception as e:
            logger.warning(f"Failed to cache split result: {e}")

    def clear(self, older_than_hours: Optional[int] = None) -> int:
        """Clear cache entries.

        Args:
            older_than_hours: If specified, only clear entries older than this.
                            If None, clear all cache entries.

        Returns:
            Number of cache entries cleared
        """
        count = 0
        cutoff = datetime.now() - timedelta(hours=older_than_hours) if older_than_hours else None

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cutoff is not None:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if mtime < cutoff:
                        cache_file.unlink()
                        count += 1
                else:
                    cache_file.unlink()
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        # Count entries by age
        now = datetime.now()
        age_counts = {
            "1h": 0,
            "6h": 0,
            "24h": 0,
            "older": 0,
        }

        for cache_file in cache_files:
            try:
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = now - mtime
                if age < timedelta(hours=1):
                    age_counts["1h"] += 1
                elif age < timedelta(hours=6):
                    age_counts["6h"] += 1
                elif age < timedelta(hours=24):
                    age_counts["24h"] += 1
                else:
                    age_counts["older"] += 1
            except Exception:
                pass

        return {
            "total_entries": len(cache_files),
            "total_size_bytes": total_size,
            "age_distribution": age_counts,
        }
