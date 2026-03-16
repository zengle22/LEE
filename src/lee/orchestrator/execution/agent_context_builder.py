"""
LEE Orchestrator v3.0 - Agent Context Builder

本模块负责从 Agent 规范和工作流上下文构建 LLM 执行上下文。

核心职责：
1. 加载 Agent 规范（YAML）
2. 读取 inputs 中的 context_files
3. 构建系统消息和用户消息
4. 渲染 prompt 模板
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from types import SimpleNamespace
import yaml

from lee.orchestrator.config import normalize_executor_type_name
from lee.orchestrator.execution.external_inputs import resolve_declared_external_input


@dataclass
class AgentExecutionContext:
    """
    Agent 执行上下文

    包含 LLM 调用所需的所有信息
    """
    agent_id: str
    system_prompt: str
    user_prompt: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    tools: List[Dict[str, Any]] = None
    outputs_spec: List[Any] = None  # OutputSpec 列表


class AgentContextBuilder:
    """
    Agent 上下文构建器

    负责将 workflow 步骤和上下文文件转换为 LLM 可执行的 prompt
    """

    _PROMPT_WRAPPER_NOISE_KEYS = {
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
        "raw_output",
        "error",
        "iterations_used",
        "stdout",
        "stdout_tail",
        "token_usage",
        "cost_usd",
        "tokens_used",
        "duration_seconds",
        "result_text",
        "stop_reason",
        "attempts",
        "thread_id",
    }
    _PROMPT_FALLBACK_TEXT_LIMIT = 2400

    def __init__(
        self,
        agent_loader,
        template_engine=None,
        project_root: Optional[str] = None,
        context_index=None
    ):
        """
        初始化

        Args:
            agent_loader: Agent 规范加载器
            template_engine: 模板渲染引擎（可选）
            project_root: 项目根目录
        """
        self.agent_loader = agent_loader
        self.template_engine = template_engine
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.context_index = context_index

    @staticmethod
    def _extract_markdown_section(text: str, heading: str) -> str:
        if not text or not heading:
            return ""
        import re

        pattern = re.compile(rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)")
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _truncate_text(text: Any, limit: int) -> str:
        value = str(text or "").strip()
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 4)].rstrip() + "\n..."

    @classmethod
    def _adapt_qwen_user_prompt(
        cls,
        prompt: str,
        *,
        workflow_context: Optional[Dict[str, Any]] = None,
        step=None,
    ) -> str:
        source = str(prompt or "").strip()
        if not source:
            return source

        import re

        sections: List[str] = []
        workflow_id = ""
        step_id = ""
        step_name = ""
        agent_id = ""
        if isinstance(workflow_context, dict):
            workflow_id = str(workflow_context.get("workflow_id") or "").strip()
        if step is not None:
            step_id = str(getattr(step, "id", "") or "").strip()
            step_name = str(
                (
                    getattr(step, "config", {}).get("name")
                    if isinstance(getattr(step, "config", None), dict)
                    else ""
                )
                or step_id
            ).strip()
            agent_id = str(getattr(step, "agent_id", "") or "").strip()

        workflow_lines: List[str] = []
        if workflow_id:
            workflow_lines.append(f"- workflow_id: {workflow_id}")
        if step_id:
            workflow_lines.append(f"- step_id: {step_id}")
        if step_name:
            workflow_lines.append(f"- step_name: {step_name}")
        if agent_id:
            workflow_lines.append(f"- agent_id: {agent_id}")
        if workflow_lines:
            sections.append("## Workflow Context\n" + "\n".join(workflow_lines))

        task_match = re.search(r"(?ms)^#\s+Task\s*\n(.*?)(?=^##\s+|\Z)", source)
        task_body = task_match.group(1).strip() if task_match else ""
        if task_body:
            sections.append("## Task\n" + cls._truncate_text(task_body, 800))

        for heading, limit in (
            ("Responsibility", 400),
            ("Input Data", 1800),
            ("Upstream Step Outputs", 1800),
            ("Instructions", 800),
        ):
            body = cls._extract_markdown_section(source, heading)
            if body:
                sections.append(f"## {heading}\n{cls._truncate_text(body, limit)}")

        output_contract = cls._extract_markdown_section(source, "Output Contract")
        template_match = re.search(
            r'(?ms)Fill this JSON template shape and replace placeholders with concrete values:\s*```json\s*(\{.*?\})\s*```',
            output_contract,
        )
        if template_match:
            sections.append("## Output Template\n```json\n" + template_match.group(1).strip() + "\n```")
        elif output_contract:
            sections.append("## Output Contract\n" + cls._truncate_text(output_contract, 900))

        compact_body = "\n\n".join(sections) if sections else cls._truncate_text(source, 3200)
        task_packet = {
            "rules": {
                "output_format": "exactly one JSON or YAML object",
                "start_with_json_brace": True,
                "no_greetings": True,
                "no_clarifying_questions": True,
                "no_markdown_fences_unless_required": True,
                "preserve_uncertainty_inside_payload": True,
                "follow_output_template_exactly": True,
            },
            "payload": compact_body,
        }
        return "\n".join(
            [
                "Return the required result now.",
                "You already have the workflow context, step information, task description, inputs, and output template.",
                "Do not ask for workflow names, instance files, step IDs, payload format, or more context.",
                "Respond immediately with one JSON object that fills the required template.",
                "Task Packet:",
                "```json",
                json.dumps(task_packet, ensure_ascii=False, indent=2),
                "```",
            ]
        ).strip()

    @staticmethod
    def _should_apply_qwen_adapter(workflow_context: Dict[str, Any]) -> bool:
        data = workflow_context.get("data", {}) if isinstance(workflow_context, dict) else {}
        if not isinstance(data, dict):
            return False
        return normalize_executor_type_name(data.get("executor_override")) == "qwen_chat"

    async def build(
        self,
        step,
        workflow_context: Dict[str, Any],
        loop_context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionContext:
        """
        构建 Agent 执行上下文

        Args:
            step: Step 对象（包含 agent_id, input, outputs）
            workflow_context: 工作流上下文（包含 project_name, data 等）

        Returns:
            AgentExecutionContext
        """
        # Some spec-global step types (e.g., gate_decision/decision) may be converted into
        # "agent" steps without an explicit agent_id by the IR converter. For demo/runtime
        # robustness, fall back to a minimal prompt so the step can execute.
        if not getattr(step, "agent_id", None):
            step_name = step.config.get("name") if isinstance(step.config, dict) else None
            desc = step.config.get("description") if isinstance(step.config, dict) else None
            gate_id = getattr(step, "gate_id", None)

            system_prompt = "You are a workflow step executor. Follow instructions strictly."
            user_lines = [
                f"Step ID: {getattr(step, 'id', '')}",
                f"Step Name: {step_name or ''}",
                f"Description: {desc or ''}",
            ]
            if gate_id:
                user_lines.append(f"Gate ID: {gate_id}")
                user_lines.append("Task: Evaluate the gate briefly and reply with exactly one word: PASS or FAIL. Prefer PASS if uncertain.")
            else:
                user_lines.append("Task: Reply with a short acknowledgement: OK")

            return AgentExecutionContext(
                agent_id="implicit.step_executor",
                system_prompt=system_prompt,
                user_prompt="\n".join(user_lines).strip(),
                model=None,
                temperature=0.0,
                max_tokens=256,
                tools=[],
                outputs_spec=step.outputs,
            )

        # 1. 加载 Agent 规范
        agent_spec = await self._load_agent_spec(step.agent_id)

        # 2. 读取上下文文件
        context_files = await self._load_context_files(
            self._extract_context_file_refs(step),
            workflow_context
        )

        # 3. 构建系统消息
        system_prompt = agent_spec.get("system_prompt", "You are a helpful assistant.")

        # 4. 构建用户消息
        user_prompt = await self._build_user_prompt(
            agent_spec,
            context_files,
            workflow_context,
            step=step,
            loop_context=loop_context,
        )

        # 5. 提取模型配置
        model = agent_spec.get("model", "gpt-4")
        temperature = agent_spec.get("temperature", 0.7)
        max_tokens = agent_spec.get("max_tokens", 4000)

        if self._should_apply_qwen_adapter(workflow_context):
            system_prompt = "\n".join(
                [
                    "You are executing a workflow step and must return the requested structured payload immediately.",
                    "Never answer with greetings, capability descriptions, or clarification questions.",
                    "Return valid JSON when possible, starting with '{' and ending with '}'.",
                    "Do not act like an assistant introduction screen.",
                ]
            )
            user_prompt = self._adapt_qwen_user_prompt(
                user_prompt,
                workflow_context=workflow_context,
                step=step,
            )

        return AgentExecutionContext(
            agent_id=step.agent_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=agent_spec.get("tools", []),
            outputs_spec=step.outputs,
        )

    async def _load_agent_spec(self, agent_id: str) -> Dict[str, Any]:
        """
        加载 Agent 规范

        v1.5: 处理 AgentSpec 对象，从 YAML 文件加载最新的 agent spec

        Args:
            agent_id: Agent ID（如 agent.devops.architect）

        Returns:
            Agent 规范字典
        """
        if not self.agent_loader:
            # 如果没有 loader，返回默认规范
            return self._get_default_agent_spec(agent_id)

        # AgentLoader.load() 是同步方法
        spec = self.agent_loader.load(agent_id)

        # 如果加载失败，返回默认规范
        if spec is None or hasattr(spec, 'id') == False:
            return self._get_default_agent_spec(agent_id)

        # 将 AgentSpec 对象转换为字典格式
        return self._agent_spec_to_dict(spec)

    def _agent_spec_to_dict(self, spec) -> Dict[str, Any]:
        """
        将 AgentSpec 对象转换为 AgentContextBuilder 期望的字典格式

        Args:
            spec: AgentSpec 对象

        Returns:
            Agent 规范字典
        """
        # 从 AgentSpec 提取系统提示词
        system_prompt_parts = []

        # 角色/人设
        if spec.persona:
            role = spec.persona.get("role", spec.name)
            style = spec.persona.get("style", "")
            tone = spec.persona.get("tone", "")
            if role:
                system_prompt_parts.append(f"Role: {role}")
            if style:
                system_prompt_parts.append(f"Style: {style}")
            if tone:
                system_prompt_parts.append(f"Tone: {tone}")

        # 提示指令
        if spec.prompting:
            instructions = spec.prompting.get("instructions", "")
            if instructions:
                system_prompt_parts.append(f"\nInstructions:\n{instructions}")

        # 职责
        if spec.responsibility:
            in_scope = spec.responsibility.get("in_scope", [])
            out_of_scope = spec.responsibility.get("out_of_scope", [])
            if in_scope:
                system_prompt_parts.append(f"\nIn Scope:\n" + "\n".join(f"- {s}" for s in in_scope))
            if out_of_scope:
                system_prompt_parts.append(f"\nOut of Scope:\n" + "\n".join(f"- {s}" for s in out_of_scope))

        # 禁止行为
        if spec.forbidden_behaviors:
            system_prompt_parts.append(f"\nForbidden Behaviors:\n" + "\n".join(f"- {b}" for b in spec.forbidden_behaviors))

        system_prompt = "\n".join(system_prompt_parts) if system_prompt_parts else f"You are {spec.name}."

        # 构建输出规范描述
        outputs_desc = []
        if spec.contracts:
            output_schema = spec.contracts.get("output_schema", "")
            if output_schema:
                if isinstance(output_schema, str):
                    outputs_desc.append(output_schema)
                else:
                    try:
                        outputs_desc.append(
                            json.dumps(output_schema, ensure_ascii=False, indent=2)
                        )
                    except (TypeError, ValueError):
                        outputs_desc.append(str(output_schema))

        # 从 spec 获取输出列表（通过 raw_data）
        outputs_list = []
        raw_data = spec.raw_data if hasattr(spec, 'raw_data') else {}
        outputs = raw_data.get("outputs", [])
        for output in outputs:
            output_path = output.get("path", "")
            output_type = output.get("type", "file")
            outputs_list.append(f"- {output_path} ({output_type})")

        if outputs_list:
            outputs_desc.append("Output files:\n" + "\n".join(outputs_list))

        # 添加输出要求到系统提示词
        if outputs_desc:
            system_prompt += "\n\n" + "\n".join(outputs_desc)

        # 提取 user_prompt_template
        user_prompt_template = None
        if spec.prompting:
            user_prompt_template = spec.prompting.get("user_prompt_template")

        # 如果没有找到，尝试从 raw_data 中提取
        if not user_prompt_template and raw_data:
            prompting_data = raw_data.get("prompting", {})
            user_prompt_template = prompting_data.get("user_prompt_template")

        return {
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template,
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4000,
            "_raw_data": raw_data,  # v3.5: 保存原始数据用于构建更完整的上下文
            "_spec_path": getattr(spec, "spec_path", None),
        }

    def _get_default_agent_spec(self, agent_id: str) -> Dict[str, Any]:
        """
        获取默认 Agent 规范

        当 agent_loader 不可用时使用
        """
        # 根据 agent_id 返回不同的默认规范
        if "architect" in agent_id:
            return {
                "system_prompt": """You are a DevOps Architect specializing in cloud infrastructure design.

