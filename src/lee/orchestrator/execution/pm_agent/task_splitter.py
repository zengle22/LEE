"""Simple PMA Task Splitter for P0.

This module provides task splitting functionality for L2 phases with complexity=L.
It uses LLM to break down complex phases into implementable feature points.

Focused on stability and correctness for P0 implementation.

P2: Added caching for split results to avoid redundant LLM calls.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import yaml
import asyncio

from lee.orchestrator.storage.models import Point, Complexity


@dataclass
class TaskSplitResult:
    """Result of PMA task split.

    Attributes:
        points: List of feature points generated from the split
        confidence: Confidence score (0-1) for the split quality
        original_estimate: Original time estimate for the phase
        split_estimate: Combined time estimate for all points
        cache_hit: Whether the result came from cache (P2)
    """
    points: List[Point]
    confidence: float
    original_estimate: str
    split_estimate: str
    cache_hit: bool = False  # P2: Cache tracking


class SimpleTaskSplitter:
    """Splits L2 phases into feature points using LLM.

    This is a P0 implementation focused on correctness.
    Future versions will add caching, prompt optimization, and validation.

    P2: Added split result caching.

    Usage:
        splitter = SimpleTaskSplitter(llm_executor)
        result = await splitter.split_phase(
            phase_id="frontend_dev",
            phase_description="UI implementation",
            prd_content="...",
            repo_context={"type": "frontend", "language": "vue"}
        )
    """

    def __init__(self, llm_executor, use_cache: bool = True, cache_dir: Optional[str] = None):
        """Initialize the task splitter.

        Args:
            llm_executor: Executor factory or LLM executor instance
            use_cache: Whether to use split result caching (P2)
            cache_dir: Custom cache directory (optional)
        """
        self.llm_executor = llm_executor
        self.use_cache = use_cache

        # P2: Initialize cache
        self._cache = None
        if use_cache:
            from lee.orchestrator.execution.pm_agent.split_cache import SplitCache
            self._cache = SplitCache(cache_dir=cache_dir)

    async def split_phase(
        self,
        phase_id: str,
        phase_description: str,
        prd_content: str = "",
        repo_context: Optional[Dict[str, Any]] = None
    ) -> TaskSplitResult:
        """Split a phase into feature points using LLM.

        P2: Checks cache first before calling LLM.

        Args:
            phase_id: Phase identifier (e.g., "frontend_dev")
            phase_description: Phase description from template
            prd_content: PRD document content
            repo_context: Repo information (type, language, structure)

        Returns:
            TaskSplitResult with list of Points
        """
        repo_context = repo_context or {}

        # P2: Check cache first
        if self._cache:
            cached_points = self._cache.get(
                phase_id=phase_id,
                phase_description=phase_description,
                prd_content=prd_content,
                repo_context=repo_context
            )
            if cached_points is not None:
                return TaskSplitResult(
                    points=cached_points,
                    confidence=0.8,  # Cached confidence
                    original_estimate=self._estimate_phase_time(phase_id),
                    split_estimate=f"{len(cached_points) * 2}h",
                    cache_hit=True
                )

        prompt = self._build_split_prompt(
            phase_id, phase_description, prd_content, repo_context
        )

        # Call LLM
        try:
            # Explicit null check for llm_executor
            if self.llm_executor is None:
                raise ValueError("LLM executor is None")

            # Handle both executor factory and direct executor
            if hasattr(self.llm_executor, 'create'):
                executor = self.llm_executor.create("llm")
                response = await executor.execute({
                    "prompt": prompt,
                    "response_format": "yaml"
                })
            elif callable(self.llm_executor):
                # Direct executor (callable)
                response = await self.llm_executor({
                    "prompt": prompt,
                    "response_format": "yaml"
                })
            else:
                raise TypeError(f"Invalid llm_executor type: {type(self.llm_executor)}")
        except Exception as e:
            # Fallback: return single point with entire phase
            return TaskSplitResult(
                points=[self._create_fallback_point(phase_id, phase_description)],
                confidence=0.5,
                original_estimate="8h",
                split_estimate="8h"
            )

        # Parse response into Points
        yaml_output = response.get("output", "") if isinstance(response, dict) else str(response)
        points = self._parse_points(yaml_output, phase_id)
        points = self._validate_and_fix_points(points)

        # P2: Store in cache
        if self._cache:
            self._cache.set(
                phase_id=phase_id,
                phase_description=phase_description,
                prd_content=prd_content,
                repo_context=repo_context,
                points=points,
                metadata={
                    "confidence": response.get("confidence", 0.8) if isinstance(response, dict) else 0.8,
                    "original_estimate": self._estimate_phase_time(phase_id),
                    "split_estimate": f"{len(points) * 2}h",
                }
            )

        # Estimate time (simplified for P0)
        point_count = len(points)
        original_estimate = self._estimate_phase_time(phase_id)
        split_estimate = f"{max(1, point_count * 2)}h"  # Rough estimate

        return TaskSplitResult(
            points=points,
            confidence=response.get("confidence", 0.8) if isinstance(response, dict) else 0.8,
            original_estimate=original_estimate,
            split_estimate=split_estimate,
            cache_hit=False
        )

    def _build_split_prompt(
        self,
        phase_id: str,
        phase_desc: str,
        prd: str,
        repo: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM task splitting.

        Args:
            phase_id: Phase identifier
            phase_desc: Phase description
            prd: PRD content
            repo: Repository context

        Returns:
            Formatted prompt string
        """
        # Truncate PRD for token limit
        prd_snippet = prd[:3000] if len(prd) > 3000 else prd

        return f"""You are a task breakdown specialist. Split the following phase into 2-5 feature points.

## Phase Information
- Phase ID: {phase_id}
- Description: {phase_desc}

## PRD Context
{prd_snippet}

## Repository Context
- Type: {repo.get('type', 'unknown')}
- Language: {repo.get('language', 'unknown')}
- Structure: {repo.get('structure', 'standard project structure')}

## Output Requirements

Output MUST be valid YAML with this exact structure:

```yaml
points:
  - id: "{phase_id}-p1"
    title: "Clear, concise title"
    desc: "What this point implements in detail"
    layer: "ui"  # One of: ui, state, api, service
    estimated_complexity: "M"  # One of: S, M, L
    files_hint:
      - "path/to/file.ext"
    depends_on: []  # IDs of points this depends on
  - id: "{phase_id}-p2"
    title: "Second point title"
    desc: "Second point description"
    layer: "ui"
    estimated_complexity: "M"
    files_hint: []
    depends_on: []
```

## Splitting Guidelines

1. **Equal Complexity**: Points should be roughly equal in complexity
2. **DAG Dependencies**: Dependencies must form a DAG (no cycles)
3. **Independent Testing**: Each point should be independently testable
4. **Max 5 Points**: Keep between 2-5 points per phase
5. **Layer Mapping**: Choose appropriate layer for each point
   - ui: UI components, pages, visual elements
   - state: State management, data stores, reducers
   - api: API contracts, endpoints, interfaces
   - service: Business logic, data processing, algorithms

Please provide only the YAML output, no additional text.
"""

    def _parse_points(self, yaml_output: str, phase_id: str) -> List[Point]:
        """Parse YAML output into Point objects.

        Args:
            yaml_output: Raw YAML string from LLM
            phase_id: Parent phase ID for fallback

        Returns:
            List of Point objects
        """
        try:
            # Try to extract YAML if there's markdown code fencing
            if "```yaml" in yaml_output:
                start = yaml_output.find("```yaml") + 7
                end = yaml_output.find("```", start)
                yaml_output = yaml_output[start:end].strip()
            elif "```" in yaml_output:
                start = yaml_output.find("```") + 3
                end = yaml_output.find("```", start)
                yaml_output = yaml_output[start:end].strip()

            data = yaml.safe_load(yaml_output)
            points_data = data.get("points", [])

            if not points_data:
                raise ValueError("No points in YAML output")

            points = []
            for p in points_data:
                # Validate required fields
                if not all(k in p for k in ["id", "title", "desc", "layer"]):
                    continue

                # Get complexity with default
                comp_str = p.get("estimated_complexity", "M")
                try:
                    complexity = Complexity(comp_str)
                except ValueError:
                    complexity = Complexity.M

                points.append(Point(
                    id=p["id"],
                    title=p["title"],
                    desc=p["desc"],
                    layer=p["layer"],
                    estimated_complexity=complexity,
                    files_hint=p.get("files_hint", []),
                    depends_on=p.get("depends_on", [])
                ))

            return points if points else self._create_fallback_points(phase_id)

        except Exception as e:
            # Fallback: return 2-3 reasonable points
            return self._create_fallback_points(phase_id)

    def _validate_and_fix_points(self, points: List[Point]) -> List[Point]:
        """Validate and fix common issues in point list.

        P2: Enhanced validation with quality checks.

        Args:
            points: List of points to validate

        Returns:
            Validated and fixed list of points
        """
        if not points:
            return points

        # Run quality validation
        quality_result = self._validate_split_quality(points)

        if not quality_result["is_valid"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Split quality issues: {quality_result['errors']}")

        # Ensure point IDs are unique
        seen_ids = set()
        unique_points = []
        for point in points:
            if point.id not in seen_ids:
                seen_ids.add(point.id)
                unique_points.append(point)

        # Validate dependencies exist
        point_ids = {p.id for p in unique_points}
        for point in unique_points:
            valid_deps = [d for d in point.depends_on if d in point_ids]
            point.depends_on = valid_deps

        # Check for obvious circular dependencies (direct)
        for point in unique_points:
            for dep_id in point.depends_on:
                dep_point = next((p for p in unique_points if p.id == dep_id), None)
                if dep_point and point.id in dep_point.depends_on:
                    # Remove circular dependency
                    point.depends_on = [d for d in point.depends_on if d != dep_id]

        return unique_points

    def _validate_split_quality(self, points: List[Point]) -> Dict[str, Any]:
        """P2: Validate the quality of a split result.

        Checks:
        1. Point count (should be 2-5 for meaningful parallelism)
        2. Complexity balance (points should have similar complexity)
        3. Title quality (should be descriptive)
        4. Dependency validity (no cycles, all deps exist)
        5. Layer consistency (points should use appropriate layers)

        Args:
            points: List of points to validate

        Returns:
            Dictionary with is_valid, errors, warnings, and score
        """
        errors = []
        warnings = []
        score = 100

        # Check 1: Point count
        if len(points) < 2:
            errors.append("Too few points (less than 2) for meaningful split")
            score -= 30
        elif len(points) > 7:
            warnings.append(f"Many points ({len(points)}) may be hard to coordinate")
            score -= 10

        # Check 2: Complexity balance
        complexity_counts = {}
        for p in points:
            comp = p.estimated_complexity.value
            complexity_counts[comp] = complexity_counts.get(comp, 0) + 1

        if complexity_counts.get("L", 0) > len(points) / 2:
            warnings.append("More than half of points are marked Large complexity")
            score -= 15

        # Check 3: Title quality
        for p in points:
            if len(p.title) < 5:
                warnings.append(f"Point {p.id} has a very short title")
                score -= 5
            if len(p.desc) < 20:
                warnings.append(f"Point {p.id} has a very short description")
                score -= 5

        # Check 4: Layer consistency
        valid_layers = {"ui", "state", "api", "service"}
        for p in points:
            if p.layer not in valid_layers:
                errors.append(f"Point {p.id} has invalid layer: {p.layer}")
                score -= 20

        # Check 5: ID format
        for p in points:
            if not p.id or p.id.strip() == "":
                errors.append(f"Point has empty ID")
                score -= 25

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": max(0, score),
        }

    def _create_fallback_point(self, phase_id: str, phase_desc: str) -> Point:
        """Create a fallback point when parsing fails.

        Args:
            phase_id: Phase identifier
            phase_desc: Phase description

        Returns:
            Single Point covering the entire phase
        """
        return Point(
            id=f"{phase_id}-p1",
            title=f"Complete {phase_id} Phase",
            desc=phase_desc or f"Complete implementation of {phase_id} phase",
            layer=self._get_default_layer_for_phase(phase_id),
            estimated_complexity=Complexity.L,
            files_hint=[],
            depends_on=[]
        )

    def _create_fallback_points(self, phase_id: str) -> List[Point]:
        """Create 2-3 fallback points when parsing fails.

        Args:
            phase_id: Phase identifier

        Returns:
            List of 2-3 reasonable Points
        """
        layer = self._get_default_layer_for_phase(phase_id)

        # Create 2-3 generic points
        return [
            Point(
                id=f"{phase_id}-p1",
                title=f"{phase_id} - Part 1: Foundation",
                desc=f"Initial setup and core functionality for {phase_id}",
                layer=layer,
                estimated_complexity=Complexity.M,
                files_hint=[],
                depends_on=[]
            ),
            Point(
                id=f"{phase_id}-p2",
                title=f"{phase_id} - Part 2: Implementation",
                desc=f"Main implementation and features for {phase_id}",
                layer=layer,
                estimated_complexity=Complexity.M,
                files_hint=[],
                depends_on=[f"{phase_id}-p1"]
            ),
        ]

    def _get_default_layer_for_phase(self, phase_id: str) -> str:
        """Get default architectural layer for a phase.

        Args:
            phase_id: Phase identifier

        Returns:
            Default layer string
        """
        layer_map = {
            "plan": "ui",
            "api_align": "api",
            "frontend_dev": "ui",
            "backend_dev": "service",
            "integration": "ui",
        }
        return layer_map.get(phase_id, "ui")

    def _validate_and_fix_points(self, points: List[Point]) -> List[Point]:
        """Validate and fix common issues in point list.

        Args:
            points: List of points to validate

        Returns:
            Validated and fixed list of points
        """
        if not points:
            return points

        # Ensure point IDs are unique
        seen_ids = set()
        unique_points = []
        for point in points:
            if point.id not in seen_ids:
                seen_ids.add(point.id)
                unique_points.append(point)

        # Validate dependencies exist
        point_ids = {p.id for p in unique_points}
        for point in unique_points:
            valid_deps = [d for d in point.depends_on if d in point_ids]
            point.depends_on = valid_deps

        # Check for obvious circular dependencies (direct)
        for point in unique_points:
            for dep_id in point.depends_on:
                dep_point = next((p for p in unique_points if p.id == dep_id), None)
                if dep_point and point.id in dep_point.depends_on:
                    # Remove circular dependency
                    point.depends_on = [d for d in point.depends_on if d != dep_id]

        return unique_points

    def _estimate_phase_time(self, phase_id: str) -> str:
        """Get rough time estimate for a phase.

        Args:
            phase_id: Phase identifier

        Returns:
            Time estimate string
        """
        estimates = {
            "plan": "4h",
            "api_align": "4h",
            "frontend_dev": "16h",
            "backend_dev": "16h",
            "integration": "4h",
        }
        return estimates.get(phase_id, "8h")
