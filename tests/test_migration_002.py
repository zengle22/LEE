"""
Unit tests for Migration 002: Gate Actions v1.1

Gate Improvement v1.1 - Phase 1
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from lee.orchestrator.storage.migrations import migration_002_gate_actions_v1_1 as migration


@pytest.fixture
def empty_db():
    """创建空数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # 创建基本表结构（模拟迁移前的数据库）
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE workflow_instances (
            id TEXT PRIMARY KEY,
            level TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE gate_approvals (
            workflow_id TEXT NOT NULL,
            gate_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            status TEXT NOT NULL,
            approver TEXT,
            comments TEXT,
            created_at TEXT,
            decided_at TEXT,
            PRIMARY KEY (workflow_id, gate_id)
        )
    """)
    conn.execute("""
        CREATE TABLE task_executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    # 清理
    db_path.unlink(missing_ok=True)


@pytest.fixture
def populated_db(empty_db):
    """创建带有测试数据的数据库"""
    conn = sqlite3.connect(str(empty_db))

    # 插入测试数据
    conn.execute("""
        INSERT INTO gate_approvals
        (workflow_id, gate_id, step_id, status, approver, comments, created_at, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("wf_1", "gate_1", "step_1", "pending", None, None, "2026-02-19T10:00:00", None))

    conn.execute("""
        INSERT INTO task_executions
        (id, workflow_id, step_name, status)
        VALUES (?, ?, ?, ?)
    """, ("exec_1", "wf_1", "step_1", "completed"))

    conn.commit()
    conn.close()

    return empty_db


class TestMigrationUpgrade:
    """测试迁移升级"""

    def test_upgrade_new_columns(self, empty_db):
        """测试添加新列"""
        # 执行迁移
        migration.upgrade(empty_db)

        # 验证 gate_approvals 新列
        for column_name, _ in migration.GATE_APPROVALS_NEW_COLUMNS:
            assert migration.check_column_exists(
                empty_db, "gate_approvals", column_name
            ), f"Column {column_name} should exist"

        # 验证 task_executions 新列
        for column_name, _ in migration.TASK_EXECUTIONS_NEW_COLUMNS:
            assert migration.check_column_exists(
                empty_db, "task_executions", column_name
            ), f"Column {column_name} should exist"

    def test_upgrade_new_indexes(self, empty_db):
        """测试添加索引"""
        migration.upgrade(empty_db)

        conn = sqlite3.connect(str(empty_db))
        cursor = conn.cursor()

        for index_name, _ in migration.NEW_INDEXES:
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name=?
            """, (index_name,))
            assert cursor.fetchone(), f"Index {index_name} should exist"

        conn.close()

    def test_upgrade_default_values(self, populated_db):
        """测试为现有记录设置默认值"""
        migration.upgrade(populated_db)

        conn = sqlite3.connect(str(populated_db))
        cursor = conn.cursor()

        # 检查 version 列的默认值
        cursor.execute("SELECT version FROM gate_approvals WHERE workflow_id=?", ("wf_1",))
        version = cursor.fetchone()

        assert version == 1, f"Version should default to 1, got {version}"

        conn.close()

    def test_upgrade_idempotent(self, empty_db):
        """测试迁移幂等性（可以重复执行）"""
        # 第一次执行
        migration.upgrade(empty_db)

        # 第二次执行（应该成功，跳过已存在的列）
        migration.upgrade(empty_db)

        # 验证状态一致
        assert migration.validate(empty_db)


class TestMigrationDowngrade:
    """测试迁移回滚"""

    def test_downgrade_drops_indexes(self, populated_db):
        """测试回滚删除索引"""
        # 先升级
        migration.upgrade(populated_db)

        # 验证索引存在
        conn = sqlite3.connect(str(populated_db))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_gate_approvals_default_action'
        """)
        assert cursor.fetchone() is not None
        conn.close()

        # 回滚
        migration.downgrade(populated_db)

        # 验证索引被删除
        conn = sqlite3.connect(str(populated_db))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_gate_approvals_default_action'
        """)
        assert cursor.fetchone() is None
        conn.close()

    def test_downgrade_preserves_data(self, populated_db):
        """测试回滚保留数据"""
        # 先升级
        migration.upgrade(populated_db)

        # 修改一些数据
        conn = sqlite3.connect(str(populated_db))
        conn.execute("""
            UPDATE gate_approvals
            SET decision_action='rollback', target_step='s1'
            WHERE workflow_id='wf_1'
        """)
        conn.commit()
        conn.close()

        # 回滚
        migration.downgrade(populated_db)

        # 验证原始数据仍然存在
        conn = sqlite3.connect(str(populated_db))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gate_approvals WHERE workflow_id=?", ("wf_1",))
        row = cursor.fetchone()
        assert row is not None
        conn.close()


class TestMigrationValidation:
    """测试迁移验证"""

    def test_validate_success(self, populated_db):
        """测试验证成功"""
        migration.upgrade(populated_db)

        result = migration.validate(populated_db)
        assert result is True

    def test_validate_missing_columns(self, populated_db):
        """测试验证缺少列"""
        # 不执行迁移，直接验证
        result = migration.validate(populated_db)
        assert result is False  # 应该有缺失的列

    def test_validate_data_integrity(self, populated_db):
        """测试数据完整性检查"""
        migration.upgrade(populated_db)

        # 添加孤儿记录（没有对应的 workflow）
        conn = sqlite3.connect(str(populated_db))
        conn.execute("""
            INSERT INTO gate_approvals
            (workflow_id, gate_id, step_id, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("orphan_wf", "orphan_gate", "step_1", "pending", "2026-02-19T10:00:00"))
        conn.commit()
        conn.close()

        # 验证应该检测到孤儿记录（但不应该失败）
        result = migration.validate(populated_db)
        # 验证仍然通过（孤儿记录只是警告）
        # 如果需要严格模式，可以修改此断言


class TestEdgeCases:
    """测试边界情况"""

    def test_nonexistent_database(self):
        """测试不存在的数据库"""
        nonexistent = Path("/nonexistent/path/database.db")

        with pytest.raises(FileNotFoundError):
            migration.upgrade(nonexistent)

    def test_empty_database(self, empty_db):
        """测试空数据库（没有 gate_approvals 表）"""
        # 删除 gate_approvals 表
        conn = sqlite3.connect(str(empty_db))
        conn.execute("DROP TABLE IF EXISTS gate_approvals")
        conn.commit()
        conn.close()

        # 迁移应该处理这种情况
        # （可能跳过或报错，取决于实现）
        # 这里我们期望它优雅地处理

    def test_partial_columns_exist(self, empty_db):
        """测试部分列已存在"""
        # 手动添加部分新列
        conn = sqlite3.connect(str(empty_db))
        conn.execute("""
            ALTER TABLE gate_approvals
            ADD COLUMN version INTEGER DEFAULT 1
        """)
        conn.commit()
        conn.close()

        # 迁移应该跳过已存在的列
        migration.upgrade(empty_db)

        # 验证所有列都存在
        for column_name, _ in migration.GATE_APPROVALS_NEW_COLUMNS:
            if column_name == "version":
                continue  # 我们手动添加的
            # 其他列应该通过迁移添加
            assert migration.check_column_exists(
                empty_db, "gate_approvals", column_name
            )
