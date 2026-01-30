"""
LangGraph Executor 测试

Phase A: 测试最小链路
- 类型定义
- 注册表
- 工具层
- unit_test Graph
- Runner
"""

import pytest
import tempfile
import os
from pathlib import Path

from lee.runtime.executor.types import (
    TaskStatus,
    ExecutorTaskSpec,
    ExecutionResult,
)
from lee.runtime.executor.registry import (
    register_graph,
    get_graph_builder,
    list_registered_types,
)
from lee.runtime.executor.tools import security, fs_tools, shell_tools


class TestTypes:
    """测试核心类型"""

    def test_task_status_enum(self):
        """测试 TaskStatus 枚举"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILED == "failed"

    def test_executor_task_spec_defaults(self):
        """测试 ExecutorTaskSpec 默认值"""
        spec = ExecutorTaskSpec(
            task_id="test-001",
            task_type="l3.test.unit",
        )
        assert spec.task_id == "test-001"
        assert spec.task_type == "l3.test.unit"
        assert spec.inputs == {}
        assert spec.outputs == {}
        assert spec.timeout_seconds == 3600
        assert spec.max_retries == 3

    def test_execution_result_defaults(self):
        """测试 ExecutionResult 默认值"""
        result = ExecutionResult(
            task_id="test-001",
            status=TaskStatus.SUCCESS,
            message="Test passed",
        )
        assert result.task_id == "test-001"
        assert result.status == TaskStatus.SUCCESS
        assert result.artifacts == {}
        assert result.logs == []
        assert result.tokens_used == 0


class TestRegistry:
    """测试注册表"""

    def test_list_registered_types(self):
        """测试列出已注册类型"""
        types = list_registered_types()
        assert isinstance(types, list)
        # Phase A 应该注册了 l3.test.unit
        assert "l3.test.unit" in types

    def test_get_graph_builder_exists(self):
        """测试获取已存在的 Builder"""
        builder = get_graph_builder("l3.test.unit")
        assert builder is not None
        assert callable(builder)

    def test_get_graph_builder_not_exists(self):
        """测试获取不存在的 Builder"""
        builder = get_graph_builder("nonexistent.type")
        assert builder is None

    def test_register_custom_graph(self):
        """测试注册自定义 Graph"""
        def custom_builder(task):
            return None

        register_graph("custom.test", custom_builder)
        assert "custom.test" in list_registered_types()
        assert get_graph_builder("custom.test") == custom_builder


class TestSecurityTools:
    """测试安全工具"""

    def test_safe_join_normal(self):
        """测试正常路径拼接"""
        result = security.safe_join("/workspace", "src/main.py")
        assert result == "/workspace/src/main.py"

    def test_safe_join_traversal_blocked(self):
        """测试路径穿越被阻止"""
        result = security.safe_join("/workspace", "../../../etc/passwd")
        assert result is None

    def test_safe_join_dot_dot_in_middle(self):
        """测试中间的 .. 被正确处理"""
        result = security.safe_join("/workspace", "src/../lib/utils.py")
        # 应该解析为 /workspace/lib/utils.py
        assert result is not None
        assert result.endswith("lib/utils.py")

    def test_validate_write_operation_in_workspace(self):
        """测试工作区内写入验证"""
        is_safe, error = security.validate_write_operation(
            "/workspace/src/main.py",
            "/workspace",
            [],
        )
        assert is_safe is True
        assert error is None

    def test_validate_write_operation_outside_workspace(self):
        """测试工作区外写入被阻止"""
        is_safe, error = security.validate_write_operation(
            "/etc/passwd",
            "/workspace",
            [],
        )
        assert is_safe is False
        assert "outside workspace" in error.lower()

    def test_validate_write_operation_with_patterns(self):
        """测试路径模式验证"""
        # 匹配模式
        is_safe, _ = security.validate_write_operation(
            "/workspace/src/main.py",
            "/workspace",
            ["src/*.py"],
        )
        assert is_safe is True

        # 不匹配模式
        is_safe, error = security.validate_write_operation(
            "/workspace/docs/readme.md",
            "/workspace",
            ["src/*.py"],
        )
        assert is_safe is False
        assert "not in allowed patterns" in error.lower()


class TestFsTools:
    """测试文件系统工具"""

    def test_read_write_file(self):
        """测试文件读写"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            content = "Hello, World!"

            # 写入
            fs_tools.write_file(filepath, content)
            assert os.path.exists(filepath)

            # 读取
            read_content = fs_tools.read_file(filepath)
            assert read_content == content

    def test_write_file_creates_parents(self):
        """测试写入时自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "nested", "test.txt")

            fs_tools.write_file(filepath, "content", create_parents=True)
            assert os.path.exists(filepath)

    def test_write_file_security_check(self):
        """测试写入时的安全检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 尝试写入工作区外
            with pytest.raises(ValueError) as exc_info:
                fs_tools.write_file(
                    "/etc/passwd",
                    "content",
                    workspace_root=tmpdir,
                )
            assert "Security violation" in str(exc_info.value)

    def test_file_exists(self):
        """测试文件存在检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")

            assert fs_tools.file_exists(filepath) is False

            fs_tools.write_file(filepath, "content")
            assert fs_tools.file_exists(filepath) is True

    def test_compute_hash(self):
        """测试文件哈希计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            fs_tools.write_file(filepath, "Hello")

            hash_value = fs_tools.compute_hash(filepath, "sha256")
            assert len(hash_value) == 64  # SHA256 hex 长度


