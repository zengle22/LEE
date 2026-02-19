"""
Migration 002: Gate Actions v1.1

Adds support for gate decision actions (rollback/retry/spawn/flag)

This migration adds the following columns:
- gate_approvals: version, default_*_action, decision_action, target_step,
                 structured_feedback, issues, invalidated_at
- task_executions: invalidated_at

Author: LEE Team
Date: 2026-02-19
Version: 1.0
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional


# ============================================================================
# Configuration
# ============================================================================

# 新增的列定义
GATE_APPROVALS_NEW_COLUMNS = [
    ("version", "INTEGER DEFAULT 1"),
    ("default_reject_action", "TEXT"),
    ("default_reject_target", "TEXT"),
    ("default_revise_action", "TEXT"),
    ("default_revise_target", "TEXT"),
    ("decision_action", "TEXT"),
    ("target_step", "TEXT"),
    ("structured_feedback", "TEXT"),
    ("issues", "TEXT"),
    ("invalidated_at", "TIMESTAMP"),
]

TASK_EXECUTIONS_NEW_COLUMNS = [
    ("invalidated_at", "TIMESTAMP"),
]

# 新增的索引
NEW_INDEXES = [
    # gate_approvals 表索引
    ("idx_gate_approvals_default_action",
     "CREATE INDEX idx_gate_approvals_default_action ON gate_approvals(default_reject_action) WHERE default_reject_action IS NOT NULL"),
    ("idx_gate_approvals_decision_action",
     "CREATE INDEX idx_gate_approvals_decision_action ON gate_approvals(decision_action) WHERE decision_action IS NOT NULL"),
    ("idx_gate_approvals_invalidated",
     "CREATE INDEX idx_gate_approvals_invalidated ON gate_approvals(workflow_id, status) WHERE status = 'invalidated'"),
    # task_executions 表索引
    ("idx_task_executions_invalidated",
     "CREATE INDEX idx_task_executions_invalidated ON task_executions(workflow_id, step_name) WHERE invalidated_at IS NOT NULL"),
]


# ============================================================================
# Migration Functions
# ============================================================================

def check_table_exists(db_path: Path, table_name: str) -> bool:
    """检查表是否存在"""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def check_column_exists(db_path: Path, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if not check_table_exists(db_path, table_name):
        return False

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    finally:
        conn.close()


def upgrade(db_path: Path) -> None:
    """
    执行迁移（升级）

    添加 gate actions 相关的列和索引
    """
    print(f"🔄 Starting migration 002 (Gate Actions v1.1) on {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()

        # ================================================================
        # 步骤 1: 添加 gate_approvals 新列
        # ================================================================
        print("  📝 Adding columns to gate_approvals table...")

        for column_name, column_type in GATE_APPROVALS_NEW_COLUMNS:
            # 检查列是否已存在
            if check_column_exists(db_path, "gate_approvals", column_name):
                print(f"    ✓ Column '{column_name}' already exists, skipping")
                continue

            try:
                cursor.execute(f"""
                    ALTER TABLE gate_approvals
                    ADD COLUMN {column_name} {column_type}
                """)
                print(f"    ✓ Added column '{column_name}'")
            except sqlite3.OperationalError as e:
                if f"duplicate column name" in str(e).lower():
                    print(f"    ✓ Column '{column_name}' already exists")
                else:
                    raise

        # ================================================================
        # 步骤 2: 添加 task_executions 新列
        # ================================================================
        print("  📝 Adding columns to task_executions table...")

        for column_name, column_type in TASK_EXECUTIONS_NEW_COLUMNS:
            if check_column_exists(db_path, "task_executions", column_name):
                print(f"    ✓ Column '{column_name}' already exists, skipping")
                continue

            try:
                cursor.execute(f"""
                    ALTER TABLE task_executions
                    ADD COLUMN {column_name} {column_type}
                """)
                print(f"    ✓ Added column '{column_name}'")
            except sqlite3.OperationalError as e:
                if f"duplicate column name" in str(e).lower():
                    print(f"    ✓ Column '{column_name}' already exists")
                else:
                    raise

        # ================================================================
        # 步骤 3: 添加索引
        # ================================================================
        print("  📝 Creating indexes...")

        for index_name, index_sql in NEW_INDEXES:
            # 检查索引是否已存在
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name=?
            """, (index_name,))
            if cursor.fetchone():
                print(f"    ✓ Index '{index_name}' already exists, skipping")
                continue

            try:
                cursor.execute(index_sql)
                print(f"    ✓ Created index '{index_name}'")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e).lower():
                    print(f"    ✓ Index '{index_name}' already exists")
                else:
                    raise

        # ================================================================
        # 步骤 4: 为现有记录设置默认值
        # ================================================================
        print("  📝 Setting default values for existing records...")

        # 为现有的 gate_approvals 记录设置 version=1
        if check_column_exists(db_path, "gate_approvals", "version"):
            cursor.execute("""
                UPDATE gate_approvals
                SET version = 1
                WHERE version IS NULL
            """)
            affected = cursor.rowcount
            if affected > 0:
                print(f"    ✓ Set version=1 for {affected} existing gate_approval records")

        conn.commit()
        print("✅ Migration 002 completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 002 failed: {e}")
        raise
    finally:
        conn.close()