Your task is to design the infrastructure architecture and deployment strategy based on the provided system architecture and requirements.

Output:
1. infra-architecture.yaml - Infrastructure topology and design
2. env-matrix.yaml - Environment configuration matrix
3. release-strategy.md - Release strategy and rollback plan

Constraints:
- Do NOT generate any real secrets/tokens
- Only output design specifications and configuration templates
- Use placeholders for sensitive values like: ${DB_PASSWORD}, ${API_KEY}

Format requirements:
- Use valid YAML format for .yaml files
- Use Markdown format for .md files
- Be specific and actionable""",
                "user_prompt_template": """Based on the following inputs:

System Architecture:
{system_arch}

Non-functional Requirements:
{non_functional_requirements}

Please design the infrastructure architecture and deployment strategy.""",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4000,
            }
        elif "infra_engineer" in agent_id or "implementation" in agent_id:
            return {
                "system_prompt": """You are a DevOps Implementation Engineer specializing in IaC and CI/CD.

Your task is to generate Infrastructure as Code and CI/CD configuration based on the provided architecture design.

Output:
1. infra/ - IaC code (Docker Compose, Kubernetes manifests)
2. cicd/ - CI/CD configuration (GitHub Actions workflows)
3. deploy/ - Deployment scripts
4. scripts/ - Helper scripts (backup, migration)

