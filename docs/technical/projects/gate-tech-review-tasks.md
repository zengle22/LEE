---
title: Gate 改进 v1.1 - 技术规格评审任务清单
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
status: 执行中
---

# Gate 改进 v1.1 - 技术规格评审任务清单

> 基于技术规格评审报告生成的实施任务清单
>
> 创建日期: 2026-02-19
> 状态: 执行中

---

## P0 任务（阻塞实施）

### 任务 1: 实现 WorkflowTemplate.get_step_order()

**优先级**: P0
**预计时间**: 0.5 天
**负责人**: 后端开发
**状态**: ⏳ 待开始

**描述**: 实现拓扑排序算法，计算步骤执行顺序

**实现文件**:
- `src/lee/orchestrator/execution/template_manager.py`

**任务细分**:
- [ ] 1.1 添加 `get_step_order()` 方法签名
- [ ] 1.2 实现拓扑排序算法
- [ ] 1.3 添加循环依赖检测
- [ ] 1.4 添加 `get_steps_after(step_id)` 方法
- [ ] 1.5 单元测试（线性、DAG、循环依赖）

**验收标准**:
```python
# 测试用例
def test_get_step_order_linear():
    """线性工作流"""
    template = WorkflowTemplate(
        steps=[
            Step(id="s1", depends_on=[]),
            Step(id="s2", depends_on=["s1"]),
            Step(id="s3", depends_on=["s2"]),
        ]
    )
    assert template.get_step_order() == ["s1", "s2", "s3"]

def test_get_step_order_dag():
    """并行分支工作流"""
    template = WorkflowTemplate(
        steps=[
            Step(id="s1", depends_on=[]),
            Step(id="s2a", depends_on=["s1"]),
            Step(id="s2b", depends_on=["s1"]),
            Step(id="s3", depends_on=["s2a", "s2b"]),
        ]
    )
    order = template.get_step_order()
    assert order[0] == "s1"
    assert order[-1] == "s3"
    assert set(order[1:3]) == {"s2a", "s2b"}

def test_get_steps_after():
    """获取后续步骤"""
    template = WorkflowTemplate(...)
    assert template.get_steps_after("s1") == ["s2a", "s2b", "s3"]
```

---

### 任务 2: 实现数据库事务支持

**优先级**: P0
**预计时间**: 0.5 天
**负责人**: 后端开发 + DBA
**状态**: ⏳ 待开始

**描述**: 实现事务上下文管理器，支持 REPEATABLE READ 隔离级别

**实现文件**:
- `src/lee/orchestrator/storage/sqlite_store.py`

**任务细分**:
- [ ] 2.1 实现 `transaction()` 上下文管理器
- [ ] 2.2 设置隔离级别为 REPEATABLE READ
- [ ] 2.3 添加事务错误处理和回滚
- [ ] 2.4 单元测试（事务提交、回滚、隔离级别）

**代码草案**:
```python
# src/lee/orchestrator/storage/sqlite_store.py
from contextlib import asynccontextmanager

class SQLiteStore:
    @asynccontextmanager
    async def transaction(self, isolation_level: str = "REPEATABLE READ"):
        """
        事务上下文管理器

        Args:
            isolation_level: 隔离级别（默认 REPEATABLE READ）
        """
        cursor = None
        try:
            cursor = self.conn.cursor()

            # 设置隔离级别
            if isolation_level == "REPEATABLE READ":
                await self.execute("BEGIN IMMEDIATE")
            else:
                await self.execute("BEGIN")

            yield cursor

            await self.execute("COMMIT")

        except Exception as e:
            if cursor:
                try:
                    await self.execute("ROLLBACK")
                except:
                    pass
            raise
```

**验收标准**:
```python
async def test_transaction_commit():
    """测试事务提交"""
    store = SQLiteStore(...)

    async with store.transaction():
        await store.insert_gate_approval(...)
        await store.insert_task_execution(...)

    # 验证数据已提交
    gate = await store.get_gate_approval(...)
    assert gate is not None

async def test_transaction_rollback():
    """测试事务回滚"""
    store = SQLiteStore(...)

    try:
        async with store.transaction():
            await store.insert_gate_approval(...)
            raise Exception("Simulated error")
    except:
        pass

    # 验证数据未提交
    gate = await store.get_gate_approval(...)
    assert gate is None
```

---

### 任务 3: 实现乐观锁机制

**优先级**: P0
**预计时间**: 0.5 天
**负责人**: 后端开发
**状态**: ⏳ 待开始

**描述**: 为 gate_approval 添加版本号，支持并发决策冲突检测

**实现文件**:
- `src/lee/orchestrator/storage/models.py`
- `src/lee/orchestrator/storage/sqlite_store.py`

**任务细分**:
- [ ] 3.1 在 `GateApproval` 添加 `version` 字段
- [ ] 3.2 在 `gate_approvals` 表添加 `version` 列
- [ ] 3.3 实现 `update_gate_approval_with_version()` 方法
- [ ] 3.4 定义 `ConcurrentDecisionError` 异常
- [ ] 3.5 单元测试（并发冲突）

