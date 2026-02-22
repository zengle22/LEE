"""
Unit tests for SQLiteStore.transaction()

Gate Improvement v1.1 - Phase 1
"""

import pytest
import aiosqlite
import tempfile
from pathlib import Path
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
)


@pytest.fixture
async def db_store():
    """创建临时数据库存储"""
    # 使用临时文件
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    await store.connect()

    yield store

    await store.close()

    # 清理临时文件
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
class TestTransactionCommit:
    """测试事务提交"""

    async def test_transaction_commit_success(self, db_store):
        """测试事务成功提交"""
        workflow_id = "test_wf_001"

        async with db_store.transaction() as cursor:
            # 在事务内插入数据
            await cursor.execute("""
                INSERT INTO workflow_instances
                (id, level, template_id, status, current_step, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                "task",
                "test_template",
                "running",
                None,
                "{}",
                "2026-02-19T10:00:00",
                "2026-02-19T10:00:00",
            ))

        # 验证数据已提交
        workflow = await db_store.get_workflow(workflow_id)
        assert workflow is not None
        assert workflow.id == workflow_id

    async def test_transaction_multiple_operations(self, db_store):
        """测试事务内的多个操作"""
        async with db_store.transaction() as cursor:
            # 插入多个工作流
            for i in range(3):
                await cursor.execute("""
                    INSERT INTO workflow_instances
                    (id, level, template_id, status, current_step, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"test_wf_{i:03d}",
                    "task",
                    "test_template",
                    "running",
                    None,
                    "{}",
                    "2026-02-19T10:00:00",
                    "2026-02-19T10:00:00",
                ))

        # 验证所有数据都已提交
        wf_0 = await db_store.get_workflow("test_wf_000")
        wf_1 = await db_store.get_workflow("test_wf_001")
        wf_2 = await db_store.get_workflow("test_wf_002")

        assert wf_0 is not None
        assert wf_1 is not None
        assert wf_2 is not None


@pytest.mark.asyncio
class TestTransactionRollback:
    """测试事务回滚"""

    async def test_transaction_rollback_on_error(self, db_store):
        """测试错误时自动回滚"""
        workflow_id = "test_wf_rollback"

        try:
            async with db_store.transaction() as cursor:
                # 插入数据
                await cursor.execute("""
                    INSERT INTO workflow_instances
                    (id, level, template_id, status, current_step, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow_id,
                    "task",
                    "test_template",
                    "running",
                    None,
                    "{}",
                    "2026-02-19T10:00:00",
                    "2026-02-19T10:00:00",
                ))

                # 模拟错误
                raise ValueError("Simulated error")
        except ValueError:
            pass  # 预期的错误

        # 验证数据未被提交（已回滚）
        workflow = await db_store.get_workflow(workflow_id)
        assert workflow is None

    async def test_transaction_rollback_partial(self, db_store):
        """测试部分操作失败时的回滚"""
        with pytest.raises(Exception):
            async with db_store.transaction() as cursor:
                # 插入第一条记录
                await cursor.execute("""
                    INSERT INTO workflow_instances
                    (id, level, template_id, status, current_step, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ("test_wf_1", "task", "test_template", "running", None, "{}",
                    "2026-02-19T10:00:00", "2026-02-19T10:00:00"))

                # 尝试插入重复 ID（会失败）
                await cursor.execute("""
                    INSERT INTO workflow_instances
                    (id, level, template_id, status, current_step, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ("test_wf_1", "task", "test_template", "running", None, "{}",
                    "2026-02-19T10:00:00", "2026-02-19T10:00:00"))

        # 两条记录都应该失败
        wf = await db_store.get_workflow("test_wf_1")
        assert wf is None


@pytest.mark.asyncio
class TestTransactionIsolationLevels:
    """测试事务隔离级别"""

    async def test_repeatable_read(self, db_store):
        """测试 REPEATABLE READ 隔离级别"""
        async with db_store.transaction(isolation_level="REPEATABLE_READ") as cursor:
            await cursor.execute("""
                INSERT INTO workflow_instances
                (id, level, template_id, status, current_step, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("test_wf_isolation", "task", "test_template", "running", None, "{}",
                "2026-02-19T10:00:00", "2026-02-19T10:00:00"))

        # 验证提交成功
        wf = await db_store.get_workflow("test_wf_isolation")
        assert wf is not None

    async def test_immediate_isolation(self, db_store):
        """测试 IMMEDIATE 隔离级别"""
        async with db_store.transaction(isolation_level="IMMEDIATE") as cursor:
            await cursor.execute("""
                INSERT INTO workflow_instances
                (id, level, template_id, status, current_step, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("test_wf_immediate", "task", "test_template", "running", None, "{}",
                "2026-02-19T10:00:00", "2026-02-19T10:00:00"))

        wf = await db_store.get_workflow("test_wf_immediate")
        assert wf is not None

    async def test_invalid_isolation_level(self, db_store):
        """测试无效的隔离级别"""
        with pytest.raises(ValueError, match="Unknown isolation level"):
            async with db_store.transaction(isolation_level="INVALID"):
                pass


@pytest.mark.asyncio
class TestTransactionEdgeCases:
    """测试事务边界情况"""

    async def test_transaction_without_connect(self, db_store):
        """测试未连接数据库时使用事务"""
        # 关闭连接
        await db_store.close()

        with pytest.raises(RuntimeError, match="Database not connected"):
            async with db_store.transaction():
                pass

    async def test_nested_transactions(self, db_store):
        """测试嵌套事务（SQLite 不支持，应报错）"""
        # SQLite 不支持嵌套事务
        # 但我们的实现允许在事务内再次调用 transaction()
        # 实际上会共享同一个连接

        async with db_store.transaction() as cursor1:
            await cursor1.execute("""
                INSERT INTO workflow_instances
                (id, level, template_id, status, current_step, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("test_wf_nested", "task", "test_template", "running", None, "{}",
                "2026-02-19T10:00:00", "2026-02-19T10:00:00"))

            # 注意：在同一个连接上开启新事务会失败
            # 这是 SQLite 的限制
            with pytest.raises(Exception):  # 可能是 sqlite3.OperationalError
                async with db_store.transaction() as cursor2:
                    await cursor2.execute("SELECT 1")

    async def test_empty_transaction(self, db_store):
        """测试空事务（没有任何操作）"""
        async with db_store.transaction():
            pass  # 空事务

        # 应该正常完成，不报错