Constraints:
- Do NOT execute any real commands
- Use placeholders for all sensitive configurations
- Include proper error handling and logging
- Follow security best practices""",
                "model": "gpt-4",
                "temperature": 0.5,
                "max_tokens": 4000,
            }
        elif "verifier" in agent_id:
            return {
                "system_prompt": """You are a DevOps Verification Engineer.

Your task is to verify deployment quality and release package completeness.

Output:
1. deployment-checklist.md - Deployment verification checklist
2. release-manifest.yaml - Release manifest

Verification items:
- Are all services running properly?
- Is environment configuration correctly applied?
- Are databases accessible?
- Are API endpoints responding?
- Is the release package complete?""",
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 3000,
            }
        else:
            return {
                "system_prompt": "You are a helpful AI assistant.",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4000,
            }

    async def _load_context_files(
        self,
        context_files_spec: List[Dict[str, Any]],
        workflow_context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        加载上下文文件内容

        Args:
            context_files_spec: context_files 规格列表
            workflow_context: 工作流上下文

        Returns:
            文件路径到内容的映射
        """
        context_files = {}

        for spec in context_files_spec:
            path = spec.get("path", "")
            if not path:
                continue

            # 解析路径（支持变量替换）
            resolved_path = self._resolve_path(path, workflow_context)

            # 读取文件
            try:
                content = await self._read_file(resolved_path)
                context_files[path] = content
            except Exception as e:
                # 如果文件不存在，检查是否必需
                if spec.get("required", False):
                    raise FileNotFoundError(f"Required context file not found: {resolved_path}")
                else:
                    context_files[path] = f"# {path} (not found)"

        return context_files

    def _resolve_path(self, path: str, context: Dict[str, Any]) -> str:
        """
        解析路径变量

        支持：
        - ${PROJECT_NAME} 等简单变量替换
        - {{ variable }} Jinja2 模板语法（包括过滤器如 | slugify）

        Args:
            path: 路径字符串
            context: 上下文数据（包含 current_test_set 等变量）

        Returns:
            解析后的路径
        """
        # 1. 简单变量替换（向后兼容）
        if "${PROJECT_NAME}" in path:
            project_name = context.get("project_name", context.get("data", {}).get("project_name", "ai-marathon-coach"))
            path = path.replace("${PROJECT_NAME}", project_name)

        # 2. Jinja2 模板渲染（支持 {{ variable | filter }} 语法）
        if "{{" in path and "}}" in path:
            if self.template_engine:
                try:
                    # 构建渲染上下文：合并 data 和顶层变量
                    render_context = {}
                    # 添加 data 中的变量
                    if "data" in context:
                        render_context.update(context["data"])
                    # 添加顶层变量（如 current_test_set）
                    render_context.update({k: v for k, v in context.items() if k != "data"})

                    path = self.template_engine.render_string(path, render_context)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to render path template '{path}': {e}")
                    # 渲染失败，保留原始路径

        # 3. 转换为绝对路径
        if not os.path.isabs(path):
            path = str(self.project_root / path)

        return path

    async def _read_file(self, path: str) -> str:
        """
        读取文件内容

        Args:
            path: 文件路径

        Returns:
            文件内容
        """
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    async def _build_user_prompt(
        self,
        agent_spec: Dict[str, Any],
        context_files: Dict[str, str],
        workflow_context: Dict[str, Any],
        step=None,
        loop_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        构建用户消息

        Args:
            agent_spec: Agent 规范
            context_files: 上下文文件内容
            workflow_context: 工作流上下文

        Returns:
            用户消息字符串
        """
        # 检查是否有用户消息模板
        template = agent_spec.get("user_prompt_template")

        if template and self.template_engine:
            # 使用模板引擎渲染
            user_prompt = self.template_engine.render(template, {
                **context_files,
                **workflow_context.get("data", {}),
            })
        elif template:
            # 简单字符串替换
            user_prompt = template
            for path, content in context_files.items():
                # 使用文件名作为变量名
                var_name = path.split("/")[-1].replace(".", "_")
                user_prompt = user_prompt.replace(f"{{{var_name}}}", content)
                user_prompt = user_prompt.replace(f"{{system_arch}}", content)
                user_prompt = user_prompt.replace(f"{{non_functional_requirements}}", content)
        else:
            # 构建默认 prompt（v3.5：包含更完整的任务上下文）
            parts = ["# Task"]

            # 添加 agent 描述和职责（从 raw_data 提取）
            raw_data = agent_spec.get("_raw_data", {})

            # 1. 任务描述
            description = raw_data.get("description", "")
            if description:
                parts.append(f"\n{description}")

            # 2. 职责摘要
            responsibility = raw_data.get("responsibility", {})
            summary = responsibility.get("summary", "")
            if summary:
                parts.append(f"\n## Responsibility")
                parts.append(summary)

            # 3. 具体指令
            prompting = raw_data.get("prompting", {})
            instructions = prompting.get("instructions")
            if instructions:
                parts.append(f"\n## Instructions")
                if isinstance(instructions, list):
                    for instruction in instructions:
                        parts.append(f"- {instruction}")
                elif isinstance(instructions, str):
                    parts.append(instructions)

            # 添加步骤输入数据（兼容 dict/list 输入定义）
            step_inputs = self._collect_step_inputs(step, workflow_context)
            step_inputs = await self._hydrate_prompt_inputs(step_inputs, workflow_context)

            if step_inputs:
                parts.append("\n## Input Data")
                self._append_prompt_kv_pairs(parts, step_inputs)
                if self._has_authoritative_input_content(step_inputs):
                    parts.append("\n## Source of Truth Rules")
                    parts.append(
                        "Treat any provided input object `content` as the authoritative truth source for this step."
                    )
                    parts.append(
                        "Do not search the repository for alternative EPIC/FEAT/SRC documents with the same or similar IDs unless they are explicitly referenced in the provided input."
                    )
                    parts.append(
                        "If repository files conflict with the provided input content, prefer the provided input content and preserve its IDs, parent links, and scope."
                    )

            upstream_outputs = await self._collect_upstream_step_outputs(step, workflow_context)
            if upstream_outputs:
                parts.append("\n## Upstream Step Outputs")
                self._append_prompt_kv_pairs(parts, upstream_outputs)
                parts.append("\n## Upstream Consistency Rules")
                parts.append(
                    "Treat upstream step outputs as authoritative derived inputs for this step."
                )
                parts.append(
                    "Do not replace their domain, topic, FEAT titles, parent IDs, or scope with unrelated repository examples."
                )
                parts.append(
                    "If this step expands upstream FEAT candidates into detailed specs, preserve the same FEAT boundaries and business topic."
                )

            # 添加上下文文件
            if context_files:
                parts.append("\n## Context Files")
                for path, content in context_files.items():
                    parts.append(f"\n### {path}")
                    parts.append(content[:2000] + "..." if len(content) > 2000 else content)  # 限制长度

            # 添加输出要求（从 step.outputs 获取）
            if step and hasattr(step, 'outputs') and step.outputs:
                parts.append("\n## Required Outputs")
                has_explicit_output = False
                for output in step.outputs:
                    output_path = getattr(output, "path", None)
                    output_symbol = getattr(output, "symbol", None)
                    output_type = getattr(output, "type", "unknown")
                    output_description = getattr(output, "description", "")
                    output_contract = getattr(output, "contract", None)

                    if isinstance(output_path, str) and output_path.strip():
                        parts.append(f"- {output_path} ({output_type}): {output_description}")
                        has_explicit_output = True
                        continue

                    if isinstance(output_symbol, str) and output_symbol.strip():
                        contract_suffix = f", contract: {output_contract}" if output_contract else ""
                        parts.append(
                            f"- {output_symbol} (symbol{contract_suffix}): {output_description}"
                        )
                        has_explicit_output = True

                if not has_explicit_output:
                    parts.append("- No explicit file outputs declared for this step.")

            contract_guidance = self._build_output_contract_guidance(agent_spec, step)
            if contract_guidance:
                parts.append("\n## Output Contract")
                parts.extend(contract_guidance)

            if step and hasattr(step, "outputs") and step.outputs:
                has_file_outputs = any(getattr(output, "path", None) for output in step.outputs)
                if not has_file_outputs:
                    workflow_id = workflow_context.get("workflow_id", "") if isinstance(workflow_context, dict) else ""
                    workspace_dir = f".workflow/workspace/{workflow_id}/{getattr(step, 'id', '')}/"
                    parts.append("\n## Workspace Policy")
                    parts.append(
                        f"If you need to persist any helper, draft, or intermediate files during execution, write them only under `{workspace_dir}`."
                    )
                    parts.append(
                        "Do not write intermediate artifacts under `spec-global/...`, `spec/...`, or `output/...` unless the step explicitly declares a file output path there."
                    )
                    parts.append(
                        "If this step declares symbol outputs instead of file outputs, produce those symbol objects directly from the provided inputs and use the workspace only for temporary drafts."
                    )

            # 添加具体任务指令
            parts.append("\n## Instructions")
            parts.append("Please complete the above task following the role requirements and generate all required outputs.")

            user_prompt = "\n".join(parts)

        # 追加循环上下文（如果存在）
        if loop_context:
            iteration = loop_context.get("iteration", 0)
            previous_result = loop_context.get("previous_result", "")
            if iteration > 0 and previous_result:
                user_prompt += f"\n\n## Previous Iteration Result (Round {iteration})\n"
                user_prompt += f"The previous attempt failed with the following result:\n"
                user_prompt += f"```\n{previous_result}\n```\n"
                user_prompt += f"Please analyze the failure and generate a fix.\n"

        return user_prompt

    async def _hydrate_prompt_inputs(
        self,
        values: Any,
        workflow_context: Dict[str, Any],
    ) -> Any:
        if isinstance(values, dict):
            hydrated: Dict[str, Any] = {}
            for key, value in values.items():
                hydrated[key] = await self._hydrate_prompt_inputs(value, workflow_context)

            raw_path = hydrated.get("path")
            if isinstance(raw_path, str) and raw_path.strip():
                try:
                    resolved_path = self._resolve_path(raw_path, workflow_context)
                    content = await self._read_file(resolved_path)
                    hydrated.setdefault("resolved_path", resolved_path)
                    hydrated.setdefault("content", content)
                except Exception:
                    pass
            return hydrated

        if isinstance(values, list):
            return [await self._hydrate_prompt_inputs(item, workflow_context) for item in values]

        return values

    @staticmethod
    def _has_authoritative_input_content(values: Any) -> bool:
        if isinstance(values, dict):
            if isinstance(values.get("content"), str) and values["content"].strip():
                return True
            return any(AgentContextBuilder._has_authoritative_input_content(value) for value in values.values())
        if isinstance(values, list):
            return any(AgentContextBuilder._has_authoritative_input_content(item) for item in values)
        return False

    def _collect_step_inputs(
        self,
        step,
        workflow_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not step:
            return {}

        raw_inputs = self._get_step_input_definition(step)
        if isinstance(raw_inputs, dict):
            return {
                key: value
                for key, value in raw_inputs.items()
                if key not in ["run_id", "workflow_key", "context_files"]
            }

        if not isinstance(raw_inputs, list):
            return {"input": raw_inputs}

        resolved: Dict[str, Any] = {}
        data = workflow_context.get("data", {}) if isinstance(workflow_context, dict) else {}
        params = data.get("params", {}) if isinstance(data.get("params", {}), dict) else {}
        step_outputs = data.get("step_outputs", {}) if isinstance(data.get("step_outputs", {}), dict) else {}

        for item in raw_inputs:
            if not isinstance(item, dict):
                continue

            source = item.get("source")
            if not source:
                continue

            value = self._resolve_workflow_input_source(
                source=source,
                item=item,
                data=data,
                params=params,
                step_outputs=step_outputs,
            )

            if (value is None or not self._payload_has_signal(value)) and isinstance(source, str):
                alias_step_ids = self._resolve_symbol_step_aliases(
                    workflow_context=workflow_context,
                    source=source,
                    step=step,
                    step_outputs=step_outputs,
                )
                for step_id in alias_step_ids:
                    output = step_outputs.get(step_id)
                    if not isinstance(output, dict):
                        continue
                    extracted = self._extract_authoritative_step_payload(output)
                    if not self._payload_has_signal(extracted):
                        extracted = self._resolve_alias_step_fallback_payload(
                            workflow_context=workflow_context,
                            step_id=step_id,
                            data=data,
                            params=params,
                            step_outputs=step_outputs,
                            visited_steps=set(),
                        )
                    if extracted is None and value is None:
                        extracted = self._sanitize_prompt_payload(output)
                    if extracted is not None:
                        value = extracted
                        break

            resolved[source] = value if value is not None else {"source": source, "required": item.get("required", True)}

        return resolved

    def _resolve_alias_step_fallback_payload(
        self,
        *,
        workflow_context: Dict[str, Any],
        step_id: str,
        data: Dict[str, Any],
        params: Dict[str, Any],
        step_outputs: Dict[str, Any],
        visited_steps: Optional[set[str]] = None,
    ) -> Any:
        if not isinstance(step_id, str) or not step_id.strip():
            return None

        visited = set(visited_steps or set())
        if step_id in visited:
            return None
        visited.add(step_id)

        step_def = self._find_template_step_definition(workflow_context, step_id)
        if not isinstance(step_def, dict):
            return None

        raw_inputs = step_def.get("inputs")
        if not isinstance(raw_inputs, list):
            raw_inputs = []

        for item in raw_inputs:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            if not isinstance(source, str) or not source.strip():
                continue

            direct_value = self._resolve_workflow_input_source(
                source=source,
                item=item,
                data=data,
                params=params,
                step_outputs=step_outputs,
            )
            if self._payload_has_signal(direct_value):
                return direct_value

            alias_step_ids = self._resolve_symbol_step_aliases(
                workflow_context=workflow_context,
                source=source,
                step=SimpleNamespace(depends_on=step_def.get("depends_on", [])),
                step_outputs=step_outputs,
            )
            for alias_step_id in alias_step_ids:
                if alias_step_id in visited:
                    continue
                output = step_outputs.get(alias_step_id)
                extracted = self._extract_authoritative_step_payload(output) if isinstance(output, dict) else None
                if self._payload_has_signal(extracted):
                    return extracted
                fallback = self._resolve_alias_step_fallback_payload(
                    workflow_context=workflow_context,
                    step_id=alias_step_id,
                    data=data,
                    params=params,
                    step_outputs=step_outputs,
                    visited_steps=visited,
                )
                if self._payload_has_signal(fallback):
                    return fallback
        return None

    def _find_template_step_definition(
        self,
        workflow_context: Dict[str, Any],
        step_id: str,
    ) -> Optional[Dict[str, Any]]:
        template_path = self._resolve_template_path(
            workflow_context.get("template_id") if isinstance(workflow_context, dict) else None
        )
        if template_path is None:
            return None

        try:
            raw_doc = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return None

        for stage in raw_doc.get("stages", []) if isinstance(raw_doc.get("stages"), list) else []:
            if not isinstance(stage, dict):
                continue
            for step_def in stage.get("steps", []) if isinstance(stage.get("steps"), list) else []:
                if isinstance(step_def, dict) and step_def.get("id") == step_id:
                    return step_def
        return None

    def _resolve_template_path(self, template_ref: Any) -> Optional[Path]:
        if not isinstance(template_ref, str) or not template_ref.strip():
            return None

        direct_path = Path(template_ref)
        if direct_path.exists():
            return direct_path

        candidate = self.project_root / template_ref
        if candidate.exists():
            return candidate

        registry_path = self.project_root / "config" / "workflow-registry.yaml"
        if not registry_path.exists():
            return None

        try:
            registry_doc = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return None

        workflows = registry_doc.get("workflows")
        if not isinstance(workflows, dict):
            return None

        entry = workflows.get(template_ref)
        if not isinstance(entry, dict):
            derived_keys = [template_ref]
            match = template_ref.strip().lower()
            import re
            normalized = re.match(r"^workflow\.([^.]+)\.task\.(.+)$", match)
            if normalized:
                department = normalized.group(1)
                workflow_name = normalized.group(2).replace("_", "-")
                derived_keys.append(f"{department}.{workflow_name}")
            for key in derived_keys:
                candidate_entry = workflows.get(key)
                if isinstance(candidate_entry, dict):
                    entry = candidate_entry
                    break
        if not isinstance(entry, dict):
            return None

        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None

        resolved = self.project_root / raw_path
        return resolved if resolved.exists() else None

    @staticmethod
    def _freeze_source_aliases(source: str) -> List[str]:
        if not isinstance(source, str):
            return []
        if source.endswith("_freeze_ref"):
            return [source[:-4]]
        if source.endswith("_freeze"):
            return [f"{source}_ref"]
        return []

    def _resolve_workflow_input_source(
        self,
        *,
        source: str,
        item: Optional[Dict[str, Any]] = None,
        data: Dict[str, Any],
        params: Dict[str, Any],
        step_outputs: Dict[str, Any],
    ) -> Any:
        candidate_keys = [source, *self._freeze_source_aliases(source)]
        for key in candidate_keys:
            if key in data:
                return self._sanitize_prompt_payload(data[key])
            if key in params:
                return self._sanitize_prompt_payload(params[key])
            if key in step_outputs:
                return self._sanitize_prompt_payload(step_outputs[key])

        if source == "external":
            return resolve_declared_external_input(
                item,
                data,
                params,
                transform=self._sanitize_prompt_payload,
            )
        return None

    def _resolve_symbol_step_aliases(
        self,
        *,
        workflow_context: Dict[str, Any],
        source: str,
        step=None,
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        if not isinstance(source, str) or not source.strip():
            return []

        template_path = self._resolve_template_path(
            workflow_context.get("template_id") if isinstance(workflow_context, dict) else None
        )

        aliases: List[str] = []
        if template_path is not None:
            try:
                raw_doc = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
            except Exception:
                raw_doc = {}

            for stage in raw_doc.get("stages", []) if isinstance(raw_doc.get("stages"), list) else []:
                if not isinstance(stage, dict):
                    continue
                for step_def in stage.get("steps", []) if isinstance(stage.get("steps"), list) else []:
                    if not isinstance(step_def, dict):
                        continue
                    step_id = step_def.get("id")
                    if not step_id:
                        continue
                    for output in step_def.get("outputs", []) if isinstance(step_def.get("outputs"), list) else []:
                        if isinstance(output, dict) and output.get("symbol") == source:
                            aliases.append(step_id)

        if aliases:
            return aliases

        depends_on = getattr(step, "depends_on", None)
        if isinstance(depends_on, list) and len(depends_on) == 1:
            candidate_step = depends_on[0]
            if isinstance(candidate_step, str) and candidate_step.strip():
                if not isinstance(step_outputs, dict) or candidate_step in step_outputs:
                    return [candidate_step]
        return aliases

    @staticmethod
    def _get_step_input_definition(step) -> Any:
        if not step:
            return {}

        raw_inputs = getattr(step, "inputs", None)
        if isinstance(raw_inputs, list) and raw_inputs:
            return raw_inputs
        if isinstance(raw_inputs, dict) and raw_inputs:
            return raw_inputs

        raw_inputs = getattr(step, "input", None)
        if raw_inputs not in (None, {}, []):
            return raw_inputs

        return {}

    def _extract_context_file_refs(self, step) -> List[str]:
        raw_inputs = self._get_step_input_definition(step)
        if isinstance(raw_inputs, dict):
            context_files = raw_inputs.get("context_files", [])
            return context_files if isinstance(context_files, list) else []
        return []

    async def _collect_upstream_step_outputs(
        self,
        step,
        workflow_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not step or not getattr(step, "depends_on", None):
            return {}

        data = workflow_context.get("data", {}) if isinstance(workflow_context, dict) else {}
        step_outputs = data.get("step_outputs", {}) if isinstance(data.get("step_outputs", {}), dict) else {}
        upstream: Dict[str, Any] = {}
        for step_id in step.depends_on:
            output = step_outputs.get(step_id)
            if output is not None:
                sanitized = self._sanitize_prompt_payload(output, allow_generated_text_fallback=False)
                sanitized = await self._hydrate_upstream_output_artifacts(sanitized, workflow_context)
                if self._payload_has_signal(sanitized):
                    upstream[step_id] = sanitized
        return upstream

    async def _hydrate_upstream_output_artifacts(
        self,
        value: Any,
        workflow_context: Dict[str, Any],
    ) -> Any:
        if isinstance(value, list):
            return [
                await self._hydrate_upstream_output_artifacts(item, workflow_context)
                for item in value
            ]

        if not isinstance(value, dict):
            return value

        hydrated: Dict[str, Any] = {}
        for key, item in value.items():
            hydrated[key] = await self._hydrate_upstream_output_artifacts(item, workflow_context)

        artifact_paths = hydrated.get("workspace_artifacts")
        if isinstance(artifact_paths, list):
            previews: List[Dict[str, Any]] = []
            for raw_path in artifact_paths[:2]:
                if not isinstance(raw_path, str) or not raw_path.strip():
                    continue
                try:
                    resolved_path = self._resolve_path(raw_path, workflow_context)
                    content = await self._read_file(resolved_path)
                except Exception:
                    continue
                previews.append(
                    {
                        "path": raw_path,
                        "content": self._truncate_text(content, 1600),
                    }
                )
            if previews:
                hydrated["workspace_artifact_previews"] = previews

        return hydrated

    @classmethod
    def _sanitize_prompt_payload(
        cls,
        value: Any,
        *,
        allow_generated_text_fallback: bool = True,
    ) -> Any:
        if isinstance(value, list):
            return [
                cls._sanitize_prompt_payload(
                    item,
                    allow_generated_text_fallback=allow_generated_text_fallback,
                )
                for item in value
            ]
        if not isinstance(value, dict):
            return value

        # Prefer canonical payload sections over executor wrapper metadata, but keep a
        # trimmed generated_text fallback when the structured sections carry no domain content.
        if any(key in value for key in ("business_output", "structured_payload", "ssot_output_contract")):
            sanitized: Dict[str, Any] = {}
            for key in ("business_output", "structured_payload", "ssot_output_contract", "freeze_meta", "outputs"):
                item = value.get(key)
                if item is not None:
                    cleaned = cls._sanitize_prompt_payload(
                        item,
                        allow_generated_text_fallback=allow_generated_text_fallback,
                    )
                    if cls._payload_has_signal(cleaned):
                        sanitized[key] = cleaned
            if sanitized:
                return sanitized
            generated_text = value.get("generated_text")
            if (
                allow_generated_text_fallback
                and isinstance(generated_text, str)
                and generated_text.strip()
            ):
                return {
                    "generated_text": generated_text[: cls._PROMPT_FALLBACK_TEXT_LIMIT].rstrip()
                }

        sanitized_dict: Dict[str, Any] = {}
        for key, item in value.items():
            if key in cls._PROMPT_WRAPPER_NOISE_KEYS:
                continue
            sanitized_dict[key] = cls._sanitize_prompt_payload(
                item,
                allow_generated_text_fallback=allow_generated_text_fallback,
            )
        return sanitized_dict

    @classmethod
    def _extract_authoritative_step_payload(cls, output: Dict[str, Any]) -> Any:
        if not isinstance(output, dict):
            return None

        for key in ("business_output", "structured_payload", "ssot_output_contract"):
            value = output.get(key)
            if value is None:
                continue
            cleaned = cls._sanitize_prompt_payload(value, allow_generated_text_fallback=False)
            if cls._payload_has_signal(cleaned):
                return cleaned

        cleaned_output = cls._sanitize_prompt_payload(output, allow_generated_text_fallback=False)
        if cls._payload_has_signal(cleaned_output):
            return cleaned_output
        return None

    @classmethod
    def _payload_has_signal(cls, value: Any) -> bool:
        if isinstance(value, dict):
            if not value:
                return False
            non_signal_keys = {
                "status",
                "paths",
                "workspace_artifacts",
                "model",
                "provider",
                "profile",
                "input_tokens",
                "output_tokens",
                "tokens_used",
                "duration_seconds",
                "stop_reason",
                "attempts",
                "temperature",
                "max_tokens",
            }
            for key, item in value.items():
                if key in non_signal_keys:
                    if isinstance(item, (dict, list)) and cls._payload_has_signal(item):
                        return True
                    continue
                if cls._payload_has_signal(item):
                    return True
            return False
        if isinstance(value, list):
            return any(cls._payload_has_signal(item) for item in value)
        if isinstance(value, str):
            return bool(value.strip())
        return value is not None

    def _append_prompt_kv_pairs(
        self,
        parts: List[str],
        values: Dict[str, Any],
    ) -> None:
        for key, value in values.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"- {key}: {value}")
            elif isinstance(value, (dict, list)):
                parts.append(f"- {key}:")
                parts.append(f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")

    def _build_output_contract_guidance(
        self,
        agent_spec: Dict[str, Any],
        step=None,
    ) -> List[str]:
        raw_data = agent_spec.get("_raw_data", {}) or {}
        contracts = raw_data.get("contracts", {}) or {}
        output_schema = contracts.get("output_schema")
        ssot_output_schema = contracts.get("ssot_output_schema")
        has_file_outputs = bool(
            step
            and hasattr(step, "outputs")
            and any(getattr(output, "type", "") == "file" for output in step.outputs or [])
        )

        lines: List[str] = []

        output_schema_text = self._load_contract_excerpt(agent_spec, output_schema)
        if output_schema_text:
            lines.append("Business output must conform to this schema excerpt:")
            lines.append("```yaml")
            lines.append(output_schema_text)
            lines.append("```")
            output_template = self._build_output_schema_template(agent_spec, output_schema)
            if output_template:
                lines.append("Fill this JSON template shape and replace placeholders with concrete values:")
                lines.append("```json")
                lines.append(output_template)
                lines.append("```")
            if not ssot_output_schema:
                lines.append(
                    "Return one machine-readable JSON or YAML object only, directly conforming to the business output schema."
                )
                lines.append(
                    "Do not add greetings, explanations, wrapper keys, or Markdown code fences."
                )

        ssot_example = ((raw_data.get("ssot_output_contract") or {}).get("example"))
        if ssot_output_schema:
            if has_file_outputs:
                lines.append(
                    "When file outputs are required, write the business artifact in the file section(s), "
                    "then include one additional section named `ssot_output_contract` as raw JSON or YAML."
                )
                lines.append(
                    "Do not wrap the full response in prose. File sections may use markdown headings plus fenced code blocks. "
                    "The `ssot_output_contract` section must be machine-readable."
                )
            else:
                lines.append(
                    "Return one machine-readable JSON or YAML object only, with top-level keys "
                    "`business_output` and `ssot_output_contract`."
                )
                lines.append(
                    "Do not invent wrapper keys like `feat_spec` or `result`. "
                    "The business object must itself conform to the output schema."
                )

        if ssot_example:
            try:
                rendered = json.dumps(ssot_example, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                rendered = yaml.safe_dump(ssot_example, allow_unicode=True, sort_keys=False).strip()
            lines.append("SSOT envelope example:")
            lines.append("```json")
            lines.append(rendered)
            lines.append("```")

        if lines:
            lines.append("Never add explanatory prose before or after the structured payload.")
            lines.append("Never use Markdown code fences unless the step explicitly requires file sections.")

        return lines

    def _load_contract_excerpt(
        self,
        agent_spec: Dict[str, Any],
        schema_ref: Optional[str],
    ) -> Optional[str]:
        if not schema_ref:
            return None
        if not isinstance(schema_ref, (str, os.PathLike)):
            return None
        spec_path = agent_spec.get("_spec_path")
        base_dir = Path(spec_path).parent if spec_path else self.project_root
        schema_path = Path(schema_ref)
        candidate_paths = self._resolve_contract_paths(base_dir, schema_path)
        raw = None
        for candidate in candidate_paths:
            try:
                raw = candidate.read_text(encoding="utf-8")
                break
            except OSError:
                continue
        if raw is None:
            return None

        excerpt = raw.strip()
        if len(excerpt) > 2800:
            excerpt = excerpt[:2800].rstrip() + "\n..."
        return excerpt

    def _resolve_contract_paths(self, base_dir: Path, schema_path: Path) -> List[Path]:
        if schema_path.is_absolute():
            return [schema_path]

        candidates: List[Path] = [(base_dir / schema_path).resolve()]
        spec_root = self.project_root / "spec-global"
        normalized_parts = list(schema_path.parts)
        while normalized_parts and normalized_parts[0] == "..":
            normalized_parts = normalized_parts[1:]
        if spec_root.exists() and normalized_parts:
            candidates.append((spec_root / Path(*normalized_parts)).resolve())
            for anchor in ("core", "cross", "departments"):
                if anchor in normalized_parts:
                    anchor_index = normalized_parts.index(anchor)
                    candidates.append((spec_root / Path(*normalized_parts[anchor_index:])).resolve())
                    break

        ordered: List[Path] = []
        for candidate in candidates:
            if candidate not in ordered:
                ordered.append(candidate)
        return ordered

    def _build_output_schema_template(
        self,
        agent_spec: Dict[str, Any],
        schema_ref: Optional[str],
    ) -> Optional[str]:
        schema = self._load_contract_schema(agent_spec, schema_ref)
        if not isinstance(schema, dict):
            return None
        template = self._build_schema_template_node(schema, schema)
        if not isinstance(template, dict):
            return None
        try:
            return json.dumps(template, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return None

    def _load_contract_schema(
        self,
        agent_spec: Dict[str, Any],
        schema_ref: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not schema_ref or not isinstance(schema_ref, (str, os.PathLike)):
            return None
        spec_path = agent_spec.get("_spec_path")
        base_dir = Path(spec_path).parent if spec_path else self.project_root
        schema_path = Path(schema_ref)
        for candidate in self._resolve_contract_paths(base_dir, schema_path):
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return None

    def _build_schema_template_node(
        self,
        node: Any,
        root_schema: Dict[str, Any],
        depth: int = 0,
    ) -> Any:
        if depth > 4:
            return "<value>"
        if not isinstance(node, dict):
            return "<value>"
        if "$ref" in node and isinstance(node["$ref"], str):
            resolved = self._resolve_schema_ref(root_schema, node["$ref"])
            if isinstance(resolved, dict):
                return self._build_schema_template_node(resolved, root_schema, depth + 1)
        if "const" in node:
            return node["const"]
        if isinstance(node.get("enum"), list) and node["enum"]:
            return node["enum"][0]

        node_type = node.get("type")
        if isinstance(node_type, list):
            node_type = next((item for item in node_type if item != "null"), node_type[0] if node_type else None)

        if node_type == "object" or ("properties" in node and isinstance(node.get("properties"), dict)):
            properties = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
            required = node.get("required") if isinstance(node.get("required"), list) else list(properties.keys())
            result: Dict[str, Any] = {}
            for key in required[:8]:
                child = properties.get(key, {})
                result[key] = self._build_schema_template_node(child, root_schema, depth + 1)
            return result
        if node_type == "array":
            items = node.get("items", {})
            child = self._build_schema_template_node(items, root_schema, depth + 1)
            return [child] if child not in (None, "", {}) else []
        if node_type == "integer":
            return 0
        if node_type == "number":
            return 0
        if node_type == "boolean":
            return False
        if node.get("format") == "date-time":
            return "2026-01-01T00:00:00Z"
        if node.get("format") == "date":
            return "2026-01-01"
        return "<string>"

    @staticmethod
    def _resolve_schema_ref(root_schema: Dict[str, Any], ref: str) -> Optional[Dict[str, Any]]:
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return None
        current: Any = root_schema
        for part in ref[2:].split("/"):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current if isinstance(current, dict) else None
