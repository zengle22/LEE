"""
Smoke Gate Storage Tests
========================
"""

import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
import tempfile
import os

from src.lee.smoke.models import (
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    SmokeGateContext,
    TestExecutionRecord,
    SmokeGateReport,
    MergeGateState,
)
from src.lee.smoke.storage.store import SmokeStore


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except (PermissionError, OSError):
        pass  # 忽略清理错误


@pytest.fixture
def store(temp_db):
    """创建存储实例。"""
    return SmokeStore(db_path=temp_db)


class TestSmokeStore:
    """测试 SmokeStore 存储类。"""

    def test_init_creates_tables(self, temp_db):
        """测试初始化时创建表。"""
        store = SmokeStore(db_path=temp_db)

        # 检查表是否存在
        with sqlite3.connect(temp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "gate_contexts" in table_names
            assert "gate_reports" in table_names
            assert "merge_gate_states" in table_names
            assert "test_executions" in table_names

    def test_create_gate_context(self, store):
        """测试创建 Gate 上下文。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )

        store.create_gate_context(context)

        # 验证可以读取
        retrieved = store.get_gate_context("MR-123")
        assert retrieved is not None
        assert retrieved.merge_request_id == "MR-123"
        assert retrieved.status == SmokeGateStatus.NOT_STARTED

    def test_get_gate_context_not_found(self, store):
        """测试获取不存在的上下文。"""
        result = store.get_gate_context("MR-NOTFOUND")
        assert result is None

    def test_update_gate_context(self, store):
        """测试更新 Gate 上下文。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )

        store.create_gate_context(context)

        # 更新状态
        context.start_execution()
        result = store.update_gate_context(context)

        assert result is True

        # 验证更新
        retrieved = store.get_gate_context("MR-123")
        assert retrieved.status == SmokeGateStatus.RUNNING

    def test_create_and_get_gate_report(self, store):
        """测试创建和获取 Gate 报告。"""
        # 先创建上下文
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )
        store.create_gate_context(context)

        # 创建报告
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_login",
                priority="P0",
                status="pass",
                duration_ms=1500
            )
        ]
        started_at = datetime.now()
        completed_at = datetime.now()

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-001",
            merge_request_id="MR-123",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=started_at,
            completed_at=completed_at,
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        store.create_gate_report(report)

        # 验证可以读取
        retrieved = store.get_gate_report("run-001")
        assert retrieved is not None
        assert retrieved.smoke_run_id == "run-001"
        assert retrieved.total_cases == 1
        assert retrieved.passed == 1

    def test_get_latest_report(self, store):
        """测试获取最新报告。"""
        # 创建上下文
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )
        store.create_gate_context(context)

        # 创建两个报告
        for i, run_id in enumerate(["run-001", "run-002"]):
            executions = [
                TestExecutionRecord(
                    test_id="test_001",
                    test_name="test_login",
                    priority="P0",
                    status="pass",
                    duration_ms=1500 + i
                )
            ]
            report = SmokeGateReport.create_from_executions(
                smoke_run_id=run_id,
                merge_request_id="MR-123",
                commit_sha="abc123",
                test_set_ref="test-set-v1",
                executions=executions,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                log_path="/logs/smoke.log",
                evidence_dir="/evidence"
            )
            store.create_gate_report(report)

        # 验证获取的是最新的
        latest = store.get_latest_report("MR-123")
        assert latest is not None
        assert latest.smoke_run_id == "run-002"

    def test_create_and_get_merge_gate_state(self, store):
        """测试创建和获取 Merge Gate 状态。"""
        state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.NOT_STARTED,
            is_mergeable=False,
            blocker_issues=["No test executed"]
        )

        store.create_merge_gate_state(state)

        # 验证可以读取
        retrieved = store.get_merge_gate_state("MR-123")
        assert retrieved is not None
        assert retrieved.merge_request_id == "MR-123"
        assert retrieved.gate_status == SmokeGateStatus.NOT_STARTED
        assert retrieved.is_mergeable == False

    def test_update_merge_gate_state(self, store):
        """测试更新 Merge Gate 状态。"""
        state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.NOT_STARTED,
            is_mergeable=False
        )

        store.create_merge_gate_state(state)

        # 更新状态
        state.gate_status = SmokeGateStatus.PASSED
        state.gate_result = GateResult.ALLOW_MERGE
        state.is_mergeable = True
        state.blocker_issues = []

        result = store.update_merge_gate_state(state)
        assert result is True

        # 验证更新
        retrieved = store.get_merge_gate_state("MR-123")
        assert retrieved.gate_status == SmokeGateStatus.PASSED
        assert retrieved.is_mergeable == True
