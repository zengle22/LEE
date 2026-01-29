"""
测试 LEE Orchestrator v3.1 - 端到端集成测试

完整测试工作流执行的全流程：
1. L1 (Project) → L2 (Department) → L3 (Task) 工作流
2. Agent 系统集成
3. 可观测性（Trace、EventLog）
4. 验证器系统
5. 重试机制
6. 令牌管理
"""

import sys
import os
import tempfile
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.core.event_bus import EventBus, Event, EventType
from lee.orchestrator.core.project_config import ProjectConfig, Repository
from lee.orchestrator.core.workflow_parser import WorkflowParser
from lee.orchestrator.execution.trace import Run, Span, Artifact, SpanStatus, RunStatus, SpanType, ArtifactType, compute_hash, generate_id
from lee.orchestrator.execution.agent_loader import AgentSpec
from lee.orchestrator.execution.agent_context import AgentContextBuilder
from lee.orchestrator.execution.validators.base import (
    ValidationResult, ValidationError, ValidationSeverity,
)
from lee.orchestrator.execution.retry import RetryPolicy, execute_with_retry
from lee.orchestrator.core.token_manager import TokenManager, ToolGuard


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_end_to_end_workflow():
    """端到端工作流测试"""
    print_section("测试 1: 端到端工作流 (L1→L2→L3)")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 创建工作流配置
        workflow_path = Path(tmpdir) / "workflow.yaml"
        workflow_path.write_text("""
id: test_workflow
name: Test E2E Workflow
steps:
  - id: p1_init
    name: Initialize Project
    kind: agent
    executor: llm
  - id: p2_design
    name: Design System
    kind: agent
    executor: llm
    depends_on: [p1_init]
  - id: p3_implement
    name: Implementation
    kind: agent
    executor: llm
    depends_on: [p2_design]
""")

        # 2. 解析工作流
        parser = WorkflowParser(str(workflow_path))
        assert parser.workflow["id"] == "test_workflow"
        assert len(parser.get_execution_order()) == 3
        print("   ✅ 工作流解析成功 (L1 级别)")

        # 3. 获取可执行步骤
        steps = parser.parse()
        assert len(steps) == 3
        assert steps[0].id == "p1_init"
        assert steps[1].id == "p2_design"
        assert steps[2].id == "p3_implement"
        print("   ✅ 执行顺序正确 (L2/L3 级别)")

        # 4. 验证依赖关系
        graph = parser.get_dependency_graph()
        assert graph["p1_init"] == []
        assert graph["p2_design"] == ["p1_init"]
        assert graph["p3_implement"] == ["p2_design"]
        print("   ✅ 依赖关系验证成功")


def test_event_bus_integration():
    """事件总线集成测试"""
    print_section("测试 2: 事件系统集成")

    bus = EventBus()
    events_received = []

    # 订阅事件
    def handler(event):
        events_received.append(event)

    bus.subscribe(EventType.BUG_CREATED, handler)
    bus.subscribe(EventType.BUG_TRIAGED, handler)

    # 发布事件
    from datetime import datetime
    event1 = Event(
        type=EventType.BUG_CREATED,
        payload={"bug_id": "BUG-001"},
        source_workflow="test_wf",
        timestamp=datetime.now().isoformat(),
        event_id="evt-001"
    )
    event2 = Event(
        type=EventType.BUG_TRIAGED,
        payload={"bug_id": "BUG-001"},
        source_workflow="test_wf",
        timestamp=datetime.now().isoformat(),
        event_id="evt-002"
    )
    bus.publish(event1)
    bus.publish(event2)

    assert len(events_received) == 2
    assert events_received[0].type == EventType.BUG_CREATED
    assert events_received[1].type == EventType.BUG_TRIAGED
    print("   ✅ 事件发布和订阅正常")

    # 查询事件
    bug_events = bus.get_events(EventType.BUG_CREATED)
    assert len(bug_events) == 1
    print("   ✅ 事件查询正常")