**代码草案**:
```python
# src/lee/orchestrator/storage/models.py
@dataclass
class GateApproval:
    # ... 现有字段 ...
    version: int = 1

# src/lee/orchestrator/storage/sqlite_store.py
async def update_gate_approval_with_version(
    self,
    workflow_id: str,
    gate_id: str,
    status: GateStatus,
    approver: str,
    comments: str,
    expected_version: int,
    **kwargs
) -> Optional[GateApproval]:
    """
    更新门禁审批（带版本检查）

    Returns:
        更新后的 GateApproval，如果版本不匹配返回 None
    """
    cursor = await self.execute("""
        UPDATE gate_approvals
        SET status = ?,
            approver = ?,
            comments = ?,
            decided_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE workflow_id = ?
            AND gate_id = ?
            AND version = ?
    """, (status.value, approver, comments, workflow_id, gate_id, expected_version))

    if cursor.rowcount == 0:
        # 版本不匹配，并发冲突
        return None

    # 返回更新后的记录
    return await self.get_gate_approval(workflow_id, gate_id)

# src/lee/orchestrator/execution/gate_operations.py
class ConcurrentDecisionError(Exception):
    """并发决策冲突"""
    pass

async def reject_gate(...):
    gate = await self.store.get_gate_approval(workflow_id, gate_id)

    updated = await self.store.update_gate_approval_with_version(
        workflow_id, gate_id,
        status=GateStatus.REJECTED,
        approver=rejecter,
        comments=reason,
        expected_version=gate.version,
    )

    if updated is None:
        raise ConcurrentDecisionError(
            f"Gate {gate_id} was modified by another user. "
            f"Please refresh and try again."
        )
```

**验收标准**:
```python
async def test_concurrent_decision():
    """测试并发决策冲突"""
    store = SQLiteStore(...)

    # 创建 gate
    gate = await store.create_gate_approval(...)
    initial_version = gate.version

    # 并发更新
    result1 = await store.update_gate_approval_with_version(
        ..., expected_version=initial_version
    )
    result2 = await store.update_gate_approval_with_version(
        ..., expected_version=initial_version
    )

    # 只有一个成功
    assert result1 is not None or result2 is not None
    assert not (result1 is not None and result2 is not None)
```

---

### 任务 4: 编写数据库迁移脚本

**优先级**: P0
**预计时间**: 1 天
**负责人**: 后端开发 + DBA
**状态**: ⏳ 待开始

**描述**: 编写完整的迁移脚本（forward + rollback）

**实现文件**:
- `src/lee/orchestrator/storage/migrations/002_gate_actions_v1.1.py`
- `src/lee/orchestrator/storage/migrations/002_gate_actions_v1.1_rollback.py`

**任务细分**:
- [ ] 4.1 编写 forward 迁移脚本
  - [ ] 添加新列（gate_approvals + task_executions）
  - [ ] 添加索引
  - [ ] 添加 version 列和默认值
- [ ] 4.2 编写 rollback 迁移脚本
  - [ ] 删除索引（反向顺序）
  - [ ] 删除列（反向顺序）
- [ ] 4.3 编写数据验证脚本
- [ ] 4.4 在测试环境执行迁移
- [ ] 4.5 执行回滚测试