class TestShellTools:
    """测试 Shell 工具"""

    def test_run_shell_echo(self):
        """测试执行 echo 命令"""
        result = shell_tools.run_shell("echo 'Hello, World!'")
        assert result.exit_code == 0
        assert "Hello" in result.stdout
        assert result.success is True

    def test_run_shell_failed_command(self):
        """测试执行失败的命令"""
        result = shell_tools.run_shell("exit 1")
        assert result.exit_code == 1
        assert result.success is False

    def test_run_shell_with_cwd(self):
        """测试指定工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = shell_tools.run_shell("pwd", cwd=tmpdir)
            assert result.exit_code == 0
            assert tmpdir in result.stdout or os.path.realpath(tmpdir) in result.stdout

    def test_run_shell_with_env(self):
        """测试环境变量"""
        result = shell_tools.run_shell(
            "echo $MY_VAR",
            env={"MY_VAR": "test_value"},
        )
        assert result.exit_code == 0
        assert "test_value" in result.stdout

    def test_run_shell_timeout(self):
        """测试命令超时"""
        result = shell_tools.run_shell("sleep 10", timeout=1)
        assert result.exit_code == 124  # timeout exit code


class TestUnitTestGraph:
    """测试 unit_test Graph"""

    def test_build_graph(self):
        """测试构建 Graph"""
        from lee.runtime.executor.graphs.unit_test import build_unit_test_graph

        task = ExecutorTaskSpec(
            task_id="test-001",
            task_type="l3.test.unit",
        )

        graph = build_unit_test_graph(task)
        assert graph is not None

    def test_graph_execution_success(self):
        """测试 Graph 执行成功"""
        from lee.runtime.executor.graphs.unit_test import build_unit_test_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个简单的测试文件
            test_file = os.path.join(tmpdir, "test_sample.py")
            fs_tools.write_file(test_file, """
def test_always_pass():
    assert True
""")

            task = ExecutorTaskSpec(
                task_id="test-001",
                task_type="l3.test.unit",
                inputs={"repo_workspace": tmpdir},
                params={"test_command": f"pytest -q {test_file}"},
            )

            graph = build_unit_test_graph(task)
            initial_state = {
                "task": task,
                "logs": [],
                "errors": [],
                "current_step": "start",
                "retry_count": 0,
                "metrics": {},
                "tokens_used": 0,
                "should_stop": False,
            }

            final_state = graph.invoke(initial_state)

            assert "exec_result" in final_state
            result = final_state["exec_result"]
            assert result.status == TaskStatus.SUCCESS

    def test_graph_execution_failure(self):
        """测试 Graph 执行失败"""
        from lee.runtime.executor.graphs.unit_test import build_unit_test_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个失败的测试文件
            test_file = os.path.join(tmpdir, "test_sample.py")
            fs_tools.write_file(test_file, """
def test_always_fail():
    assert False, "This test should fail"
""")

            task = ExecutorTaskSpec(
                task_id="test-002",
                task_type="l3.test.unit",
                inputs={"repo_workspace": tmpdir},
                params={"test_command": f"pytest -q {test_file}"},
            )

            graph = build_unit_test_graph(task)
            initial_state = {
                "task": task,
                "logs": [],
                "errors": [],
                "current_step": "start",
                "retry_count": 0,
                "metrics": {},
                "tokens_used": 0,
                "should_stop": False,
            }

            final_state = graph.invoke(initial_state)

            assert "exec_result" in final_state
            result = final_state["exec_result"]
            assert result.status == TaskStatus.FAILED


class TestLangGraphRunner:
    """测试 LangGraph Runner"""

    def test_run_task_unknown_type(self):
        """测试执行未知类型任务"""
        from lee.runtime.executor import run_task

        task = ExecutorTaskSpec(
            task_id="test-001",
            task_type="unknown.type",
        )

        result = run_task(task)
        assert result.status == TaskStatus.FAILED
        assert "Unknown task_type" in result.message

    def test_run_task_success(self):
        """测试执行成功的任务"""
        from lee.runtime.executor import run_task

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test_sample.py")
            fs_tools.write_file(test_file, """
def test_pass():
    assert 1 + 1 == 2
""")

            task = ExecutorTaskSpec(
                task_id="test-001",
                task_type="l3.test.unit",
                inputs={"repo_workspace": tmpdir},
                params={"test_command": f"pytest -q {test_file}"},
            )

            result = run_task(task)

            assert result.status == TaskStatus.SUCCESS
            assert result.duration_seconds > 0
            assert result.started_at is not None
            assert result.completed_at is not None

    def test_run_task_with_report_output(self):
        """测试执行任务并生成报告"""
        from lee.runtime.executor import run_task

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test_sample.py")
            fs_tools.write_file(test_file, """
def test_pass():
    assert True
""")

            report_path = os.path.join(tmpdir, "test_report.md")

            task = ExecutorTaskSpec(
                task_id="test-001",
                task_type="l3.test.unit",
                inputs={"repo_workspace": tmpdir},
                outputs={"test_report_human": report_path},
                params={"test_command": f"pytest -q {test_file}"},
            )

            result = run_task(task)

            assert result.status == TaskStatus.SUCCESS
            assert os.path.exists(report_path)
            assert "test_report_human" in result.artifacts

            # 验证报告内容
            report_content = fs_tools.read_file(report_path)
            assert "# Test Report" in report_content
            assert "PASSED" in report_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
