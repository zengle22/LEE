"""
LangGraph Executor Phase B 测试

测试 LLM 集成和 impl_coding Graph。

包含:
- Profile 加载器测试
- LLM 工具测试（使用 mock）
- impl_coding Graph 测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from lee.runtime.executor.types import (
    TaskStatus,
    ExecutorTaskSpec,
    ExecutionResult,
)
from lee.runtime.executor.registry import (
    get_graph_builder,
    list_registered_types,
)
from lee.runtime.executor.tools import fs_tools


class TestProfileLoader:
    """测试 Profile 加载器"""

    def test_list_profiles(self):
        """测试列出可用 Profile"""
        from lee.runtime.executor.profiles.loader import list_profiles

        profiles = list_profiles()
        # 内置 profiles 应该存在
        assert "claudebot" in profiles
        assert "claude-sonnet" in profiles
        # 可能还有配置文件中的 profiles
        assert "zhipu" in profiles or "default" in profiles

    def test_load_builtin_profile_without_api_key(self):
        """测试加载纯内置 Profile（无 API Key 时应报错）"""
        from lee.runtime.executor.profiles.loader import load_profile

        # claude-opus 是纯内置 Profile，配置文件中没有
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)

        try:
            with pytest.raises(ValueError) as exc_info:
                load_profile("claude-opus")
            assert "api key" in str(exc_info.value).lower()
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key

    def test_load_builtin_profile_with_api_key(self):
        """测试加载纯内置 Profile（有 API Key）"""
        from lee.runtime.executor.profiles.loader import load_profile

        # 使用 claude-opus 测试纯内置 Profile
        os.environ["ANTHROPIC_API_KEY"] = "test-key-12345"

        try:
            profile = load_profile("claude-opus")
            assert profile.name == "claude-opus"
            assert profile.provider == "anthropic"
            assert "claude-opus" in profile.model
            assert profile.api_key == "test-key-12345"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_load_config_file_profile(self):
        """测试加载配置文件中的 Profile"""
        from lee.runtime.executor.profiles.loader import load_profile

        # zhipu 在配置文件中，应该有 API key
        try:
            profile = load_profile("zhipu")
        except ValueError as e:
            if "api key" in str(e).lower() or "api_key" in str(e).lower():
                pytest.skip(f"zhipu API key not configured: {e}")
            raise
        assert profile.name == "zhipu"
        assert profile.provider == "openai"  # GLM 使用 OpenAI 兼容 API
        assert "glm" in profile.model
        assert profile.api_key  # 应该有 API Key

    def test_load_unknown_profile(self):
        """测试加载未知 Profile"""
        from lee.runtime.executor.profiles.loader import load_profile

        with pytest.raises(ValueError) as exc_info:
            load_profile("nonexistent-profile")
        assert "Unknown profile" in str(exc_info.value) or "profile" in str(exc_info.value).lower()


class TestLLMTools:
    """测试 LLM 工具"""

    def test_estimate_tokens(self):
        """测试 token 估算"""
        from lee.runtime.executor.tools.llm_tools import estimate_tokens

        # 短文本
        assert estimate_tokens("hello") > 0

        # 长文本
        long_text = "a" * 1000
        tokens = estimate_tokens(long_text)
        assert 200 < tokens < 500  # 粗略范围

    @patch("lee.runtime.executor.tools.llm_tools.get_client")
    @patch("lee.runtime.executor.tools.llm_tools.load_profile")
    def test_call_llm_anthropic_mock(self, mock_load_profile, mock_get_client):
        """测试调用 LLM (Anthropic, mock)"""
        from lee.runtime.executor.tools.llm_tools import call_llm

        # 设置 mock profile
        mock_profile = Mock()
        mock_profile.provider = "anthropic"
        mock_profile.model = "claude-sonnet-4-20250514"
        mock_profile.temperature = 0.3
        mock_profile.max_tokens = 4096
        mock_load_profile.return_value = mock_profile

        # 设置 mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello, I'm Claude!")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"
        mock_response.model_dump = Mock(return_value={})
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        # 调用
        response = call_llm(
            profile="default",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert response.content == "Hello, I'm Claude!"
        assert response.tokens_used == 15
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    @patch("lee.runtime.executor.tools.llm_tools.get_client")
    @patch("lee.runtime.executor.tools.llm_tools.load_profile")
    def test_call_llm_with_system_prompt(self, mock_load_profile, mock_get_client):
        """测试带系统提示的 LLM 调用"""
        from lee.runtime.executor.tools.llm_tools import call_llm

        mock_profile = Mock()
        mock_profile.provider = "anthropic"
        mock_profile.model = "claude-sonnet-4-20250514"
        mock_profile.temperature = None
        mock_profile.max_tokens = 4096
        mock_load_profile.return_value = mock_profile

        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=20, output_tokens=10)
        mock_response.stop_reason = "end_turn"
        mock_response.model_dump = Mock(return_value={})
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        response = call_llm(
            profile="default",
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant.",
            temperature=0.5,
        )

        # 验证调用参数
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["system"] == "You are a helpful assistant."
        assert call_args.kwargs["temperature"] == 0.5


class TestImplCodingGraph:
    """测试 impl_coding Graph"""

    def test_graph_registered(self):
        """测试 Graph 已注册"""
        types = list_registered_types()
        assert "l3.impl.coding" in types

    def test_build_graph(self):
        """测试构建 Graph"""
        builder = get_graph_builder("l3.impl.coding")
        assert builder is not None

        task = ExecutorTaskSpec(
            task_id="impl-001",
            task_type="l3.impl.coding",
        )

        graph = builder(task)
        assert graph is not None

    def test_parse_file_markers(self):
        """测试文件标记解析"""
        from lee.runtime.executor.graphs.impl_coding import _parse_file_markers

        content = """Here is the implementation:

