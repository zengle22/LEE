"""
EventLog 集成测试

验证 v3.2 EventLog 激活和 LLM 元数据增强:
1. Orchestrator 初始化时创建 EventLog 实例
2. run_step 生命周期中产生 JSONL 事件
3. LLMExecutor 返回增强的元数据
"""

import asyncio
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ========================================================================
# Feature 1: Orchestrator 拥有 EventLog 实例
# ========================================================================

class TestEventLogInOrchestrator:
    """验证 Orchestrator 初始化时创建了 EventLog"""

    def test_orchestrator_has_event_log(self):
        """验证 Orchestrator 有 event_log 属性"""
        from lee.orchestrator.storage.event_log import EventLog

        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        assert hasattr(orch, 'event_log')
        assert isinstance(orch.event_log, EventLog)

    def test_event_log_project_dir(self):
        """验证 EventLog 项目目录正确设置"""
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_el")

        assert str(orch.event_log.project_dir) == "/tmp/test_el"

    def test_event_log_default_project_root(self):
        """验证 EventLog 在无 project_root 时使用 '.'"""
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store)

        assert str(orch.event_log.project_dir) == "."


# ========================================================================
# Feature 2: create_workflow 写入 RUN_CREATED 事件
# ========================================================================

class TestEventLogOnCreateWorkflow:
    """验证 create_workflow 记录 RUN_CREATED 事件"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_create_workflow_logs_run_created(self):
        """验证 create_workflow 后 events.jsonl 中有 run_created 事件"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from lee.orchestrator.storage.models import WorkflowLevel

        mock_store = AsyncMock()
        mock_store.create_workflow = AsyncMock()

        # Mock template_manager
        mock_template = MagicMock()
        mock_template.departments = []
        mock_template.tasks = []
        mock_tm = MagicMock()
        mock_tm.get_template.return_value = mock_template

        orch = Orchestrator(
            store=mock_store,
            template_manager=mock_tm,
            project_root=self.temp_dir
        )

        await orch.create_workflow(
            level=WorkflowLevel.TASK,
            template_id="test-template",
            data={"run_id": "RUN-TEST-001"},
        )

        # 检查 events.jsonl 文件
        log_path = Path(self.temp_dir) / ".workflow" / "events.jsonl"
        assert log_path.exists(), f"events.jsonl not found at {log_path}"

        events = []
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        assert len(events) >= 1
        run_created = [e for e in events if e["event_type"] == "run_created"]
        assert len(run_created) == 1
        assert run_created[0]["run_id"] == "RUN-TEST-001"


# ========================================================================
# Feature 3: LLMExecutor 增强元数据
# ========================================================================

class TestLLMExecutorEnhancedOutput:
    """验证 LLMExecutor 返回增强的 LLM 元数据"""

    @pytest.mark.asyncio
    async def test_execute_returns_token_counts(self):
        """验证 execute 返回 input_tokens, output_tokens, duration_seconds"""
        from lee.orchestrator.execution.llm_executor import LLMExecutor

        # Mock API 响应
        mock_api_response = {
            "choices": [{
                "message": {"content": "Hello, this is a test response."},
                "finish_reason": "stop",
            }],
            "model": "gpt-4-test",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 10,
                "total_tokens": 60,
            },
        }

        with patch.object(LLMExecutor, '__init__', lambda self, **kw: None):
            executor = LLMExecutor.__new__(LLMExecutor)
            executor.config = {
                "api_key": "test-key",
                "model": "gpt-4",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
            }
            executor.profile = "test"
            executor.config_manager = MagicMock()

            # Mock _call_with_retry 直接返回增强 dict
            async def mock_call(*args, **kwargs):
                return {
                    "content": "Hello, this is a test response.",
                    "model": "gpt-4-test",
                    "input_tokens": 50,
                    "output_tokens": 10,
                    "stop_reason": "stop",
                }

            executor._call_with_retry = mock_call

            result = await executor.execute({
                "prompt": "Hello",
                "system_message": "You are a test.",
            })

        assert result["status"] == "completed"
        assert result["generated_text"] == "Hello, this is a test response."
        assert result["model"] == "gpt-4-test"
        assert result["input_tokens"] == 50
        assert result["output_tokens"] == 10
        assert result["tokens_used"] == 60
        assert result["stop_reason"] == "stop"
        assert "duration_seconds" in result
        assert isinstance(result["duration_seconds"], float)

    @pytest.mark.asyncio
    async def test_execute_handles_failure(self):
        """验证 execute 在失败时仍包含 status=failed"""
        from lee.orchestrator.execution.llm_executor import LLMExecutor

        with patch.object(LLMExecutor, '__init__', lambda self, **kw: None):
            executor = LLMExecutor.__new__(LLMExecutor)
            executor.config = {
                "api_key": "test-key",
                "model": "gpt-4",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 4000,
            }
            executor.profile = "test"
            executor.config_manager = MagicMock()

            async def mock_call(*args, **kwargs):
                raise ValueError("API Error")

            executor._call_with_retry = mock_call

            result = await executor.execute({
                "prompt": "Hello",
            })

        assert result["status"] == "failed"
        assert "error" in result


