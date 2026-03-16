"""QA execution preflight checks for canonical `lee qa execute`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import re

import yaml

from lee.orchestrator.core.project_config import _discover_repos
from lee.qa.runner.sut import SUTConfigLoader


TEMPLATE_STATUS_FILL_REQUIRED = "fill_required"


@dataclass
class PreflightIssue:
    """One blocking prerequisite issue discovered before QA execution."""

    kind: str
    path: Path
    message: str
    action_hint: str
    created: bool = False


@dataclass
class PreflightResult:
    """Aggregate preflight result."""

    issues: List[PreflightIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def run_execution_preflight(project_root: Path, params: Dict[str, Any]) -> PreflightResult:
    """Ensure the minimum QA execution prerequisites exist and are actionable."""

    issues: List[PreflightIssue] = []
    issues.extend(_ensure_repo_registry(project_root))
    issues.extend(_ensure_sut_config(project_root, params))
    issues.extend(_ensure_test_sets(project_root, params))
    return PreflightResult(issues=issues)


def _ensure_repo_registry(project_root: Path) -> List[PreflightIssue]:
    repos_path = project_root / ".lee" / "repos.yaml"
    if repos_path.exists():
        return []

    try:
        discovered = _discover_repos(project_root, max_depth=4)
        _write_repo_registry_template(repos_path, project_root, repos=discovered)
    except Exception:
        _write_repo_registry_template(repos_path, project_root)

    return [
        PreflightIssue(
            kind="repo_registry",
            path=repos_path,
            message="缺少 repo registry，已生成初始模板。",
            action_hint="检查 repo_id、path、type，确认前后端仓库映射正确后重试。",
            created=True,
        )
    ]


def _ensure_sut_config(project_root: Path, params: Dict[str, Any]) -> List[PreflightIssue]:
    environment = str(params.get("environment") or "test").strip() or "test"
    loader = SUTConfigLoader(project_root)
    config_path = loader.get_config_path(environment)
    raw = _load_yaml_file(config_path)

    if raw is None:
        _write_sut_template(config_path, environment, str(params.get("base_url") or "").strip())
        return [
            PreflightIssue(
                kind="sut_config",
                path=config_path,
                message=f"缺少环境 '{environment}' 的 SUT 配置，已生成模板。",
                action_hint="填写真实 base_url、协议和认证信息后，将 template_status 改为 ready 或直接删除该字段。",
                created=True,
            )
        ]

    if _is_fill_required(raw):
        return [
            PreflightIssue(
                kind="sut_config",
                path=config_path,
                message=f"环境 '{environment}' 的 SUT 模板仍未补全。",
                action_hint="补全真实连接信息后，将 template_status 改为 ready 或直接删除该字段。",
            )
        ]

    return []


def _ensure_test_sets(project_root: Path, params: Dict[str, Any]) -> List[PreflightIssue]:
    issues: List[PreflightIssue] = []
    target_test_sets = list(_normalize_test_set_ids(params.get("target_test_sets")))

    for test_set_id in target_test_sets:
        existing_path = _find_test_set_path(project_root, test_set_id)
        if existing_path is None:
            template_path = _canonical_test_set_path(project_root, test_set_id)
            _write_test_set_template(template_path, test_set_id)
            issues.append(
                PreflightIssue(
                    kind="test_set",
                    path=template_path,
                    message=f"缺少目标 Test Set 资产 '{test_set_id}'，已生成模板。",
                    action_hint="补全 Test Set 内容，或先运行 `lee qa test-set create ...` 生成正式设计资产。",
                    created=True,
                )
            )
            continue

        raw = _load_yaml_file(existing_path)
        if raw is not None and _is_fill_required(raw):
            issues.append(
                PreflightIssue(
                    kind="test_set",
                    path=existing_path,
                    message=f"Test Set 模板 '{test_set_id}' 仍未补全。",
                    action_hint="补全 case、范围和追踪字段后，将 template_status 改为 ready 或直接删除该字段。",
                )
            )

    return issues


def _write_repo_registry_template(
    repos_path: Path,
    project_root: Path,
    *,
    repos: Optional[Dict[str, Any]] = None,
) -> None:
    repos_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_repos = dict(repos or {})
    project_name = _slugify(project_root.name or "project")
    if not resolved_repos:
        resolved_repos = {
            project_name: {
                "path": "./.",
                "type": "git",
                "default_branch": "main",
                "description": f"Review and replace with real repo mapping for {project_root.name}",
            }
        }
    payload = {
        "version": "1.0",
        "repos": resolved_repos,
    }
    repos_path.write_text(
        yaml.dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _write_sut_template(config_path: Path, environment: str, base_url_hint: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    protocol = "https" if base_url_hint.startswith("https://") else "http"
    template = {
        "template_status": TEMPLATE_STATUS_FILL_REQUIRED,
        "generated_by": "lee qa execute preflight",
        "sut_type": "web",
        "name": f"{environment}-fill-me",
        "base_url": base_url_hint or f"{protocol}://replace-with-real-{environment}-host",
        "base_path": "",
        "protocol": protocol,
        "auth_type": "bearer",
        "enabled": False,
        "extras": {
            "note": "Fill real host/auth data before rerunning lee qa execute.",
        },
        "metadata": {
            "environment": environment,
            "guidance": "Set template_status to ready or delete it after filling this file.",
        },
    }
    config_path.write_text(
        yaml.dump(template, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _write_test_set_template(test_set_path: Path, test_set_id: str) -> None:
    test_set_path.parent.mkdir(parents=True, exist_ok=True)
    module = _derive_module_name(test_set_id)
    template = {
        "template_status": TEMPLATE_STATUS_FILL_REQUIRED,
        "generated_by": "lee qa execute preflight",
        "test_set_id": test_set_id,
        "module": module,
        "title": f"TODO: describe scope for {test_set_id}",
        "status": "draft",
        "traceability": {
            "derived_from": ["TODO: FEAT-..."],
            "task_ref": "TODO: TASK-TESTPLAN-REL-...",
        },
        "scope": {
            "in_scope": ["TODO"],
            "out_of_scope": ["TODO"],
        },
        "cases": [
            {
                "case_id": f"{_slugify(test_set_id).upper()}-001",
                "title": "TODO: first case title",
                "priority": "P1",
                "preconditions": ["TODO"],
                "steps": ["TODO"],
                "expected_results": ["TODO"],
            }
        ],
        "notes": [
            "Fill this file or replace it with a formal Test Set asset before rerunning lee qa execute.",
            "After filling, set template_status to ready or remove the field entirely.",
        ],
    }
    test_set_path.write_text(
        yaml.dump(template, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _normalize_test_set_ids(raw_value: Any) -> Iterable[str]:
    if not isinstance(raw_value, list):
        return []
    normalized: List[str] = []
    for item in raw_value:
        candidate = str(item).strip()
        if candidate:
            normalized.append(candidate)
    return normalized


def _find_test_set_path(project_root: Path, test_set_id: str) -> Optional[Path]:
    possible_paths = [
        project_root / "spec" / "qa" / "test-sets" / f"{test_set_id}.yaml",
        project_root / "spec" / "qa" / "test-sets" / f"ts-{test_set_id}.yaml",
        _canonical_test_set_path(project_root, test_set_id),
    ]
    for candidate in possible_paths:
        if candidate.exists():
            return candidate
    return None


def _canonical_test_set_path(project_root: Path, test_set_id: str) -> Path:
    return project_root / "spec" / "qa" / "test-sets" / f"ts-{_slugify(test_set_id)}.yaml"


def _derive_module_name(test_set_id: str) -> str:
    lowered = test_set_id.removeprefix("TESTSET-")
    lowered = lowered.removeprefix("TESTSET_")
    return _slugify(lowered or test_set_id)


def _is_fill_required(raw: Dict[str, Any]) -> bool:
    status = str(raw.get("template_status") or "").strip().lower()
    return status == TEMPLATE_STATUS_FILL_REQUIRED


def _load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _slugify(value: str) -> str:
    collapsed = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower())
    return collapsed.strip("-") or "placeholder"