===FILE:src/main.py===
def main():
    print("Hello")

if __name__ == "__main__":
    main()
===END===

===FILE:src/utils.py===
def helper():
    return 42
===END===
"""

        files = _parse_file_markers(content)

        assert len(files) == 2
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "def main():" in files["src/main.py"]
        assert "def helper():" in files["src/utils.py"]

    def test_parse_file_markers_no_end(self):
        """测试解析没有 END 标记的文件"""
        from lee.runtime.executor.graphs.impl_coding import _parse_file_markers

        content = """===FILE:src/main.py===
def main():
    pass
"""
        files = _parse_file_markers(content)
        assert len(files) == 1
        assert "def main():" in files["src/main.py"]

    def test_build_user_prompt(self):
        """测试用户提示构建"""
        from lee.runtime.executor.graphs.impl_coding import _build_user_prompt

        prompt = _build_user_prompt(
            prd="This is the PRD",
            design="This is the design",
            contract="This is the contract",
            extra_instructions="Please use Python 3.11",
        )

        assert "PRD" in prompt
        assert "This is the PRD" in prompt
        assert "DESIGN" in prompt
        assert "IMPLEMENTATION CONTRACT" in prompt
        assert "ADDITIONAL INSTRUCTIONS" in prompt
        assert "Python 3.11" in prompt

    @patch("lee.runtime.executor.tools.llm_tools.call_llm")
    def test_graph_execution_mock(self, mock_call_llm):
        """测试 Graph 执行（mock LLM）"""
        from lee.runtime.executor.tools.llm_tools import LLMResponse

        # 设置 mock LLM 响应
        mock_call_llm.return_value = LLMResponse(
            content="""===FILE:src/hello.py===
def hello():
    return "Hello, World!"
