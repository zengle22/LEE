"""
测试 LEE Orchestrator v3.1 - Phase 2 集成测试

测试内容：
1. Trace 系统
2. EventLog 功能
3. Sanitization 功能
"""

import sys
import os
import tempfile
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.trace import (
    compute_hash, generate_id, sanitize as trace_sanitize,
)
from lee.orchestrator.storage.event_log import EventLog
from lee.orchestrator.utils.sanitization import sanitize


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_trace_utils():
    """测试 Trace 工具函数"""
    print_section("测试 1: Trace 工具")

    # 测试 ID 生成
    run_id = generate_id("run")
    span_id = generate_id("span")
    print(f"   ✅ ID 生成: {run_id[:20]}...")

    # 测试 Hash 计算
    data = {"test": "data", "number": 123}
    hash_value = compute_hash(data)
    print(f"   ✅ Hash 计算: {hash_value}")

    # 测试脱敏函数
    text = "Email: user@example.com"
    sanitized = trace_sanitize(text)
    assert "[EMAIL]" in sanitized
    print("   ✅ Trace 脱敏函数正常")


def test_event_log():
    """测试 EventLog 功能"""
    print_section("测试 2: EventLog")

    with tempfile.TemporaryDirectory() as tmpdir:
        event_log = EventLog(tmpdir, run_id="run_001")

        # 测试记录事件
        event_log.log_step_started("step_001", "developer", "token_001")
        print("   ✅ 步骤开始事件记录成功")

        event_log.log_step_completed("step_001", "developer", ["output.txt"], "hash123")
        print("   ✅ 步骤完成事件记录成功")

        # 测试查询事件
        events = event_log.get_events()
        assert len(events) >= 2
        print(f"   ✅ 查询到 {len(events)} 个事件")


def test_sanitization():
    """测试 Sanitization 功能"""
    print_section("测试 3: Sanitization")

    # 测试 Email 脱敏
    text = "Contact user@example.com for support"
    sanitized = sanitize(text)
    assert "[EMAIL]" in sanitized
    assert "user@example.com" not in sanitized
    print("   ✅ Email 脱敏正常")

    # 测试 Phone 脱敏
    text = "Call 13812345678 for support"
    sanitized = sanitize(text)
    assert "[PHONE]" in sanitized
    assert "13812345678" not in sanitized
    print("   ✅ Phone 脱敏正常")

    # 测试 API Key 脱敏
    text = "API key: sk-1234567890abcdef"
    sanitized = sanitize(text)
    assert "[REDACTED]" in sanitized
    print("   ✅ API Key 脱敏正常")


def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 LEE Orchestrator v3.1 - Phase 2 集成测试")
    print("=" * 60)

    test_trace_utils()
    test_event_log()
    test_sanitization()

    print("\n" + "=" * 60)
    print("✅ Phase 2 所有测试通过！")
    print("=" * 60)

    print("\n📋 验证结果:")
    print("  ✅ Trace 工具函数")
    print("  ✅ EventLog")
    print("  ✅ Sanitization")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
