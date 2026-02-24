"""
Lee Chat Command
PM Agent interactive interface (REPL).

Refactored to use new Decision Engine architecture.
"""
import asyncio
import sys
import click
from pathlib import Path
from contextlib import contextmanager
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from datetime import datetime

from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.sqlite_store import SQLiteStore as SQLiteWorkflowStore
from lee.orchestrator.execution.llm_executor import LLMExecutor
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.pm_agent.security import SecurityManager, SecurityConfig
from lee.orchestrator.execution.pm_agent.exceptions import PMAgentException


@contextmanager
def _timestamped_echo():
    """
    Prefix all click.echo outputs with a timestamp while chat command is running.
    """
    original_echo = click.echo

    def _echo_with_ts(message="", *args, **kwargs):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        text = "" if message is None else str(message)
        return original_echo(f"{timestamp} {text}", *args, **kwargs)

    click.echo = _echo_with_ts
    try:
        yield
    finally:
        click.echo = original_echo


class LeeChatREPL:
    """Enhanced Chat REPL with Decision Engine integration"""

    def __init__(
        self,
        project_dir: str,
        enable_llm: bool = True,
    ):
        self.project_dir = Path(project_dir).resolve()

        # Initialize Orchestrator
        # Orchestrator API will use .workflow/orchestrator.db internally
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        # Use the same database path as Orchestrator API
        db_path = self.project_dir / ".workflow" / "orchestrator.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = SQLiteStore(str(db_path))

        # Align chat template discovery with Orchestrator API path resolution.
        template_dir = self.project_dir / "spec-global"
        if not template_dir.exists():
            alt_template_dir = self.project_dir / "lee" / "spec-global"
            if alt_template_dir.exists():
                template_dir = alt_template_dir
            else:
                parent_alt_template_dir = self.project_dir.parent / "lee" / "spec-global"
                if parent_alt_template_dir.exists():
                    template_dir = parent_alt_template_dir

        self.template_dir = template_dir
        template_manager = TemplateManager(
            template_dir=str(self.template_dir),
            project_root=str(self.project_dir),
        )

        self.orchestrator = Orchestrator(
            store,
            template_manager=template_manager,
            project_root=str(self.project_dir),
        )
        self.store = store  # Keep store for PMAgentRuntime

        # Initialize LLM Executor
        self.llm_executor = None
        if enable_llm:
            try:
                # Try to use a working profile instead of default
                # Priority: huawei_deepseek > deepseek > zhipu > default
                for profile_name in ["huawei_deepseek", "deepseek", "zhipu", "default"]:
                    try:
                        executor = LLMExecutor(profile=profile_name)
                        # Verify it has a valid API key (not an env var placeholder)
                        api_key = executor.config.get("api_key", "")
                        if api_key and not api_key.startswith("${"):
                            self.llm_executor = executor
                            model_name = executor.config.get("model", "unknown")
                            click.echo(f"✓ LLM Executor initialized (using {profile_name} - {model_name})")
                            break
                    except Exception:
                        continue

                if not self.llm_executor:
                    raise ValueError("No valid LLM configuration found")

            except Exception as e:
                click.echo(f"⚠ LLM Executor initialization failed: {e}")
                click.echo("Running in basic mode (no natural language understanding)")
                click.echo("Hint: Use 'lee chat --no-llm' for basic mode or configure LLM_API_KEY")

        # Initialize Security Manager
        self.security = SecurityManager(SecurityConfig())

        # Initialize Runtime
        self.runtime = PMAgentRuntime(
            self.orchestrator,
            self.llm_executor,
            self.store,
            project_dir=str(self.project_dir),
            enable_decision_engine=bool(self.llm_executor)
        )

        # Session management
        self.session_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Setup history file
        lee_dir = self.project_dir / ".lee"
        lee_dir.mkdir(exist_ok=True)
        history_file = lee_dir / "chat_history.txt"

        # Create PromptSession with history
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )
        self._ensure_prompt_auto_suggest()

        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            'pm': 'ansigreen',
            'success': 'ansigreen bold',
            'error': 'ansired bold',
            'warning': 'ansiyellow bold',
            'info': 'ansiblue',
        })

        # Statistics
        self.turn_count = 0

    async def run_loop(self):
        """Main REPL loop"""
        self._print_welcome()

        # Track consecutive Ctrl+C presses for graceful exit
        ctrl_c_count = 0
        max_ctrl_c = 2
        running = True

        while running:
            try:
                self._ensure_prompt_auto_suggest()

                # Use prompt_async with a timeout to prevent infinite blocking
                try:
                    user_input = await self.session.prompt_async(
                        HTML("<prompt>Lee></prompt> "),
                        style=self.style
                    )
                except asyncio.TimeoutError:
                    # Should not happen normally, but handle gracefully
                    continue

                # Reset Ctrl+C counter on successful input
                ctrl_c_count = 0

                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.lower() in ('exit', 'quit'):
                    click.echo("Goodbye!")
                    running = False
                    break

                if user_input.lower() in ('help', '?'):
                    self._show_help()
                    continue

                if user_input.lower() == 'metrics':
                    self._show_metrics()
                    continue

                await self.handle_input(user_input)
                self.turn_count += 1

            except KeyboardInterrupt:
                ctrl_c_count += 1
                if ctrl_c_count >= max_ctrl_c:
                    click.echo("\nGoodbye!")
                    running = False
                else:
                    click.echo("\n(Press Ctrl+C again to exit, or type 'exit')")
                    continue
            except EOFError:
                # Ctrl+D on Unix, or when input stream is closed
                # On Windows, may need to press Ctrl+Z then Enter
                click.echo("\nGoodbye!")
                running = False
            except asyncio.CancelledError:
                # Async task was cancelled
                click.echo("\nGoodbye!")
                running = False
            except Exception as e:
                # Log unexpected errors but don't crash
                self._print_error(f"Error: {e}")
                # Reset Ctrl+C counter on other errors
                ctrl_c_count = 0

        # Cleanup: ensure we exit cleanly
        try:
            # Save any pending history
            if hasattr(self.session, 'history'):
                self.session.history.save()
        except Exception:
            pass

    async def handle_input(self, text: str):
        """Process user input via PM Agent Runtime"""
        try:
            # Security check
            text = self.security.sanitize_and_validate_input(text, self.session_id)

            if self.runtime.enable_decision_engine and self.llm_executor:
                # Use new Decision Engine
                await self._handle_with_decision_engine(text)
            else:
                # Legacy mode
                await self._handle_legacy(text)

        except PMAgentException as e:
            self._print_error(f"PM Agent Error: {e.message}")
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
        except Exception as e:
            self._print_error(f"Unexpected error: {e}")

    async def _handle_with_decision_engine(self, text: str):
        """Handle input using Decision Engine via direct API responses."""
        click.echo(HTML("<pm>🤔 Processing...</pm>"))

        # Process input end-to-end (this calls Orchestrator API internally)
        result = await self.runtime.process_input(text, self.session_id)

        # Show reasoning/LLM thought process
        if 'reasoning' in result and result['reasoning']:
            click.echo()
            click.echo(click.style("🧠 思考过程:", fg='cyan', bold=True))
            click.echo(click.style(f"   {result['reasoning']}", fg='cyan'))
            click.echo()

        # Show what action will be taken
        if 'action' in result:
            action = result['action']
            click.echo(click.style(f"⚡ 执行动作: {action}", fg='yellow'))

        # Show extracted parameters
        data = result.get('data', {})
        if data:
            if 'template_id' in data:
                click.echo(click.style(f"📦 模板ID: {data['template_id']}", fg='blue'))
            if (
                data.get('template_input')
                and data.get('template_resolved')
                and data.get('template_input') != data.get('template_resolved')
            ):
                click.echo(
                    click.style(
                        f"🔎 模板解析: {data['template_input']} -> {data['template_resolved']}",
                        fg='cyan',
                    )
                )

            if 'workflow_id' in data:
                click.echo(click.style(f"🔄 工作流ID: {data['workflow_id']}", fg='blue'))

            if data.get('step_id'):
                click.echo(click.style(f"➡️  步骤ID: {data['step_id']}", fg='blue'))

            if 'gate_id' in data:
                click.echo(click.style(f"✅ 网关ID: {data['gate_id']}", fg='blue'))

        click.echo()

        # Render API response directly (chat no longer shells out to lee CLI).
        self._display_result_data(data)
        status = result.get("status")
        error = result.get("error")
        action = result.get("action", "")

        await self._maybe_show_gate_block_hint(action, data, status, error)

        if status == "success":
            self._print_success("✓ API 执行成功")
        elif status == "failed":
            self._print_warning(error or "执行未完成")
        elif status == "denied":
            self._print_error(error or "权限不足")
        else:
            self._print_error(error or f"执行失败: {status}")
            if error and ("template not found" in error.lower() or "template" in error.lower()):
                await self._show_available_templates()

        # Show confidence if available
        if 'confidence' in result:
            confidence = result['confidence']
            confidence_str = f"{confidence:.0%}" if confidence > 0 else "N/A"
            click.echo()
            click.echo(click.style(f"Confidence: {confidence_str}", fg='blue'))

    async def _maybe_show_gate_block_hint(
        self,
        action: str,
        data: dict,
        status: str,
        error: str,
    ):
        """Show explicit gate-blocked guidance when workflow is blocked."""
        if action not in {"run_workflow", "run_step", "next_step", "approve_gate"}:
            return

        run_result = data.get("run_result") if isinstance(data.get("run_result"), dict) else {}
        blocked = bool(
            run_result.get("status") == "blocked"
            or run_result.get("blocked_at")
            or (
                status == "failed"
                and isinstance(error, str)
                and any(token in error.lower() for token in ("gate", "blocked", "approval", "门禁"))
            )
        )
        if not blocked:
            return

        workflow_id = data.get("workflow_id") or run_result.get("workflow_id")
        blocked_at = run_result.get("blocked_at")

        click.echo()
        click.echo(click.style("🚧 工作流已在门禁处阻塞", fg="yellow", bold=True))
        if workflow_id:
            click.echo(f"   Workflow: {workflow_id}")
        if blocked_at:
            click.echo(f"   Blocked at: {blocked_at}")
        if error:
            click.echo(f"   Reason: {error}")

        gate_id = None
        if workflow_id:
            try:
                from lee.orchestrator.api import api_list_gates
                gates_result = await api_list_gates(str(self.project_dir), workflow_id, "pending")
                gates = gates_result.get("gates", []) if isinstance(gates_result, dict) else []
                if gates:
                    gate = gates[0]
                    gate_id = gate.get("gate_id")
                    click.echo(f"   Pending gate: {gate.get('gate_id')} [{gate.get('status')}]")
                    click.echo(f"   Gate step: {gate.get('step_id')}")
                    if gate.get("created_at"):
                        click.echo(f"   Created at: {gate.get('created_at')}")
                    if len(gates) > 1:
                        click.echo(f"   (还有 {len(gates) - 1} 个待处理门禁)")
            except Exception as e:
                click.echo(f"   (获取待处理门禁失败: {e})")

        click.echo("   下一步建议:")
        if gate_id:
            click.echo(f"   - 批准: 批准 {gate_id}")
            click.echo(f"   - 拒绝: 拒绝 {gate_id}，并说明原因")
            click.echo(f"   - 修订: 修订 {gate_id}，并给出修改建议")
            click.echo(f"   - 标记: 标记 {gate_id}，并列出问题")
        else:
            click.echo("   - 查看门禁: 查看当前gate")

    async def _show_available_templates(self):
        """Show available workflow templates when template not found"""
        click.echo()
        click.echo(click.style("💡 提示: 可用的工作流模板:", fg='yellow'))
        try:
            tm = TemplateManager(
                template_dir=str(self.template_dir),
                project_root=str(self.project_dir),
            )
            templates_dict = tm.load_all_templates()

            if templates_dict:
                templates = list(templates_dict.keys())
                for tmpl in templates[:10]:  # Show first 10
                    click.echo(f"   - {tmpl}")
                if len(templates) > 10:
                    click.echo(f"   ... 还有 {len(templates) - 10} 个")
            else:
                click.echo("   (当前项目没有配置工作流模板)")
                click.echo("   请在 specs/ 目录下创建工作流定义文件")
        except Exception as e:
            click.echo(f"   (无法获取模板列表: {e})")
        click.echo()
        click.echo(click.style("💡 提示: 使用 'lee list' 查看所有可用的命令", fg='blue'))

    async def _handle_legacy(self, text: str):
        """Handle input in legacy mode (no Decision Engine)"""
        click.echo(HTML(f"<pm>PM Agent (Basic Mode): {text}</pm>"))
        click.echo("(Natural language processing not available in basic mode)")

    def _ensure_prompt_auto_suggest(self):
        """
        Guard against prompt_toolkit config incompatibility.

        Some prompt_toolkit versions/plugins can mutate buffer.auto_suggest to bool,
        but prompt_async expects an AutoSuggest-like object with
        get_suggestion_async().
        """
        try:
            default_buffer = getattr(self.session, "default_buffer", None)
            if not default_buffer:
                return
            current = getattr(default_buffer, "auto_suggest", None)
            if isinstance(current, bool):
                default_buffer.auto_suggest = AutoSuggestFromHistory() if current else None
        except Exception:
            # Never let prompt guard break chat startup.
            pass

    def _display_result_data(self, data: dict):
        """Display result data in user-friendly format"""
        if not data:
            return

        # Display create_result (workflow creation)
        if 'create_result' in data:
            create_result = data['create_result']
            click.echo(f"\n✅ 工作流已创建:")
            if 'workflow_id' in create_result:
                click.echo(f"  ID: {create_result['workflow_id']}")
            if 'template_id' in create_result:
                click.echo(f"  模板: {create_result['template_id']}")
            if 'status' in create_result:
                click.echo(f"  状态: {create_result['status']}")

        # Display run_result (execution progress)
        if 'run_result' in data:
            run_result = data['run_result']
            click.echo(f"\n📊 执行进度:")
            if 'total_steps' in run_result:
                total = run_result['total_steps']
                completed = run_result.get('completed_steps', 0)
                click.echo(f"  进度: {completed}/{total} 步骤已完成")
            if 'status' in run_result:
                click.echo(f"  状态: {run_result['status']}")
            if 'blocked_at' in run_result:
                click.echo(f"  阻塞于: {run_result['blocked_at']}")

        # Display state information
        if 'state' in data:
            state = data['state']
            click.echo(f"\n📊 工作流状态:")
            if 'workflow_id' in state:
                click.echo(f"  ID: {state['workflow_id']}")
            if 'status' in state:
                click.echo(f"  状态: {state['status']}")
            if 'ready_steps' in state and state['ready_steps']:
                click.echo(f"  就绪步骤: {', '.join([s['id'] for s in state['ready_steps']])}")

        # Display workflows list
        if 'workflows' in data:
            workflows = data['workflows']
            click.echo(f"\n📋 Workflows ({data.get('total', len(workflows))}):")
            for wf in workflows[:10]:  # Limit to first 10
                click.echo(f"  - {wf['id']}: {wf['status']}")
            if len(workflows) > 10:
                click.echo(f"  ... and {len(workflows) - 10} more")

        # Display gates list
        if 'gates' in data:
            gates = data['gates']
            click.echo(f"\n🚧 Gates ({data.get('total', len(gates))}):")
            for gate in gates[:10]:
                click.echo(
                    f"  - {gate.get('gate_id')} [{gate.get('status')}]"
                    f" (workflow={gate.get('workflow_id')}, step={gate.get('step_id')})"
                )
                decision_action = gate.get("decision_action")
                target_step = gate.get("target_step")
                comments = gate.get("comments")
                approver = gate.get("approver")
                decided_at = gate.get("decided_at")
                issues = gate.get("issues")
                structured_feedback = gate.get("structured_feedback")

                if decision_action:
                    click.echo(f"    decision_action: {decision_action}")
                if target_step:
                    click.echo(f"    target_step: {target_step}")
                if approver:
                    click.echo(f"    approver: {approver}")
                if comments:
                    click.echo(f"    comments: {comments}")
                if issues:
                    click.echo(f"    issues: {issues}")
                if structured_feedback:
                    click.echo(f"    structured_feedback: {structured_feedback}")
                if decided_at:
                    click.echo(f"    decided_at: {decided_at}")
            if len(gates) > 10:
                click.echo(f"  ... and {len(gates) - 10} more")

        # Display step execution result
        if data.get('step_id'):
            click.echo(f"\n✓ Step executed: {data['step_id']}")
            if 'message' in data and data['message']:
                click.echo(f"  Message: {data['message']}")

        # Display gate decision result
        if data.get('decision') and data.get('gate_id'):
            click.echo(
                f"\n🚦 Gate decision: {data['gate_id']} -> {data['decision']}"
            )
            if data.get('workflow_id'):
                click.echo(f"  Workflow: {data['workflow_id']}")
            if data.get('action'):
                click.echo(f"  Action: {data['action']}")
            if data.get('target_step'):
                click.echo(f"  Target step: {data['target_step']}")
            if data.get('new_workflow_id'):
                click.echo(f"  New workflow: {data['new_workflow_id']}")

        # Display generic workflow action message (pause/resume/create/etc.)
        if 'message' in data and data.get('message') and not data.get('step_id'):
            click.echo(f"\n📝 {data['message']}")
            if data.get('workflow_id'):
                click.echo(f"  Workflow: {data['workflow_id']}")

        # Display revise/flag details
        if data.get('target_step') and not data.get('decision'):
            click.echo(f"\n🎯 Target step: {data['target_step']}")
        if isinstance(data.get('issues'), list) and data['issues']:
            click.echo("\n🚩 Issues:")
            for issue in data['issues'][:10]:
                click.echo(f"  - {issue}")

    def _print_welcome(self):
        """Print welcome message"""
        import platform

        # On Windows, Ctrl+Z+Enter is the EOF signal instead of Ctrl+D
        is_windows = platform.system() == "Windows"
        eof_hint = "Ctrl+Z then Enter" if is_windows else "Ctrl+D"

        welcome = f"""
╔════════════════════════════════════════════════════════════╗
║           Lee Chat - PM Agent Interactive Interface         ║
╚════════════════════════════════════════════════════════════╝

Session ID: {self.session_id}
Mode: {'Decision Engine (Full NLP)' if self.runtime.enable_decision_engine else 'Basic (No NLM)'}

快捷键:
  ↑/↓ 箭头键    - 翻阅历史命令
  Ctrl+C        - 中断当前输入 (按两次退出)
  {eof_hint:12} - 直接退出

Type 'help' for available commands, 'exit' to quit.
"""
        click.echo(welcome)

    def _show_help(self):
        """Show help information"""
        help_text = """
Available Commands:
  status, 当前状态          - Query workflow status
  gates, 门禁列表           - List gates (all/pending)
  run, 运行                - Execute next step
  run <step_id>            - Execute specific step
  approve <gate_id>        - Approve a gate
  reject <gate_id>         - Reject a gate
  revise <gate_id>         - Revise a gate and retry
  flag <gate_id>           - Flag a gate with issues
  pause <workflow_id>      - Pause a workflow
  resume <workflow_id>     - Resume a workflow
  list, 列表                - List all workflows
  help, ?                  - Show this help
  metrics                  - Show performance metrics
  exit, quit               - Exit chat

Examples:
  - 当前状态如何？
  - 运行下一步
  - 执行 generate_code
  - 批准 gate_review
"""
        click.echo(help_text)

    def _show_metrics(self):
        """Show performance metrics"""
        metrics = self.runtime.get_metrics()

        click.echo("\n📊 Performance Metrics:")
        click.echo(f"  Session turns: {self.turn_count}")

        if 'decision_engine' in metrics:
            de_metrics = metrics['decision_engine']
            click.echo(f"\n  Decision Engine:")
            click.echo(f"    Total decisions: {de_metrics.get('total_decisions', 0)}")
            click.echo(f"    Success rate: {de_metrics.get('success_rate', 0):.1%}")
            click.echo(f"    Fallback rate: {de_metrics.get('fallback_rate', 0):.1%}")

        if 'intent_classifier' in metrics:
            ic_metrics = metrics['intent_classifier']
            click.echo(f"\n  Intent Classifier:")
            click.echo(f"    Total classifications: {ic_metrics.get('total_classifications', 0)}")
            click.echo(f"    Rule match rate: {ic_metrics.get('rule_match_rate', 0):.1%}")

    def _print_success(self, message: str):
        """Print success message"""
        click.echo(click.style(message, fg='green', bold=True))

    def _print_error(self, message: str):
        """Print error message"""
        click.echo(click.style(message, fg='red', bold=True))

    def _print_warning(self, message: str):
        """Print warning message"""
        click.echo(click.style(message, fg='yellow', bold=True))

    def _print_info(self, message: str):
        """Print info message"""
        click.echo(click.style(message, fg='blue'))


@click.command()
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--no-llm", is_flag=True, help="Disable LLM (basic mode)")
def chat(project_dir, no_llm):
    """Start Lee Chat interactive session."""
    enable_llm = not no_llm
    with _timestamped_echo():
        repl = LeeChatREPL(
            project_dir,
            enable_llm=enable_llm,
        )
        asyncio.run(repl.run_loop())
