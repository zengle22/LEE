"""
Smoke Gate Manager Tests
========================
"""

import pytest
from datetime import datetime
import tempfile
import os

from src.lee.smoke.models import (
    SmokeGateStatus,
    GateResult,
    SmokeGateConfig,
    TestExecutionRecord,
)
from src.lee.smoke.gate.manager import SmokeGateManager
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
def manager(temp_db):
    """创建管理器实例。"""
    store = SmokeStore(db_path=temp_db)
    return SmokeGateManager(store=store)


@pytest.mark.asyncio
class TestSmokeGateManager:
    """测试 SmokeGateManager 类。"""

    async def test_create_gate(self, manager):
        """测试创建 Gate。"""
        config = SmokeGateConfig(test_set_ref="test-set-v1")

        context = await manager.create_gate("MR-123", config)

        assert context.merge_request_id == "MR-123"
        assert context.status == SmokeGateStatus.NOT_STARTED
        assert context.test_set_ref == "test-set-v1"

    async def test_create_gate_empty_id_raises_error(self, manager):
        """测试创建 Gate 时空 ID 抛出异常。"""
        config = SmokeGateConfig(test_set_ref="test-set-v1")

        with pytest.raises(ValueError, match="merge_request_id cannot be empty"):
            await manager.create_gate("", config)

    async def test_get_gate_status(self, manager):
        """测试获取 Gate 状态。"""
        config = SmokeGateConfig(test_set_ref="test-set-v1")
        await manager.create_gate("MR-123", config)

        status = await manager.get_gate_status("MR-123")

        assert status == SmokeGateStatus.NOT_STARTED

    async def test_get_gate_status_not_found(self, manager):
        """测试获取不存在的 Gate 状态。"""
        status = await manager.get_gate_status("MR-NOTFOUND")

        assert status is None

    async def test_get_or_create_context(self, manager):
        """测试获取或创建上下文。"""
        config = SmokeGateConfig(test_set_ref="test-set-v1")

        # 第一次调用，创建上下文
        context1 = await manager.get_or_create_context("MR-123", config)
        assert context1.status == SmokeGateStatus.NOT_STARTED

        # 第二次调用，获取已存在的上下文
        context2 = await manager.get_or_create_context("MR-123", config)
        assert context2.merge_request_id == "MR-123"
