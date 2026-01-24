"""
Orchestrator CLI - 使用统一 Engine 接口的命令

这个模块提供了使用统一 Engine 接口的 CLI 命令，
与现有的 CLI 命令并存，作为新的推荐方式。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from .state_machine import StateMachine
from .event_log import EventLog
from .workflow_parser import WorkflowParser
from .agent_context import AgentContextBuilder
from .trace import TraceLog, SpanType, SpanStatus

# 导入统一的 Engine 接口
from flowcore.engines.protocol import StepExecutionRequest, StepExecutionResult, ArtifactReference
from flowcore.engines.base import EngineRegistry

# ANSI 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")


def print_info(text: str):
    print(f"{CYAN}ℹ️  {text}{RESET}")


async def cmd_run_engine(args):
    """
    使用统一 Engine 接口执行步骤

    这是新的推荐方式，与 cmd_next 功能类似，
    但使用统一的 Engine 接口而不是依赖外部 AI 工具。

    用法：
        python -m flowcore.orchestrator run-engine <project_dir> [step_id]
    """
    project_dir = args.project_dir
    step_id = getattr(args, 'step_id', None)

    # 初始化状态机
    sm = StateMachine(project_dir)
    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    # 加载 workflow
    workflow_file = Path(project_dir) / "workflow.yaml"
    if not workflow_file.exists():
        print_error("workflow.yaml not found")
        return 1

    parser = WorkflowParser(str(workflow_file))
    workflow = parser.workflow

    # 获取要执行的步骤
    if step_id:
        # 指定步骤
        ready_steps = [step_id]
    else:
        # 自动选择下一个就绪步骤
        ready_steps = sm.get_ready_steps()
        if not ready_steps:
            print_info("No ready steps available")
            return 0
        step_id = ready_steps[0]
        ready_steps = [step_id]

    # 执行步骤
    step_id = ready_steps[0]

    try:
        result = await _execute_step_with_engine(
            project_dir=project_dir,
            step_id=step_id,
            workflow=workflow,
            state=state
        )

        if result.status == "completed":
            print_success(f"Step '{step_id}' completed successfully")

            # 显示输出产物
            if result.outputs:
                print(f"\n{CYAN}Outputs:{RESET}")
                for out in result.outputs:
                    if out.path:
                        print(f"  - {out.path}")
                    if out.summary:
                        print(f"    {out.summary}")

            # 完成步骤
            outputs = result.get_output_paths()
            sm.complete_step(step_id, outputs)

            # 记录事件
            event_log = EventLog(project_dir, state["run_id"])
            event_log.log_step_completed(step_id, result.engine_type or "engine", outputs, "")
            event_log.log_validation_passed(step_id, "engine_execution")

            return 0
        else:
            print_error(f"Step '{step_id}' failed: {result.error}")
            if result.error_details:
                import json
                print(json.dumps(result.error_details, indent=2))
            return 1

    except Exception as e:
        print_error(f"Failed to execute step: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def _execute_step_with_engine(
    project_dir: str,
    step_id: str,
    workflow: dict,
    state: dict
) -> StepExecutionResult:
    """
    使用统一 Engine 接口执行步骤

    Args:
        project_dir: 项目目录
        step_id: 步骤 ID
        workflow: 工作流定义
        state: 状态

    Returns:
        执行结果
    """
    print_info(f"Executing step '{step_id}' with unified Engine interface...")

    # 1. 解析步骤定义
    step_data = None
    for step in workflow.get("steps", []):
        if step.get("id") == step_id:
            step_data = step
            break

    if not step_data:
        raise ValueError(f"Step '{step_id}' not found in workflow")

    # 2. 加载 Agent 规范
    # 尝试多种可能的字段名
    agent_ref = step_data.get("run", "") or step_data.get("agent", "")
    if isinstance(agent_ref, dict):
        agent_ref = agent_ref.get("ref", "")

    # 构建 Agent 规范（简化版，完整版应该从 spec 文件加载）
    agent_spec = _build_agent_spec(project_dir, agent_ref, step_data)

    # 3. 构建执行上下文
    context = _build_execution_context(step_id, step_data, workflow, state, project_dir)

    # 4. 创建执行请求
    request = StepExecutionRequest(
        project_dir=project_dir,
        step_id=step_id,
        run_id=state["run_id"],
        agent_spec=agent_spec,
        context=context,
        token_id=state.get("steps", {}).get(step_id, {}).get("token"),
        timeout_seconds=3600
    )

    # 5. 通过 EngineRegistry 创建 Executor
    engine_type = agent_spec.get('engine', {}).get('type', 'llm')
    print_info(f"Creating executor for engine type: '{engine_type}'")
    executor = EngineRegistry.create(agent_spec, project_dir)

    # 6. 执行步骤
    print_info(f"Starting execution with {executor.get_engine_type()} engine...")

    # 调试：显示引擎配置
    import json
    print_debug(f"Engine config: {json.dumps(agent_spec.get('engine', {}), indent=2)}")

    result = await executor.execute(request)

    return result

# 添加调试打印
def print_debug(text: str):
    print(f"[DEBUG] {text}")


def _build_agent_spec(project_dir: str, agent_ref: str, step_data: dict) -> dict:
    """
    构建 Agent 或 Skill 规范

    Args:
        project_dir: 项目目录
        agent_ref: Agent/Skill 引用（如 "agent:developer" 或 "skill:ci.run_tests"）
        step_data: 步骤定义

    Returns:
        Agent 或 Skill 规范
    """
    # 检查步骤类型
    step_kind = step_data.get("kind", "agent")

    # 完整版：从 spec 文件加载
    # 简化版：从 step_data 构建

    if step_kind == "skill":
        # Skill 步骤 - 使用 Skill 规范
        skill_ref = step_data.get("skill", agent_ref)

        # 尝试从 ai-spec/skills/ 加载（相对于项目目录）
        spec_path = Path(project_dir) / "ai-spec" / "skills" / f"{skill_ref}.yaml"
        if spec_path.exists():
            import yaml
            with open(spec_path) as f:
                spec = yaml.safe_load(f)
                # 迁移旧格式到新格式
                spec = _migrate_skill_spec(spec)
                return spec

        # 如果没有找到 spec 文件，从 step_data 构建
        engine_config = step_data.get("engine", {"type": "shell"})
        if not engine_config.get("type"):
            engine_config["type"] = "shell"

        return {
            "id": skill_ref,
            "kind": "skill",
            "name": step_data.get("name", skill_ref),
            "description": step_data.get("description", ""),
            "engine": engine_config,
            "outputs": step_data.get("outputs", [])
        }
    else:
        # Agent 步骤 - 使用 Agent 规范
        agent_id = agent_ref.replace("agent:", "") if agent_ref.startswith("agent:") else agent_ref

        # 获取项目根目录（向上查找到包含 spec-global 的目录）
        project_path = Path(project_dir).resolve()
        while project_path.name != "" and not (project_path / "spec-global").exists():
            parent = project_path.parent
            if parent == project_path:
                break
            project_path = parent

        # 尝试多个路径加载 agent spec
        spec_paths = [
            project_path / "ai-spec" / "agents" / agent_id / "agent.yaml",  # 旧路径
            project_path / "spec-global" / "departments" / "stg" / "agents" / agent_id / "v1" / "agent.yaml",  # 新路径
            project_path / "spec-global" / "departments" / "prd" / "agents" / agent_id / "v1" / "agent.yaml",
            project_path / "spec-global" / "departments" / "dev" / "agents" / agent_id / "v1" / "agent.yaml",
            project_path / "spec-global" / "departments" / "qa" / "agents" / agent_id / "v1" / "agent.yaml",
            project_path / "spec-global" / "departments" / "ui" / "agents" / agent_id / "v1" / "agent.yaml",
        ]

        for spec_path in spec_paths:
            if spec_path.exists():
                import yaml
                with open(spec_path) as f:
                    spec = yaml.safe_load(f)
                    return spec

        # 如果没有找到 spec 文件，从 step_data 构建
        engine_config = step_data.get("engine", {"type": "llm"})
        if not engine_config.get("type"):
            engine_config["type"] = "llm"

        return {
            "id": agent_ref,
            "kind": "agent",
            "name": step_data.get("name", agent_ref),
            "description": step_data.get("description", ""),
            "engine": engine_config,
            "system_prompt": step_data.get("system_prompt", ""),
            "instructions": step_data.get("instructions", []),
            "outputs": step_data.get("outputs", [])
        }


def _migrate_skill_spec(spec: dict) -> dict:
    """
    迁移旧格式的 Skill spec 到新格式

    旧格式：command 使用 "cd {{ project_dir }} && ..."
    新格式：command 使用简单命令，working_dir 指定工作目录
    """
    engine_config = spec.get("engine", {})

    # 检查是否需要迁移
    command = engine_config.get("command", "")
    if "{{ project_dir }}" in command or "{{ project_dir}}" in command:
        # 旧格式：需要迁移
        import re

        # 提取 cd 后面的命令
        match = re.search(r'cd\s*\{\{\s*project_dir\s*}}\s*&&\s*(.+)', command, re.DOTALL)
        if match:
            new_command = match.group(1).strip()
            working_dir = "{{ project_dir }}"

            engine_config["command"] = new_command
            engine_config["working_dir"] = working_dir

    return spec


def _get_step_by_id(step_id: str, workflow: dict) -> Optional[dict]:
    """
    Get step definition by ID from workflow

    Args:
        step_id: Step ID
        workflow: Workflow definition

    Returns:
        Step definition dict or None if not found
    """
    for step in workflow.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


def _build_execution_context(
    step_id: str,
    step_data: dict,
    workflow: dict,
    state: dict,
    project_dir: str = "."
) -> dict:
    """
    构建执行上下文

    Args:
        step_id: 步骤 ID
        step_data: 步骤定义
        workflow: 工作流定义
        state: 状态
        project_dir: 项目目录路径

    Returns:
        执行上下文
    """
    import yaml

    project_path = Path(project_dir).resolve()

    # 构建输入产物
    inputs = []

    # 从依赖获取上游产物
    deps = step_data.get("depends_on", [])
    for dep_id in deps:
        dep_state = state.get("steps", {}).get(dep_id, {})
        dep_outputs = dep_state.get("outputs", [])

        # Check if this dependency is a human gate
        dep_step = _get_step_by_id(dep_id, workflow)
        dep_kind = dep_step.get("kind", "") if dep_step else ""
        is_human_gate = dep_kind == "human_gate"

        # For human gates, read from gate file and its dependencies
        if is_human_gate:
            # Read the gate file
            gate_file = project_path / ".workflow" / "gates" / f"{dep_id}.yaml"
            if gate_file.exists():
                with open(gate_file, 'r', encoding='utf-8') as f:
                    gate_data = yaml.safe_load(f)

                # Build gate summary
                gate_summary = f"# Gate: {gate_data.get('step_name', dep_id)}\n\n"
                gate_summary += f"**Status**: {gate_data.get('status', 'unknown')}\n"
                if gate_data.get('comment'):
                    gate_summary += f"**Comment**: {gate_data['comment']}\n"
                if gate_data.get('checklist'):
                    gate_summary += "\n**Checklist**:\n"
                    for item in gate_data['checklist']:
                        status = "✓" if item.get('ok') else "✗"
                        gate_summary += f"  {status} {item.get('item')}: {item.get('note', '')}\n"

                # Read the freeze contract if it exists
                freeze_contract_path = project_path / "contracts" / dep_id.replace('freeze_', '') / "v1" / "freeze.yaml"
                freeze_content = ""
                if freeze_contract_path.exists():
                    with open(freeze_contract_path, 'r', encoding='utf-8') as f:
                        freeze_content = f.read()
                    gate_summary += f"\n## Freeze Contract\n\n{freeze_content}\n"
                else:
                    # If no freeze contract, read all upstream analysis files
                    gate_summary += "\n## Upstream Analysis\n\n"
                    gate_deps = gate_data.get('depends_on', [])
                    for gate_dep_id in gate_deps:
                        dep_file = project_path / ".workflow" / "workspace" / gate_dep_id / "response.txt"
                        if dep_file.exists():
                            with open(dep_file, 'r', encoding='utf-8') as f:
                                dep_content = f.read()
                                # Truncate if too long
                                if len(dep_content) > 5000:
                                    dep_content = dep_content[:5000] + "\n\n...[truncated]"
                                gate_summary += f"\n### {gate_dep_id}\n\n```\n{dep_content}\n```\n\n"

                inputs.append({
                    "id": dep_id,
                    "path": str(gate_file.relative_to(project_path)),
                    "summary": f"Gate approval: {gate_data.get('step_name', dep_id)}",
                    "content": gate_summary
                })
            else:
                # Gate file not found, add warning
                import sys
                print(f"[WARNING] Gate file not found for '{dep_id}': {gate_file}", file=sys.stderr)
                inputs.append({
                    "id": dep_id,
                    "path": None,
                    "summary": f"Gate file not found: {dep_id}",
                    "content": f"[Gate file not found for {dep_id}]"
                })
        else:
            # Regular step - read from workspace outputs
            for out_path in dep_outputs:
                # 读取文件内容
                content = ""
                full_path = project_path / out_path
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Warn if file is empty
                        if not content or len(content.strip()) == 0:
                            import sys
                            print(
                                f"[WARNING] Empty file read from upstream step '{dep_id}': {out_path}",
                                file=sys.stderr
                            )
                            print(
                                f"[WARNING] This may indicate the previous step failed or produced no output.",
                                file=sys.stderr
                            )
                            content = f"[Empty file from {dep_id}. File path: {out_path}]"

                    except Exception as e:
                        content = f"[Error reading file: {e}]"
                        import sys
                        print(f"[ERROR] Failed to read file {out_path}: {e}", file=sys.stderr)
                else:
                    content = "[File not found]"
                    import sys
                    print(f"[ERROR] File not found: {out_path}", file=sys.stderr)

                inputs.append({
                    "id": dep_id,
                    "path": out_path,
                    "summary": f"Output from {dep_id}",
                    "content": content  # 添加文件内容
                })

    # 构建契约
    contracts = {}
    output_validation = step_data.get("output_validation")
    if output_validation:
        contracts["output_schema"] = {
            "schema_type": "json",
            "schema": output_validation
        }

    # 构建项目元信息
    project_meta = {
        "name": workflow.get("name", ""),
        "id": workflow.get("id", ""),
        "run_id": state.get("run_id", "")
    }

    return {
        "step_description": step_data.get("description", ""),
        "inputs": inputs,
        "contracts": contracts,
        "project_meta": project_meta,
        "workflow_info": {
            "workflow_id": workflow.get("id"),
            "workflow_name": workflow.get("name")
        }
    }


# 导出函数供主 CLI 使用
def register_run_engine_command(subparsers):
    """
    注册 run-engine 命令到主 CLI

    Usage:
        from flowcore.orchestrator.cli import main
        # 在 cli.py 中:
        from .engine_commands import register_run_engine_command
        register_run_engine_command(subparsers)
    """
    p_run = subparsers.add_parser(
        "run-engine",
        help="Execute step with unified Engine interface (new recommended way)"
    )
    p_run.add_argument("project_dir", help="Project directory")
    p_run.add_argument("step_id", nargs="?", help="Step ID (optional, auto-select if not provided)")
    p_run.set_defaults(command="run_engine", func=cmd_run_engine)

    return p_run
