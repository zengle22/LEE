"""LEE Orchestrator LLM step runners."""

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

from lee.orchestrator.config import is_coding_executor_type, normalize_executor_type_name
from lee.orchestrator.config_loader import load_config
from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY, RetryPolicy
from lee.orchestrator.execution.output_path_guard import detect_forbidden_template_write_paths
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext
from lee.orchestrator.execution.runners.code_executor_scope import build_code_executor_io_config, fail_code_executor_scope_violation, validate_code_executor_write_scope
from lee.orchestrator.execution.runners.normalization import (
    PmPlannerTaskNormalizer,
    ReviewSemanticValidator,
    SingleSSOTNormalizer,
    WorkflowSemanticValidator,
    align_inputs_with_required_artifacts,
    align_required_artifacts,
    refine_acceptance_checks,
    refine_feat_outputs,
)
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
    def _is_qwen_chat_executor(executor_type: Any) -> bool:
        return str(executor_type or "").strip().lower() in {"qwen", "qwen_chat"}

    @staticmethod
    def _is_coding_executor(executor_type: Any) -> bool:
        return str(executor_type or "").strip().lower() in {"claude_code", "codex", "kimi"}

    @staticmethod
    def _contains_cjk(text: Any) -> bool:
        if not isinstance(text, str):
            return False
        return re.search(r"[\u3400-\u9fff]", text) is not None

    @staticmethod
    def _extract_markdown_section(text: Any, heading: str) -> str:
        source = str(text or "")
        if not source.strip() or not heading:
            return ""
        pattern = re.compile(
            rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
        )
        match = pattern.search(source)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _truncate_text(text: Any, limit: int) -> str:
        value = str(text or "").strip()
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 4)].rstrip() + "\n..."

    @classmethod
    def _adapt_qwen_structured_prompt(cls, prompt: Any) -> str:
        source = str(prompt or "").strip()
        if not source:
            return source

        sections: List[str] = []
        task_match = re.search(r"(?ms)^#\s+Task\s*\n(.*?)(?=^##\s+|\Z)", source)
        task_body = task_match.group(1).strip() if task_match else ""
        if task_body:
            sections.append("## Task\n" + cls._truncate_text(task_body, 800))

        for heading, limit in (
            ("Responsibility", 400),
            ("Input Data", 1800),
            ("Upstream Step Outputs", 1800),
            ("Output Contract", 2200),
            ("Instructions", 800),
        ):
            body = cls._extract_markdown_section(source, heading)
            if body:
                sections.append(f"## {heading}\n{cls._truncate_text(body, limit)}")

        compact_body = "\n\n".join(sections) if sections else cls._truncate_text(source, 3200)
        return "\n".join(
            [
                "Return the required result now.",
                "Rules:",
                "- Output exactly one machine-readable JSON or YAML object.",
                "- Do not introduce yourself, list capabilities, ask what the user needs, or add commentary.",
                "- Do not use Markdown code fences unless the prompt explicitly requires file sections.",
                "- If the input is incomplete, preserve uncertainty inside the structured payload instead of asking follow-up questions.",
                "",
                compact_body,
            ]
        ).strip()

    @classmethod
    def _adapt_qwen_input_data(cls, input_data: Dict[str, Any]) -> Dict[str, Any]:
        adapted = dict(input_data)
        system_message = str(adapted.get("system_message") or "").strip()
        strict_system = "\n".join(
            [
                "You are executing a workflow step and must return the requested structured payload immediately.",
                "Never answer with greetings, capability descriptions, or clarification questions.",
                "Prefer strict JSON output when possible.",
            ]
        )
        adapted["system_message"] = (
            f"{system_message}\n\n{strict_system}".strip()
            if system_message
            else strict_system
        )
        adapted["prompt"] = cls._adapt_qwen_structured_prompt(adapted.get("prompt"))
        return adapted

    @classmethod
    def _build_qwen_repair_input(
        cls,
        *,
        input_data: Dict[str, Any],
        llm_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        original_prompt = str(input_data.get("prompt") or "")
        previous_answer = cls._truncate_text(llm_output.get("generated_text") or "", 2400)
        repair_prompt = "\n".join(
            [
                "Your previous answer did not satisfy the required structured output contract.",
                "Return exactly one machine-readable JSON or YAML object now.",
                "Do not ask for clarification. Do not introduce yourself. Do not describe capabilities.",
                "Do not use Markdown code fences.",
                "",
                "## Original Task",
                cls._adapt_qwen_structured_prompt(original_prompt),
                "",
                "## Previous Invalid Answer",
                previous_answer or "<empty>",
            ]
        ).strip()
        repaired = dict(input_data)
        repaired["prompt"] = repair_prompt
        return repaired

    @classmethod
    async def _retry_same_executor_output(
        cls,
        *,
        executor: Any,
        input_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)
        retry_result = await retry_executor.execute(executor.execute, input_data)
        if not retry_result.success:
            return None
        repaired_output = retry_result.result or {}
        if repaired_output.get("status") == "failed":
            return None
        return repaired_output

    @classmethod
    def _resolve_qwen_fallback_target(cls, project_root: Optional[str]) -> Optional[str]:
        try:
            config = load_config(project_root or ".")
        except Exception:
            return None
        candidate = normalize_executor_type_name(getattr(config.executor, "default_type", None))
        if not candidate or cls._is_qwen_chat_executor(candidate) or is_coding_executor_type(candidate):
            return None
        return candidate

    @classmethod
    def _resolve_code_executor_type(
        cls,
        *,
        instance_data: Optional[Dict[str, Any]],
        project_root: Optional[str],
    ) -> str:
        override = ""
        if isinstance(instance_data, dict):
            override = str(instance_data.get("executor_override") or "").strip().lower()
        if cls._is_coding_executor(override):
            return override

        for candidate in cls._resolve_code_executor_candidates(project_root):
            return candidate
        return "claude_code"

    @classmethod
    def _resolve_code_executor_candidates(cls, project_root: Optional[str]) -> List[str]:
        candidates: List[str] = []

        def add(raw_value: Any) -> None:
            normalized = normalize_executor_type_name(raw_value)
            if cls._is_coding_executor(normalized) and normalized not in candidates:
                candidates.append(normalized)

        try:
            config = load_config(project_root or ".")
        except Exception:
            config = None

        executor_config = getattr(config, "executor", None) if config is not None else None
        add(getattr(executor_config, "coding_executor", None))

        configured_fallbacks = getattr(executor_config, "coding_fallbacks", None)
        if isinstance(configured_fallbacks, (list, tuple)):
            for item in configured_fallbacks:
                add(item)
        else:
            add(getattr(executor_config, "coding_fallback", None))
            add(getattr(executor_config, "coding_second_fallback", None))

        add(getattr(executor_config, "default_type", None))
        for builtin in ("claude_code", "kimi", "codex"):
            add(builtin)
        return candidates

    @classmethod
    async def _execute_fallback_executor(
        cls,
        *,
        fallback_executor_type: str,
        selected_profile: str,
        step,
        ctx: RunnerContext,
        input_data: Dict[str, Any],
        workflow_id: str,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        fallback_profile = cls._resolve_fallback_profile(
            fallback_executor_type=fallback_executor_type,
            selected_profile=selected_profile,
            ctx=ctx,
        )
        if fallback_executor_type == "llm" and not fallback_profile:
            return None
        fallback_executor = ctx.executor_factory.create(
            fallback_executor_type,
            profile=fallback_profile,
            agent_id=step.agent_id or "",
        )
        retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)
        fallback_retry_result = await retry_executor.execute(fallback_executor.execute, input_data)
        if not fallback_retry_result.success:
            return None
        fallback_output = fallback_retry_result.result or {}
        if fallback_output.get("status") == "failed":
            return None
        return fallback_output

    @classmethod
    def _resolve_fallback_profile(
        cls,
        *,
        fallback_executor_type: str,
        selected_profile: str,
        ctx: RunnerContext,
    ) -> Optional[str]:
        if fallback_executor_type == "kimi":
            return "kimi"
        if fallback_executor_type == "llm":
            default_profile = (
                ctx.llm_config_loader.get_default_profile()
                if hasattr(ctx, "llm_config_loader")
                else None
            )
            normalized = str(default_profile or "").strip().lower()
            if normalized in {"qwen", "qwen_chat"}:
                return None
            return default_profile or None
        return os.getenv("LLM_PROFILE") or selected_profile

    @classmethod
    async def _maybe_fallback_qwen_output(
        cls,
        *,
        executor_type: str,
        executor: Any,
        step,
        ctx: RunnerContext,
        instance,
        workflow_id: str,
        execution_id: str,
        input_data: Dict[str, Any],
        llm_output: Dict[str, Any],
        selected_profile: str,
    ) -> Dict[str, Any]:
        if not cls._is_qwen_chat_executor(executor_type):
            return llm_output

        source_prompt = "\n".join(
            part for part in [
                str(input_data.get("prompt") or ""),
                str(input_data.get("goal") or ""),
                str(input_data.get("system_message") or ""),
            ]
            if part
        )
        if not cls._contains_cjk(source_prompt):
            return llm_output

        generated_text = str(llm_output.get("generated_text") or "").strip()
        structured_payload = llm_output.get("structured_payload")
        should_fallback = (
            llm_output.get("status") == "failed"
            or not generated_text
            or not isinstance(structured_payload, dict)
        )
        if should_fallback:
            repaired_output = await cls._retry_same_executor_output(
                executor=executor,
                input_data=cls._build_qwen_repair_input(
                    input_data=input_data,
                    llm_output=llm_output,
                ),
            )
            if repaired_output:
                repaired_text = str(repaired_output.get("generated_text") or "").strip()
                repaired_payload = repaired_output.get("structured_payload")
                if not isinstance(repaired_payload, dict):
                    repaired_payload = cls._parse_structured_output_if_possible(repaired_text)
                    if isinstance(repaired_payload, dict):
                        repaired_output = dict(repaired_output)
                        repaired_output["structured_payload"] = repaired_payload
                if repaired_text and isinstance(repaired_payload, dict):
                    repaired_output["qwen_repair_retry"] = True
                    repaired_output["qwen_initial_output"] = {
                        "status": llm_output.get("status"),
                        "generated_text": generated_text,
                        "error": llm_output.get("error"),
                    }
                    return repaired_output
        if not should_fallback:
            return llm_output

        fallback_target = cls._resolve_qwen_fallback_target(ctx.project_root)
        if not fallback_target:
            return llm_output

        fallback_reason = "qwen_quality_regression"
        fallback_output = await cls._execute_fallback_executor(
            fallback_executor_type=fallback_target,
            selected_profile=selected_profile,
            step=step,
            ctx=ctx,
            input_data=input_data,
            workflow_id=workflow_id,
            execution_id=execution_id,
        )
        if not fallback_output:
            return llm_output

        fallback_output["fallback_triggered"] = True
        fallback_output["fallback_from"] = "qwen_chat"
        fallback_output["fallback_to"] = fallback_target
        fallback_output["fallback_reason"] = fallback_reason
        fallback_output["fallback_source_output"] = {
            "status": llm_output.get("status"),
            "generated_text": generated_text,
            "error": llm_output.get("error"),
        }
        return fallback_output

    async def _recover_llm_contract_mismatch(
        self,
        *,
        executor_type: str,
        executor: Any,
        step,
        ctx: RunnerContext,
        workflow_id: str,
        execution_id: str,
        input_data: Dict[str, Any],
        selected_profile: str,
        generated_text: str,
        business_output: Any,
        structured_payload: Any,
        validation_result: Any,
    ) -> Optional[Dict[str, Any]]:
        if self._is_coding_executor(executor_type):
            return None
        if validation_result is None or validation_result.passed:
            return None

        error_msg = (
            f"Output schema validation failed: "
            f"{validation_result.errors[0].message if validation_result.errors else 'unknown'}"
        )
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
                repaired_output = dict(repaired["output"])
                repaired_output["contract_repair_retry"] = True
                repaired_output["schema_repair_retry"] = True
                if self._is_qwen_chat_executor(executor_type):
                    repaired_output["qwen_contract_repair"] = True
                return {
                    "output": repaired_output,
                    "business_output": repaired["business_output"],
                    "structured_payload": repaired["structured_payload"],
                    "generated_text": repaired_output.get("generated_text", generated_text),
                    "validation_result": repaired_validation,
                }

        if not self._is_qwen_chat_executor(executor_type):
            return None

        fallback_target = self._resolve_qwen_fallback_target(ctx.project_root)
        if not fallback_target:
            return None

        fallback_output = await self._execute_fallback_executor(
            fallback_executor_type=fallback_target,
            selected_profile=selected_profile,
            step=step,
            ctx=ctx,
            input_data=input_data,
            workflow_id=workflow_id,
            execution_id=execution_id,
        )
        if not fallback_output:
            return None

        fallback_generated_text = fallback_output.get("generated_text", "") or ""
        fallback_structured_payload = self._parse_structured_output_if_possible(fallback_generated_text)
        fallback_business_output = self._extract_business_output_payload(
            fallback_structured_payload,
            fallback_generated_text,
            step=step,
            written_files=[],
        )
        fallback_business_output, fallback_structured_payload = self._normalize_business_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=fallback_business_output,
            structured_payload=fallback_structured_payload,
            instance_data=None,
        )
        fallback_validation = self._validate_step_output(step, fallback_business_output)
        if fallback_validation and not fallback_validation.passed:
            return None

        fallback_output = dict(fallback_output)
        fallback_output["fallback_triggered"] = True
        fallback_output["fallback_from"] = "qwen_chat"
        fallback_output["fallback_to"] = fallback_target
        fallback_output["fallback_reason"] = "qwen_contract_validation_failed"
        fallback_output["fallback_source_output"] = {
            "generated_text": generated_text,
            "business_output": business_output,
            "validation_result": validation_result.to_dict() if hasattr(validation_result, "to_dict") else None,
        }
        return {
            "output": fallback_output,
            "business_output": fallback_business_output,
            "structured_payload": fallback_structured_payload,
            "generated_text": fallback_generated_text,
            "validation_result": fallback_validation,
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

    @staticmethod
    def _parse_coverage_percentage(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip().rstrip("%")
            try:
                return float(text)
            except ValueError:
                return None
        return None

    @classmethod
    def _evaluate_backend_coverage_gate(
        cls,
        step,
        business_output: Any,
    ) -> Optional[Dict[str, Any]]:
        step_config = getattr(step, "config", {}) or {}
        threshold = step_config.get("coverage_threshold")
        retry_target = step_config.get("coverage_retry_target")
        if threshold is None or not isinstance(business_output, dict):
            return None

        actual = cls._parse_coverage_percentage(
            business_output.get("coverage_actual")
            or business_output.get("coverage")
            or business_output.get("coverage_percent")
        )
        if actual is None:
            return {
                "passed": False,
                "message": "Coverage gate output missing numeric coverage_actual.",
                "retry_target": retry_target,
            }

        passed = actual >= float(threshold)
        return {
            "passed": passed,
            "actual": actual,
            "threshold": float(threshold),
            "message": (
                f"Coverage gate failed: actual {actual:.1f}% < required {float(threshold):.1f}%."
                if not passed else None
            ),
            "retry_target": retry_target,
        }

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
            # 支持 kimi 和 claude_code 配置键
            code_config = {}
            if step.config:
                code_config = step.config.get("kimi", {}) or step.config.get("claude_code", {})
            workspace = ctx.resolve_workdir(step, instance.data.get("run_id", workflow_id))
            context_files = self._merge_context_files(
                self._collect_authoritative_context_files(step, instance.data),
                code_config.get("context_files", []),
            )
            input_data: Dict[str, Any] = {
                "goal": agent_ctx.user_prompt or code_config.get("goal", ""),
                "workspace": workspace,
                "context_files": context_files,
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
            input_data.update(build_code_executor_io_config(
                workspace=workspace,
                workflow_id=workflow_id,
                step_id=step.id,
                step=step,
                configured_write_scope=code_config.get("write_scope", []),
                project_root=ctx.project_root,
            ))
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
            if self._is_qwen_chat_executor(executor_type):
                input_data = self._adapt_qwen_input_data(input_data)

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
            LLMRunner._append_context_files(group, merged)
        return merged

    @classmethod
    def _append_context_files(cls, value: Any, collected: List[str]) -> None:
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return
            if normalized.startswith("[") and normalized.endswith("]"):
                try:
                    parsed = yaml.safe_load(normalized)
                except Exception:
                    parsed = None
                if isinstance(parsed, (list, tuple, set)):
                    for item in parsed:
                        cls._append_context_files(item, collected)
                    return
            if normalized not in collected:
                collected.append(normalized)
            return

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
                cls._append_context_files(nested, collected)
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                cls._append_context_files(item, collected)

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
                    cls._append_context_files(raw_path, collected)
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
                or ("qwen" if self._is_qwen_chat_executor(executor_type) else None)
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
            llm_output = await self._maybe_fallback_qwen_output(
                executor_type=executor_type,
                executor=executor,
                step=step,
                ctx=ctx,
                instance=instance,
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data=input_data,
                llm_output=llm_output,
                selected_profile=selected_profile,
            )

            # 检查 LLM 调用是否成功
            # 审批 agent 特殊状态处理：审批决策（如 CONDITIONAL_APPROVED）不应视为任务执行失败
            llm_status = llm_output.get("status")
            agent_id = getattr(step, "agent_id", "") or ""
            is_approval_agent = agent_id.startswith("agent.governance.approval_")

            if is_approval_agent and llm_status in ("fail", "failed"):
                # 检查审批决策字段，如果是通过状态则视为成功
                approval_decision = (
                    llm_output.get("approval_decision")
                    or llm_output.get("审批决策")
                    or llm_output.get("decision")
                )
                if approval_decision:
                    decision_str = str(approval_decision).upper()
                    # 审批通过状态映射（包括条件批准的各种变体）
                    approval_states = {
                        "APPROVED",
                        "APPROVE",
                        "CONDITIONAL_APPROVED",
                        "CONDITIONALLY_APPROVED",
                        "PASS",
                        "PASSED",
                        "SUCCESS",
                        "OK",
                        "APPROVED_WITH_RECOMMENDATIONS",
                        "APPROVED_WITH_NOTES",
                        "APPROVED_WITH_CONDITIONS",
                    }
                    if decision_str in approval_states:
                        # 审批通过，任务执行成功
                        llm_output["execution_status"] = "success"
                        llm_output["approval_decision"] = approval_decision
                        llm_status = "success"  # 覆盖状态

            if llm_status in ("fail", "failed"):
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
            changed_files = llm_output.get("changed_files", [])
            resolved_changed_files = self._resolve_changed_file_paths(workspace=input_data.get("workspace", ctx.project_root), project_root=ctx.project_root, changed_files=changed_files) if changed_files else []
            write_scope_error = validate_code_executor_write_scope(changed_files=resolved_changed_files, project_root=ctx.project_root, write_scope=input_data.get("write_scope"))
            if write_scope_error:
                return await fail_code_executor_scope_violation(ctx=ctx, workflow_id=workflow_id, step=step, execution_id=execution_id, message=write_scope_error, output_data=llm_output)
            declared_output_error = self._detect_forbidden_template_write_paths(
                paths=[
                    str(getattr(output, "path", None) or output.get("path"))
                    for output in (step.outputs or [])
                    if (
                        (isinstance(output, dict) and output.get("path"))
                        or getattr(output, "path", None)
                    )
                ],
                project_root=ctx.project_root,
            )
            if declared_output_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, declared_output_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=declared_output_error,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=declared_output_error,
                )

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

            declared_output_error = self._validate_declared_output_files(
                step=step,
                project_root=ctx.project_root,
                written_files=written_files,
            )
            if declared_output_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, declared_output_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "written_files": written_files,
                        "structured_payload": structured_payload,
                    },
                    error_message=declared_output_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=declared_output_error,
                )

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
            qwen_contract_recovery = await self._recover_llm_contract_mismatch(
                executor_type=executor_type,
                executor=executor,
                step=step,
                ctx=ctx,
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data=input_data,
                selected_profile=selected_profile,
                generated_text=generated_text,
                business_output=business_output,
                structured_payload=structured_payload,
                validation_result=validation_result,
            )
            if qwen_contract_recovery:
                llm_output = qwen_contract_recovery["output"]
                business_output = qwen_contract_recovery["business_output"]
                structured_payload = qwen_contract_recovery["structured_payload"]
                generated_text = qwen_contract_recovery["generated_text"]
                validation_result = qwen_contract_recovery["validation_result"]

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

            coverage_gate = self._evaluate_backend_coverage_gate(step, business_output)
            if coverage_gate and not coverage_gate["passed"]:
                retry_target = coverage_gate.get("retry_target") or "write_ut"
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "business_output": business_output,
                        "coverage_gate": coverage_gate,
                    },
                    error_message=coverage_gate["message"],
                    completed_at=datetime.now(),
                )
                return await ctx.state_machine.rewind_to(
                    workflow_id,
                    retry_target,
                    mode="retry",
                    reason=coverage_gate["message"],
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
                business_output, structured_payload = self._synchronize_business_identity_from_materialized_ssot(
                    business_output=business_output,
                    structured_payload=structured_payload,
                    ssot_materialized=ssot_materialized,
                )

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
            for key in (
                "contract_repair_retry",
                "schema_repair_retry",
                "qwen_contract_repair",
                "qwen_repair_retry",
                "fallback_triggered",
                "fallback_from",
                "fallback_to",
                "fallback_reason",
                "fallback_source_output",
                "qwen_initial_output",
            ):
                if key in llm_output:
                    output_data[key] = llm_output[key]
            output_data.update(
                self._extract_declared_output_values(
                    step=step,
                    written_files=written_files,
                    project_root=ctx.project_root,
                    generated_text=generated_text,
                )
            )
            if isinstance(business_output, dict):
                output_data["business_output"] = business_output
            if isinstance(structured_payload, dict):
                output_data["structured_payload"] = structured_payload
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
        formal_output_specs = (
            getattr(self, "_resolve_formal_ssot_output_specs", None)
            or LLMRunner._resolve_formal_ssot_output_specs
        )(step)
        validate_only = formal_output_specs == []

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
            if formal_output_specs is not None:
                return None
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
                if formal_output_specs is not None:
                    return None
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
            if formal_output_specs is not None:
                return None
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
            if validate_only:
                materializer.validate_contract(contract_data)
                return None
            outputs = materializer.materialize(contract_data)
        except Exception as exc:
            strict = (step.config or {}).get("strict_output_validation", False)
            if strict:
                raise
            print(f"[SSOTContract] Warning: Step {step.id} SSOT materialization failed: {exc}")
            if formal_output_specs is not None:
                return None
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
    def _resolve_formal_ssot_output_specs(step) -> Optional[List[Any]]:
        outputs = getattr(step, "outputs", None)
        if not outputs:
            return None

        return [
            output_spec
            for output_spec in outputs
            if bool(getattr(output_spec, "freeze", False))
        ]

    @classmethod
    def _validate_declared_output_files(
        cls,
        *,
        step,
        project_root: Optional[str],
        written_files: Optional[List[str]] = None,
    ) -> Optional[str]:
        declared_paths: List[str] = []
        missing_paths: List[str] = []
        base_dir = Path(project_root or ".").resolve()
        normalized_written: set[str] = set()
        for path in written_files or []:
            if not isinstance(path, str) or not path.strip():
                continue
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = (base_dir / candidate).resolve()
            else:
                candidate = candidate.resolve()
            normalized_written.add(str(candidate))

        for output_spec in getattr(step, "outputs", []) or []:
            output_type = getattr(output_spec, "type", None)
            if output_type and str(output_type).lower() == "symbol":
                continue
            raw_path = getattr(output_spec, "path", None)
            if not raw_path:
                continue
            normalized_path = str(raw_path).strip()
            if not normalized_path:
                continue
            if "{" in normalized_path or "}" in normalized_path:
                continue

            candidate = Path(normalized_path)
            if not candidate.is_absolute():
                candidate = (base_dir / candidate).resolve()
            declared_paths.append(str(candidate))

            if not candidate.exists() and str(candidate) not in normalized_written:
                missing_paths.append(str(candidate))

        forbidden_write_error = cls._detect_forbidden_template_write_paths(
            paths=declared_paths,
            project_root=project_root,
        )
        if forbidden_write_error:
            return forbidden_write_error
        if missing_paths:
            return f"Missing declared output file(s): {', '.join(missing_paths)}"
        return None

    @staticmethod
    def _synchronize_business_identity_from_materialized_ssot(
        *,
        business_output: Any,
        structured_payload: Any,
        ssot_materialized: Optional[Dict[str, Any]],
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict) or not isinstance(ssot_materialized, dict):
            return business_output, structured_payload

        outputs = ssot_materialized.get("outputs")
        if not isinstance(outputs, dict):
            return business_output, structured_payload

        epic_id = None
        for item in outputs.values():
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("id") or "").strip()
            if candidate_id.startswith("EPIC-"):
                epic_id = candidate_id
                break

        if not epic_id:
            return business_output, structured_payload

        normalized_business = dict(business_output)
        normalized_business["epic_id"] = epic_id
        normalized_business["epic_ref"] = epic_id

        if not isinstance(structured_payload, dict):
            return normalized_business, structured_payload

        normalized_structured = dict(structured_payload)
        structured_business = (
            dict(normalized_structured.get("business_output"))
            if isinstance(normalized_structured.get("business_output"), dict)
            else {}
        )
        structured_business["epic_id"] = epic_id
        structured_business["epic_ref"] = epic_id
        normalized_structured["business_output"] = structured_business
        return normalized_business, normalized_structured

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
            parent = output.get("parent")
            if isinstance(parent, str) and parent.upper().startswith("FEAT-"):
                raw_verifies = output.get("verifies")
                if isinstance(raw_verifies, list):
                    repaired_verifies = []
                    for value in raw_verifies:
                        if isinstance(value, str) and value.strip().lower() == "feat":
                            repaired_verifies.append(parent)
                        else:
                            repaired_verifies.append(value)
                    output["verifies"] = repaired_verifies
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
    def _extract_step_business_candidate(step_output: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(step_output, dict):
            return None

        direct_business = step_output.get("business_output")
        if isinstance(direct_business, dict):
            return direct_business

        structured_payload = step_output.get("structured_payload")
        if isinstance(structured_payload, dict):
            nested_business = structured_payload.get("business_output")
            if isinstance(nested_business, dict):
                return nested_business
            for key, value in structured_payload.items():
                if (
                    isinstance(key, str)
                    and key != "business_output"
                    and "business_output" in key.lower()
                    and isinstance(value, dict)
                ):
                    return value

        for key, value in step_output.items():
            if (
                isinstance(key, str)
                and key != "business_output"
                and "business_output" in key.lower()
                and isinstance(value, dict)
            ):
                return value

        for text_field in ("generated_text", "raw_output"):
            text_value = step_output.get(text_field)
            if not isinstance(text_value, str) or not text_value.strip():
                continue
            parsed = LLMRunner._parse_structured_output_if_possible(text_value)
            if not isinstance(parsed, dict):
                anchor_match = re.search(
                    r'(?s)\{\s*"(business_output|ssot_output_contract|review_id|review_type|parent_epic|epic_ref|source_feats)"\s*:',
                    text_value,
                )
                first_brace = anchor_match.start() if anchor_match else text_value.find("{")
                last_brace = text_value.rfind("}")
                if 0 <= first_brace < last_brace:
                    parsed = LLMRunner._parse_structured_output_if_possible(
                        text_value[first_brace : last_brace + 1]
                    )
            if isinstance(parsed, dict):
                nested_business = parsed.get("business_output")
                if isinstance(nested_business, dict):
                    return nested_business
                return parsed

        return step_output

    @staticmethod
    def _is_valid_feat_bundle_payload(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        feat_specs = payload.get("feat_specs")
        if not isinstance(feat_specs, list) or not feat_specs:
            return False
        valid_count = 0
        for item in feat_specs:
            if not isinstance(item, dict):
                continue
            feat_id = str(item.get("feat_id") or "").strip()
            title = str(item.get("title") or "").strip()
            has_embedded_noise = any(
                isinstance(key, str)
                and key != "business_output"
                and "business_output" in key.lower()
                for key in item.keys()
            )
            if feat_id and title and not has_embedded_noise:
                valid_count += 1
        return valid_count > 0

    @staticmethod
    def _is_valid_epic_payload(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        epic_id = str(payload.get("epic_id") or "").strip()
        title = str(payload.get("title") or "").strip()
        goal = str(payload.get("goal") or "").strip()
        return bool((epic_id or title) and goal)

    @staticmethod
    def _feat_bundle_quality(payload: Any) -> tuple[int, int, int]:
        if not isinstance(payload, dict):
            return (-1, -1, 0)
        feat_specs = payload.get("feat_specs")
        if not isinstance(feat_specs, list):
            return (-1, -1, 0)

        valid_count = 0
        noise_count = 0
        for item in feat_specs:
            if not isinstance(item, dict):
                continue
            feat_id = str(item.get("feat_id") or "").strip()
            title = str(item.get("title") or "").strip()
            has_embedded_noise = any(
                isinstance(key, str)
                and key != "business_output"
                and "business_output" in key.lower()
                for key in item.keys()
            )
            if has_embedded_noise:
                noise_count += 1
            if feat_id and title and not has_embedded_noise:
                valid_count += 1

        return (valid_count, len(feat_specs), -noise_count)

    @staticmethod
    def _normalize_approval_reviewer_handoff_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.governance.approval_reviewer":
            return business_output, structured_payload
        if not isinstance(instance_data, dict):
            return business_output, structured_payload

        step_id = str(getattr(step, "id", "") or "").strip()
        current_candidate = (
            business_output
            if isinstance(business_output, dict)
            else LLMRunner._extract_step_business_candidate(
                {"structured_payload": structured_payload}
            )
        )

        handoff_plan = {
            "epic_identity_prepare": {
                "upstream_steps": ("epic_design",),
                "validator": LLMRunner._is_valid_epic_payload,
            },
            "epic_identity_formalize": {
                "upstream_steps": ("epic_identity_prepare", "epic_design"),
                "validator": LLMRunner._is_valid_epic_payload,
            },
            "feat_identity_prepare": {
                "upstream_steps": ("feat_spec_generation",),
                "validator": LLMRunner._is_valid_feat_bundle_payload,
            },
            "feat_identity_formalize": {
                "upstream_steps": ("feat_identity_prepare", "feat_spec_generation"),
                "validator": LLMRunner._is_valid_feat_bundle_payload,
            },
        }
        plan = handoff_plan.get(step_id)
        if not plan:
            return business_output, structured_payload

        validator = plan["validator"]
        if validator(current_candidate):
            normalized_structured = LLMRunner._ensure_structured_envelope(
                business_output=current_candidate,
                structured_payload=structured_payload,
            )
            return current_candidate, normalized_structured

        step_outputs = instance_data.get("step_outputs", {})
        if not isinstance(step_outputs, dict):
            return business_output, structured_payload

        for upstream_step in plan["upstream_steps"]:
            upstream_payload = LLMRunner._extract_step_business_candidate(
                step_outputs.get(upstream_step)
            )
            if validator(upstream_payload):
                normalized_structured = LLMRunner._ensure_structured_envelope(
                    business_output=upstream_payload,
                    structured_payload=structured_payload,
                )
                return upstream_payload, normalized_structured

        return business_output, structured_payload

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
            raw_outputs = _normalize_string_list(
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
            outputs = refine_feat_outputs(
                raw_outputs,
                title=title,
                goal=goal,
                acceptance_criteria=acceptance_criteria,
                processing=processing,
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

            input_contract = _normalize_input_contract(
                candidate.get("input_contract"),
                inputs=inputs,
                source_refs=source_refs,
                epic_ref=normalized_epic_ref,
            )
            input_contract["required_artifacts"] = align_required_artifacts(
                input_contract.get("required_artifacts") or [],
                non_goals,
            )
            inputs = align_inputs_with_required_artifacts(
                inputs,
                input_contract.get("required_artifacts") or [],
            )

            synthesized = {
                "feat_id": feat_id,
                "title": title,
                "goal": goal,
                "user_value": user_value,
                "inputs": inputs,
                "input_contract": input_contract,
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
            synthesized["acceptance_checks"] = refine_acceptance_checks(
                _build_acceptance_checks(synthesized, acceptance_criteria),
                title=title,
                goal=goal,
                outputs=outputs,
                processing=processing,
                derived_object_expectations=synthesized.get("derived_object_expectations"),
            )
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
            raw_outputs = _normalize_string_list(
                normalized_feat.get("outputs")
                or normalized_feat.get("output")
                or normalized_feat.get("acceptance_boundary"),
                fallback=[f"{title} FEAT specification"],
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
            normalized_feat["input_contract"]["required_artifacts"] = align_required_artifacts(
                normalized_feat["input_contract"].get("required_artifacts") or [],
                normalized_feat.get("non_goals") or [],
            )
            normalized_feat["inputs"] = _truncate_list(
                align_inputs_with_required_artifacts(
                    normalized_feat.get("inputs") or [],
                    normalized_feat["input_contract"].get("required_artifacts") or [],
                ),
                5,
            )
            normalized_feat["outputs"] = _truncate_list(
                refine_feat_outputs(
                    raw_outputs,
                    title=title,
                    goal=goal,
                    acceptance_criteria=normalized_feat.get("acceptance_criteria") or [],
                    processing=normalized_feat.get("processing") or [],
                ),
                5,
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
            normalized_feat["acceptance_checks"] = refine_acceptance_checks(
                _build_acceptance_checks(
                    normalized_feat,
                    normalized_feat.get("acceptance_criteria") or [],
                ),
                title=title,
                goal=goal,
                outputs=normalized_feat.get("outputs") or [],
                processing=normalized_feat.get("processing") or [],
                derived_object_expectations=normalized_feat.get("derived_object_expectations"),
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
        structured_business = (
            structured_payload.get("business_output")
            if isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
            else {}
        )
        if expects_bundle and structured_business:
            current_quality = LLMRunner._feat_bundle_quality(normalized_business)
            structured_quality = LLMRunner._feat_bundle_quality(structured_business)
            if structured_quality > current_quality:
                normalized_business = dict(structured_business)

        bundle_specs = normalized_business.get("feat_specs")
        if isinstance(bundle_specs, list):
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

    _detect_forbidden_template_write_paths = staticmethod(
        detect_forbidden_template_write_paths
    )

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
        business_output, structured_payload = LLMRunner._normalize_problem_definition_payload(
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
        business_output, structured_payload = LLMRunner._normalize_approval_reviewer_handoff_payload(
            step=step,
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
    def _normalize_problem_definition_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        agent_id = getattr(step, "agent_id", "") or ""
        step_id = getattr(step, "id", "") or ""
        if step_id != "problem_alignment" and agent_id != "agent.product.requirement_alignment":
            return business_output, structured_payload

        def _normalize_list(value: Any) -> List[str]:
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        normalized_business = dict(business_output)
        if not str(normalized_business.get("problem_statement") or "").strip():
            for candidate_key in ("summary", "description", "essence"):
                candidate = str(normalized_business.get(candidate_key) or "").strip()
                if candidate:
                    normalized_business["problem_statement"] = candidate
                    break
        if not _normalize_list(normalized_business.get("target_users")):
            for candidate_key in ("target_user", "stakeholders", "users"):
                values = _normalize_list(normalized_business.get(candidate_key))
                if values:
                    normalized_business["target_users"] = values
                    break
        if not _normalize_list(normalized_business.get("scenarios")):
            for candidate_key in ("findings", "use_cases", "situations"):
                values = _normalize_list(normalized_business.get(candidate_key))
                if values:
                    normalized_business["scenarios"] = values
                    break
        if not _normalize_list(normalized_business.get("non_goals")):
            for candidate_key in ("out_of_scope", "non_goal_items", "excluded_scope"):
                values = _normalize_list(normalized_business.get(candidate_key))
                if values:
                    normalized_business["non_goals"] = values
                    break
        if not _normalize_list(normalized_business.get("constraints")):
            for candidate_key in ("risks", "risk_notes", "assumptions"):
                values = _normalize_list(normalized_business.get(candidate_key))
                if values:
                    normalized_business["constraints"] = values
                    break

        normalized_target_users = _normalize_list(normalized_business.get("target_users"))
        if normalized_target_users:
            normalized_business["target_users"] = normalized_target_users
        normalized_scenarios = _normalize_list(normalized_business.get("scenarios"))
        if normalized_scenarios:
            normalized_business["scenarios"] = normalized_scenarios
        normalized_non_goals = _normalize_list(normalized_business.get("non_goals"))
        if normalized_non_goals:
            normalized_business["non_goals"] = normalized_non_goals
        normalized_constraints = _normalize_list(normalized_business.get("constraints"))
        if normalized_constraints:
            normalized_business["constraints"] = normalized_constraints

        if isinstance(structured_payload, dict):
            normalized_structured = dict(structured_payload)
            if isinstance(normalized_structured.get("business_output"), dict):
                normalized_structured["business_output"] = normalized_business
            return normalized_business, normalized_structured
        return normalized_business, structured_payload

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
        agent_id = getattr(step, "agent_id", "") or ""
        if (
            agent_id == "agent.product.feat_reviewer"
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
        elif (
            agent_id == "agent.product.epic_reviewer"
            and normalized_business.get("review_type") is None
        ):
            normalized_business["review_type"] = "epic_review"

        if normalized_business.get("review_type") == "epic_review":
            normalized_business = LLMRunner._normalize_epic_review_legacy_payload(
                normalized_business,
                instance_data=instance_data,
            )

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
        elif review_type == "feat_review":
            expected_subject_refs = LLMRunner._expected_feat_review_subject_refs(
                instance_data or {},
            )
            actual_subject_refs = normalized_business.get("subject_refs")
            actual_subject_ref_set = {
                str(item).strip()
                for item in actual_subject_refs
                if isinstance(actual_subject_refs, list) and str(item).strip()
            }
            expected_subject_ref_set = {
                str(item).strip()
                for item in expected_subject_refs
                if isinstance(item, str) and item.strip()
            }
            if expected_subject_ref_set and not expected_subject_ref_set.issubset(actual_subject_ref_set):
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

        if review_type == "feat_review":
            normalized_business = LLMRunner._sanitize_feat_review_payload(
                review_payload=normalized_business,
                instance_data=instance_data,
            )
        elif review_type == "delivery_plan_review":
            normalized_business = LLMRunner._sanitize_delivery_plan_review_payload(
                review_payload=normalized_business,
                instance_data=instance_data,
            )

        normalized_structured = structured_payload
        if (
            isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
        ):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business
        elif isinstance(structured_payload, dict) and structured_payload.get("review_type") == review_type:
            normalized_structured = {**dict(structured_payload), **normalized_business}

        return normalized_business, normalized_structured

    @staticmethod
    def _normalize_epic_review_legacy_payload(
        review_payload: Dict[str, Any],
        *,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = dict(review_payload)

        epic_ref = (
            str(normalized.get("epic_id") or "").strip()
            or str(normalized.get("epic_ref") or "").strip()
            or str(LLMRunner._resolve_epic_ref_from_instance_data(instance_data) or "").strip()
        )
        if epic_ref:
            normalized["subject_refs"] = [epic_ref]

        if not str(normalized.get("review_id") or "").strip():
            normalized["review_id"] = f"RVW-{epic_ref}" if epic_ref else "RVW-EPIC-001"

        if normalized.get("decision") not in {"pass", "revise", "reject"}:
            status_candidate = str(
                normalized.get("review_status")
                or normalized.get("status")
                or normalized.get("approval_decision")
                or ""
            ).strip().lower()
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
                "changes_requested": "revise",
                "reject": "reject",
                "rejected": "reject",
                "fail": "reject",
                "failed": "reject",
            }
            decision = decision_map.get(status_candidate)
            if decision:
                normalized["decision"] = decision

        observations = normalized.get("observations")
        if not isinstance(normalized.get("findings"), list) and isinstance(observations, list):
            normalized["findings"] = [
                str(item).strip() for item in observations if str(item).strip()
            ]

        recommendations = normalized.get("recommendations")
        if not isinstance(recommendations, list):
            if isinstance(recommendations, str) and recommendations.strip():
                normalized["recommendations"] = [recommendations.strip()]
            else:
                normalized["recommendations"] = []

        if not isinstance(normalized.get("risks"), list):
            normalized["risks"] = []

        if not str(normalized.get("summary") or "").strip():
            title = str(normalized.get("title") or "").strip()
            findings = normalized.get("findings") if isinstance(normalized.get("findings"), list) else []
            if title and normalized.get("decision") == "pass":
                normalized["summary"] = (
                    f"EPIC {title} passed structure, boundary, and split readiness review."
                )
            elif findings:
                normalized["summary"] = str(findings[0]).strip()
            elif epic_ref:
                normalized["summary"] = f"{epic_ref} review completed."
            else:
                normalized["summary"] = "EPIC review completed."

        return normalized

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
            repaired_input["structured_output_only"] = True
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

    @staticmethod
    def _expected_delivery_plan_subject_refs(
        instance_data: Optional[Dict[str, Any]],
        business_output: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        return ReviewSemanticValidator.expected_delivery_plan_subject_refs(
            runner_cls=LLMRunner,
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
        if not isinstance(instance_data, dict):
            return None
        step_outputs = instance_data.get("step_outputs")
        if not isinstance(step_outputs, dict):
            return None

        for step_id in ("task_plan", "task_planning"):
            candidate = step_outputs.get(step_id)
            if not isinstance(candidate, dict):
                continue
            extracted = cls._extract_step_business_candidate(candidate)
            if isinstance(extracted, dict) and (
                isinstance(extracted.get("task_specs"), list)
                or isinstance(extracted.get("task_hierarchy"), list)
                or isinstance(extracted.get("task_planning"), dict)
            ):
                return extracted
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
            task_kind = cls._review_clean_text(task_spec.get("task_kind")).lower()
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
    def _delivery_plan_has_authoritative_plan_shape(
        cls,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        milestones = task_plan.get("milestones")
        dependency_graph = task_plan.get("dependency_graph")
        resource_allocation = task_plan.get("resource_allocation")
        return (
            isinstance(milestones, list)
            and bool(milestones)
            and isinstance(dependency_graph, dict)
            and bool(dependency_graph)
            and isinstance(resource_allocation, dict)
            and bool(resource_allocation)
        )

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
            r"均具备",
            r"完整的",
            r"字段$",
            r"清晰",
            r"完整$",
            r"支持",
            r"明确",
            r"已正确映射",
            r"已映射到",
            r"一致$",
        ]
        return any(re.search(pattern, lowered) for pattern in positive_patterns)

    @classmethod
    def _load_feat_bundle_business_output(
        cls,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(instance_data, dict):
            return None
        step_outputs = instance_data.get("step_outputs")
        if not isinstance(step_outputs, dict):
            return None

        for step_id in ("feat_scoped_specs", "feat_identity_prepare", "feat_spec_generation"):
            candidate = cls._extract_step_business_candidate(step_outputs.get(step_id))
            if cls._is_valid_feat_bundle_payload(candidate):
                return candidate
        return None

    @staticmethod
    def _feat_bundle_has_structural_minimum(bundle: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(bundle, dict):
            return False
        feat_specs = bundle.get("feat_specs")
        if not isinstance(feat_specs, list) or not feat_specs:
            return False

        placeholder_pattern = re.compile(
            r"(inputs defined by epic scope|same as epic|\btbd\b|to be defined|待补充|待定义|同 epic)",
            re.IGNORECASE,
        )
        for feat_item in feat_specs:
            if not isinstance(feat_item, dict):
                return False
            required_scalar_fields = ("feat_id", "title", "goal", "user_value")
            if any(not str(feat_item.get(field) or "").strip() for field in required_scalar_fields):
                return False

            for field_name in ("inputs", "processing", "outputs", "acceptance_criteria"):
                values = feat_item.get(field_name)
                if not isinstance(values, list) or not values:
                    return False
                normalized_values = [str(item).strip() for item in values if str(item).strip()]
                if not normalized_values:
                    return False
                if field_name == "inputs" and any(placeholder_pattern.search(item) for item in normalized_values):
                    return False

            input_contract = feat_item.get("input_contract")
            if not isinstance(input_contract, dict):
                return False
            for key in ("required_artifacts", "required_fields", "consumption_rules"):
                values = input_contract.get(key)
                if not isinstance(values, list) or not any(str(item).strip() for item in values):
                    return False

            acceptance_checks = feat_item.get("acceptance_checks")
            if not isinstance(acceptance_checks, list) or not acceptance_checks:
                return False
            for check in acceptance_checks:
                if not isinstance(check, dict):
                    return False
                for key in ("id", "scenario", "given", "when", "then"):
                    if not str(check.get(key) or "").strip():
                        return False
                trace_hints = check.get("trace_hints")
                if not isinstance(trace_hints, list) or not any(str(item).strip() for item in trace_hints):
                    return False

            ssot = feat_item.get("ssot")
            if not isinstance(ssot, dict) or not str(ssot.get("parent") or "").strip():
                return False
        return True

    @classmethod
    def _sanitize_feat_review_payload(
        cls,
        *,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        sanitized = dict(review_payload)
        feat_bundle = cls._load_feat_bundle_business_output(instance_data)
        if not cls._feat_bundle_has_structural_minimum(feat_bundle):
            return sanitized

        soft_blocker_patterns = [
            r"抽象标签",
            r"仍不足以直接指导下游实现",
            r"尚未把.*落到可执行粒度",
            r"结构关系.*未冻结",
            r"最小字段清单",
            r"repo_context.*边界",
            r"正式枚举边界",
            r"当前仍像高层提纲",
            r"未具体化",
            r"不够具体",
            r"难以直接生成校验逻辑",
            r"trace_hints.*抽象",
            r"trace_hints.*没有指向",
            r"未冻结.*正式枚举",
            r"未冻结.*允许组合矩阵",
            r"未冻结.*映射表",
            r"未把.*字段级必填性.*冻结为可实现契约",
            r"对正式边界动作仅给出示例集合",
            r"未说明未来新增正式动作的纳入规则",
            r"未冻结每条链路的输出字段契约",
            r"decision_outcome.*正式结果枚举",
            r"trace_hints.*标签级别",
            r"trace_hints.*缺少 UI",
            r"trace_hints.*仅覆盖 TECH/TESTSET",
            r"缺少可直接派生下游对象的具体追踪锚点",
            r"形成新的治理分叉",
            r"缺少统一字段级契约",
            r"required_fields.*抽象口号",
            r"required_fields.*未定义其.*schema",
            r"required_fields.*未说明具体格式或内容边界",
        ]
        combined_pattern = re.compile("|".join(soft_blocker_patterns), re.IGNORECASE)
        governance_markers = [
            "purpose",
            "decision_mode",
            "旧分类",
            "legacy",
            "human_gate_context",
            "gate_result",
            "decision_outcome",
            "trace_hints",
            "list、show、decide",
            "list,show,decide",
            "输出字段契约",
            "校验矩阵",
        ]
        refinement_markers = [
            "未冻结",
            "未定义",
            "未体现",
            "未闭合",
            "缺失处理规则",
            "仍需自行补定义",
            "更像方向说明",
            "合法组合",
            "正式允许值",
            "输出格式",
            "回链规则",
            "不能稳定支撑",
            "无法直接产出一致",
            "字段名集合",
        ]
        hard_blocker_patterns = [
            r"占位式?\s*inputs?",
            r"占位值",
            r"\btbd\b",
            r"same as epic",
            r"inputs defined by epic scope",
            r"input_contract.*缺少",
            r"required_artifacts.*缺少",
            r"required_fields.*缺少",
            r"consumption_rules.*缺少",
            r"subject_refs?.*不一致",
            r"subject_refs?.*编造",
            r"替换为占位符",
            r"acceptance_checks?.*缺少",
            r"缺少 id/scenario/given/when/then/trace_hints",
        ]
        hard_blocker_pattern = re.compile("|".join(hard_blocker_patterns), re.IGNORECASE)

        def _is_soft_governance_refinement(text: str) -> bool:
            normalized = text.strip()
            if not normalized:
                return False
            lowered = normalized.lower()
            return (
                any(marker in normalized or marker in lowered for marker in governance_markers)
                and any(marker in normalized for marker in refinement_markers)
            )

        def _is_hard_blocker(text: str) -> bool:
            normalized = text.strip()
            return bool(normalized) and bool(hard_blocker_pattern.search(normalized))

        def _is_positive_observation(text: str) -> bool:
            normalized = text.strip()
            if not normalized:
                return False
            if cls._contains_feat_review_negative_signal(normalized):
                return False
            return cls._contains_feat_review_positive_signal(normalized)

        findings = [
            item.strip()
            for item in sanitized.get("findings") or []
            if isinstance(item, str) and item.strip()
        ]
        filtered_findings = [
            item for item in findings
            if not combined_pattern.search(item)
            and not _is_soft_governance_refinement(item)
            and not _is_positive_observation(item)
        ]
        sanitized["findings"] = filtered_findings

        sanitized["risks"] = [
            item.strip()
            for item in sanitized.get("risks") or []
            if isinstance(item, str)
            and item.strip()
            and not combined_pattern.search(item.strip())
            and not _is_soft_governance_refinement(item.strip())
            and not _is_positive_observation(item.strip())
        ]

        if (
            sanitized.get("decision") == "revise"
            and filtered_findings
            and all(not _is_hard_blocker(item) for item in filtered_findings)
        ):
            filtered_findings = []
            sanitized["findings"] = []
            sanitized["risks"] = []

        if sanitized.get("decision") == "revise" and not filtered_findings:
            sanitized["decision"] = "pass"
            subject_refs = [
                item.strip()
                for item in sanitized.get("subject_refs") or []
                if isinstance(item, str) and item.strip()
            ]
            subject_text = ", ".join(subject_refs) if subject_refs else "the reviewed FEAT bundle"
            sanitized["summary"] = (
                f"All reviewed FEATs satisfy the minimum structural requirements for downstream derivation: {subject_text}."
            )
        elif (
            sanitized.get("decision") == "pass"
            and not cls._contains_feat_review_negative_signal(sanitized.get("summary"))
            and not any(cls._contains_feat_review_negative_signal(item) for item in sanitized["findings"])
            and not any(cls._contains_feat_review_negative_signal(item) for item in sanitized["risks"])
        ):
            sanitized["findings"] = []
            sanitized["risks"] = []
        return sanitized

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
            r"\bincomplete\b",
            r"\bmissing\b",
            r"\bunclear\b",
            r"\binsufficient\b",
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
            r"不完整",
            r"缺少",
            r"不清晰",
            r"不足",
        ]
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _contains_feat_review_positive_signal(text: Any) -> bool:
        if not isinstance(text, str):
            return False
        normalized = text.strip().lower()
        if not normalized:
            return False

        patterns = [
            r"\ball\b.*\b(?:complete|defined|consistent|covered|present|valid)\b",
            r"\bcontains?\b.*\b(?:required|complete)\b",
            r"\bcovers?\b",
            r"\bdefined\b",
            r"\bconsistent\b",
            r"\bclear\b",
            r"\bcorrect(?:ly)?\b",
            r"\bcomplete\b",
            r"\bno ui\b",
            r"\bwithout ui\b",
            r"\btraceability\b.*\bcomplete\b",
            r"\bdependencies?\b.*\bclear\b",
            r"\brequired_fields\b.*\bconcrete\b",
            r"\binput_contract\b.*\bcomplete\b",
            r"\bconsumption_rules\b.*\bclear\b",
            r"\bnon_goals\b.*\bclear\b",
            r"\bderived_object_expectations\b.*\bconsistent\b",
            r"所有 .* 均包含",
            r"所有 .* 完整",
            r"所有 .* 统一",
            r"均覆盖",
            r"覆盖 .*tech/task/testset",
            r"无需 ui",
            r"无 ui",
            r"无 .*tbd",
            r"无 .*占位值",
            r"未使用 tbd",
            r"未使用 same as epic",
            r"具体输入物",
            r"具体输入",
            r"包含 .* 三要素",
            r"为具体字段名",
            r"明确说明",
            r"正确声明",
            r"正确指向",
            r"依赖图清晰",
            r"明确排除",
            r"统一指向",
            r"追溯链完整",
            r"预期一致",
            r"边界清晰",
            r"结构完整",
            r"可派生下游",
            r"优先级分层合理",
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
    _detect_forbidden_template_write_paths = staticmethod(
        LLMRunner._detect_forbidden_template_write_paths
    )
    _synchronize_business_identity_from_materialized_ssot = staticmethod(
        LLMRunner._synchronize_business_identity_from_materialized_ssot
    )
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
    _extract_primary_file_output = staticmethod(LLMRunner._extract_primary_file_output)
    _should_prefer_written_file_payload = staticmethod(LLMRunner._should_prefer_written_file_payload)
    _unwrap_business_output_candidate = staticmethod(LLMRunner._unwrap_business_output_candidate)
    _extract_best_written_file_payload = classmethod(LLMRunner._extract_best_written_file_payload.__func__)
    _extract_named_output_segment = staticmethod(LLMRunner._extract_named_output_segment)
    _coerce_ssot_contract_dict = staticmethod(LLMRunner._coerce_ssot_contract_dict)
    _normalize_ssot_contract_payload = staticmethod(LLMRunner._normalize_ssot_contract_payload)
    _resolve_formal_ssot_output_specs = staticmethod(LLMRunner._resolve_formal_ssot_output_specs)
    _append_context_files = classmethod(LLMRunner._append_context_files.__func__)
    _parse_structured_output_if_possible = staticmethod(LLMRunner._parse_structured_output_if_possible)
    _merge_context_files = staticmethod(LLMRunner._merge_context_files)
    _collect_authoritative_context_files = classmethod(LLMRunner._collect_authoritative_context_files.__func__)
    _resolve_authoritative_input_value = classmethod(LLMRunner._resolve_authoritative_input_value.__func__)
    _extract_context_file_paths = classmethod(LLMRunner._extract_context_file_paths.__func__)
    _merge_forbidden_read_paths = classmethod(LLMRunner._merge_forbidden_read_paths.__func__)
    _is_qwen_chat_executor = staticmethod(LLMRunner._is_qwen_chat_executor)
    _is_coding_executor = staticmethod(LLMRunner._is_coding_executor)
    _resolve_code_executor_candidates = classmethod(LLMRunner._resolve_code_executor_candidates.__func__)
    _resolve_code_executor_type = classmethod(LLMRunner._resolve_code_executor_type.__func__)
    _evaluate_backend_coverage_gate = classmethod(LLMRunner._evaluate_backend_coverage_gate.__func__)
    _parse_coverage_percentage = staticmethod(LLMRunner._parse_coverage_percentage)

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

        symbol_payload = cls._extract_declared_symbol_payload(step, structured_payload)
        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            business_output = structured_payload["business_output"]
        elif isinstance(structured_payload, dict) and not looks_like_executor_wrapper(structured_payload):
            business_output = structured_payload
        elif symbol_payload is not None:
            business_output = symbol_payload
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
    def _extract_declared_symbol_payload(cls, step, structured_payload: Any) -> Any:
        if not isinstance(structured_payload, dict):
            return None
        symbols = structured_payload.get("symbols")
        if not isinstance(symbols, dict):
            return None

        for output_spec in getattr(step, "outputs", []) or []:
            symbol = getattr(output_spec, "symbol", None)
            if symbol is None and isinstance(output_spec, dict):
                symbol = output_spec.get("symbol")
            if not isinstance(symbol, str) or not symbol.strip():
                continue
            candidate = symbols.get(symbol.strip())
            if candidate is None:
                continue
            if isinstance(candidate, str):
                parsed = cls._parse_structured_output_if_possible(candidate)
                return parsed if parsed is not None else candidate
            return candidate
        return None

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

    @classmethod
    def _validate_declared_output_files(
        cls,
        *,
        step,
        project_root: Optional[str],
    ) -> Optional[str]:
        declared_paths: List[str] = []
        missing_paths: List[str] = []
        base_dir = Path(project_root or ".").resolve()

        for output_spec in getattr(step, "outputs", []) or []:
            if isinstance(output_spec, dict):
                output_type = output_spec.get("type")
                raw_path = output_spec.get("path")
                required = output_spec.get("required", True)
            else:
                output_type = getattr(output_spec, "type", None)
                raw_path = getattr(output_spec, "path", None)
                required = getattr(output_spec, "required", True)

            if output_type == "symbol" or not raw_path or required is False:
                continue

            normalized_path = cls._normalize_project_relative_path(str(raw_path))
            candidate = Path(normalized_path)
            if not candidate.is_absolute():
                candidate = (base_dir / candidate).resolve()
            declared_paths.append(str(candidate))

            if not candidate.exists():
                missing_paths.append(str(candidate))

        forbidden_write_error = cls._detect_forbidden_template_write_paths(
            paths=declared_paths,
            project_root=project_root,
        )
        if forbidden_write_error:
            return forbidden_write_error
        if missing_paths:
            return f"Missing declared output file(s): {', '.join(missing_paths)}"
        return None

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "claude_code"

    @classmethod
    def _build_claude_code_input_data(
        cls,
        *,
        agent_ctx,
        step=None,
        claude_config: Dict[str, Any],
        workspace: str,
        workflow_id: str,
        step_id: str,
        context_files: List[str],
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        input_data = {
            "goal": agent_ctx.user_prompt or claude_config.get("goal", ""),
            "workspace": workspace,
            "context_files": context_files,
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
        input_data.update(build_code_executor_io_config(
            workspace=workspace,
            workflow_id=workflow_id,
            step_id=step_id,
            step=step,
            configured_write_scope=claude_config.get("write_scope", []),
            project_root=project_root,
        ))
        return input_data

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
        executor_type = self._resolve_code_executor_type(
            instance_data=instance.data,
            project_root=ctx.project_root,
        )

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

        if executor_type == "llm":
            input_data = self._build_llm_alias_input_data(agent_ctx=agent_ctx)
        else:
            input_data = self._build_claude_code_input_data(
                agent_ctx=agent_ctx,
                step=step,
                claude_config=claude_config,
                workspace=workspace,
                workflow_id=workflow_id,
                step_id=step.id,
                context_files=context_files,
                project_root=ctx.project_root,
            )

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

        if executor_type != "llm":
            run_id = instance.data.get("run_id", workflow_id)
            evidence_base = str(
                Path(workspace) / ".workflow" / "claude-code" / f"{run_id}-{step.id}"
            )
            input_data["evidence_base"] = evidence_base

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

        import logging
        logging.info(f"[ClaudeCodeRunner] Starting execution for step {step.id} (workflow={workflow_id}, execution={execution_id})")

        try:
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
            agent_id = getattr(step, "agent_id", "") or ""
            if agent_id.startswith("agent.governance.approval_"):
                approval_decision = (
                    output.get("approval_decision")
                    or output.get("审批决策")
                    or output.get("decision")
                )
                if approval_decision:
                    decision_str = str(approval_decision).upper()
                    if decision_str in ("APPROVED", "CONDITIONAL_APPROVED", "PASS", "SUCCESS"):
                        status = "success"
                        output["execution_status"] = "success"
                        output["approval_decision"] = approval_decision

            changed = output.get("changed_files", [])
            abs_changed = self._resolve_changed_file_paths(
                workspace=workspace,
                project_root=ctx.project_root,
                changed_files=changed,
            ) if changed else []
            forbidden_write_error = self._detect_forbidden_template_write_paths(
                paths=abs_changed,
                project_root=ctx.project_root,
            )
            if forbidden_write_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, forbidden_write_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=forbidden_write_error,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=forbidden_write_error,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=forbidden_write_error,
                    output=output,
                )
            write_scope_error = validate_code_executor_write_scope(changed_files=abs_changed, project_root=ctx.project_root, write_scope=input_data.get("write_scope"))
            if write_scope_error:
                return await fail_code_executor_scope_violation(ctx=ctx, workflow_id=workflow_id, step=step, execution_id=execution_id, message=write_scope_error, output_data=output, include_output=True)

            diff_summary = output.get("diff_summary", {})
            max_diff_files = claude_config.get("max_diff_files", 1000)
            if diff_summary.get("files_changed", 0) > max_diff_files:
                status = "needs_human"
                output["error"] = (
                    f"Diff too large: {diff_summary['files_changed']} files changed "
                    f"(limit: {max_diff_files})"
                )

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

            declared_output_error = self._validate_declared_output_files(
                step=step,
                project_root=ctx.project_root,
            )
            if declared_output_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, declared_output_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=declared_output_error,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=declared_output_error,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code declared outputs missing: {declared_output_error}",
                    output=output,
                )

            evidence_path = output.get("evidence_bundle_path", "")
            if evidence_path:
                await self._collect_evidence(ctx, workflow_id, step.id, [evidence_path])
            if changed:
                await self._collect_evidence(ctx, workflow_id, step.id, abs_changed)

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

            coverage_gate = self._evaluate_backend_coverage_gate(step, business_output)
            if coverage_gate and not coverage_gate["passed"]:
                retry_target = coverage_gate.get("retry_target") or "write_ut"
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "raw_output": output.get("raw_output", "") or json.dumps(output),
                        "business_output": business_output,
                        "structured_payload": structured_payload,
                        "coverage_gate": coverage_gate,
                    },
                    error_message=coverage_gate["message"],
                    completed_at=datetime.now(),
                )
                return await ctx.state_machine.rewind_to(
                    workflow_id,
                    retry_target,
                    mode="retry",
                    reason=coverage_gate["message"],
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
                business_output, structured_payload = self._synchronize_business_identity_from_materialized_ssot(
                    business_output=business_output,
                    structured_payload=structured_payload,
                    ssot_materialized=ssot_materialized,
                )
                if isinstance(business_output, dict):
                    output["business_output"] = business_output
                if isinstance(structured_payload, dict):
                    output["structured_payload"] = structured_payload

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