def test_trace_system_integration():
    """追踪系统集成测试"""
    print_section("测试 3: 追踪系统集成")

    from datetime import datetime
    from lee.orchestrator.execution.trace import AgentInfo

    # 创建 Run
    run = Run(
        run_id=generate_id("run"),
        workflow_id="test_workflow",
        workflow_name="Test Workflow",
        started_at=datetime.now().isoformat(),
        status=RunStatus.RUNNING,
    )
    assert run.status == RunStatus.RUNNING
    print("   ✅ Run 创建成功")

    # 创建 AgentInfo
    agent_info = AgentInfo(agent_id="agent1")
    print("   ✅ AgentInfo 创建成功")

    # 创建 Span
    span = Span(
        span_id=generate_id("span"),
        run_id=run.run_id,
        span_type=SpanType.AGENT,
        name="step1",
        started_at=datetime.now().isoformat(),
        status=SpanStatus.RUNNING,
        agent=agent_info,
    )
    assert span.status == SpanStatus.RUNNING
    print("   ✅ Span 创建成功")

    # 创建 Artifact
    artifact = Artifact(
        artifact_id=generate_id("artifact"),
        run_id=run.run_id,
        span_id=span.span_id,
        artifact_type=ArtifactType.FILE_CREATED,
        path="output/test.txt",
        hash=compute_hash("test content"),
    )
    assert artifact.artifact_type == ArtifactType.FILE_CREATED
    print("   ✅ Artifact 创建成功")

    # 测试哈希计算
    hash1 = compute_hash("test")
    hash2 = compute_hash("test")
    assert hash1 == hash2
    print("   ✅ 哈希计算一致")


def test_agent_system_integration():
    """Agent 系统集成测试"""
    print_section("测试 4: Agent 系统集成")

    # 测试 AgentSpec 创建
    spec = AgentSpec(
        id="test_agent",
        name="Test Agent",
        version="1.0",
        description="Test agent description"
    )
    assert spec.id == "test_agent"
    assert spec.name == "Test Agent"
    print("   ✅ AgentSpec 创建成功")

    # 测试默认 AgentSpec
    default_spec = AgentSpec.default()
    assert default_spec.id == "agent.default"
    print("   ✅ 默认 AgentSpec 创建成功")

    # 测试 AgentContextBuilder 创建
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = AgentContextBuilder(tmpdir)
        assert builder.project_root == Path(tmpdir)
        print("   ✅ AgentContextBuilder 创建成功")


def test_validator_integration():
    """验证器集成测试"""
    print_section("测试 5: 验证器系统集成")

    # 创建 ValidationResult
    result = ValidationResult(
        validator="TestValidator",
        passed=True,
        errors=[],
        warnings=[],
        metadata={"test": "data"}
    )
    assert result.passed == True
    assert not result.has_errors
    assert not result.has_warnings
    print("   ✅ ValidationResult 创建成功")

    # 创建带错误的 ValidationResult
    error_result = ValidationResult(
        validator="ErrorValidator",
        passed=False,
        errors=[
            ValidationError(
                code="ERR_001",
                message="Test error",
                path="/test/path",
                severity=ValidationSeverity.ERROR
            )
        ],
        warnings=[],
        metadata={}
    )
    assert error_result.has_errors
    assert not error_result.has_warnings
    print("   ✅ 错误验证结果正常")


def test_retry_integration():
    """重试机制集成测试"""
    print_section("测试 6: 重试机制集成")

    # 测试成功场景
    def success_func():
        return "success"

    result = execute_with_retry(success_func, max_retries=3)
    assert result.success == True
    assert result.total_attempts == 1
    print("   ✅ 成功场景重试正常")

    # 测试失败后重试场景
    attempt_count = [0]

    def fail_then_succeed():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise ValueError("Temporary error")
        return "success"

    result = execute_with_retry(fail_then_succeed, max_retries=3)
    assert result.success == True
    assert result.total_attempts == 2
    assert result.was_successful_on_retry == True
    print("   ✅ 失败后重试成功")


