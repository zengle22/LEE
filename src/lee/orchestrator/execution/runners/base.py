"""
LEE Orchestrator — StepRunner 基类 + RunnerContext

RunnerContext 封装了所有 runner 运行所需的依赖（store、state_machine 等），
避免每个 runner 直接持有 orchestrator 引用。
"""

from __future__ import annotations

import glob
import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, TYPE_CHECKING, Dict

import asyncio
import logging
import yaml

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY
from lee.orchestrator.execution.validators import SchemaValidator, ValidationResult


class RunnerContext:
    """
    Runner 运行上下文 — 封装所有共享依赖

    由 Orchestrator 构建并传入每个 runner。
    """

    def __init__(
        self,
        store,
        state_machine,
        event_log,
        evidence_collector,
        verifier_engine,
        executor_factory,
        agent_context_builder,
        contract_discovery,
        file_output_handler,
        token_manager,
        project_root: Optional[str] = None,
        repo_registry=None,
        worktree_manager=None,
    ):
        self.store = store
        self.state_machine = state_machine
        self.event_log = event_log
        self.evidence_collector = evidence_collector
        self.verifier_engine = verifier_engine
        self.executor_factory = executor_factory
        self.agent_context_builder = agent_context_builder
        self.contract_discovery = contract_discovery
        self.file_output_handler = file_output_handler
        self.token_manager = token_manager
        self.project_root = project_root
        self.repo_registry = repo_registry
        self.worktree_manager = worktree_manager

    def resolve_workdir(self, step, run_id: str) -> str:
        """
        解析步骤的工作目录

        优先级：
        1. step.repo_scope + worktree_manager → 隔离 worktree
        2. project_root → 回退到项目根目录

        Args:
            step: 步骤对象（可能有 repo_scope 属性）
            run_id: 运行 ID（用于 worktree 分配）

        Returns:
            工作目录绝对路径
        """
        repo_scope = getattr(step, "repo_scope", None)
        if repo_scope and self.worktree_manager:
            try:
                return self.worktree_manager.get_workdir(run_id, repo_scope)
            except ValueError:
                pass  # 未分配则 fallback
        return str(Path(self.project_root or ".").resolve())


class StepRunnerStrategy(ABC):
    """步骤 runner 策略接口"""

    @abstractmethod
    def can_handle(self, step_kind: str) -> bool:
        """是否能处理此类步骤"""
        ...

    @abstractmethod
    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """执行步骤"""
        ...


