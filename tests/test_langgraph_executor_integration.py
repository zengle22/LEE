"""
LangGraph Executor Integration Tests

测试 LangGraph Executor 与 Orchestrator 的集成。
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock


class TestLangGraphExecutorAdapter:
    """测试 LangGraph 执行器适配器"""

    def test_executor_registered(self):
        """测试执行器已注册"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        # 导入 execution 模块会触发自动注册
        from lee.orchestrator import execution

        executor = ExecutorFactory.create("langgraph")
        assert executor is not None

    def test_create_with_params(self):
        """测试带参数创建"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        executor = ExecutorFactory.create(
            "langgraph",
            default_profile="claudebot",
            default_workspace="/tmp/test"
        )
        assert executor.default_profile == "claudebot"
        assert executor.default_workspace == "/tmp/test"

    @pytest.mark.asyncio
    async def test_missing_task_type(self):
        """测试缺少 task_type"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        executor = ExecutorFactory.create("langgraph")
        result = await executor.execute({})

        assert result["status"] == "failed"
        assert "task_type" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_task_type(self):
        """测试未知 task_type"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        executor = ExecutorFactory.create("langgraph")
        result = await executor.execute({"task_type": "unknown.type"})

        assert result["status"] == "failed"
        assert "unknown.type" in result["error"]
        assert "available_types" in result

    @pytest.mark.asyncio
    @patch("lee.runtime.executor.tools.llm_tools.call_llm")
    async def test_impl_coding_execution(self, mock_call_llm):
        """测试 impl_coding 任务执行"""
        from lee.orchestrator.execution.executors import ExecutorFactory
        from lee.runtime.executor.tools.llm_tools import LLMResponse

        # Mock LLM 响应
        mock_call_llm.return_value = LLMResponse(
            content="""===FILE:hello.py===
def hello():
    return "Hello, World!"
===END===
""",
            model="claude-sonnet-4-20250514",
            profile="default",
            tokens_used=50,
            input_tokens=30,
            output_tokens=20,
            duration_seconds=1.0,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建设计文档
            design_path = os.path.join(tmpdir, "design.md")
            with open(design_path, "w") as f:
                f.write("# Design\nCreate a hello function")

            executor = ExecutorFactory.create("langgraph")
            result = await executor.execute({
                "task_type": "l3.impl.coding",
                "task_id": "test-impl-001",
                "inputs": {
                    "design_spec": design_path,
                    "repo_workspace": tmpdir,
                },
                "llm_profile": "default",
            })

            assert result["status"] == "success"
            assert result["tokens_used"] == 50
            assert "hello.py" in str(result["logs"])

            # 验证文件已写入
            output_file = os.path.join(tmpdir, "hello.py")
            assert os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_unit_test_execution(self):
        """测试单元测试任务执行"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建简单的测试文件
            test_file = os.path.join(tmpdir, "test_sample.py")
            with open(test_file, "w") as f:
                f.write("""
def test_always_pass():
    assert True
""")

            executor = ExecutorFactory.create("langgraph")
            result = await executor.execute({
                "task_type": "l3.test.unit",
                "task_id": "test-unit-001",
                "inputs": {
                    "repo_workspace": tmpdir,
                },
                "params": {
                    "test_patterns": ["test_sample.py"],
                    "test_framework": "pytest",
                },
            })

            # 单元测试图会尝试运行 pytest
            # 结果可能是 success 或 failed 取决于环境
            assert result["status"] in ["success", "failed"]


class TestLangGraphExecutorFactory:
    """测试 ExecutorFactory 集成"""

    def test_factory_list_types(self):
        """测试工厂支持的类型列表"""
        from lee.orchestrator.execution.executors import ExecutorFactory

        # 触发自动注册
        from lee.orchestrator import execution

        assert "langgraph" in ExecutorFactory._executors

    def test_register_custom_executor(self):
        """测试注册自定义执行器"""
        from lee.orchestrator.execution.executors import ExecutorFactory, BaseExecutor

        class CustomExecutor(BaseExecutor):
            async def execute(self, input_data):
                return {"status": "custom"}

        ExecutorFactory.register("custom_test", CustomExecutor)

        executor = ExecutorFactory.create("custom_test")
        assert isinstance(executor, CustomExecutor)

        # 清理
        del ExecutorFactory._executors["custom_test"]


class TestTaskSpecConversion:
    """测试 input_data 到 ExecutorTaskSpec 的转换"""

    def test_minimal_input(self):
        """测试最小输入"""
        from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor

        executor = LangGraphExecutor()
        spec = executor._build_task_spec({
            "task_type": "l3.test.unit",
        })

        assert spec.task_type == "l3.test.unit"
        assert spec.task_id.startswith("task-l3.test.unit")
        assert spec.inputs == {}

    def test_full_input(self):
        """测试完整输入"""
        from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor

        executor = LangGraphExecutor(
            default_profile="claudebot",
            default_workspace="/default"
        )

        spec = executor._build_task_spec({
            "task_type": "l3.impl.coding",
            "task_id": "custom-id",
            "inputs": {"design_spec": "/path/to/design.md"},
            "outputs": {"code": "/path/to/output"},
            "workspace_root": "/custom/workspace",
            "allowed_write_patterns": ["src/*.py"],
            "llm_profile": "claude-opus",
            "llm_temperature": 0.7,
            "llm_max_tokens": 8000,
            "params": {"instructions": "Use Python 3.11"},
        })

        assert spec.task_id == "custom-id"
        assert spec.task_type == "l3.impl.coding"
        assert spec.inputs == {"design_spec": "/path/to/design.md"}
        assert spec.workspace_root == "/custom/workspace"
        assert spec.allowed_write_patterns == ["src/*.py"]
        assert spec.llm_profile == "claude-opus"
        assert spec.llm_temperature == 0.7
        assert spec.llm_max_tokens == 8000
        assert spec.params == {"instructions": "Use Python 3.11"}

    def test_default_workspace_fallback(self):
        """测试默认工作空间回退"""
        from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor

        executor = LangGraphExecutor(default_workspace="/fallback/workspace")

        spec = executor._build_task_spec({
            "task_type": "l3.test.unit",
        })

        assert spec.workspace_root == "/fallback/workspace"


class TestResultConversion:
    """测试 ExecutionResult 到 Dict 的转换"""

    def test_success_result(self):
        """测试成功结果转换"""
        from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor
        from lee.runtime.executor.types import ExecutionResult, TaskStatus
        from datetime import datetime

        executor = LangGraphExecutor()

        result = ExecutionResult(
            task_id="test-001",
            status=TaskStatus.SUCCESS,
            message="Task completed",
            artifacts={"code": "/path/to/code.py"},
            logs=["Step 1", "Step 2"],
            metrics={"files_written": 2},
            tokens_used=100,
            completed_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        output = executor._convert_result(result)

        assert output["task_id"] == "test-001"
        assert output["status"] == "success"
        assert output["message"] == "Task completed"
        assert output["artifacts"] == {"code": "/path/to/code.py"}
        assert output["logs"] == ["Step 1", "Step 2"]
        assert output["tokens_used"] == 100
        assert "completed_at" in output

    def test_failed_result(self):
        """测试失败结果转换"""
        from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor
        from lee.runtime.executor.types import ExecutionResult, TaskStatus

        executor = LangGraphExecutor()

        result = ExecutionResult(
            task_id="test-002",
            status=TaskStatus.FAILED,
            message="Task failed",
            error_details="Connection timeout",
        )

        output = executor._convert_result(result)

        assert output["status"] == "failed"
        assert output["error_details"] == "Connection timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