def test_token_manager_integration():
    """令牌管理集成测试"""
    print_section("测试 7: 令牌管理集成")

    with tempfile.TemporaryDirectory() as tmpdir:
        tm = TokenManager(tmpdir)
        guard = ToolGuard(tm)

        # 签发令牌
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step1",
            agent_id="agent1",
            permissions=["read", "write"],
        )
        assert token.token_id.startswith("TKN-")
        print("   ✅ 令牌签发成功")

        # 验证令牌
        valid, _ = tm.validate_token(token.token_id, step_id="step1")
        assert valid == True
        print("   ✅ 令牌验证成功")

        # 检查工具权限
        allowed, _ = guard.check_tool_access(token.token_id, "Read", step_id="step1")
        assert allowed == True
        allowed, _ = guard.check_tool_access(token.token_id, "Bash", step_id="step1")
        assert allowed == False
        print("   ✅ 工具权限控制正常")


def test_project_config_integration():
    """项目配置集成测试"""
    print_section("测试 8: 项目配置集成")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建项目配置
        config_path = Path(tmpdir) / "project.yaml"
        config_path.write_text("""
id: test_project
name: Test Project

repositories:
  main:
    type: git
    path: https://github.com/test/repo
""")

        # 加载配置
        config = ProjectConfig.load(str(tmpdir))
        assert config is not None
        assert config.id == "test_project"
        assert config.name == "Test Project"
        assert len(config.repositories) == 1
        print("   ✅ 项目配置加载成功")

        # 测试路径别名
        path = config.resolve_path("@openspec/spec.yaml")
        assert "openspec" in path
        print("   ✅ 路径别名解析成功")


def test_data_sanity():
    """数据完整性测试"""
    print_section("测试 9: 数据完整性")

    # 测试敏感数据脱敏
    from lee.orchestrator.utils.sanitization import sanitize

    # 测试邮箱脱敏
    sanitized = sanitize("Contact: test@example.com")
    assert "test@" not in sanitized
    assert "[EMAIL]" in sanitized or "[REDACTED]" in sanitized
    print("   ✅ 邮箱脱敏正常")

    # 测试手机号脱敏
    sanitized = sanitize("Phone: 13812345678")
    assert "13812345678" not in sanitized
    assert "[PHONE]" in sanitized or "[REDACTED]" in sanitized
    print("   ✅ 手机号脱敏正常")

    # 测试 API Key 脱敏
    sanitized = sanitize("Key: sk-ant-api1234567890abcdefghij")
    assert "sk-ant-api1234567890abcdefghij" not in sanitized
    assert "[REDACTED]" in sanitized
    print("   ✅ API Key 脱敏正常")


def main():
    """主测试流程"""
    print("=" * 70)
    print("🚀 LEE Orchestrator v3.1 - 端到端集成测试")
    print("=" * 70)

    test_end_to_end_workflow()
    test_event_bus_integration()
    test_trace_system_integration()
    test_agent_system_integration()
    test_validator_integration()
    test_retry_integration()
    test_token_manager_integration()
    test_project_config_integration()
    test_data_sanity()

    print("\n" + "=" * 70)
    print("✅ 端到端集成测试全部通过！")
    print("=" * 70)

    print("\n📋 验证结果:")
    print("  ✅ 端到端工作流 (L1→L2→L3)")
    print("  ✅ 事件系统")
    print("  ✅ 追踪系统")
    print("  ✅ Agent 系统")
    print("  ✅ 验证器系统")
    print("  ✅ 重试机制")
    print("  ✅ 令牌管理")
    print("  ✅ 项目配置")
    print("  ✅ 数据完整性")

    print("\n" + "=" * 70)
    print("🎉 LEE Orchestrator v3.1 集成完成！")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