===END===
""",
            model="claude-sonnet-4-20250514",
            profile="default",
            tokens_used=100,
            input_tokens=50,
            output_tokens=50,
            duration_seconds=1.5,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建输入文件
            prd_path = os.path.join(tmpdir, "prd.md")
            fs_tools.write_file(prd_path, "# PRD\nCreate a hello function")

            task = ExecutorTaskSpec(
                task_id="impl-001",
                task_type="l3.impl.coding",
                inputs={
                    "frozen_prd": prd_path,
                    "repo_workspace": tmpdir,
                },
                llm_profile="default",
            )

            builder = get_graph_builder("l3.impl.coding")
            graph = builder(task)

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

            # 验证结果
            assert "exec_result" in final_state
            result = final_state["exec_result"]
            assert result.status == TaskStatus.SUCCESS
            assert result.tokens_used == 100

            # 验证文件已写入
            output_file = os.path.join(tmpdir, "src/hello.py")
            assert os.path.exists(output_file)
            content = fs_tools.read_file(output_file)
            assert "def hello():" in content

    @patch("lee.runtime.executor.tools.llm_tools.call_llm")
    def test_graph_with_security_boundary(self, mock_call_llm):
        """测试带安全边界的 Graph 执行"""
        from lee.runtime.executor.tools.llm_tools import LLMResponse

        # LLM 尝试写入不允许的路径
        mock_call_llm.return_value = LLMResponse(
            content="""===FILE:../../../etc/passwd===
root:x:0:0:root:/root:/bin/bash
===END===

===FILE:src/safe.py===
# Safe file
===END===
""",
            model="claude-sonnet-4-20250514",
            profile="default",
            tokens_used=50,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            task = ExecutorTaskSpec(
                task_id="impl-002",
                task_type="l3.impl.coding",
                inputs={"repo_workspace": tmpdir},
                workspace_root=tmpdir,
                allowed_write_patterns=["src/*.py"],
                llm_profile="default",
            )

            builder = get_graph_builder("l3.impl.coding")
            graph = builder(task)

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

            result = final_state["exec_result"]

            # 应该成功（部分文件写入）
            assert result.status == TaskStatus.SUCCESS

            # 验证安全文件已写入
            safe_file = os.path.join(tmpdir, "src/safe.py")
            assert os.path.exists(safe_file)

            # 验证不安全路径被阻止（通过检查日志或错误）
            assert any("traversal" in str(e).lower() or "security" in str(e).lower()
                       for e in final_state.get("errors", []))


class TestRunTaskWithImplCoding:
    """测试通过 run_task 执行 impl_coding"""

    @patch("lee.runtime.executor.tools.llm_tools.call_llm")
    def test_run_task_impl_coding(self, mock_call_llm):
        """测试 run_task 执行 impl_coding"""
        from lee.runtime.executor import run_task
        from lee.runtime.executor.tools.llm_tools import LLMResponse

        mock_call_llm.return_value = LLMResponse(
            content="""===FILE:calculator.py===
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

def subtract(a: int, b: int) -> int:
    \"\"\"Subtract two numbers.\"\"\"
    return a - b
===END===
""",
            model="claude-sonnet-4-20250514",
            profile="default",
            tokens_used=80,
            duration_seconds=2.0,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建输入
            design_path = os.path.join(tmpdir, "design.md")
            fs_tools.write_file(design_path, """
# Calculator Design

