---
title: Gate 改进 v1.1 实施计划
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
status: 执行中
---

# Gate 改进 v1.1 实施计划

> 作者: LEE Team
> 日期: 2026-02-19
> 版本: 1.0
> 状态: 执行中

---

## 目录

1. [计划概览](#计划概览)
2. [阶段 1: 技术规格评审](#阶段-1-技术规格评审)
3. [阶段 2: 测试用例编写](#阶段-2-测试用例编写)
4. [阶段 3: 数据模型升级实施](#阶段-3-数据模型升级实施)
5. [关键决策记录](#关键决策记录)
6. [风险监控](#风险监控)

---

## 计划概览

### 总体时间线

```
┌─────────────────────────────────────────────────────────────────┐
│  阶段 1: 技术规格评审        │  阶段 2: 测试用例编写   │
│  ├─ 技术可行性分析           │  ├─ 单元测试设计       │
│  ├─ 接口定义评审             │  ├─ 集成测试设计       │
│  ├─ 数据库设计评审           │  ├─ 并发测试设计       │
│  └─ 实施细节确认             │  └─ 数据一致性测试     │
│  预计: 1-2 天                │  预计: 1-2 天          │
├─────────────────────────────────────────────────────────────────┤
│  阶段 3: 数据模型升级                                        │
│  ├─ 数据库迁移脚本          │
│  ├─ 模型代码更新            │
│  ├─ 迁移测试                │
│  └─ 文档更新                │
│  预计: 2-3 天               │
└─────────────────────────────────────────────────────────────────┘
```

### 任务依赖关系

```
技术规格评审 ──► 测试用例编写 ──► 数据模型升级实施
     │                    │               │
     ▼                    ▼               ▼
  接口定义冻结         测试用例评审      迁移脚本执行
  数据库设计确认       测试环境准备      模型代码更新
```

---

## 阶段 1: 技术规格评审

**目标**: 确认 v1.1 方案的技术可行性，冻结接口定义

**时间**: 1-2 天

**负责人**: 架构师 + 技术负责人

### 1.1 技术可行性分析

**任务清单**:

- [ ] **1.1.1 核心原语评审**
  - 评审 `rewind_to(step_id, mode)` 原语设计
  - 确认与现有 `WorkflowStateMachine` 的兼容性
  - 评估性能影响（大型 workflow 的 rollback 成本）

- [ ] **1.1.2 数据库设计评审**
  - 评审新增列的设计合理性
  - 评估索引策略
  - 确认迁移复杂度

- [ ] **1.1.3 并发安全性评估**
  - 评估 `rewind_to` 事务隔离级别需求
  - 确认乐观锁/悲观锁策略
  - 评估死锁风险

- [ ] **1.1.4 向后兼容性评估**
  - 确认现有 gate 的处理策略
  - 评估 CLI 命令兼容性
  - 确认 API 兼容性

**交付物**:
- 技术可行性评审报告
- 风险评估清单
- 技术债务记录

### 1.2 接口定义评审

**任务清单**:

- [ ] **1.2.1 数据模型接口**
  ```python
  # 需要评审的接口
  class GateApproval:
      default_reject_action: Optional[str]
      default_reject_target: Optional[str]
      default_revise_action: Optional[str]
      default_revise_target: Optional[str]
      decision_action: Optional[str]
      target_step: Optional[str]
      structured_feedback: Optional[Dict]
      issues: Optional[List[str]]
      invalidated_at: Optional[Timestamp]
  ```

- [ ] **1.2.2 状态机接口**
  ```python
  # 需要评审的接口
  async def rewind_to(
      workflow_id: str,
      target_step_id: str,
      mode: str,  # "rollback" | "retry"
      reason: str,
  ) -> StepResult

  async def invalidate_steps_after(
      workflow_id: str,
      step_id: str,
  ) -> List[str]

  async def _invalidate_step(
      workflow_id: str,
      step_id: str,
  ) -> None
  ```

- [ ] **1.2.3 Gate 操作接口**
  ```python
  # 需要评审的接口
  async def reject_gate(...) -> StepResult
  async def revise_gate(...) -> StepResult
  async def flag_gate(...) -> StepResult
  ```

- [ ] **1.2.4 CLI 命令接口**
  ```bash
  lee gates reject <workflow_id> <gate_id> \
    --approver <name> \
    --action <rollback|spawn> \
    --target-step <step_id> \
    --comments <reason>

  lee gates revise <workflow_id> <gate_id> \
    --reviewer <name> \
    --comments <reason> \
    --target-step <step_id> \
    --feedback-file <path>

  lee gates flag <workflow_id> <gate_id> \
    --reporter <name> \
    --issues <issue> \
    --continue-workflow/--pause-workflow
  ```

**交付物**:
- 接口定义文档（API 规格说明）
- 接口变更影响分析
- 向后兼容性保证说明

### 1.3 实施细节确认

**任务清单**:

- [ ] **1.3.1 Template Step Order 计算**
  - 确认 `Template.get_step_order()` 实现方式
  - 处理 DAG 并行分支的情况
  - 确认 `get_steps_after(step_id)` 语义

- [ ] **1.3.2 事务边界定义**
  - 确认 `rewind_to` 事务范围
  - 定义失败回滚策略
  - 确认锁持有时间

- [ ] **1.3.3 索引优化策略**
  ```sql
  -- 需要评审的索引
  CREATE INDEX idx_gate_approvals_default_action
    ON gate_approvals(default_reject_action);
  CREATE INDEX idx_task_executions_invalidated
    ON task_executions(workflow_id, status)
    WHERE status = 'invalidated';
  CREATE INDEX idx_gate_approvals_invalidated
    ON gate_approvals(workflow_id, status)
    WHERE status = 'invalidated';
  ```

- [ ] **1.3.4 数据迁移策略**
  - 确认迁移脚本执行顺序
  - 确认回滚脚本设计
  - 确认数据验证检查点

**交付物**:
- 实施技术决策文档
- 数据库迁移脚本（草稿）
- 性能优化方案

### 1.4 评审会议安排

**会议 1: 核心设计评审**
- **时间**: Day 1 上午
- **参与者**: 架构师、技术负责人、核心开发
- **议题**:
  - `rewind_to` 原语设计
  - 数据库设计
  - 并发安全策略

**会议 2: 接口评审**
- **时间**: Day 1 下午
- **参与者**: 技术负责人、后端开发、QA 负责人
- **议题**:
  - API 接口定义
  - CLI 命令设计
  - 向后兼容性

**会议 3: 实施细节评审**
- **时间**: Day 2 上午
- **参与者**: 技术负责人、DBA、运维
- **议题**:
  - 数据库迁移
  - 索引优化
  - 性能影响

**会议 4: 评审总结**
- **时间**: Day 2 下午
- **参与者**: 全体
- **议题**:
  - 评审意见汇总
  - 风险确认
  - 实施计划调整

**交付物**:
- 评审会议纪要
- 行动项清单
- 风险登记表

---

## 阶段 2: 测试用例编写

**目标**: 编写全面的测试用例，确保数据一致性和并发安全

**时间**: 1-2 天

**负责人**: QA 负责人 + 开发负责人

### 2.1 单元测试设计

**任务清单**:

- [ ] **2.1.1 WorkflowStateMachine 测试**
  ```python
  class TestWorkflowStateMachine:
      async def test_rewind_to_rollback_mode(self):
          """测试 rewind_to 的 rollback 模式"""
          # Arrange: 创建包含 s1->s2->s3->gate 的工作流
          # 执行到 s1, s2 完成，gate 在 s3

          # Act: rewind_to(s1, mode="rollback")

          # Assert:
          # - s2, s3 被作废
          # - current_step = s1
          # - workflow status = RUNNING
          # - s1 被 enqueue

      async def test_rewind_to_retry_mode(self):
          """测试 rewind_to 的 retry 模式"""
          # Arrange: s1->s2->gate, s1 完成，gate 在 s2

          # Act: rewind_to(s2, mode="retry")

          # Assert:
          # - gate 被作废
          # - s2 attempt += 1
          # - current_step = s2
          # - s2 被重新 enqueue

      async def test_rewind_to_with_dag(self):
          """测试 DAG 结构的 rewind"""
          # Arrange: s1->(s2a, s2b)->s3
          # s2a, s2b 完成，gate 在 s3

          # Act: rewind_to(s1, mode="rollback")

          # Assert:
          # - s2a, s2b, s3 都被作废
          # - current_step = s1

      async def test_rewind_to_transaction_rollback(self):
          """测试 rewind_to 事务回滚"""
          # Arrange: 模拟中间步骤失败

          # Act: rewind_to(...)

          # Assert: 所有变更被回滚，状态一致
  ```

- [ ] **2.1.2 Gate 操作测试**
  ```python
  class TestGateOperations:
      async def test_reject_with_rollback(self):
          """测试 reject + rollback"""

      async def test_reject_with_spawn(self):
          """测试 reject + spawn"""

      async def test_revise_with_retry(self):
          """测试 revise + retry"""

      async def test_flag_with_continue(self):
          """测试 flag + continue_workflow"""

      async def test_flag_with_pause(self):
          """测试 flag + pause_workflow"""

      async def test_default_action_from_db(self):
          """测试从 DB 读取默认 action"""
  ```

- [ ] **2.1.3 数据清理测试**
  ```python
  class TestDataCleanup:
      async def test_invalidate_task_executions(self):
          """测试 task_executions 作废"""

      async def test_invalidate_gate_approvals(self):
          """测试 gate_approvals 作废"""

      async def test_clear_step_attempts(self):
          """测试 step_attempts 清理"""

      async def test_clear_step_outputs(self):
          """测试 step_outputs 清理"""

      async def test_cleanup_completeness(self):
          """测试清理完整性"""
          # 确保所有关联数据都被清理
  ```

**交付物**:
- 单元测试用例文档
- 测试代码（pytest 格式）
- Mock 数据准备脚本

### 2.2 集成测试设计

**任务清单**:

- [ ] **2.2.1 端到端场景测试**
  ```python
  class TestE2EScenarios:
      async def test_full_rejection_rollback_flow(self):
          """测试完整的拒绝回退流程"""
          # 1. 运行工作流到 gate
          # 2. reject with rollback
          # 3. 验证回退到正确步骤
          # 4. 验证工作流继续执行
          # 5. 验证数据一致性

      async def test_full_revision_retry_flow(self):
          """测试完整的修订重试流程"""
          # 1. 运行工作流到 gate
          # 2. revise with feedback
          # 3. 验证重试目标步骤
          # 4. 验证工作流继续执行

      async def test_full_spawn_workflow_flow(self):
          """测试完整的派生工作流流程"""
          # 1. 运行工作流到 gate
          # 2. reject with spawn
          # 3. 验证新工作流创建
          # 4. 验证原工作流 SUPERSEDED

      async def test_full_flag_continue_flow(self):
          """测试完整的标记继续流程"""
          # 1. 运行工作流到 gate
          # 2. flag with issues
          # 3. 验证工作流继续运行
          # 4. 验证问题被记录
  ```

- [ ] **2.2.2 工作流场景测试**
  ```python
  class TestWorkflowScenarios:
      async def test_linear_workflow_rollback(self):
          """测试线性工作流回退"""

      async def test_parallel_workflow_rollback(self):
          """测试并行工作流回退"""

      async def test_nested_workflow_rollback(self):
          """测试嵌套工作流回退"""

      async def test_multi_gate_workflow(self):
          """测试多门禁工作流"""
  ```

**交付物**:
- 集成测试用例文档
- 测试场景描述
- 测试数据准备方案

### 2.3 并发测试设计

**任务清单**:

- [ ] **2.3.1 并发决策测试**
  ```python
  class TestConcurrentDecisions:
      async def test_concurrent_reject_and_approve(self):
          """测试并发 reject 和 approve"""
          # 两个用户同时对同一 gate 做决策
          # 期望: 只有一个成功，另一个失败

      async def test_concurrent_rewind_and_execute(self):
          """测试并发 rewind 和执行"""
          # 一个用户在 rewind，另一个步骤在执行
          # 期望: rewind 优先，执行被中断

      async def test_concurrent_multi_gate_decision(self):
          """测试并发多 gate 决策"""
          # 多个用户同时决策不同 gate
          # 期望: 互不影响

      async def test_race_condition_on_rollback(self):
          """测试 rollback 的竞态条件"""
          # 模拟两个用户同时触发 rollback
          # 期望: 第二个等待或失败
  ```

- [ ] **2.3.2 事务隔离测试**
  ```python
  class TestTransactionIsolation:
      async def test_rewind_isolation_level(self):
          """测试 rewind 的事务隔离级别"""
          # 验证脏读、不可重复读、幻读保护

      async def test_deadlock_scenario(self):
          """测试死锁场景"""
          # 模拟可能的死锁情况
          # 验证死锁检测和恢复

      async def test_lock_timeout(self):
          """测试锁超时"""
          # 验证锁超时机制
  ```

**交付物**:
- 并发测试用例文档
- 并发测试脚本
- 性能基准测试

### 2.4 数据一致性测试

**任务清单**:

- [ ] **2.4.1 清理完整性测试**
  ```python
  class TestCleanupIntegrity:
      async def test_no_orphan_task_executions(self):
          """测试无孤儿 task_executions"""

      async def test_no_orphan_gate_approvals(self):
          """测试无孤儿 gate_approvals"""

      async def test_no_orphan_step_outputs(self):
          """测试无孤儿 step_outputs"""

      async def test_consistent_step_attempts(self):
          """测试 step_attempts 一致性"""

      async def test_foreign_key_integrity(self):
          """测试外键完整性"""
  ```

- [ ] **2.4.2 状态一致性测试**
  ```python
  class TestStateConsistency:
      async def test_workflow_status_consistent(self):
          """测试 workflow.status 一致性"""

      async def test_step_status_consistent(self):
          """测试 step.status 一致性"""

      async def test_gate_status_consistent(self):
          """测试 gate.status 一致性"""

      async def test_current_step_pointer_consistent(self):
          """测试 current_step 指针一致性"""
  ```

- [ ] **2.4.3 迁移数据验证**
  ```python
  class TestMigrationDataValidation:
      async def test_existing_gates migrated(self):
          """测试现有 gate 迁移"""

      async def test_existing_workflows_migrated(self):
          """测试现有 workflow 迁移"""

      async def test_no_data_loss_during_migration(self):
          """测试迁移无数据丢失"""

      async def test_rollback_no_side_effects(self):
          """测试回滚无副作用"""
  ```

**交付物**:
- 数据一致性测试用例文档
- 数据验证脚本
- 迁移验证工具

### 2.5 测试环境准备

**任务清单**:

- [ ] **2.5.1 测试数据库**
  - 准备测试数据库实例
  - 准备测试数据集
  - 配置数据库监控

- [ ] **2.5.2 测试工作流**
  - 准备各种复杂度的工作流模板
  - 准备边界情况测试数据
  - 准备性能测试数据

- [ ] **2.5.3 测试工具**
  - 配置并发测试工具
  - 配置性能监控工具
  - 配置数据一致性检查工具

**交付物**:
- 测试环境配置文档
- 测试数据准备脚本
- 测试工具使用指南

### 2.6 测试用例评审

**评审会议安排**:

**会议 1: 单元测试评审**
- **时间**: Day 1 下午
- **参与者**: 开发、QA
- **议题**: 单元测试覆盖度

**会议 2: 集成测试评审**
- **时间**: Day 2 上午
- **参与者**: 开发、QA、架构师
- **议题**: 测试场景完整性

**会议 3: 并发测试评审**
- **时间**: Day 2 下午
- **参与者**: 开发、QA、DBA
- **议题**: 并发安全性

**交付物**:
- 测试用例评审报告
- 测试覆盖度分析
- 测试优先级排序

---

## 阶段 3: 数据模型升级实施

**目标**: 完成数据库迁移和模型代码更新

**时间**: 2-3 天

**负责人**: 后端开发 + DBA

### 3.1 数据库迁移脚本

**任务清单**:

- [ ] **3.1.1 迁移脚本开发**
  ```sql
  -- 文件: migrations/002_gate_actions_v1.1.sql

  -- === 步骤 1: 添加新列 ===
  ALTER TABLE gate_approvals ADD COLUMN default_reject_action TEXT;
  ALTER TABLE gate_approvals ADD COLUMN default_reject_target TEXT;
  ALTER TABLE gate_approvals ADD COLUMN default_revise_action TEXT;
  ALTER TABLE gate_approvals ADD COLUMN default_revise_target TEXT;
  ALTER TABLE gate_approvals ADD COLUMN decision_action TEXT;
  ALTER TABLE gate_approvals ADD COLUMN target_step TEXT;
  ALTER TABLE gate_approvals ADD COLUMN structured_feedback TEXT;
  ALTER TABLE gate_approvals ADD COLUMN issues TEXT;
  ALTER TABLE gate_approvals ADD COLUMN invalidated_at TIMESTAMP;

  ALTER TABLE task_executions ADD COLUMN invalidated_at TIMESTAMP;

  -- === 步骤 2: 添加索引 ===
  CREATE INDEX idx_gate_approvals_default_action
    ON gate_approvals(default_reject_action)
    WHERE default_reject_action IS NOT NULL;

  CREATE INDEX idx_gate_approvals_decision_action
    ON gate_approvals(decision_action)
    WHERE decision_action IS NOT NULL;

  CREATE INDEX idx_task_executions_invalidated
    ON task_executions(workflow_id, status)
    WHERE status = 'invalidated';

  CREATE INDEX idx_gate_approvals_invalidated
    ON gate_approvals(workflow_id, status)
    WHERE status = 'invalidated';

  -- === 步骤 3: 数据迁移（现有 gate） ===
  -- 为现有 gate 添加默认值（可选）
  -- UPDATE gate_approvals SET default_reject_action = 'rollback' WHERE status = 'PENDING';

  -- === 步骤 4: 添加约束 ===
  -- 验证决策 action 合法性（通过触发器）
  ```

- [ ] **3.1.2 回滚脚本开发**
  ```sql
  -- 文件: migrations/002_gate_actions_v1.1_rollback.sql

  -- 删除索引
  DROP INDEX IF EXISTS idx_gate_approvals_invalidated;
  DROP INDEX IF EXISTS idx_task_executions_invalidated;
  DROP INDEX IF EXISTS idx_gate_approvals_decision_action;
  DROP INDEX IF EXISTS idx_gate_approvals_default_action;

  -- 删除列（反向顺序）
  ALTER TABLE task_executions DROP COLUMN IF EXISTS invalidated_at;

  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS issues;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS structured_feedback;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS invalidated_at;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS target_step;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS decision_action;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS default_revise_target;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS default_revise_action;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS default_reject_target;
  ALTER TABLE gate_approvals DROP COLUMN IF EXISTS default_reject_action;
  ```

- [ ] **3.1.3 数据验证脚本**
  ```python
  # 文件: migrations/validate_002.py

  async def validate_migration(db):
      """验证迁移结果"""

      # 1. 检查列是否存在
      columns = await db.get_table_columns("gate_approvals")
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
      ]
      for col in required_columns:
          assert col in columns, f"Column {col} missing"

      # 2. 检查索引是否存在
      indexes = await db.get_indexes("gate_approvals")
      required_indexes = [
          "idx_gate_approvals_default_action",
          "idx_gate_approvals_decision_action",
          "idx_gate_approvals_invalidated",
      ]
      for idx in required_indexes:
          assert idx in indexes, f"Index {idx} missing"

      # 3. 检查现有数据完整性
      gates = await db.query("SELECT * FROM gate_approvals")
      for gate in gates:
          # 验证必要字段
          assert gate["workflow_id"] is not None
          assert gate["gate_id"] is not None

      # 4. 检查外键完整性
      await validate_foreign_keys(db)

      print("✅ Migration validation passed")
  ```

**交付物**:
- 迁移脚本（forward + rollback）
- 数据验证脚本
- 迁移执行文档

### 3.2 模型代码更新

**任务清单**:

- [ ] **3.2.1 更新数据模型**
  ```python
  # 文件: src/lee/orchestrator/storage/models.py

  class GateStatus(Enum):
      """Gate 状态"""
      PENDING = "pending"
      APPROVED = "approved"
      REJECTED = "rejected"
      REVISED = "revised"
      FLAGGED = "flagged"  # 新增

  class WorkflowStatus(Enum):
      """Workflow 状态"""
      # ... 现有状态
      SUPERSEDED = "superseded"  # 新增

  @dataclass
  class GateApproval:
      """门禁审批"""
      workflow_id: str
      gate_id: str
      step_id: str
      status: GateStatus
      approval_criteria: List[Dict] = field(default_factory=list)
      reviewers: List[Dict] = field(default_factory=list)
      # 默认 action（新增）
      default_reject_action: Optional[str] = None
      default_reject_target: Optional[str] = None
      default_revise_action: Optional[str] = None
      default_revise_target: Optional[str] = None
      # 实际决策（新增）
      decision_action: Optional[str] = None
      target_step: Optional[str] = None
      # 反馈（新增）
      structured_feedback: Optional[Dict] = None
      issues: Optional[List[str]] = None
      # 作废标记（新增）
      invalidated_at: Optional[str] = None
      approver: Optional[str] = None
      comments: Optional[str] = None
      created_at: Optional[str] = None
      decided_at: Optional[str] = None
  ```

- [ ] **3.2.2 更新存储层接口**
  ```python
  # 文件: src/lee/orchestrator/storage/sqlite_store.py

  class SQLiteStore:
      # 新增方法
      async def update_gate_approval_with_action(
          self,
          workflow_id: str,
          gate_id: str,
          status: GateStatus,
          approver: str,
          comments: str,
          action: Optional[str] = None,
          target_step: Optional[str] = None,
          structured_feedback: Optional[Dict] = None,
          issues: Optional[List[str]] = None,
      ) -> GateApproval:
          """更新门禁审批（带 action）"""
          ...

      async def invalidate_task_executions_after(
          self,
          workflow_id: str,
          step_ids: List[str],
      ) -> None:
          """作废任务执行记录"""
          ...

      async def invalidate_gate_approvals_after(
          self,
          workflow_id: str,
          step_ids: List[str],
      ) -> None:
          """作废门禁审批记录"""
          ...

      async def update_workflow_current_step(
          self,
          workflow_id: str,
          step_id: str,
      ) -> None:
          """更新当前步骤指针"""
          ...
  ```

- [ ] **3.2.3 添加事务支持**
  ```python
  # 文件: src/lee/orchestrator/storage/sqlite_store.py

  class SQLiteStore:
      @asynccontextmanager
      async def transaction(self):
          """事务上下文管理器"""
          cursor = self.conn.cursor()
          try:
              await self.execute("BEGIN")
              yield cursor
              await self.execute("COMMIT")
          except Exception as e:
              await self.execute("ROLLBACK")
              raise
  ```

**交付物**:
- 更新的模型代码
- 更新的存储层代码
- 单元测试（模型层）

### 3.3 迁移测试

**任务清单**:

- [ ] **3.3.1 迁移脚本测试**
  ```python
  # 文件: tests/migrations/test_002_gate_actions.py

  class TestMigration002:
      async def test_forward_migration(self):
          """测试前向迁移"""
          # 1. 准备旧版本数据库
          # 2. 执行迁移脚本
          # 3. 验证新列和索引存在
          # 4. 验证数据完整性

      async def test_rollback_migration(self):
          """测试回滚"""
          # 1. 准备已迁移的数据库
          # 2. 执行回滚脚本
          # 3. 验证旧结构恢复

      async def test_migration_with_existing_data(self):
          """测试有现有数据的迁移"""
          # 1. 准备包含现有 gate 和 workflow 的数据库
          # 2. 执行迁移
          # 3. 验证现有数据未损坏

      async def test_migration_idempotency(self):
          """测试迁移幂等性"""
          # 多次执行迁移应该安全
  ```

- [ ] **3.3.2 数据完整性测试**
  ```python
  class TestMigrationDataIntegrity:
      async def test_no_data_loss(self):
          """测试无数据丢失"""

      async def test_foreign_key_integrity(self):
          """测试外键完整性"""

      async def test_constraints_preserved(self):
          """测试约束保留"""
  ```

**交付物**:
- 迁移测试报告
- 数据完整性验证报告

### 3.4 文档更新

**任务清单**:

- [ ] **3.4.1 数据库文档更新**
  - 更新 ER 图
  - 更新表结构文档
  - 更新索引文档

- [ ] **3.4.2 API 文档更新**
  - 更新 `GateApproval` 文档
  - 更新 `GateStatus` 文档
  - 更新 `WorkflowStatus` 文档

- [ ] **3.4.3 迁移指南更新**
  - 迁移步骤说明
  - 回滚步骤说明
  - 常见问题解答

**交付物**:
- 更新的数据库文档
- 更新的 API 文档
- 迁移执行指南

### 3.5 代码审查

**审查清单**:

- [ ] **3.5.1 迁移脚本审查**
  - DBA 审查 SQL 语句
  - 性能影响评估
  - 安全性审查

- [ ] **3.5.2 模型代码审查**
  - 代码风格审查
  - 类型检查
  - 文档完整性

- [ ] **3.5.3 测试代码审查**
  - 测试覆盖度审查
  - 测试质量审查
  - 边界情况检查

**交付物**:
- 代码审查报告
- 修改建议清单
- 批准记录

---

## 关键决策记录

### 决策 1: Template Step Order 计算

**日期**: 2026-02-19

**背景**: rollback 需要知道哪些步骤在目标步骤之后

**选项**:
- A. 基于 `completed_steps` 列表
- B. 基于 template 定义的顺序
- C. 基于 step 依赖关系图

**决策**: **选项 B** - 基于 template 定义的顺序

**理由**:
- gate 被卡住时目标 step 往往不在 `completed_steps`
- template 顺序是稳定的、预定义的
- 可以处理线性工作流（最常见场景）

**后续考虑**:
- 未来需要支持 DAG 时，切换到选项 C

---

### 决策 2: FLAGGED 状态语义

**日期**: 2026-02-19

**背景**: 需要一种方式记录问题但不阻断工作流

**选项**:
- A. `APPROVED_WITH_NOTES` 状态
- B. `WAIVED` 状态
- C. `FLAGGED` 状态（新增）

**决策**: **选项 C** - `FLAGGED` 状态

**理由**:
- 语义清晰："标记问题"
- 不与 APPROVED 混淆
- 可以独立追踪和管理

---

### 决策 3: 默认 Action 存储

**日期**: 2026-02-19

**背景**: reject 时需要知道默认 action

**选项**:
- A. reject 时动态读取 template
- B. 创建 gate 时写入 DB
- C. 运行时缓存 template 配置

**决策**: **选项 B** - 创建 gate 时写入 DB

**理由**:
- 避免 template 变更导致的历史解释不一致
- 性能更好（无需解析 template）
- 更容易审计和调试

---

### 决策 4: 事务隔离级别

**日期**: 2026-02-19

**背景**: `rewind_to` 需要事务保护

**选项**:
- A. READ COMMITTED
- B. REPEATABLE READ
- C. SERIALIZABLE

**决策**: **选项 B** - REPEATABLE READ

**理由**:
- 平衡性能和一致性
- 防止不可重复读
- 大多数数据库支持良好

---

## 风险监控

### 风险登记表

| ID | 风险 | 概率 | 影响 | 缓解措施 | 负责人 | 状态 |
|----|------|------|------|---------|--------|------|
| R1 | 迁移脚本执行失败 | 中 | 高 | 完整测试 + 回滚准备 | DBA | 🟡 |
| R2 | 性能退化 | 中 | 中 | 索引优化 + 批量操作 | 开发 | 🟡 |
| R3 | 并发决策冲突 | 高 | 高 | 乐观锁 + 重试机制 | 开发 | 🟡 |
| R4 | 数据不一致 | 低 | 高 | 事务 + 验证脚本 | DBA | 🟡 |
| R5 | 向后兼容性破坏 | 低 | 高 | 充分测试 + 文档 | 开发 | 🟡 |
| R6 | 死锁 | 中 | 中 | 锁超时 + 重试 | DBA | 🟡 |

### 风险缓解计划

**R1: 迁移脚本执行失败**
- 缓解措施:
  - 在测试环境充分测试
  - 准备完整回滚脚本
  - 执行前备份数据库
- 应急预案:
  - 立即执行回滚
  - 恢复数据库备份

**R2: 性能退化**
- 缓解措施:
  - 添加必要索引
  - 使用批量操作
  - 性能基准测试
- 监控指标:
  - `rewind_to` 执行时间
  - 数据库查询时间
  - 工作流总执行时间

**R3: 并发决策冲突**
- 缓解措施:
  - 使用乐观锁（版本号）
  - 添加重试机制
  - 并发测试覆盖
- 应急预案:
  - 第二个决策排队等待
  - 返回明确错误信息

**R4: 数据不一致**
- 缓解措施:
  - 使用事务保护
  - 数据验证脚本
  - 外键约束
- 监控指标:
  - 定期运行一致性检查
  - 监控数据库约束违反

**R5: 向后兼容性破坏**
- 缓解措施:
  - 保留旧 API
  - 渐进式迁移
  - 充分测试
- 验证方法:
  - 测试旧版本 workflow
  - 测试旧版本 CLI 命令

**R6: 死锁**
- 缓解措施:
  - 设置锁超时
  - 按固定顺序获取锁
  - 死锁检测和重试
- 监控指标:
  - 死锁发生次数
  - 锁等待时间

---

## 进度跟踪

### 里程碑

| 里程碑 | 目标日期 | 状态 | 完成日期 |
|--------|---------|------|---------|
| M1: 技术规格评审完成 | Day 2 | ⏳ | - |
| M2: 测试用例编写完成 | Day 4 | ⏳ | - |
| M3: 数据模型升级完成 | Day 7 | ⏳ | - |

### 每日站会

**时间**: 每天上午 10:00

**参与者**: 全体实施团队

**议题**:
- 昨日完成情况
- 今日计划
- 阻碍问题

---

## 附录

### A. 相关文档

- [Gate 改进方案 v1.1](./gate-improvement-plan-v1.1.md)
- [架构评审报告](./gate-improvement-review.md)
- [Human Gate 实现说明](./HUMAN_GATE_IMPLEMENTATION.md)

### B. 联系人

| 角色 | 姓名 | 联系方式 |
|------|------|---------|
| 架构师 | - | - |
| 技术负责人 | - | - |
| DBA | - | - |
| QA 负责人 | - | - |

### C. 工具和资源

- 项目管理: [工具链接]
- 文档协作: [工具链接]
- 代码仓库: [工具链接]
- 测试环境: [环境信息]