# ========================================================================
# Feature 4: EventLog 基础功能验证
# ========================================================================

class TestEventLogBasics:
    """验证 EventLog 的基础写入和查询功能"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_writes_jsonl(self):
        """验证 log 方法追加 JSONL 到文件"""
        from lee.orchestrator.storage.event_log import EventLog, EventType

        el = EventLog(self.temp_dir, run_id="RUN-001")
        el.log(EventType.RUN_CREATED, data={"test": True})
        el.log(EventType.STEP_STARTED, step_id="step_1", agent_id="agent.coder")

        log_path = Path(self.temp_dir) / ".workflow" / "events.jsonl"
        assert log_path.exists()

        events = []
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        assert len(events) == 2
        assert events[0]["event_type"] == "run_created"
        assert events[0]["run_id"] == "RUN-001"
        assert events[1]["event_type"] == "step_started"
        assert events[1]["step_id"] == "step_1"

    def test_get_events_filtering(self):
        """验证事件查询过滤"""
        from lee.orchestrator.storage.event_log import EventLog, EventType

        el = EventLog(self.temp_dir, run_id="RUN-001")
        el.log(EventType.RUN_CREATED, data={"test": True})
        el.log(EventType.STEP_STARTED, step_id="s1")
        el.log(EventType.STEP_COMPLETED, step_id="s1")
        el.log(EventType.STEP_STARTED, step_id="s2")

        step_events = el.get_events(event_type=EventType.STEP_STARTED)
        assert len(step_events) == 2

        s1_events = el.get_events(step_id="s1")
        assert len(s1_events) == 2  # started + completed

    def test_compute_hash(self):
        """验证 hash 计算一致性"""
        from lee.orchestrator.storage.event_log import EventLog

        el = EventLog(self.temp_dir, run_id="RUN-001")
        data = {"key": "value", "nested": {"a": 1}}
        h1 = el._compute_hash(data)
        h2 = el._compute_hash(data)
        assert h1 == h2
        assert len(h1) == 16

    def test_gate_event_helpers_cover_revise_and_flag(self):
        """验证 gate helper 方法完整可用（包含 revise/flag/reject action）"""
        from lee.orchestrator.storage.event_log import EventLog

        el = EventLog(self.temp_dir, run_id="RUN-001")
        el.log_gate_triggered("gate_s1", "s1", "human", True)
        el.log_gate_rejected("gate_s1", "s1", "reviewer", "need changes", action="rollback")
        el.log_gate_revised("gate_s1", "s1", "reviewer", "fix formatting")
        el.log_gate_flagged("gate_s1", "s1", "reviewer", ["minor style issue"])

        events = [e.to_dict() for e in el.get_events()]
        assert [e["event_type"] for e in events] == [
            "gate_triggered",
            "gate_rejected",
            "gate_revised",
            "gate_flagged",
        ]
        assert events[1]["data"]["action"] == "rollback"
        assert events[2]["data"]["reviewer"] == "reviewer"
        assert events[3]["data"]["issues"] == ["minor style issue"]

    def test_gate_wait_time_includes_revised_and_flagged(self):
        """验证统计中的 gate_wait_times 支持 revised/flagged 终态"""
        from lee.orchestrator.storage.event_log import EventLog, EventType

        el = EventLog(self.temp_dir, run_id="RUN-001")
        el.log_gate_triggered("gate_revised", "s1", "human", True)
        el.log(EventType.GATE_REVISED, step_id="s1", data={"gate_id": "gate_revised"})
        el.log_gate_triggered("gate_flagged", "s2", "human", True)
        el.log(EventType.GATE_FLAGGED, step_id="s2", data={"gate_id": "gate_flagged"})

        stats = el.get_statistics()
        assert "gate_revised" in stats["gate_wait_times"]
        assert "gate_flagged" in stats["gate_wait_times"]
