"""
单元测试任务 Graph (l3.test.unit)

处理单元测试执行任务：加载配置 -> 执行测试 -> 生成报告 -> 构建结果。
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    UnitTestState,
)
from ..tools import shell_tools, fs_tools
from .common import should_continue, add_log


def build_unit_test_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建单元测试任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(UnitTestState)

    # ============================================
    # 节点定义
    # ============================================

    def load_config(state: UnitTestState) -> UnitTestState:
        """加载测试配置"""
        t = state["task"]
        logs = add_log(state, "[load_config] Loading test configuration...")
        errors = state.get("errors", []).copy()

        # 获取测试命令
        test_command = t.params.get("test_command", "pytest -q")
        logs = [*logs, f"  Test command: {test_command}"]

        # 加载测试配置文件（如果有）
        test_config: Dict[str, Any] = {}
        if "test_config" in t.inputs:
            try:
                import yaml
                config_path = t.inputs["test_config"]
                with open(config_path) as f:
                    test_config = yaml.safe_load(f) or {}
                logs = [*logs, f"  Loaded config from {config_path}"]
            except Exception as e:
                logs = [*logs, f"  Failed to load config: {e}"]
                # 配置加载失败不是致命错误

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "test_command": test_command,
            "test_config": test_config,
            "current_step": "load_config",
        }

    def run_tests(state: UnitTestState) -> UnitTestState:
        """执行测试"""
        t = state["task"]
        logs = add_log(state, "[run_tests] Running tests...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        cwd = t.inputs.get("repo_workspace", ".")
        test_command = state.get("test_command", "pytest -q")

        test_results: Dict[str, Any] = {}

        try:
            result = shell_tools.run_shell(
                test_command,
                cwd=cwd,
                timeout=t.timeout_seconds,
            )

            test_results = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": result.duration_seconds,
            }

            logs = [*logs, f"  Exit code: {result.exit_code}"]
            logs = [*logs, f"  Duration: {result.duration_seconds:.2f}s"]

            metrics["test_duration"] = result.duration_seconds
            metrics["test_exit_code"] = result.exit_code

            if result.exit_code == 0:
                logs = [*logs, "  Tests passed!"]
            else:
                logs = [*logs, "  Tests failed!"]
                errors = [*errors, f"Tests failed with exit code {result.exit_code}"]

        except Exception as e:
            logs = [*logs, f"  Test execution failed: {e}"]
            errors = [*errors, f"Test execution failed: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "test_results": test_results,
            "current_step": "run_tests",
        }

    def generate_report(state: UnitTestState) -> UnitTestState:
        """生成测试报告"""
        t = state["task"]
        logs = add_log(state, "[generate_report] Generating test report...")
        errors = state.get("errors", []).copy()

        # 生成 Markdown 报告
        test_results = state.get("test_results", {})
        exit_code = test_results.get("exit_code", "N/A")
        duration = test_results.get("duration", 0)
        stdout = test_results.get("stdout", "")
        stderr = test_results.get("stderr", "")

        status_str = "PASSED" if exit_code == 0 else "FAILED"

        report = f"""# Test Report

**Exit Code:** {exit_code}
**Duration:** {duration:.2f}s
**Status:** {status_str}

## Output

```
{stdout}
```
"""

        if stderr:
            report += f"""
## Errors

```
{stderr}
```
"""

        # 写入报告文件
        if "test_report_human" in t.outputs:
            report_path = t.outputs["test_report_human"]
            try:
                fs_tools.write_file(report_path, report)
                logs = [*logs, f"  Written report to {report_path}"]
            except Exception as e:
                logs = [*logs, f"  Failed to write report: {e}"]
                errors = [*errors, f"Failed to write report: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "test_report": report,
            "current_step": "generate_report",
        }

    def build_result(state: UnitTestState) -> UnitTestState:
        """构建执行结果"""
        t = state["task"]
        logs = add_log(state, "[build_result] Building execution result...")

        errors = state.get("errors", [])
        test_results = state.get("test_results", {})

        # 判断状态：测试 exit_code == 0 且无其他错误
        test_passed = test_results.get("exit_code") == 0
        has_other_errors = len([e for e in errors if "Tests failed" not in e]) > 0

        if test_passed and not has_other_errors:
            status = TaskStatus.SUCCESS
            message = "Tests completed successfully"
        else:
            status = TaskStatus.FAILED
            message = "Tests failed" if not test_passed else "Test execution had errors"

        # 收集 artifacts
        artifacts: Dict[str, str] = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        exec_result = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message=message,
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics={
                **state.get("metrics", {}),
                **{k: v for k, v in test_results.items() if k != "stdout" and k != "stderr"},
            },
            completed_at=datetime.now(),
        )

        return {
            **state,
            "logs": logs,
            "exec_result": exec_result,
            "current_step": "build_result",
        }

    # ============================================
    # 添加节点
    # ============================================
    graph.add_node("load_config", load_config)
    graph.add_node("run_tests", run_tests)
    graph.add_node("generate_report", generate_report)
    graph.add_node("build_result", build_result)

    # ============================================
    # 连接图
    # ============================================
    graph.set_entry_point("load_config")

    # load_config -> run_tests（配置加载失败不中断）
    graph.add_edge("load_config", "run_tests")

    # run_tests -> (条件) -> generate_report 或 build_result
    graph.add_conditional_edges(
        "run_tests",
        should_continue,
        {
            "continue": "generate_report",
            "stop": "build_result",
        }
    )

    # generate_report -> build_result
    graph.add_edge("generate_report", "build_result")

    # build_result -> END
    graph.add_edge("build_result", END)

    return graph.compile()
