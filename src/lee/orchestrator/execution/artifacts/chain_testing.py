"""
Chain testing framework for formal SSOT requirement chains.

This implements the first ADR-011 execution slice:
- tester registration and dispatch
- sampling / cache / incremental execution
- schema and trace testers
- report.json / scorecard.md generation
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Set

from jinja2 import Template

from .models import ArtifactMetadata
from .ssot_files import parse_front_matter
from .ssot_service import SSOTValidator


REPORT_TEMPLATE = Template(
    """# Requirement Chain Scorecard

- Generated At: {{ generated_at }}
- Project Root: `{{ project_root }}`
- Testers: {{ testers|join(", ") if testers else "none" }}
- Target Count: {{ target_count }}
- Sampled Count: {{ sampled_count }}

## Metrics

| Metric | Value |
| --- | ---: |
{% for key, value in metrics.items() -%}
| {{ key }} | {{ value }} |
{% endfor %}

## Tester Summary

{% for result in results -%}
### {{ result.tester_id }}

- Passed: {{ "yes" if result.passed else "no" }}
- Checked IDs: {{ result.checked_ids|length }}
- Errors: {{ result.error_count }}
- Warnings: {{ result.warning_count }}

{% if result.issues -%}
| Severity | Artifact | Message |
| --- | --- | --- |
{% for issue in result.issues -%}
| {{ issue.severity }} | {{ issue.artifact_id or "-" }} | {{ issue.message }} |
{% endfor %}
{% else -%}
No issues.
{% endif %}

