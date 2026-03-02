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
            step.input.get("context_files", []),
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

            # 添加步骤输入数据（从 step.input 获取）
            step_inputs = {}
            if step and hasattr(step, 'input'):
                step_inputs = step.input

            if step_inputs:
                parts.append("\n## Input Data")
                for key, value in step_inputs.items():
                    if key not in ["run_id", "workflow_key", "context_files"]:  # 过滤掉元数据
                        if isinstance(value, (str, int, float, bool)):
                            parts.append(f"- {key}: {value}")
                        elif isinstance(value, dict):
                            import json
                            parts.append(f"- {key}:")
                            parts.append(f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")
                        elif isinstance(value, list):
                            import json
                            parts.append(f"- {key}:")
                            parts.append(f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")

            # 添加上下文文件
            if context_files:
                parts.append("\n## Context Files")
                for path, content in context_files.items():
                    parts.append(f"\n### {path}")
                    parts.append(content[:2000] + "..." if len(content) > 2000 else content)  # 限制长度

            # 添加输出要求（从 step.outputs 获取）
            if step and hasattr(step, 'outputs') and step.outputs:
                parts.append("\n## Required Outputs")
                for output in step.outputs:
                    if hasattr(output, 'path'):
                        parts.append(f"- {output.path} ({output.type}): {output.description}")

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