def downgrade(db_path: Path) -> None:
    """
    回滚迁移

    删除 gate actions 相关的索引和列

    注意：SQLite 不直接支持 DROP COLUMN（需要重建表）
    因此这里采用标记删除的方式
    """
    print(f"🔄 Rolling back migration 002 (Gate Actions v1.1) on {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()

        # ================================================================
        # 步骤 1: 删除索引（反向顺序）
        # ================================================================
        print("  📝 Dropping indexes...")

        for index_name, _ in reversed(NEW_INDEXES):
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                print(f"    ✓ Dropped index '{index_name}'")
            except sqlite3.OperationalError as e:
                print(f"    ⚠️  Failed to drop index '{index_name}': {e}")

        # ================================================================
        # 步骤 2: 标记列为已删除（说明）
        # ================================================================
        print("  📝 Note: SQLite does not support DROP COLUMN")
        print("  📝 Columns are left in place but should be ignored by application code")

        # 列会被保留，但应用代码应该忽略它们
        # 这是 SQLite 的限制

        conn.commit()
        print("✅ Migration 002 rollback completed successfully")
        print("⚠️  Note: Columns still exist (SQLite limitation)")
        print("⚠️  Application code should handle missing columns gracefully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 002 rollback failed: {e}")
        raise
    finally:
        conn.close()


def validate(db_path: Path) -> bool:
    """
    验证迁移结果

    检查所有必需的列和索引是否已创建
    """
    print(f"🔍 Validating migration 002 on {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        all_valid = True

        # ================================================================
        # 检查表是否存在
        # ================================================================
        if not check_table_exists(db_path, "gate_approvals"):
            print("❌ Table 'gate_approvals' does not exist")
            return False

        if not check_table_exists(db_path, "task_executions"):
            print("❌ Table 'task_executions' does not exist")
            return False

        # ================================================================
        # 检查 gate_approvals 新列
        # ================================================================
        print("  🔍 Checking gate_approvals columns...")

        for column_name, _ in GATE_APPROVALS_NEW_COLUMNS:
            if check_column_exists(db_path, "gate_approvals", column_name):
                print(f"    ✓ Column '{column_name}' exists")
            else:
                print(f"    ❌ Column '{column_name}' is missing")
                all_valid = False

        # ================================================================
        # 检查 task_executions 新列
        # ================================================================
        print("  🔍 Checking task_executions columns...")

        for column_name, _ in TASK_EXECUTIONS_NEW_COLUMNS:
            if check_column_exists(db_path, "task_executions", column_name):
                print(f"    ✓ Column '{column_name}' exists")
            else:
                print(f"    ❌ Column '{column_name}' is missing")
                all_valid = False

        # ================================================================
        # 检查索引
        # ================================================================
        print("  🔍 Checking indexes...")

        for index_name, _ in NEW_INDEXES:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name=?
            """, (index_name,))
            if cursor.fetchone():
                print(f"    ✓ Index '{index_name}' exists")
            else:
                print(f"    ⚠️  Index '{index_name}' is missing (optional)")

        # ================================================================
        # 检查数据完整性
        # ================================================================
        print("  🔍 Checking data integrity...")

        # 检查现有记录的 version 字段
        if check_column_exists(db_path, "gate_approvals", "version"):
            cursor.execute("""
                SELECT COUNT(*) FROM gate_approvals
                WHERE version IS NULL
            """)
            null_version_count = cursor.fetchone()[0]

            if null_version_count > 0:
                print(f"    ⚠️  Found {null_version_count} records with NULL version")
            else:
                print(f"    ✓ All records have version set")

        # 检查外键完整性
        cursor.execute("""
            SELECT COUNT(*) FROM gate_approvals g
            LEFT JOIN workflow_instances w ON g.workflow_id = w.id
            WHERE w.id IS NULL
        """)
        orphan_gates = cursor.fetchone()[0]

        if orphan_gates > 0:
            print(f"    ⚠️  Found {orphan_gates} orphaned gate_approvals")
        else:
            print(f"    ✓ No orphaned gate_approvals")

        if all_valid:
            print("✅ Migration 002 validation passed")
        else:
            print("❌ Migration 002 validation failed")

        return all_valid

    finally:
        conn.close()


# ============================================================================
# CLI Entry Point
# ============================================================================

def print_usage():
    """打印使用说明"""
    print("""
Usage: python 002_gate_actions_v1.1.py <command> [db_path]

Commands:
  upgrade   - Execute the migration (upgrade)
  downgrade - Rollback the migration
  validate  - Validate the migration results

Arguments:
  db_path   - Path to the SQLite database (default: .workflow/orchestrator.db)

Examples:
  python 002_gate_actions_v1.1.py upgrade
  python 002_gate_actions_v1.1.py upgrade /path/to/database.db
  python 002_gate_actions_v1.1.py validate
  python 002_gate_actions_v1.1.py downgrade
    """)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".workflow/orchestrator.db")

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    # 执行命令
    if command == "upgrade":
        upgrade(db_path)
    elif command == "downgrade":
        downgrade(db_path)
    elif command == "validate":
        result = validate(db_path)
        sys.exit(0 if result else 1)
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
