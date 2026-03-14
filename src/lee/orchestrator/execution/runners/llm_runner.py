"""
LEE Orchestrator — LLM Step Runners

包含:
  - LLMRunner: 处理 agent 步骤 (kind=agent)
  - ClaudeCodeRunner: 处理 claude_code 步骤 (kind=claude_code)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import uuid
import difflib
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.artifacts import ArtifactManager
from lee.orchestrator.execution.artifacts.placement import resolve_src_root_id
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService
from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY, RetryPolicy
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext
from lee.orchestrator.execution.runners.normalization import (
    OutputExtractor,
    PmPlannerTaskNormalizer,
    PrdWriterFeatNormalizer,
    ProductReviewNormalizer,
    ReviewSemanticValidator,
    SchemaRepairHelper,
    SingleSSOTNormalizer,
    WorkflowSemanticValidator,
)
from lee.orchestrator.execution.llm_executor import LLMExecutor as RealLLMExecutor


class LLMRunner(StepRunnerBase):
    """Agent (LLM) 步骤运行器 - 使用智谱 GLM 模型"""

    DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS = [
        "output/",
        "evidence/",
        "/".join([".workflow", "claude-code", ""]),
        "pytest-temp/",
        ".codex-worktrees/",
    ]
    FEAT_TOPIC_FAMILIES = {
        "governance": [
            "cli",
            "workflow",
            "ssot",
            "gate",
            "freeze",
            "governance",
            "command",
            "approval",
            "review",
            "治理",
            "命令",
            "工作流",
            "物化",
            "放行",
            "审阅",
            "冻结",
            "约束",
        ],
        "auth_sms": [
            "sms",
            "otp",
            "mobile",
            "phone",
            "login",
            "session",
            "验证码",
            "短信",
            "手机号",
            "手机",
            "登录",
            "会话",
            "账户",
            "手机号绑定",
            "手机号解绑",
            "验证码登录",
        ],
    }
    PM_TASK_DRIFT_KEYWORDS = {
        "infra_storage": [
            "redis",
            "postgres",
            "postgresql",
            "mysql",
            "mongodb",
            "database schema",
            "db schema",
            "schema migration",
            "cache layer",
            "缓存层",
            "数据库",
            "数据库迁移",
        ],
        "gateway_auth": [
            "api gateway",
            "gateway service",
            "jwt",
            "oauth",
            "access token",
            "refresh token",
            "rate limit",
            "rate limiting",
            "ratelimit",
            "鉴权网关",
            "令牌",
            "限流",
        ],
        "deployment_ops": [
            "deployment script",
            "deploy script",
            "kubernetes",
            "helm",
            "prometheus",
            "grafana",
            "ingress",
            "nginx",
            "监控配置",
            "告警规则",
            "部署脚本",
        ],
        "product_ui": [
            "ui",
            "ux",
            "dashboard",
            "management ui",
            "admin ui",
            "page",
            "screen",
            "visualizer",
            "control panel",
            "管理界面",
            "页面",
            "界面",
            "可视化面板",
            "仪表盘",
        ],
    }
    FEAT_UI_KEYWORDS = [
        "ui",
        "ux",
        "page",
        "screen",
        "form",
        "modal",
        "dialog",
        "button",
        "wireframe",
        "界面",
        "页面",
        "线框",
        "表单",
        "弹窗",
        "按钮",
    ]
    FEAT_UI_NEGATION_PATTERNS = [
        r"(?:不涉及|无|无需|不需要|不包含|不新增).{0,6}(?:ui|ux|page|screen|component|interaction|frontend)",
        r"(?:不涉及|无|无需|不需要|不包含|不新增).{0,6}(?:界面|页面|交互|组件|前端|视觉|布局|表单|弹窗|按钮)",
    ]
    AUTHORITATIVE_CONTEXT_SKIP_KEYS = {
        "frozen_inputs",
        "ssot_materialized",
        "workspace_artifacts",
        "written_files",
        "outputs",
    }

    @staticmethod
    def _resolve_step_timeout_seconds(input_data: Dict[str, Any]) -> int:
        base_timeout = int(os.getenv("LEE_STEP_TIMEOUT_SECONDS", "300"))
        executor_timeout = input_data.get("timeout_seconds")
        try:
            executor_timeout_int = int(executor_timeout)
        except (TypeError, ValueError):
            executor_timeout_int = 0
        if executor_timeout_int > 0:
            return max(base_timeout, executor_timeout_int + 30)
        return base_timeout

    @staticmethod
    def _is_identity_formalize_step(step) -> bool:
        step_id = str(getattr(step, "id", "") or "")
        return step_id.endswith("_identity_formalize")

    @staticmethod
    def _is_identity_prepare_step(step) -> bool:
        step_id = str(getattr(step, "id", "") or "")
        return step_id.endswith("_identity_prepare")

    @classmethod
    def _resolve_step_input_sources(cls, step) -> List[str]:
        resolved: List[str] = []
        for item in getattr(step, "inputs", []) or []:
            source = item.get("source") if isinstance(item, dict) else getattr(item, "source", None)
            if isinstance(source, str) and source.strip():
                resolved.append(source.strip())
        return resolved

    @classmethod
    def _collect_payload_artifact_ids(cls, payload: Any, collected: List[str]) -> None:
        if isinstance(payload, dict):
            candidate_id = payload.get("id")
            if cls._is_literal_ssot_ref(candidate_id):
                collected.append(str(candidate_id))
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    cls._collect_payload_artifact_ids(value, collected)
        elif isinstance(payload, list):
            for item in payload:
                cls._collect_payload_artifact_ids(item, collected)
        elif cls._is_literal_ssot_ref(payload):
            collected.append(str(payload))

    @classmethod
    def _replace_text_refs(cls, text: str, replacements: Dict[str, str]) -> str:
        updated = text
        for old_id, new_id in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            updated = updated.replace(f"{old_id}#", f"{new_id}#")
            updated = updated.replace(old_id, new_id)
        return updated

    @classmethod
    def _rewrite_payload_refs(cls, payload: Any, replacements: Dict[str, str]) -> Any:
        if isinstance(payload, str):
            return cls._replace_text_refs(payload, replacements)
        if isinstance(payload, list):
            return [cls._rewrite_payload_refs(item, replacements) for item in payload]
        if isinstance(payload, dict):
            return {key: cls._rewrite_payload_refs(value, replacements) for key, value in payload.items()}
        return payload

    @classmethod
    def _extract_src_root_from_payload(
        cls,
        payload: Any,
        manager: ArtifactManager,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        if isinstance(payload, dict):
            properties = payload.get("properties") if isinstance(payload.get("properties"), dict) else {}
            source_refs = payload.get("source_refs") if isinstance(payload.get("source_refs"), list) else []
            parent_id = payload.get("parent_id") if isinstance(payload.get("parent_id"), str) else None
            artifact_id = payload.get("id") if isinstance(payload.get("id"), str) else None
            src_root_id = resolve_src_root_id(
                parent_id=parent_id or artifact_id,
                source_refs=source_refs,
                properties=properties,
            )
            if src_root_id:
                return src_root_id
            if artifact_id:
                metadata = manager.get_ssot(artifact_id)
                if metadata:
                    resolved = resolve_src_root_id(
                        parent_id=metadata.properties.get("parent_id") or metadata.id,
                        source_refs=metadata.properties.get("source_refs", []),
                        properties=metadata.properties,
                    )
                    if resolved:
                        return resolved
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    resolved = cls._extract_src_root_from_payload(value, manager, fallback=fallback)
                    if resolved:
                        return resolved
        elif isinstance(payload, list):
            for item in payload:
                resolved = cls._extract_src_root_from_payload(item, manager, fallback=fallback)
                if resolved:
                    return resolved
        elif isinstance(payload, str):
            resolved = resolve_src_root_id(parent_id=payload, source_refs=[payload], properties={})
            if resolved:
                return resolved
        return fallback

    @classmethod
    def _inject_identity_prepare_context(
        cls,
        payload: Any,
        *,
        src_root_id: Optional[str],
        mode: str,
    ) -> Any:
        if isinstance(payload, dict):
            rewritten = {
                key: cls._inject_identity_prepare_context(value, src_root_id=src_root_id, mode=mode)
                for key, value in payload.items()
            }
            if "id" in rewritten or "source_refs" in rewritten or "ssot_materialized" in rewritten:
                identity_context = dict(rewritten.get("identity_context", {}) or {})
                identity_context.setdefault("mode", mode)
                if src_root_id:
                    identity_context.setdefault("src_root_id", src_root_id)
                rewritten["identity_context"] = identity_context
            if "properties" in rewritten and isinstance(rewritten["properties"], dict) and src_root_id:
                rewritten["properties"].setdefault("src_root_id", src_root_id)
            return rewritten
        if isinstance(payload, list):
            return [
                cls._inject_identity_prepare_context(item, src_root_id=src_root_id, mode=mode)
                for item in payload
            ]
        return payload

    async def _execute_identity_prepare_step(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
        instance,
    ) -> StepResult:
        project_root = Path(ctx.project_root or ".").resolve()
        manager = ArtifactManager(project_root=project_root)

        instance_data = getattr(instance, "data", {}) or {}
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data, dict) else {}
        params = instance_data.get("params", {}) if isinstance(instance_data, dict) else {}
        input_sources = self._resolve_step_input_sources(step)

        payloads: List[Any] = []
        for source in input_sources:
            if source in step_outputs:
                payloads.append(step_outputs[source])
                continue
            aliased = f"{source}_ref" if not source.endswith("_ref") else source[:-4]
            if aliased in step_outputs:
                payloads.append(step_outputs[aliased])
                continue
            if source in params:
                payloads.append(params[source])
                continue
            if aliased in params:
                payloads.append(params[aliased])

        fallback_src_root = params.get("src_root_id") if isinstance(params.get("src_root_id"), str) else None
        src_root_id = None
        for payload in payloads:
            src_root_id = self._extract_src_root_from_payload(payload, manager, fallback=fallback_src_root)
            if src_root_id:
                break

        primary_payload = payloads[0] if payloads else {}
        rewritten_payload = self._inject_identity_prepare_context(
            primary_payload,
            src_root_id=src_root_id,
            mode="provisional",
        )
        artifact_ids: List[str] = []
        self._collect_payload_artifact_ids(primary_payload, artifact_ids)
        if isinstance(rewritten_payload, dict):
            rewritten_payload["identity_prepare_result"] = {
                "src_root_id": src_root_id,
                "mode": "provisional",
                "artifact_ids": list(dict.fromkeys(artifact_ids)),
            }
        else:
            rewritten_payload = {
                "identity_prepare_result": {
                    "src_root_id": src_root_id,
                    "mode": "provisional",
                    "artifact_ids": list(dict.fromkeys(artifact_ids)),
                }
            }

        await ctx.state_machine.complete_step(workflow_id, step.id, rewritten_payload)
        return StepResult(
            status="success",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Identity prepare completed with src_root_id={src_root_id or 'unknown'}",
            output=rewritten_payload,
        )

    async def _execute_identity_formalize_step(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
        instance,
    ) -> StepResult:
        project_root = Path(ctx.project_root or ".").resolve()
        manager = ArtifactManager(project_root=project_root)
        service = SSOTService(manager)

        instance_data = getattr(instance, "data", {}) or {}
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data, dict) else {}
        input_sources = self._resolve_step_input_sources(step)

        payloads: List[Any] = []
        for source in input_sources:
            if source in step_outputs:
                payloads.append(step_outputs[source])
                continue
            aliased = f"{source}_ref" if not source.endswith("_ref") else source[:-4]
            if aliased in step_outputs:
                payloads.append(step_outputs[aliased])

        artifact_ids: List[str] = []
        for payload in payloads:
            self._collect_payload_artifact_ids(payload, artifact_ids)
        deduped_ids: List[str] = []
        for artifact_id in artifact_ids:
            if artifact_id not in deduped_ids:
                deduped_ids.append(artifact_id)

        result = service.formalize(deduped_ids)
        replacements = result["replacements"]

        primary_payload = payloads[0] if payloads else {}
        rewritten_payload = self._rewrite_payload_refs(primary_payload, replacements)
        if isinstance(rewritten_payload, dict):
            rewritten_payload["formalize_result"] = result
            if "outputs" not in rewritten_payload and result.get("grouped_ids"):
                rewritten_payload["outputs"] = result["grouped_ids"]
        else:
            rewritten_payload = {
                "formalize_result": result,
                "outputs": result.get("grouped_ids", {}),
            }

        await ctx.state_machine.complete_step(workflow_id, step.id, rewritten_payload)
        return StepResult(
            status="success",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Identity formalize completed for {result['count']} artifacts",
            output=rewritten_payload,
        )

    def can_handle(self, step_kind: str) -> bool:
        return step_kind in ("agent", "llm")

    @staticmethod
    def _extract_feat_freeze_path(instance_data: Any) -> Optional[str]:
        if not isinstance(instance_data, dict):
            return None
        params = instance_data.get("params")
        if not isinstance(params, dict):
            return None

        for key in ("feat_freeze", "feat_freeze_ref"):
            value = params.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                for path_key in ("path", "file_path"):
                    candidate = value.get(path_key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
        return None

    @classmethod
    def _load_feat_bundle_payload(cls, instance_data: Any) -> Optional[Any]:
        feat_freeze_path = cls._extract_feat_freeze_path(instance_data)
        if not feat_freeze_path:
            return None
        path = Path(feat_freeze_path)
        if not path.exists() or not path.is_file():
            return None
        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception:
            return None
        if path.suffix.lower() == ".md":
            frontmatter = cls._load_yaml_frontmatter(path) or {}
            body = cls._extract_markdown_body(raw_text)
            return {
                "title": frontmatter.get("title"),
                "goal": body,
                "description": body,
                "source_refs": frontmatter.get("source_refs") or [],
                "parent_id": frontmatter.get("parent_id"),
            }
        try:
            return yaml.safe_load(raw_text)
        except Exception:
            return None

    @staticmethod
    def _load_yaml_frontmatter(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists() or not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return None
        if not raw.startswith("---"):
            return None
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return None
        try:
            frontmatter = yaml.safe_load(parts[1])
        except Exception:
            return None
        return frontmatter if isinstance(frontmatter, dict) else None

    @staticmethod
    def _extract_markdown_body(raw_markdown: str) -> str:
        if not isinstance(raw_markdown, str):
            return ""
        if not raw_markdown.startswith("---"):
            return raw_markdown
        parts = raw_markdown.split("---", 2)
        if len(parts) < 3:
            return raw_markdown
        return parts[2]

    @classmethod
    def _load_feat_acceptance_checks(cls, project_root: str, feat_id: str) -> List[Dict[str, Any]]:
        markdown = cls._load_ssot_markdown(project_root, feat_id)
        if (not isinstance(markdown, str) or not markdown.strip()) and isinstance(project_root, str) and feat_id:
            features_dir = Path(project_root) / "spec" / "requirements" / "features"
            if features_dir.exists():
                for candidate in sorted(features_dir.glob(f"{feat_id}__*.md")):
                    try:
                        markdown = candidate.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    if isinstance(markdown, str) and markdown.strip():
                        break
        if not isinstance(markdown, str) or not markdown.strip():
            return []

        body = cls._extract_markdown_body(markdown)
        checks: List[Dict[str, Any]] = []
        for match in re.finditer(
            r"(?ms)^##\s+(AC-[A-Za-z0-9-]+)\s*\n(.*?)(?=^##\s+AC-[A-Za-z0-9-]+\s*$|\Z)",
            body,
        ):
            ac_id = match.group(1).strip()
            block = match.group(2).strip()
            parsed: Dict[str, Any] = {"id": ac_id, "raw_text": block}
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("- Scenario:"):
                    parsed["scenario"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("- Given:"):
                    parsed["given"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("- When:"):
                    parsed["when"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("- Then:"):
                    parsed["then"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("- Trace Hints:"):
                    hints = stripped.split(":", 1)[1].strip()
                    parsed["trace_hints"] = [
                        item.strip() for item in re.split(r"[,/]", hints) if item.strip()
                    ]
            checks.append(parsed)
        return checks

    @classmethod
    def _is_structural_acceptance_check(cls, check: Dict[str, Any]) -> bool:
        if not isinstance(check, dict):
            return False
        text = " ".join(
            str(check.get(key) or "")
            for key in ("scenario", "given", "when", "then", "raw_text")
        )
        structural_keywords = (
            "rule-",
            "规则",
            "状态机",
            "state machine",
            "contract",
            "schema",
            "template",
            "边界",
            "链路",
            "路径",
            "校验",
            "优先级",
            "priority",
            "来源",
            "source",
            "source tracing",
            "cli_override",
            "旁路",
            "阻断",
            "bypass",
            "enforcement",
            "错误码",
            "routing rule",
            "validation rule",
        )
        return any(cls._text_contains_keyword(text, keyword) for keyword in structural_keywords)

    @classmethod
    def _resolve_feat_parent_epic(cls, feat_id: str, instance_data: Any) -> Optional[str]:
        feat_ref_path = None
        if isinstance(instance_data, dict):
            params = instance_data.get("params")
            if isinstance(params, dict):
                feat_ref_path = params.get("feat_freeze_ref")
        if isinstance(feat_ref_path, str) and feat_ref_path.strip():
            frontmatter = cls._load_yaml_frontmatter(Path(feat_ref_path.strip()))
            parent_id = str((frontmatter or {}).get("parent_id") or "").strip()
            if parent_id:
                return parent_id

        candidate_dir = Path("spec/requirements/features")
        if not isinstance(feat_id, str) or not feat_id.strip() or not candidate_dir.exists():
            return None
        for candidate in candidate_dir.glob(f"{feat_id.strip()}__*.md"):
            frontmatter = cls._load_yaml_frontmatter(candidate)
            parent_id = str((frontmatter or {}).get("parent_id") or "").strip()
            if parent_id:
                return parent_id
        return None

    @classmethod
    def _feat_bundle_requires_ui(cls, instance_data: Any) -> Optional[bool]:
        payload = cls._load_feat_bundle_payload(instance_data)
        if payload is None:
            return None

        fragments: List[str] = []

        def _collect(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(key, str) and key.lower() in {
                        "title",
                        "description",
                        "objective",
                        "goal",
                        "user_value",
                        "requirement",
                        "acceptance",
                        "acceptance_criteria",
                        "interface_spec",
                        "workflow_steps",
                        "outputs",
                    }:
                        _collect(item)
                    elif key in {"feat_specs", "feat_specifications"}:
                        _collect(item)
            elif isinstance(value, list):
                for item in value:
                    _collect(item)
            elif isinstance(value, str) and value.strip():
                fragments.append(value.strip())

        _collect(payload)
        if not fragments:
            return None

        text = "\n".join(fragments)
        normalized_text = text
        for pattern in cls.FEAT_UI_NEGATION_PATTERNS:
            normalized_text = re.sub(pattern, " ", normalized_text, flags=re.IGNORECASE)
        return any(cls._text_contains_keyword(normalized_text, keyword) for keyword in cls.FEAT_UI_KEYWORDS)

    @staticmethod
    def _extract_step_written_markdown(
        step_id: str,
        structured_payload: Any,
    ) -> Optional[str]:
        if not isinstance(structured_payload, dict):
            return None
        candidate_paths: List[str] = []
        for key in ("written_files", "workspace_artifacts", "paths"):
            value = structured_payload.get(key)
            if isinstance(value, list):
                candidate_paths.extend(str(item) for item in value if isinstance(item, (str, Path)))

        expected_keyword = {
            "ui_design": "ui-prototype",
            "tech_design": "technical-architecture",
        }.get(step_id)
        for path_text in candidate_paths:
            path = Path(path_text)
            if path.suffix.lower() != ".md":
                continue
            if expected_keyword and expected_keyword not in path.name.lower():
                continue
            if not path.exists() or not path.is_file():
                continue
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                continue
        return None

    async def _complete_non_ui_design_step(
        self,
        *,
        workflow_id: str,
        step,
        ctx: RunnerContext,
        execution_id: str,
        reason: str,
    ) -> StepResult:
        business_output = {
            "applicable": False,
            "ui_required": False,
            "skip_reason": reason,
        }
        output_data = {
            "generated_text": "",
            "written_files": [],
            "agent_id": getattr(step, "agent_id", ""),
            "business_output": business_output,
            "structured_payload": {"business_output": business_output},
            "completion_summary": self._build_completion_summary(
                step=step,
                written_files=[],
                structured_payload={"business_output": business_output},
                governance_preflight={"warnings": []},
            ),
        }
        result = await ctx.state_machine.complete_step(
            workflow_id,
            step.id,
            output_data,
            step_outputs=step.outputs if hasattr(step, "outputs") else None,
        )
        await ctx.store.update_task_execution(
            execution_id,
            TaskExecutionStatus.COMPLETED,
            output_data=output_data,
            completed_at=datetime.now(),
        )
        ctx.event_log.log_step_completed(
            step_id=step.id,
            agent_id=getattr(step, "agent_id", "") or "",
            outputs=[],
            outputs_hash=ctx.event_log._compute_hash(output_data),
        )
        result.message = f"Step {step.id} completed. UI design not applicable."
        return result

    def __init__(self, profile: str = "qwen", config_path: str = None,
                 fallback_providers: list = None,
                 **kwargs):
        self.profile = profile
        self.config_path = config_path
        self.fallback_providers = fallback_providers

        self._executor = RealLLMExecutor(
            profile=profile,
            config_path=config_path,
            fallback_providers=fallback_providers
        )

    def _build_executor_input(
        self,
        *,
        executor_type: str,
        step,
        ctx: RunnerContext,
        instance,
        workflow_id: str,
        agent_ctx,
        step_token: Optional[str],
    ) -> Dict[str, Any]:
        if executor_type in ("codex", "claude_code", "kimi"):
            code_config = step.config.get("claude_code", {}) if step.config else {}
            workspace = ctx.resolve_workdir(step, instance.data.get("run_id", workflow_id))
            context_files = self._merge_context_files(
                self._collect_authoritative_context_files(step, instance.data),
                code_config.get("context_files", []),
            )
            input_data: Dict[str, Any] = {
                "goal": agent_ctx.user_prompt or code_config.get("goal", ""),
                "workspace": workspace,
                "context_files": context_files,
                "write_scope": code_config.get("write_scope", []),
                "read_only": bool(code_config.get("read_only", False)),
                "forbidden_read_paths": self._merge_forbidden_read_paths(
                    code_config.get("forbidden_read_paths")
                ),
                "max_iterations": code_config.get("max_iterations", 5),
                "timeout_seconds": code_config.get("timeout_seconds", 3600),
                "timeout_retries": code_config.get("timeout_retries", 1),
                "retry_backoff_seconds": code_config.get("retry_backoff_seconds", 5),
                "stop_conditions": code_config.get("stop_conditions", {}),
                "system_prompt_extra": agent_ctx.system_prompt or "",
            }
            if code_config.get("allowed_commands"):
                input_data["allowed_commands"] = code_config.get("allowed_commands")
            if code_config.get("model"):
                input_data["model"] = code_config.get("model")
            if "silence_timeout_seconds" in code_config:
                input_data["silence_timeout_seconds"] = code_config.get("silence_timeout_seconds")
            if "silence_grace_seconds" in code_config:
                input_data["silence_grace_seconds"] = code_config.get("silence_grace_seconds")
            if "max_bash_calls" in code_config:
                input_data["max_bash_calls"] = code_config.get("max_bash_calls")
            if "resume_on_retry" in code_config:
                input_data["resume_on_retry"] = bool(code_config.get("resume_on_retry"))
        else:
            input_data = {
                "system_message": agent_ctx.system_prompt,
                "prompt": agent_ctx.user_prompt,
                "temperature": agent_ctx.temperature,
                "max_tokens": agent_ctx.max_tokens,
            }
            input_data = self._inject_authoritative_feat_review_bundle(
                step=step,
                instance_data=getattr(instance, "data", {}) or {},
                input_data=input_data,
            )

        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)
        return input_data

    @classmethod
    def _inject_authoritative_feat_review_bundle(
        cls,
        *,
        step,
        instance_data: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if getattr(step, "agent_id", "") != "agent.product.feat_reviewer":
            return input_data
        if not isinstance(input_data, dict):
            return input_data

        prompt = str(input_data.get("prompt") or "")
        if "Authoritative FEAT Bundle" in prompt:
            return input_data

        feat_bundle = cls._extract_feat_review_bundle_from_instance_data(instance_data)
        if not isinstance(feat_bundle, dict):
            return input_data
        feat_specs = feat_bundle.get("feat_specs")
        if not isinstance(feat_specs, list) or not feat_specs:
            return input_data

        authoritative_block = (
            "\n\n## Authoritative FEAT Bundle\n"
            "Ignore any stale review memo or executor metadata shown above.\n"
            "Review only the following FEAT bundle as the source of truth for subject_refs, acceptance_checks, inputs, input_contract, and dependencies.\n"
            "```json\n"
            f"{json.dumps(feat_bundle, ensure_ascii=False, indent=2)}\n"
            "```"
        )
        rewritten = dict(input_data)
        rewritten["prompt"] = prompt + authoritative_block
        return rewritten

    @classmethod
    def _extract_feat_review_bundle_from_instance_data(
        cls,
        instance_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        step_outputs = instance_data.get("step_outputs") if isinstance(instance_data, dict) else {}
        step_outputs = step_outputs if isinstance(step_outputs, dict) else {}
        feat_output = step_outputs.get("feat_spec_generation")
        if isinstance(feat_output, dict):
            direct_business = feat_output.get("business_output")
            if isinstance(direct_business, dict) and isinstance(direct_business.get("feat_specs"), list):
                return direct_business
            generated_text = feat_output.get("generated_text")
            if isinstance(generated_text, str) and generated_text.strip():
                parsed = cls._parse_structured_output_if_possible(generated_text)
                if isinstance(parsed, dict):
                    business_output = parsed.get("business_output")
                    if isinstance(business_output, dict) and isinstance(business_output.get("feat_specs"), list):
                        return business_output
                    if isinstance(parsed.get("feat_specs"), list):
                        return parsed

        feat_bundle = cls._load_feat_bundle_payload(instance_data)
        return feat_bundle if isinstance(feat_bundle, dict) else None

    @classmethod
    def _merge_forbidden_read_paths(cls, configured_paths: Any) -> List[str]:
        merged: List[str] = []
        for raw_path in cls.DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS:
            normalized = str(raw_path).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
        if isinstance(configured_paths, list):
            for raw_path in configured_paths:
                normalized = str(raw_path).strip()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    @staticmethod
    def _merge_context_files(*groups: Any) -> List[str]:
        merged: List[str] = []
        for group in groups:
            if not isinstance(group, list):
                continue
            for raw_path in group:
                normalized = str(raw_path).strip()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    @classmethod
    def _collect_authoritative_context_files(cls, step, instance_data: Optional[Dict[str, Any]]) -> List[str]:
        if not step or not isinstance(instance_data, dict):
            return []

        raw_inputs = getattr(step, "inputs", None)
        if not isinstance(raw_inputs, list):
            return []

        params = instance_data.get("params", {}) if isinstance(instance_data.get("params", {}), dict) else {}
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data.get("step_outputs", {}), dict) else {}
        data = instance_data if isinstance(instance_data, dict) else {}

        collected: List[str] = []
        for item in raw_inputs:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            if not isinstance(source, str) or not source.strip():
                continue
            value = cls._resolve_authoritative_input_value(
                source=source,
                data=data,
                params=params,
                step_outputs=step_outputs,
            )
            cls._extract_context_file_paths(value, collected)
        return collected

    @classmethod
    def _resolve_authoritative_input_value(
        cls,
        *,
        source: str,
        data: Dict[str, Any],
        params: Dict[str, Any],
        step_outputs: Dict[str, Any],
    ) -> Any:
        candidate_keys = [source]
        if source.endswith("_freeze"):
            candidate_keys.append(f"{source}_ref")
        elif source.endswith("_freeze_ref"):
            candidate_keys.append(source[:-4])

        for key in candidate_keys:
            if key in data:
                return data[key]
            if key in params:
                return params[key]
            if key in step_outputs:
                return step_outputs[key]
        return None

    @classmethod
    def _extract_context_file_paths(cls, value: Any, collected: List[str]) -> None:
        if isinstance(value, dict):
            for key in ("resolved_path", "path"):
                raw_path = value.get(key)
                if isinstance(raw_path, str):
                    normalized = raw_path.strip()
                    if normalized and normalized not in collected:
                        collected.append(normalized)
            for key, nested in value.items():
                if key in cls.AUTHORITATIVE_CONTEXT_SKIP_KEYS:
                    continue
                cls._extract_context_file_paths(nested, collected)
            return

        if isinstance(value, list):
            for item in value:
                cls._extract_context_file_paths(item, collected)

    @staticmethod
    def _coerce_output_file_value(raw_text: str) -> Any:
        text = (raw_text or "").strip()
        stripped = StepRunnerBase._strip_code_fence(text)
        if not stripped:
            return ""
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if re.fullmatch(r"-?\d+", stripped):
            try:
                return int(stripped)
            except ValueError:
                pass
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            try:
                return float(stripped)
            except ValueError:
                pass
        return stripped

    @staticmethod
    def _extract_named_output_segment(raw_text: str, output_name: str) -> str:
        text = (raw_text or "").strip()
        if not text or not output_name:
            return text

        lines = text.splitlines()
        start_index: Optional[int] = None
        token = f"`{output_name}`"
        for index, line in enumerate(lines):
            stripped = line.strip()
            is_output_heading = stripped.startswith("#") or bool(re.match(r"^\d+\.\s+", stripped))
            if is_output_heading and token in stripped:
                start_index = index + 1
                break

        if start_index is None:
            return text

        body_lines: List[str] = []
        for line in lines[start_index:]:
            stripped = line.strip()
            if stripped == "---":
                break
            is_output_heading = stripped.startswith("#") or bool(re.match(r"^\d+\.\s+", stripped))
            if is_output_heading and "`" in stripped:
                break
            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if body:
            return body
        return text

    def _extract_declared_output_values(
        self,
        step,
        written_files: List[str],
        project_root: Optional[str],
        generated_text: str = "",
    ) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        if not step.outputs:
            return extracted

        written_index = {Path(path).name: Path(path) for path in written_files}
        for output_spec in step.outputs:
            raw_path = getattr(output_spec, "path", None)
            if not raw_path:
                continue
            normalized_path = self._normalize_project_relative_path(str(raw_path))
            path_obj = Path(normalized_path)
            file_name = path_obj.name
            key_name = path_obj.stem if path_obj.suffix else file_name
            if "/" in normalized_path or "\\" in normalized_path:
                continue
            try:
                matched_path = written_index.get(file_name)
                raw_text = ""
                if matched_path and matched_path.exists() and not matched_path.is_dir():
                    raw_text = matched_path.read_text(encoding="utf-8")
                elif generated_text:
                    raw_text = generated_text
                else:
                    continue
                if key_name:
                    raw_text = self._extract_named_output_segment(raw_text, key_name)
                extracted[key_name] = self._coerce_output_file_value(raw_text)
            except Exception:
                continue
        return extracted

    def _resolve_spec_writeback_payload(
        self,
        *,
        step,
        structured_payload: Optional[Any],
        generated_text: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if isinstance(structured_payload, dict):
            payload.update(structured_payload)
            business_output = structured_payload.get("business_output")
            if isinstance(business_output, dict):
                payload.update({k: v for k, v in business_output.items() if k not in payload})

        for key in ("maintained_spec_path", "target_spec_path", "spec_path"):
            if key in payload and payload[key]:
                payload["maintained_spec_path"] = payload[key]
                break

        for key in ("maintained_spec_content", "target_spec_content", "spec_content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                payload["maintained_spec_content"] = self._strip_code_fence(value).strip()
                break
        else:
            for key in ("maintained_spec_content", "target_spec_content", "spec_content"):
                segment = self._extract_named_output_segment(generated_text, key)
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_content"] = self._strip_code_fence(segment).strip()
                    break

        if not payload.get("maintained_spec_content"):
            target_ref = ((step.config or {}).get("spec_writeback") or {}).get("target_path")
            if target_ref:
                segment = self._extract_named_output_segment(generated_text, str(target_ref))
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_content"] = self._strip_code_fence(segment).strip()

        if not payload.get("maintained_spec_path"):
            for key in ("maintained_spec_path", "target_spec_path", "spec_path"):
                segment = self._extract_named_output_segment(generated_text, key)
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_path"] = self._strip_code_fence(segment).strip()
                    break

        return payload

    def _apply_spec_writeback(
        self,
        *,
        step,
        project_root: Optional[str],
        structured_payload: Optional[Any],
        generated_text: str,
    ) -> Optional[Dict[str, Any]]:
        writeback_config = ((step.config or {}).get("spec_writeback") or {})
        if not writeback_config.get("enabled"):
            return None

        payload = self._resolve_spec_writeback_payload(
            step=step,
            structured_payload=structured_payload,
            generated_text=generated_text,
        )

        target_ref = (
            writeback_config.get("target_path")
            or payload.get("maintained_spec_path")
            or payload.get("target_spec_path")
        )
        content = payload.get("maintained_spec_content")
        if not target_ref or not isinstance(content, str) or not content.strip():
            return {
                "enabled": True,
                "applied": False,
                "reason": "missing_target_path_or_spec_content",
            }

        normalized_target = self._normalize_project_relative_path(str(target_ref))
        target_path = Path(normalized_target)
        if not target_path.is_absolute():
            target_path = (Path(project_root or ".").resolve() / target_path).resolve()

        existing_content = ""
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")

        new_content = content.strip()
        changed = existing_content != new_content
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_content, encoding="utf-8")

        diff_report_path = writeback_config.get("diff_report_path")
        diff_report: Optional[Path] = None
        diff_text = ""
        if diff_report_path:
            normalized_diff = self._normalize_project_relative_path(str(diff_report_path))
            diff_report = Path(normalized_diff)
            if not diff_report.is_absolute():
                diff_report = (Path(project_root or ".").resolve() / diff_report).resolve()
            diff_report.parent.mkdir(parents=True, exist_ok=True)
            diff_lines = list(
                difflib.unified_diff(
                    existing_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(target_path),
                    tofile=str(target_path),
                    lineterm="",
                )
            )
            diff_text = "\n".join(diff_lines).strip()
            if not diff_text:
                diff_text = f"No content changes for {target_path}\n"
            diff_report.write_text(diff_text, encoding="utf-8")

        written_files = [str(target_path)]
        if diff_report:
            written_files.append(str(diff_report))

        return {
            "enabled": True,
            "applied": True,
            "changed": changed,
            "target_path": str(target_path),
            "diff_report_path": str(diff_report) if diff_report else None,
            "diff_preview": diff_text[:2000] if diff_text else "",
            "written_files": written_files,
        }

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Agent 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 agent spec 加载 prompt，执行后处理输出文件
        """
        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "template_id": instance.template_id,
            "project_name": instance.data.get("project_name", "ai-marathon-coach"),
            "data": instance.data,
        }

        # v3.1: 注入已发现的契约路径到工作流上下文
        try:
            contract_inputs = ctx.contract_discovery.get_workflow_inputs(
                instance.template_id
            )
            if contract_inputs:
                workflow_context["contract_inputs"] = contract_inputs
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                f"Contract discovery failed for template {instance.template_id}: {e}"
            )
            pass  # 契约发现失败不阻塞执行

        # 1. 构建 Agent 执行上下文（包含 prompt）
        agent_ctx = await ctx.agent_context_builder.build(step, workflow_context)

        # v3.1: ToolGuard - 签发步骤令牌
        step_token = None
        try:
            default_perms = ["read", "write"]
            if step.executor_type == "shell":
                default_perms = ["read", "write", "execute"]
            step_token = ctx.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=default_perms,
            )
        except Exception:
            pass  # token 签发失败不阻塞执行

        # 2. 解析 executor_type：CLI 参数优先级最高
        executor_type = instance.data.get("executor_override") or step.executor_type or "claude_code"

        input_data = self._build_executor_input(
            executor_type=executor_type,
            step=step,
            ctx=ctx,
            instance=instance,
            workflow_id=workflow_id,
            agent_ctx=agent_ctx,
            step_token=step_token,
        )

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=executor_type,
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await ctx.store.create_task_execution(execution)

        if getattr(step, "agent_id", "") == "agent.design.ui_designer":
            ui_required = self._feat_bundle_requires_ui(instance.data)
            if ui_required is False:
                return await self._complete_non_ui_design_step(
                    workflow_id=workflow_id,
                    step=step,
                    ctx=ctx,
                    execution_id=execution_id,
                    reason="Source FEAT bundle does not describe any UI surface.",
                )

        # P0-5: 记录步骤执行开始日志
        import logging
        logging.info(f"[LLMRunner] Starting execution for step {step.id} (workflow={workflow_id}, execution={execution_id})")

        try:
            # 3. 调用 LLM Executor
            # 优先使用 workflow instance 绑定的 llm_profile，再看环境变量，
            # 否则从配置文件读取 default_profile，最后兜底为 huawei_deepseek。
            default_profile = ctx.llm_config_loader.get_default_profile() if hasattr(ctx, 'llm_config_loader') else "huawei_deepseek"
            selected_profile = (
                instance.data.get("llm_profile")
                or ("qwen" if executor_type == "qwen" else None)
                or ("kimi" if executor_type == "kimi" else None)
                or os.getenv("LLM_PROFILE")
                or default_profile
            )
            executor = ctx.executor_factory.create(
                executor_type,
                profile=selected_profile,
                agent_id=step.agent_id or ""
            )

            # v3.5: 步骤级超时保护
            import asyncio
            STEP_TIMEOUT = self._resolve_step_timeout_seconds(input_data)

            # v3.4: AsyncRetryExecutor 包裹 LLM 调用
            retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)

            try:
                retry_result = await asyncio.wait_for(
                    retry_executor.execute(executor.execute, input_data),
                    timeout=STEP_TIMEOUT
                )
            except asyncio.TimeoutError:
                error_msg = f"Step execution timeout after {STEP_TIMEOUT}s"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=error_msg,
                )

            if not retry_result.success:
                error_msg = retry_result.final_error or "LLM call failed after retries"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=f"Retry exhausted ({retry_result.total_attempts} attempts): {error_msg}",
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"LLM execution failed after {retry_result.total_attempts} attempts: {error_msg}",
                )

            llm_output = retry_result.result

            # 检查 LLM 调用是否成功
            if llm_output.get("status") == "failed":
                error_msg = llm_output.get("error", "Unknown error")
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"LLM execution failed: {error_msg}",
                )

            generated_text = llm_output.get("generated_text", "")

            # 检查是否生成了内容
            if not generated_text or not generated_text.strip():
                await ctx.state_machine.fail_step(workflow_id, step.id, "LLM returned empty response")
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message="LLM returned empty response",
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="LLM returned empty response",
                )

            structured_payload = self._parse_structured_output_if_possible(generated_text)
            agent_spec = self._load_agent_spec_for_step(ctx, step)
            governance_preflight = self._evaluate_governance_preflight(
                step=step,
                agent_spec=agent_spec,
                project_root=ctx.project_root,
                structured_payload=structured_payload,
            )
            spec_writeback = self._apply_spec_writeback(
                step=step,
                project_root=ctx.project_root,
                structured_payload=structured_payload,
                generated_text=generated_text,
            )
            # 3. 处理输出文件
            written_files = []
            file_outputs = [
                output
                for output in (step.outputs or [])
                if getattr(output, "type", None) in {"file", "dir"} and getattr(output, "path", None)
            ]
            if file_outputs:
                try:
                    written_files = await ctx.file_output_handler.handle(
                        generated_text,
                        file_outputs,
                        workflow_context
                    )
                except Exception as e:
                    print(f"[FileOutputHandler] Warning: {e}")

            if spec_writeback and spec_writeback.get("applied"):
                writeback_files = spec_writeback.get("written_files", [])
                written_files = list(
                    dict.fromkeys(written_files + writeback_files)
                )

            # v1.0: SSOT 集成 - 注册写入的文件为产出物
            if written_files:
                await self._collect_evidence(ctx, workflow_id, step.id, written_files)
                await self._register_artifacts(ctx, workflow_id, step.id, written_files, generated_text)

            # 4. Verifiers (if configured)
            verifier_results = await self._run_verifiers(ctx, workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(ctx, verifier_results):
                await ctx.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # v3.4: 输出 Contract Schema 校验
            business_output = self._extract_business_output_payload(
                structured_payload,
                generated_text,
                step=step,
                written_files=written_files,
            )
            business_output, structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=business_output,
                structured_payload=structured_payload,
                instance_data=instance.data,
            )
            validation_result = self._validate_step_output(step, business_output)
            if validation_result and not validation_result.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {validation_result.errors[0].message if validation_result.errors else 'unknown'}"
                    repaired = await self._attempt_schema_repair(
                        executor=executor,
                        executor_type=executor_type,
                        input_data=input_data,
                        step=step,
                        workflow_id=workflow_id,
                        validation_error=error_msg,
                        business_output=business_output,
                        structured_payload=structured_payload,
                    )
                    if repaired:
                        repaired_validation = self._validate_step_output(step, repaired["business_output"])
                        if not repaired_validation or repaired_validation.passed:
                            business_output = repaired["business_output"]
                            structured_payload = repaired["structured_payload"]
                            generated_text = repaired["output"].get("generated_text", generated_text)
                            validation_result = repaired_validation
                            repaired_workspace_files = self._materialize_symbolic_workspace_outputs(
                                step=step,
                                workflow_id=workflow_id,
                                project_root=ctx.project_root,
                                business_output=business_output,
                                structured_payload=structured_payload,
                            )
                            if repaired_workspace_files:
                                written_files = list(dict.fromkeys(written_files + repaired_workspace_files))
                        else:
                            error_msg = (
                                "Output schema validation failed after repair retry: "
                                f"{repaired_validation.errors[0].message if repaired_validation.errors else 'unknown'}"
                            )
                            validation_result = repaired_validation
                    if validation_result and not validation_result.passed:
                        await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                        await ctx.store.update_task_execution(
                            execution_id,
                            TaskExecutionStatus.FAILED,
                            output_data={
                                "generated_text": generated_text,
                                "business_output": business_output,
                                "validation_result": validation_result.to_dict(),
                            },
                            error_message=error_msg,
                            completed_at=datetime.now(),
                        )
                        return StepResult(
                            status="failed",
                            step_id=step.id,
                            workflow_id=workflow_id,
                            message=error_msg,
                        )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

            feat_review_subject_error = None
            expected_subject_refs: List[str] = []
            if getattr(step, "agent_id", "") == "agent.product.feat_reviewer":
                expected_subject_refs = self._expected_feat_review_subject_refs(instance.data)
                feat_review_subject_error = self._validate_feat_review_subject_refs(
                    business_output,
                    expected_subject_refs,
                )
                if not feat_review_subject_error:
                    feat_review_subject_error = self._validate_feat_review_semantics(
                        business_output,
                        expected_subject_refs,
                    )
            if feat_review_subject_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, feat_review_subject_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "business_output": business_output,
                        "expected_subject_refs": expected_subject_refs,
                    },
                    error_message=feat_review_subject_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=feat_review_subject_error,
                )

            semantic_error = None
            agent_id = getattr(step, "agent_id", "")
            if agent_id == "agent.product.prd_writer":
                semantic_error = self._validate_feat_bundle_epic_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            elif agent_id == "agent.product.pm_planner":
                semantic_error = self._validate_pm_planner_task_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            elif agent_id == "agent.product.delivery_plan_reviewer":
                expected_subject_refs = self._expected_delivery_plan_subject_refs(
                    instance.data,
                    business_output,
                )
                semantic_error = self._validate_delivery_plan_review_subject_refs(
                    business_output,
                    expected_subject_refs,
                )
                if not semantic_error:
                    semantic_error = self._validate_delivery_plan_review_semantics(
                        project_root=ctx.project_root,
                        review_payload=business_output,
                        instance_data=instance.data,
                    )
            if semantic_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, semantic_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "business_output": business_output,
                    },
                    error_message=semantic_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=semantic_error,
                )

            if governance_preflight["warnings"]:
                for warning in governance_preflight["warnings"]:
                    print(f"[Governance] Warning: Step {step.id}: {warning}")

            governance_strict = bool((step.config or {}).get("strict_governance"))
            if governance_preflight["implementation_facing"] and not governance_preflight["allow_full_completion"]:
                if governance_strict:
                    error_msg = (
                        "Governance preflight failed: no formal SSOT truth source and no Acceptance Brief or Module Contract found"
                    )
                    await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                    return StepResult(
                        status="failed",
                        step_id=step.id,
                        workflow_id=workflow_id,
                        message=error_msg,
                    )

            # SSOT agent output contract 校验与物化
            ssot_materialized = await self._materialize_ssot_outputs(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                generated_text=generated_text,
                structured_payload=structured_payload,
                written_files=written_files,
            )
            if ssot_materialized:
                materialized_files = ssot_materialized.get("materialized_files", [])
                if materialized_files:
                    await self._collect_evidence(ctx, workflow_id, step.id, materialized_files)
                written_files = list(dict.fromkeys(written_files + materialized_files))

            workspace_files = self._materialize_symbolic_workspace_outputs(
                step=step,
                workflow_id=workflow_id,
                project_root=ctx.project_root,
                business_output=business_output,
                structured_payload=structured_payload,
            )
            if workspace_files:
                written_files = list(dict.fromkeys(written_files + workspace_files))

            # 5. 完成步骤
            output_data = {
                "generated_text": generated_text,
                "written_files": written_files,
                "agent_id": step.agent_id,
                "llm_meta": {
                    "model": llm_output.get("model"),
                    "provider": llm_output.get("provider"),
                    "tokens_used": llm_output.get("tokens_used"),
                    "input_tokens": llm_output.get("input_tokens"),
                    "output_tokens": llm_output.get("output_tokens"),
                    "duration_seconds": llm_output.get("duration_seconds"),
                    "stop_reason": llm_output.get("stop_reason"),
                },
            }
            output_data.update(
                self._extract_declared_output_values(
                    step=step,
                    written_files=written_files,
                    project_root=ctx.project_root,
                    generated_text=generated_text,
                )
            )
            if ssot_materialized:
                output_data["ssot_materialized"] = ssot_materialized["outputs"]
            if spec_writeback:
                output_data["spec_writeback"] = spec_writeback
                if spec_writeback.get("target_path"):
                    output_data["maintained_spec_path"] = spec_writeback["target_path"]
            output_data["governance_preflight"] = governance_preflight
            output_data["completion_summary"] = self._build_completion_summary(
                step=step,
                written_files=written_files,
                structured_payload=structured_payload,
                governance_preflight=governance_preflight,
            )

            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output_data,
                step_outputs=step.outputs if hasattr(step, 'outputs') else None
            )

            # P0-1: 确保 task_execution 状态更新（BUG-2026-0038）
            # 使用 try-except 确保即使 update 失败也不会丢失步骤完成状态
            try:
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.COMPLETED,
                    output_data=output_data,
                    completed_at=datetime.now()
                )
                # P0-5: 记录 task_execution 更新日志
                import logging
                logging.info(f"[LLMRunner] Updated task_execution {execution_id} to COMPLETED for step {step.id}")
            except Exception as update_error:
                # 记录错误但不抛出，因为步骤已经完成
                logging.error(f"[LLMRunner] Failed to update task_execution {execution_id}: {update_error}")

            ctx.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "",
                outputs=written_files,
                outputs_hash=ctx.event_log._compute_hash(output_data),
            )

            if written_files:
                result.message = f"Step {step.id} completed. Files written: {', '.join(written_files)}"
            else:
                result.message = f"Step {step.id} completed. No files written (outputs may be empty)"

            return result

        except Exception as e:
            await ctx.state_machine.fail_step(workflow_id, step.id, str(e))
            await ctx.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.now()
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error: {e}",
            )
        finally:
            if step_token:
                try:
                    ctx.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass

    async def _materialize_ssot_outputs(
        self,
        ctx: RunnerContext,
        step,
        workflow_id: str,
        generated_text: str,
        structured_payload: Optional[Any] = None,
        written_files: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        If the agent spec declares ssot_output_schema, validate and materialize it.
        """
        agent_spec = self._load_agent_spec_for_step(ctx, step)
        contracts = getattr(agent_spec, "contracts", {}) or {} if agent_spec else {}
        schema_ref = contracts.get("ssot_output_schema")

        if structured_payload is None:
            structured_payload = self._parse_structured_output_if_possible(generated_text)

        contract_data = self._extract_ssot_contract_payload(
            structured_payload,
            generated_text=generated_text,
        )
        if not schema_ref and contract_data is None:
            return self._materialize_workspace_formal_ssot_markdown(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                written_files=written_files,
            )
        if contract_data is None:
            try:
                contract_data = self._parse_structured_output(generated_text)
            except ValueError as exc:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    raise
                print(f"[SSOTContract] Warning: Step {step.id} structured output parse failed: {exc}")
                return self._materialize_workspace_formal_ssot_markdown(
                    ctx=ctx,
                    step=step,
                    workflow_id=workflow_id,
                    written_files=written_files,
                )

        if contract_data is None:
            strict = (step.config or {}).get("strict_output_validation", False)
            if strict:
                raise ValueError("SSOT output schema declared but no ssot_output_contract found")
            print(f"[SSOTContract] Warning: Step {step.id} missing ssot_output_contract payload")
            return self._materialize_workspace_formal_ssot_markdown(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                written_files=written_files,
            )

        if schema_ref:
            schema_path = self._resolve_contract_path(
                schema_ref=schema_ref,
                spec_path=getattr(agent_spec, "spec_path", None),
                project_root=ctx.project_root,
            )
        else:
            from lee.orchestrator.execution.artifacts.ssot_contract import DEFAULT_SSOT_CONTRACT_SCHEMA

            schema_path = str(Path(DEFAULT_SSOT_CONTRACT_SCHEMA).resolve())
        contract_data = self._normalize_ssot_contract_payload(contract_data)

        try:
            from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTContractMaterializer

            manager = ArtifactManager(
                project_root=Path(ctx.project_root or ".").resolve(),
            )
            materializer = SSOTContractMaterializer(manager, schema_path=Path(schema_path))
            outputs = materializer.materialize(contract_data)
        except Exception as exc:
            strict = (step.config or {}).get("strict_output_validation", False)
            if strict:
                raise
            print(f"[SSOTContract] Warning: Step {step.id} SSOT materialization failed: {exc}")
            return self._materialize_workspace_formal_ssot_markdown(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                written_files=written_files,
            )

        materialized_summary = {}
        materialized_files: List[str] = []
        for key, item in outputs.items():
            artifact = item.artifact
            materialized_summary[key] = {
                "id": artifact.id,
                "identity_kind": item.identity_kind,
                "path": artifact.path,
                "path_root": artifact.path_root,
                "parent_id": artifact.properties.get("parent_id"),
            }
            materialized_files.append(str(artifact.absolute_path))

        return {
            "schema_path": schema_path,
            "outputs": materialized_summary,
            "materialized_files": materialized_files,
        }

    @staticmethod
    def _materialize_workspace_formal_ssot_markdown(
        ctx: RunnerContext,
        step,
        workflow_id: str,
        written_files: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        if getattr(step, "id", "") not in {"ui_design", "tech_design"}:
            return None

        candidate_paths = [Path(path) for path in (written_files or []) if isinstance(path, str) and path.strip()]
        if not candidate_paths:
            return None

        try:
            from lee.orchestrator.execution.artifacts import ArtifactManager
            from lee.orchestrator.execution.artifacts.ssot_files import parse_front_matter
            from lee.orchestrator.execution.artifacts.types import ArtifactStatus, SSOTType
        except Exception:
            return None

        manager = ArtifactManager(project_root=Path(ctx.project_root or ".").resolve())
        materialized_summary: Dict[str, Any] = {}
        materialized_files: List[str] = []

        ssot_type_aliases = {
            "frozen_technical_architecture": ("tech", "tech_spec"),
            "frozen_ui_prototype": ("ui", "ui_prototype"),
        }

        for path in candidate_paths:
            if not path.exists() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
                continue
            if path.suffix.lower() in {".yaml", ".yml"}:
                if getattr(step, "id", "") != "tech_design":
                    continue
                feat_match = re.search(r"(FEAT-[A-Za-z0-9-]+)", path.stem, re.IGNORECASE)
                parent_id = feat_match.group(1).upper() if feat_match else None
                if not parent_id:
                    continue
                raw_text = path.read_text(encoding="utf-8").strip()
                title_line = next(
                    (
                        line.lstrip("#").strip()
                        for line in raw_text.splitlines()
                        if line.strip().startswith("#")
                    ),
                    "",
                )
                artifact = manager.create_ssot(
                    ssot_type=SSOTType.TECH,
                    title=title_line or path.stem.replace("-", " "),
                    content=raw_text,
                    run_id=workflow_id,
                    formal_id="",
                    parent_id=parent_id,
                    derived_from=[],
                    source_refs=[f"{parent_id}#scope"],
                    owner=None,
                    tags=[],
                    status=ArtifactStatus.FROZEN,
                    version="v1",
                    properties={"workspace_source": path.name, "identity_kind": "ssot"},
                )
                materialized_summary["tech_spec"] = {
                    "id": artifact.id,
                    "identity_kind": "ssot",
                    "path": artifact.path,
                    "path_root": artifact.path_root,
                    "parent_id": artifact.properties.get("parent_id"),
                }
                materialized_files.append(str(artifact.absolute_path))
                continue
            try:
                front_matter, body = parse_front_matter(path)
            except Exception:
                continue

            artifact_id = front_matter.get("id")
            ssot_type_value = front_matter.get("ssot_type")
            title = front_matter.get("title")
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                continue
            if not isinstance(ssot_type_value, str) or not ssot_type_value.strip():
                continue
            normalized_ssot_type_value, output_key = ssot_type_aliases.get(
                ssot_type_value.strip().lower(),
                (ssot_type_value.strip().lower(), None),
            )
            try:
                ssot_type = SSOTType(normalized_ssot_type_value)
            except Exception:
                continue

            try:
                status = ArtifactStatus(str(front_matter.get("status", "active")).upper())
            except Exception:
                status = ArtifactStatus.ACTIVE

            formal_id = artifact_id.strip()
            if ssot_type == SSOTType.TECH and not formal_id.startswith("TECH-"):
                formal_id = ""
            if ssot_type == SSOTType.UI and not formal_id.startswith("UI-"):
                formal_id = ""

            derived_from_ids = front_matter.get("derived_from_ids")
            source_refs = front_matter.get("source_refs")
            owner = front_matter.get("owner")
            tags = front_matter.get("tags")
            version = front_matter.get("version")
            properties = front_matter.get("properties")

            artifact = manager.create_ssot(
                ssot_type=ssot_type,
                title=str(title or artifact_id).strip() or artifact_id.strip(),
                content=body,
                run_id=workflow_id,
                formal_id=formal_id,
                parent_id=front_matter.get("parent_id"),
                derived_from=derived_from_ids if isinstance(derived_from_ids, list) else [],
                source_refs=source_refs if isinstance(source_refs, list) else [],
                owner=owner if isinstance(owner, str) else None,
                tags=tags if isinstance(tags, list) else [],
                status=status,
                version=str(version or "v1"),
                properties=properties if isinstance(properties, dict) else {},
            )

            output_key = output_key or ("ui_prototype" if ssot_type == SSOTType.UI else "tech_spec")
            materialized_summary[output_key] = {
                "id": artifact.id,
                "identity_kind": "ssot",
                "path": artifact.path,
                "path_root": artifact.path_root,
                "parent_id": artifact.properties.get("parent_id"),
            }
            materialized_files.append(str(artifact.absolute_path))

        if not materialized_summary:
            return None

        return {
            "schema_path": None,
            "outputs": materialized_summary,
            "materialized_files": materialized_files,
        }

    @staticmethod
    def _normalize_ssot_contract_payload(contract_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(contract_data)
        if "contract_version" in normalized:
            normalized["contract_version"] = "1.0"
        if "run_id" in normalized and normalized["run_id"] is not None:
            normalized["run_id"] = str(normalized["run_id"])
        relation_list_keys = {
            "derived_from",
            "source_refs",
            "primary_refs",
            "verifies",
            "implements",
            "depends_on",
        }
        allowed_output_keys = {
            "key",
            "identity_kind",
            "ssot_type",
            "title",
            "description",
            "content",
            "owner",
            "version",
            "parent",
            "derived_from",
            "derived_from_ids",
            "source_refs",
            "primary_refs",
            "verifies",
            "implements",
            "depends_on",
            "derived_from_one",
            "placement_key",
            "tags",
            "artifact_type",
            "category",
            "governance_kind",
            "properties",
            "evidence_layers",
        }
        outputs = []
        for raw_output in normalized.get("outputs", []) or []:
            if not isinstance(raw_output, dict):
                outputs.append(raw_output)
                continue
            output = {
                key: value for key, value in dict(raw_output).items() if key in allowed_output_keys
            }
            raw_verifies = output.get("verifies")
            for relation_key in relation_list_keys:
                if relation_key not in output:
                    continue
                normalized_relations = LLMRunner._filter_materializable_refs(output.get(relation_key))
                if normalized_relations:
                    output[relation_key] = normalized_relations
                else:
                    output.pop(relation_key, None)
            normalized_key = LLMRunner._normalize_ssot_output_key(output.get("key"))
            if normalized_key:
                output["key"] = normalized_key
            parent = output.get("parent")
            if isinstance(parent, str) and parent.lower() == "feat":
                candidates: List[str] = []
                for value in output.get("verifies", []) or []:
                    if isinstance(value, str) and value.upper().startswith("FEAT-"):
                        candidates.append(value)
                properties = output.get("properties") or {}
                for key in ("feature_id", "feat_id", "parent_feat_id"):
                    value = properties.get(key)
                    if isinstance(value, str) and value.upper().startswith("FEAT-"):
                        candidates.append(value)
                if candidates:
                    output["parent"] = candidates[0]
            if isinstance(output.get("parent"), str) and output["parent"].upper().startswith("FEAT-"):
                verifies = []
                verify_candidates = output.get("verifies", []) or raw_verifies or []
                for value in verify_candidates:
                    if isinstance(value, str) and value.lower() == "feat":
                        verifies.append(output["parent"])
                    else:
                        verifies.append(value)
                if verifies:
                    output["verifies"] = verifies
            outputs.append(output)
        normalized["outputs"] = outputs
        return normalized

    @staticmethod
    def _normalize_ssot_output_key(raw_key: Any) -> Optional[str]:
        if raw_key is None:
            return None
        key = str(raw_key).strip().lower()
        if not key:
            return None
        key = re.sub(r"[^a-z0-9_]+", "_", key)
        key = re.sub(r"_+", "_", key).strip("_")
        if not key:
            return None
        if not key[0].isalpha():
            key = f"output_{key}"
        return key

    @staticmethod
    def _parse_structured_output_if_possible(generated_text: str) -> Optional[Any]:
        try:
            return StepRunnerBase._parse_structured_output(generated_text)
        except ValueError:
            return None

    def _extract_business_output_payload(
        self,
        structured_payload: Optional[Any],
        fallback_text: str,
        *,
        step=None,
        written_files: Optional[List[str]] = None,
    ) -> Any:
        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            wrapped_business_output = structured_payload["business_output"]
            if (
                step
                and written_files
                and self._should_prefer_written_file_payload(step, wrapped_business_output)
            ):
                best_file_payload = self._extract_best_written_file_payload(step, written_files)
                if best_file_payload is not None:
                    return self._unwrap_business_output_candidate(best_file_payload)
            return wrapped_business_output
        if isinstance(structured_payload, dict):
            return structured_payload
        segment_payload = self._extract_structured_segment_payload(fallback_text, "business_output")
        if segment_payload is not None:
            return segment_payload
        if step and written_files:
            file_output = self._extract_primary_file_output(step, written_files)
            if file_output is not None:
                return file_output
            best_file_payload = self._extract_best_written_file_payload(step, written_files)
            if best_file_payload is not None:
                return self._unwrap_business_output_candidate(best_file_payload)
        return fallback_text

    @classmethod
    def _should_prefer_written_file_payload(cls, step, payload: Any) -> bool:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return True
        agent_id = getattr(step, "agent_id", "")
        if agent_id == "agent.product.pm_planner":
            task_specs = candidate.get("task_specs")
            if isinstance(task_specs, list) and task_specs:
                return False
            return True
        return False

    @classmethod
    def _expected_feat_review_subject_refs(
        cls,
        instance_data: Dict[str, Any],
    ) -> List[str]:
        return ReviewSemanticValidator.expected_feat_review_subject_refs(
            runner_cls=cls,
            instance_data=instance_data,
        )

    @staticmethod
    def _extract_epic_id_from_output_payload(payload: Any) -> Optional[str]:
        if not isinstance(payload, dict):
            return None

        candidates: List[Any] = [payload]
        business_output = payload.get("business_output")
        if isinstance(business_output, dict):
            candidates.append(business_output)
        structured_payload = payload.get("structured_payload")
        if isinstance(structured_payload, dict):
            candidates.append(structured_payload)

        nested_paths = [
            ("epic_formalized_candidate", "business_output"),
            ("epic_scoped_candidate", "business_output"),
            ("epic_review_report", "epic_identity"),
            ("epic_identity",),
            ("ssot",),
        ]

        for candidate in candidates:
            direct_id = candidate.get("epic_id") or candidate.get("epic_ref") or candidate.get("id")
            if isinstance(direct_id, str) and direct_id.strip() and direct_id.strip().upper().startswith("EPIC-"):
                return direct_id.strip()
            for path in nested_paths:
                current: Any = candidate
                for key in path:
                    current = current.get(key) if isinstance(current, dict) else None
                if not isinstance(current, dict):
                    continue
                nested_id = current.get("epic_id") or current.get("epic_ref") or current.get("id") or current.get("ssot_id")
                if isinstance(nested_id, str) and nested_id.strip() and nested_id.strip().upper().startswith("EPIC-"):
                    return nested_id.strip()
        return None

    @staticmethod
    def _resolve_epic_ref_from_instance_data(instance_data: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(instance_data, dict):
            return None

        candidates: List[Any] = [
            instance_data.get("epic_freeze"),
            instance_data.get("epic_freeze_ref"),
        ]

        params = instance_data.get("params")
        if isinstance(params, dict):
            candidates.extend(
                [
                    params.get("epic_freeze"),
                    params.get("epic_freeze_ref"),
                ]
            )

        for candidate in candidates:
            if isinstance(candidate, dict):
                artifact_id = candidate.get("artifact_id") or candidate.get("id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()
                path_value = candidate.get("path")
            elif isinstance(candidate, str):
                path_value = candidate
            else:
                continue

            if not isinstance(path_value, str) or not path_value.strip():
                continue
            path = Path(path_value)
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                parsed = StepRunnerBase._parse_structured_output(text)
            except Exception:
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                parsed = None
            if isinstance(parsed, dict):
                artifact_id = parsed.get("artifact_id") or parsed.get("id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()
            match = re.search(r"(?m)^(?:artifact_id|id):\s*([A-Za-z0-9_.-]+)\s*$", text)
            if match:
                return match.group(1).strip()

        parent_workflow_id = str(instance_data.get("parent_workflow_id") or "").strip()
        if parent_workflow_id:
            db_path = Path.cwd() / ".workflow" / "orchestrator.db"
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cur = conn.cursor()
                    sibling_ids = [
                        row[0]
                        for row in cur.execute(
                            """
                            SELECT id
                            FROM workflow_instances
                            WHERE parent_id = ?
                              AND template_id = 'workflow.product.task.src_to_epic'
                            ORDER BY created_at DESC
                            """,
                            (parent_workflow_id,),
                        ).fetchall()
                    ]
                    for sibling_id in sibling_ids:
                        rows = cur.execute(
                            """
                            SELECT output_data
                            FROM task_executions
                            WHERE workflow_id = ?
                            ORDER BY started_at DESC
                            """,
                            (sibling_id,),
                        ).fetchall()
                        for (raw_output_data,) in rows:
                            if not isinstance(raw_output_data, str) or not raw_output_data.strip():
                                continue
                            try:
                                parsed_output = json.loads(raw_output_data)
                            except Exception:
                                continue
                            resolved = LLMRunner._extract_epic_id_from_output_payload(parsed_output)
                            if resolved:
                                conn.close()
                                return resolved
                    conn.close()
                except Exception:
                    pass

        return None

    @staticmethod
    def _normalize_requirement_decomposer_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.requirement_decomposer":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        actual_epic_ref = LLMRunner._resolve_epic_ref_from_instance_data(instance_data)
        if not actual_epic_ref:
            return business_output, structured_payload

        normalized_business = dict(business_output)
        normalized_business["epic_ref"] = actual_epic_ref

        raw_candidates = normalized_business.get("feat_candidates")
        if not isinstance(raw_candidates, list):
            alternate_candidates = normalized_business.get("features")
            if isinstance(alternate_candidates, list):
                raw_candidates = alternate_candidates
                normalized_business["feat_candidates"] = alternate_candidates
        if not isinstance(raw_candidates, list):
            alternate_candidates = normalized_business.get("feats")
            if isinstance(alternate_candidates, list):
                raw_candidates = alternate_candidates
                normalized_business["feat_candidates"] = alternate_candidates
        if not isinstance(raw_candidates, list):
            alternate_candidates = normalized_business.get("feat_breakdown")
            if isinstance(alternate_candidates, list):
                raw_candidates = alternate_candidates
                normalized_business["feat_candidates"] = alternate_candidates
        if not str(normalized_business.get("breakdown_id") or "").strip():
            normalized_business["breakdown_id"] = f"FEAT-BREAKDOWN-{actual_epic_ref}"
        if not isinstance(raw_candidates, list):
            boundary_design = (
                normalized_business.get("boundary_design")
                if isinstance(normalized_business.get("boundary_design"), dict)
                else {}
            )
            derived_feats = boundary_design.get("derived_feats")
            if isinstance(derived_feats, list):
                raw_candidates = derived_feats
                normalized_business["feat_candidates"] = derived_feats

        if isinstance(raw_candidates, list):
            normalized_candidates: List[Dict[str, Any]] = []
            for item in raw_candidates:
                if not isinstance(item, dict):
                    continue
                nested_business_output = (
                    item.get("business_output")
                    if isinstance(item.get("business_output"), dict)
                    else {}
                )
                normalized_item = {
                    **nested_business_output,
                    **dict(item),
                }
                normalized_item.pop("business_output", None)

                title = str(
                    normalized_item.get("title")
                    or normalized_item.get("name")
                    or normalized_item.get("feat_title")
                    or normalized_item.get("id")
                    or "Untitled FEAT"
                ).strip()
                normalized_item["title"] = title

                user_value = str(
                    normalized_item.get("user_value")
                    or normalized_item.get("goal")
                    or normalized_item.get("description")
                    or normalized_item.get("value")
                    or title
                ).strip()
                normalized_item["user_value"] = user_value

                acceptance_boundary = normalized_item.get("acceptance_boundary")
                if isinstance(acceptance_boundary, dict):
                    boundary_parts: List[str] = []
                    for value in acceptance_boundary.values():
                        if isinstance(value, list):
                            boundary_parts.extend(
                                str(part).strip() for part in value if str(part).strip()
                            )
                            continue
                        text = str(value or "").strip()
                        if text:
                            boundary_parts.append(text)
                    normalized_item["acceptance_boundary"] = "\n".join(boundary_parts).strip() or title
                else:
                    normalized_item["acceptance_boundary"] = str(
                        acceptance_boundary
                        or normalized_item.get("acceptance")
                        or normalized_item.get("description")
                        or title
                    ).strip()

                dependencies = normalized_item.get("dependencies")
                if isinstance(dependencies, dict):
                    flattened_dependencies: List[str] = []
                    for value in dependencies.values():
                        if isinstance(value, list):
                            flattened_dependencies.extend(
                                str(part).strip() for part in value if str(part).strip()
                            )
                        else:
                            text = str(value or "").strip()
                            if text:
                                flattened_dependencies.append(text)
                    normalized_item["dependencies"] = flattened_dependencies
                elif not isinstance(dependencies, list):
                    normalized_item["dependencies"] = (
                        [str(dependencies).strip()] if str(dependencies or "").strip() else []
                    )

                non_goals = normalized_item.get("non_goals")
                if non_goals in (None, [], {}):
                    non_goals = normalized_item.get("out_of_scope")
                if isinstance(non_goals, list):
                    normalized_item["non_goals"] = [
                        str(value).strip() for value in non_goals if str(value).strip()
                    ]
                else:
                    if isinstance(non_goals, dict):
                        normalized_item["non_goals"] = [
                            str(value).strip()
                            for value in non_goals.values()
                            if str(value).strip()
                        ]
                    elif str(non_goals or "").strip():
                        normalized_item["non_goals"] = [str(non_goals).strip()]
                    else:
                        normalized_item["non_goals"] = []

                priority = str(normalized_item.get("priority") or "").strip().upper()
                normalized_item["priority"] = priority if priority in {"P0", "P1", "P2"} else "P1"

                normalized_candidates.append(normalized_item)

            if normalized_candidates:
                normalized_business["feat_candidates"] = normalized_candidates

        if isinstance(structured_payload, dict):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business
            return normalized_business, normalized_structured

        return normalized_business, structured_payload

    @staticmethod
    def _normalize_prd_writer_feat_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        return PrdWriterFeatNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )


    @staticmethod
    def _resolve_changed_file_paths(
        *,
        workspace: str,
        project_root: Optional[str],
        changed_files: List[str],
    ) -> List[str]:
        resolved_paths: List[str] = []
        project_root_path = Path(project_root or workspace).resolve()
        workspace_path = Path(workspace).resolve()
        project_relative_roots = {
            ".workflow",
            ".artifacts",
            "spec",
            "output",
            "docs",
            "tests",
            ".tmp",
        }

        for item in changed_files or []:
            if not isinstance(item, str) or not item.strip():
                continue
            candidate = Path(item)
            if candidate.is_absolute():
                resolved_paths.append(str(candidate))
                continue

            normalized = candidate.as_posix()
            project_candidate = (project_root_path / candidate).resolve()
            workspace_candidate = (workspace_path / candidate).resolve()
            root_part = normalized.split("/", 1)[0]
            if root_part in project_relative_roots:
                resolved_paths.append(str(project_candidate))
            elif project_candidate.exists() and not workspace_candidate.exists():
                resolved_paths.append(str(project_candidate))
            else:
                resolved_paths.append(str(workspace_candidate))
        return resolved_paths

    @staticmethod
    def _normalize_pm_planner_task_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        return PmPlannerTaskNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )

    @staticmethod
    def _synthesize_single_ssot_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        return SingleSSOTNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )


    @staticmethod
    def _normalize_business_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        business_output, structured_payload = LLMRunner._normalize_source_freeze_payload(
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_requirement_decomposer_payload(
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_prd_writer_feat_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_pm_planner_task_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_product_review_payload(
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        return LLMRunner._synthesize_single_ssot_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )

    @staticmethod
    def _normalize_product_review_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        return ProductReviewNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )


    @classmethod
    def _sanitize_feat_review_payload(
        cls,
        *,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sanitized = dict(review_payload)
        findings = [
            item.strip()
            for item in sanitized.get("findings") or []
            if isinstance(item, str) and item.strip()
        ]
        filtered_findings = [
            item for item in findings if not cls._contains_feat_review_false_positive(item)
        ]
        sanitized["findings"] = filtered_findings
        if sanitized.get("decision") == "pass" and filtered_findings:
            sanitized["decision"] = "revise"
        all_findings_filtered = bool(findings) and not filtered_findings
        if sanitized.get("decision") in {"revise", "reject"} and all_findings_filtered:
            sanitized["decision"] = "pass"
            sanitized["summary"] = ""
        elif sanitized.get("decision") == "revise" and not filtered_findings:
            summary = str(sanitized.get("summary") or "").strip()
            if not cls._contains_feat_review_negative_signal(summary):
                sanitized["decision"] = "pass"
        if (
            sanitized.get("decision") in {"revise", "reject"}
            and cls._is_self_contradictory_feat_review(
                review_payload=sanitized,
                instance_data=instance_data,
            )
        ):
            sanitized["decision"] = "pass"
            sanitized["summary"] = ""
            sanitized["findings"] = []
            sanitized["risks"] = []
            sanitized["recommendations"] = []
        if not str(sanitized.get("summary") or "").strip():
            subject_refs = [
                item.strip()
                for item in sanitized.get("subject_refs") or []
                if isinstance(item, str) and item.strip()
            ]
            subject_text = ", ".join(subject_refs) if subject_refs else "the planned FEATs"
            decision = str(sanitized.get("decision") or "").strip() or "pass"
            sanitized["summary"] = f"FEAT review {decision} for {subject_text}"
        return sanitized

    @classmethod
    def _is_self_contradictory_feat_review(
        cls,
        *,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(review_payload, dict):
            return False
        expected_subject_refs = cls._expected_feat_review_subject_refs(instance_data or {})
        expected = {
            ref.strip()
            for ref in expected_subject_refs
            if isinstance(ref, str) and ref.strip()
        }
        actual = {
            str(item).strip()
            for item in (review_payload.get("subject_refs") or [])
            if str(item).strip()
        }
        if not expected or actual != expected:
            return False

        contradiction_markers = (
            "feat-bundle-contract",
            "feat_specs",
            "input bundle",
            "输入对象",
            "输入数据",
            "derived_object_expectations",
            "trace_hints",
            "trace hints",
            "required_fields",
            "formal object",
            "repo-evidence-manifest",
            "canonical-ssot-path-rules",
            "adr-016",
        )
        findings = review_payload.get("findings") or []
        summary = review_payload.get("summary") or ""
        lowered = "\n".join(
            str(item).lower()
            for item in list(findings) + [summary]
            if isinstance(item, str) and item.strip()
        )
        if not lowered:
            return False
        if cls._looks_like_reverse_ssot_contract_noise(lowered):
            return True
        return any(marker in lowered for marker in contradiction_markers)

    @classmethod
    def _looks_like_reverse_ssot_contract_noise(cls, text: str) -> bool:
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        if not lowered:
            return False
        reverse_markers = (
            "feat-bundle-contract",
            "input bundle",
            "输入对象",
            "输入数据",
            "feat_specs",
            "feat_id",
            "derived_object_expectations",
            "trace_hints",
            "trace hints",
            "formal object",
            "adr-016",
            "repo-evidence-manifest",
        )
        governance_markers = (
            "user_stories",
            "user stories",
            "dependencies",
            "acceptance_criteria",
            "required_fields",
            "specific derivation paths",
            "generic category names",
            "technical schema keys",
            "without business validation rules",
            "review contract",
            "canonical-ssot-path-rules",
        )
        return any(marker in lowered for marker in reverse_markers) and any(
            marker in lowered for marker in governance_markers
        )

    @staticmethod
    def _build_schema_repair_prompt(
        *,
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> str:
        return SchemaRepairHelper.build_repair_prompt(
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )

    @classmethod
    def _build_schema_repair_input(
        cls,
        *,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Dict[str, Any]:
        return SchemaRepairHelper.build_repair_input(
            executor_type=executor_type,
            input_data=input_data,
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )

    async def _attempt_schema_repair(
        self,
        *,
        executor,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        workflow_id: str,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Optional[Dict[str, Any]]:
        return await SchemaRepairHelper.attempt_repair(
            runner=self,
            executor=executor,
            executor_type=executor_type,
            input_data=input_data,
            step=step,
            workflow_id=workflow_id,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )

    @staticmethod
    def _validate_feat_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        return ReviewSemanticValidator.validate_feat_review_subject_refs(
            review_payload,
            expected_subject_refs,
        )

    @classmethod
    def _validate_feat_review_semantics(
        cls,
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        return ReviewSemanticValidator.validate_feat_review_semantics(
            runner_cls=cls,
            review_payload=review_payload,
            expected_subject_refs=expected_subject_refs,
        )

    @classmethod
    def _expected_delivery_plan_subject_refs(
        cls,
        instance_data: Optional[Dict[str, Any]],
        business_output: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        return ReviewSemanticValidator.expected_delivery_plan_subject_refs(
            runner_cls=cls,
            instance_data=instance_data,
            business_output=business_output,
        )

    @staticmethod
    def _validate_delivery_plan_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        return ReviewSemanticValidator.validate_delivery_plan_review_subject_refs(
            review_payload,
            expected_subject_refs,
        )

    @classmethod
    def _load_task_plan_business_output(cls, instance_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return ReviewSemanticValidator.load_task_plan_business_output(
            runner_cls=cls,
            instance_data=instance_data,
        )

    @staticmethod
    def _review_clean_text(value: Any) -> str:
        return ReviewSemanticValidator.review_clean_text(value)

    @classmethod
    def _delivery_plan_has_persisted_tasks(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        return ReviewSemanticValidator.delivery_plan_has_persisted_tasks(
            project_root=project_root,
            task_plan=task_plan,
        )

    @classmethod
    def _delivery_plan_has_structural_spec_coverage(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        return ReviewSemanticValidator.delivery_plan_has_structural_spec_coverage(
            runner_cls=cls,
            project_root=project_root,
            task_plan=task_plan,
        )

    @classmethod
    def _contains_delivery_plan_false_positive(cls, text: str) -> bool:
        return ReviewSemanticValidator.contains_delivery_plan_false_positive(text)

    @classmethod
    def _sanitize_delivery_plan_review_payload(
        cls,
        *,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return ReviewSemanticValidator.sanitize_delivery_plan_review_payload(
            runner_cls=cls,
            review_payload=review_payload,
            instance_data=instance_data,
        )

    @classmethod
    def _validate_delivery_plan_review_semantics(
        cls,
        *,
        project_root: str,
        review_payload: Any,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        return ReviewSemanticValidator.validate_delivery_plan_review_semantics(
            runner_cls=cls,
            project_root=project_root,
            review_payload=review_payload,
            instance_data=instance_data,
        )

    @staticmethod
    def _contains_feat_review_negative_signal(text: Any) -> bool:
        if not isinstance(text, str):
            return False
        normalized = text.strip().lower()
        if not normalized:
            return False

        patterns = [
            r"\bblocker\b",
            r"\bmajor\b",
            r"\breject\b",
            r"\brevise\b",
            r"\bmust fix\b",
            r"\bcritical issue\b",
            r"阻塞",
            r"不通过",
            r"拒绝",
            r"驳回",
            r"需修订",
            r"需要修订",
            r"必须修复",
            r"关键问题",
            r"严重问题",
            r"不可通过",
        ]
        return any(re.search(pattern, normalized) for pattern in patterns)

    @classmethod
    def _contains_feat_review_false_positive(cls, text: str) -> bool:
        lowered = text.strip().lower()
        if not lowered:
            return False
        positive_patterns = [
            r"\bsatisf(y|ies)\b",
            r"\bcomplete\b",
            r"\bvalid\b",
            r"\baligns?\b",
            r"\btraceable\b",
            r"\bconcrete\b",
            r"\bspecific\b",
            r"\bcomplies?\b",
            r"\bcover(s|age)?\b",
            r"\bclear\b",
            r"\bexplicitly support\b",
            r"\bno unauthorized\b",
            r"满足",
            r"完整",
            r"有效",
            r"对齐",
            r"可追溯",
            r"清晰",
            r"合规",
            r"具体",
            r"覆盖",
            r"明确",
            r"支持下游",
            r"无未经授权",
        ]
        if cls._contains_feat_review_negative_signal(lowered):
            return False
        return any(re.search(pattern, lowered) for pattern in positive_patterns)

    @classmethod
    def _extract_topic_families(cls, text: Any) -> set[str]:
        if not isinstance(text, str):
            return set()
        normalized = text.lower()
        families: set[str] = set()
        for family, keywords in cls.FEAT_TOPIC_FAMILIES.items():
            for keyword in keywords:
                if not keyword:
                    continue
                lowered = keyword.lower()
                if re.search(r"[a-z]", lowered):
                    if re.search(rf"\b{re.escape(lowered)}\b", normalized):
                        families.add(family)
                        break
                elif lowered in normalized:
                    families.add(family)
                    break
        return families

    @staticmethod
    def _text_contains_keyword(text: str, keyword: str) -> bool:
        normalized = (text or "").lower()
        lowered = keyword.lower()
        if not lowered:
            return False
        if re.search(r"[a-z]", lowered):
            return bool(re.search(rf"\b{re.escape(lowered)}\b", normalized))
        return lowered in normalized

    @staticmethod
    def _load_ssot_markdown(project_root: str, artifact_id: str) -> Optional[str]:
        if not artifact_id:
            return None
        try:
            from lee.orchestrator.execution.artifacts.manager import ArtifactManager

            manager = ArtifactManager(project_root=Path(project_root))
            content = manager.get_content(artifact_id)
            if isinstance(content, bytes):
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    return None
            if isinstance(content, str):
                return content
        except Exception:
            pass

        project_root_path = Path(project_root)
        candidates = list(project_root_path.glob(f"spec/**/*{artifact_id}__*.md"))
        if not candidates:
            return None
        try:
            return candidates[0].read_text(encoding="utf-8")
        except OSError:
            return None

    @classmethod
    def _validate_feat_bundle_epic_semantics(
        cls,
        *,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        return WorkflowSemanticValidator.validate_feat_bundle_epic_semantics(
            runner_cls=cls,
            project_root=project_root,
            business_output=business_output,
        )

    @classmethod
    def _validate_pm_planner_task_semantics(
        cls,
        *,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        return WorkflowSemanticValidator.validate_pm_planner_task_semantics(
            runner_cls=cls,
            project_root=project_root,
            business_output=business_output,
        )

    @staticmethod
    def _extract_primary_file_output(step, written_files: List[str]) -> Optional[Any]:
        file_specs = [
            output
            for output in (getattr(step, "outputs", None) or [])
            if getattr(output, "type", None) == "file"
        ]
        if len(file_specs) != 1 or not written_files:
            return None
        spec_filename = Path(getattr(file_specs[0], "path", "")).name
        for file_path in written_files:
            if Path(file_path).name != spec_filename:
                continue
            try:
                return StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                return None
        return None

    @staticmethod
    def _unwrap_business_output_candidate(payload: Any) -> Any:
        if isinstance(payload, dict) and "business_output" in payload:
            return payload["business_output"]
        return payload

    @staticmethod
    def _coerce_single_prd_writer_feat_candidate(payload: Any) -> Optional[Dict[str, Any]]:
        candidate = LLMRunner._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return None

        feat_id = str(
            candidate.get("feat_id")
            or candidate.get("id")
            or candidate.get("parent_feat")
            or candidate.get("symbol_id")
            or ""
        ).strip()
        title = str(candidate.get("title") or candidate.get("name") or "").strip()
        if not feat_id or not title:
            return None

        kind = str(candidate.get("kind") or "").strip().lower()
        specification = candidate.get("specification") if isinstance(candidate.get("specification"), dict) else {}
        overview = specification.get("overview") if isinstance(specification.get("overview"), dict) else {}
        objective = str(
            candidate.get("goal")
            or candidate.get("objective")
            or overview.get("summary")
            or ""
        ).strip()
        if kind not in {"feat_specification", "feat_spec", "feat"} and not objective:
            return None

        dependencies = candidate.get("dependencies") or candidate.get("depends_on") or []
        if isinstance(dependencies, str):
            dependencies = [dependencies]

        interface_spec = specification.get("technical_specifications", {}).get("interfaces", {}) if isinstance(
            specification.get("technical_specifications"), dict
        ) else {}
        input_fields = (
            interface_spec.get("input", {}).get("fields")
            if isinstance(interface_spec.get("input"), dict)
            else []
        ) or []
        output_fields = (
            interface_spec.get("output", {}).get("fields")
            if isinstance(interface_spec.get("output"), dict)
            else []
        ) or []
        functional_requirements = specification.get("functional_requirements") if isinstance(
            specification.get("functional_requirements"), list
        ) else []
        aggregated_acceptance: List[str] = []
        for requirement in functional_requirements[:5]:
            if not isinstance(requirement, dict):
                continue
            for item in requirement.get("acceptance_criteria") or []:
                if isinstance(item, str) and item.strip():
                    aggregated_acceptance.append(item.strip())
        if not aggregated_acceptance and objective:
            aggregated_acceptance = [objective]

        return {
            "feat_id": feat_id,
            "title": title,
            "goal": objective,
            "user_value": candidate.get("user_value") or objective or title,
            "inputs": candidate.get("inputs")
            or candidate.get("input")
            or [field.get("name") for field in input_fields if isinstance(field, dict) and field.get("name")],
            "processing": candidate.get("processing")
            or [req.get("requirement") for req in functional_requirements if isinstance(req, dict) and req.get("requirement")],
            "outputs": candidate.get("outputs")
            or candidate.get("output")
            or [field.get("name") for field in output_fields if isinstance(field, dict) and field.get("name")],
            "acceptance_criteria": candidate.get("acceptance_criteria")
            or candidate.get("acceptance_boundaries")
            or aggregated_acceptance,
            "dependencies": dependencies,
            "non_goals": candidate.get("non_goals"),
            "priority": candidate.get("priority"),
            "delivery_slice": candidate.get("delivery_slice") or candidate.get("category"),
            "lifecycle_status": candidate.get("lifecycle_status") or candidate.get("status"),
            "epic_ref": candidate.get("epic_ref") or candidate.get("parent_epic"),
            "source_refs": candidate.get("source_refs"),
        }

    @classmethod
    def _referenced_written_files(cls, file_path: str, payload: Any) -> List[str]:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return []

        references: List[str] = []
        deliverables = candidate.get("deliverables")
        if not isinstance(deliverables, list):
            return references

        base_path = Path(file_path).parent
        for item in deliverables:
            if not isinstance(item, dict):
                continue
            referenced_path = item.get("file_path")
            if not isinstance(referenced_path, str) or not referenced_path.strip():
                continue
            resolved_path = Path(referenced_path)
            if not resolved_path.is_absolute():
                resolved_path = (base_path / resolved_path).resolve()
            if resolved_path.exists():
                references.append(str(resolved_path))
        return references

    @classmethod
    def _score_written_output_candidate(cls, step, payload: Any) -> int:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return -1

        score = 1
        agent_id = getattr(step, "agent_id", "")
        if agent_id == "agent.product.prd_writer":
            if isinstance(candidate.get("feat_specs"), list):
                score += 100
            if isinstance(candidate.get("features"), list):
                score += 90
            if isinstance(candidate.get("feat_candidates"), list):
                score += 80
            if isinstance(candidate.get("epic_breakdowns"), list):
                score += 70
            if isinstance(candidate.get("feats"), list):
                score += 65
            if cls._coerce_single_prd_writer_feat_candidate(payload):
                score += 60
            if isinstance(candidate.get("epic_ref"), str) and candidate.get("epic_ref").strip():
                score += 10
        elif agent_id == "agent.product.requirement_decomposer":
            if isinstance(candidate.get("feat_candidates"), list):
                score += 100
            if isinstance(candidate.get("features"), list):
                score += 90
            if isinstance(candidate.get("epic_breakdowns"), list):
                score += 80
            if isinstance(candidate.get("breakdown_id"), str) and candidate.get("breakdown_id").strip():
                score += 10
        elif agent_id == "agent.product.pm_planner":
            if isinstance(candidate.get("task_specs"), list) and candidate.get("task_specs"):
                score += 100
            if isinstance(candidate.get("task_hierarchy"), list) and candidate.get("task_hierarchy"):
                score += 95
            if isinstance(candidate.get("task_planning"), dict):
                score += 80
            metadata = candidate.get("metadata")
            if isinstance(metadata, dict) and isinstance(metadata.get("epic_id"), str) and metadata.get("epic_id").strip():
                score += 10
        elif isinstance(candidate.get("business_output"), dict):
                score += 10
        return score

    @classmethod
    def _build_prd_writer_bundle_from_written_files(cls, written_files: List[str]) -> Optional[Dict[str, Any]]:
        feat_specs: List[Dict[str, Any]] = []
        epic_ref: Optional[str] = None
        pending_files = list(written_files)
        seen_files: set[str] = set()
        direct_bundle_candidates: List[Dict[str, Any]] = []

        if written_files:
            workspace_dir = Path(written_files[0]).parent
            upstream_boundary_dir = workspace_dir.parent / "feat_boundary_design"
            if upstream_boundary_dir.exists():
                for candidate_name in (
                    "feat_breakdown.yaml",
                    "feat-breakdown.yaml",
                    "business_output.yaml",
                    "structured_payload.yaml",
                ):
                    candidate_path = upstream_boundary_dir / candidate_name
                    if candidate_path.exists():
                        pending_files.append(str(candidate_path))

        while pending_files:
            file_path = pending_files.pop(0)
            if file_path in seen_files:
                continue
            seen_files.add(file_path)
            try:
                parsed_file = StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                continue

            for referenced_file in cls._referenced_written_files(file_path, parsed_file):
                if referenced_file not in seen_files:
                    pending_files.append(referenced_file)

            unwrapped = cls._unwrap_business_output_candidate(parsed_file)
            if isinstance(unwrapped, dict) and any(
                isinstance(unwrapped.get(key), list)
                for key in ("feat_specs", "features", "feats", "feat_candidates", "epic_breakdowns")
            ):
                direct_bundle_candidates.append(unwrapped)
                continue

            coerced_feat = cls._coerce_single_prd_writer_feat_candidate(parsed_file)
            if not isinstance(coerced_feat, dict):
                continue
            feat_specs.append(coerced_feat)
            if epic_ref is None:
                candidate_epic_ref = str(coerced_feat.get("epic_ref") or "").strip()
                if candidate_epic_ref:
                    epic_ref = candidate_epic_ref

        if not feat_specs:
            for candidate in direct_bundle_candidates:
                if isinstance(candidate.get("epic_ref"), str) and candidate.get("epic_ref").strip():
                    return candidate
            return direct_bundle_candidates[0] if direct_bundle_candidates else None
        return {
            "epic_ref": epic_ref,
            "feat_specs": feat_specs,
        }

    @classmethod
    def _parse_legacy_task_planning_specs_text(cls, text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(text, str) or "task_planning_specs:" not in text:
            return None

        epic_match = re.search(r"(?m)^\s*epic_id:\s*([A-Z]+-\d+)\s*$", text)
        epic_id = epic_match.group(1).strip() if epic_match else ""

        tasks: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None
        current_indent = 0
        related_features_mode = False
        acceptance_mode = False
        description_mode = False
        description_indent = 0

        def _flush_current() -> None:
            nonlocal current
            if not isinstance(current, dict):
                return
            related_feat = str(current.get("related_feat") or "").strip()
            if not related_feat:
                related_features = current.get("related_features") or []
                if isinstance(related_features, list) and related_features:
                    current["related_feat"] = str(related_features[0]).strip()
            if isinstance(current.get("description_lines"), list):
                description = "\n".join(
                    line.rstrip() for line in current.get("description_lines") or [] if str(line).strip()
                ).strip()
                if description:
                    current["description"] = description
            current.pop("description_lines", None)
            tasks.append(current)
            current = None

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            task_match = re.match(r"^\s*-\s+task_id:\s*(.+?)\s*$", line)
            if task_match and indent <= 4:
                _flush_current()
                current_indent = indent
                current = {
                    "task_id": task_match.group(1).strip().strip('"'),
                    "description_lines": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                    "related_features": [],
                }
                related_features_mode = False
                acceptance_mode = False
                description_mode = False
                continue

            if not isinstance(current, dict):
                continue

            if description_mode:
                if stripped and indent > description_indent:
                    current.setdefault("description_lines", []).append(line[description_indent:].rstrip())
                    continue
                description_mode = False

            if related_features_mode:
                feat_match = re.match(r"^\s*-\s+(FEAT-[A-Z0-9-]+)\s*$", line)
                if feat_match and indent > current_indent:
                    current.setdefault("related_features", []).append(feat_match.group(1).strip())
                    continue
                related_features_mode = False

            if acceptance_mode:
                acceptance_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
                if acceptance_match and indent > current_indent:
                    current.setdefault("acceptance_criteria", []).append(
                        acceptance_match.group(1).strip().strip('"')
                    )
                    continue
                acceptance_mode = False

            if stripped.startswith("title:") and indent <= current_indent + 2:
                current["title"] = stripped.split(":", 1)[1].strip().strip('"')
                continue
            if stripped.startswith("related_feature:") and indent <= current_indent + 2:
                current["related_feat"] = stripped.split(":", 1)[1].strip().strip('"')
                continue
            if stripped.startswith("related_features:") and indent <= current_indent + 2:
                related_features_mode = True
                continue
            if stripped.startswith("description: |"):
                description_mode = True
                description_indent = indent + 2
                continue
            if stripped.startswith("acceptance_criteria:"):
                acceptance_mode = True
                continue
            if stripped.startswith("estimated_effort:") and "estimated_effort" not in current:
                current["estimated_effort"] = stripped.split(":", 1)[1].strip().strip('"')
                continue
            if stripped.startswith("dependencies:"):
                dependency_value = stripped.split(":", 1)[1].strip()
                if dependency_value.startswith("[") and dependency_value.endswith("]"):
                    items = [
                        item.strip().strip('"')
                        for item in dependency_value[1:-1].split(",")
                        if item.strip()
                    ]
                    current.setdefault("dependencies", []).extend(items)
                continue

        _flush_current()
        if not tasks:
            return None

        return {
            "metadata": {
                "epic_id": epic_id or "EPIC-001",
                "status": "legacy_task_planning_specs",
            },
            "task_hierarchy": [
                {
                    "phase": "Legacy Task Planning",
                    "phase_id": "P1",
                    "tasks": [
                        {
                            "task_id": str(task.get("task_id") or "").strip(),
                            "title": str(task.get("title") or task.get("task_id") or "").strip(),
                            "description": str(
                                task.get("description")
                                or task.get("title")
                                or task.get("task_id")
                                or ""
                            ).strip(),
                            "related_feat": str(task.get("related_feat") or "").strip(),
                            "dependencies": task.get("dependencies") or [],
                            "acceptance_criteria": task.get("acceptance_criteria") or [],
                            "estimated_effort": str(task.get("estimated_effort") or "1 day").strip(),
                        }
                        for task in tasks
                    ],
                }
            ],
        }

    @classmethod
    def _build_pm_planner_bundle_from_written_files(cls, written_files: List[str]) -> Optional[Dict[str, Any]]:
        markdown_tasks: List[Dict[str, Any]] = []
        for file_path in written_files:
            path = Path(file_path)
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue

            parsed = cls._parse_structured_output_if_possible(text)
            candidate = cls._unwrap_business_output_candidate(parsed) if parsed is not None else None
            if isinstance(candidate, dict) and (
                (isinstance(candidate.get("task_specs"), list) and candidate.get("task_specs"))
                or (isinstance(candidate.get("task_hierarchy"), list) and candidate.get("task_hierarchy"))
                or (isinstance(candidate.get("tasks"), list) and candidate.get("tasks"))
                or isinstance(candidate.get("task_planning"), dict)
            ):
                return candidate

            if path.name == "task-planning-specs.yaml":
                legacy_candidate = cls._parse_legacy_task_planning_specs_text(text)
                if legacy_candidate is not None:
                    return legacy_candidate
            if path.suffix.lower() == ".md":
                markdown_task = cls._parse_pm_planner_task_markdown(path)
                if markdown_task is not None:
                    markdown_tasks.append(markdown_task)
        if markdown_tasks:
            return cls._build_pm_planner_bundle_from_task_markdowns(markdown_tasks)
        return None

    @staticmethod
    def _extract_markdown_section_lines(markdown: str, heading: str) -> List[str]:
        if not isinstance(markdown, str) or not markdown.strip():
            return []
        pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
        match = re.search(pattern, markdown)
        if not match:
            return []
        return [line.rstrip() for line in match.group(1).strip().splitlines()]

    @classmethod
    def _parse_pm_planner_task_markdown(cls, path: Path) -> Optional[Dict[str, Any]]:
        frontmatter = cls._load_yaml_frontmatter(path) or {}
        task_id = str(frontmatter.get("id") or "").strip()
        parent_id = str(frontmatter.get("parent_id") or "").strip()
        ssot_type = str(frontmatter.get("ssot_type") or "").strip().lower()
        if not task_id or not parent_id or ssot_type != "task":
            return None
        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception:
            return None
        body = cls._extract_markdown_body(raw_text)

        def _lines(section: str) -> List[str]:
            return cls._extract_markdown_section_lines(body, section)

        def _bullet_values(section: str) -> List[str]:
            values: List[str] = []
            for line in _lines(section):
                stripped = line.strip()
                if stripped.startswith("- "):
                    values.append(stripped[2:].strip())
            return values

        title = str(frontmatter.get("title") or task_id).strip()
        objective = "\n".join(_lines("Objective")).strip()
        description = "\n".join(_lines("Description")).strip()
        definition_of_done = _bullet_values("Definition Of Done")
        processing = _bullet_values("Processing")
        outputs = _bullet_values("Outputs")
        input_refs = _bullet_values("Inputs")
        non_goals = _bullet_values("Non Goals")

        acceptance_mapping: List[Dict[str, Any]] = []
        for line in _bullet_values("Acceptance Mapping"):
            match = re.match(r"^(FEAT-[A-Za-z0-9-]+)\s*/\s*([A-Z0-9-]+)\s*:\s*(.+)$", line)
            if match:
                acceptance_mapping.append(
                    {
                        "feat": match.group(1).strip(),
                        "ac": match.group(2).strip(),
                        "description": match.group(3).strip(),
                    }
                )

        dependencies: List[str] = []
        for line in _bullet_values("Dependencies"):
            nested_match = re.search(r'"task_id"\s*:\s*"([^"]+)"', line)
            if nested_match:
                dependencies.append(nested_match.group(1).strip())
                continue
            task_match = re.search(r"(TASK-[A-Za-z0-9-]+)", line)
            if task_match:
                dependencies.append(task_match.group(1).strip())
                continue
            if line == "无（规范定义 TASK 为起始 TASK）":
                continue

        task_kind = "implementation"
        lowered_title = title.lower()
        lowered_desc = description.lower()
        if any(keyword in title for keyword in ("规范", "契约", "定义")):
            task_kind = "specification"
        elif any(keyword in title for keyword in ("验证", "测试")):
            task_kind = "validation"
        elif "audit" in lowered_title or "审计" in title:
            task_kind = "implementation"

        role_map = {
            "specification": "spec-owner",
            "implementation": "runtime-owner",
            "validation": "qa-validation-owner",
        }
        workstream_map = {
            "specification": "specification",
            "implementation": "runtime-implementation",
            "validation": "validation",
        }

        return {
            "task_id": task_id,
            "title": title,
            "objective": objective or title,
            "description": description or objective or title,
            "source_feat": parent_id,
            "workstream": workstream_map.get(task_kind, "runtime-implementation"),
            "task_kind": task_kind,
            "responsible_role": role_map.get(task_kind, "runtime-owner"),
            "acceptance_criteria_mapping": acceptance_mapping,
            "prerequisites": list(dict.fromkeys(dependencies)),
            "dependencies": list(dict.fromkeys(dependencies)),
            "definition_of_done": definition_of_done or ["TASK 文件已冻结"],
            "priority": "P0",
            "milestone": "M1" if task_kind == "specification" else "M2",
            "estimated_effort": "2 days",
            "lifecycle_status": str(frontmatter.get("status") or "draft").strip() or "draft",
            "observability": {
                "execution_unit": "task",
                "log_scope": f"task-{task_id.lower()}",
                "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
            },
            "evidence_requirements": {
                "required_refs": list(dict.fromkeys([parent_id] + input_refs[:3])),
                "review_required": True,
            },
            "rollback_strategy": {
                "mode": "revert",
                "restore_targets": outputs[:3] or [f"spec/tasks/{parent_id}"],
            },
            "non_goals": non_goals,
            "processing": processing,
            "outputs": outputs,
            "source_refs": frontmatter.get("source_refs") if isinstance(frontmatter.get("source_refs"), list) else [],
            "ssot": {
                "identity_kind": str((frontmatter.get("properties") or {}).get("identity_kind") or "ssot").strip(),
                "ssot_type": "TASK",
                "parent": parent_id,
                "derived_from": f"{parent_id}#delivery",
            },
        }

    @classmethod
    def _build_pm_planner_bundle_from_task_markdowns(
        cls,
        task_specs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        source_feats = list(
            dict.fromkeys(
                str(task.get("source_feat")).strip()
                for task in task_specs
                if isinstance(task, dict) and str(task.get("source_feat") or "").strip()
            )
        )
        primary_feat = source_feats[0] if source_feats else "FEAT-001"
        milestones: Dict[str, Dict[str, Any]] = {}
        resource_allocation: Dict[str, Dict[str, Any]] = {}
        dependency_matrix: List[Dict[str, Any]] = []
        critical_path: List[str] = []
        for task in task_specs:
            if not isinstance(task, dict):
                continue
            task_id = str(task.get("task_id") or "").strip()
            if not task_id:
                continue
            milestone_id = str(task.get("milestone") or "M1").strip() or "M1"
            milestones.setdefault(
                milestone_id,
                {
                    "id": milestone_id,
                    "name": milestone_id,
                    "task_ids": [],
                    "acceptance_criteria": f"{milestone_id} completed",
                },
            )
            milestones[milestone_id]["task_ids"].append(task_id)
            role = str(task.get("responsible_role") or "runtime-owner").strip() or "runtime-owner"
            resource_allocation.setdefault(role, {"tasks": []})
            resource_allocation[role]["tasks"].append(task_id)
            dependencies = [
                item for item in (task.get("dependencies") or [])
                if isinstance(item, str) and item.strip()
            ]
            dependency_matrix.append({"task_id": task_id, "depends_on": dependencies})
            if not dependencies:
                critical_path.append(task_id)

        if not critical_path:
            critical_path = [item["task_id"] for item in dependency_matrix if item.get("task_id")]

        return {
            "parent_epic": cls._resolve_feat_parent_epic(primary_feat, {}) or "EPIC-001",
            "source_feats": source_feats or ["FEAT-001"],
            "planning_metadata": {
                "planning_timestamp": datetime.now().strftime("%Y-%m-%d"),
                "project_profile": "task_markdown_recovery",
                "task_directory": f"spec/tasks/{primary_feat}",
            },
            "task_specs": task_specs,
            "milestones": list(milestones.values()),
            "dependency_graph": {
                "critical_path": critical_path,
                "dependency_matrix": dependency_matrix,
            },
            "resource_allocation": resource_allocation,
            "risk_mitigation": [],
        }

    @classmethod
    def _extract_best_written_file_payload(cls, step, written_files: List[str]) -> Optional[Any]:
        return OutputExtractor.extract_best_written_file_payload(
            step=step,
            written_files=written_files,
            build_prd_writer_bundle_from_written_files=cls._build_prd_writer_bundle_from_written_files,
            build_pm_planner_bundle_from_written_files=cls._build_pm_planner_bundle_from_written_files,
            score_written_output_candidate=cls._score_written_output_candidate,
        )

    def _extract_structured_segment_payload(
        self,
        generated_text: str,
        segment_name: str,
    ) -> Optional[Any]:
        segment = self._extract_named_output_segment(generated_text, segment_name)
        if not segment or segment.strip() == (generated_text or "").strip():
            heading_pattern = (
                rf"(?ms)^(?:#+|\d+\.)\s*`?{re.escape(segment_name)}`?\s*\n"
                rf"(?:```[a-zA-Z0-9_-]*\n)?(.*?)(?:```|\n(?:#+|\d+\.)\s+|\Z)"
            )
            match = re.search(heading_pattern, generated_text or "")
            if match:
                segment = match.group(1).strip()
        if not segment or segment.strip() == (generated_text or "").strip():
            plain_label_pattern = (
                rf"(?ms)^\s*{re.escape(segment_name)}\s*\n"
                rf"```[a-zA-Z0-9_-]*\n(.*?)```"
            )
            match = re.search(plain_label_pattern, generated_text or "")
            if match:
                segment = match.group(1).strip()
        if not segment or segment.strip() == (generated_text or "").strip():
            return None
        try:
            return self._parse_structured_output(segment)
        except ValueError:
            return None

    def _extract_structured_payload_from_code_blocks(
        self,
        generated_text: str,
        segment_name: str,
    ) -> Optional[Any]:
        pattern = r"```(?:yaml|yml|json)?\n(.*?)```"
        for match in re.finditer(pattern, generated_text or "", re.DOTALL):
            candidate = match.group(1).strip()
            if segment_name not in candidate:
                continue
            parsed = self._parse_structured_output_if_possible(candidate)
            if not isinstance(parsed, dict):
                continue
            if segment_name in parsed:
                return parsed[segment_name]
            if "contract_version" in parsed and "outputs" in parsed:
                return parsed
        return None

    def _extract_ssot_contract_payload(
        self,
        structured_payload: Optional[Any],
        generated_text: str = "",
    ) -> Optional[Dict[str, Any]]:
        return OutputExtractor.extract_ssot_contract_payload(
            structured_payload=structured_payload,
            generated_text=generated_text,
            extract_structured_segment_payload=self._extract_structured_segment_payload,
            extract_structured_payload_from_code_blocks=self._extract_structured_payload_from_code_blocks,
            coerce_ssot_contract_dict=self._coerce_ssot_contract_dict,
        )

    @staticmethod
    def _coerce_ssot_contract_dict(payload: Optional[Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        if "contract_version" in payload and "outputs" in payload:
            return payload
        nested = payload.get("ssot_output_contract")
        if isinstance(nested, dict):
            return nested
        return None

    async def _register_artifacts(
        self,
        ctx: RunnerContext,
        workflow_id: str,
        step_id: str,
        written_files: List[str],
        llm_output: str,
    ) -> None:
        """
        v1.0: 注册写入的文件为产出物 (SSOT 集成)

        Args:
            ctx: RunnerContext
            workflow_id: Workflow ID
            step_id: Step ID
            written_files: 已写入的文件路径列表
            llm_output: LLM 原始输出 (用于记录 Context Bundle)
        """
        try:
            from lee.orchestrator.execution.artifacts import (
                create_artifact_handler,
                ContextBuilder,
                ArtifactManager,
            )

            # 获取 run_id 和部门信息
            instance = await ctx.store.get_workflow(workflow_id)
            if not instance:
                return

            run_id = instance.data.get("run_id")
            if not run_id:
                return

            department = instance.data.get("department")
            template_id = instance.template_id or ""

            # 创建产出物处理器
            handler = create_artifact_handler(
                run_id=run_id,
                workflow_id=workflow_id,
                department=department,
                project_root=Path(ctx.file_output_handler.project_root),
            )

            # 注册写入的文件
            handler.register_files_from_output(written_files)

            # v1.0: 记录 Context Bundle (简化版 v0.9)
            # 仅在配置启用时记录
            if getattr(ctx, "enable_context_bundle", True):
                try:
                    manager = ArtifactManager()
                    context_builder = ContextBuilder(manager)

                    # 构建 prompt 快照 (system + user)
                    # 注意：这里只能使用 llm_output，因为 system/user prompt 在 agent_ctx 中
                    # 简化版只记录最终输出
                    context_builder.record_llm_call(
                        run_id=run_id,
                        step_id=step_id,
                        prompt_text=f"[Step Output] {step_id}\n\n{llm_output[:10000]}",  # 限制大小
                        department=department,
                        workflow_id=workflow_id,
                    )
                except Exception as bundle_error:
                    # Context Bundle 记录失败不阻塞主流程
                    import logging
                    logging.getLogger(__name__).debug(
                        f"Failed to record Context Bundle for step {step_id}: {bundle_error}"
                    )

        except Exception as e:
            # 产出物注册失败不阻塞主流程 (warning 模式)
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to register artifacts for step {step_id}: {e}"
            )


    @staticmethod
    def _ensure_structured_envelope(
        *,
        business_output: Any,
        structured_payload: Any,
    ) -> Dict[str, Any]:
        if isinstance(structured_payload, dict):
            normalized = dict(structured_payload)
        else:
            normalized = {}
        normalized["business_output"] = business_output
        return normalized

    @staticmethod
    def _is_literal_ssot_ref(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(
            re.match(
                r"^(?:SRC|EPIC|FEAT|REL|UI|TECH|DEVPLAN|TESTPLAN|TASK|TESTSET|TC|BUG|REPORT|ADR|EVI|ART)-",
                value.strip(),
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _filter_materializable_refs(values: Any) -> List[str]:
        refs = values if isinstance(values, list) else [values] if values is not None else []
        filtered: List[str] = []
        for item in refs:
            if not isinstance(item, str):
                continue
            ref = item.strip()
            if not ref:
                continue
            ref_root = ref.split("#", 1)[0]
            if LLMRunner._is_literal_ssot_ref(ref_root):
                filtered.append(ref)
        return filtered

    @staticmethod
    def _derive_source_refs_from_business_output(
        business_output: Any,
        *,
        allowed_prefixes: Optional[List[str]] = None,
    ) -> List[str]:
        if not isinstance(business_output, dict):
            return []

        candidates: List[Any] = []
        metadata = business_output.get("metadata")
        if isinstance(metadata, dict):
            candidates.extend([metadata.get("source_refs"), metadata.get("source_ref")])

        normalized_content = business_output.get("normalized_content")
        if isinstance(normalized_content, dict):
            candidates.extend([normalized_content.get("source_refs"), normalized_content.get("source_ref")])

        candidates.extend([business_output.get("source_refs"), business_output.get("source_ref")])

        prefixes = {prefix.upper() for prefix in (allowed_prefixes or []) if isinstance(prefix, str)}
        derived_refs: List[str] = []
        for value in candidates:
            for ref in LLMRunner._filter_materializable_refs(value):
                ref_root = ref.split("#", 1)[0].upper()
                if prefixes and not any(ref_root.startswith(f"{prefix}-") for prefix in prefixes):
                    continue
                if ref not in derived_refs:
                    derived_refs.append(ref)
        return derived_refs

    @staticmethod
    def _resolve_source_ref_from_instance_data(instance_data: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(instance_data, dict):
            return None
        params = instance_data.get("params")
        if not isinstance(params, dict):
            return None
        source_freeze = params.get("source_freeze")
        candidates: List[Any] = [source_freeze, params.get("source_freeze_ref"), params.get("src")]
        for candidate in candidates:
            if isinstance(candidate, dict):
                values = [candidate.get("id"), candidate.get("artifact_id"), candidate.get("path")]
            else:
                values = [candidate]
            for value in values:
                if not isinstance(value, str):
                    continue
                match = re.search(r"(SRC-\d+)", value.upper())
                if match:
                    return match.group(1)
        return None

    @staticmethod
    def _derive_src_title_from_business_output(business_output: Any) -> str:
        if not isinstance(business_output, dict):
            return "SRC"

        def _clean(value: Any) -> str:
            return str(value or "").strip()

        def _meaningful(value: Any) -> Optional[str]:
            text = _clean(value)
            if not text:
                return None
            if text.upper() in {"SRC", "UNTITLED SRC"}:
                return None
            return text

        normalized_content = (
            business_output.get("normalized_content")
            if isinstance(business_output.get("normalized_content"), dict)
            else {}
        )
        metadata = business_output.get("metadata") if isinstance(business_output.get("metadata"), dict) else {}

        for candidate in (
            business_output.get("title"),
            normalized_content.get("title"),
            business_output.get("name"),
            normalized_content.get("name"),
            normalized_content.get("problem_statement"),
            normalized_content.get("summary"),
            business_output.get("problem_statement"),
            business_output.get("summary"),
        ):
            title = _meaningful(candidate)
            if title:
                return title

        source_ref = _meaningful(metadata.get("source_ref") or business_output.get("source_ref"))
        domain = _meaningful(metadata.get("domain"))
        if source_ref and domain:
            return f"{source_ref} {domain}".replace("_", " ")
        if source_ref:
            return source_ref
        if domain:
            return domain.replace("_", " ")

        src_id = _meaningful(business_output.get("src_id"))
        if src_id:
            return src_id
        return "SRC"

    @staticmethod
    def _normalize_source_freeze_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "id", "") != "source_normalization":
            return business_output, structured_payload

        def _fallback_constraints() -> List[str]:
            return [
                "不新增平行 workflow key",
                "formal object 只直接物化 SRC / EPIC / FEAT",
                "UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI 默认只产 seed、view、handoff/index",
                "输出路径必须对齐当前 canonical SSOT 目录",
            ]

        def _sanitize_constraints(items: Any) -> List[str]:
            if not isinstance(items, list):
                return _fallback_constraints()
            blocked_patterns = (
                r"待补充",
                r"raw_source_input",
                r"工作区路径参考",
                r"范围排除",
                r"out of scope",
                r"下一步建议",
                r"next steps",
                r"分析师备注",
                r"\broi\b",
                r"具体功能列表",
                r"技术选型",
                r"研发排期",
                r"持久化中间草稿",
                r"内容边界",
                r"^\s*✅",
                r"\b包含\b",
            )
            required_signals = (
                "workflow",
                "ssot",
                "formal",
                "canonical",
                "path",
                "seed",
                "view",
                "handoff",
                "freeze",
                "src",
                "epic",
                "feat",
                "ui",
                "tech",
                "task",
                "testset",
                "tc",
                "report",
                "bug",
                "evi",
                "物化",
                "目录",
                "路径",
                "边界",
                "种子",
                "视图",
                "移交",
            )
            sanitized: List[str] = []
            for item in items:
                text = str(item or "").strip()
                if not text:
                    continue
                compact = re.sub(r"\s+", " ", text)
                lowered = compact.lower()
                if (
                    compact.startswith("##")
                    or compact.startswith(">")
                    or compact.startswith("--")
                    or compact.startswith("❌")
                    or any(re.search(pattern, compact, flags=re.I) for pattern in blocked_patterns)
                    or not any(signal in lowered for signal in required_signals)
                ):
                    continue
                sanitized.append(compact)
            sanitized = list(dict.fromkeys(sanitized))
            return sanitized or _fallback_constraints()

        required_fields = {
            "source_id",
            "title",
            "problem_statement",
            "target_user",
            "business_motivation",
            "constraints",
            "freeze_meta",
            "ssot",
        }
        if isinstance(business_output, dict) and required_fields.issubset(business_output.keys()):
            normalized_business = dict(business_output)
            normalized_business["constraints"] = _sanitize_constraints(
                normalized_business.get("constraints")
            )
            payload = LLMRunner._ensure_structured_envelope(
                business_output=normalized_business,
                structured_payload=structured_payload,
            )
            return normalized_business, payload

        if isinstance(structured_payload, dict):
            structured_business = structured_payload.get("business_output")
            if isinstance(structured_business, dict) and required_fields.issubset(structured_business.keys()):
                normalized_business = dict(structured_business)
                normalized_business["constraints"] = _sanitize_constraints(
                    normalized_business.get("constraints")
                )
                payload = dict(structured_payload)
                payload["business_output"] = normalized_business
                return normalized_business, payload

        params = instance_data.get("params") if isinstance(instance_data, dict) else {}
        params = params if isinstance(params, dict) else {}
        step_outputs = instance_data.get("step_outputs") if isinstance(instance_data, dict) else {}
        step_outputs = step_outputs if isinstance(step_outputs, dict) else {}

        raw_requirement = str(params.get("raw_requirement") or "").strip()
        raw_intake = step_outputs.get("raw_input_intake") if isinstance(step_outputs.get("raw_input_intake"), dict) else {}
        raw_intake_text = str(raw_intake.get("generated_text") or "").strip()
        seed_text = raw_requirement or raw_intake_text or (
            business_output if isinstance(business_output, str) else ""
        )
        seed_lines = [line.strip() for line in seed_text.splitlines() if line.strip()]

        def _extract_numbered_block(label: str) -> List[str]:
            match = re.search(
                rf"{re.escape(label)}[:：]\s*(.*?)(?=\n\s*[^\n]+[:：]\s*$|\n\s*\d+\.\s|\Z)",
                seed_text,
                flags=re.S,
            )
            if not match:
                return []
            items: List[str] = []
            for line in match.group(1).splitlines():
                normalized = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
                if normalized:
                    items.append(normalized)
            return items

        title_line = next((line for line in seed_lines if "reverse-epic-feat" in line or "SSOT" in line), "")
        title = re.sub(r"^[#*\-\s]+", "", title_line).strip(" 。:：") or "reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级"
        problem_statement = " ".join(_extract_numbered_block("当前问题")) or (
            raw_requirement[:400].strip() if raw_requirement else "当前 reverse workflow 无法完整承接现行 SSOT 文档链。"
        )
        business_motivation = " ".join(_extract_numbered_block("目标")) or problem_statement
        constraints = _sanitize_constraints(_extract_numbered_block("约束"))
        target_users = []
        if "产品经理" in raw_intake_text or "Product Manager" in raw_intake_text:
            target_users.append("产品经理")
        if "架构" in raw_intake_text or "开发" in raw_intake_text:
            target_users.extend(["架构师", "研发工程师"])
        if "QA" in raw_intake_text or "测试" in raw_intake_text:
            target_users.append("QA 工程师")
        if "审查" in raw_intake_text or "Reviewer" in raw_intake_text:
            target_users.append("治理审查员")
        if not target_users:
            target_users = ["产品经理", "研发工程师", "QA 工程师", "治理审查员"]

        adr_refs = sorted(set(re.findall(r"ADR-\d+", seed_text, flags=re.I)))
        synthesized = {
            "source_id": "SRC-DRAFT",
            "title": title,
            "problem_statement": problem_statement,
            "target_user": list(dict.fromkeys(target_users)),
            "trigger_context": title,
            "business_motivation": business_motivation,
            "constraints": constraints,
            "source_refs": [ref.upper() for ref in adr_refs],
            "freeze_meta": {"status": "draft"},
            "ssot": {
                "identity_kind": "ssot",
                "ssot_type": "SRC",
            },
        }
        payload = LLMRunner._ensure_structured_envelope(
            business_output=synthesized,
            structured_payload=structured_payload,
        )
        return synthesized, payload


class ClaudeCodeRunner(StepRunnerBase):
    """Claude Code 步骤运行器"""

    DEFAULT_SILENCE_TIMEOUT_SECONDS = 600
    DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS = LLMRunner.DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS
    AUTHORITATIVE_CONTEXT_SKIP_KEYS = LLMRunner.AUTHORITATIVE_CONTEXT_SKIP_KEYS
    FEAT_TOPIC_FAMILIES = LLMRunner.FEAT_TOPIC_FAMILIES
    PM_TASK_DRIFT_KEYWORDS = LLMRunner.PM_TASK_DRIFT_KEYWORDS
    FEAT_UI_KEYWORDS = LLMRunner.FEAT_UI_KEYWORDS
    FEAT_UI_NEGATION_PATTERNS = LLMRunner.FEAT_UI_NEGATION_PATTERNS
    _attempt_schema_repair = LLMRunner._attempt_schema_repair
    _build_schema_repair_input = staticmethod(LLMRunner._build_schema_repair_input)
    _build_schema_repair_prompt = staticmethod(LLMRunner._build_schema_repair_prompt)
    _complete_non_ui_design_step = LLMRunner._complete_non_ui_design_step
    _extract_feat_freeze_path = staticmethod(LLMRunner._extract_feat_freeze_path)
    _load_feat_bundle_payload = classmethod(LLMRunner._load_feat_bundle_payload.__func__)
    _load_yaml_frontmatter = staticmethod(LLMRunner._load_yaml_frontmatter)
    _extract_markdown_body = staticmethod(LLMRunner._extract_markdown_body)
    _feat_bundle_requires_ui = classmethod(LLMRunner._feat_bundle_requires_ui.__func__)
    _normalize_requirement_decomposer_payload = staticmethod(LLMRunner._normalize_requirement_decomposer_payload)
    _normalize_prd_writer_feat_payload = staticmethod(LLMRunner._normalize_prd_writer_feat_payload)
    _normalize_pm_planner_task_payload = staticmethod(LLMRunner._normalize_pm_planner_task_payload)
    _normalize_business_payload = staticmethod(LLMRunner._normalize_business_payload)
    _ensure_structured_envelope = staticmethod(LLMRunner._ensure_structured_envelope)
    _filter_materializable_refs = staticmethod(LLMRunner._filter_materializable_refs)
    _is_literal_ssot_ref = staticmethod(LLMRunner._is_literal_ssot_ref)
    _resolve_changed_file_paths = staticmethod(LLMRunner._resolve_changed_file_paths)
    _synthesize_single_ssot_payload = staticmethod(LLMRunner._synthesize_single_ssot_payload)
    _extract_topic_families = classmethod(LLMRunner._extract_topic_families.__func__)
    _text_contains_keyword = staticmethod(LLMRunner._text_contains_keyword)
    _load_ssot_markdown = staticmethod(LLMRunner._load_ssot_markdown)
    _validate_feat_bundle_epic_semantics = classmethod(LLMRunner._validate_feat_bundle_epic_semantics.__func__)
    _validate_pm_planner_task_semantics = classmethod(LLMRunner._validate_pm_planner_task_semantics.__func__)
    _parse_legacy_task_planning_specs_text = classmethod(LLMRunner._parse_legacy_task_planning_specs_text.__func__)
    _build_pm_planner_bundle_from_written_files = classmethod(LLMRunner._build_pm_planner_bundle_from_written_files.__func__)
    _materialize_ssot_outputs = LLMRunner._materialize_ssot_outputs
    _extract_ssot_contract_payload = LLMRunner._extract_ssot_contract_payload
    _extract_structured_segment_payload = LLMRunner._extract_structured_segment_payload
    _extract_structured_payload_from_code_blocks = LLMRunner._extract_structured_payload_from_code_blocks
    _extract_business_output_payload = LLMRunner._extract_business_output_payload
    _extract_best_written_file_payload = classmethod(LLMRunner._extract_best_written_file_payload.__func__)
    _extract_named_output_segment = staticmethod(LLMRunner._extract_named_output_segment)
    _coerce_ssot_contract_dict = staticmethod(LLMRunner._coerce_ssot_contract_dict)
    _normalize_ssot_contract_payload = staticmethod(LLMRunner._normalize_ssot_contract_payload)
    _parse_structured_output_if_possible = staticmethod(LLMRunner._parse_structured_output_if_possible)
    _merge_context_files = staticmethod(LLMRunner._merge_context_files)
    _collect_authoritative_context_files = classmethod(LLMRunner._collect_authoritative_context_files.__func__)
    _resolve_authoritative_input_value = classmethod(LLMRunner._resolve_authoritative_input_value.__func__)
    _extract_context_file_paths = classmethod(LLMRunner._extract_context_file_paths.__func__)
    _merge_forbidden_read_paths = classmethod(LLMRunner._merge_forbidden_read_paths.__func__)

    def _materialize_workspace_formal_ssot_markdown(self, *args, **kwargs):
        return LLMRunner._materialize_workspace_formal_ssot_markdown(*args, **kwargs)

    @staticmethod
    def _get_success_criteria(step) -> Dict[str, Any]:
        config = step.config or {}
        criteria = config.get("success_criteria")
        return criteria if isinstance(criteria, dict) else {}

    @staticmethod
    def _extract_commands_run(output: Dict[str, Any]) -> List[str]:
        commands = output.get("commands_run", [])
        if not isinstance(commands, list):
            return []
        result: List[str] = []
        for item in commands:
            if isinstance(item, dict):
                cmd = item.get("cmd") or item.get("command")
                if cmd:
                    result.append(str(cmd))
            elif isinstance(item, str):
                result.append(item)
        return result

    @staticmethod
    def _git_head(workspace: str) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", workspace, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                return None
            value = (proc.stdout or "").strip()
            return value or None
        except Exception:
            return None

    @staticmethod
    def _check_outputs_completed(step, workspace: str, project_root: Optional[str] = None) -> bool:
        """
        智能完成检测 (BUG-2026-0061)

        检测 step.outputs 中定义的文件是否已生成。
        如果所有必需文件都已存在，认为任务已完成，即使达到迭代上限也返回成功。

        Args:
            step: 步骤对象
            workspace: 工作目录
            project_root: 项目根目录

        Returns:
            bool: 所有必需输出文件是否都已存在
        """
        outputs = getattr(step, 'outputs', None)
        if not outputs:
            return False

        base_path = Path(workspace) if workspace else Path(project_root or ".")

        for out in outputs:
            # 只检查文件类型输出，忽略目录
            path = getattr(out, 'path', None)
            if not path:
                continue
            out_type = getattr(out, 'type', None) or ("dir" if path.endswith("/") else "file")
            if out_type == "dir":
                continue

            target = Path(path)
            if not target.is_absolute():
                target = base_path / target

            if not target.exists():
                return False

        return True

    @staticmethod
    def _parse_structured_output_if_possible(output_text: str) -> Optional[Any]:
        return OutputExtractor.parse_structured_output_if_possible(output_text)

    @classmethod
    def _extract_business_output_for_validation(
        cls,
        *,
        step,
        workflow_id: str,
        output: Dict[str, Any],
        written_files: List[str],
    ) -> tuple[Any, Any]:
        return OutputExtractor.extract_for_validation(
            step=step,
            workflow_id=workflow_id,
            output=output,
            written_files=written_files,
            extract_primary_file_output=LLMRunner._extract_primary_file_output,
            extract_best_written_file_payload=LLMRunner._extract_best_written_file_payload,
            normalize_business_payload=LLMRunner._normalize_business_payload,
        )

    @classmethod
    def _validate_success_criteria(
        cls,
        output: Dict[str, Any],
        criteria: Dict[str, Any],
        workspace: str,
        head_before: Optional[str],
    ) -> Optional[str]:
        required_commands = criteria.get("require_commands") or criteria.get("required_commands") or []
        if isinstance(required_commands, str):
            required_commands = [required_commands]
        if not isinstance(required_commands, list):
            required_commands = []

        commands_run = cls._extract_commands_run(output)
        lowered = [cmd.lower() for cmd in commands_run]

        missing: List[str] = []
        for expected in required_commands:
            expected_text = str(expected).strip().lower()
            if not expected_text:
                continue
            if not any(expected_text in cmd for cmd in lowered):
                missing.append(str(expected))
        if missing:
            return f"Missing required command(s): {', '.join(missing)}"

        if bool(criteria.get("require_new_commit", False)):
            head_after = cls._git_head(workspace)
            if not head_before or not head_after:
                return "Unable to verify git commit creation (HEAD unavailable)"
            if head_before == head_after:
                return f"No new commit detected (HEAD unchanged: {head_after[:8]})"

        return None

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "claude_code"

    @classmethod
    def _build_claude_code_input_data(
        cls,
        *,
        agent_ctx,
        claude_config: Dict[str, Any],
        workspace: str,
        workflow_id: str,
        step_id: str,
        context_files: List[str],
    ) -> Dict[str, Any]:
        return {
            "goal": agent_ctx.user_prompt or claude_config.get("goal", ""),
            "workspace": workspace,
            "step_workspace": str(
                Path(workspace) / ".workflow" / "workspace" / workflow_id / step_id
            ),
            "context_files": context_files,
            "write_scope": claude_config.get("write_scope", []),
            "read_only": bool(claude_config.get("read_only", False)),
            "forbidden_read_paths": cls._merge_forbidden_read_paths(
                claude_config.get("forbidden_read_paths")
            ),
            "max_iterations": claude_config.get("max_iterations", 5),
            "timeout_seconds": claude_config.get("timeout_seconds", 3600),
            "timeout_retries": claude_config.get("timeout_retries", 1),
            "retry_backoff_seconds": claude_config.get("retry_backoff_seconds", 5),
            "silence_timeout_seconds": claude_config.get(
                "silence_timeout_seconds", cls.DEFAULT_SILENCE_TIMEOUT_SECONDS
            ),
            "silence_grace_seconds": claude_config.get("silence_grace_seconds", 20),
            "stop_conditions": claude_config.get("stop_conditions", {}),
            "system_prompt_extra": agent_ctx.system_prompt or "",
        }

    @staticmethod
    def _build_llm_alias_input_data(*, agent_ctx) -> Dict[str, Any]:
        return {
            "system_message": agent_ctx.system_prompt or "",
            "prompt": agent_ctx.user_prompt or "",
            "temperature": agent_ctx.temperature,
            "max_tokens": agent_ctx.max_tokens,
        }

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Claude Code 步骤

        多轮 LLM + 工具调用的闭环执行器，适用于 L3 实现/修复类 step。
        """
        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", ""),
            "data": instance.data,
        }

        if self._is_identity_prepare_step(step):
            return await self._execute_identity_prepare_step(
                workflow_id=workflow_id,
                step=step,
                ctx=ctx,
                instance=instance,
            )

        if self._is_identity_formalize_step(step):
            return await self._execute_identity_formalize_step(
                workflow_id=workflow_id,
                step=step,
                ctx=ctx,
                instance=instance,
            )

        # 1. 构建 Agent 执行上下文
        agent_ctx = await ctx.agent_context_builder.build(step, workflow_context)

        # 2. ToolGuard - 签发步骤令牌
        step_token = None
        try:
            step_token = ctx.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=["read", "write", "execute"],
            )
        except Exception:
            pass

        # 3. 解析 executor_type：CLI 参数优先级最高
        # 对于 claude_code 步骤，executor_override 可能指定为 "codex"
        executor_type = instance.data.get("executor_override") or "claude_code"

        # 4. 构建执行输入
        claude_config = step.config.get("claude_code", {}) if step.config else {}
        workspace = ctx.resolve_workdir(step, instance.data.get("run_id", workflow_id))
        context_files = self._merge_context_files(
            self._collect_authoritative_context_files(step, instance.data),
            claude_config.get("context_files", []),
        )
        success_criteria = self._get_success_criteria(step)
        head_before = None
        if success_criteria.get("require_new_commit"):
            head_before = self._git_head(workspace)

        if executor_type in ("qwen", "llm"):
            input_data = self._build_llm_alias_input_data(agent_ctx=agent_ctx)
        else:
            input_data = self._build_claude_code_input_data(
                agent_ctx=agent_ctx,
                claude_config=claude_config,
                workspace=workspace,
                workflow_id=workflow_id,
                step_id=step.id,
                context_files=context_files,
            )

            # 仅在显式配置时传 allowed_commands，避免把空列表传给执行器导致 Bash 被禁用。
            configured_allowed_commands = claude_config.get("allowed_commands")
            if isinstance(configured_allowed_commands, list) and configured_allowed_commands:
                input_data["allowed_commands"] = configured_allowed_commands
            if "setting_sources" in claude_config:
                input_data["setting_sources"] = claude_config.get("setting_sources", "")
            if "strict_mcp_config" in claude_config:
                input_data["strict_mcp_config"] = bool(claude_config.get("strict_mcp_config"))
            if claude_config.get("mcp_config_path"):
                input_data["mcp_config_path"] = claude_config.get("mcp_config_path")
            if claude_config.get("model"):
                input_data["model"] = claude_config.get("model")
            if "max_bash_calls" in claude_config:
                input_data["max_bash_calls"] = claude_config.get("max_bash_calls")
            if "resume_on_retry" in claude_config:
                input_data["resume_on_retry"] = bool(claude_config.get("resume_on_retry"))

        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)

        # Evidence 目录仅适用于 code-style 执行器
        if executor_type not in ("qwen", "llm"):
            run_id = instance.data.get("run_id", workflow_id)
            evidence_base = str(
                Path(workspace) / ".workflow" / "claude-code" / f"{run_id}-{step.id}"
            )
            input_data["evidence_base"] = evidence_base

        # 5. 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=executor_type,
            input_data={k: v for k, v in input_data.items() if k != "token_context"},
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await ctx.store.create_task_execution(execution)

        if getattr(step, "agent_id", "") == "agent.design.ui_designer":
            ui_required = self._feat_bundle_requires_ui(instance.data)
            if ui_required is False:
                return await self._complete_non_ui_design_step(
                    workflow_id=workflow_id,
                    step=step,
                    ctx=ctx,
                    execution_id=execution_id,
                    reason="Source FEAT bundle does not describe any UI surface.",
                )

        # P0-5: 记录步骤执行开始日志
        import logging
        logging.info(f"[ClaudeCodeRunner] Starting execution for step {step.id} (workflow={workflow_id}, execution={execution_id})")

        try:
            # 6. v3.4: AsyncRetryExecutor 包裹 Claude Code/Codex 调用
            executor = ctx.executor_factory.create(executor_type)
            retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)
            retry_result = await retry_executor.execute(executor.execute, input_data)

            if not retry_result.success:
                error_msg = retry_result.final_error or "Claude Code call failed after retries"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=f"Retry exhausted ({retry_result.total_attempts} attempts): {error_msg}",
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code failed after {retry_result.total_attempts} attempts: {error_msg}",
                )

            output = retry_result.result
            status = output.get("status", "fail")

            # 6. 治理 Gate：diff 过大检查
            diff_summary = output.get("diff_summary", {})
            max_diff_files = claude_config.get("max_diff_files", 1000)
            if diff_summary.get("files_changed", 0) > max_diff_files:
                status = "needs_human"
                output["error"] = (
                    f"Diff too large: {diff_summary['files_changed']} files changed "
                    f"(limit: {max_diff_files})"
                )

            # 7. 处理 needs_human → 暂停工作流
            if status == "needs_human":
                from lee.orchestrator.storage.models import WorkflowStatus

                await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=output.get("error", "Needs human review"),
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="blocked",
                    blocked_reason="claude_code_needs_human",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code step requires human review: {output.get('error', '')}",
                    output=output,
                )

            # 8. 失败处理
            if status in ("fail", "failed", "timeout"):
                error_msg = output.get("error", f"Claude Code step {status}")
                debug_hint = output.get("debug_log_path") or output.get("conversation_log_path")
                if debug_hint:
                    error_msg = f"{error_msg} (debug: {debug_hint})"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=error_msg,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=error_msg,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code execution failed: {error_msg}",
                    output=output,
                )

            criteria_error = self._validate_success_criteria(
                output=output,
                criteria=success_criteria,
                workspace=workspace,
                head_before=head_before,
            )
            if criteria_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, criteria_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=criteria_error,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=criteria_error,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code success criteria not met: {criteria_error}",
                    output=output,
                )

            # 9. 收集证据
            evidence_path = output.get("evidence_bundle_path", "")
            if evidence_path:
                await self._collect_evidence(ctx, workflow_id, step.id, [evidence_path])
            changed = output.get("changed_files", [])
            if changed:
                abs_changed = self._resolve_changed_file_paths(
                    workspace=workspace,
                    project_root=ctx.project_root,
                    changed_files=changed,
                )
                await self._collect_evidence(ctx, workflow_id, step.id, abs_changed)

            # 10. Verifiers
            verifier_results = await self._run_verifiers(ctx, workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(ctx, verifier_results):
                await ctx.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # v3.4: 输出 Contract Schema 校验
            business_output, structured_payload = self._extract_business_output_for_validation(
                step=step,
                workflow_id=workflow_id,
                output=output,
                written_files=abs_changed if changed else [],
            )
            business_output, structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=business_output,
                structured_payload=structured_payload,
                instance_data=instance.data,
            )
            if isinstance(business_output, dict):
                output["business_output"] = business_output
            if isinstance(structured_payload, dict):
                output["structured_payload"] = structured_payload
            cc_validation = self._validate_step_output(step, business_output)
            if cc_validation and not cc_validation.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {cc_validation.errors[0].message if cc_validation.errors else 'unknown'}"
                    repaired = await self._attempt_schema_repair(
                        executor=executor,
                        executor_type=executor_type,
                        input_data=input_data,
                        step=step,
                        workflow_id=workflow_id,
                        validation_error=error_msg,
                        business_output=business_output,
                        structured_payload=structured_payload,
                    )
                    if repaired:
                        repaired_validation = self._validate_step_output(step, repaired["business_output"])
                        if not repaired_validation or repaired_validation.passed:
                            business_output = repaired["business_output"]
                            structured_payload = repaired["structured_payload"]
                            output["schema_repair_retry"] = True
                            output["business_output"] = business_output
                            if isinstance(structured_payload, dict):
                                output["structured_payload"] = structured_payload
                            cc_validation = repaired_validation
                        else:
                            error_msg = (
                                "Output schema validation failed after repair retry: "
                                f"{repaired_validation.errors[0].message if repaired_validation.errors else 'unknown'}"
                            )
                            cc_validation = repaired_validation
                    if cc_validation and not cc_validation.passed:
                        await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                        await ctx.store.update_task_execution(
                            execution_id,
                            TaskExecutionStatus.FAILED,
                            output_data={
                                "raw_output": output.get("raw_output", "") or json.dumps(output),
                                "business_output": business_output,
                                "structured_payload": structured_payload,
                                "validation_result": cc_validation.to_dict(),
                            },
                            error_message=error_msg,
                            completed_at=datetime.now(),
                        )
                        return StepResult(
                            status="failed",
                            step_id=step.id,
                            workflow_id=workflow_id,
                            message=error_msg,
                        )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

            semantic_error = None
            agent_id = getattr(step, "agent_id", "")
            if agent_id == "agent.product.prd_writer":
                semantic_error = self._validate_feat_bundle_epic_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            elif agent_id == "agent.product.pm_planner":
                semantic_error = self._validate_pm_planner_task_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            elif agent_id == "agent.product.feat_reviewer":
                expected_subject_refs = LLMRunner._expected_feat_review_subject_refs(instance.data)
                semantic_error = LLMRunner._validate_feat_review_subject_refs(
                    business_output,
                    expected_subject_refs,
                )
                if not semantic_error:
                    semantic_error = LLMRunner._validate_feat_review_semantics(
                        business_output,
                        expected_subject_refs,
                    )
            elif agent_id == "agent.product.delivery_plan_reviewer":
                expected_subject_refs = LLMRunner._expected_delivery_plan_subject_refs(
                    instance.data,
                    business_output if isinstance(business_output, dict) else None,
                )
                semantic_error = LLMRunner._validate_delivery_plan_review_subject_refs(
                    business_output,
                    expected_subject_refs,
                )
                if not semantic_error:
                    semantic_error = LLMRunner._validate_delivery_plan_review_semantics(
                        project_root=ctx.project_root,
                        review_payload=business_output,
                        instance_data=instance.data,
                    )
            if semantic_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, semantic_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "raw_output": output.get("raw_output", "") or json.dumps(output),
                        "business_output": business_output,
                        "structured_payload": structured_payload,
                    },
                    error_message=semantic_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=semantic_error,
                )

            ssot_materialized = await self._materialize_ssot_outputs(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                generated_text=output.get("generated_text", "") or output.get("raw_output", ""),
                structured_payload=structured_payload,
                written_files=abs_changed if changed else [],
            )
            if ssot_materialized:
                materialized_files = ssot_materialized.get("materialized_files", [])
                if materialized_files:
                    await self._collect_evidence(ctx, workflow_id, step.id, materialized_files)
                    changed = list(dict.fromkeys(changed + materialized_files))
                output["ssot_materialized"] = ssot_materialized["outputs"]

            workspace_files = self._materialize_symbolic_workspace_outputs(
                step=step,
                workflow_id=workflow_id,
                project_root=ctx.project_root,
                business_output=business_output,
                structured_payload=structured_payload,
            )
            if workspace_files:
                output["workspace_artifacts"] = list(
                    dict.fromkeys((output.get("workspace_artifacts") or []) + workspace_files)
                )
                changed = list(dict.fromkeys(changed + workspace_files))

            # BUG-2026-0061: 智能完成检测
            # 即使状态是 fail，如果是因达到迭代上限但输出文件已完成，仍视为成功
            iterations_used = output.get("iterations_used", 0)
            max_iterations = input_data.get("max_iterations", 5)
            if status == "fail" and iterations_used >= max_iterations:
                # 检测输出文件是否已完成
                if self._check_outputs_completed(step, workspace, ctx.project_root):
                    logging.info(
                        f"[ClaudeCodeRunner] Smart completion: step {step.id} reached max iterations "
                        f"({iterations_used}/{max_iterations}) but outputs are complete, treating as success"
                    )
                    status = "success"
                    output["status"] = "success"
                    output["smart_completion"] = True

            # 11. 完成步骤
            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output,
                step_outputs=step.outputs if hasattr(step, 'outputs') else None
            )

            # P0-1: 确保 task_execution 状态更新（BUG-2026-0038）
            # 使用重试机制确保状态更新成功
            updated = await self._update_task_execution_with_retry(
                ctx,
                execution_id,
                TaskExecutionStatus.COMPLETED,
                max_retries=3,
                output_data=output,
                completed_at=datetime.now(),
            )
            if updated:
                logging.info(f"[ClaudeCodeRunner] Updated task_execution {execution_id} to COMPLETED for step {step.id}")
            else:
                logging.error(f"[ClaudeCodeRunner] Failed to update task_execution {execution_id} after retries")

            changed = output.get("changed_files", [])
            ctx.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "claude_code",
                outputs=changed,
                outputs_hash=ctx.event_log._compute_hash(output),
            )

            result.message = (
                f"Step {step.id} completed via Claude Code. "
                f"Files changed: {diff_summary.get('files_changed', 0)}, "
                f"Iterations: {output.get('iterations_used', '?')}"
            )
            return result

        except Exception as e:
            await ctx.state_machine.fail_step(workflow_id, step.id, str(e))
            # 使用重试机制更新失败状态 (BUG-2026-0038)
            await self._update_task_execution_with_retry(
                ctx,
                execution_id,
                TaskExecutionStatus.FAILED,
                max_retries=3,
                error_message=str(e),
                completed_at=datetime.now(),
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error in Claude Code step: {e}",
            )
        finally:
            if step_token:
                try:
                    ctx.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass
