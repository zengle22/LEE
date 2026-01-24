#!/usr/bin/env python3
"""
Workflow Orchestrator CLI

通用的 AI 工作流编排器命令行工具

用法:
  python -m orchestrator init <project_dir> --workflow <workflow.yaml>
  python -m orchestrator status <project_dir>
  python -m orchestrator next <project_dir>
  python -m orchestrator start <project_dir> <step_id> [--inject-context] [--injector <name>]
  python -m orchestrator complete <project_dir> <step_id> [--outputs file1,file2]
  python -m orchestrator validate <project_dir> <step_id>
  python -m orchestrator approve <project_dir> <gate_id> --approver <name>
  python -m orchestrator reject <project_dir> <gate_id> --approver <name> --reason <reason>
  python -m orchestrator token <project_dir> <step_id>
  python -m orchestrator check <project_dir> --token <token_id>
  python -m orchestrator log <project_dir> [--step <step_id>]
  python -m orchestrator export <project_dir> --format <json|yaml>
  python -m orchestrator trace <project_dir> [--format markdown|yaml]
  python -m orchestrator context <project_dir> [--clear] [--injector <name>]

测试流程扩展命令 (v1.3 新增):
  python -m orchestrator loop-start <project_dir> <loop_id>
  python -m orchestrator loop-complete <project_dir> <loop_id> [--continue]
  python -m orchestrator wait <project_dir> <step_id> --event <event_type> [--timeout 48h]
  python -m orchestrator resolve <project_dir> <wait_id> --resolver <name> [--data <json>]
  python -m orchestrator loop-back <project_dir> <from_step> <to_step> [--reason <reason>]

特性:
  - 使用 TracedStateMachine 自动记录 span-based 执行追踪
  - 追踪日志存放在 .workflow/traces/traces.jsonl
  - 使用 trace 命令查看和导出追踪报告

Agent 自动调度 (v1.2 新增):
  - 步骤开始时自动加载 workflow.yaml 中定义的 Agent spec
  - 生成 .workflow/current-context.yaml 供 AI 工具读取
  - 支持多种 AI 工具: Claude Code (已实现), Codex/Gemini/OpenCode (预留)
  - 使用 context 命令查看当前注入的 Agent 上下文

测试流程支持 (v1.3 新增):
  - 循环执行: 支持 bug 修复验证循环等迭代场景
  - 外部等待: 支持等待开发修复等外部事件
  - Loop Back: 支持从失败的门禁回退到之前的步骤
  - 增强状态机: 新增 WAITING_EXTERNAL, LOOP_ITERATION 状态
"""

import sys
import argparse
import yaml
import json
import asyncio
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from .state_machine import StateMachine, StepState, RunState
from .tracing_integration import TracedStateMachine
from .trace import TraceLog, SpanType, SpanStatus
from .event_log import EventLog, EventType
from .token_manager import TokenManager, ToolGuard
from .workflow_parser import WorkflowParser
from .agent_context import AgentContextBuilder
from .agent_injector import InjectorRegistry
from .workflow_generator import (
    WorkflowGenerator,
    PhaseConfig,
    validate_workflow_against_template,
)
from .engine_commands import cmd_run_engine as cmd_run_engine_async
from .project_config import (
    init_project_structure,
    check_project_structure_initialized,
    require_project_structure,
    get_project_structure
)

# ANSI 颜色
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{BLUE}{BOLD}{'═' * 60}{RESET}")
    print(f"{BLUE}{BOLD}  {text}{RESET}")
    print(f"{BLUE}{BOLD}{'═' * 60}{RESET}\n")


def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str):
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text: str):
    print(f"{CYAN}ℹ️  {text}{RESET}")


def _resolve_agent_id(project_dir: str, step_id: str, state: dict, fallback: str = "auto") -> str:
    """从 workflow.yaml 解析步骤的 agent_id

    优先级:
    1. state 中存储的 agent_id (如果不是 "auto" 或空)
    2. workflow.yaml 中定义的 run: 字段
    3. fallback 值 (默认 "auto")

    Args:
        project_dir: 项目目录
        step_id: 步骤 ID
        state: 工作流状态
        fallback: 后备值

    Returns:
        解析后的 agent_id
    """
    # 尝试从 state 获取
    step_data = state.get("steps", {}).get(step_id, {})
    agent_id = step_data.get("agent_id") or ""

    # 如果是 "auto" 或空，尝试从 workflow.yaml 重新读取
    if not agent_id or agent_id == "auto":
        try:
            workflow_file = Path(project_dir) / state.get("workflow_file", "workflow.yaml")
            if workflow_file.exists():
                parser = WorkflowParser(str(workflow_file))
                steps = parser.parse()
                for step in steps:
                    if step.id == step_id and step.agent_id:
                        return step.agent_id
        except Exception:
            pass

    return agent_id if agent_id and agent_id != "auto" else fallback


def _load_workflow_from_project(project_dir: str) -> dict:
    """从项目目录加载 workflow.yaml

    Args:
        project_dir: 项目目录

    Returns:
        workflow dict，如果不存在则返回 None
    """
    project_path = Path(project_dir)
    workflow_path = project_path / "workflow.yaml"

    if workflow_path.exists():
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            pass

    return None


def _extract_directories_from_workflow(workflow: dict) -> set:
    """从 workflow.yaml 的 outputs 中提取需要创建的目录

    Args:
        workflow: 解析后的 workflow dict

    Returns:
        目录路径集合 (不含 @ 前缀)
    """
    directories = set()

    steps = workflow.get("steps", [])
    for step in steps:
        outputs = step.get("outputs", [])
        for output in outputs:
            # output 可能是字符串或 dict
            if isinstance(output, dict):
                path = output.get("path", "")
            else:
                path = str(output)

            # 移除 @ 前缀
            if path.startswith("@"):
                path = path[1:]

            # 提取目录部分 (去掉文件名)
            if "/" in path:
                dir_path = "/".join(path.split("/")[:-1])
                if dir_path:
                    directories.add(dir_path)

    return directories


def _create_phase_directories(project_dir: str, workflow: dict = None) -> list:
    """创建 Phase 目录结构

    优先从 workflow.yaml 的 outputs 动态提取目录。
    如果没有 workflow，使用最小默认结构。

    Args:
        project_dir: 项目目录
        workflow: 可选的 workflow dict，用于动态提取目录

    Returns:
        创建的目录列表
    """
    project_path = Path(project_dir)

    # 如果有 workflow，从 outputs 动态提取目录
    if workflow:
        directories = _extract_directories_from_workflow(workflow)
        # 确保基础目录存在
        directories.add("output")
        directories.add(".workflow")
    else:
        # 最小默认结构 (向后兼容)
        directories = {
            "openspec",
            "output",
            ".workflow",
        }

    created = []
    for dir_path in sorted(directories):
        full_path = project_path / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            created.append(dir_path)

    return created


def _validate_project_config(project_dir: str) -> tuple:
    """验证项目配置 (project.yaml)

    在 orchestrator 初始化之前验证：
    1. project.yaml 存在且格式正确
    2. 所有必需字段已填写
    3. 仓库路径存在
    4. 路径别名引用正确

    Args:
        project_dir: 项目目录 (phase 目录或其父目录)

    Returns:
        (is_valid, list of error messages)
    """
    from pathlib import Path

    project_path = Path(project_dir).resolve()

    # 向上查找 project.yaml
    project_yaml = None
    current = project_path
    for _ in range(10):
        candidate = current / "project.yaml"
        if candidate.exists():
            project_yaml = candidate
            break
        parent = current.parent
        if parent == current:
            break
        current = parent

    if not project_yaml:
        # 没有 project.yaml 不是错误，只是警告
        print(f"  {YELLOW}Note: No project.yaml found (optional){RESET}")
        return True, []

    print(f"  {CYAN}Validating: {project_yaml}{RESET}")

    # 尝试导入验证器
    try:
        import sys
        # 添加 ai-spec/tools 到路径
        ai_spec_tools = project_yaml.parent.parent / "ai-spec" / "tools"
        if ai_spec_tools.exists() and str(ai_spec_tools) not in sys.path:
            sys.path.insert(0, str(ai_spec_tools))

        from validate.validators.project_config import validate_project_config
        return validate_project_config(project_yaml)

    except ImportError:
        # 如果验证器不可用，使用内置的简单验证
        return _simple_project_validation(project_yaml)


def _simple_project_validation(project_yaml: Path) -> tuple:
    """简单的项目配置验证 (当完整验证器不可用时)"""
    import yaml
    from pathlib import Path

    errors = []

    try:
        with open(project_yaml, encoding='utf-8') as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"Invalid YAML: {e}"]

    if not isinstance(content, dict):
        return False, ["project.yaml must be a YAML object"]

    # 必需字段
    for field in ["kind", "version", "id", "name"]:
        if field not in content:
            errors.append(f"Missing required field: {field}")

    # kind 检查
    if content.get("kind") != "project":
        errors.append(f"Invalid kind: '{content.get('kind')}', expected 'project'")

    # 仓库路径检查
    repos = content.get("repositories", {})
    base_path = project_yaml.parent

    for repo_id, repo_config in repos.items():
        if isinstance(repo_config, str):
            repo_path = repo_config
        elif isinstance(repo_config, dict):
            repo_path = repo_config.get("path")
            if not repo_path:
                errors.append(f"Repository '{repo_id}' missing 'path'")
                continue
        else:
            errors.append(f"Repository '{repo_id}' invalid format")
            continue

        resolved = (base_path / repo_path).resolve()
        if not resolved.exists():
            errors.append(f"Repository '{repo_id}' path not found: {resolved}")
        elif not resolved.is_dir():
            errors.append(f"Repository '{repo_id}' path is not a directory: {resolved}")

    return len(errors) == 0, errors


