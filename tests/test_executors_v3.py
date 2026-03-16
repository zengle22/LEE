"""
测试 LEE Orchestrator v3.0 - 统一 ExecutorFactory

验证：
1. LLM Executor 创建和执行
2. Shell Executor 创建和执行
3. 未知执行器会报错
4. ExecutorFactory 正常工作
"""

import asyncio
import json
import sys
import os
import pytest

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.executors import (
    BaseExecutor,
    KimiExecutor,
    LLMExecutor,
    QwenExecutor,
    ShellExecutor,
    ExecutorFactory,
)
from lee.orchestrator.execution.llm_executor import LLMConfig


def test_llm_config_falls_back_to_project_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm_config.yaml").write_text(
        "\n".join(
            [
                "default_profile: sample_profile",
                "sample_profile:",
                "  type: llm",
                "  provider: openai",
                "  base_url: https://example.invalid/v1",
                "  api_key: ${SAMPLE_API_KEY}",
                "  model: sample-model",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("SAMPLE_API_KEY=sample-key\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SAMPLE_API_KEY", raising=False)

    config = LLMConfig()

    assert config.config_path == config_dir / "llm_config.yaml"
    assert config.get_default_profile() == "sample_profile"
    assert config.get_config("sample_profile")["api_key"] == "sample-key"


def test_executor_factory_uses_config_default_profile(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm_config.yaml").write_text(
        "\n".join(
            [
                "default_profile: sample_profile",
                "sample_profile:",
                "  type: llm",
                "  provider: openai",
                "  base_url: https://example.invalid/v1",
                "  api_key: sample-key",
                "  model: sample-model",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_PROFILE", raising=False)

    executor = ExecutorFactory.create("llm")

    assert isinstance(executor, LLMExecutor)
    assert executor._executor.profile == "sample_profile"


def test_llm_config_default_profile_skips_unusable_configured_profile(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm_config.yaml").write_text(
        "\n".join(
            [
                "default_profile: broken_profile",
                "broken_profile:",
                "  type: llm",
                "  provider: openai",
                "  base_url: https://example.invalid/v1",
                "  api_key: ${BROKEN_API_KEY}",
                "  model: broken-model",
                "deepseek:",
                "  type: llm",
                "  provider: deepseek",
                "  base_url: https://api.deepseek.com",
                "  api_key: deepseek-key",
                "  model: deepseek-chat",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BROKEN_API_KEY", raising=False)

    config = LLMConfig()

    assert config.get_default_profile() == "deepseek"


def test_llm_executor_uses_config_default_profile_when_unspecified(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm_config.yaml").write_text(
        "\n".join(
            [
                "default_profile: sample_profile",
                "sample_profile:",
                "  type: llm",
                "  provider: openai",
                "  base_url: https://example.invalid/v1",
                "  api_key: sample-key",
                "  model: sample-model",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_PROFILE", raising=False)

    executor = LLMExecutor()

    assert executor._executor.profile == "sample_profile"


def test_executor_factory_qwen_chat_executor_defaults_to_qwen_profile(monkeypatch):
    monkeypatch.delenv("LLM_PROFILE", raising=False)
    monkeypatch.setattr("lee.orchestrator.execution.qwen_executor.shutil.which", lambda name: "C:/Users/test/AppData/Roaming/npm/qwen.cmd" if name in {"qwen", "qwen.cmd"} else None)

    executor = ExecutorFactory.create("qwen_chat")

    assert isinstance(executor, QwenExecutor)
    assert executor._qwen_binary.endswith("qwen.cmd")


def test_executor_factory_qwen_chat_executor_ignores_llm_profile_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "llm_config.yaml").write_text("qwen:\n  model: qwen-max\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    executor = ExecutorFactory.create("qwen_chat")

    assert isinstance(executor, QwenExecutor)


def test_executor_factory_legacy_qwen_alias_maps_to_chat_executor():
    executor = ExecutorFactory.create("qwen")

    assert isinstance(executor, QwenExecutor)


@pytest.mark.asyncio
async def test_qwen_executor_uses_headless_json_mode(monkeypatch):
    captured = {"calls": []}

    class _FakeProcess:
        returncode = 0

        async def communicate(self, input=None):
            return (
                json.dumps({"result": "hello qwen", "changed_files": ["spec/demo.md"]}).encode("utf-8"),
                b"",
            )

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["calls"].append((args, kwargs))
        return _FakeProcess()

    from lee.orchestrator.execution.qwen_executor import QwenExecutor

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    executor = QwenExecutor()
    result = await executor.execute(
        {
            "system_message": "system",
            "prompt": "user",
            "workspace": os.getcwd(),
        }
    )

    first_args = captured["calls"][0][0]
    assert str(first_args[0]).lower().endswith("qwen.cmd") or first_args[0] == "qwen"
    assert "system\n\nuser" in first_args
    assert "--output-format" in first_args
    assert result["status"] == "completed"
    assert result["generated_text"] == "hello qwen"
    assert result["changed_files"] == ["spec/demo.md"]
    assert ".workflow" in result["evidence_bundle_path"]
    assert "qwen-cli" in result["evidence_bundle_path"]


def test_qwen_executor_build_command_supports_coding_mode_flags():
    executor = QwenExecutor()

    command = executor._build_command(
        prompt="fix bug",
        output_format="stream-json",
        approval_mode="auto_edit",
        include_directories=["src", "tests"],
        all_files=True,
        yolo=False,
    )

    assert "fix bug" in command
    assert "--output-format" in command
    assert "stream-json" in command
    assert "--approval-mode" in command
    assert "auto_edit" in command
    assert command.count("--include-directories") == 1
    assert "src,tests" in command
    assert "--all-files" in command
    assert "--yolo" not in command


def test_qwen_executor_build_command_supports_yolo_shortcut_and_string_directory():
    executor = QwenExecutor()

    command = executor._build_command(
        prompt="fix bug",
        output_format="json",
        approval_mode="default",
        include_directories="src",
        all_files=False,
        yolo=True,
    )

    assert "--yolo" in command
    assert "--approval-mode" not in command
    assert command.count("--include-directories") == 1
    assert "src" in command
    assert "--all-files" not in command


def test_qwen_executor_detects_invalid_greeting_reply_for_retry():
    executor = QwenExecutor()

    assert executor._should_retry_for_invalid_reply(
        {"generated_text": "我是产品目标分析师。请告诉我您需要分析什么。", "structured_payload": None, "error": None}
    ) is True
    assert executor._should_retry_for_invalid_reply(
        {"generated_text": "我是 Qwen Code，你的 AI 编程助手。我可以帮助你。有什么需要我帮助的吗？", "structured_payload": None, "error": None}
    ) is True
    assert executor._should_retry_for_invalid_reply(
        {"generated_text": "{\"ok\": true}", "structured_payload": {"ok": True}, "error": None}
    ) is False


def test_qwen_executor_detects_placeholder_heavy_structured_payload_for_retry():
    executor = QwenExecutor()

    assert executor._should_retry_for_invalid_reply(
        {
            "generated_text": "{\"contract_type\": \"product-goal-contract\"}",
            "structured_payload": {
                "contract_type": "product-goal-contract",
                "requirement_overview": {
                    "description": "待确认",
                    "target_users": "待补充",
                    "expected_timeline": "待定",
                },
                "key_designs": {
                    "core_goal": {
                        "primary_goal": {
                            "description": "待完善",
                            "rationale": "待确认",
                        }
                    }
                },
            },
            "error": None,
        }
    ) is True


def test_qwen_executor_allows_structured_payload_with_limited_placeholders():
    executor = QwenExecutor()

    assert executor._should_retry_for_invalid_reply(
        {
            "generated_text": "{\"contract_type\": \"product-goal-contract\"}",
            "structured_payload": {
                "contract_type": "product-goal-contract",
                "requirement_overview": {
                    "description": "支持 qwen cli 作为可选执行器组件。",
                    "target_users": "LEE 工作流维护者",
                    "expected_timeline": "待确认",
                },
                "key_designs": {
                    "core_goal": {
                        "primary_goal": {
                            "description": "通过配置切换执行器。",
                            "rationale": "降低单执行器耦合。",
                        }
                    }
                },
            },
            "error": None,
        }
    ) is False


@pytest.mark.asyncio
async def test_qwen_executor_retries_invalid_reply_with_stdin(monkeypatch):
    calls = []

    async def fake_invoke_qwen(self, **kwargs):
        calls.append((kwargs["prompt_transport"], kwargs["output_format"]))
        if len(calls) == 1:
            return json.dumps(
                [
                    {
                        "type": "result",
                        "result": "我是产品目标分析师。请告诉我您需要分析什么。",
                    }
                ]
            )
        return json.dumps(
            [
                {
                    "type": "result",
                    "result": "```json\n{\"business_output\":{\"summary\":\"ok\"}}\n```",
                }
            ]
        )

    monkeypatch.setattr(QwenExecutor, "_invoke_qwen", fake_invoke_qwen)
    executor = QwenExecutor()
    result = await executor.execute({"prompt": "user", "workspace": os.getcwd()})

    assert calls == [("positional", "json"), ("stdin", "json")]
    assert result["status"] == "completed"
    assert result["structured_payload"] == {"business_output": {"summary": "ok"}}


@pytest.mark.asyncio
async def test_qwen_executor_normalizes_stream_json(monkeypatch):
    payload = "\n".join(
        [
            json.dumps({"type": "delta", "text": "hello"}),
            json.dumps({"type": "delta", "text": "world"}),
            json.dumps({"type": "result", "changed_files": ["a.md"]}),
        ]
    )

    class _FakeProcess:
        returncode = 0

        async def communicate(self, input=None):
            return (payload.encode("utf-8"), b"")

    async def fake_create_subprocess_exec(*args, **kwargs):
        return _FakeProcess()

    from lee.orchestrator.execution.qwen_executor import QwenExecutor

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setenv("QWEN_OUTPUT_FORMAT", "stream-json")
    executor = QwenExecutor()
    result = await executor.execute(
        {
            "prompt": "user",
            "workspace": os.getcwd(),
        }
    )

    assert result["status"] == "completed"
    assert "hello" in result["generated_text"]
    assert "world" in result["generated_text"]
    assert result["changed_files"] == ["a.md"]


@pytest.mark.asyncio
async def test_qwen_executor_extracts_structured_payload_from_fenced_json(monkeypatch):
    payload = json.dumps(
        [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "```json\n{\"business_output\":{\"summary\":\"中文验证通过\"}}\n```"}]}},
            {"type": "result", "result": "```json\n{\"business_output\":{\"summary\":\"中文验证通过\"}}\n```"},
        ]
    )

    class _FakeProcess:
        returncode = 0

        async def communicate(self, input=None):
            return (payload.encode("utf-8"), b"")

    async def fake_create_subprocess_exec(*args, **kwargs):
        return _FakeProcess()

    from lee.orchestrator.execution.qwen_executor import QwenExecutor

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    executor = QwenExecutor()
    result = await executor.execute(
        {
            "prompt": "user",
            "workspace": os.getcwd(),
        }
    )

    assert result["status"] == "completed"
    assert result["structured_payload"] == {
        "business_output": {"summary": "中文验证通过"}
    }


def test_executor_factory_kimi_executor_defaults_to_kimi_profile(monkeypatch):
    executor = ExecutorFactory.create("kimi")

    assert isinstance(executor, KimiExecutor)
    assert executor._kimi_binary == "kimi-cli"


@pytest.mark.asyncio
async def test_executor_factory():
    """测试 ExecutorFactory"""
    print("=" * 60)
    print("测试 ExecutorFactory")
    print("=" * 60)

    # 测试 LLM Executor 创建
    print("\n1. 测试 LLM Executor 创建...")
    try:
        llm_executor = ExecutorFactory.create("llm", profile="antigravity")
        assert isinstance(llm_executor, BaseExecutor)
        assert isinstance(llm_executor, LLMExecutor)
        print("   ✅ LLM Executor 创建成功")
    except ValueError as e:
        if "api_key" in str(e).lower() or "missing" in str(e).lower():
            print(f"   ⚠️  LLM API key not configured, skipping: {e}")
        else:
            raise

    # 测试 Shell Executor 创建
    print("\n2. 测试 Shell Executor 创建...")
    shell_executor = ExecutorFactory.create("shell")
    assert isinstance(shell_executor, BaseExecutor)
    assert isinstance(shell_executor, ShellExecutor)
    print("   ✅ Shell Executor 创建成功")

    # 测试未知类型报错
    print("\n3. 测试未知类型报错...")
    with pytest.raises(ValueError, match="Unknown executor type: legacy_executor"):
        ExecutorFactory.create("legacy_executor", role="Developer")
    print("   ✅ 未知类型报错正常")

    # 测试未知类型
    print("\n4. 测试未知类型...")
    try:
        ExecutorFactory.create("unknown")
        print("   ❌ 应该抛出异常")
        return False
    except ValueError as e:
        print(f"   ✅ 正确抛出异常: {e}")

    print("\n" + "=" * 60)
    print("✅ 所有 ExecutorFactory 测试通过！")
    print("=" * 60)
    return True


@pytest.mark.asyncio
async def test_shell_executor():
    """测试 Shell Executor 执行"""
    print("\n" + "=" * 60)
    print("测试 Shell Executor 执行")
    print("=" * 60)

    executor = ExecutorFactory.create("shell")

    # 测试简单命令
    print("\n1. 执行简单命令: echo 'Hello LEE v3'")
    result = await executor.execute({
        "command": "echo 'Hello LEE v3'",
    })
    assert result["return_code"] == 0
    assert "Hello LEE v3" in result["stdout"]
    print(f"   ✅ 输出: {result['stdout'].strip()}")

    # 测试命令失败
    print("\n2. 执行失败命令: exit 1")
    result = await executor.execute({
        "command": "exit 1",
    })
    assert result["return_code"] == 1
    assert result["status"] == "failed"
    print("   ✅ 正确处理失败命令")

    print("\n" + "=" * 60)
    print("✅ 所有 Shell Executor 测试通过！")
    print("=" * 60)
    return True


@pytest.mark.asyncio
async def test_llm_executor():
    """测试 LLM Executor（需要配置）"""
    print("\n" + "=" * 60)
    print("测试 LLM Executor")
    print("=" * 60)

    # 使用新的配置路径
    config_path = os.path.join(project_root, "config", "llm_config.yaml")
    if not os.path.exists(config_path):
        print("\n⚠️  配置文件不存在，跳过 LLM 测试")
        print(f"   配置文件路径: {config_path}")
        return True

    print("\n1. 创建 LLM Executor...")
    try:
        executor = ExecutorFactory.create("llm", profile="zhipu", config_path=config_path)
    except ValueError as e:
        if "missing api_key" in str(e).lower():
            print(f"   ⚠️  LLM API key not configured, skipping: {e}")
            return True
        raise

    print("\n2. 执行 LLM 调用...")
    result = await executor.execute({
        "prompt": "Say 'Hello LEE v3'",
    })

    print(f"   ✅ LLM 响应: {result.get('response', 'N/A')}")

    print("\n" + "=" * 60)
    print("✅ LLM Executor 测试通过！")
    print("=" * 60)
    return True


@pytest.mark.asyncio
async def test_executor_registration():
    """测试自定义 Executor 注册"""
    print("\n" + "=" * 60)
    print("测试自定义 Executor 注册")
    print("=" * 60)

    # 定义自定义 Executor
    class CustomExecutor(BaseExecutor):
        async def execute(self, input_data):
            return {"custom": "result", "input": input_data}

    # 注册
    print("\n1. 注册自定义 Executor...")
    ExecutorFactory.register("custom", CustomExecutor)
    print("   ✅ 注册成功")

    # 创建
    print("\n2. 创建自定义 Executor...")
    custom_executor = ExecutorFactory.create("custom")
    result = await custom_executor.execute({"test": "data"})
    assert result["custom"] == "result"
    print(f"   ✅ 执行成功: {result}")

    print("\n" + "=" * 60)
    print("✅ 自定义 Executor 测试通过！")
    print("=" * 60)
    return True


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🚀 LEE Orchestrator v3.0 - Executor 统一测试")
    print("=" * 60)

    results = []

    # 测试 ExecutorFactory
    results.append(await test_executor_factory())

    # 测试 Shell Executor
    results.append(await test_shell_executor())

    # 测试 LLM Executor（可能跳过）
    results.append(await test_llm_executor())

    # 测试自定义 Executor
    results.append(await test_executor_registration())

    # 总结
    print("\n" + "=" * 60)
    if all(results):
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n📋 验证结果:")
        print("  ✅ ExecutorFactory 正常工作")
        print("  ✅ LLM Executor 可创建")
        print("  ✅ Shell Executor 可执行")
        print("  ✅ 未知类型报错正常")
        print("  ✅ 支持自定义 Executor 注册")
        return 0
    else:
        print("❌ 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