class StepRunnerBase(StepRunnerStrategy):
    """
    提供所有 runner 共享的工具方法：
    - evidence 收集
    - verifier 运行
    - output 校验
    - demo 模式检测
    """

    @staticmethod
    def _normalize_project_relative_path(path: str) -> str:
        if isinstance(path, str) and path.startswith(("/", "\\")) and not Path(path).drive:
            return path.lstrip("/\\")
        return path

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    async def _collect_evidence(
        self, ctx: RunnerContext, workflow_id: str, step_id: str, artifacts: List[str]
    ) -> None:
        """收集证据产物"""
        if not artifacts:
            return

        instance = await ctx.store.get_workflow(workflow_id)
        if not instance:
            return

        run_id = instance.data.get("run_id")
        if not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await ctx.store.update_workflow_data(workflow_id, instance.data)

        ctx.evidence_collector.collect(run_id, step_id, artifacts)

    @staticmethod
    def _generate_run_id() -> str:
        import uuid
        return f"RUN-{uuid.uuid4().hex[:8].upper()}"

    # ------------------------------------------------------------------
    # Output path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_output_paths(outputs, project_root: Optional[str] = None) -> List[str]:
        """根据 outputs 规格解析路径"""
        if not outputs:
            return []
        paths = []
        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue
            path = StepRunnerBase._normalize_project_relative_path(path)
            if os.path.isabs(path):
                paths.append(path)
            else:
                base = Path(project_root or ".").resolve()
                paths.append(str(base / path))
        return paths

    @staticmethod
    def _ensure_output_artifacts(outputs, project_root: Optional[str] = None) -> List[str]:
        """确保输出产物存在（用于 demo/兜底）"""
        if not outputs:
            return []

        created: List[str] = []
        base = Path(project_root or ".").resolve()

        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue
            path = StepRunnerBase._normalize_project_relative_path(path)

            target = Path(path)
            if not target.is_absolute():
                target = base / target

            out_type = getattr(out, "type", None) or ("dir" if path.endswith("/") else "file")
            if out_type == "dir":
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue

            fmt = (getattr(out, "format", None) or "text").lower()
            if fmt == "json":
                payload = {"placeholder": True, "path": path, "status": "demo"}
                content = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
            elif fmt in ("yaml", "yml"):
                content = "placeholder: true\nstatus: demo\n"
            elif fmt in ("markdown", "md"):
                content = "# Placeholder\n\nGenerated in demo mode.\n"
            else:
                content = "placeholder\n"

            target.write_text(content, encoding="utf-8")
            created.append(str(target))

        return created

    # ------------------------------------------------------------------
    # Demo mode
    # ------------------------------------------------------------------

    @staticmethod
    def _demo_mode_enabled() -> bool:
        return os.getenv("LEE_DEMO_MODE", "").lower() in ("1", "true", "yes")

    # ------------------------------------------------------------------
    # Output validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_step_output(step, output_data) -> Optional[ValidationResult]:
        """v3.4: 验证步骤输出是否符合 Contract Schema"""
        config = step.config or {}

        schema_path = config.get("output_contract")
        if not schema_path:
            execution_config = config.get("execution", {})
            schema_path = execution_config.get("output_contract") if isinstance(execution_config, dict) else None
        if not schema_path:
            return None

        try:
            validator = SchemaValidator()
            result = validator.validate(output_data, {"schema_path": schema_path})
            return result
        except Exception as e:
            print(f"[OutputValidation] Error validating step {step.id}: {e}")
            return None

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        """Strip a single top-level markdown code fence if present."""
        if not isinstance(content, str):
            return content
        text = content.strip()
        fenced = re.match(r"^```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```$", text)
        if fenced:
            return fenced.group(1).strip()
        return text

    @staticmethod
    def _strip_leading_think_block(content: str) -> str:
        """Strip a leading <think>...</think> block emitted before structured output."""
        if not isinstance(content, str):
            return content
        return re.sub(r"^\s*<think>[\s\S]*?</think>\s*", "", content, count=1).strip()

    @classmethod
    def _structured_output_candidates(cls, output_text: str) -> List[str]:
        if not isinstance(output_text, str):
            return []

        text = output_text.strip()
        if not text:
            return []

        candidates: List[str] = []
        seen: set[str] = set()

        def add(candidate: str) -> None:
            value = (candidate or "").strip()
            if not value or value in seen:
                return
            seen.add(value)
            candidates.append(value)

        add(cls._strip_leading_think_block(cls._strip_code_fence(text)))

        first_fence = re.search(r"\n```(?:json|yaml|yml)?\s*\n", text, re.IGNORECASE)
        if first_fence:
            add(cls._strip_leading_think_block(text[:first_fence.start()]))

        for match in re.finditer(r"```(?:json|yaml|yml)?\s*\n([\s\S]*?)\n```", text, re.IGNORECASE):
            add(cls._strip_leading_think_block(match.group(1)))

        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                add(cls._strip_leading_think_block(text[start:end + 1]))

        return candidates

    @classmethod
    def _parse_structured_output(cls, output_text: str) -> Any:
        """
        Parse JSON/YAML-like structured output from LLM text.
        """
        import yaml

        candidates = cls._structured_output_candidates(output_text)
        if not candidates:
            raise ValueError("Structured output is empty")

        last_error: Optional[Exception] = None
        for text in candidates:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = exc

            try:
                data = yaml.safe_load(text)
            except Exception as exc:
                last_error = exc
                continue

            if isinstance(data, (dict, list)):
                return data
            if data is not None:
                last_error = ValueError("Structured output must be a JSON/YAML object or array")

        if last_error is not None:
            raise ValueError(f"Failed to parse structured output: {last_error}") from last_error
        raise ValueError("Structured output is empty")

    @staticmethod
    def _workflow_workspace_dir(
        *,
        project_root: Optional[str],
        workflow_id: str,
        step_id: str,
    ) -> Path:
        base_root = Path(project_root or ".").resolve()
        return base_root / ".workflow" / "workspace" / workflow_id / step_id

    @staticmethod
    def _dump_structured_output_text(payload: Any, preferred_format: str = "yaml") -> str:
        normalized_format = (preferred_format or "yaml").lower()
        if normalized_format == "json":
            return json.dumps(payload, ensure_ascii=False, indent=2)
        if isinstance(payload, str):
            return payload
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    @classmethod
    def _materialize_workspace_payload(
        cls,
        *,
        project_root: Optional[str],
        workflow_id: str,
        step_id: str,
        file_stem: str,
        payload: Any,
        preferred_format: str = "yaml",
    ) -> Optional[str]:
        if payload is None:
            return None
        if not isinstance(payload, (dict, list, str)):
            return None

        workspace_dir = cls._workflow_workspace_dir(
            project_root=project_root,
            workflow_id=workflow_id,
            step_id=step_id,
        )
        workspace_dir.mkdir(parents=True, exist_ok=True)

        ext = ".json" if (preferred_format or "").lower() == "json" else ".yaml"
        target_path = workspace_dir / f"{file_stem}{ext}"
        target_path.write_text(
            cls._dump_structured_output_text(payload, preferred_format=preferred_format),
            encoding="utf-8",
        )
        return str(target_path)

    @classmethod
    def _materialize_symbolic_workspace_outputs(
        cls,
        *,
        step,
        workflow_id: str,
        project_root: Optional[str],
        business_output: Any,
        structured_payload: Any,
    ) -> List[str]:
        if not getattr(step, "outputs", None):
            return []

        has_explicit_paths = any(getattr(output_spec, "path", None) for output_spec in step.outputs)
        if has_explicit_paths:
            return []

        written_files: List[str] = []
        business_path = cls._materialize_workspace_payload(
            project_root=project_root,
            workflow_id=workflow_id,
            step_id=step.id,
            file_stem="business_output",
            payload=business_output,
            preferred_format="yaml",
        )
        if business_path:
            written_files.append(business_path)

        if isinstance(structured_payload, dict) and structured_payload != business_output:
            structured_path = cls._materialize_workspace_payload(
                project_root=project_root,
                workflow_id=workflow_id,
                step_id=step.id,
                file_stem="structured_payload",
                payload=structured_payload,
                preferred_format="yaml",
            )
            if structured_path:
                written_files.append(structured_path)

        return written_files

    @staticmethod
    def _resolve_contract_path(
        schema_ref: str,
        spec_path: Optional[str],
        project_root: Optional[str],
    ) -> str:
        """
        Resolve a contract path relative to the agent spec first, then project root.
        """
        schema_path = Path(schema_ref)
        if schema_path.is_absolute():
            return str(schema_path)

        if spec_path:
            spec_dir = Path(spec_path).resolve().parent
            candidate = (spec_dir / schema_path).resolve()
            if candidate.exists():
                return str(candidate)

        base = Path(project_root or ".").resolve()
        return str((base / schema_path).resolve())

    @staticmethod
    def _load_agent_spec_for_step(ctx: RunnerContext, step) -> Optional[Any]:
        """
        Load the concrete agent spec for the current step when available.
        """
        try:
            builder = getattr(ctx, "agent_context_builder", None)
            loader = getattr(builder, "agent_loader", None)
            if loader and getattr(step, "agent_id", None):
                return loader.load(step.agent_id)
        except Exception:
            return None
        return None

    @staticmethod
    def _get_agent_mapping(agent_spec: Optional[Any], attr_name: str) -> Dict[str, Any]:
        if not agent_spec:
            return {}
        value = getattr(agent_spec, attr_name, {}) or {}
        return value if isinstance(value, dict) else {}

    @classmethod
    def _resolve_governance_paths(
        cls,
        agent_spec: Optional[Any],
        project_root: Optional[str],
    ) -> Dict[str, str]:
        governance = cls._get_agent_mapping(agent_spec, "governance")
        spec_path = getattr(agent_spec, "spec_path", None) if agent_spec else None
        resolved: Dict[str, str] = {}
        for key, ref in governance.items():
            if isinstance(ref, str):
                resolved[key] = cls._resolve_contract_path(ref, spec_path, project_root)
        return resolved

    @staticmethod
    def _is_implementation_facing_step(step, agent_spec: Optional[Any]) -> bool:
        step_config = getattr(step, "config", {}) or {}
        if "implementation_facing" in step_config:
            return bool(step_config["implementation_facing"])

        agent_id = (getattr(step, "agent_id", "") or "").lower()
        if any(token in agent_id for token in ("spec_maintainer", "spec-review", "spec_review")):
            return False

        tags = set()
        if agent_spec:
            raw_tags = getattr(agent_spec, "tags", []) or []
            tags = {str(tag).lower() for tag in raw_tags}

        governance_tags = {"governance", "spec", "maintainer", "review", "lint", "contract", "workflow", "gate", "skill"}
        return not bool(tags & governance_tags)

    @staticmethod
    def _find_acceptance_brief(
        acceptance_briefs_dir: Optional[str],
        step,
    ) -> Optional[str]:
        if not acceptance_briefs_dir:
            return None

        step_config = getattr(step, "config", {}) or {}
        explicit_path = step_config.get("acceptance_brief")
        if explicit_path and Path(explicit_path).exists():
            return str(Path(explicit_path).resolve())

        brief_id = step_config.get("acceptance_brief_id") or step_config.get("task_id")
        if brief_id:
            matches = StepRunnerBase._scan_acceptance_briefs(acceptance_briefs_dir)
            for match in matches:
                metadata = match["metadata"]
                if metadata.get("brief_id") == brief_id and metadata.get("status", "active") == "active":
                    return match["path"]

            pattern = str(Path(acceptance_briefs_dir) / f"*{brief_id}*.md")
            matches = glob.glob(pattern)
            if matches:
                return str(Path(matches[0]).resolve())
        return None

    @staticmethod
    def _scan_acceptance_briefs(acceptance_briefs_dir: Optional[str]) -> List[Dict[str, Any]]:
        if not acceptance_briefs_dir:
            return []

        results: List[Dict[str, Any]] = []
        for path in Path(acceptance_briefs_dir).glob("*.md"):
            metadata = StepRunnerBase._parse_markdown_front_matter(path)
            if metadata:
                results.append({"path": str(path.resolve()), "metadata": metadata})
        return results

    @staticmethod
    def _parse_markdown_front_matter(path: Path) -> Dict[str, Any]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return {}

        if not text.startswith("---\n"):
            return {}

        end_idx = text.find("\n---", 4)
        if end_idx == -1:
            return {}

        raw = text[4:end_idx]
        try:
            metadata = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            return {}
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _find_module_contract(
        module_contracts_dir: Optional[str],
        step,
    ) -> Optional[str]:
        if not module_contracts_dir:
            return None

        step_config = getattr(step, "config", {}) or {}
        explicit_path = step_config.get("module_contract")
        if explicit_path and Path(explicit_path).exists():
            return str(Path(explicit_path).resolve())

        module_name = step_config.get("module_name") or step_config.get("governed_module")
        if module_name:
            candidate = Path(module_contracts_dir) / f"{module_name}.md"
            if candidate.exists():
                return str(candidate.resolve())
        return None

    @classmethod
    def _evaluate_governance_preflight(
        cls,
        step,
        agent_spec: Optional[Any],
        project_root: Optional[str],
        structured_payload: Optional[Any] = None,
    ) -> Dict[str, Any]:
        implementation_facing = cls._is_implementation_facing_step(step, agent_spec)
        governance_paths = cls._resolve_governance_paths(agent_spec, project_root)
        step_config = getattr(step, "config", {}) or {}

        formal_ssot_present = False
        contracts = cls._get_agent_mapping(agent_spec, "contracts")
        if contracts.get("ssot_output_schema"):
            formal_ssot_present = True
        if isinstance(structured_payload, dict) and (
            "ssot_output_contract" in structured_payload
            or ("contract_version" in structured_payload and "outputs" in structured_payload)
        ):
            formal_ssot_present = True
        if step_config.get("formal_ssot_id") or step_config.get("ssot_root_id"):
            formal_ssot_present = True

        acceptance_brief_path = cls._find_acceptance_brief(governance_paths.get("acceptance_briefs"), step)
        acceptance_brief_metadata = {}
        if acceptance_brief_path:
            acceptance_brief_metadata = cls._parse_markdown_front_matter(Path(acceptance_brief_path))
        module_contract_path = cls._find_module_contract(governance_paths.get("module_contracts"), step)

        warnings: List[str] = []
        allow_full_completion = True

        if implementation_facing and not formal_ssot_present:
            if not acceptance_brief_path and not module_contract_path:
                allow_full_completion = False
                warnings.append(
                    "No formal SSOT truth source or temporary governance anchor found."
                )
            else:
                warnings.append(
                    "No formal SSOT truth source; running under temporary governance."
                )

        return {
            "implementation_facing": implementation_facing,
            "formal_ssot_present": formal_ssot_present,
            "acceptance_brief_found": bool(acceptance_brief_path),
            "acceptance_brief_path": acceptance_brief_path,
            "acceptance_brief_metadata": acceptance_brief_metadata,
            "module_contract_found": bool(module_contract_path),
            "module_contract_path": module_contract_path,
            "allow_full_completion": allow_full_completion,
            "governance_paths": governance_paths,
            "human_gate_required": (not formal_ssot_present) and implementation_facing,
            "warnings": warnings,
        }

    @staticmethod
    def _build_completion_summary(
        step,
        written_files: List[str],
        structured_payload: Optional[Any],
        governance_preflight: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        structured_payload = structured_payload if isinstance(structured_payload, dict) else {}
        changed_files = structured_payload.get("changed_files") or written_files
        tests_executed = structured_payload.get("tests_executed") or "missing"
        known_limitations = structured_payload.get("known_limitations") or "not declared"
        evidence = structured_payload.get("evidence") or (written_files if written_files else "missing")

        return {
            "scope_completed": structured_payload.get("scope_completed") or step.id,
            "changed_files": changed_files,
            "evidence": evidence,
            "tests_executed": tests_executed,
            "known_limitations": known_limitations,
            "human_gate_required": (
                governance_preflight.get("human_gate_required")
                if governance_preflight
                else "unknown"
            ),
        }

    def _handle_validation_result(
        self, validation_result: Optional[ValidationResult], step, strict: bool
    ) -> Optional[str]:
        """处理校验结果，返回错误消息（strict 模式）或 None"""
        if validation_result and not validation_result.passed:
            if strict:
                return f"Output schema validation failed: {validation_result.errors[0].message if validation_result.errors else 'unknown'}"
            else:
                print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")
        return None

    async def _validate_step_output_with_retry(
        self,
        ctx: RunnerContext,
        step,
        output_data: Any,
        workflow_id: str
    ) -> tuple[bool, Optional[ValidationResult], int]:
        """
        v3.5: 验证步骤输出，支持重试机制

        Args:
            ctx: Runner 上下文
            step: 步骤对象
            output_data: 输出数据
            workflow_id: 工作流 ID

        Returns:
            (passed, validation_result, attempt_count) 元组
        """
        config = step.config or {}
        execution_config = config.get("execution", {}) if isinstance(config.get("execution"), dict) else {}

        # 获取重试配置
        on_failure = execution_config.get("on_failure", "warn")  # block | warn | retry
        max_retries = execution_config.get("max_retries", 3)
        retry_delay = execution_config.get("retry_delay_seconds", 5)

        # 如果不是 retry 模式，使用原有逻辑
        if on_failure != "retry":
            result = self._validate_step_output(step, output_data)
            if result is None:
                return True, None, 1  # 无验证配置时认为通过

            if result.passed:
                return True, result, 1

            # 处理验证失败
            if on_failure == "block":
                return False, result, 1
            else:  # warn
                print(f"[OutputValidation] Warning: Step {step.id} output validation failed (warn mode)")
                return True, result, 1  # warn 模式下仍返回 True

        # 重试模式
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=retry_delay,
            max_delay=60.0,
            jitter=True,
        )

        retry_executor = AsyncRetryExecutor(policy)
        attempt_count = 0

        async def validate_once():
            """单次验证函数"""
            nonlocal attempt_count
            attempt_count += 1
            result = self._validate_step_output(step, output_data)

            if result is None:
                return  # 无验证配置，认为通过

            if not result.passed:
                # 构造验证错误
                error_msg = result.errors[0].message if result.errors else "Validation failed"
                raise ValueError(f"Output validation failed: {error_msg}")

            return result

        try:
            await retry_executor.execute(validate_once)
            # 重试成功或无需验证
            result = self._validate_step_output(step, output_data)
            return True, result, attempt_count
        except Exception as e:
            # 重试耗尽
            print(f"[OutputValidation] Step {step.id} output validation failed after {attempt_count} attempts: {e}")
            result = self._validate_step_output(step, output_data)
            return False, result, attempt_count

    @staticmethod
    def _get_step_output_validation_config(step_id: str, template_config: dict = None) -> dict:
        """
        获取步骤的输出验证配置

        Args:
            step_id: 步骤 ID
            template_config: 模板配置（来自 workflow template）

        Returns:
            验证配置字典，包含:
            - contract_ref: 契约 schema 路径
            - on_failure: 失败处理策略 (block/warn/retry)
            - max_retries: 最大重试次数
            - required_fields: 必填字段列表
            - validation_rules: 验证规则列表
        """
        if not template_config:
            return {}

        step_validation = template_config.get("step_output_validation", {})
        return step_validation.get(step_id, {})

    # ------------------------------------------------------------------
    # Verifiers
    # ------------------------------------------------------------------

    async def _run_verifiers(self, ctx: RunnerContext, workflow_id: str, step) -> Optional[List]:
        """运行 verifiers，返回结果列表或 None"""
        verifiers = step.config.get("verifiers") if step.config else None
        if not verifiers:
            return None

        if self._demo_mode_enabled():
            from lee.orchestrator.verifiers.base import VerifyResult, VerifyStatus
            results = []
            for item in verifiers or []:
                vtype = item.get("type") if isinstance(item, dict) else None
                results.append(VerifyResult(
                    status=VerifyStatus.PASSED,
                    verifier_id=vtype or "unknown",
                    message="verifier skipped in demo mode",
                    details={"mode": "demo"},
                ))

            instance = await ctx.store.get_workflow(workflow_id)
            run_id = instance.data.get("run_id") if instance else None
            if instance and not run_id:
                run_id = self._generate_run_id()
                instance.data["run_id"] = run_id
                await ctx.store.update_workflow_data(workflow_id, instance.data)

            report_path = self._write_verifier_report(ctx, run_id or "RUN-UNKNOWN", step.id, results)
            if report_path:
                await self._collect_evidence(ctx, workflow_id, step.id, [report_path])

            return results

        instance = await ctx.store.get_workflow(workflow_id)
        run_id = instance.data.get("run_id") if instance else None
        if instance and not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await ctx.store.update_workflow_data(workflow_id, instance.data)

        context = {
            "workflow_id": workflow_id,
            "step_id": step.id,
            "run_id": run_id,
        }

        results = ctx.verifier_engine.run(verifiers, context)

        report_path = self._write_verifier_report(ctx, run_id or "RUN-UNKNOWN", step.id, results)
        if report_path:
            await self._collect_evidence(ctx, workflow_id, step.id, [report_path])

        return results

    def _verifiers_passed(self, ctx: RunnerContext, results: List) -> bool:
        return ctx.verifier_engine.all_passed(results)

    @staticmethod
    def _write_verifier_report(
        ctx: RunnerContext, run_id: str, step_id: str, results: List
    ) -> Optional[str]:
        """写入 verifier 结果报告到 .workflow/verifiers/"""
        base = Path(ctx.project_root or ".").resolve()
        report_dir = base / ".workflow" / "verifiers"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{run_id}-{step_id}.json"

        payload = []
        for r in results:
            payload.append({
                "verifier_id": r.verifier_id,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "message": r.message,
                "details": r.details,
            })

        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(report_path)

    # ------------------------------------------------------------------
    # Workflow completion check (delegate to orchestrator)
    # ------------------------------------------------------------------

    async def _check_workflow_completion(self, ctx: RunnerContext, workflow_id: str) -> None:
        """检查工作流是否完成 — 由 orchestrator 实现"""
        # 这个方法在 Orchestrator 中有具体实现
        # Runner 层面不需要做任何事情，由 StepRunnerMixin dispatch 层调用
        pass

    async def _update_task_execution_with_retry(
        self,
        ctx: RunnerContext,
        execution_id: str,
        status: TaskExecutionStatus,
        max_retries: int = 3,
        backoff_base: float = 0.1,
        **kwargs
    ) -> bool:
        """
        带重试的 task_execution 状态更新 (BUG-2026-0038)

        Args:
            ctx: Runner 上下文
            execution_id: Task execution ID
            status: 目标状态
            max_retries: 最大重试次数
            backoff_base: 退避基数（秒）
            **kwargs: 传递给 update_task_execution 的其他参数

        Returns:
            bool: 是否成功更新
        """
        logger = logging.getLogger(__name__)

        for attempt in range(max_retries):
            try:
                await ctx.store.update_task_execution(
                    execution_id,
                    status,
                    **kwargs
                )
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"[TaskExecutionUpdater] Failed to update {execution_id} "
                        f"to {status.value} after {max_retries} attempts: {e}"
                    )
                    return False
                wait_time = backoff_base * (2 ** attempt)
                logger.warning(
                    f"[TaskExecutionUpdater] Attempt {attempt + 1} failed, "
                    f"retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
        return False