{% endfor -%}
"""
)


@dataclass
class ChainTestIssue:
    code: str
    message: str
    severity: str = "error"
    artifact_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainTestResult:
    tester_id: str
    passed: bool
    checked_ids: List[str]
    issues: List[ChainTestIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    cache_hit: bool = False

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity != "error")


@dataclass
class ChainTestRunReport:
    generated_at: str
    project_root: str
    tester_ids: List[str]
    target_count: int
    sampled_count: int
    sampled_ids: List[str]
    metrics: Dict[str, Any]
    results: List[ChainTestResult]
    snapshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "project_root": self.project_root,
            "tester_ids": self.tester_ids,
            "target_count": self.target_count,
            "sampled_count": self.sampled_count,
            "sampled_ids": self.sampled_ids,
            "metrics": self.metrics,
            "results": [
                {
                    **asdict(result),
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                }
                for result in self.results
            ],
            "snapshot_path": self.snapshot_path,
        }


@dataclass
class ChainTestContext:
    project_root: Path
    manager: Any
    target_ids: List[str]
    sampled_ids: List[str]
    sample_strategy: str
    cache_dir: Path
    snapshot_path: Optional[Path] = None

    @property
    def registry(self):
        return self.manager.registry


class ChainTester(Protocol):
    tester_id: str

    def run(self, context: ChainTestContext) -> ChainTestResult:
        ...


def _resolve_artifact_path(context: ChainTestContext, artifact: ArtifactMetadata) -> Path:
    return context.manager._resolve_metadata_path(artifact)


def _artifact_body(context: ChainTestContext, artifact: ArtifactMetadata) -> str:
    path = _resolve_artifact_path(context, artifact)
    if not path.exists():
        return ""
    try:
        _, body = parse_front_matter(path)
    except Exception:
        body = path.read_text(encoding="utf-8")
    return body


def _tokenize(text: str) -> List[str]:
    lowered = text.lower()
    return [token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", lowered) if len(token) >= 2]


def _token_freq(tokens: Sequence[str]) -> Dict[str, float]:
    freq: Dict[str, float] = {}
    if not tokens:
        return freq
    for token in tokens:
        freq[token] = freq.get(token, 0.0) + 1.0
    total = float(len(tokens))
    return {token: count / total for token, count in freq.items()}


def _cosine_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    left_freq = _token_freq(left)
    right_freq = _token_freq(right)
    if not left_freq or not right_freq:
        return 0.0
    keys = set(left_freq) | set(right_freq)
    dot = sum(left_freq.get(key, 0.0) * right_freq.get(key, 0.0) for key in keys)
    left_norm = math.sqrt(sum(value * value for value in left_freq.values()))
    right_norm = math.sqrt(sum(value * value for value in right_freq.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _top_keywords(tokens: Sequence[str], limit: int = 8) -> List[str]:
    freq = _token_freq(tokens)
    ranked = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
    return [key for key, _ in ranked[:limit]]


def _extract_markdown_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^#{{1,6}}\s+{re.escape(heading)}\s*$\n(?P<section>.*?)(?=^#{{1,6}}\s+|\Z)"
    )
    match = pattern.search(body)
    return match.group("section").strip() if match else ""


def _sentence_embedding_backend() -> Optional[Any]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _semantic_similarity(left_text: str, right_text: str, backend: Optional[Any] = None) -> float:
    if backend is not None:
        try:
            left_vec, right_vec = backend.encode([left_text, right_text], normalize_embeddings=True)
            return float(sum(float(l) * float(r) for l, r in zip(left_vec, right_vec)))
        except Exception:
            pass
    return _cosine_similarity(_tokenize(left_text), _tokenize(right_text))


def _cluster_pairs(nodes: Sequence[str], edges: Sequence[tuple[str, str]]) -> List[List[str]]:
    try:
        import hdbscan  # type: ignore
        import numpy as np  # type: ignore

        if not nodes:
            return []
        index = {node_id: pos for pos, node_id in enumerate(nodes)}
        matrix = np.ones((len(nodes), len(nodes)))
        np.fill_diagonal(matrix, 0.0)
        for left, right in edges:
            left_idx = index[left]
            right_idx = index[right]
            matrix[left_idx][right_idx] = 0.0
            matrix[right_idx][left_idx] = 0.0
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="precomputed")
        labels = clusterer.fit_predict(matrix)
        groups: Dict[int, List[str]] = {}
        for node_id, label in zip(nodes, labels):
            if int(label) < 0:
                continue
            groups.setdefault(int(label), []).append(node_id)
        return [sorted(group) for _, group in sorted(groups.items())]
    except Exception:
        adjacency: Dict[str, Set[str]] = {node_id: set() for node_id in nodes}
        for left, right in edges:
            adjacency[left].add(right)
            adjacency[right].add(left)
        seen: Set[str] = set()
        groups: List[List[str]] = []
        for node_id in nodes:
            if node_id in seen or not adjacency[node_id]:
                continue
            stack = [node_id]
            component: List[str] = []
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                component.append(current)
                stack.extend(sorted(adjacency[current] - seen))
            if len(component) > 1:
                groups.append(sorted(component))
        return sorted(groups)


def _cluster_backend_name() -> str:
    try:
        import hdbscan  # type: ignore  # noqa: F401

        return "hdbscan"
    except Exception:
        return "graph-fallback"


def _environment_fingerprint() -> Dict[str, str]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "timezone": str(datetime.now().astimezone().tzinfo or "unknown"),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", ""),
    }


def _issue_signature(issue: ChainTestIssue) -> Dict[str, Any]:
    return {
        "code": issue.code,
        "severity": issue.severity,
        "artifact_id": issue.artifact_id,
        "message": issue.message,
    }


@dataclass
class SampleLibrary:
    root_dir: Path

    def versions_dir(self) -> Path:
        return self.root_dir / "versions"

    def manifest_path(self) -> Path:
        return self.root_dir / "manifest.json"

    def version_manifest_path(self, version: str) -> Path:
        return self.versions_dir() / version / "manifest.json"

    def initialize_defaults(self, version: str = "v1") -> Dict[str, int]:
        counts = {"positive": 50, "negative": 30, "boundary": 20}
        manifest = {
            "version": version,
            "generated_at": datetime.now().isoformat(),
            "categories": {},
        }
        version_dir = self.versions_dir() / version
        for category, count in counts.items():
            category_dir = version_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            entries = []
            for index in range(1, count + 1):
                sample_id = f"{category[:3]}-{index:03d}"
                filename = f"{sample_id}.json"
                payload = {
                    "id": sample_id,
                    "category": category,
                    "title": f"{category.title()} Sample {index}",
                    "input": {"sample": index, "category": category},
                    "expected": {"status": "pass" if category == "positive" else "review"},
                }
                (category_dir / filename).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                entries.append({"id": sample_id, "file": f"{category}/{filename}"})
            manifest["categories"][category] = entries
        self.version_manifest_path(version).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.manifest_path().parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path().write_text(
            json.dumps(
                {
                    "active_version": version,
                    "versions": [version],
                    "updated_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return counts

    def metadata(self) -> Dict[str, Any]:
        return json.loads(self.manifest_path().read_text(encoding="utf-8"))

    def active_version(self) -> str:
        return str(self.metadata().get("active_version", "v1"))

    def list_versions(self) -> List[str]:
        metadata = self.metadata()
        versions = list(metadata.get("versions", []))
        if not versions and self.versions_dir().exists():
            versions = sorted(path.name for path in self.versions_dir().iterdir() if path.is_dir())
        return versions

    def activate_version(self, version: str) -> None:
        if not self.version_manifest_path(version).exists():
            raise FileNotFoundError(f"Unknown sample version: {version}")
        metadata = self.metadata() if self.manifest_path().exists() else {}
        versions = list(dict.fromkeys([*(metadata.get("versions", [])), version]))
        self.manifest_path().write_text(
            json.dumps(
                {
                    "active_version": version,
                    "versions": versions,
                    "updated_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def create_version(self, version: str, samples_by_category: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        manifest = {
            "version": version,
            "generated_at": datetime.now().isoformat(),
            "categories": {},
        }
        version_dir = self.versions_dir() / version
        counts: Dict[str, int] = {}
        for category, samples in samples_by_category.items():
            category_dir = version_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            entries = []
            for index, sample in enumerate(samples, start=1):
                sample_id = str(sample.get("id") or f"{category[:3]}-{index:03d}")
                filename = f"{sample_id}.json"
                payload = {
                    "id": sample_id,
                    "category": category,
                    **sample,
                }
                (category_dir / filename).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                entries.append({"id": sample_id, "file": f"{category}/{filename}"})
            manifest["categories"][category] = entries
            counts[category] = len(entries)
        self.version_manifest_path(version).parent.mkdir(parents=True, exist_ok=True)
        self.version_manifest_path(version).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        metadata = self.metadata() if self.manifest_path().exists() else {}
        versions = list(dict.fromkeys([*(metadata.get("versions", [])), version]))
        self.manifest_path().parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path().write_text(
            json.dumps(
                {
                    "active_version": version,
                    "versions": versions,
                    "updated_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return counts

    def load(
        self,
        version: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        version = version or self.active_version()
        manifest = json.loads(self.version_manifest_path(version).read_text(encoding="utf-8"))
        if not category:
            return manifest
        entries = list(manifest.get("categories", {}).get(category, []))
        samples: List[Dict[str, Any]] = []
        for entry in entries:
            samples.append(
                json.loads(
                    (self.versions_dir() / version / entry["file"]).read_text(encoding="utf-8")
                )
            )
        return {"version": version, "category": category, "entries": entries, "samples": samples}

    def validate(self, version: Optional[str] = None) -> Dict[str, Any]:
        manifest = self.load(version=version)
        version = str(manifest.get("version", version or self.active_version()))
        counts: Dict[str, int] = {}
        missing_files: List[str] = []
        duplicate_ids: List[str] = []
        seen_ids: Set[str] = set()
        for category, entries in manifest.get("categories", {}).items():
            counts[category] = len(entries)
            for entry in entries:
                sample_path = self.versions_dir() / version / entry["file"]
                if not sample_path.exists():
                    missing_files.append(entry["file"])
                    continue
                sample = json.loads(sample_path.read_text(encoding="utf-8"))
                sample_id = str(sample.get("id", entry.get("id", "")))
                if sample_id in seen_ids:
                    duplicate_ids.append(sample_id)
                seen_ids.add(sample_id)
        return {
            "version": version,
            "counts": counts,
            "missing_files": missing_files,
            "duplicate_ids": duplicate_ids,
            "is_valid": not missing_files and not duplicate_ids,
        }


def _artifact_hash(artifact: ArtifactMetadata) -> str:
    payload = {
        "id": artifact.id,
        "path": artifact.path,
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else "",
        "content_hash": artifact.content_hash or "",
        "parent_id": (artifact.properties or {}).get("parent_id"),
        "derived_from": artifact.derived_from,
        "derived_from_ids": (artifact.properties or {}).get("derived_from_ids", []),
        "source_refs": (artifact.properties or {}).get("source_refs", []),
        "status": artifact.status.value,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _chain_artifacts(registry) -> List[ArtifactMetadata]:
    allowed = {"src", "epic", "feat", "task"}
    artifacts: List[ArtifactMetadata] = []
    for artifact in registry.list_all():
        if artifact.category != "ssot_object":
            continue
        ssot_type = str((artifact.properties or {}).get("ssot_type", "")).lower()
        if ssot_type in allowed:
            artifacts.append(artifact)
    return sorted(artifacts, key=lambda item: item.id)


class SchemaChainTester:
    tester_id = "schema"

    def run(self, context: ChainTestContext) -> ChainTestResult:
        validator = SSOTValidator(context.registry)
        issues: List[ChainTestIssue] = []
        checked_ids: List[str] = []
        failed_ids: Set[str] = set()

        for artifact_id in context.sampled_ids:
            artifact = context.registry.get(artifact_id)
            if not artifact:
                issues.append(
                    ChainTestIssue(
                        code="ARTIFACT_MISSING",
                        message=f"{artifact_id} missing from registry",
                        artifact_id=artifact_id,
                    )
                )
                failed_ids.add(artifact_id)
                continue

            checked_ids.append(artifact_id)
            validation = validator.validate_all(artifact_id)
            for error in validation.errors:
                issues.append(
                    ChainTestIssue(
                        code="SCHEMA_VALIDATION_ERROR",
                        message=error,
                        severity="error",
                        artifact_id=artifact_id,
                    )
                )
                failed_ids.add(artifact_id)
            for warning in validation.warnings:
                issues.append(
                    ChainTestIssue(
                        code="SCHEMA_VALIDATION_WARNING",
                        message=warning,
                        severity="warning",
                        artifact_id=artifact_id,
                    )
                )

        metrics = {
            "checked_count": len(checked_ids),
            "pass_rate": round(((len(checked_ids) - len(failed_ids)) / len(checked_ids)) * 100, 2)
            if checked_ids
            else 100.0,
        }
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=not any(issue.severity == "error" for issue in issues),
            checked_ids=checked_ids,
            issues=issues,
            metrics=metrics,
        )


class TraceChainTester:
    tester_id = "trace"

    def run(self, context: ChainTestContext) -> ChainTestResult:
        sampled_set = set(context.sampled_ids)
        artifacts = {
            artifact.id: artifact
            for artifact in _chain_artifacts(context.registry)
            if artifact.id in sampled_set
        }
        issues: List[ChainTestIssue] = []
        edges: Dict[str, Set[str]] = {artifact_id: set() for artifact_id in artifacts}

        for artifact_id, artifact in artifacts.items():
            props = artifact.properties or {}
            parent_id = props.get("parent_id")
            if parent_id:
                if context.registry.exists(parent_id):
                    edges[artifact_id].add(parent_id)
                else:
                    issues.append(
                        ChainTestIssue(
                            code="BROKEN_PARENT",
                            message=f"parent_id '{parent_id}' does not exist",
                            artifact_id=artifact_id,
                        )
                    )

            for ref in props.get("derived_from_ids", []):
                ref_id = ref.get("id") if isinstance(ref, dict) else ref
                if not ref_id:
                    continue
                if context.registry.exists(ref_id):
                    edges[artifact_id].add(ref_id)
                else:
                    issues.append(
                        ChainTestIssue(
                            code="BROKEN_DERIVED_FROM",
                            message=f"derived_from_ids '{ref_id}' does not exist",
                            artifact_id=artifact_id,
                        )
                    )

            for ref in props.get("source_refs", []):
                ref_id = str(ref).split("#", 1)[0]
                if context.registry.exists(ref_id):
                    edges[artifact_id].add(ref_id)
                else:
                    issues.append(
                        ChainTestIssue(
                            code="BROKEN_SOURCE_REF",
                            message=f"source_refs '{ref}' does not exist",
                            artifact_id=artifact_id,
                        )
                    )

        visited: Set[str] = set()
        visiting: Set[str] = set()

        def walk(node_id: str) -> None:
            if node_id in visiting:
                issues.append(
                    ChainTestIssue(
                        code="TRACE_CYCLE",
                        message=f"cycle detected at '{node_id}'",
                        artifact_id=node_id,
                    )
                )
                return
            if node_id in visited or node_id not in edges:
                return
            visiting.add(node_id)
            for upstream in edges[node_id]:
                walk(upstream)
            visiting.remove(node_id)
            visited.add(node_id)

        for artifact_id in list(edges):
            walk(artifact_id)

        for artifact_id, artifact in artifacts.items():
            ssot_type = str((artifact.properties or {}).get("ssot_type", "")).lower()
            upstreams = edges.get(artifact_id, set())
            if ssot_type == "epic" and not any(ref.startswith("SRC-") for ref in upstreams):
                issues.append(
                    ChainTestIssue(
                        code="TRACE_MISSING_SRC",
                        message="EPIC missing SRC linkage",
                        severity="warning",
                        artifact_id=artifact_id,
                    )
                )
            if ssot_type == "feat" and not any(ref.startswith("EPIC-") for ref in upstreams):
                issues.append(
                    ChainTestIssue(
                        code="TRACE_MISSING_EPIC",
                        message="FEAT missing EPIC linkage",
                        severity="warning",
                        artifact_id=artifact_id,
                    )
                )
            if ssot_type == "task" and not any(ref.startswith("FEAT-") for ref in upstreams):
                issues.append(
                    ChainTestIssue(
                        code="TRACE_MISSING_FEAT",
                        message="TASK missing FEAT linkage",
                        severity="warning",
                        artifact_id=artifact_id,
                    )
                )

        epic_ids = [artifact_id for artifact_id, artifact in artifacts.items() if (artifact.properties or {}).get("ssot_type") == "epic"]
        feat_ids = [artifact_id for artifact_id, artifact in artifacts.items() if (artifact.properties or {}).get("ssot_type") == "feat"]
        task_ids = [artifact_id for artifact_id, artifact in artifacts.items() if (artifact.properties or {}).get("ssot_type") == "task"]

        epic_covered = sum(1 for artifact_id in epic_ids if any(ref.startswith("SRC-") for ref in edges.get(artifact_id, set())))
        feat_covered = sum(1 for artifact_id in feat_ids if any(ref.startswith("EPIC-") for ref in edges.get(artifact_id, set())))
        task_covered = sum(1 for artifact_id in task_ids if any(ref.startswith("FEAT-") for ref in edges.get(artifact_id, set())))

        metrics = {
            "epic_trace_coverage": round((epic_covered / len(epic_ids)) * 100, 2) if epic_ids else 100.0,
            "feat_trace_coverage": round((feat_covered / len(feat_ids)) * 100, 2) if feat_ids else 100.0,
            "task_trace_coverage": round((task_covered / len(task_ids)) * 100, 2) if task_ids else 100.0,
            "broken_link_count": sum(1 for issue in issues if issue.code.startswith("BROKEN_")),
            "cycle_count": sum(1 for issue in issues if issue.code == "TRACE_CYCLE"),
        }
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=not any(issue.severity == "error" for issue in issues),
            checked_ids=sorted(artifacts),
            issues=issues,
            metrics=metrics,
        )


class SemanticChainTester:
    tester_id = "semantic"

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or {
            "epic": 0.05,
            "feat": 0.08,
            "task": 0.1,
        }
        self._embedding_backend = None

    def run(self, context: ChainTestContext) -> ChainTestResult:
        if self._embedding_backend is None:
            self._embedding_backend = _sentence_embedding_backend()
        sampled = {
            artifact.id: artifact
            for artifact in _chain_artifacts(context.registry)
            if artifact.id in set(context.sampled_ids)
        }
        issues: List[ChainTestIssue] = []
        similarities: List[float] = []
        keyword_coverages: List[float] = []

        for artifact_id, artifact in sampled.items():
            props = artifact.properties or {}
            upstream_ids: List[str] = []
            parent_id = props.get("parent_id")
            if parent_id:
                upstream_ids.append(parent_id)
            for ref in props.get("derived_from_ids", []):
                ref_id = ref.get("id") if isinstance(ref, dict) else ref
                if ref_id:
                    upstream_ids.append(ref_id)
            for ref in props.get("source_refs", []):
                ref_id = str(ref).split("#", 1)[0]
                if ref_id:
                    upstream_ids.append(ref_id)
            upstream_ids = list(dict.fromkeys(upstream_ids))
            if not upstream_ids:
                continue

            artifact_body = _artifact_body(context, artifact)
            artifact_tokens = _tokenize(artifact_body)
            for upstream_id in upstream_ids:
                upstream = context.registry.get(upstream_id)
                if not upstream:
                    continue
                upstream_body = _artifact_body(context, upstream)
                upstream_tokens = _tokenize(upstream_body)
                similarity = _semantic_similarity(artifact_body, upstream_body, backend=self._embedding_backend)
                similarities.append(similarity)
                ssot_type = str(props.get("ssot_type", "")).lower()
                threshold = self.thresholds.get(ssot_type, 0.08)
                if similarity < threshold:
                    issues.append(
                        ChainTestIssue(
                            code="SEMANTIC_DRIFT",
                            message=f"semantic similarity {similarity:.3f} below {threshold:.3f} against {upstream_id}",
                            severity="warning",
                            artifact_id=artifact_id,
                            details={"upstream_id": upstream_id, "similarity": similarity},
                        )
                    )

                upstream_keywords = _top_keywords(upstream_tokens)
                coverage = 0.0
                if upstream_keywords:
                    covered = sum(1 for keyword in upstream_keywords if keyword in set(artifact_tokens))
                    coverage = covered / len(upstream_keywords)
                keyword_coverages.append(coverage)
                if upstream_keywords and coverage < 0.4:
                    issues.append(
                        ChainTestIssue(
                            code="KEYWORD_COVERAGE_LOW",
                            message=f"keyword coverage {coverage:.2f} below 0.40 against {upstream_id}",
                            severity="warning",
                            artifact_id=artifact_id,
                            details={"upstream_id": upstream_id, "coverage": coverage, "keywords": upstream_keywords},
                        )
                    )

        metrics = {
            "embedding_backend": "sentence-transformers" if self._embedding_backend is not None else "token-fallback",
            "semantic_alignment_score": round((sum(similarities) / len(similarities)) * 100, 2) if similarities else 100.0,
            "keyword_coverage_score": round((sum(keyword_coverages) / len(keyword_coverages)) * 100, 2) if keyword_coverages else 100.0,
        }
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=True,
            checked_ids=sorted(sampled),
            issues=issues,
            metrics=metrics,
        )


class OverlapChainTester:
    tester_id = "overlap"

    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold
        self._embedding_backend = None

    def run(self, context: ChainTestContext) -> ChainTestResult:
        if self._embedding_backend is None:
            self._embedding_backend = _sentence_embedding_backend()
        artifacts = [
            artifact
            for artifact in _chain_artifacts(context.registry)
            if artifact.id in set(context.sampled_ids)
            and str((artifact.properties or {}).get("ssot_type", "")).lower() in {"feat", "task"}
        ]
        issues: List[ChainTestIssue] = []
        pair_count = 0
        overlap_hits = 0
        similarities: List[float] = []
        overlap_edges: List[tuple[str, str]] = []

        for index, left in enumerate(artifacts):
            left_body = _artifact_body(context, left)
            for right in artifacts[index + 1 :]:
                left_type = str((left.properties or {}).get("ssot_type", "")).lower()
                right_type = str((right.properties or {}).get("ssot_type", "")).lower()
                if left_type != right_type:
                    continue
                pair_count += 1
                similarity = _semantic_similarity(
                    left_body,
                    _artifact_body(context, right),
                    backend=self._embedding_backend,
                )
                similarities.append(similarity)
                if similarity >= self.threshold:
                    overlap_hits += 1
                    overlap_edges.append((left.id, right.id))
                    issues.append(
                        ChainTestIssue(
                            code="OVERLAP_HIGH",
                            message=f"high overlap {similarity:.2f} between {left.id} and {right.id}",
                            severity="warning",
                            artifact_id=left.id,
                            details={"peer_id": right.id, "similarity": similarity},
                        )
                    )

        clusters = _cluster_pairs([artifact.id for artifact in artifacts], overlap_edges)
        incremental_hits = 0
        if context.snapshot_path and context.snapshot_path.exists():
            try:
                baseline = json.loads(context.snapshot_path.read_text(encoding="utf-8"))
                previous_pairs = {
                    tuple(sorted(str(key).split("|", 1)))
                    for key, value in baseline.get("overlap_pairs", {}).items()
                    if value >= self.threshold
                }
                current_pairs = {tuple(sorted(edge)) for edge in overlap_edges}
                incremental_hits = len(current_pairs - previous_pairs)
            except Exception:
                incremental_hits = len(overlap_edges)

        metrics = {
            "overlap_rate": round((overlap_hits / pair_count) * 100, 2) if pair_count else 0.0,
            "average_pair_similarity": round((sum(similarities) / len(similarities)) * 100, 2) if similarities else 0.0,
            "overlap_pair_count": overlap_hits,
            "overlap_cluster_count": len(clusters),
            "incremental_overlap_hits": incremental_hits,
            "cluster_backend": _cluster_backend_name(),
        }
        for cluster in clusters:
            issues.append(
                ChainTestIssue(
                    code="OVERLAP_CLUSTER",
                    message=f"overlap cluster suggests consolidation: {', '.join(cluster)}",
                    severity="warning",
                    artifact_id=cluster[0],
                    details={"cluster": cluster},
                )
            )
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=True,
            checked_ids=[artifact.id for artifact in artifacts],
            issues=issues,
            metrics=metrics,
        )


class ReplayChainTester:
    tester_id = "replay"

    def __init__(self, base_testers: Sequence[ChainTester], replay_count: int = 3):
        self.base_testers = [tester for tester in base_testers if tester.tester_id != self.tester_id]
        self.replay_count = max(2, replay_count)

    def run(self, context: ChainTestContext) -> ChainTestResult:
        issues: List[ChainTestIssue] = []
        fingerprints: Dict[str, List[str]] = {}
        checked_ids = list(context.sampled_ids)
        env = _environment_fingerprint()
        baseline_fingerprints: Dict[str, List[str]] = {}
        if context.snapshot_path and context.snapshot_path.exists():
            try:
                baseline = json.loads(context.snapshot_path.read_text(encoding="utf-8"))
                baseline_fingerprints = baseline.get("replay_fingerprints", {})
                previous_env = baseline.get("environment", {})
                if previous_env and previous_env != env:
                    issues.append(
                        ChainTestIssue(
                            code="REPLAY_ENVIRONMENT_DRIFT",
                            message="environment fingerprint changed since baseline snapshot",
                            severity="warning",
                            details={"baseline": previous_env, "current": env},
                        )
                    )
            except Exception:
                baseline_fingerprints = {}

        for tester in self.base_testers:
            run_fingerprints: List[str] = []
            for _ in range(self.replay_count):
                result = tester.run(context)
                payload = {
                    "issues": [_issue_signature(issue) for issue in result.issues],
                    "metrics": result.metrics,
                    "checked_ids": result.checked_ids,
                }
                run_fingerprints.append(
                    hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
                )
            fingerprints[tester.tester_id] = run_fingerprints
            if len(set(run_fingerprints)) != 1:
                issues.append(
                    ChainTestIssue(
                        code="REPLAY_UNSTABLE",
                        message=f"{tester.tester_id} produced non-deterministic results across replay runs",
                        severity="warning",
                        details={"fingerprints": run_fingerprints},
                    )
                )
            previous = baseline_fingerprints.get(tester.tester_id)
            if previous and previous[-1] != run_fingerprints[-1]:
                issues.append(
                    ChainTestIssue(
                        code="REPLAY_HISTORY_DRIFT",
                        message=f"{tester.tester_id} diverged from baseline replay fingerprint",
                        severity="warning",
                        details={"baseline": previous, "current": run_fingerprints},
                    )
                )

        stable = sum(1 for values in fingerprints.values() if len(set(values)) == 1)
        metrics = {
            "replay_stability_score": round((stable / len(fingerprints)) * 100, 2) if fingerprints else 100.0,
            "replayed_tester_count": len(fingerprints),
            "replay_count": self.replay_count,
            "environment_consistent": not any(issue.code == "REPLAY_ENVIRONMENT_DRIFT" for issue in issues),
            "fingerprints": fingerprints,
        }
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=True,
            checked_ids=checked_ids,
            issues=issues,
            metrics=metrics,
        )


class ExecutableChainTester:
    tester_id = "executable"

    def __init__(self, ambiguity_terms: Optional[Sequence[str]] = None):
        self.ambiguity_terms = list(
            ambiguity_terms
            or ["尽快", "适当", "若干", "等等", "优化一下", "maybe", "approximately", "soon", "somehow"]
        )

    def run(self, context: ChainTestContext) -> ChainTestResult:
        tasks = [
            artifact
            for artifact in _chain_artifacts(context.registry)
            if artifact.id in set(context.sampled_ids)
            and str((artifact.properties or {}).get("ssot_type", "")).lower() == "task"
        ]
        issues: List[ChainTestIssue] = []
        scores: List[float] = []

        for task in tasks:
            body = _artifact_body(context, task)
            score = 0.0
            missing: List[str] = []
            ambiguous_terms = [term for term in self.ambiguity_terms if term.lower() in body.lower()]
            if "# Objective" in body:
                score += 0.2
            else:
                missing.append("objective")
            if "# Description" in body:
                score += 0.2
            else:
                missing.append("description")
            if "## Definition Of Done" in body:
                score += 0.2
            else:
                missing.append("definition_of_done")
            if (task.properties or {}).get("parent_id") and (task.properties or {}).get("source_refs"):
                score += 0.15
            else:
                missing.append("trace_context")
            description_section = _extract_markdown_section(body, "Description")
            if any(marker in description_section for marker in ["输入", "输出", "input", "output"]):
                score += 0.1
            else:
                missing.append("input_output_contract")
            if "## Dependencies" in body:
                score += 0.05
            else:
                missing.append("dependencies")
            if "## Acceptance Mapping" in body:
                score += 0.05
            else:
                missing.append("acceptance_mapping")
            if not ambiguous_terms:
                score += 0.05
            scores.append(score)
            if missing:
                issues.append(
                    ChainTestIssue(
                        code="EXECUTABILITY_GAP",
                        message=f"missing executability signals: {', '.join(missing)}",
                        severity="warning",
                        artifact_id=task.id,
                        details={"score": score, "missing": missing},
                    )
                )
            if ambiguous_terms:
                issues.append(
                    ChainTestIssue(
                        code="EXECUTABILITY_AMBIGUOUS_LANGUAGE",
                        message=f"ambiguous language detected: {', '.join(ambiguous_terms)}",
                        severity="warning",
                        artifact_id=task.id,
                        details={"terms": ambiguous_terms},
                    )
                )

        metrics = {
            "executability_rate": round((sum(scores) / len(scores)) * 100, 2) if scores else 100.0,
            "task_count": len(tasks),
            "ambiguity_issue_count": sum(1 for issue in issues if issue.code == "EXECUTABILITY_AMBIGUOUS_LANGUAGE"),
            "feedback_path": str(context.project_root / ".artifacts" / "trace" / "chain-testing-feedback.json"),
        }
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=True,
            checked_ids=[task.id for task in tasks],
            issues=issues,
            metrics=metrics,
        )


class ChainTestRunner:
    def __init__(self, manager: Any):
        self.manager = manager
        self._testers: Dict[str, ChainTester] = {}

    def register(self, tester: ChainTester) -> None:
        self._testers[tester.tester_id] = tester

    def register_defaults(self) -> "ChainTestRunner":
        schema = SchemaChainTester()
        trace = TraceChainTester()
        semantic = SemanticChainTester()
        overlap = OverlapChainTester()
        executable = ExecutableChainTester()
        self.register(schema)
        self.register(trace)
        self.register(semantic)
        self.register(overlap)
        self.register(executable)
        self.register(ReplayChainTester([schema, trace, semantic, overlap, executable]))
        return self

    def available_testers(self) -> List[str]:
        return sorted(self._testers)

    def run(
        self,
        tester_ids: Optional[Sequence[str]] = None,
        sample_strategy: str = "all",
        sample_size: Optional[int] = None,
        seed: int = 7,
        use_cache: bool = True,
        incremental: bool = False,
        baseline_path: Optional[Path] = None,
        max_workers: int = 4,
    ) -> ChainTestRunReport:
        registry = self.manager.registry
        registry.rebuild()
        targets = _chain_artifacts(registry)
        target_ids = [artifact.id for artifact in targets]
        sampled_ids = self._sample_targets(targets, sample_strategy, sample_size, seed)

        snapshot_path = baseline_path or (self.manager.root_path / "trace" / "chain-test-baseline.json")
        if incremental:
            sampled_ids = self._apply_incremental_filter(targets, sampled_ids, snapshot_path)

        cache_dir = self.manager.root_path / "cache" / "chain-tests"
        cache_dir.mkdir(parents=True, exist_ok=True)
        context = ChainTestContext(
            project_root=self.manager.project_root,
            manager=self.manager,
            target_ids=target_ids,
            sampled_ids=sampled_ids,
            sample_strategy=sample_strategy,
            cache_dir=cache_dir,
            snapshot_path=snapshot_path,
        )

        selected = list(tester_ids or self.available_testers())
        for tester_id in selected:
            if tester_id not in self._testers:
                raise ValueError(f"Unknown chain tester: {tester_id}")

        results: List[ChainTestResult] = []
        workers = max(1, min(max_workers, len(selected) or 1))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._run_one, self._testers[tester_id], context, use_cache): tester_id
                for tester_id in selected
            }
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(key=lambda item: item.tester_id)
        metrics = self._aggregate_metrics(results, len(target_ids), len(sampled_ids))
        self._write_snapshot(targets, snapshot_path, results)
        return ChainTestRunReport(
            generated_at=datetime.now().isoformat(),
            project_root=str(self.manager.project_root),
            tester_ids=selected,
            target_count=len(target_ids),
            sampled_count=len(sampled_ids),
            sampled_ids=sampled_ids,
            metrics=metrics,
            results=results,
            snapshot_path=str(snapshot_path),
        )

    def write_report(self, report: ChainTestRunReport, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "report.json"
        scorecard_path = output_dir / "scorecard.md"
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        scorecard = REPORT_TEMPLATE.render(
            generated_at=report.generated_at,
            project_root=report.project_root,
            testers=report.tester_ids,
            target_count=report.target_count,
            sampled_count=report.sampled_count,
            metrics=report.metrics,
            results=[
                {
                    **asdict(result),
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                }
                for result in report.results
            ],
        )
        scorecard_path.write_text(scorecard, encoding="utf-8")
        return {"report_json": json_path, "scorecard_md": scorecard_path}

    def _run_one(self, tester: ChainTester, context: ChainTestContext, use_cache: bool) -> ChainTestResult:
        cache_key = self._cache_key(tester.tester_id, context.sampled_ids, context.registry)
        cache_path = context.cache_dir / f"{cache_key}.json"
        if use_cache and cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return self._result_from_payload(payload, cache_hit=True)

        started = datetime.now()
        result = tester.run(context)
        result.duration_ms = int((datetime.now() - started).total_seconds() * 1000)
        if use_cache:
            cache_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _cache_key(self, tester_id: str, sampled_ids: Sequence[str], registry) -> str:
        parts = [tester_id]
        for artifact_id in sampled_ids:
            artifact = registry.get(artifact_id)
            if artifact:
                parts.append(f"{artifact_id}:{_artifact_hash(artifact)}")
        raw = "|".join(parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _result_from_payload(self, payload: Dict[str, Any], cache_hit: bool) -> ChainTestResult:
        return ChainTestResult(
            tester_id=payload["tester_id"],
            passed=payload["passed"],
            checked_ids=payload.get("checked_ids", []),
            issues=[ChainTestIssue(**issue) for issue in payload.get("issues", [])],
            metrics=payload.get("metrics", {}),
            duration_ms=payload.get("duration_ms", 0),
            cache_hit=cache_hit,
        )

    def _sample_targets(
        self,
        targets: Sequence[ArtifactMetadata],
        strategy: str,
        sample_size: Optional[int],
        seed: int,
    ) -> List[str]:
        if strategy == "all" or not sample_size or sample_size >= len(targets):
            return [artifact.id for artifact in targets]

        rng = random.Random(seed)
        if strategy == "random":
            return sorted(artifact.id for artifact in rng.sample(list(targets), sample_size))

        if strategy == "importance":
            scored = sorted(targets, key=self._importance_score, reverse=True)
            return [artifact.id for artifact in scored[:sample_size]]

        if strategy == "stratified":
            buckets: Dict[str, List[ArtifactMetadata]] = {}
            for artifact in targets:
                buckets.setdefault(str((artifact.properties or {}).get("ssot_type", "")).lower(), []).append(artifact)
            selected: List[str] = []
            keys = sorted(k for k in buckets if k)
            while len(selected) < sample_size and any(buckets.values()):
                for key in keys:
                    bucket = buckets.get(key) or []
                    if not bucket:
                        continue
                    choice = rng.choice(bucket)
                    bucket.remove(choice)
                    selected.append(choice.id)
                    if len(selected) >= sample_size:
                        break
            return sorted(selected)

        raise ValueError(f"Unsupported sample strategy: {strategy}")

    def _importance_score(self, artifact: ArtifactMetadata) -> int:
        ssot_type = str((artifact.properties or {}).get("ssot_type", "")).lower()
        weights = {"src": 100, "epic": 80, "feat": 60, "task": 40}
        return weights.get(ssot_type, 10)

    def _apply_incremental_filter(
        self,
        targets: Sequence[ArtifactMetadata],
        sampled_ids: Sequence[str],
        snapshot_path: Path,
    ) -> List[str]:
        current = {artifact.id: _artifact_hash(artifact) for artifact in targets}
        if not snapshot_path.exists():
            return list(sampled_ids)
        baseline = json.loads(snapshot_path.read_text(encoding="utf-8"))
        baseline_hashes = baseline.get("artifacts", {})
        changed = [
            artifact_id
            for artifact_id in sampled_ids
            if baseline_hashes.get(artifact_id) != current.get(artifact_id)
        ]
        return changed or list(sampled_ids)

    def _write_snapshot(
        self,
        targets: Sequence[ArtifactMetadata],
        snapshot_path: Path,
        results: Optional[Sequence[ChainTestResult]] = None,
    ) -> None:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_context = ChainTestContext(
            project_root=self.manager.project_root,
            manager=self.manager,
            target_ids=[],
            sampled_ids=[],
            sample_strategy="all",
            cache_dir=self.manager.root_path / "cache" / "chain-tests",
            snapshot_path=snapshot_path,
        )
        overlap_pairs: Dict[str, float] = {}
        overlap_candidates = [
            artifact
            for artifact in targets
            if str((artifact.properties or {}).get("ssot_type", "")).lower() in {"feat", "task"}
        ]
        for index, left in enumerate(overlap_candidates):
            left_body = _artifact_body(snapshot_context, left)
            left_type = str((left.properties or {}).get("ssot_type", "")).lower()
            for right in overlap_candidates[index + 1 :]:
                right_type = str((right.properties or {}).get("ssot_type", "")).lower()
                if left_type != right_type:
                    continue
                pair_key = "|".join(sorted([left.id, right.id]))
                overlap_pairs[pair_key] = round(
                    _semantic_similarity(left_body, _artifact_body(snapshot_context, right)),
                    6,
                )
        payload = {
            "generated_at": datetime.now().isoformat(),
            "artifacts": {artifact.id: _artifact_hash(artifact) for artifact in targets},
            "environment": _environment_fingerprint(),
            "overlap_pairs": overlap_pairs,
            "replay_fingerprints": next(
                (
                    result.metrics.get("fingerprints", {})
                    for result in (results or [])
                    if result.tester_id == "replay"
                ),
                {},
            ),
        }
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _aggregate_metrics(
        self,
        results: Sequence[ChainTestResult],
        target_count: int,
        sampled_count: int,
    ) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {
            "target_count": target_count,
            "sampled_count": sampled_count,
            "tester_count": len(results),
            "passed_tester_count": sum(1 for result in results if result.passed),
            "overall_passed": all(result.passed for result in results),
        }
        for result in results:
            for key, value in result.metrics.items():
                metrics[key] = value
        return metrics


def write_chain_ci_templates(project_root: Path) -> Dict[str, Path]:
    github_path = project_root / ".github" / "workflows" / "requirement-chain-test.yml"
    gitlab_path = project_root / "deploy" / "ci" / "gitlab.requirement-chain-test.yml"
    docker_path = project_root / "deploy" / "ci" / "Dockerfile.chain-test"
    readme_path = project_root / "deploy" / "ci" / "README.chain-test.md"

    github_path.parent.mkdir(parents=True, exist_ok=True)
    gitlab_path.parent.mkdir(parents=True, exist_ok=True)

    github_path.write_text(
        """name: requirement-chain-test