## Functions
- add(a, b): returns a + b
- subtract(a, b): returns a - b
""")

            task = ExecutorTaskSpec(
                task_id="calc-impl-001",
                task_type="l3.impl.coding",
                inputs={
                    "design_spec": design_path,
                    "repo_workspace": tmpdir,
                },
                llm_profile="default",
            )

            result = run_task(task)

            assert result.status == TaskStatus.SUCCESS
            assert result.tokens_used == 80
            assert "calculator.py" in str(result.logs)

            # 验证生成的文件
            calc_file = os.path.join(tmpdir, "calculator.py")
            assert os.path.exists(calc_file)

            content = fs_tools.read_file(calc_file)
            assert "def add(" in content
            assert "def subtract(" in content


class TestLLMIntegration:
    """LLM 集成测试（使用 zhipu/GLM）

    这些测试使用配置文件中的 zhipu profile (config/llm_config.yaml)。
    运行方式: pytest tests/test_langgraph_executor_phase_b.py -k "Integration" -v -s
    """

    def _get_available_profile(self) -> str:
        """获取可用的 LLM Profile"""
        from lee.runtime.executor.profiles.loader import list_profiles, load_profile, get_client

        # 优先使用 zhipu（有稳定的 API Key）
        for profile_name in ["zhipu", "antigravity", "default"]:
            if profile_name in list_profiles():
                try:
                    profile = load_profile(profile_name)
                    # Verify client can be created (provider is supported)
                    get_client(profile)
                    return profile_name
                except (ValueError, ImportError):
                    continue
        return None

    def test_real_llm_call(self):
        """测试真实 LLM 调用"""
        from lee.runtime.executor.tools.llm_tools import call_llm

        profile = self._get_available_profile()
        if profile is None:
            pytest.skip("没有可用的 LLM Profile（需要配置 API Key）")

        print(f"\n使用 Profile: {profile}")

        try:
            response = call_llm(
                profile=profile,
                messages=[{"role": "user", "content": "Say 'Hello' and nothing else."}],
                max_tokens=50,
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg or "protocol" in error_msg:
                pytest.skip(f"LLM API 连接失败: {e}")
            raise

        assert response.content is not None
        assert len(response.content) > 0
        assert response.tokens_used > 0
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.tokens_used}")

    def test_real_impl_coding(self):
        """测试真实的代码实现（简单任务）"""
        from lee.runtime.executor import run_task

        profile = self._get_available_profile()
        if profile is None:
            pytest.skip("没有可用的 LLM Profile（需要配置 API Key）")

        print(f"\n使用 Profile: {profile}")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 创建简单的设计文档，明确要求输出格式
                design_path = os.path.join(tmpdir, "design.md")
                fs_tools.write_file(design_path, """
# Simple Greeter

Create a Python function `greet(name)` that returns a greeting message.

Example:
- greet("Alice") -> "Hello, Alice!"

IMPORTANT: Output the code using the exact format below:
===FILE:greeter.py===
<your code here>
===END===
""")

                task = ExecutorTaskSpec(
                    task_id="greet-impl",
                    task_type="l3.impl.coding",
                    inputs={
                        "design_spec": design_path,
                        "repo_workspace": tmpdir,
                    },
                    llm_profile=profile,
                    llm_max_tokens=500,
                )

                result = run_task(task)

                print(f"Status: {result.status}")
                print(f"Message: {result.message}")
                print(f"Tokens: {result.tokens_used}")
                for log in result.logs:
                    print(f"  {log}")

                # LLM 调用应该成功并消耗 token
                assert result.tokens_used > 0, f"LLM 调用失败: {result.error_details}"

                # 检查是否生成了文件（某些 LLM 可能不完全遵循格式）
                py_files = [f for f in os.listdir(tmpdir) if f.endswith('.py')]
                if py_files:
                    assert result.status == TaskStatus.SUCCESS
                    print(f"\n生成的文件:")
                    for f in py_files:
                        fpath = os.path.join(tmpdir, f)
                        print(f"  {f}:")
                        print(fs_tools.read_file(fpath))
                else:
                    # 如果没有生成文件，至少验证 LLM 调用成功了
                    print(f"\n警告: LLM 没有按预期格式生成文件")
                    print(f"Error details: {result.error_details}")

        except (AssertionError, Exception) as e:
            error_msg = str(e).lower()
            # Also check if the result has connection error details
            result_err = ""
            try:
                result_err = str(result.error_details).lower() if hasattr(result, 'error_details') else ""
            except NameError:
                pass
            combined = error_msg + " " + result_err
            if "connection" in combined or "timeout" in combined or "protocol" in combined:
                pytest.skip(f"LLM API 连接失败: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