**代码框架**:
```python
# src/lee/orchestrator/storage/migrations/002_gate_actions_v1.1.py
"""
Migration 002: Gate Actions v1.1

Adds support for gate decision actions (rollback/retry/spawn/flag)
"""
import sqlite3
from pathlib import Path

def upgrade(db_path: Path) -> None:
    """执行迁移"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 步骤 1: 添加 gate_approvals 新列
        cursor.executescript("""
            ALTER TABLE gate_approvals ADD COLUMN default_reject_action TEXT;
            ALTER TABLE gate_approvals ADD COLUMN default_reject_target TEXT;
            ALTER TABLE gate_approvals ADD COLUMN default_revise_action TEXT;
            ALTER TABLE gate_approvals ADD COLUMN default_revise_target TEXT;
            ALTER TABLE gate_approvals ADD COLUMN decision_action TEXT;
            ALTER TABLE gate_approvals ADD COLUMN target_step TEXT;
            ALTER TABLE gate_approvals ADD COLUMN structured_feedback TEXT;
            ALTER TABLE gate_approvals ADD COLUMN issues TEXT;
            ALTER TABLE gate_approvals ADD COLUMN invalidated_at TIMESTAMP;
            ALTER TABLE gate_approvals ADD COLUMN version INTEGER DEFAULT 1;
        """)

        # 步骤 2: 添加 task_executions 新列
        cursor.executescript("""
            ALTER TABLE task_executions ADD COLUMN invalidated_at TIMESTAMP;
        """)

        # 步骤 3: 添加索引
        cursor.executescript("""
            CREATE INDEX idx_gate_approvals_default_action
                ON gate_approvals(default_reject_action)
                WHERE default_reject_action IS NOT NULL;

            CREATE INDEX idx_gate_approvals_decision_action
                ON gate_approvals(decision_action)
                WHERE decision_action IS NOT NULL;

            CREATE INDEX idx_task_executions_invalidated
                ON task_executions(workflow_id, step_id)
                WHERE invalidated_at IS NOT NULL;
        """)

        # 步骤 4: 为现有记录设置默认值
        cursor.execute("""
            UPDATE gate_approvals
            SET version = 1
            WHERE version IS NULL
        """)

        conn.commit()
        print("✅ Migration 002 completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 002 failed: {e}")
        raise
    finally:
        conn.close()


def downgrade(db_path: Path) -> None:
    """回滚迁移"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 步骤 1: 删除索引
        cursor.executescript("""
            DROP INDEX IF EXISTS idx_task_executions_invalidated;
            DROP INDEX IF EXISTS idx_gate_approvals_decision_action;
            DROP INDEX IF EXISTS idx_gate_approvals_default_action;
        """)

        # 步骤 2: 删除列（SQLite 不支持 DROP COLUMN，需要重建表）
        # ... 省略表重建逻辑 ...

        conn.commit()
        print("✅ Migration 002 rollback completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 002 rollback failed: {e}")
        raise
    finally:
        conn.close()


def validate(db_path: Path) -> bool:
    """验证迁移结果"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 检查列是否存在
        cursor.execute("PRAGMA table_info(gate_approvals)")
        columns = [row[1] for row in cursor.fetchall()]

        required_columns = [
            "default_reject_action",
            "default_reject_target",
            "default_revise_action",
            "default_revise_target",
            "decision_action",
            "target_step",
            "structured_feedback",
            "issues",
            "invalidated_at",
            "version",
        ]

        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False

        # 检查索引是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
                AND tbl_name='gate_approvals'
                AND name IN (
                    'idx_gate_approvals_default_action',
                    'idx_gate_approvals_decision_action'
                )
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        if len(indexes) < 2:
            print(f"❌ Missing indexes")
            return False

        print("✅ Migration 002 validation passed")
        return True

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python 002_gate_actions_v1.1.py <upgrade|downgrade|validate> [db_path]")
        sys.exit(1)

    action = sys.argv[1]
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".workflow/orchestrator.db")

    if action == "upgrade":
        upgrade(db_path)
    elif action == "downgrade":
        downgrade(db_path)
    elif action == "validate":
        validate(db_path)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
```

**验收标准**:
- ✅ 迁移脚本在测试环境执行成功
- ✅ 回滚脚本执行成功
- ✅ 验证脚本通过
- ✅ 现有数据无损坏

---

## P1 任务（重要但不阻塞）

### 任务 5: 添加结构化反馈支持

**优先级**: P1
**预计时间**: 0.5 天
**负责人**: 后端开发
**状态**: ⏳ 待开始

**描述**: 支持结构化的反馈数据（issues, expected_changes）

**任务细分**:
- [ ] 5.1 定义 `StructuredFeedback` 数据类
- [ ] 5.2 在 `revise_gate()` 中集成
- [ ] 5.3 CLI 支持 `--feedback-file`
- [ ] 5.4 单元测试

---

### 任务 6: 性能优化

**优先级**: P1
**预计时间**: 0.5 天
**负责人**: 后端开发
**状态**: ⏳ 待开始

**描述**: 优化 `rewind_to` 性能

**任务细分**:
- [ ] 6.1 缓存 `get_step_order()` 结果
- [ ] 6.2 批量数据库更新
- [ ] 6.3 性能基准测试
- [ ] 6.4 性能监控

---

## 执行顺序

```
第 1 步: 任务 1 - get_step_order() 实现
  └─ 预计: 0.5 天
  └─ 阻塞: rewind_to 实现

第 2 步: 任务 2 - 事务支持实现
  └─ 预计: 0.5 天
  └─ 可并行: 任务 1

第 3 步: 任务 3 - 乐观锁实现
  └─ 预计: 0.5 天
  └─ 可并行: 任务 1, 2

第 4 步: 任务 4 - 迁移脚本
  └─ 预计: 1 天
  └─ 依赖: 任务 1, 2, 3 完成

总计: 2-3 天（P0 任务）
```

---

## 进度跟踪

| 任务 | 负责人 | 预计 | 实际 | 状态 |
|------|--------|------|------|------|
| 任务 1: get_step_order() | - | 0.5d | - | ⏳ |
| 任务 2: 事务支持 | - | 0.5d | - | ⏳ |
| 任务 3: 乐观锁 | - | 0.5d | - | ⏳ |
| 任务 4: 迁移脚本 | - | 1d | - | ⏳ |

---

## 下一步行动

1. ✅ 技术规格评审完成
2. ⏳ 开始任务 1: 实现 `get_step_order()`
3. ⏳ 并行开始任务 2, 3
4. ⏳ 准备测试用例编写（阶段 2）