on:
  pull_request:
    paths:
      - "spec/**"
      - "src/lee/**"
      - ".github/workflows/requirement-chain-test.yml"
  push:
    branches: [main, dev]
    paths:
      - "spec/**"
      - "src/lee/**"

jobs:
  chain-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install
        run: pip install -e .[dev]
      - name: Run chain tests
        run: python -m lee.cli.main ssot chain-test --tester schema --tester trace --tester semantic --tester overlap --tester replay --tester executable
      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: requirement-chain-reports
          path: .artifacts/trace/chain-tests/
""",
        encoding="utf-8",
    )

    gitlab_path.write_text(
        """requirement_chain_test:
  image: python:3.10
  stage: test
  rules:
    - changes:
        - spec/**/*
        - src/lee/**/*
        - deploy/ci/gitlab.requirement-chain-test.yml
  script:
    - pip install -e .[dev]
    - python -m lee.cli.main ssot chain-test --tester schema --tester trace --tester semantic --tester overlap --tester replay --tester executable
  artifacts:
    when: always
    paths:
      - .artifacts/trace/chain-tests/
""",
        encoding="utf-8",
    )

    docker_path.write_text(
        """FROM python:3.10-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .[dev]
CMD ["python", "-m", "lee.cli.main", "ssot", "chain-test", "--tester", "schema", "--tester", "trace", "--tester", "semantic", "--tester", "overlap", "--tester", "replay", "--tester", "executable"]
""",
        encoding="utf-8",
    )

    readme_path.write_text(
        """# Requirement Chain CI

- GitHub Actions: `.github/workflows/requirement-chain-test.yml`
- GitLab CI: `deploy/ci/gitlab.requirement-chain-test.yml`
- Docker: `deploy/ci/Dockerfile.chain-test`

These templates run `lee ssot chain-test` and publish `report.json` plus `scorecard.md`.
""",
        encoding="utf-8",
    )

    return {
        "github_workflow": github_path,
        "gitlab_ci": gitlab_path,
        "dockerfile": docker_path,
        "readme": readme_path,
    }