def cmd_generate_workflow(args):
    """Generate workflow.yaml from template and phase config.

    Usage:
        python -m orchestrator generate-workflow \\
            --template ai-spec/specs/.../phase-openspec-flow/v1/workflow.yaml \\
            --config ./phase-config.yaml \\
            --output ./workflow.yaml
    """
    template_path = args.template
    config_path = getattr(args, 'config', None)
    output_path = args.output

    print_header("Generate Workflow")

    # 1. Load phase config
    try:
        if config_path:
            config = WorkflowGenerator.load_phase_config(config_path)
            print(f"  Config:   {config_path}")
        else:
            # Use CLI arguments
            phase_dir = getattr(args, 'phase_dir', None) or '.'
            config = PhaseConfig(
                id=getattr(args, 'phase_id', None) or "generated-phase",
                name=getattr(args, 'phase_name', None) or "Generated Phase",
                phase_dir=phase_dir,
                change_id=getattr(args, 'change_id', None) or "CHG-001",
                project_dir=getattr(args, 'project_dir', None) or "",
            )
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        return 1

    print(f"  Phase ID: {config.id}")
    print(f"  Name:     {config.name}")

    # 2. Initialize generator
    try:
        generator = WorkflowGenerator(template_path)
        print(f"  Template: {template_path}")

        # Show template info
        template_steps = len(generator.template.get("steps", []))
        print(f"  Template steps: {template_steps}")
    except FileNotFoundError:
        print_error(f"Template not found: {template_path}")
        return 1
    except Exception as e:
        print_error(f"Failed to load template: {e}")
        return 1

    # 3. Generate workflow
    result = generator.generate(config, output_path)

    # 4. Report results
    if result.warnings:
        for warning in result.warnings:
            print_warning(warning)

    if result.success:
        print_success(f"Workflow generated: {result.workflow_path}")
        print(f"  Steps: {result.step_count}")
        print_info(f"Next: python -m orchestrator init <project_dir> --workflow {result.workflow_path}")
        return 0
    else:
        print_error("Workflow generation failed:")
        for err in result.errors:
            print(f"    {RED}- {err}{RESET}")
        return 1


def cmd_init(args):
    """初始化工作流运行"""
    project_dir = args.project_dir
    workflow_path = args.workflow
    template_path = getattr(args, 'template', None)

    # === Directory Structure Initialization (NEW) ===
    print_header("Initializing Project Structure")
    skip_structure_init = getattr(args, 'skip_structure_init', False)
    if not skip_structure_init:
        try:
            dir_config = init_project_structure(Path(project_dir))
            print_success(f"Directory structure initialized: {dir_config.version}")
        except Exception as e:
            print_error(f"Failed to initialize directory structure: {e}")
            print_info("Use --skip-structure-init to bypass (not recommended)")
            return 1
    else:
        # Verify structure exists if not skipping
        is_initialized, _ = check_project_structure_initialized(Path(project_dir))
        if not is_initialized:
            print_error("Project structure not initialized and --skip-structure-init is set")
            print_info("Either remove --skip-structure-init or initialize the structure separately")
            return 1

    # === 项目配置验证 (在初始化前执行) ===
    skip_validation = getattr(args, 'skip_validation', False)
    if not skip_validation:
        validation_passed, validation_errors = _validate_project_config(project_dir)
        if not validation_passed:
            print_error("Project configuration validation failed:")
            for err in validation_errors:
                print(f"    {RED}- {err}{RESET}")
            print_info("Fix the errors above or use --skip-validation to bypass (not recommended)")
            return 1

    # === 工作流结构验证 (v1.6 新增) ===
    skip_workflow_validation = getattr(args, 'skip_workflow_validation', False)
    if not skip_workflow_validation and template_path:
        workflow_valid, workflow_errors = validate_workflow_against_template(
            workflow_path,
            template_path
        )
        if not workflow_valid:
            print_error("Workflow structure validation failed:")
            for err in workflow_errors:
                print(f"    {RED}- {err}{RESET}")
            print_info(f"Workflow must match template: {template_path}")
            print_info("Use 'python -m orchestrator generate-workflow' to generate a valid workflow")
            print_info("Or use --skip-workflow-validation to bypass (not recommended)")
            return 1
        print_success("Workflow structure validation passed")

    # 解析 workflow
    parser = WorkflowParser(workflow_path)
    workflow = parser.workflow

    # 初始化状态机 (使用 TracedStateMachine 自动记录 spans)
    sm = TracedStateMachine(project_dir)
    run_id = sm.init(workflow)

    # 初始化事件日志
    event_log = EventLog(project_dir, run_id)
    event_log.log_run_created(
        workflow.get("id", "unknown"),
        workflow.get("name", "unknown")
    )

    # 创建 Phase 目录结构 (从 workflow 动态提取)
    created_dirs = _create_phase_directories(project_dir, workflow)

    print_header("Workflow Initialized")
    print(f"  Run ID:      {run_id}")
    print(f"  Workflow:    {workflow.get('name')}")
    print(f"  Project:     {project_dir}")
    print(f"  State file:  {sm.state_path}")

    # 显示步骤概览
    steps = parser.parse()
    print(f"\n  Total steps: {len(steps)}")

    gates = [s for s in steps if s.gate]
    print(f"  Human gates: {len(gates)}")

    # 显示创建的目录
    if created_dirs:
        print(f"\n  {CYAN}Phase directories:{RESET}")
        for d in created_dirs:
            print(f"    - {d}/")

    print_success("Ready to start execution")
    print_info(f"Run 'python -m orchestrator status {project_dir}' to see current state")


def cmd_status(args):
    """显示当前状态"""
    project_dir = args.project_dir

    sm = TracedStateMachine(project_dir)
    try:
        summary = sm.get_summary()
    except FileNotFoundError:
        print_error(f"No workflow state found in {project_dir}")
        print_info("Run 'python -m orchestrator init' first")
        return 1

    print_header("Workflow Status")

    # 基本信息
    print(f"  Run ID:       {summary['run_id']}")
    state = summary['run_state']
    state_color = {
        "running": GREEN,
        "paused": YELLOW,
        "completed": GREEN,
        "failed": RED
    }.get(state, RESET)
    print(f"  State:        {state_color}{state}{RESET}")
    print(f"  Current step: {summary.get('current_step') or 'None'}")

    # 步骤统计
    print(f"\n  {BOLD}Step Progress:{RESET}")
    for state, count in summary['step_counts'].items():
        color = {
            "completed": GREEN,
            "in_progress": CYAN,
            "pending": RESET,
            "failed": RED,
            "gate_pending": YELLOW
        }.get(state, RESET)
        print(f"    {color}● {state}: {count}{RESET}")

    # 门禁状态
    print(f"\n  {BOLD}Gates:{RESET}")
    for state, count in summary['gate_counts'].items():
        if count > 0:
            color = {
                "approved": GREEN,
                "pending": YELLOW,
                "rejected": RED
            }.get(state, RESET)
            print(f"    {color}● {state}: {count}{RESET}")

    # 待审批门禁
    pending_gates = summary.get('pending_gates', [])
    if pending_gates:
        print(f"\n  {YELLOW}{BOLD}⏳ Pending Gates (BLOCKING):{RESET}")
        for gate_id in pending_gates:
            print(f"    - {gate_id}")
            print(f"      {CYAN}Approve: python -m orchestrator approve {project_dir} {gate_id} --approver <name>{RESET}")

    # 可执行步骤
    ready_steps = summary.get('ready_steps', [])
    if ready_steps:
        print(f"\n  {GREEN}{BOLD}Ready Steps:{RESET}")
        for step_id in ready_steps:
            print(f"    - {step_id}")

    # Run-to-Gate 决策信息 (用于 AI 自动执行)
    next_info = summary.get('next_step_info', {})
    if next_info:
        print(f"\n  {BOLD}Run-to-Gate Decision:{RESET}")
        print(f"    next_step: {next_info.get('next_step') or 'null'}")
        print(f"    next_step_human_gate: {str(next_info.get('next_step_human_gate', False)).lower()}")
        print(f"    action: {next_info.get('action', 'unknown')}")

        action = next_info.get('action')
        if action == 'continue':
            print(f"\n  {GREEN}➡️  ACTION: Auto-continue to {next_info.get('next_step')}{RESET}")
        elif action == 'wait_for_approval':
            gate_id = next_info.get('gate_id', 'unknown')
            print(f"\n  {YELLOW}⏸️  ACTION: Wait for gate approval ({gate_id}){RESET}")
        elif action == 'workflow_done':
            print(f"\n  {GREEN}✅ ACTION: Workflow completed{RESET}")

    # 测试流程扩展: 循环状态
    loops = summary.get('loops', {})
    if loops:
        print(f"\n  {BOLD}Loop Status:{RESET}")
        for loop_id, loop_info in loops.items():
            status_color = {
                "pending": RESET,
                "running": CYAN,
                "completed": GREEN,
                "max_reached": YELLOW,
                "failed": RED
            }.get(loop_info['status'], RESET)
            print(f"    {loop_id}:")
            print(f"      {status_color}● Status: {loop_info['status']}{RESET}")
            print(f"      Iteration: {loop_info['iteration']} / {loop_info['max']}")

    # 测试流程扩展: 外部等待状态
    pending_waits = summary.get('pending_external_waits', [])
    if pending_waits:
        print(f"\n  {YELLOW}{BOLD}⏳ External Waits (BLOCKING):{RESET}")
        for wait_id in pending_waits:
            print(f"    - {wait_id}")
            print(f"      {CYAN}Resolve: python -m orchestrator resolve {project_dir} {wait_id} --resolver <name>{RESET}")

    return 0


