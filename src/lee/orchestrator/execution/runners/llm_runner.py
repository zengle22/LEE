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
import subprocess
import uuid
import difflib
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY, RetryPolicy
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext
from lee.orchestrator.execution.llm_executor import LLMExecutor as RealLLMExecutor


class LLMRunner(StepRunnerBase):
    """Agent (LLM) 步骤运行器 - 使用智谱 GLM 模型"""

    DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS = [
        "output/",
        "evidence/",
        ".workflow/claude-code/",
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

        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)
        return input_data

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

        for path in candidate_paths:
            if not path.exists() or path.suffix.lower() != ".md":
                continue
            try:
                front_matter, _body = parse_front_matter(path)
            except Exception:
                continue

            artifact_id = front_matter.get("id")
            ssot_type_value = front_matter.get("ssot_type")
            title = front_matter.get("title")
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                continue
            if not isinstance(ssot_type_value, str) or not ssot_type_value.strip():
                continue
            try:
                ssot_type = SSOTType(ssot_type_value.strip().lower())
            except Exception:
                continue

            try:
                status = ArtifactStatus(str(front_matter.get("status", "active")).upper())
            except Exception:
                status = ArtifactStatus.ACTIVE

            derived_from_ids = front_matter.get("derived_from_ids")
            source_refs = front_matter.get("source_refs")
            owner = front_matter.get("owner")
            tags = front_matter.get("tags")
            version = front_matter.get("version")
            properties = front_matter.get("properties")

            artifact = manager.create_ssot(
                ssot_type=ssot_type,
                title=str(title or artifact_id).strip() or artifact_id.strip(),
                content=path,
                run_id=workflow_id,
                formal_id=artifact_id.strip(),
                parent_id=front_matter.get("parent_id"),
                derived_from=derived_from_ids if isinstance(derived_from_ids, list) else [],
                source_refs=source_refs if isinstance(source_refs, list) else [],
                owner=owner if isinstance(owner, str) else None,
                tags=tags if isinstance(tags, list) else [],
                status=status,
                version=str(version or "v1"),
                properties=properties if isinstance(properties, dict) else {},
            )

            output_key = "ui_prototype" if ssot_type == SSOTType.UI else "tech_spec"
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
                for value in output.get("verifies", []) or []:
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

    def _expected_feat_review_subject_refs(
        self,
        instance_data: Dict[str, Any],
    ) -> List[str]:
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data, dict) else {}
        feat_spec_output = step_outputs.get("feat_spec_generation")
        if not isinstance(feat_spec_output, dict):
            return []

        ssot_materialized = feat_spec_output.get("ssot_materialized")
        if isinstance(ssot_materialized, dict):
            feat_entry = ssot_materialized.get("feat")
            if isinstance(feat_entry, dict):
                feat_id = feat_entry.get("id")
                if isinstance(feat_id, str) and feat_id.strip():
                    return [feat_id]
            elif isinstance(feat_entry, list):
                materialized_ids = [
                    item.get("id")
                    for item in feat_entry
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id").strip()
                ]
                if materialized_ids:
                    return materialized_ids

        generated_text = feat_spec_output.get("generated_text", "")
        feat_payload: Any = None
        try:
            parsed_output = StepRunnerBase._parse_structured_output(generated_text)
        except Exception:
            parsed_output = None

        if isinstance(parsed_output, dict):
            if isinstance(parsed_output.get("business_output"), dict):
                feat_payload = parsed_output.get("business_output")
            else:
                feat_payload = parsed_output

        if feat_payload is None:
            feat_payload = self._extract_business_output_payload(None, generated_text)
        if not isinstance(feat_payload, dict):
            return []

        bundle_specs = feat_payload.get("feat_specs")
        if isinstance(bundle_specs, list):
            feat_ids = [
                item.get("feat_id")
                for item in bundle_specs
                if isinstance(item, dict) and isinstance(item.get("feat_id"), str) and item.get("feat_id").strip()
            ]
            if feat_ids:
                return feat_ids

        feat_id = feat_payload.get("feat_id")
        return [feat_id] if isinstance(feat_id, str) and feat_id.strip() else []

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
                normalized_item = dict(item)

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
        if getattr(step, "agent_id", "") != "agent.product.prd_writer":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        actual_epic_ref = LLMRunner._resolve_epic_ref_from_instance_data(instance_data)
        step_config = getattr(step, "config", {}) or {}
        output_contract = str(step_config.get("output_contract") or "").replace("\\", "/")
        expects_bundle = output_contract.endswith("feat-bundle-contract/v1/schema.json") or (
            not output_contract and getattr(step, "id", "") == "feat_spec_generation"
        )

        def _clean_text(value: Any) -> str:
            return str(value or "").strip()

        def _normalize_priority(value: Any) -> str:
            normalized = _clean_text(value).upper()
            if normalized in {"P0", "P1", "P2"}:
                return normalized
            if normalized in {"HIGH", "CRITICAL"}:
                return "P0"
            if normalized in {"MEDIUM", "NORMAL"}:
                return "P1"
            if normalized in {"LOW"}:
                return "P2"
            if normalized in {"0", "1", "2"}:
                return f"P{normalized}"
            if normalized.startswith("P") and len(normalized) > 1 and normalized[1:].isdigit():
                return normalized if normalized in {"P0", "P1", "P2"} else "P1"
            return "P1"

        def _normalize_lifecycle_status(value: Any) -> str:
            normalized = _clean_text(value).lower()
            mapping = {
                "draft": "draft",
                "active": "active",
                "frozen": "frozen",
                "archived": "archived",
                "completed": "active",
                "complete": "active",
                "success": "active",
                "done": "active",
                "specified": "draft",
            }
            return mapping.get(normalized, "draft")

        def _normalize_string_list(values: Any, *, fallback: Optional[List[str]] = None) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_items: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = (
                        item.get("description")
                        or item.get("criterion")
                        or item.get("title")
                        or item.get("id")
                    )
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_items.append(text)
            if normalized_items:
                return normalized_items
            return [text for text in (fallback or []) if _clean_text(text)]

        def _normalize_dependency_ids(values: Any) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_dependencies: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = item.get("id") or item.get("feat_id") or item.get("epic_id") or item.get("title")
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_dependencies.append(text)
            return normalized_dependencies

        def _normalize_acceptance_criteria(values: Any, *, title: str, goal: str) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_criteria: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = item.get("description") or item.get("criterion") or item.get("validation")
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_criteria.append(text)
            if normalized_criteria:
                return normalized_criteria
            fallback_text = goal or title or "Feature is independently acceptable"
            return [fallback_text]

        def _build_acceptance_checks(
            feat_item: Dict[str, Any],
            acceptance_criteria: List[str],
        ) -> List[Dict[str, Any]]:
            raw_checks = feat_item.get("acceptance_checks")
            normalized_checks: List[Dict[str, Any]] = []
            if isinstance(raw_checks, list):
                for index, item in enumerate(raw_checks[:5], start=1):
                    if not isinstance(item, dict):
                        normalized_checks.append(
                            {
                                "id": f"AC-{index:03d}",
                                "scenario": _clean_text(item),
                                "given": "",
                                "when": "",
                                "then": "",
                                "trace_hints": ["TECH"],
                            }
                        )
                        continue
                    normalized_item = dict(item)
                    normalized_item.setdefault("id", f"AC-{index:03d}")
                    normalized_item.setdefault("scenario", "")
                    normalized_item.setdefault("given", "")
                    normalized_item.setdefault("when", "")
                    normalized_item.setdefault("then", "")
                    trace_hints = normalized_item.get("trace_hints")
                    if not isinstance(trace_hints, list) or not trace_hints:
                        normalized_item["trace_hints"] = ["TECH"]
                    normalized_checks.append(normalized_item)
            if normalized_checks:
                return normalized_checks

            scenario_seed = acceptance_criteria[:5]
            if len(scenario_seed) == 1:
                scenario_seed.append(f"{feat_item.get('title') or 'Feature'} remains traceable")
            if not scenario_seed:
                scenario_seed = [
                    feat_item.get("goal") or feat_item.get("title") or "Feature behavior is verifiable",
                    f"{feat_item.get('title') or 'Feature'} outputs remain stable",
                ]

            synthesized_checks: List[Dict[str, Any]] = []
            for index, criterion in enumerate(scenario_seed[:5], start=1):
                synthesized_checks.append(
                    {
                        "id": f"AC-{index:03d}",
                        "scenario": criterion,
                        "given": feat_item.get("title") or "",
                        "when": "the feature workflow runs",
                        "then": criterion,
                        "trace_hints": ["TECH"],
                    }
                )
            return synthesized_checks

        def _extract_breakdown_feature_candidates(
            payload: Dict[str, Any],
            fallback_epic_ref: Optional[str],
        ) -> tuple[Optional[List[Any]], Optional[str]]:
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            resolved_epic_ref = (
                _clean_text(payload.get("epic_ref"))
                or _clean_text(metadata.get("epic_id"))
                or fallback_epic_ref
            )
            if isinstance(payload.get("features"), list):
                return payload.get("features"), resolved_epic_ref
            if isinstance(payload.get("feats"), list):
                return payload.get("feats"), resolved_epic_ref
            if isinstance(payload.get("feat_candidates"), list):
                return payload.get("feat_candidates"), resolved_epic_ref
            if isinstance(payload.get("feat_specifications"), list):
                return payload.get("feat_specifications"), resolved_epic_ref

            epic_breakdowns = payload.get("epic_breakdowns")
            if not isinstance(epic_breakdowns, list):
                return None, resolved_epic_ref

            selected_breakdown: Optional[Dict[str, Any]] = None
            if resolved_epic_ref:
                for item in epic_breakdowns:
                    if not isinstance(item, dict):
                        continue
                    if _clean_text(item.get("epic_id")).lower() == resolved_epic_ref.lower():
                        selected_breakdown = item
                        break
            if selected_breakdown is None:
                for item in epic_breakdowns:
                    if isinstance(item, dict) and isinstance(item.get("features"), list):
                        selected_breakdown = item
                        break
            if not isinstance(selected_breakdown, dict):
                return None, resolved_epic_ref

            resolved_epic_ref = _clean_text(selected_breakdown.get("epic_id")) or resolved_epic_ref
            if isinstance(selected_breakdown.get("features"), list):
                return selected_breakdown.get("features"), resolved_epic_ref
            return None, resolved_epic_ref

        def _is_placeholder_input_value(value: Any) -> bool:
            normalized = _clean_text(value).lower()
            if not normalized:
                return True
            placeholder_markers = (
                "inputs defined by epic scope",
                "input defined by epic scope",
                "same as epic",
                "tbd",
                "to be defined",
                "待补充",
                "待定义",
                "同 epic",
            )
            return any(marker in normalized for marker in placeholder_markers)

        def _normalize_input_entries(value: Any, *, fallback: Optional[List[Any]] = None) -> List[Any]:
            items = value if isinstance(value, list) else [value] if value is not None else []
            normalized_entries: List[Any] = []
            for item in items:
                if isinstance(item, dict):
                    normalized_item: Dict[str, Any] = {}
                    for raw_key, raw_value in item.items():
                        key = _clean_text(raw_key)
                        if not key:
                            continue
                        if isinstance(raw_value, dict):
                            nested: Dict[str, str] = {}
                            for nested_key, nested_value in raw_value.items():
                                normalized_nested_key = _clean_text(nested_key)
                                normalized_nested_value = _clean_text(nested_value)
                                if normalized_nested_key and normalized_nested_value:
                                    nested[normalized_nested_key] = normalized_nested_value
                            if nested:
                                normalized_item[key] = nested
                        elif isinstance(raw_value, list):
                            normalized_list = [_clean_text(part) for part in raw_value if _clean_text(part)]
                            if normalized_list:
                                normalized_item[key] = normalized_list
                        else:
                            text_value = _clean_text(raw_value)
                            if text_value:
                                normalized_item[key] = text_value
                    if normalized_item:
                        normalized_entries.append(normalized_item)
                    continue
                text_value = _clean_text(item)
                if text_value:
                    normalized_entries.append(text_value)
            if normalized_entries:
                return normalized_entries
            if fallback:
                return _normalize_input_entries(fallback, fallback=None)
            return []

        def _extract_input_field_names(inputs: List[Any]) -> List[str]:
            field_names: List[str] = []
            for item in inputs:
                if isinstance(item, str):
                    if not _is_placeholder_input_value(item):
                        field_names.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                for raw_key, raw_value in item.items():
                    key = _clean_text(raw_key)
                    if not key:
                        continue
                    if isinstance(raw_value, dict) and raw_value:
                        for nested_key in raw_value.keys():
                            normalized_nested_key = _clean_text(nested_key)
                            if normalized_nested_key:
                                field_names.append(f"{key}.{normalized_nested_key}")
                    else:
                        field_names.append(key)
            return list(dict.fromkeys(field_names))

        def _normalize_input_contract(
            contract_value: Any,
            *,
            inputs: List[Any],
            source_refs: List[str],
            epic_ref: Optional[str],
        ) -> Dict[str, Any]:
            existing = contract_value if isinstance(contract_value, dict) else {}
            required_artifacts = _normalize_string_list(
                existing.get("required_artifacts"),
                fallback=source_refs or ([f"{epic_ref}#scope"] if epic_ref else []),
            )
            required_fields = _normalize_string_list(
                existing.get("required_fields"),
                fallback=_extract_input_field_names(inputs),
            )
            optional_fields = _normalize_string_list(existing.get("optional_fields"))
            consumption_rules = _normalize_string_list(
                existing.get("consumption_rules"),
                fallback=[
                    (
                        f"Consume {required_artifacts[0]} and map fields "
                        f"{', '.join(required_fields[:3])}"
                    )
                    if required_artifacts and required_fields
                    else "Consume upstream FEAT context and preserve traceability"
                ],
            )
            return {
                "required_artifacts": required_artifacts,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "consumption_rules": consumption_rules,
            }

        def _synthesize_feat_spec(candidate: Dict[str, Any], epic_ref: Optional[str]) -> Dict[str, Any]:
            title = _clean_text(candidate.get("title")) or "Untitled FEAT"
            feat_id = _clean_text(candidate.get("feat_id") or candidate.get("id"))
            if not feat_id:
                slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").upper()
                feat_id = f"FEAT-{slug}" if slug else "FEAT-AUTO"

            business_context = candidate.get("business_context") if isinstance(candidate.get("business_context"), dict) else {}
            scope_boundary = candidate.get("scope_boundary") if isinstance(candidate.get("scope_boundary"), dict) else {}
            requirement = candidate.get("requirement") if isinstance(candidate.get("requirement"), dict) else {}
            interface_spec = candidate.get("interface_spec") if isinstance(candidate.get("interface_spec"), dict) else {}
            input_schema = interface_spec.get("input_schema") if isinstance(interface_spec.get("input_schema"), dict) else {}
            output_schema = interface_spec.get("output_schema") if isinstance(interface_spec.get("output_schema"), dict) else {}
            state_machine = candidate.get("state_machine") if isinstance(candidate.get("state_machine"), dict) else {}
            dependency_block = candidate.get("dependencies") if isinstance(candidate.get("dependencies"), dict) else {}
            description = _clean_text(candidate.get("description"))
            rich_description = _clean_text(requirement.get("description"))
            goal = _clean_text(candidate.get("goal")) or rich_description or description or title
            user_value = (
                _clean_text(candidate.get("user_value"))
                or _clean_text(business_context.get("problem"))
                or rich_description
                or description
                or title
            )
            inputs = _normalize_input_entries(
                candidate.get("inputs")
                or candidate.get("input")
                or [
                    field.get("name")
                    for field in (input_schema.get("fields") if isinstance(input_schema.get("fields"), list) else [])
                    if isinstance(field, dict) and _clean_text(field.get("name"))
                ]
                or scope_boundary.get("in_scope"),
                fallback=[],
            )
            processing = _normalize_string_list(
                candidate.get("processing")
                or [
                    transition.get("trigger")
                    for transition in (state_machine.get("transitions") if isinstance(state_machine.get("transitions"), list) else [])
                    if isinstance(transition, dict) and _clean_text(transition.get("trigger"))
                ],
                fallback=[rich_description or description or f"Deliver {title} capability"],
            )
            outputs = _normalize_string_list(
                candidate.get("outputs")
                or candidate.get("output")
                or [
                    field.get("name")
                    for field in (output_schema.get("fields") if isinstance(output_schema.get("fields"), list) else [])
                    if isinstance(field, dict) and _clean_text(field.get("name"))
                ]
                or candidate.get("acceptance_boundary"),
                fallback=[f"{title} FEAT specification"],
            )
            acceptance_criteria = _normalize_acceptance_criteria(
                candidate.get("acceptance_criteria")
                or requirement.get("acceptance_criteria")
                or candidate.get("acceptance_boundaries"),
                title=title,
                goal=goal,
            )
            non_goals = _normalize_string_list(
                candidate.get("non_goals") or scope_boundary.get("out_of_scope"),
            )
            priority = _normalize_priority(candidate.get("priority"))
            parent_workflow = _clean_text(candidate.get("parent_workflow"))
            category = _clean_text(candidate.get("category"))
            delivery_slice = _clean_text(candidate.get("delivery_slice")) or parent_workflow or category or "core"
            normalized_epic_ref = epic_ref or _clean_text(candidate.get("parent_epic"))
            source_refs = _normalize_string_list(
                candidate.get("source_refs"),
                fallback=[f"{normalized_epic_ref}#scope"] if normalized_epic_ref else [],
            )
            dependencies = _normalize_dependency_ids(
                candidate.get("dependencies")
                if not isinstance(candidate.get("dependencies"), dict)
                else dependency_block.get("upstream")
            )

            synthesized = {
                "feat_id": feat_id,
                "title": title,
                "goal": goal,
                "user_value": user_value,
                "inputs": inputs,
                "input_contract": _normalize_input_contract(
                    candidate.get("input_contract"),
                    inputs=inputs,
                    source_refs=source_refs,
                    epic_ref=normalized_epic_ref,
                ),
                "processing": processing,
                "outputs": outputs,
                "acceptance_criteria": acceptance_criteria,
                "dependencies": dependencies,
                "non_goals": non_goals,
                "priority": priority,
                "delivery_slice": delivery_slice,
                "lifecycle_status": _normalize_lifecycle_status(
                    candidate.get("lifecycle_status") or candidate.get("status")
                ),
                "source_refs": source_refs,
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "FEAT",
                    "parent": normalized_epic_ref,
                    "derived_from": normalized_epic_ref,
                },
                "testability_seed": {
                    "risk_notes": non_goals,
                    "integration_points": [value for value in [parent_workflow, category] if value],
                    "priority_hint": priority,
                },
            }
            synthesized["acceptance_checks"] = _build_acceptance_checks(synthesized, acceptance_criteria)
            return synthesized

        def _normalize_user_story_item(item: Any) -> Optional[Dict[str, str]]:
            if not isinstance(item, dict):
                return None

            as_a = _clean_text(item.get("as_a") or item.get("role") or item.get("actor"))
            i_want = _clean_text(item.get("i_want") or item.get("action") or item.get("need"))
            so_that = _clean_text(
                item.get("so_that")
                or item.get("benefit")
                or item.get("value")
                or item.get("outcome")
            )
            if not (as_a and i_want and so_that):
                return None

            return {
                "as_a": as_a,
                "i_want": i_want,
                "so_that": so_that,
            }

        def normalize_feat_item(feat_item: Any) -> Any:
            if not isinstance(feat_item, dict):
                return feat_item

            normalized_feat = dict(feat_item)

            def _truncate_list(values: Any, max_items: int) -> Any:
                if not isinstance(values, list):
                    return values
                return values[:max_items]

            ssot = normalized_feat.get("ssot")
            if isinstance(ssot, dict):
                normalized_ssot = dict(ssot)
            else:
                normalized_ssot = {}
            feat_id = _clean_text(normalized_feat.get("feat_id") or normalized_feat.get("id"))
            if not feat_id:
                seed_text = (
                    _clean_text(normalized_feat.get("title"))
                    or _clean_text(normalized_feat.get("goal"))
                    or _clean_text(normalized_feat.get("name"))
                )
                seed_slug = re.sub(r"[^A-Za-z0-9]+", "-", seed_text).strip("-").lower()
                feat_id = (
                    f"feat-{seed_slug}"
                    if seed_slug
                    else (
                        f"{actual_epic_ref}-feat"
                        if actual_epic_ref
                        else "FEAT-AUTO"
                    )
                )
            if feat_id:
                normalized_feat["feat_id"] = feat_id
            title = _clean_text(normalized_feat.get("title")) or feat_id or "Untitled FEAT"
            normalized_feat["title"] = title
            goal = _clean_text(normalized_feat.get("goal") or normalized_feat.get("description")) or title
            normalized_feat["goal"] = goal
            normalized_feat["user_value"] = (
                _clean_text(normalized_feat.get("user_value"))
                or _clean_text(
                    normalized_feat.get("business_context", {}).get("problem")
                    if isinstance(normalized_feat.get("business_context"), dict)
                    else ""
                )
                or _clean_text(normalized_feat.get("description"))
                or title
            )
            scope_boundary = normalized_feat.get("scope_boundary")
            if not isinstance(scope_boundary, dict):
                scope_boundary = {}
            normalized_feat["inputs"] = _truncate_list(
                _normalize_input_entries(
                    normalized_feat.get("inputs") or normalized_feat.get("input") or scope_boundary.get("in_scope"),
                    fallback=[
                        normalized_feat.get("source_refs", [f"{actual_epic_ref}#scope"])[0]
                        if isinstance(normalized_feat.get("source_refs"), list) and normalized_feat.get("source_refs")
                        else (f"{actual_epic_ref}#scope" if actual_epic_ref else title)
                    ],
                ),
                5,
            )
            normalized_feat["input_contract"] = _normalize_input_contract(
                normalized_feat.get("input_contract"),
                inputs=normalized_feat.get("inputs") or [],
                source_refs=normalized_feat.get("source_refs") if isinstance(normalized_feat.get("source_refs"), list) else [],
                epic_ref=actual_epic_ref
                or _clean_text(normalized_feat.get("epic_ref"))
                or _clean_text(normalized_ssot.get("parent")),
            )
            normalized_feat["processing"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("processing"),
                    fallback=[_clean_text(normalized_feat.get("description")) or f"Deliver {title} capability"],
                ),
                5,
            )
            normalized_feat["outputs"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("outputs")
                    or normalized_feat.get("output")
                    or normalized_feat.get("acceptance_boundary"),
                    fallback=[f"{title} FEAT specification"],
                ),
                5,
            )
            normalized_feat["acceptance_criteria"] = _truncate_list(
                _normalize_acceptance_criteria(
                    normalized_feat.get("acceptance_criteria") or normalized_feat.get("acceptance_boundaries"),
                    title=title,
                    goal=goal,
                ),
                5,
            )
            normalized_feat["dependencies"] = _truncate_list(
                _normalize_dependency_ids(normalized_feat.get("dependencies")),
                10,
            )
            normalized_feat["non_goals"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("non_goals") or scope_boundary.get("out_of_scope"),
                ),
                10,
            )
            normalized_feat["priority"] = _normalize_priority(normalized_feat.get("priority"))
            normalized_feat["delivery_slice"] = (
                _clean_text(normalized_feat.get("delivery_slice"))
                or _clean_text(normalized_feat.get("parent_workflow"))
                or _clean_text(normalized_feat.get("category"))
                or "core"
            )
            normalized_feat["lifecycle_status"] = _normalize_lifecycle_status(
                normalized_feat.get("lifecycle_status") or normalized_feat.get("status")
            )
            source_refs = normalized_feat.get("source_refs")
            if isinstance(source_refs, list):
                normalized_feat["source_refs"] = _truncate_list(
                    _normalize_string_list(source_refs),
                    5,
                )
            if normalized_feat.get("feat_id"):
                normalized_ssot.setdefault("identity_kind", "ssot")
                normalized_ssot.setdefault("ssot_type", "FEAT")
                normalized_ssot.setdefault(
                    "parent",
                    actual_epic_ref
                    or _clean_text(normalized_feat.get("epic_ref"))
                    or _clean_text(normalized_ssot.get("parent")),
                )
                normalized_ssot.setdefault(
                    "derived_from",
                    actual_epic_ref
                    or _clean_text(normalized_feat.get("epic_ref"))
                    or _clean_text(normalized_ssot.get("derived_from"))
                    or _clean_text(normalized_ssot.get("parent")),
                )
            if normalized_ssot:
                normalized_feat["ssot"] = normalized_ssot

            derived = normalized_feat.get("derived_object_expectations")
            if isinstance(derived, dict):
                normalized_derived = dict(derived)
            else:
                normalized_derived = {}
            normalized_derived.setdefault("task_required", True)
            normalized_derived.setdefault("testset_required", True)
            normalized_derived.setdefault("testset_owner", "qa")
            normalized_derived.setdefault("qa_seed_required", True)
            normalized_feat["derived_object_expectations"] = normalized_derived
            testability_seed = normalized_feat.get("testability_seed")
            if isinstance(testability_seed, dict):
                normalized_testability = dict(testability_seed)
            else:
                normalized_testability = {}
            normalized_testability.setdefault("risk_notes", normalized_feat.get("non_goals") or [])
            normalized_testability.setdefault("integration_points", normalized_feat.get("dependencies") or [])
            normalized_testability.setdefault("priority_hint", normalized_feat.get("priority"))
            normalized_feat["testability_seed"] = normalized_testability
            normalized_user_stories: List[Dict[str, str]] = []
            raw_user_stories = normalized_feat.get("user_stories")
            if isinstance(raw_user_stories, list):
                for story in raw_user_stories:
                    normalized_story = _normalize_user_story_item(story)
                    if normalized_story:
                        normalized_user_stories.append(normalized_story)
            normalized_feat["user_stories"] = normalized_user_stories[:3]
            normalized_feat["acceptance_checks"] = _build_acceptance_checks(
                normalized_feat,
                normalized_feat.get("acceptance_criteria") or [],
            )
            return normalized_feat

        def _format_list_section(title: str, values: Any) -> str:
            normalized_values = [str(item).strip() for item in (values or []) if str(item).strip()]
            if not normalized_values:
                return f"# {title}\n\n- None\n"
            lines = "\n".join(f"- {item}" for item in normalized_values)
            return f"# {title}\n\n{lines}\n"

        def _format_acceptance_checks_section(checks: Any) -> str:
            if not isinstance(checks, list) or not checks:
                return "# Acceptance Checks\n\n- None\n"

            blocks: List[str] = []
            for index, item in enumerate(checks, start=1):
                if not isinstance(item, dict):
                    blocks.append(f"## AC-{index:03d}\n\n{item}\n")
                    continue
                trace_hints = item.get("trace_hints") or []
                trace_text = ", ".join(str(hint).strip() for hint in trace_hints if str(hint).strip()) or "None"
                block = (
                    f"## {item.get('id') or f'AC-{index:03d}'}\n\n"
                    f"- Scenario: {item.get('scenario', '')}\n"
                    f"- Given: {item.get('given', '')}\n"
                    f"- When: {item.get('when', '')}\n"
                    f"- Then: {item.get('then', '')}\n"
                    f"- Trace Hints: {trace_text}\n"
                )
                blocks.append(block)
            return "# Acceptance Checks\n\n" + "\n".join(blocks).rstrip() + "\n"

        def _build_feat_markdown(feat_item: Dict[str, Any]) -> str:
            sections = [
                f"# Goal\n\n{feat_item.get('goal', '').strip()}\n",
                f"# User Value\n\n{feat_item.get('user_value', '').strip()}\n",
                _format_list_section("Inputs", feat_item.get("inputs")),
                _format_list_section("Processing", feat_item.get("processing")),
                _format_list_section("Outputs", feat_item.get("outputs")),
                _format_list_section("Acceptance", feat_item.get("acceptance_criteria")),
                _format_acceptance_checks_section(feat_item.get("acceptance_checks")),
                _format_list_section("Dependencies", feat_item.get("dependencies")),
                _format_list_section("Non Goals", feat_item.get("non_goals")),
            ]
            return "\n".join(section.rstrip() for section in sections).strip() + "\n"

        def _build_contract_outputs(feat_specs: List[Dict[str, Any]], epic_ref: Optional[str]) -> List[Dict[str, Any]]:
            outputs: List[Dict[str, Any]] = []
            use_single_key = len(feat_specs) == 1
            for index, feat_item in enumerate(feat_specs, start=1):
                if not isinstance(feat_item, dict):
                    continue
                feat_id = str(feat_item.get("feat_id") or "").strip()
                feat_title = str(feat_item.get("title") or feat_id or f"FEAT {index}").strip()
                feat_ssot = feat_item.get("ssot") if isinstance(feat_item.get("ssot"), dict) else {}
                source_refs = LLMRunner._filter_materializable_refs(feat_item.get("source_refs"))
                parent_ref = feat_ssot.get("parent") or epic_ref
                if not LLMRunner._is_literal_ssot_ref(parent_ref):
                    parent_ref = None
                output_key = "feat" if use_single_key else f"feat_{index:03d}"
                output_item = {
                    "key": output_key,
                    "identity_kind": "ssot",
                    "ssot_type": "feat",
                    "title": feat_title,
                    "content": _build_feat_markdown(feat_item),
                    "properties": {
                        "formal_id": feat_id,
                        "feat_id": feat_id,
                        "epic_ref": epic_ref,
                    },
                }
                if parent_ref:
                    output_item["parent"] = parent_ref
                if source_refs:
                    output_item["source_refs"] = source_refs
                outputs.append(output_item)
            return outputs

        normalized_business = dict(business_output)
        bundle_specs = normalized_business.get("feat_specs")
        if isinstance(bundle_specs, list):
            structured_business = (
                structured_payload.get("business_output")
                if isinstance(structured_payload, dict)
                and isinstance(structured_payload.get("business_output"), dict)
                else {}
            )
            normalized_business = {
                "epic_ref": normalized_business.get("epic_ref"),
                "feat_specs": [normalize_feat_item(item) for item in bundle_specs],
            }
            if normalized_business["epic_ref"] is None and structured_business.get("epic_ref"):
                normalized_business["epic_ref"] = structured_business["epic_ref"]
        else:
            candidate_specs, candidate_epic_ref = _extract_breakdown_feature_candidates(
                normalized_business,
                actual_epic_ref or _clean_text(normalized_business.get("epic_ref")) or None,
            )
            if isinstance(candidate_specs, list) and candidate_specs:
                normalized_business = {
                    "epic_ref": candidate_epic_ref,
                    "feat_specs": [
                        normalize_feat_item(_synthesize_feat_spec(item, candidate_epic_ref))
                        for item in candidate_specs
                        if isinstance(item, dict)
                    ],
                }
                if not normalized_business["feat_specs"]:
                    normalized_business = normalize_feat_item(normalized_business)
            else:
                normalized_business = normalize_feat_item(normalized_business)
                if expects_bundle:
                    normalized_business = {
                        "epic_ref": actual_epic_ref or _clean_text(normalized_business.get("epic_ref")) or None,
                        "feat_specs": [normalized_business],
                    }

        if actual_epic_ref:
            normalized_business["epic_ref"] = actual_epic_ref
            if isinstance(normalized_business.get("feat_specs"), list):
                rewritten_specs = []
                for item in normalized_business["feat_specs"]:
                    if not isinstance(item, dict):
                        rewritten_specs.append(item)
                        continue
                    normalized_item = dict(item)
                    normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
                    ssot = normalized_item.get("ssot") if isinstance(normalized_item.get("ssot"), dict) else {}
                    normalized_item["ssot"] = {
                        **dict(ssot),
                        "identity_kind": "ssot",
                        "ssot_type": "FEAT",
                        "parent": actual_epic_ref,
                        "derived_from": actual_epic_ref,
                    }
                    rewritten_specs.append(normalized_item)
                normalized_business["feat_specs"] = rewritten_specs

        feat_specs = normalized_business.get("feat_specs") if isinstance(normalized_business.get("feat_specs"), list) else []
        if feat_specs:
            project_root: Optional[Path] = None
            if isinstance(instance_data, dict):
                params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
                epic_freeze = params.get("epic_freeze")
                epic_path = (
                    epic_freeze.get("path")
                    if isinstance(epic_freeze, dict)
                    else epic_freeze
                )
                if isinstance(epic_path, str) and epic_path.strip():
                    epic_candidate = Path(epic_path)
                    for parent in [epic_candidate, *epic_candidate.parents]:
                        if parent.name == ".workflow":
                            project_root = parent.parent
                            break

            def _is_canonical_feat_id(value: str) -> bool:
                return bool(re.fullmatch(r"FEAT-\d{3}", value))

            def _next_canonical_feat_ids(count: int) -> List[str]:
                if count <= 0:
                    return []
                highest = 0
                if project_root is not None:
                    features_dir = project_root / "spec" / "requirements" / "features"
                    if features_dir.exists():
                        for path in features_dir.glob("FEAT-*.md"):
                            match = re.match(r"FEAT-(\d{3})__", path.name)
                            if match:
                                highest = max(highest, int(match.group(1)))
                return [f"FEAT-{highest + index:03d}" for index in range(1, count + 1)]

            if project_root is not None:
                remap_candidates: List[tuple[str, str]] = []
                generated_ids = _next_canonical_feat_ids(len(feat_specs))
                for index, feat_item in enumerate(feat_specs):
                    if not isinstance(feat_item, dict):
                        continue
                    current_id = _clean_text(feat_item.get("feat_id"))
                    if current_id and _is_canonical_feat_id(current_id):
                        continue
                    target_id = generated_ids[index] if index < len(generated_ids) else ""
                    if current_id and target_id:
                        remap_candidates.append((current_id, target_id))

                feat_id_alias_map = {
                    source_id: target_id
                    for source_id, target_id in remap_candidates
                    if source_id != target_id
                }
                if feat_id_alias_map:
                    rewritten_specs = []
                    for feat_item in feat_specs:
                        if not isinstance(feat_item, dict):
                            rewritten_specs.append(feat_item)
                            continue
                        normalized_item = dict(feat_item)
                        current_id = _clean_text(normalized_item.get("feat_id"))
                        rewritten_id = feat_id_alias_map.get(current_id, current_id)
                        if rewritten_id:
                            normalized_item["feat_id"] = rewritten_id

                        dependencies = normalized_item.get("dependencies")
                        if isinstance(dependencies, list):
                            normalized_item["dependencies"] = [
                                feat_id_alias_map.get(_clean_text(dep), _clean_text(dep))
                                for dep in dependencies
                                if _clean_text(dep)
                            ]

                        source_refs = normalized_item.get("source_refs")
                        if isinstance(source_refs, list):
                            normalized_item["source_refs"] = [
                                (
                                    f"{feat_id_alias_map.get(ref.split('#', 1)[0], ref.split('#', 1)[0])}#{ref.split('#', 1)[1]}"
                                    if isinstance(ref, str)
                                    and "#" in ref
                                    and ref.split("#", 1)[0] in feat_id_alias_map
                                    else ref
                                )
                                for ref in source_refs
                            ]

                        input_contract = normalized_item.get("input_contract")
                        if isinstance(input_contract, dict):
                            required_artifacts = input_contract.get("required_artifacts")
                            if isinstance(required_artifacts, list):
                                normalized_item["input_contract"] = {
                                    **input_contract,
                                    "required_artifacts": [
                                        (
                                            f"{feat_id_alias_map.get(ref.split('#', 1)[0], ref.split('#', 1)[0])}#{ref.split('#', 1)[1]}"
                                            if isinstance(ref, str)
                                            and "#" in ref
                                            and ref.split("#", 1)[0] in feat_id_alias_map
                                            else ref
                                        )
                                        for ref in required_artifacts
                                    ],
                                }

                        acceptance_checks = normalized_item.get("acceptance_checks")
                        if isinstance(acceptance_checks, list):
                            rewritten_checks = []
                            for item in acceptance_checks:
                                if not isinstance(item, dict):
                                    rewritten_checks.append(item)
                                    continue
                                trace_hints = item.get("trace_hints")
                                rewritten_checks.append(
                                    {
                                        **item,
                                        "trace_hints": [
                                            feat_id_alias_map.get(_clean_text(hint), _clean_text(hint))
                                            for hint in trace_hints
                                            if _clean_text(hint)
                                        ] if isinstance(trace_hints, list) else trace_hints,
                                    }
                                )
                            normalized_item["acceptance_checks"] = rewritten_checks

                        rewritten_specs.append(normalized_item)
                    normalized_business["feat_specs"] = rewritten_specs

        normalized_structured = LLMRunner._ensure_structured_envelope(
            business_output=normalized_business,
            structured_payload=structured_payload,
        )

        ssot_contract = normalized_structured.get("ssot_output_contract")
        if isinstance(ssot_contract, dict):
            normalized_contract = dict(ssot_contract)
        else:
            normalized_contract = {}
        normalized_contract.setdefault("contract_version", "1.0")
        normalized_contract.setdefault("run_id", workflow_id)

        outputs = normalized_contract.get("outputs")
        if isinstance(normalized_business.get("feat_specs"), list):
            normalized_contract["outputs"] = _build_contract_outputs(
                normalized_business.get("feat_specs") or [],
                normalized_business.get("epic_ref"),
            )
        elif not isinstance(outputs, list) or not outputs:
            normalized_contract["outputs"] = _build_contract_outputs(
                normalized_business.get("feat_specs") or [],
                normalized_business.get("epic_ref"),
            )
        elif isinstance(outputs, list):
            normalized_outputs = []
            for item in outputs:
                if not isinstance(item, dict):
                    normalized_outputs.append(item)
                    continue
                normalized_item = dict(item)
                normalized_item.setdefault("identity_kind", "ssot")
                if normalized_item.get("key") == "feat":
                    normalized_item.setdefault("ssot_type", "feat")
                    if normalized_business.get("title"):
                        normalized_item.setdefault("title", normalized_business["title"])
                    parent = normalized_business.get("ssot", {}).get("parent")
                    if LLMRunner._is_literal_ssot_ref(parent):
                        normalized_item.setdefault("parent", parent)
                    source_refs = LLMRunner._filter_materializable_refs(normalized_business.get("source_refs"))
                    if source_refs:
                        normalized_item.setdefault("source_refs", source_refs)
                if actual_epic_ref and LLMRunner._is_literal_ssot_ref(actual_epic_ref):
                    normalized_item["parent"] = actual_epic_ref
                    normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
                else:
                    parent_ref = normalized_item.get("parent")
                    if not LLMRunner._is_literal_ssot_ref(parent_ref):
                        normalized_item.pop("parent", None)
                    filtered_refs = LLMRunner._filter_materializable_refs(normalized_item.get("source_refs"))
                    if filtered_refs:
                        normalized_item["source_refs"] = filtered_refs
                    else:
                        normalized_item.pop("source_refs", None)
                properties = normalized_item.get("properties") if isinstance(normalized_item.get("properties"), dict) else {}
                normalized_item["properties"] = {
                    **properties,
                    "epic_ref": actual_epic_ref or normalized_business.get("epic_ref"),
                }
                normalized_outputs.append(normalized_item)
            normalized_contract["outputs"] = normalized_outputs
        normalized_structured["ssot_output_contract"] = normalized_contract

        return normalized_business, normalized_structured

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
        if getattr(step, "agent_id", "") != "agent.product.pm_planner":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        def _clean_text(value: Any) -> str:
            return str(value or "").strip()

        def _normalize_list(values: Any) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            return [_clean_text(item) for item in items if _clean_text(item)]

        def _normalize_priority(value: Any) -> str:
            normalized = _clean_text(value).upper()
            if normalized in {"P0", "P1", "P2"}:
                return normalized
            lowered = _clean_text(value).lower()
            if lowered in {"critical", "high"}:
                return "P0"
            if lowered in {"medium", "normal"}:
                return "P1"
            if lowered in {"low", "minor"}:
                return "P2"
            return "P1"

        def _normalize_role(value: Any) -> str:
            normalized = _clean_text(value).lower().replace("_", "-").replace(" ", "-")
            return normalized or "workflow-runtime-owner"

        def _normalize_workstream(task: Dict[str, Any], role: str) -> str:
            explicit = _clean_text(task.get("workstream"))
            if explicit:
                return explicit
            combined = " ".join(
                [
                    _clean_text(task.get("task_id")).lower(),
                    _clean_text(task.get("title")).lower(),
                    _clean_text(task.get("description")).lower(),
                ]
            )
            if any(token in combined for token in ("migration", "registry", "compatibility", "文档", "迁移")):
                return "governance-spec"
            if role.startswith("qa"):
                return "qa-seed"
            if role.startswith("technical-writer"):
                return "governance-docs"
            return "workflow-runtime"

        def _infer_task_kind(task: Dict[str, Any], role: str, workstream: str) -> str:
            combined = " ".join(
                [
                    _clean_text(task.get("title")).lower(),
                    _clean_text(task.get("description")).lower(),
                    role.lower(),
                    workstream.lower(),
                ]
            )
            if any(token in combined for token in ("migration", "迁移")):
                return "migration"
            if any(token in combined for token in ("governance", "registry", "compatibility", "文档")):
                return "governance"
            if role.startswith("qa") or "test" in combined or "验证" in combined:
                return "validation"
            if any(token in combined for token in ("ux", "design", "ui")):
                return "ux"
            if "refactor" in combined:
                return "refactor"
            return "implementation"

        def _title_key(value: Any) -> str:
            lowered = _clean_text(value).lower()
            return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", lowered)

        def _derive_project_root_from_feat_freeze(feat_freeze_path: str) -> Optional[Path]:
            candidate = Path(feat_freeze_path)
            for parent in [candidate, *candidate.parents]:
                if parent.name == ".workflow":
                    return parent.parent
            return None

        def _extract_canonical_title_map(project_root: Optional[Path]) -> Dict[str, str]:
            if project_root is None:
                return {}
            features_dir = project_root / "spec" / "requirements" / "features"
            if not features_dir.exists():
                return {}
            title_map: Dict[str, str] = {}
            for path in sorted(features_dir.glob("*.md")):
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if not text.startswith("---"):
                    continue
                try:
                    _, frontmatter, _ = text.split("---", 2)
                    metadata = yaml.safe_load(frontmatter) or {}
                except Exception:
                    continue
                if not isinstance(metadata, dict):
                    continue
                title = _clean_text(metadata.get("title"))
                canonical_id = _clean_text(metadata.get("id"))
                if title and canonical_id:
                    title_map[_title_key(title)] = canonical_id
            return title_map

        def _extract_source_feat_title_map(feat_freeze_path: str) -> Dict[str, str]:
            freeze_path = Path(feat_freeze_path)
            if not freeze_path.exists():
                return {}
            try:
                payload = yaml.safe_load(freeze_path.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
            title_map: Dict[str, str] = {}
            candidates = payload.get("feat_specifications")
            if not isinstance(candidates, list):
                candidates = payload.get("feat_specs")
            if not isinstance(candidates, list):
                return {}
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                feat_id = _clean_text(item.get("feat_id"))
                title = _clean_text(item.get("title"))
                if feat_id and title:
                    title_map[feat_id] = title
            return title_map

        def _build_feat_alias_map(instance_payload: Optional[Dict[str, Any]]) -> Dict[str, str]:
            if not isinstance(instance_payload, dict):
                return {}
            params = instance_payload.get("params") if isinstance(instance_payload.get("params"), dict) else {}
            feat_freeze_path = params.get("feat_freeze")
            if not isinstance(feat_freeze_path, str) or not feat_freeze_path.strip():
                return {}
            source_title_map = _extract_source_feat_title_map(feat_freeze_path)
            if not source_title_map:
                return {}
            canonical_title_map = _extract_canonical_title_map(
                _derive_project_root_from_feat_freeze(feat_freeze_path)
            )
            if not canonical_title_map:
                return {}
            alias_map: Dict[str, str] = {}
            for source_feat_id, title in source_title_map.items():
                canonical_id = canonical_title_map.get(_title_key(title))
                if canonical_id:
                    alias_map[source_feat_id] = canonical_id
            return alias_map

        feat_alias_map = _build_feat_alias_map(instance_data)

        def _resolve_parent_epic(epic_candidate: str, feat_ids: List[str]) -> str:
            for feat_id in feat_ids:
                resolved = LLMRunner._resolve_feat_parent_epic(feat_id, instance_data)
                if resolved:
                    return resolved
            return epic_candidate or "EPIC-001"

        project_root = None
        if isinstance(instance_data, dict):
            params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
            feat_ref_path = params.get("feat_freeze_ref")
            if isinstance(feat_ref_path, str) and feat_ref_path.strip():
                candidate_path = Path(feat_ref_path.strip())
                if candidate_path.exists():
                    for parent in [candidate_path.parent, *candidate_path.parents]:
                        if parent.name == "spec":
                            project_root = parent.parent
                            break
            if project_root is None:
                feat_freeze = params.get("feat_freeze")
                if isinstance(feat_freeze, str) and feat_freeze.strip():
                    project_root = _derive_project_root_from_feat_freeze(feat_freeze.strip())

        def _load_formal_acceptance_checks_for_feat(feat_id: str) -> List[Dict[str, Any]]:
            if not isinstance(project_root, Path):
                return []
            return LLMRunner._load_feat_acceptance_checks(str(project_root), feat_id)

        def _load_formal_feat_title(feat_id: str) -> str:
            if not isinstance(project_root, Path):
                return ""
            features_dir = project_root / "spec" / "requirements" / "features"
            if not features_dir.exists():
                return ""
            for candidate in sorted(features_dir.glob(f"{feat_id}__*.md")):
                frontmatter = LLMRunner._load_yaml_frontmatter(candidate) or {}
                title = _clean_text(frontmatter.get("title"))
                if title:
                    return title
            return ""

        def _requires_structural_governance_task(structural_checks: List[Dict[str, Any]]) -> bool:
            strong_markers = (
                "rule-",
                "状态机",
                "链路",
                "路径",
                "旁路",
                "入口",
                "bypass",
                "stage order",
                "phase order",
                "schema",
                "template",
                "错误码",
                "优先级",
                "priority",
                "来源",
                "source",
                "cli_override",
            )
            for check in structural_checks:
                if not isinstance(check, dict):
                    continue
                text = " ".join(
                    _clean_text(check.get(key))
                    for key in ("scenario", "given", "when", "then", "raw_text")
                )
                if any(LLMRunner._text_contains_keyword(text, marker) for marker in strong_markers):
                    return True
            return False

        def _classify_structural_governance_theme(
            feat_title: str,
            structural_checks: List[Dict[str, Any]],
        ) -> Dict[str, Any]:
            combined_text = " ".join(
                _clean_text(item.get(key))
                for item in structural_checks
                if isinstance(item, dict)
                for key in ("scenario", "given", "when", "then", "raw_text")
            )
            combined_text = f"{feat_title} {combined_text}".strip()

            if any(
                LLMRunner._text_contains_keyword(combined_text, marker)
                for marker in (
                    "优先级",
                    "priority",
                    "来源",
                    "source",
                    "executor",
                    "执行器",
                    "cli_override",
                    "config_file",
                    "default",
                )
            ):
                return {
                    "title": "执行器配置优先级与验证规则规范",
                    "objective": "冻结执行器类型选择、优先级判定、来源追踪与错误处理边界，作为实现任务的前置规范基线",
                    "description": "在正式实现前冻结执行器配置规范，覆盖执行器类型白名单、CLI/环境变量/配置文件/默认值的优先级规则、来源追踪字段和错误信息模板，避免结构性规则散落在实现代码中。",
                    "responsible_role": "executor-config-governance-owner",
                    "milestone_name": "配置规范冻结",
                    "milestone_acceptance": "执行器类型、优先级规则和错误处理边界已冻结",
                }

            if any(
                LLMRunner._text_contains_keyword(combined_text, marker)
                for marker in ("入口", "链路", "路径", "旁路", "bypass", "状态机")
            ):
                return {
                    "title": "执行入口链路规则与状态机规范",
                    "objective": "冻结执行入口链路规则、状态机边界和错误处理约束，作为实现任务的前置规范基线",
                    "description": "在正式实现前冻结执行入口规范，覆盖路径校验边界、状态转换约束、旁路阻断规则和错误码映射，避免结构性规则直接埋入实现代码。",
                    "responsible_role": "workflow-governance-owner",
                    "milestone_name": "规则规范冻结",
                    "milestone_acceptance": "执行链路规则、状态机和错误码边界已冻结",
                }

            return {
                "title": f"{feat_title or '结构性规则'}规范冻结任务",
                "objective": "冻结结构性规则、约束边界和模板契约，作为实现任务的前置规范基线",
                "description": "在正式实现前冻结结构性规则，覆盖关键约束、契约边界、模板要求和错误处理基线，避免规范含义在实现过程中漂移。",
                "responsible_role": "governance-owner",
                "milestone_name": "规范冻结",
                "milestone_acceptance": "结构性规则和契约边界已冻结",
            }

        def _remap_acceptance_mapping(
            mappings: Any,
            *,
            feat_id: str,
            formal_checks: List[Dict[str, Any]],
        ) -> List[Dict[str, Any]]:
            if not isinstance(mappings, list):
                return []
            formal_ids = [str(item.get("id")).strip() for item in formal_checks if isinstance(item, dict) and str(item.get("id") or "").strip()]
            used_ids: set[str] = set()
            normalized: List[Dict[str, Any]] = []
            for index, item in enumerate(mappings, start=1):
                if not isinstance(item, dict):
                    continue
                raw_ac = _clean_text(item.get("ac"))
                selected_ac = raw_ac if raw_ac in formal_ids else ""
                if not selected_ac and raw_ac:
                    suffix_match = re.search(r"(\d{3})$", raw_ac)
                    if suffix_match:
                        for candidate in formal_ids:
                            if candidate.endswith(suffix_match.group(1)):
                                selected_ac = candidate
                                break
                if not selected_ac:
                    candidate_index = min(index - 1, len(formal_ids) - 1)
                    if candidate_index >= 0 and formal_ids:
                        selected_ac = formal_ids[candidate_index]
                if not selected_ac:
                    selected_ac = raw_ac or f"AC-{index:03d}"
                used_ids.add(selected_ac)
                normalized.append(
                    {
                        "feat": feat_id,
                        "ac": selected_ac,
                        "description": _clean_text(item.get("description")) or _clean_text(item.get("ac")) or selected_ac,
                    }
                )
            return normalized

        def _task_is_structural(task_spec: Dict[str, Any]) -> bool:
            workstream = _clean_text(task_spec.get("workstream")).lower()
            task_kind = _clean_text(task_spec.get("task_kind")).lower()
            if workstream in {"governance-spec", "governance-docs"}:
                return True
            if task_kind in {"governance", "specification", "template"}:
                return True
            if task_kind == "implementation":
                return False

            combined = " ".join(
                [
                    _clean_text(task_spec.get("title")),
                    _clean_text(task_spec.get("objective")),
                    _clean_text(task_spec.get("description")),
                ]
            )
            structural_keywords = (
                "governance",
                "specification",
                "template",
                "schema",
                "contract",
                "错误码映射",
                "状态机",
                "规则定义",
                "规则集",
                "规范文档",
                "规范冻结",
            )
            return any(LLMRunner._text_contains_keyword(combined, keyword) for keyword in structural_keywords)

        def _ensure_structural_governance_task(normalized_business: Dict[str, Any]) -> None:
            task_specs = normalized_business.get("task_specs")
            source_feats = normalized_business.get("source_feats")
            if not isinstance(task_specs, list) or not task_specs or not isinstance(source_feats, list) or not source_feats:
                return

            primary_feat = _clean_text(source_feats[0]) or "FEAT-001"
            feat_title = _load_formal_feat_title(primary_feat)
            formal_checks = _load_formal_acceptance_checks_for_feat(primary_feat)
            structural_checks = [
                check for check in formal_checks if LLMRunner._is_structural_acceptance_check(check)
            ]
            if not structural_checks:
                return
            if not _requires_structural_governance_task(structural_checks):
                return
            if any(_task_is_structural(task_spec) for task_spec in task_specs if isinstance(task_spec, dict)):
                return

            structural_task_id = f"TASK-{primary_feat}-000"
            mapped_checks = [
                {
                    "feat": primary_feat,
                    "ac": str(check.get("id")).strip(),
                    "description": _clean_text(check.get("then") or check.get("scenario") or check.get("raw_text")),
                }
                for check in structural_checks
                if isinstance(check, dict) and str(check.get("id") or "").strip()
            ]
            if not mapped_checks:
                return

            governance_theme = _classify_structural_governance_theme(feat_title, structural_checks)
            governance_task = {
                "task_id": structural_task_id,
                "title": governance_theme["title"],
                "objective": governance_theme["objective"],
                "description": governance_theme["description"],
                "source_feat": primary_feat,
                "workstream": "governance-spec",
                "task_kind": "governance",
                "responsible_role": governance_theme["responsible_role"],
                "acceptance_criteria_mapping": mapped_checks,
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": [
                    "结构性规则和契约边界文档已冻结",
                    "规范任务已覆盖相关结构性 Acceptance Checks",
                    "实现任务已明确引用该规范任务作为前置依赖",
                ],
                "priority": "P0",
                "milestone": "M0-Governance-Baseline",
                "estimated_effort": "2 days",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id", "changed_files", "evidence_refs", "review_refs"],
                },
                "evidence_requirements": {
                    "required_refs": [primary_feat],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["spec/tasks", "spec/contracts", "spec-global/departments/product/workflows"],
                },
                "source_refs": [f"{primary_feat}#delivery"] if LLMRunner._is_literal_ssot_ref(primary_feat) else [],
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": primary_feat,
                    "derived_from": f"{primary_feat}#delivery",
                },
            }
            task_specs.insert(0, governance_task)

            for task_spec in task_specs[1:]:
                if not isinstance(task_spec, dict):
                    continue
                dependencies = _normalize_list(task_spec.get("dependencies"))
                if structural_task_id not in dependencies:
                    dependencies.insert(0, structural_task_id)
                task_spec["dependencies"] = dependencies

                prerequisites = _normalize_list(task_spec.get("prerequisites"))
                if governance_task["title"] not in prerequisites:
                    prerequisites.insert(0, governance_task["title"])
                task_spec["prerequisites"] = prerequisites

            milestones = normalized_business.get("milestones")
            if isinstance(milestones, list):
                milestones.insert(
                    0,
                    {
                        "id": "M0-Governance-Baseline",
                        "name": governance_theme["milestone_name"],
                        "task_ids": [structural_task_id],
                        "acceptance_criteria": governance_theme["milestone_acceptance"],
                    },
                )

            dependency_graph = normalized_business.get("dependency_graph")
            if isinstance(dependency_graph, dict):
                critical_path = dependency_graph.get("critical_path")
                if isinstance(critical_path, list) and structural_task_id not in critical_path:
                    critical_path.insert(0, structural_task_id)

            resource_allocation = normalized_business.get("resource_allocation")
            if isinstance(resource_allocation, dict):
                resource_allocation.setdefault(
                    governance_theme["responsible_role"],
                    {"tasks": []},
                )
                if structural_task_id not in resource_allocation[governance_theme["responsible_role"]]["tasks"]:
                    resource_allocation[governance_theme["responsible_role"]]["tasks"].insert(0, structural_task_id)

        def _format_string_list_section(heading: str, values: Any) -> List[str]:
            if not isinstance(values, list) or not values:
                return []
            lines = [f"## {heading}"]
            for item in values:
                lines.append(f"- {_clean_text(item)}")
            lines.append("")
            return lines

        def _format_dict_section(heading: str, value: Any) -> List[str]:
            if not isinstance(value, dict) or not value:
                return []
            yaml_text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False).strip()
            if not yaml_text:
                return []
            return [f"## {heading}", "```yaml", yaml_text, "```", ""]

        def _build_task_markdown(task_spec: Dict[str, Any]) -> str:
            lines = [
                f"# Objective\n\n{_clean_text(task_spec.get('objective'))}\n",
                f"# Description\n\n{_clean_text(task_spec.get('description'))}\n",
            ]
            mapping = task_spec.get("acceptance_criteria_mapping")
            if isinstance(mapping, list) and mapping:
                lines.append("## Acceptance Mapping")
                for item in mapping:
                    if not isinstance(item, dict):
                        continue
                    lines.append(
                        f"- {item.get('feat', '')} / {item.get('ac', '')}: {item.get('description', '')}"
                    )
                lines.append("")
            lines.extend(_format_string_list_section("Prerequisites", task_spec.get("prerequisites")))
            lines.extend(_format_string_list_section("Dependencies", task_spec.get("dependencies")))
            lines.extend(_format_dict_section("Observability", task_spec.get("observability")))
            lines.extend(_format_dict_section("Evidence Requirements", task_spec.get("evidence_requirements")))
            lines.extend(_format_dict_section("Rollback Strategy", task_spec.get("rollback_strategy")))
            lines.extend(_format_string_list_section("Definition Of Done", task_spec.get("definition_of_done")))
            return "\n".join(lines).strip() + "\n"

        payload = business_output.get("task_planning") if isinstance(business_output.get("task_planning"), dict) else business_output
        if not isinstance(payload, dict):
            return business_output, structured_payload

        if isinstance(payload.get("task_specs"), list) and payload.get("task_specs"):
            normalized_business = dict(payload)
            normalized_business["source_feats"] = [
                feat_alias_map.get(_clean_text(item), _clean_text(item))
                for item in (payload.get("source_feats") or [])
                if _clean_text(item)
            ]
            remapped_task_specs: List[Dict[str, Any]] = []
            for task_spec in payload.get("task_specs") or []:
                if not isinstance(task_spec, dict):
                    continue
                remapped_task = dict(task_spec)
                raw_source_feat = _clean_text(task_spec.get("source_feat"))
                canonical_source_feat = feat_alias_map.get(raw_source_feat, raw_source_feat) or "FEAT-001"
                formal_checks = _load_formal_acceptance_checks_for_feat(canonical_source_feat)
                remapped_task["source_feat"] = canonical_source_feat
                if isinstance(task_spec.get("source_refs"), list):
                    remapped_task["source_refs"] = [
                        f"{canonical_source_feat}#delivery"
                        if isinstance(ref, str) and ref == f"{raw_source_feat}#delivery" and canonical_source_feat
                        else ref
                        for ref in task_spec.get("source_refs") or []
                    ]
                if isinstance(task_spec.get("ssot"), dict):
                    remapped_ssot = dict(task_spec.get("ssot") or {})
                    remapped_ssot["parent"] = canonical_source_feat
                    derived_from = _clean_text(remapped_ssot.get("derived_from"))
                    if raw_source_feat and derived_from == f"{raw_source_feat}#delivery":
                        remapped_ssot["derived_from"] = f"{canonical_source_feat}#delivery"
                    remapped_task["ssot"] = remapped_ssot
                if isinstance(task_spec.get("acceptance_criteria_mapping"), list):
                    remapped_task["acceptance_criteria_mapping"] = _remap_acceptance_mapping(
                        task_spec.get("acceptance_criteria_mapping") or [],
                        feat_id=canonical_source_feat,
                        formal_checks=formal_checks,
                    )
                remapped_task_specs.append(remapped_task)
            normalized_business["task_specs"] = remapped_task_specs
        else:
            epic_ref = _clean_text(payload.get("parent_epic") or payload.get("epic_ref"))
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            if not epic_ref:
                epic_ref = _clean_text(metadata.get("epic_id"))
            feat_tasks = payload.get("feat_tasks") if isinstance(payload.get("feat_tasks"), list) else []
            plan_tasks = payload.get("tasks") if isinstance(payload.get("tasks"), list) else []
            source_feats = [
                feat_alias_map.get(_clean_text(item.get("feat_id")), _clean_text(item.get("feat_id")))
                for item in feat_tasks
                if isinstance(item, dict) and _clean_text(item.get("feat_id"))
            ]

            task_specs: List[Dict[str, Any]] = []
            milestones_map: Dict[str, Dict[str, Any]] = {}
            resource_allocation: Dict[str, Dict[str, Any]] = {}
            critical_path: List[str] = []
            risk_mitigation: List[Dict[str, Any]] = []

            for feat_entry in feat_tasks:
                if not isinstance(feat_entry, dict):
                    continue
                feat_id = feat_alias_map.get(
                    _clean_text(feat_entry.get("feat_id")),
                    _clean_text(feat_entry.get("feat_id")),
                )
                phases = (
                    feat_entry.get("implementation_plan", {}).get("phases")
                    if isinstance(feat_entry.get("implementation_plan"), dict)
                    else []
                )
                for phase in phases if isinstance(phases, list) else []:
                    if not isinstance(phase, dict):
                        continue
                    milestone_id = _clean_text(phase.get("phase_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(phase.get("name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{feat_id} {milestone_name}".strip(),
                        },
                    )
                    tasks = phase.get("tasks") if isinstance(phase.get("tasks"), list) else []
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        task_id = _clean_text(task.get("task_id")) or f"{feat_id}-TASK-{len(task_specs) + 1:03d}"
                        title = _clean_text(task.get("title")) or task_id
                        description = _clean_text(task.get("description")) or title
                        role = _normalize_role(task.get("assignee_role") or task.get("responsible_role"))
                        workstream = _normalize_workstream(task, role)
                        acceptance_items = _normalize_list(task.get("acceptance_criteria"))
                        if not acceptance_items:
                            acceptance_items = [description]
                        task_specs.append(
                            {
                                "task_id": task_id,
                                "title": title,
                                "objective": acceptance_items[0],
                                "description": description,
                                "source_feat": feat_id or "FEAT-001",
                                "workstream": workstream,
                                "task_kind": _infer_task_kind(task, role, workstream),
                                "responsible_role": role,
                                "acceptance_criteria_mapping": [
                                    {
                                        "feat": feat_id or "FEAT-001",
                                        "ac": f"{feat_id or 'FEAT-001'}-AC-{index:03d}",
                                        "description": item,
                                    }
                                    for index, item in enumerate(acceptance_items, start=1)
                                ],
                                "prerequisites": _normalize_list(task.get("prerequisites")),
                                "dependencies": _normalize_list(task.get("dependencies")),
                                "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
                                "priority": _normalize_priority(feat_entry.get("priority") or task.get("priority")),
                                "milestone": milestone_id,
                                "estimated_effort": _clean_text(task.get("effort") or task.get("estimated_effort") or "1 day"),
                                "lifecycle_status": "draft",
                                "observability": {
                                    "execution_unit": "task",
                                    "log_scope": "task-execution",
                                    "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
                                },
                                "evidence_requirements": {
                                    "required_refs": [feat_id] if feat_id else ["delivery-plan"],
                                    "review_required": True,
                                },
                                "rollback_strategy": {
                                    "mode": "revert",
                                    "restore_targets": [workstream],
                                },
                                "source_refs": [f"{feat_id}#delivery"] if feat_id and LLMRunner._is_literal_ssot_ref(feat_id) else [],
                                "ssot": {
                                    "identity_kind": "ssot",
                                    "ssot_type": "TASK",
                                    "parent": feat_id or "FEAT-001",
                                    "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan",
                                },
                            }
                        )
                        milestone["task_ids"].append(task_id)
                        critical_path.append(task_id)
                        resource_allocation.setdefault(role, {"tasks": []})
                        resource_allocation[role]["tasks"].append(task_id)

            if not task_specs and plan_tasks:
                seen_source_feats: set[str] = set(source_feats)
                group_lookup: Dict[str, Dict[str, str]] = {}
                overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
                groups = overview.get("groups") if isinstance(overview.get("groups"), list) else []
                for group in groups:
                    if not isinstance(group, dict):
                        continue
                    milestone_id = _clean_text(group.get("group_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(group.get("name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{milestone_name} completed",
                        },
                    )
                    for task_ref in group.get("tasks") if isinstance(group.get("tasks"), list) else []:
                        task_key = _clean_text(task_ref)
                        if task_key:
                            group_lookup[task_key] = {
                                "milestone_id": milestone_id,
                                "milestone_name": milestone.get("name", milestone_id),
                            }

                for task in plan_tasks:
                    if not isinstance(task, dict):
                        continue
                    raw_feat_id = _clean_text(
                        task.get("feat_ref") or task.get("source_feat") or task.get("related_feat") or task.get("feat_id")
                    )
                    feat_id = feat_alias_map.get(raw_feat_id, raw_feat_id)
                    if feat_id and feat_id not in seen_source_feats:
                        source_feats.append(feat_id)
                        seen_source_feats.add(feat_id)

                    task_id = _clean_text(task.get("task_id")) or f"{feat_id or 'FEAT-001'}-TASK-{len(task_specs) + 1:03d}"
                    title = _clean_text(task.get("title")) or task_id
                    description = _clean_text(task.get("description")) or title
                    role = _normalize_role(task.get("assignee_role") or task.get("responsible_role"))
                    workstream = _normalize_workstream(task, role)
                    acceptance_items = _normalize_list(task.get("acceptance_criteria"))
                    if not acceptance_items:
                        acceptance_items = [description]
                    dependencies = task.get("dependencies") if isinstance(task.get("dependencies"), dict) else {}
                    prerequisite_ids = _normalize_list(dependencies.get("upstream"))
                    group_info = group_lookup.get(task_id, {})
                    milestone_id = _clean_text(group_info.get("milestone_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(group_info.get("milestone_name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{milestone_name} completed",
                        },
                    )
                    estimated_effort = _clean_text(task.get("estimated_effort") or task.get("effort"))
                    if not estimated_effort and task.get("story_points") is not None:
                        estimated_effort = f"{_clean_text(task.get('story_points'))} points"
                    task_specs.append(
                        {
                            "task_id": task_id,
                            "title": title,
                            "objective": acceptance_items[0],
                            "description": description,
                            "source_feat": feat_id or "FEAT-001",
                            "workstream": workstream,
                            "task_kind": _infer_task_kind(task, role, workstream),
                            "responsible_role": role,
                            "acceptance_criteria_mapping": [
                                {
                                    "feat": feat_id or "FEAT-001",
                                    "ac": f"{feat_id or 'FEAT-001'}-AC-{index:03d}",
                                    "description": item,
                                }
                                for index, item in enumerate(acceptance_items, start=1)
                            ],
                            "prerequisites": prerequisite_ids,
                            "dependencies": prerequisite_ids,
                            "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
                            "priority": _normalize_priority(task.get("priority")),
                            "milestone": milestone_id,
                            "estimated_effort": estimated_effort or "1 day",
                            "lifecycle_status": "draft",
                            "observability": {
                                "execution_unit": "task",
                                "log_scope": "task-execution",
                                "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
                            },
                            "evidence_requirements": {
                                "required_refs": [feat_id] if feat_id else ["delivery-plan"],
                                "review_required": True,
                            },
                            "rollback_strategy": {
                                "mode": "revert",
                                "restore_targets": [workstream],
                            },
                            "source_refs": [f"{feat_id}#delivery"] if feat_id and LLMRunner._is_literal_ssot_ref(feat_id) else [],
                            "ssot": {
                                "identity_kind": "ssot",
                                "ssot_type": "TASK",
                                "parent": feat_id or "FEAT-001",
                                "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan",
                            },
                        }
                    )
                    milestone["task_ids"].append(task_id)
                    critical_path.append(task_id)
                    resource_allocation.setdefault(role, {"tasks": []})
                    resource_allocation[role]["tasks"].append(task_id)

            if not task_specs:
                task_hierarchy = payload.get("task_hierarchy") if isinstance(payload.get("task_hierarchy"), list) else []
                seen_source_feats: set[str] = set(source_feats)
                for phase in task_hierarchy:
                    if not isinstance(phase, dict):
                        continue
                    milestone_id = _clean_text(phase.get("phase_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(phase.get("phase")) or _clean_text(phase.get("name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{milestone_name} completed",
                        },
                    )
                    tasks = phase.get("tasks") if isinstance(phase.get("tasks"), list) else []
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        raw_feat_id = _clean_text(
                            task.get("related_feat") or task.get("source_feat") or task.get("feat_id")
                        )
                        feat_id = feat_alias_map.get(raw_feat_id, raw_feat_id)
                        if feat_id and feat_id not in seen_source_feats:
                            source_feats.append(feat_id)
                            seen_source_feats.add(feat_id)
                        task_id = _clean_text(task.get("task_id")) or f"{feat_id or 'FEAT-001'}-TASK-{len(task_specs) + 1:03d}"
                        title = _clean_text(task.get("title")) or task_id
                        description = _clean_text(task.get("description")) or title
                        role = _normalize_role(task.get("assignee_role") or task.get("responsible_role"))
                        workstream = _normalize_workstream(task, role)
                        acceptance_items = _normalize_list(task.get("acceptance_criteria"))
                        if not acceptance_items:
                            acceptance_items = [description]
                        estimated_effort = _clean_text(task.get("estimated_effort") or task.get("effort"))
                        if not estimated_effort and task.get("story_points") is not None:
                            estimated_effort = f"{_clean_text(task.get('story_points'))} points"
                        task_specs.append(
                            {
                                "task_id": task_id,
                                "title": title,
                                "objective": acceptance_items[0],
                                "description": description,
                                "source_feat": feat_id or "FEAT-001",
                                "workstream": workstream,
                                "task_kind": _infer_task_kind(task, role, workstream),
                                "responsible_role": role,
                                "acceptance_criteria_mapping": [
                                    {
                                        "feat": feat_id or "FEAT-001",
                                        "ac": f"{feat_id or 'FEAT-001'}-AC-{index:03d}",
                                        "description": item,
                                    }
                                    for index, item in enumerate(acceptance_items, start=1)
                                ],
                                "prerequisites": _normalize_list(task.get("prerequisites")),
                                "dependencies": _normalize_list(task.get("dependencies")),
                                "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
                                "priority": _normalize_priority(task.get("priority")),
                                "milestone": milestone_id,
                                "estimated_effort": estimated_effort or "1 day",
                                "lifecycle_status": "draft",
                                "observability": {
                                    "execution_unit": "task",
                                    "log_scope": "task-execution",
                                    "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
                                },
                                "evidence_requirements": {
                                    "required_refs": [feat_id] if feat_id else ["delivery-plan"],
                                    "review_required": True,
                                },
                                "rollback_strategy": {
                                    "mode": "revert",
                                    "restore_targets": [workstream],
                                },
                                "source_refs": [f"{feat_id}#delivery"] if feat_id and LLMRunner._is_literal_ssot_ref(feat_id) else [],
                                "ssot": {
                                    "identity_kind": "ssot",
                                    "ssot_type": "TASK",
                                    "parent": feat_id or "FEAT-001",
                                    "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan",
                                },
                            }
                        )
                        milestone["task_ids"].append(task_id)
                        critical_path.append(task_id)
                        resource_allocation.setdefault(role, {"tasks": []})
                        resource_allocation[role]["tasks"].append(task_id)

            raw_risks = payload.get("risks") if isinstance(payload.get("risks"), list) else []
            for risk in raw_risks:
                if not isinstance(risk, dict):
                    continue
                affected_tasks = _normalize_list(risk.get("affected_tasks")) or critical_path[:2]
                if not affected_tasks and task_specs:
                    affected_tasks = [str(task_specs[0].get("task_id"))]
                risk_mitigation.append(
                    {
                        "risk": _clean_text(risk.get("description") or risk.get("title") or risk.get("risk_id") or "planning-risk"),
                        "mitigation": _clean_text(risk.get("mitigation") or risk.get("fallback") or "Track in delivery review"),
                        "affected_tasks": affected_tasks,
                    }
                )

            normalized_business = {
                "parent_epic": epic_ref or "EPIC-001",
                "source_feats": source_feats or ["FEAT-001"],
                "planning_metadata": {
                    "planning_timestamp": _clean_text(payload.get("created_at")) or datetime.now().strftime("%Y-%m-%d"),
                    "project_profile": "legacy_task_planning_view",
                    "task_directory": f"spec/tasks/{(source_feats or ['FEAT-001'])[0]}",
                },
                "task_specs": task_specs,
                "milestones": list(milestones_map.values()) or [
                    {
                        "id": "M1",
                        "name": "Initial Delivery Plan",
                        "task_ids": [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict)],
                        "acceptance_criteria": "Delivery plan created",
                    }
                ],
                "dependency_graph": {
                    "critical_path": critical_path or [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict)],
                },
                "resource_allocation": resource_allocation or {"workflow-runtime-owner": {"tasks": []}},
                "risk_mitigation": risk_mitigation,
            }

        source_feat_ids = normalized_business.get("source_feats") if isinstance(normalized_business.get("source_feats"), list) else []
        if not source_feat_ids and isinstance(normalized_business.get("task_specs"), list):
            source_feat_ids = [
                _clean_text(item.get("source_feat"))
                for item in normalized_business.get("task_specs") or []
                if isinstance(item, dict) and _clean_text(item.get("source_feat"))
            ]
        normalized_business["source_feats"] = [feat_alias_map.get(item, item) for item in source_feat_ids if item]
        source_feat_ids = normalized_business.get("source_feats") if isinstance(normalized_business.get("source_feats"), list) else []
        normalized_business["parent_epic"] = _resolve_parent_epic(
            _clean_text(normalized_business.get("parent_epic")),
            [item for item in source_feat_ids if isinstance(item, str)],
        )
        _ensure_structural_governance_task(normalized_business)
        planning_metadata = normalized_business.get("planning_metadata")
        if isinstance(planning_metadata, dict):
            task_directory = _clean_text(planning_metadata.get("task_directory"))
            primary_feat = next(
                (
                    _clean_text(item)
                    for item in source_feat_ids
                    if isinstance(item, str) and _clean_text(item)
                ),
                "",
            )
            if not primary_feat and isinstance(normalized_business.get("task_specs"), list):
                primary_feat = next(
                    (
                        _clean_text(item.get("source_feat"))
                        for item in normalized_business.get("task_specs") or []
                        if isinstance(item, dict) and _clean_text(item.get("source_feat"))
                    ),
                    "",
                )
            if not task_directory or "<FEAT-ID>" in task_directory:
                task_directory = f"spec/tasks/{primary_feat or 'FEAT-001'}"
            normalized_business["planning_metadata"] = {
                **planning_metadata,
                "task_directory": task_directory,
            }

        normalized_structured = LLMRunner._ensure_structured_envelope(
            business_output=normalized_business,
            structured_payload=structured_payload,
        )
        task_specs = normalized_business.get("task_specs") if isinstance(normalized_business.get("task_specs"), list) else []
        outputs: List[Dict[str, Any]] = []
        for index, task_spec in enumerate(task_specs, start=1):
            if not isinstance(task_spec, dict):
                continue
            task_id = _clean_text(task_spec.get("task_id")) or f"TASK-{index:03d}"
            title = _clean_text(task_spec.get("title")) or task_id
            source_feat = _clean_text(task_spec.get("source_feat")) or "FEAT-001"
            output_key = re.sub(r"[^a-z0-9_]+", "_", task_id.lower()).strip("_") or f"task_{index:03d}"
            output_item = {
                "key": output_key,
                "identity_kind": "ssot",
                "ssot_type": "task",
                "title": title,
                "parent": source_feat,
                "content": _build_task_markdown(task_spec),
                "properties": {
                    "feat_id": source_feat,
                    "task_id": task_id,
                    "slice_key": _clean_text(task_spec.get("task_kind")) or "implementation",
                    "workstream": _clean_text(task_spec.get("workstream")) or "workflow-runtime",
                },
            }
            if LLMRunner._is_literal_ssot_ref(source_feat):
                output_item["source_refs"] = [f"{source_feat}#delivery"]
                output_item["verifies"] = [source_feat]
            outputs.append(output_item)
        normalized_structured["ssot_output_contract"] = {
            "contract_version": "1.0",
            "run_id": workflow_id,
            "outputs": outputs,
        }
        return normalized_business, normalized_structured

    @staticmethod
    def _synthesize_single_ssot_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        agent_id = getattr(step, "agent_id", "") or ""
        step_id = getattr(step, "id", "") or ""
        if step_id in {"ui_design", "tech_design"}:
            payload = LLMRunner._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            metadata = business_output.get("metadata") if isinstance(business_output.get("metadata"), dict) else {}
            feat_id = None
            for candidate in (
                business_output.get("parent"),
                business_output.get("feat_id"),
                metadata.get("feat_id"),
                metadata.get("feature_id"),
                metadata.get("parent"),
            ):
                if isinstance(candidate, str) and LLMRunner._is_literal_ssot_ref(candidate):
                    feat_id = candidate.strip()
                    break
            if feat_id is None and isinstance(instance_data, dict):
                params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
                for candidate in (
                    params.get("feat_freeze"),
                    params.get("feat_freeze_ref"),
                ):
                    if isinstance(candidate, str) and LLMRunner._is_literal_ssot_ref(candidate):
                        feat_id = candidate.strip()
                        break
                    if isinstance(candidate, dict):
                        artifact_id = candidate.get("artifact_id")
                        if isinstance(artifact_id, str) and LLMRunner._is_literal_ssot_ref(artifact_id):
                            feat_id = artifact_id.strip()
                            break
                if feat_id is None:
                    feat_freeze_path = LLMRunner._extract_feat_freeze_path(instance_data)
                    if isinstance(feat_freeze_path, str) and feat_freeze_path.strip():
                        frontmatter = LLMRunner._load_yaml_frontmatter(Path(feat_freeze_path.strip()))
                        candidate = frontmatter.get("id")
                        if isinstance(candidate, str) and LLMRunner._is_literal_ssot_ref(candidate):
                            feat_id = candidate.strip()
            default_title = (
                str(
                    business_output.get("title")
                    or metadata.get("feature_title")
                    or metadata.get("title")
                    or getattr(step, "name", "")
                    or step_id
                ).strip()
                or step_id
            )
            default_output = {
                "key": "ui_prototype" if step_id == "ui_design" else "tech_spec",
                "identity_kind": "ssot",
                "ssot_type": "ui" if step_id == "ui_design" else "tech",
                "title": default_title,
                "content": LLMRunner._extract_step_written_markdown(step_id, payload)
                or yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            output_item = {
                **default_output,
            }
            if feat_id:
                output_item["parent"] = feat_id
                output_item["implements"] = [feat_id]

            existing_contract = payload.get("ssot_output_contract")
            if isinstance(existing_contract, dict):
                normalized_contract = dict(existing_contract)
                raw_outputs = normalized_contract.get("outputs")
                normalized_outputs: List[Dict[str, Any]] = []
                if isinstance(raw_outputs, list):
                    for raw_output in raw_outputs:
                        if not isinstance(raw_output, dict):
                            continue
                        merged_output = {**default_output, **dict(raw_output)}
                        if feat_id:
                            current_parent = merged_output.get("parent")
                            if not (
                                isinstance(current_parent, str)
                                and LLMRunner._is_literal_ssot_ref(current_parent)
                            ):
                                merged_output["parent"] = feat_id
                            implements = merged_output.get("implements")
                            if not isinstance(implements, list) or not implements:
                                merged_output["implements"] = [feat_id]
                        normalized_outputs.append(merged_output)
                if not normalized_outputs:
                    normalized_outputs = [output_item]
                normalized_contract["contract_version"] = "1.0"
                normalized_contract["run_id"] = str(normalized_contract.get("run_id") or workflow_id)
                normalized_contract["outputs"] = normalized_outputs
                payload["ssot_output_contract"] = normalized_contract
            else:
                payload["ssot_output_contract"] = {
                    "contract_version": "1.0",
                    "run_id": workflow_id,
                    "outputs": [output_item],
                }
            return business_output, payload

        if isinstance(structured_payload, dict) and isinstance(structured_payload.get("ssot_output_contract"), dict):
            return business_output, structured_payload

        if agent_id == "agent.product.epic_designer":
            source_refs = LLMRunner._derive_source_refs_from_business_output(
                business_output,
                allowed_prefixes=["SRC"],
            )
            ssot_meta = business_output.get("ssot") if isinstance(business_output.get("ssot"), dict) else {}
            derived_from = ssot_meta.get("derived_from")
            source_problem = ssot_meta.get("source_problem")
            canonical_source_ref = LLMRunner._resolve_source_ref_from_instance_data(instance_data)
            if not source_refs and isinstance(source_problem, str) and LLMRunner._is_literal_ssot_ref(source_problem):
                source_refs = [f"{source_problem}#scope"]
            if not derived_from and isinstance(source_problem, str) and LLMRunner._is_literal_ssot_ref(source_problem):
                derived_from = source_problem
            if not source_refs and canonical_source_ref:
                source_refs = [f"{canonical_source_ref}#scope"]
            if not derived_from and canonical_source_ref:
                derived_from = canonical_source_ref
            elif canonical_source_ref and (
                not isinstance(derived_from, str) or not LLMRunner._is_literal_ssot_ref(derived_from)
            ):
                derived_from = canonical_source_ref
            formal_epic_id = business_output.get("epic_id")
            if not source_refs and isinstance(derived_from, str) and LLMRunner._is_literal_ssot_ref(derived_from):
                source_refs = [f"{derived_from}#scope"]
            payload = LLMRunner._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            epic_output = {
                "key": "epic",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": str(business_output.get("title") or "EPIC").strip() or "EPIC",
                "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            if source_refs:
                epic_output["source_refs"] = source_refs
            if isinstance(derived_from, str) and derived_from.strip():
                epic_output["derived_from"] = derived_from.strip()
            if isinstance(formal_epic_id, str) and formal_epic_id.strip():
                epic_output["properties"] = {"formal_id": formal_epic_id.strip()}
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [epic_output],
            }
            return business_output, payload

        if step_id == "source_normalization":
            payload = LLMRunner._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            source_refs = LLMRunner._derive_source_refs_from_business_output(business_output)
            src_output = {
                "key": "src",
                "identity_kind": "ssot",
                "ssot_type": "src",
                "title": LLMRunner._derive_src_title_from_business_output(business_output),
                "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            if source_refs:
                src_output["source_refs"] = source_refs
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [src_output],
            }
            return business_output, payload

        return business_output, structured_payload

    @staticmethod
    def _normalize_business_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
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
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        normalized_business = dict(business_output)
        if (
            getattr(step, "agent_id", "") == "agent.product.feat_reviewer"
            and normalized_business.get("review_type") is None
        ):
            normalized_business["review_type"] = "feat_review"
            normalized_business.setdefault("summary", normalized_business.get("review_summary") or "")
            feat_reviews = normalized_business.get("feat_reviews")
            if isinstance(feat_reviews, list):
                normalized_business.setdefault(
                    "subject_refs",
                    [
                        str(item.get("feat_id")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict) and str(item.get("feat_id") or "").strip()
                    ],
                )
                if "findings" not in normalized_business:
                    findings = [
                        str(item.get("notes")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict)
                        and str(item.get("status") or "").strip().lower()
                        not in {"approved", "pass", "passed", "approved_with_notes", "approved_with_recommendations"}
                        and str(item.get("notes") or "").strip()
                    ]
                    normalized_business["findings"] = findings
                if not isinstance(normalized_business.get("recommendations"), list):
                    normalized_business["recommendations"] = []
                for item in feat_reviews:
                    if not isinstance(item, dict):
                        continue
                    item_status = str(item.get("status") or "").strip().lower()
                    note = str(item.get("notes") or "").strip()
                    if item_status in {"approved_with_notes", "approved_with_recommendations"} and note:
                        normalized_business["recommendations"].append(note)
            recommendations = normalized_business.get("recommendations")
            if not isinstance(recommendations, list):
                normalized_business["recommendations"] = []
            normalized_business.setdefault("risks", [])
            status_text = str(normalized_business.get("status") or "").strip().lower()
            if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
                if status_text in {"approved", "approved_with_recommendations", "approved_with_notes"}:
                    normalized_business["decision"] = "pass"
                elif status_text in {"revise", "needs_revision", "changes_requested"}:
                    normalized_business["decision"] = "revise"
                elif status_text in {"rejected", "reject", "failed"}:
                    normalized_business["decision"] = "reject"
            if "findings" not in normalized_business:
                normalized_business["findings"] = []

        review_type = normalized_business.get("review_type")
        if review_type not in {"source_review", "epic_review", "feat_review", "delivery_plan_review"}:
            return business_output, structured_payload

        if review_type == "delivery_plan_review":
            expected_subject_refs = LLMRunner._expected_delivery_plan_subject_refs(
                instance_data,
                normalized_business,
            )
            if expected_subject_refs and not normalized_business.get("subject_refs"):
                normalized_business["subject_refs"] = expected_subject_refs

        if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
            candidate = (
                normalized_business.get("status")
                or normalized_business.get("review_status")
                or normalized_business.get("approval_decision")
            )
            decision_map = {
                "pass": "pass",
                "passed": "pass",
                "approved": "pass",
                "approve": "pass",
                "success": "pass",
                "ok": "pass",
                "revise": "revise",
                "revision_required": "revise",
                "needs_revision": "revise",
                "needs_revise": "revise",
                "changes_requested": "revise",
                "approved_with_recommendations": "pass",
                "approved_with_notes": "pass",
                "reject": "reject",
                "rejected": "reject",
                "fail": "reject",
                "failed": "reject",
            }
            normalized_candidate = str(candidate or "").strip().lower()
            normalized_decision = decision_map.get(normalized_candidate)
            if normalized_decision:
                normalized_business["decision"] = normalized_decision
        if not isinstance(normalized_business.get("summary"), str):
            normalized_business["summary"] = str(
                normalized_business.get("review_summary")
                or normalized_business.get("summary")
                or ""
            ).strip()
        for field_name in ("subject_refs", "findings", "risks", "recommendations"):
            value = normalized_business.get(field_name)
            if isinstance(value, list):
                normalized_business[field_name] = [str(item).strip() for item in value if str(item).strip()]
            elif field_name == "subject_refs":
                normalized_business[field_name] = []
            else:
                normalized_business[field_name] = []

        normalized_structured = structured_payload
        if (
            isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
        ):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business

        return normalized_business, normalized_structured

    @staticmethod
    def _build_schema_repair_prompt(
        *,
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> str:
        payload = business_output
        if not isinstance(payload, dict) and isinstance(structured_payload, dict):
            payload = structured_payload

        payload_text = json.dumps(
            payload if payload is not None else {},
            ensure_ascii=False,
            indent=2,
        )
        return (
            "修复下面这个结构化输出，使其满足当前 step 的 output contract。\n"
            "只允许返回最终 JSON 对象，不要输出解释、标题、代码块或额外包裹层。\n"
            f"step_id: {getattr(step, 'id', '')}\n"
            f"validation_error: {validation_error}\n"
            "要求：\n"
            "- 保留原始语义，不要重新发明业务内容\n"
            "- 仅补足缺失字段、修正字段名或枚举值、规范结构\n"
            "- 如果原输出里缺少必要结论字段，请基于已有 summary/findings/risks/recommendations 做最小修复\n"
            "- 返回内容必须是可直接通过 schema 校验的单个 JSON 对象\n"
            "原始 payload:\n"
            f"{payload_text}"
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
        repair_prompt = cls._build_schema_repair_prompt(
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )
        repaired_input = dict(input_data)
        if executor_type in ("codex", "claude_code", "kimi"):
            repaired_input["goal"] = repair_prompt
            repaired_input["context_files"] = []
            repaired_input["write_scope"] = []
            repaired_input["max_iterations"] = 1
            repaired_input["allowed_commands"] = []
            repaired_input["system_prompt_extra"] = (
                "你正在执行 schema repair retry。"
                "不要修改文件，不要调用命令，只输出最终 JSON 对象。"
            )
        else:
            repaired_input["prompt"] = repair_prompt
            repaired_input["system_message"] = (
                "You are repairing structured output to satisfy a JSON schema. "
                "Return only a single JSON object."
            )
            repaired_input["temperature"] = 0
        return repaired_input

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
        repair_input = self._build_schema_repair_input(
            executor_type=executor_type,
            input_data=input_data,
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )

        retry_executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=0, base_delay=0, jitter=False)
        )
        repair_result = await retry_executor.execute(executor.execute, repair_input)
        if not repair_result.success:
            return None

        repaired_output = repair_result.result
        if not isinstance(repaired_output, dict):
            return None

        if executor_type in ("codex", "claude_code", "kimi"):
            repaired_business_output, repaired_structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
                step=step,
                workflow_id=workflow_id,
                output=repaired_output,
                written_files=[],
            )
        else:
            repaired_generated_text = repaired_output.get("generated_text", "") or ""
            repaired_structured_payload = self._parse_structured_output_if_possible(repaired_generated_text)
            repaired_business_output = self._extract_business_output_payload(
                repaired_structured_payload,
                repaired_generated_text,
                step=step,
                written_files=[],
            )
            repaired_business_output, repaired_structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=repaired_business_output,
                structured_payload=repaired_structured_payload,
            )

        if not isinstance(repaired_business_output, dict):
            return None

        return {
            "output": repaired_output,
            "business_output": repaired_business_output,
            "structured_payload": repaired_structured_payload,
        }

    @staticmethod
    def _validate_feat_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not expected_subject_refs:
            return None
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"

        expected = {ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()}
        actual = {ref for ref in subject_refs if isinstance(ref, str) and ref.strip()}
        if not expected.issubset(actual):
            return (
                "FEAT review subject_refs must include the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )
        return None

    @staticmethod
    def _validate_feat_review_semantics(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"

        review_type = review_payload.get("review_type")
        if review_type != "feat_review":
            return "FEAT review output must set review_type=feat_review"

        summary = review_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return "FEAT review output must include a non-empty summary"

        decision = review_payload.get("decision")
        if decision not in {"pass", "revise", "reject"}:
            return "FEAT review output decision must be one of: pass, revise, reject"

        for field_name in ("findings", "risks", "recommendations"):
            value = review_payload.get(field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return f"FEAT review output field '{field_name}' must be a string array"

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"

        expected = [ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()]
        actual = [ref for ref in subject_refs if isinstance(ref, str) and ref.strip()]
        if expected and sorted(actual) != sorted(expected):
            return (
                "FEAT review subject_refs must exactly match the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )

        findings = review_payload.get("findings") or []
        if decision == "pass":
            if findings:
                return "FEAT review output with decision=pass must not include findings"
            if LLMRunner._contains_feat_review_negative_signal(summary):
                return "FEAT review summary conflicts with decision=pass"

        if decision in {"revise", "reject"} and not findings:
            return f"FEAT review output with decision={decision} must include at least one finding"

        if decision == "revise":
            return "FEAT review requires revision before freeze"
        if decision == "reject":
            return "FEAT review rejected the generated FEAT bundle"

        return None

    @staticmethod
    def _expected_delivery_plan_subject_refs(
        instance_data: Optional[Dict[str, Any]],
        business_output: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        refs: List[str] = []

        if isinstance(business_output, dict):
            for candidate in business_output.get("subject_refs", []):
                if isinstance(candidate, str) and candidate.strip() and candidate.strip() not in refs:
                    refs.append(candidate.strip())

        if isinstance(instance_data, dict):
            step_outputs = instance_data.get("step_outputs")
            if isinstance(step_outputs, dict):
                task_planning = step_outputs.get("task_planning")
                if isinstance(task_planning, dict):
                    task_business = task_planning.get("business_output")
                    if not isinstance(task_business, dict):
                        generated_text = task_planning.get("generated_text")
                        if isinstance(generated_text, str) and generated_text.strip():
                            parsed = LLMRunner._parse_structured_output_if_possible(generated_text)
                            if isinstance(parsed, dict):
                                nested_business = parsed.get("business_output")
                                task_business = nested_business if isinstance(nested_business, dict) else parsed
                    if isinstance(task_business, dict):
                        for candidate in task_business.get("source_feats", []):
                            if isinstance(candidate, str) and candidate.strip() and candidate.strip() not in refs:
                                refs.append(candidate.strip())

        return refs

    @staticmethod
    def _validate_delivery_plan_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not expected_subject_refs:
            return None
        if not isinstance(review_payload, dict):
            return "Delivery plan review output is not a structured object"

        review_type = review_payload.get("review_type")
        if review_type != "delivery_plan_review":
            return "Delivery plan review output must set review_type=delivery_plan_review"

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "Delivery plan review output missing subject_refs list"

        expected = [ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()]
        actual = [ref for ref in subject_refs if isinstance(ref, str) and ref.strip()]
        if sorted(actual) != sorted(expected):
            return (
                "Delivery plan review subject_refs must exactly match the planned FEAT ID(s): "
                + ", ".join(sorted(expected))
            )
        return None

    @classmethod
    def _load_task_plan_business_output(cls, instance_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(instance_data, dict):
            return None
        step_outputs = instance_data.get("step_outputs")
        if not isinstance(step_outputs, dict):
            return None
        task_planning = step_outputs.get("task_planning")
        if not isinstance(task_planning, dict):
            return None
        business_output = task_planning.get("business_output")
        if isinstance(business_output, dict):
            return business_output
        generated_text = task_planning.get("generated_text")
        if isinstance(generated_text, str) and generated_text.strip():
            parsed = cls._parse_structured_output_if_possible(generated_text)
            if isinstance(parsed, dict):
                nested = parsed.get("business_output")
                if isinstance(nested, dict):
                    return nested
                return parsed
        return None

    @staticmethod
    def _review_clean_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @classmethod
    def _delivery_plan_has_persisted_tasks(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        planning_metadata = task_plan.get("planning_metadata")
        task_directory = ""
        if isinstance(planning_metadata, dict):
            task_directory = cls._review_clean_text(planning_metadata.get("task_directory"))
        if not task_directory:
            source_feats = task_plan.get("source_feats") if isinstance(task_plan.get("source_feats"), list) else []
            primary_feat = next(
                (
                    cls._review_clean_text(item)
                    for item in source_feats
                    if isinstance(item, str) and cls._review_clean_text(item)
                ),
                "",
            )
            task_directory = f"spec/tasks/{primary_feat or 'FEAT-001'}"
        task_dir_path = Path(project_root) / task_directory
        task_specs = task_plan.get("task_specs") if isinstance(task_plan.get("task_specs"), list) else []
        if not task_dir_path.exists() or not task_specs:
            return False
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            task_id = cls._review_clean_text(task_spec.get("task_id"))
            if not task_id:
                continue
            if not list(task_dir_path.glob(f"{task_id}__*.md")):
                return False
        return True

    @classmethod
    def _delivery_plan_has_structural_spec_coverage(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        source_feats = task_plan.get("source_feats") if isinstance(task_plan.get("source_feats"), list) else []
        primary_feat = next(
            (
                cls._review_clean_text(item)
                for item in source_feats
                if isinstance(item, str) and cls._review_clean_text(item)
            ),
            "",
        )
        if not primary_feat:
            return False
        formal_checks = cls._load_feat_acceptance_checks(project_root, primary_feat)
        structural_ids = {
            str(item.get("id")).strip()
            for item in formal_checks
            if isinstance(item, dict)
            and str(item.get("id") or "").strip()
            and cls._is_structural_acceptance_check(item)
        }
        if not structural_ids:
            return False
        task_specs = task_plan.get("task_specs") if isinstance(task_plan.get("task_specs"), list) else []
        covered_ids: set[str] = set()
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            task_kind = _clean_text(task_spec.get("task_kind")).lower()
            if task_kind not in {"governance", "specification", "template"}:
                continue
            mappings = task_spec.get("acceptance_criteria_mapping")
            if not isinstance(mappings, list):
                continue
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    continue
                ac_id = cls._review_clean_text(mapping.get("ac"))
                if ac_id in structural_ids:
                    covered_ids.add(ac_id)
        return structural_ids.issubset(covered_ids)

    @classmethod
    def _contains_delivery_plan_false_positive(cls, text: str) -> bool:
        lowered = text.strip().lower()
        if not lowered:
            return False
        positive_patterns = [
            r"\bexists\b",
            r"\bdefined\b",
            r"\bcovers\b",
            r"\bconsistent\b",
            r"\bcan be derived\b",
            r"\bhas \d+\b",
            r"\bverified\b",
            r"\bavailable\b",
            r"存在",
            r"已定义",
            r"一致",
            r"可推导",
            r"可得",
            r"已覆盖",
            r"已落盘",
        ]
        return any(re.search(pattern, lowered) for pattern in positive_patterns)

    @classmethod
    def _validate_delivery_plan_review_semantics(
        cls,
        *,
        project_root: str,
        review_payload: Any,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not isinstance(review_payload, dict):
            return "Delivery plan review output is not a structured object"

        if review_payload.get("review_type") != "delivery_plan_review":
            return "Delivery plan review output must set review_type=delivery_plan_review"

        summary = review_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return "Delivery plan review output must include a non-empty summary"

        decision = review_payload.get("decision")
        if decision not in {"pass", "revise", "reject"}:
            return "Delivery plan review output decision must be one of: pass, revise, reject"

        for field_name in ("findings", "risks", "recommendations"):
            value = review_payload.get(field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return f"Delivery plan review output field '{field_name}' must be a string array"

        findings = [item.strip() for item in review_payload.get("findings") or [] if isinstance(item, str) and item.strip()]
        if decision == "pass":
            if findings:
                return "Delivery plan review output with decision=pass must not include findings"
            if cls._contains_feat_review_negative_signal(summary):
                return "Delivery plan review summary conflicts with decision=pass"

        if decision in {"revise", "reject"} and not findings:
            return f"Delivery plan review output with decision={decision} must include at least one finding"

        task_plan = cls._load_task_plan_business_output(instance_data)
        if decision == "revise":
            if findings and all(cls._contains_delivery_plan_false_positive(item) for item in findings):
                return "Delivery plan review findings contain no blocking issues"

            all_review_text = "\n".join(
                findings
                + [item.strip() for item in review_payload.get("risks") or [] if isinstance(item, str)]
                + [item.strip() for item in review_payload.get("recommendations") or [] if isinstance(item, str)]
            )
            if re.search(r"落盘|persist|persistence|unverified", all_review_text, re.IGNORECASE):
                if cls._delivery_plan_has_persisted_tasks(project_root=project_root, task_plan=task_plan):
                    return "Delivery plan review incorrectly reports TASK persistence as unverified"
            if re.search(r"spec/template coverage|规范任务|模板任务|specification", all_review_text, re.IGNORECASE):
                if cls._delivery_plan_has_structural_spec_coverage(project_root=project_root, task_plan=task_plan):
                    return "Delivery plan review incorrectly reports missing structural specification coverage"

            return "Delivery plan review requires revision before freeze"

        if decision == "reject":
            return "Delivery plan review rejected the generated delivery plan"

        return None

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
        if not isinstance(business_output, dict):
            return None
        epic_ref = business_output.get("epic_ref")
        feat_specs = business_output.get("feat_specs")
        if not isinstance(epic_ref, str) or not epic_ref.strip():
            return None
        if not isinstance(feat_specs, list) or not feat_specs:
            return None

        def _is_placeholder_input_value(value: Any) -> bool:
            normalized = str(value or "").strip().lower()
            if not normalized:
                return True
            placeholder_markers = (
                "inputs defined by epic scope",
                "input defined by epic scope",
                "same as epic",
                "tbd",
                "to be defined",
                "待补充",
                "待定义",
                "同 epic",
            )
            return any(marker in normalized for marker in placeholder_markers)

        for feat_spec in feat_specs:
            if not isinstance(feat_spec, dict):
                continue
            feat_id = str(feat_spec.get("feat_id") or feat_spec.get("title") or "unknown").strip()
            inputs = feat_spec.get("inputs")
            if not isinstance(inputs, list) or not inputs:
                return f"FEAT {feat_id} is missing concrete inputs"
            if any(_is_placeholder_input_value(item) for item in inputs):
                return f"FEAT {feat_id} uses placeholder inputs and cannot drive downstream design"
            input_contract = feat_spec.get("input_contract")
            if not isinstance(input_contract, dict):
                return f"FEAT {feat_id} is missing input_contract"
            required_artifacts = input_contract.get("required_artifacts")
            required_fields = input_contract.get("required_fields")
            consumption_rules = input_contract.get("consumption_rules")
            if not isinstance(required_artifacts, list) or not required_artifacts:
                return f"FEAT {feat_id} is missing input_contract.required_artifacts"
            if not isinstance(required_fields, list) or not required_fields:
                return f"FEAT {feat_id} is missing input_contract.required_fields"
            if any(_is_placeholder_input_value(item) for item in required_fields):
                return f"FEAT {feat_id} uses placeholder required_fields and cannot drive downstream design"
            if not isinstance(consumption_rules, list) or not consumption_rules:
                return f"FEAT {feat_id} is missing input_contract.consumption_rules"

        epic_markdown = cls._load_ssot_markdown(project_root, epic_ref.strip())
        if not isinstance(epic_markdown, str) or not epic_markdown.strip():
            return None

        epic_families = cls._extract_topic_families(epic_markdown)
        if not epic_families:
            return None

        feat_fragments: List[str] = []
        for feat_spec in feat_specs:
            if not isinstance(feat_spec, dict):
                continue
            for key in ("title", "goal", "user_value"):
                value = feat_spec.get(key)
                if isinstance(value, str) and value.strip():
                    feat_fragments.append(value.strip())
            for key in ("inputs", "processing", "outputs", "acceptance_criteria", "dependencies", "non_goals"):
                value = feat_spec.get(key)
                if isinstance(value, list):
                    feat_fragments.extend(str(item).strip() for item in value if str(item).strip())

        feat_text = "\n".join(feat_fragments)
        feat_families = cls._extract_topic_families(feat_text)
        if feat_families and epic_families.isdisjoint(feat_families):
            return (
                f"FEAT bundle semantics drift from {epic_ref}: "
                f"epic topic families={sorted(epic_families)}, "
                f"feat topic families={sorted(feat_families)}"
            )
        return None

    @classmethod
    def _validate_pm_planner_task_semantics(
        cls,
        *,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        if not isinstance(business_output, dict):
            return None

        task_specs = business_output.get("task_specs")
        if not isinstance(task_specs, list) or not task_specs:
            return None

        source_feats = [
            str(item).strip()
            for item in (business_output.get("source_feats") or [])
            if isinstance(item, str) and str(item).strip()
        ]
        if not source_feats:
            source_feats = list(
                dict.fromkeys(
                    str(item.get("source_feat")).strip()
                    for item in task_specs
                    if isinstance(item, dict) and isinstance(item.get("source_feat"), str) and item.get("source_feat").strip()
                )
            )
        if not source_feats:
            return None

        feat_markdowns: List[str] = []
        for feat_id in source_feats:
            markdown = cls._load_ssot_markdown(project_root, feat_id)
            if isinstance(markdown, str) and markdown.strip():
                feat_markdowns.append(markdown)
        if not feat_markdowns:
            return None

        source_text = "\n".join(feat_markdowns)
        source_families = cls._extract_topic_families(source_text)
        governance_scope = bool(source_families & {"governance"}) or any(
            cls._text_contains_keyword(
                source_text,
                keyword,
            )
            for keyword in (
                "workflow",
                "pipeline",
                "freeze",
                "gate",
                "registry",
                "run spec",
                "migration guide",
                "调用文档",
                "契约",
                "文档",
                "模板",
            )
        )
        if not governance_scope:
            return None

        task_fragments: List[str] = []
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            for key in (
                "task_id",
                "title",
                "objective",
                "description",
                "source_feat",
                "workstream",
                "task_kind",
                "responsible_role",
                "milestone",
                "estimated_effort",
            ):
                value = task_spec.get(key)
                if isinstance(value, str) and value.strip():
                    task_fragments.append(value.strip())
            for key in ("definition_of_done", "prerequisites", "dependencies"):
                value = task_spec.get(key)
                if isinstance(value, list):
                    task_fragments.extend(str(item).strip() for item in value if str(item).strip())
            for mapping in task_spec.get("acceptance_criteria_mapping") or []:
                if not isinstance(mapping, dict):
                    continue
                for key in ("feat", "ac", "description"):
                    value = mapping.get(key)
                    if isinstance(value, str) and value.strip():
                        task_fragments.append(value.strip())
            rollback_strategy = task_spec.get("rollback_strategy")
            if isinstance(rollback_strategy, dict):
                for key in ("mode",):
                    value = rollback_strategy.get(key)
                    if isinstance(value, str) and value.strip():
                        task_fragments.append(value.strip())
                restore_targets = rollback_strategy.get("restore_targets")
                if isinstance(restore_targets, list):
                    task_fragments.extend(str(item).strip() for item in restore_targets if str(item).strip())

        task_text = "\n".join(task_fragments)
        source_allows_ui = any(
            cls._text_contains_keyword(source_text, keyword)
            for keyword in cls.FEAT_UI_KEYWORDS
        )
        source_allows_tech = bool(
            re.search(r"trace hints:\s*[^\n]*\btech\b", source_text, re.IGNORECASE)
            or re.search(r"trace hints:\s*[^\n]*技术", source_text, re.IGNORECASE)
        )

        drift_hits: List[str] = []
        for family, keywords in cls.PM_TASK_DRIFT_KEYWORDS.items():
            if family == "product_ui" and source_allows_ui:
                continue
            if family == "infra_storage" and source_allows_tech:
                continue
            for keyword in keywords:
                if cls._text_contains_keyword(task_text, keyword) and not cls._text_contains_keyword(source_text, keyword):
                    drift_hits.append(keyword)
        if drift_hits:
            return (
                "TASK bundle semantics drift from source FEAT scope: "
                f"unexpected topics={sorted(set(drift_hits))}, source_feats={source_feats}"
            )

        max_expected_tasks = max(len(source_feats) * 2, 8)
        if len(task_specs) > max_expected_tasks:
            return (
                "TASK bundle overscoped for workflow/governance FEATs: "
                f"task_count={len(task_specs)}, max_expected={max_expected_tasks}, source_feats={source_feats}"
            )

        return None

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
        return None

    @classmethod
    def _extract_best_written_file_payload(cls, step, written_files: List[str]) -> Optional[Any]:
        if getattr(step, "agent_id", "") == "agent.product.prd_writer":
            aggregated_bundle = cls._build_prd_writer_bundle_from_written_files(written_files)
            if aggregated_bundle is not None:
                return aggregated_bundle
        if getattr(step, "agent_id", "") == "agent.product.pm_planner":
            aggregated_bundle = cls._build_pm_planner_bundle_from_written_files(written_files)
            if aggregated_bundle is not None:
                return aggregated_bundle

        best_payload: Optional[Any] = None
        best_score = -1
        for file_path in written_files:
            try:
                parsed_file = StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                continue
            score = cls._score_written_output_candidate(step, parsed_file)
            if score > best_score:
                best_score = score
                best_payload = parsed_file
        return best_payload

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
        if not isinstance(structured_payload, dict):
            payload = self._extract_structured_segment_payload(generated_text, "ssot_output_contract")
            payload = self._coerce_ssot_contract_dict(payload)
            if isinstance(payload, dict):
                return payload
            block_payload = self._extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
            block_payload = self._coerce_ssot_contract_dict(block_payload)
            return block_payload if isinstance(block_payload, dict) else None
        if "contract_version" in structured_payload and "outputs" in structured_payload:
            return structured_payload
        payload = self._coerce_ssot_contract_dict(structured_payload.get("ssot_output_contract"))
        if isinstance(payload, dict):
            return payload
        segment_payload = self._coerce_ssot_contract_dict(
            self._extract_structured_segment_payload(generated_text, "ssot_output_contract")
        )
        if isinstance(segment_payload, dict):
            return segment_payload
        block_payload = self._coerce_ssot_contract_dict(
            self._extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
        )
        if isinstance(block_payload, dict):
            return block_payload
        return None

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
    _materialize_workspace_formal_ssot_markdown = staticmethod(
        LLMRunner._materialize_workspace_formal_ssot_markdown
    )
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
        try:
            return StepRunnerBase._parse_structured_output(output_text)
        except ValueError:
            return None

    @classmethod
    def _extract_business_output_for_validation(
        cls,
        *,
        step,
        workflow_id: str,
        output: Dict[str, Any],
        written_files: List[str],
    ) -> tuple[Any, Any]:
        raw_output = output.get("raw_output", "") or ""
        generated_text = output.get("generated_text", "") or ""

        def looks_like_executor_wrapper(payload: Any) -> bool:
            if not isinstance(payload, dict):
                return False
            wrapper_keys = {
                "status",
                "changed_files",
                "commands_run",
                "test_results",
                "diff_summary",
                "evidence_bundle_path",
                "conversation_log_path",
                "debug_log_path",
                "prompt_system_path",
                "prompt_user_path",
                "generated_text",
                "error",
                "iterations_used",
            }
            return bool(wrapper_keys & set(payload.keys()))

        raw_structured_payload = cls._parse_structured_output_if_possible(raw_output)
        generated_structured_payload = cls._parse_structured_output_if_possible(generated_text)

        structured_payload = raw_structured_payload
        if structured_payload is None or looks_like_executor_wrapper(structured_payload):
            if generated_structured_payload is not None:
                structured_payload = generated_structured_payload

        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            business_output = structured_payload["business_output"]
        elif isinstance(structured_payload, dict) and not looks_like_executor_wrapper(structured_payload):
            business_output = structured_payload
        else:
            business_output = LLMRunner._extract_primary_file_output(step, written_files)
            if business_output is None:
                business_output = LLMRunner._extract_best_written_file_payload(step, written_files)
            if isinstance(business_output, dict) and "business_output" in business_output:
                business_output = business_output["business_output"]
            if business_output is None:
                business_output = raw_output or generated_text or json.dumps(output)

        if isinstance(business_output, list):
            business_output = business_output[0] if business_output else {}

        return LLMRunner._normalize_business_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=None,
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
