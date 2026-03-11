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
import yaml


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

            upstream_outputs = self._collect_upstream_step_outputs(step, workflow_context)
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

            if value is None and isinstance(source, str) and source.endswith("_specs"):
                base_name = source[:-1] if source.endswith("s") else source
                for step_id, output in step_outputs.items():
                    if not isinstance(output, dict):
                        continue
                    if "business_output" in output:
                        value = output["business_output"]
                        if step and step_id in getattr(step, "depends_on", []):
                            break

            resolved[source] = value if value is not None else {"source": source, "required": item.get("required", True)}

        return resolved

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
                return data[key]
            if key in params:
                return params[key]
            if key in step_outputs:
                return step_outputs[key]

        if source == "external" and isinstance(item, dict):
            raw_types = item.get("type", [])
            if isinstance(raw_types, str):
                raw_types = [raw_types]
            for type_name in raw_types:
                if not isinstance(type_name, str):
                    continue
                if type_name in data:
                    return data[type_name]
                if type_name in params:
                    return params[type_name]
        return None

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

    def _collect_upstream_step_outputs(
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
                upstream[step_id] = output
        return upstream

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
        if not schema_path.is_absolute():
            schema_path = (base_dir / schema_path).resolve()
        try:
            raw = schema_path.read_text(encoding="utf-8")
        except OSError:
            return None

        excerpt = raw.strip()
        if len(excerpt) > 2800:
            excerpt = excerpt[:2800].rstrip() + "\n..."
        return excerpt