def cmd_next(args):
    """执行下一步"""
    project_dir = args.project_dir

    sm = TracedStateMachine(project_dir)
    token_mgr = TokenManager(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        print_info("Run 'python -m orchestrator init' first")
        return 1

    # === 项目结构初始化检查 ===
    from pathlib import Path
    from .project_config import check_project_structure_initialized
    project_path = Path(project_dir)
    is_initialized, dir_config = check_project_structure_initialized(project_path)
    if not is_initialized:
        print_warning("Project directory structure not initialized")
        print_info("Run: python -m flowcore.orchestrator.cli init-structure .")
        print_info("Or run: python -m flowcore.orchestrator.cli init . --force-structure")
        return 1

    # 确保 Phase 目录结构存在 (从 workflow 动态提取)
    workflow = _load_workflow_from_project(project_dir)
    created_dirs = _create_phase_directories(project_dir, workflow)
    if created_dirs:
        print_info(f"Auto-created missing directories: {', '.join(created_dirs)}")

    # 检查是否有阻断门禁
    pending_gates = sm.get_pending_gates()
    blocking_gates = [g for g in pending_gates if g.blocking]

    if blocking_gates:
        print_error("Execution blocked by pending gates:")
        for gate in blocking_gates:
            print(f"  - {gate.gate_id}")
            print(f"    Approve: python -m orchestrator approve {project_dir} {gate.gate_id} --approver <name>")
        return 1

    # 获取可执行步骤
    ready_steps = sm.get_ready_steps()

    if not ready_steps:
        run_state = sm.get_run_state()
        if run_state == RunState.COMPLETED:
            print_success("Workflow completed!")
        else:
            print_warning("No ready steps available")
        return 0

    # 执行第一个就绪步骤
    step_id = ready_steps[0]

    # 签发令牌
    token = token_mgr.issue_token(
        run_id=state["run_id"],
        step_id=step_id,
        agent_id="auto"
    )

    # 开始步骤
    success, reason = sm.start_step(step_id, agent_id="auto", token=token.token_id)

    if success:
        # 记录事件
        event_log = EventLog(project_dir, state["run_id"])
        event_log.log_step_started(step_id, "auto", token.token_id)
        event_log.log_token_issued(step_id, token.token_id, token.expires_at)

        print_success(f"Started step: {step_id}")
        print(f"  Token: {token.token_id}")
        print(f"  Expires: {token.expires_at}")

        # === Agent Context 注入 ===
        inject_result = _inject_agent_context(
            project_dir=project_dir,
            step_id=step_id,
            state=state,
            sm=sm,
        )

        if inject_result:
            print(f"\n  {BOLD}--- Agent Context ---{RESET}")
            if inject_result.success:
                print_success(f"Context injected: {inject_result.injector_name}")
                print(f"  📋 Agent: {inject_result.details.get('agent_id', 'N/A')}")
                print(f"  📋 Name: {inject_result.details.get('agent_name', 'N/A')}")
                print(f"  📄 Context: {inject_result.context_location}")
            else:
                print_warning(f"Context injection skipped: {inject_result.message}")

        print_info(f"When done, run: python -m orchestrator complete {project_dir} {step_id}")
    else:
        print_error(f"Failed to start step: {reason}")
        return 1

    return 0


def cmd_start(args):
    """开始指定步骤

    新增功能:
    - --inject-context: 自动注入 Agent context (默认启用)
    - --context-file: 自定义 context 输出路径
    - --no-agent: 跳过 Agent 加载 (调试用)
    - --injector: 指定注入器 (默认自动检测)
    """
    project_dir = args.project_dir
    step_id = args.step_id

    sm = TracedStateMachine(project_dir)
    token_mgr = TokenManager(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        print_info("Run 'python -m orchestrator init' first")
        return 1

    # === 项目结构初始化检查 ===
    from pathlib import Path
    from .project_config import check_project_structure_initialized
    project_path = Path(project_dir)
    is_initialized, dir_config = check_project_structure_initialized(project_path)
    if not is_initialized:
        print_warning("Project directory structure not initialized")
        print_info("Run: python -m flowcore.orchestrator.cli init-structure .")
        print_info("Or run: python -m flowcore.orchestrator.cli init . --force-structure")
        return 1

    # 确保 Phase 目录结构存在 (从 workflow 动态提取)
    workflow = _load_workflow_from_project(project_dir)
    created_dirs = _create_phase_directories(project_dir, workflow)
    if created_dirs:
        print_info(f"Auto-created missing directories: {', '.join(created_dirs)}")

    # 检查是否可以开始
    can_start, reason = sm.can_start_step(step_id)
    if not can_start:
        print_error(f"Cannot start step {step_id}: {reason}")
        return 1

    # 获取步骤定义的 agent_id (优先级: CLI 参数 > workflow 定义 > "auto")
    workflow_agent_id = _resolve_agent_id(project_dir, step_id, state)
    effective_agent_id = args.agent or workflow_agent_id

    # 签发令牌
    token = token_mgr.issue_token(
        run_id=state["run_id"],
        step_id=step_id,
        agent_id=effective_agent_id
    )

    # 开始步骤
    success, reason = sm.start_step(step_id, agent_id=effective_agent_id, token=token.token_id)

    if success:
        event_log = EventLog(project_dir, state["run_id"])
        event_log.log_step_started(step_id, effective_agent_id, token.token_id)
        event_log.log_token_issued(step_id, token.token_id, token.expires_at)

        print_success(f"Started step: {step_id}")
        print(f"  Token: {token.token_id}")

        # 输出可注入上下文的令牌
        encoded = token_mgr.encode_token_for_context(token)
        print(f"\n  Context token (for LLM):\n  {encoded}")

        # === Agent Context 注入 ===
        inject_context = getattr(args, 'inject_context', True)  # 默认启用
        no_agent = getattr(args, 'no_agent', False)

        if inject_context and not no_agent:
            inject_result = _inject_agent_context(
                project_dir=project_dir,
                step_id=step_id,
                state=state,
                sm=sm,
                injector_name=getattr(args, 'injector', None),
                context_file=getattr(args, 'context_file', None),
            )

            if inject_result:
                print(f"\n  {BOLD}--- Agent Context ---{RESET}")
                if inject_result.success:
                    print_success(f"Context injected: {inject_result.injector_name}")
                    print(f"  📋 Agent: {inject_result.details.get('agent_id', 'N/A')}")
                    print(f"  📋 Name: {inject_result.details.get('agent_name', 'N/A')}")
                    print(f"  📄 Context: {inject_result.context_location}")
                else:
                    print_warning(f"Context injection skipped: {inject_result.message}")
        elif no_agent:
            print(f"\n  {YELLOW}⚠️  Agent context injection disabled (--no-agent){RESET}")

        # === 显示解析后的输出路径 ===
        _show_resolved_outputs(project_dir, step_id, sm)
    else:
        print_error(f"Failed: {reason}")
        return 1

    return 0


def _inject_agent_context(
    project_dir: str,
    step_id: str,
    state: dict,
    sm: TracedStateMachine,
    injector_name: str = None,
    context_file: str = None,
):
    """注入 Agent context 到 AI 工具

    Args:
        project_dir: 项目目录
        step_id: 步骤 ID
        state: 工作流状态
        sm: 状态机实例
        injector_name: 注入器名称 (可选)
        context_file: 自定义 context 文件路径 (可选)

    Returns:
        InjectionResult 或 None
    """
    from core.agent_injector import InjectionResult

    project_path = Path(project_dir).resolve()

    # 1. 查找 workflow.yaml
    workflow_file = project_path / "workflow.yaml"
    if not workflow_file.exists():
        # 尝试从 state 获取
        workflow_file = project_path / state.get("workflow_file", "workflow.yaml")

    if not workflow_file.exists():
        return InjectionResult(
            success=False,
            injector_name=injector_name or "auto",
            context_location="",
            message=f"workflow.yaml not found in {project_path}",
        )

    # 2. 解析 workflow
    parser = WorkflowParser(str(workflow_file))
    steps = parser.parse()

    # 3. 查找步骤数据
    step_data = None
    for step in steps:
        if step.id == step_id:
            step_data = {
                "id": step.id,
                "name": step.name,
                "description": getattr(step, 'description', ''),
                "run": step.agent_id,
                "inputs": [{"path": inp.source} for inp in step.inputs],
                "outputs": [{"path": out.path} for out in step.outputs],
            }
            break

    if step_data is None:
        return InjectionResult(
            success=False,
            injector_name=injector_name or "auto",
            context_location="",
            message=f"Step '{step_id}' not found in workflow",
        )

    # 4. 查找 ai-spec 根目录 (向上查找)
    ai_spec_root = _find_ai_spec_root(project_path)
    if ai_spec_root is None:
        ai_spec_root = project_path  # 降级：使用项目目录

    # 4.1 查找项目根目录 (有 CLAUDE.md 或 .claude 的目录)
    project_root = _find_project_root(project_path)
    if project_root is None:
        project_root = project_path

    # 5. 构建上下文
    builder = AgentContextBuilder(
        project_root=str(ai_spec_root),
        phase_dir=str(project_root),  # 使用项目根目录作为注入位置
    )

    workflow_data = {
        "id": parser.workflow.get("id", ""),
        "name": parser.workflow.get("name", ""),
    }

    state_data = {
        "run_id": state.get("run_id", ""),
    }

    # 6. 构建并注入
    # 将 "auto" 转换为 None 以触发自动检测
    actual_injector_name = None if injector_name == "auto" else injector_name

    result = builder.build_and_inject(
        step_id=step_id,
        step_data=step_data,
        workflow_data=workflow_data,
        state_data=state_data,
        injector_name=actual_injector_name,
    )

    return result


def _find_ai_spec_root(start_path: Path) -> Path:
    """向上查找 ai-spec 目录所在的根目录

    Args:
        start_path: 起始路径

    Returns:
        ai-spec 所在的根目录，如果没找到返回 None
    """
    current = start_path
    for _ in range(10):  # 最多向上查找 10 层
        if (current / "ai-spec").exists():
            return current
        parent = current.parent
        if parent == current:  # 到达根目录
            break
        current = parent
    return None


def _find_project_root(start_path: Path) -> Path:
    """向上查找项目根目录 (有 CLAUDE.md 或 .claude 的目录)

    Args:
        start_path: 起始路径

    Returns:
        项目根目录，如果没找到返回 None
    """
    current = start_path
    for _ in range(10):  # 最多向上查找 10 层
        if (current / "CLAUDE.md").exists() or (current / ".claude").exists():
            return current
        parent = current.parent
        if parent == current:  # 到达根目录
            break
        current = parent
    return None


def _show_resolved_outputs(project_dir: str, step_id: str, sm: TracedStateMachine):
    """显示步骤的必需输出路径及其解析后的绝对路径

    帮助 AI 工具明确知道应该在哪个目录创建文件。

    Args:
        project_dir: 项目目录 (phase 目录)
        step_id: 步骤 ID
        sm: 状态机实例
    """
    from core.project_config import ProjectConfig

    project_path = Path(project_dir).resolve()

    # 1. 获取步骤的 required_outputs (从 raw state 中获取)
    try:
        state = sm.load()
        step_data = state.get("steps", {}).get(step_id, {})
        required_outputs = step_data.get("required_outputs", [])
    except Exception:
        required_outputs = []

    if not required_outputs:
        print(f"\n  {YELLOW}No required outputs defined for this step{RESET}")
        return

    # 2. 加载 project.yaml (会自动向上查找)
    project_config = None
    try:
        project_config = ProjectConfig.load(str(project_path))
        if project_config:
            print(f"\n  {CYAN}📁 Project: {project_config.name} (from {project_config.base_path}/project.yaml){RESET}")
    except Exception as e:
        print(f"\n  {YELLOW}Warning: Failed to load project.yaml: {e}{RESET}")

    if not project_config:
        print(f"\n  {YELLOW}Warning: No project.yaml found. @ aliases cannot be resolved.{RESET}")

    # 3. 显示解析后的路径
    print(f"\n  {BOLD}--- Required Outputs (Resolved Paths) ---{RESET}")
    print(f"  {CYAN}AI should create files at these locations:{RESET}")

    for output_item in required_outputs:
        # Handle both string and dict output formats
        if isinstance(output_item, dict):
            output_path = output_item.get("path", str(output_item))
        else:
            output_path = output_item

        if isinstance(output_path, str) and output_path.startswith("@") and project_config:
            # 解析 @ 别名
            try:
                resolved = project_config.resolve_path(output_path, project_path)
                resolved_path = Path(resolved)

                # 检查目录是否存在
                parent_dir = resolved_path.parent if not resolved.endswith("/") else resolved_path
                exists = parent_dir.exists()
                exists_icon = f"{GREEN}✓{RESET}" if exists else f"{YELLOW}⚠ (dir not exists){RESET}"

                print(f"    {output_path}")
                print(f"      → {resolved} {exists_icon}")
            except Exception as e:
                print(f"    {output_path}")
                print(f"      {RED}→ Failed to resolve: {e}{RESET}")
        elif isinstance(output_path, str):
            # 相对路径，直接基于 phase 目录
            resolved = project_path / output_path
            print(f"    {output_path}")
            print(f"      → {resolved}")
        else:
            # Unknown format, just print it
            print(f"    {output_item}")

    print()


def cmd_complete(args):
    """完成步骤"""
    project_dir = args.project_dir
    step_id = args.step_id
    outputs = args.outputs.split(",") if args.outputs else []

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    success, reason = sm.complete_step(step_id, outputs)

    if success:
        event_log = EventLog(project_dir, state["run_id"])
        step = sm.get_step_state(step_id)

        # 解析 agent_id (优先 workflow.yaml 定义)
        effective_agent_id = _resolve_agent_id(project_dir, step_id, state)

        event_log.log_step_completed(step_id, effective_agent_id, outputs, step.outputs_hash or "")

        print_success(f"Step {step_id} marked for validation")
        print_info(f"Run: python -m orchestrator validate {project_dir} {step_id}")
    else:
        print_error(f"Failed: {reason}")
        return 1

    return 0


def cmd_validate(args):
    """验证步骤产物 - 交付物强约束 (Artifact Gate)

    核心规则：
    1. 从 workflow 定义获取 required_outputs
    2. 检查所有必需文件是否存在
    3. 缺文件直接失败，不允许过门
    4. 生成 manifest 用于审计
    """
    project_dir = args.project_dir
    step_id = args.step_id

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    step = sm.get_step_state(step_id)

    if step.state != StepState.VALIDATING:
        print_error(f"Step {step_id} is not in validating state (current: {step.state.value})")
        return 1

    # === 交付物强约束验证 (Artifact Gate) ===
    print(f"\n  {BOLD}--- Artifact Gate: Required Outputs Check ---{RESET}")

    # 使用新的 verify_required_outputs 方法
    result = sm.verify_required_outputs(step_id, step.outputs)

    # 显示必需输出
    required = result.get("required", [])
    if required:
        print(f"  Required outputs ({len(required)}):")
        for req in required:
            print(f"    - {req}")
    else:
        print(f"  {YELLOW}No required outputs defined{RESET}")

    # 显示缺失文件
    missing = result.get("missing", [])
    if missing:
        print(f"\n  {RED}{BOLD}❌ MISSING OUTPUTS ({len(missing)}):{RESET}")
        for m in missing:
            print(f"    {RED}- {m}{RESET}")
        print(f"\n  {RED}Artifact Gate BLOCKED: 必须补齐所有必需输出后才能通过验证{RESET}")
        print(f"  {YELLOW}提示: Agent 应立即补齐缺失文件，然后重新运行 validate{RESET}")

        # 记录失败
        event_log = EventLog(project_dir, state["run_id"])
        event_log.log_validation_failed(step_id, "artifact_gate", missing)

        # 写入 manifest (incomplete 状态)
        manifest = result.get("manifest", {})
        manifest_path = sm.write_step_manifest(step_id, manifest)
        print(f"\n  Manifest: {manifest_path}")

        return 1

    # 显示找到的文件
    found = result.get("found", [])
    if found:
        print(f"\n  {GREEN}✅ Found outputs ({len(found)}):{RESET}")
        for f in found:
            print(f"    {GREEN}- {f}{RESET}")

    # 显示额外文件
    extra = result.get("extra", [])
    if extra:
        print(f"\n  {CYAN}Extra outputs ({len(extra)}):{RESET}")
        for e in extra:
            print(f"    {CYAN}- {e}{RESET}")

    # 写入 manifest (done 状态)
    manifest = result.get("manifest", {})
    manifest_path = sm.write_step_manifest(step_id, manifest)
    print(f"\n  Manifest: {manifest_path}")

    # === 原有验证逻辑 (兼容性) ===
    passed = result.get("passed", True)
    details = {"manifest": manifest}

    sm.set_validation_result(step_id, passed, details)

    event_log = EventLog(project_dir, state["run_id"])

    if passed:
        event_log.log_validation_passed(step_id, "artifact_gate")
        print_success(f"Artifact Gate PASSED for {step_id}")

        # 检查是否有门禁
        step = sm.get_step_state(step_id)
        if step.state == StepState.GATE_PENDING:
            print_warning(f"Step {step_id} is waiting for gate approval: {step.gate_id}")
            print_info(f"Approve: python -m orchestrator approve {project_dir} {step.gate_id} --approver <name>")

        # 输出 Run-to-Gate 决策信息 (宪法强制要求)
        next_info = sm.get_next_step_info()
        print(f"\n  {BOLD}--- Run-to-Gate Check ---{RESET}")
        print(f"  step_completed: {step_id}")
        print(f"  next_step: {next_info.get('next_step') or 'null'}")
        print(f"  next_step_human_gate: {str(next_info.get('next_step_human_gate', False)).lower()}")
        print(f"  action: {next_info.get('action', 'unknown')}")

    return 0 if passed else 1


def _normalize_gate_id(gate_id: str, state: dict):
    """将字符串 gate_id 转换为 state 中实际的 key

    YAML 会将 "true"/"false" 解析为布尔值，所以需要特殊处理
    """
    # 首先尝试直接匹配
    if gate_id in state.get("gates", {}):
        return gate_id

    # 尝试布尔值转换
    if gate_id.lower() == "true":
        if True in state.get("gates", {}):
            return True
    elif gate_id.lower() == "false":
        if False in state.get("gates", {}):
            return False

    # 返回原值
    return gate_id


def cmd_approve(args):
    """审批门禁"""
    project_dir = args.project_dir
    gate_id = args.gate_id
    approver = args.approver
    comment = args.comment

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    # 规范化 gate_id (处理 YAML 的 true/false 布尔值问题)
    normalized_gate_id = _normalize_gate_id(gate_id, state)

    success, approval_id = sm.approve_gate(normalized_gate_id, approver, comment)

    if success:
        event_log = EventLog(project_dir, state["run_id"])
        gate = state["gates"].get(normalized_gate_id, {})
        event_log.log_gate_approved(normalized_gate_id, gate.get("step_id", ""), approver, approval_id)

        print_success(f"Gate {gate_id} approved")
        print(f"  Approval ID: {approval_id}")
        print(f"  Approver: {approver}")

        # 检查是否可以继续
        ready_steps = sm.get_ready_steps()
        if ready_steps:
            print_info(f"Ready to continue. Run: python -m orchestrator next {project_dir}")
    else:
        print_error(f"Failed: {approval_id}")
        return 1

    return 0


def cmd_reject(args):
    """拒绝门禁"""
    project_dir = args.project_dir
    gate_id = args.gate_id
    approver = args.approver
    reason = args.reason

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    # 规范化 gate_id (处理 YAML 的 true/false 布尔值问题)
    normalized_gate_id = _normalize_gate_id(gate_id, state)

    success, _ = sm.reject_gate(normalized_gate_id, approver, reason)

    if success:
        event_log = EventLog(project_dir, state["run_id"])
        gate = state["gates"].get(normalized_gate_id, {})
        event_log.log_gate_rejected(normalized_gate_id, gate.get("step_id", ""), approver, reason)

        print_warning(f"Gate {gate_id} rejected")
        print(f"  Reason: {reason}")
    else:
        print_error("Failed to reject gate")
        return 1

    return 0


def cmd_token(args):
    """获取或验证令牌"""
    project_dir = args.project_dir
    step_id = args.step_id

    sm = TracedStateMachine(project_dir)
    token_mgr = TokenManager(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    # 获取活跃令牌
    active_tokens = token_mgr.get_active_tokens(step_id)

    if active_tokens:
        print_header(f"Active Tokens for {step_id}")
        for token in active_tokens:
            print(f"  Token ID:    {token.token_id}")
            print(f"  Expires:     {token.expires_at}")
            print(f"  Permissions: {', '.join(token.permissions)}")
            print(f"  Context:     {token_mgr.encode_token_for_context(token)}")
            print()
    else:
        print_warning(f"No active tokens for {step_id}")

        # 提示签发
        step = sm.get_step_state(step_id)
        if step.state == StepState.IN_PROGRESS:
            print_info("Step is in progress but has no token")

    return 0


def cmd_check(args):
    """检查令牌和权限"""
    project_dir = args.project_dir
    token_id = args.token
    tool = args.tool

    token_mgr = TokenManager(project_dir)

    valid, reason = token_mgr.validate_token(token_id)

    if valid:
        print_success(f"Token {token_id} is valid")

        if tool:
            guard = ToolGuard(token_mgr)
            allowed, block_reason = guard.check_tool_access(token_id, tool)
            if allowed:
                print_success(f"Tool '{tool}' is allowed")
            else:
                print_error(f"Tool '{tool}' is blocked: {block_reason}")
                return 1
    else:
        print_error(f"Token invalid: {reason}")
        return 1

    return 0


def cmd_log(args):
    """查看事件日志"""
    project_dir = args.project_dir
    step_id = args.step

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    event_log = EventLog(project_dir, state["run_id"])
    events = event_log.get_events(step_id=step_id, limit=args.limit or 50)

    print_header(f"Event Log ({len(events)} events)")

    for event in events:
        ts = event.timestamp[:19]  # 截断到秒
        type_color = {
            "step_started": CYAN,
            "step_completed": GREEN,
            "step_failed": RED,
            "gate_triggered": YELLOW,
            "gate_approved": GREEN,
            "gate_rejected": RED,
            "validation_passed": GREEN,
            "validation_failed": RED
        }.get(event.event_type.value, RESET)

        print(f"  {ts} {type_color}{event.event_type.value:20}{RESET} {event.step_id or ''}")
        if event.error:
            print(f"    {RED}Error: {event.error}{RESET}")

    # 统计
    if args.stats:
        stats = event_log.get_statistics()
        print(f"\n  {BOLD}Statistics:{RESET}")
        print(f"    Total events: {stats['total_events']}")
        print(f"    Errors: {stats['error_count']}")
        print(f"    Retries: {stats['retry_count']}")

    return 0


def cmd_export(args):
    """导出审计报告"""
    project_dir = args.project_dir
    output_format = args.format

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    event_log = EventLog(project_dir, state["run_id"])
    output_path = event_log.export_audit_report()

    print_success(f"Audit report exported to: {output_path}")
    return 0


def cmd_reset(args):
    """重置步骤状态，允许重试"""
    project_dir = args.project_dir
    step_id = args.step_id
    reason = args.reason

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    success, error = sm.reset_step(step_id, reason)

    if success:
        print_success(f"Step {step_id} reset to pending")
        if reason:
            print(f"  Reason: {reason}")
        print_info(f"Run: python -m orchestrator next {project_dir}")
    else:
        print_error(f"Failed to reset: {error}")
        return 1

    return 0


def cmd_trace(args):
    """查看执行追踪 (span-based logs)"""
    project_dir = args.project_dir
    export_format = args.format
    output_file = args.output

    sm = TracedStateMachine(project_dir)

    try:
        state = sm.load()
    except FileNotFoundError:
        print_error("No workflow state found")
        return 1

    # 获取 TraceLog
    trace_log = TraceLog(project_dir, state["run_id"])

    # 检查是否有追踪数据
    traces_file = Path(project_dir) / ".workflow" / "traces" / "traces.jsonl"
    if not traces_file.exists():
        print_warning("No trace logs found yet")
        print_info("Trace logs are generated automatically when using orchestrator commands")
        return 0

    if export_format:
        # 导出模式
        if export_format == "markdown":
            output_path = trace_log.export_markdown_report(output_file)
        else:
            output_path = trace_log.export_yaml(output_file)
        print_success(f"Trace report exported to: {output_path}")
        return 0

    # 显示模式
    print_header("Execution Trace")

    stats = trace_log.get_statistics()
    print(f"  Run ID:          {stats['run_id']}")
    print(f"  Total Spans:     {stats['total_spans']}")
    print(f"  Total Duration:  {stats['total_duration_ms']}ms")
    print(f"  Total Tokens:    {stats['total_tokens']}")
    print(f"  Total Cost:      ${stats['total_cost_usd']:.4f}")
    print(f"  Errors:          {stats['error_count']}")

    # 按类型统计
    print(f"\n  {BOLD}By Type:{RESET}")
    for t, count in stats['by_type'].items():
        print(f"    - {t}: {count}")

    # 按状态统计
    print(f"\n  {BOLD}By Status:{RESET}")
    for s, count in stats['by_status'].items():
        color = {
            "success": GREEN,
            "failed": RED,
            "running": CYAN,
            "timeout": YELLOW,
        }.get(s, RESET)
        print(f"    {color}● {s}: {count}{RESET}")

    # 显示最近的 spans
    spans = trace_log.get_spans(limit=args.limit or 10)
    if spans:
        print(f"\n  {BOLD}Recent Spans:{RESET}")
        for span in spans:
            status_icon = {
                SpanStatus.SUCCESS: f"{GREEN}✅{RESET}",
                SpanStatus.FAILED: f"{RED}❌{RESET}",
                SpanStatus.RUNNING: f"{CYAN}⏳{RESET}",
                SpanStatus.TIMEOUT: f"{YELLOW}⏰{RESET}",
            }.get(span.status, "  ")

            duration = f"{span.duration_ms}ms" if span.duration_ms else "-"
            print(f"    {status_icon} {span.name} ({span.span_type.value}) - {duration}")
            if span.error:
                print(f"       {RED}Error: {span.error.message}{RESET}")

    print_info(f"Export: python -m orchestrator trace {project_dir} --format markdown")
    return 0


def cmd_validate_project(args):
    """验证项目配置 (project.yaml)

    检查：
    1. project.yaml 存在且格式正确
    2. 所有必需字段已填写 (kind, version, id, name)
    3. 仓库路径存在
    4. 路径别名引用正确的仓库
    """
    project_dir = args.project_dir

    print_header("Project Configuration Validation")

    is_valid, errors = _validate_project_config(project_dir)

    if is_valid:
        print_success("Project configuration is valid")

        # 显示额外信息
        from core.project_config import ProjectConfig
        config = ProjectConfig.load(project_dir)

        if config:
            print(f"\n  {BOLD}Project Info:{RESET}")
            print(f"    ID:   {config.id}")
            print(f"    Name: {config.name}")

            # 检查仓库状态
            repo_status = config.check_repositories()
            if repo_status:
                print(f"\n  {BOLD}Repositories:{RESET}")
                for repo_id, exists in repo_status.items():
                    repo = config.get_repository(repo_id)
                    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
                    resolved = repo.resolve(config.base_path) if repo else "N/A"
                    print(f"    {status} {repo_id}: {resolved}")

            # 显示路径别名
            print(f"\n  {BOLD}Path Aliases:{RESET}")
            for alias, target in config.path_aliases.items():
                print(f"    {alias} → {target}")

        return 0
    else:
        print_error("Project configuration validation failed:")
        for err in errors:
            print(f"    {RED}- {err}{RESET}")
        return 1


def cmd_context(args):
    """查看或清除当前 Agent context"""
    project_dir = args.project_dir
    project_path = Path(project_dir).resolve()

    # 获取注入器
    injector_name = getattr(args, 'injector', None)
    if injector_name == "auto":
        injector_name = None

    injector = InjectorRegistry.create_injector(project_path, injector_name)

    if injector is None:
        print_warning("No suitable injector found for this project")
        print_info("Available injectors: " + ", ".join(InjectorRegistry.list_injectors()))
        return 1

    # 清除模式
    if args.clear:
        success = injector.clear_context()
        if success:
            print_success("Context cleared")
        else:
            print_error("Failed to clear context")
            return 1
        return 0

    # 显示模式
    context = injector.get_current_context()

    if context is None:
        print_warning("No context currently injected")
        print_info(f"Context location: {injector.get_context_location()}")
        return 0

    print_header("Current Agent Context")

    print(f"  {BOLD}Step:{RESET}")
    print(f"    ID:          {context.step_id}")
    print(f"    Name:        {context.step_name}")
    print(f"    Description: {context.step_description or 'N/A'}")

    print(f"\n  {BOLD}Agent:{RESET}")
    print(f"    ID:          {context.agent_id}")
    print(f"    Name:        {context.agent_name}")
    print(f"    Version:     {context.agent_version}")

    if context.agent_persona:
        print(f"\n  {BOLD}Persona:{RESET}")
        for key, value in context.agent_persona.items():
            print(f"    {key}: {value}")

    if context.agent_forbidden_behaviors:
        print(f"\n  {BOLD}Forbidden Behaviors ({len(context.agent_forbidden_behaviors)}):{RESET}")
        for i, behavior in enumerate(context.agent_forbidden_behaviors[:5], 1):
            if isinstance(behavior, dict):
                print(f"    {RED}{i}. {behavior.get('name', behavior.get('id', 'Unknown'))}{RESET}")
            else:
                print(f"    {RED}{i}. {behavior}{RESET}")
        if len(context.agent_forbidden_behaviors) > 5:
            print(f"    ... and {len(context.agent_forbidden_behaviors) - 5} more")

    if context.agent_quality_bar:
        print(f"\n  {BOLD}Quality Bar ({len(context.agent_quality_bar)}):{RESET}")
        for i, item in enumerate(context.agent_quality_bar[:5], 1):
            print(f"    {GREEN}{i}. {item}{RESET}")
        if len(context.agent_quality_bar) > 5:
            print(f"    ... and {len(context.agent_quality_bar) - 5} more")

    print(f"\n  {BOLD}Workflow:{RESET}")
    print(f"    ID:          {context.workflow_id}")
    print(f"    Name:        {context.workflow_name}")
    print(f"    Run ID:      {context.run_id}")

    print(f"\n  {BOLD}Metadata:{RESET}")
    print(f"    Generated:   {context.generated_at}")
    print(f"    Spec Path:   {context.spec_path or 'N/A'}")
    print(f"    Location:    {injector.get_context_location()}")

    return 0


def cmd_detailed_log(args):
    """生成详细执行日志 (包含 AI 工作过程)"""
    project_dir = args.project_dir
    session = args.session
    output = args.output
    source = args.source

    # 导入日志解析器
    from .core.session_log import (
        SessionLogParserRegistry,
        ClaudeCodeLogParser,  # 确保注册
    )
    from .core.session_log.report_generator import DetailedReportGenerator

    # 查找会话日志
    if session:
        # 用户指定了 session
        if source == "auto":
            # 尝试自动检测
            parser_class = SessionLogParserRegistry.detect_parser(Path(session))
            if parser_class:
                session_path = Path(session)
            else:
                # 可能是 session ID，尝试查找
                sessions_all = SessionLogParserRegistry.find_sessions_all(project_dir)
                session_path = None
                for src, paths in sessions_all.items():
                    for p in paths:
                        if session in str(p):
                            session_path = p
                            source = src
                            break
                    if session_path:
                        break
        else:
            parser_class = SessionLogParserRegistry.get_parser(source)
            if parser_class:
                session_path = parser_class.find_latest_session(project_dir)
            else:
                print_error(f"Unknown source: {source}")
                return 1
    else:
        # 自动查找最新会话
        sessions_all = SessionLogParserRegistry.find_sessions_all(project_dir)
        if not sessions_all:
            print_error("No session logs found for this project")
            print_info("Supported sources: " + ", ".join(SessionLogParserRegistry.list_parsers()))
            return 1

        # 取第一个源的最新会话
        for src, paths in sessions_all.items():
            if paths:
                session_path = paths[0]  # 已按时间排序
                source = src
                break
        else:
            print_error("No session logs found")
            return 1

    if not session_path or not session_path.exists():
        print_error(f"Session log not found: {session_path}")
        return 1

    print(f"\n{CYAN}📋 Generating detailed execution log...{RESET}")
    print(f"  Session: {session_path.name}")
    print(f"  Source: {source}")

    # 生成报告
    try:
        generator = DetailedReportGenerator(project_dir)

        # 默认输出路径
        if not output:
            output = str(Path(project_dir) / "output" / "detailed-execution-log.md")

        report = generator.generate(
            session_log_path=str(session_path),
            output_path=output,
            parser_type=source if source != "auto" else "auto"
        )

        print_success(f"Detailed log exported to: {output}")

        # 显示摘要
        lines = report.split('\n')
        summary_start = None
        summary_end = None
        for i, line in enumerate(lines):
            if '## 执行摘要' in line:
                summary_start = i
            elif summary_start and line.startswith('---'):
                summary_end = i
                break

        if summary_start and summary_end:
            print("\n" + "\n".join(lines[summary_start:summary_end]))

        return 0

    except Exception as e:
        print_error(f"Failed to generate report: {e}")
        import traceback
        traceback.print_exc()
        return 1


# ============================================
# 测试流程扩展命令
# ============================================

def cmd_loop_start(args):
    """开始循环执行"""
    print_header("Start Loop")

    sm = TracedStateMachine(args.project_dir)
    try:
        sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    success, error = sm.start_loop(args.loop_id)
    if not success:
        print_error(f"Failed to start loop: {error}")
        return 1

    loop_status = sm.get_loop_status(args.loop_id)
    print_success(f"Loop '{args.loop_id}' started")
    print(f"  Iteration: {loop_status['current_iteration']} / {loop_status['max_iterations']}")

    return 0


def cmd_loop_complete(args):
    """完成循环迭代"""
    print_header("Complete Loop Iteration")

    sm = TracedStateMachine(args.project_dir)
    try:
        sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    continue_loop = args.continue_loop
    success, error = sm.complete_loop_iteration(args.loop_id, continue_loop=continue_loop)

    if not success:
        print_warning(f"Loop completion: {error}")
    else:
        loop_status = sm.get_loop_status(args.loop_id)
        if continue_loop:
            print_success(f"Loop '{args.loop_id}' continuing to iteration {loop_status['current_iteration']}")
        else:
            print_success(f"Loop '{args.loop_id}' completed")

    return 0


def cmd_wait(args):
    """开始外部等待"""
    print_header("Start External Wait")

    sm = TracedStateMachine(args.project_dir)
    try:
        sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    notify_channels = args.notify.split(",") if args.notify else []

    success, wait_id = sm.start_external_wait(
        step_id=args.step_id,
        event_type=args.event,
        timeout=args.timeout,
        timeout_action=args.timeout_action,
        notify_channels=notify_channels
    )

    if not success:
        print_error(f"Failed to start wait: {wait_id}")
        return 1

    print_success(f"External wait started: {wait_id}")
    print(f"  Step: {args.step_id}")
    print(f"  Waiting for: {args.event}")
    print(f"  Timeout: {args.timeout}")

    return 0


def cmd_resolve(args):
    """解决外部等待"""
    print_header("Resolve External Wait")

    sm = TracedStateMachine(args.project_dir)
    try:
        sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    event_data = None
    if args.data:
        try:
            event_data = json.loads(args.data)
        except json.JSONDecodeError:
            print_error("Invalid JSON data")
            return 1

    success, error = sm.resolve_external_wait(
        wait_id=args.wait_id,
        resolved_by=args.resolver,
        event_data=event_data
    )

    if not success:
        print_error(f"Failed to resolve wait: {error}")
        return 1

    print_success(f"External wait resolved: {args.wait_id}")
    return 0


def cmd_loop_back(args):
    """回退到之前的步骤"""
    print_header("Loop Back")

    sm = TracedStateMachine(args.project_dir)
    try:
        sm.load()
    except FileNotFoundError:
        print_error("Workflow not initialized. Run 'init' first.")
        return 1

    success, error = sm.loop_back(
        from_step_id=args.from_step,
        target_step_id=args.to_step,
        reason=args.reason
    )

    if not success:
        print_error(f"Failed to loop back: {error}")
        return 1

    print_success(f"Looped back from '{args.from_step}' to '{args.to_step}'")
    if args.reason:
        print(f"  Reason: {args.reason}")

    return 0


def cmd_init_structure(args):
    """Initialize project directory structure"""
    print_header("Initializing Project Directory Structure")

    from pathlib import Path
    from .project_config import init_project_structure, check_project_structure_initialized

    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print_error(f"Project directory does not exist: {project_dir}")
        return 1

    # Get project name from args or prompt user
    project_name = getattr(args, 'project_name', None)

    # Check if already initialized
    is_initialized, existing_config = check_project_structure_initialized(project_dir)
    if is_initialized and not getattr(args, 'force', False):
        if existing_config.project_name and not project_name:
            project_name = existing_config.project_name
        print_warning(f"Project structure already initialized at {existing_config.initialized_at}")
        print_info("Use --force to re-initialize (this will update the structure)")
        # Still show current structure
        print()
        if existing_config.project_name:
            print_success(f"Project name: {existing_config.project_name}")
            print_info(f"Content directory: {existing_config.project_content_dir}")
        return 0

    try:
        # Load custom config if provided
        custom_config = None
        if hasattr(args, 'config') and args.config:
            import yaml
            with open(args.config, 'r', encoding='utf-8') as f:
                custom_config = yaml.safe_load(f)

        dir_config = init_project_structure(
            project_dir,
            project_name=project_name,
            config_schema=custom_config,
            force=getattr(args, 'force', False)
        )

        print_success(f"Directory structure initialized (v{dir_config.version})")
        print_info(f"Config saved to: {project_dir / '.project' / 'dirs.yaml'}")
        print()
        if dir_config.project_name:
            print_success(f"Project name: {dir_config.project_name}")
            print_info(f"Content directory: {dir_config.project_content_dir}")
            print()
        print("Directories created:")
        for dir_id, dir_info in dir_config.directories.items():
            status = "✓" if (project_dir / dir_info.path).exists() else "✗"
            print(f"  {status} {dir_id}: {dir_info.path}")
            if dir_info.description:
                print(f"     {dir_info.description}")
        print()
        print_info("All outputs will now use these fixed directories")
        return 0

    except Exception as e:
        print_error(f"Failed to initialize directory structure: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_check_structure(args):
    """Check project directory structure status"""
    print_header("Checking Project Directory Structure")

    from pathlib import Path
    from .project_config import check_project_structure_initialized, get_project_structure

    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print_error(f"Project directory does not exist: {project_dir}")
        return 1

    # Check if initialized
    is_initialized, config = check_project_structure_initialized(project_dir)

    if not is_initialized:
        print_error("Project structure not initialized")
        print_info("Run: python -m flowcore.orchestrator.cli init-structure .")
        return 1

    print_success(f"Project structure initialized (v{config.version})")
    print_info(f"Initialized at: {config.initialized_at}")
    print_info(f"Initialized by: {config.initialized_by}")
    if config.project_name:
        print_success(f"Project name: {config.project_name}")
        print_info(f"Content directory: {config.project_content_dir}")
    print()

    # Check each directory
    print("Directory Status:")
    all_exist = True
    for dir_id, dir_info in config.directories.items():
        # Use get_directory_path to get full path (respects project_content_dir)
        dir_path = config.get_directory_path(dir_id)
        # Show relative path from project_dir
        try:
            rel_path = dir_path.relative_to(project_dir)
        except ValueError:
            rel_path = dir_path
        exists = dir_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_id}: {rel_path}")
        if dir_info.description:
            print(f"     {dir_info.description}")

        if not exists:
            all_exist = False
        elif dir_info.subdirs:
            # Check subdirectories
            for subdir in dir_info.subdirs:
                subdir_path = dir_path / subdir
                sub_exists = subdir_path.exists()
                sub_status = "✓" if sub_exists else "✗"
                print(f"    {sub_status} {subdir}/")

    print()

    # Show constraints
    if config.constraints:
        print("Constraints:")
        for key, value in config.constraints.items():
            if value:
                print(f"  • {key}: {value}")
        print()

    # Optional validation
    if getattr(args, 'validate', False):
        print_header("Validating Outputs Against Structure")
        # TODO: Implement output validation
        print_warning("Output validation not yet implemented")
        print_info("This will check all generated files against the configured structure")

    if all_exist:
        print_success("All directories exist")
        return 0
    else:
        print_warning("Some directories are missing")
        print_info("Run: python -m flowcore.orchestrator.cli init-structure --force .")
        return 1


def cmd_run_engine(args):
    """使用统一 Engine 接口执行步骤（同步包装器）"""
    return asyncio.run(cmd_run_engine_async(args))


def main():
    parser = argparse.ArgumentParser(
        description="Workflow Orchestrator - 通用 AI 工作流编排器",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # generate-workflow (v1.6 - Workflow Generator)
    p_generate = subparsers.add_parser("generate-workflow",
        help="Generate workflow.yaml from template and phase config")
    p_generate.add_argument("--template", "-t", required=True,
        help="Path to workflow template (e.g., phase-openspec-flow/v1/workflow.yaml)")
    p_generate.add_argument("--config", "-c",
        help="Path to phase-config.yaml (alternative to CLI args)")
    p_generate.add_argument("--output", "-o", required=True,
        help="Output path for generated workflow.yaml")
    # Alternative to config file - CLI args
    p_generate.add_argument("--phase-id", dest="phase_id",
        help="Phase ID (e.g., phase11-logging)")
    p_generate.add_argument("--phase-name", dest="phase_name",
        help="Phase name (e.g., '日志体系改造')")
    p_generate.add_argument("--phase-dir", dest="phase_dir",
        help="Phase directory path")
    p_generate.add_argument("--change-id", dest="change_id",
        help="Change ID (e.g., CHG-001)")
    p_generate.add_argument("--project-dir", dest="project_dir_config",
        help="Project directory for knowledge merge")

    # init
    p_init = subparsers.add_parser("init", help="Initialize workflow run")
    p_init.add_argument("project_dir", help="Project directory")
    p_init.add_argument("--workflow", "-w", required=True, help="Workflow YAML file")
    p_init.add_argument("--template",
        help="Template workflow to validate against (optional)")
    p_init.add_argument("--skip-validation", dest="skip_validation", action="store_true",
        help="Skip project.yaml validation (not recommended)")
    p_init.add_argument("--skip-workflow-validation", dest="skip_workflow_validation",
        action="store_true",
        help="Skip workflow structure validation (not recommended)")
    p_init.add_argument("--skip-structure-init", dest="skip_structure_init", action="store_true",
        help="Skip directory structure initialization (not recommended)")
    p_init.add_argument("--force-structure", dest="force_structure", action="store_true",
        help="Re-initialize directory structure even if already exists")

    # status
    p_status = subparsers.add_parser("status", help="Show current status")
    p_status.add_argument("project_dir", help="Project directory")

    # next
    p_next = subparsers.add_parser("next", help="Execute next ready step")
    p_next.add_argument("project_dir", help="Project directory")

    # start
    p_start = subparsers.add_parser("start", help="Start specific step")
    p_start.add_argument("project_dir", help="Project directory")
    p_start.add_argument("step_id", help="Step ID")
    p_start.add_argument("--agent", help="Agent ID")
    p_start.add_argument("--inject-context", dest="inject_context", action="store_true",
                        default=True, help="Inject Agent context (default: enabled)")
    p_start.add_argument("--no-inject-context", dest="inject_context", action="store_false",
                        help="Disable Agent context injection")
    p_start.add_argument("--context-file", help="Custom context output path")
    p_start.add_argument("--no-agent", action="store_true",
                        help="Skip Agent loading (debug mode)")
    p_start.add_argument("--injector", choices=["claude_code", "auto"],
                        default="auto", help="Context injector (default: auto-detect)")

    # complete
    p_complete = subparsers.add_parser("complete", help="Complete step")
    p_complete.add_argument("project_dir", help="Project directory")
    p_complete.add_argument("step_id", help="Step ID")
    p_complete.add_argument("--outputs", help="Comma-separated output files")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate step outputs")
    p_validate.add_argument("project_dir", help="Project directory")
    p_validate.add_argument("step_id", help="Step ID")

    # approve
    p_approve = subparsers.add_parser("approve", help="Approve gate")
    p_approve.add_argument("project_dir", help="Project directory")
    p_approve.add_argument("gate_id", help="Gate ID")
    p_approve.add_argument("--approver", required=True, help="Approver name")
    p_approve.add_argument("--comment", help="Approval comment")

    # reject
    p_reject = subparsers.add_parser("reject", help="Reject gate")
    p_reject.add_argument("project_dir", help="Project directory")
    p_reject.add_argument("gate_id", help="Gate ID")
    p_reject.add_argument("--approver", required=True, help="Approver name")
    p_reject.add_argument("--reason", required=True, help="Rejection reason")

    # token
    p_token = subparsers.add_parser("token", help="Get/show tokens")
    p_token.add_argument("project_dir", help="Project directory")
    p_token.add_argument("step_id", help="Step ID")

    # check
    p_check = subparsers.add_parser("check", help="Check token validity")
    p_check.add_argument("project_dir", help="Project directory")
    p_check.add_argument("--token", required=True, help="Token ID")
    p_check.add_argument("--tool", help="Tool name to check")

    # log
    p_log = subparsers.add_parser("log", help="View event log")
    p_log.add_argument("project_dir", help="Project directory")
    p_log.add_argument("--step", help="Filter by step ID")
    p_log.add_argument("--limit", type=int, help="Limit events")
    p_log.add_argument("--stats", action="store_true", help="Show statistics")

    # export
    p_export = subparsers.add_parser("export", help="Export audit report")
    p_export.add_argument("project_dir", help="Project directory")
    p_export.add_argument("--format", choices=["json", "yaml"], default="json")

    # reset
    p_reset = subparsers.add_parser("reset", help="Reset step to pending (allow retry)")
    p_reset.add_argument("project_dir", help="Project directory")
    p_reset.add_argument("step_id", help="Step ID to reset")
    p_reset.add_argument("--reason", help="Reason for reset")

    # trace (span-based logs)
    p_trace = subparsers.add_parser("trace", help="View execution traces (span-based logs)")
    p_trace.add_argument("project_dir", help="Project directory")
    p_trace.add_argument("--format", choices=["markdown", "yaml"], help="Export format")
    p_trace.add_argument("--output", help="Output file path (optional)")
    p_trace.add_argument("--limit", type=int, help="Limit spans displayed")

    # detailed-log (AI 工作详细日志)
    p_detailed = subparsers.add_parser("detailed-log", help="Generate detailed execution log with AI activities")
    p_detailed.add_argument("project_dir", help="Project directory")
    p_detailed.add_argument("--session", help="Session ID or log file path")
    p_detailed.add_argument("--source", choices=["auto", "claude_code", "codex", "gemini", "opencode"],
                           default="auto", help="Log source (default: auto-detect)")
    p_detailed.add_argument("--output", help="Output file path (default: output/detailed-execution-log.md)")

    # context (Agent context 管理)
    p_context = subparsers.add_parser("context", help="View or manage current Agent context")
    p_context.add_argument("project_dir", help="Project directory")
    p_context.add_argument("--clear", action="store_true", help="Clear current context")
    p_context.add_argument("--injector", choices=["claude_code", "auto"],
                          default="auto", help="Context injector (default: auto-detect)")

    # validate-project (项目配置验证)
    p_validate_project = subparsers.add_parser("validate-project",
                                               help="Validate project.yaml configuration")
    p_validate_project.add_argument("project_dir", help="Project directory (or phase directory)")

    # ============================================
    # 统一 Engine 接口命令 (新推荐)
    # ============================================
    # run-engine (使用统一 Engine 接口执行步骤)
    p_run_engine = subparsers.add_parser("run-engine",
                                             help="Execute step with unified Engine interface (new recommended way)")
    p_run_engine.add_argument("project_dir", help="Project directory")
    p_run_engine.add_argument("step_id", nargs="?", help="Step ID (optional, auto-select if not provided)")

    # ============================================
    # 测试流程扩展命令
    # ============================================

    # loop-start (开始循环)
    p_loop_start = subparsers.add_parser("loop-start", help="Start a loop execution (testing workflow)")
    p_loop_start.add_argument("project_dir", help="Project directory")
    p_loop_start.add_argument("loop_id", help="Loop ID (e.g., t5_bug_fix_cycle)")

    # loop-complete (完成循环迭代)
    p_loop_complete = subparsers.add_parser("loop-complete", help="Complete a loop iteration (testing workflow)")
    p_loop_complete.add_argument("project_dir", help="Project directory")
    p_loop_complete.add_argument("loop_id", help="Loop ID")
    p_loop_complete.add_argument("--continue", dest="continue_loop", action="store_true",
                                 help="Continue to next iteration")

    # wait (开始外部等待)
    p_wait = subparsers.add_parser("wait", help="Start waiting for an external event (testing workflow)")
    p_wait.add_argument("project_dir", help="Project directory")
    p_wait.add_argument("step_id", help="Step ID")
    p_wait.add_argument("--event", required=True, help="Event type to wait for (e.g., fix_version_submitted)")
    p_wait.add_argument("--timeout", default="48h", help="Timeout duration (default: 48h)")
    p_wait.add_argument("--timeout-action", dest="timeout_action", default="escalate",
                        choices=["escalate", "fail", "skip"], help="Action on timeout")
    p_wait.add_argument("--notify", help="Comma-separated notification channels")

    # resolve (解决外部等待)
    p_resolve = subparsers.add_parser("resolve", help="Resolve an external wait (testing workflow)")
    p_resolve.add_argument("project_dir", help="Project directory")
    p_resolve.add_argument("wait_id", help="Wait ID")
    p_resolve.add_argument("--resolver", required=True, help="Who resolved this (user/agent)")
    p_resolve.add_argument("--data", help="Event data as JSON string")

    # loop-back (回退到之前步骤)
    p_loop_back = subparsers.add_parser("loop-back", help="Loop back to a previous step (testing workflow)")
    p_loop_back.add_argument("project_dir", help="Project directory")
    p_loop_back.add_argument("from_step", help="Current step ID")
    p_loop_back.add_argument("to_step", help="Target step ID to loop back to")
    p_loop_back.add_argument("--reason", help="Reason for loop back")

    # init-structure (NEW: Initialize directory structure only)
    p_init_structure = subparsers.add_parser("init-structure", help="Initialize directory structure")
    p_init_structure.add_argument("project_dir", help="Project directory")
    p_init_structure.add_argument("--project-name", dest="project_name",
        help="Name of the project (creates subdirectory with this name)")
    p_init_structure.add_argument("--force", action="store_true",
        help="Re-initialize even if already exists")
    p_init_structure.add_argument("--config", help="Custom config schema file (optional)")

    # check-structure (NEW: Check directory structure)
    p_check_structure = subparsers.add_parser("check-structure", help="Check directory structure status")
    p_check_structure.add_argument("project_dir", help="Project directory")
    p_check_structure.add_argument("--validate", action="store_true",
        help="Validate all outputs against configured structure")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 命令路由
    commands = {
        "generate-workflow": cmd_generate_workflow,
        "init": cmd_init,
        "status": cmd_status,
        "next": cmd_next,
        "start": cmd_start,
        "complete": cmd_complete,
        "validate": cmd_validate,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "token": cmd_token,
        "check": cmd_check,
        "log": cmd_log,
        "export": cmd_export,
        "reset": cmd_reset,
        "trace": cmd_trace,
        "detailed-log": cmd_detailed_log,
        "context": cmd_context,
        "validate-project": cmd_validate_project,
        # 统一 Engine 接口命令（新推荐）
        "run-engine": cmd_run_engine,
        # 测试流程扩展命令
        "loop-start": cmd_loop_start,
        "loop-complete": cmd_loop_complete,
        "wait": cmd_wait,
        "resolve": cmd_resolve,
        "loop-back": cmd_loop_back,
        # 项目初始化命令
        "init-structure": cmd_init_structure,
        "check-structure": cmd_check_structure,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
