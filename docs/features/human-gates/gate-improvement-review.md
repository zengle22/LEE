---
title: Gate 改进方案 - 架构评审报告
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# Gate 改进方案 - 架构评审报告

> 评审人: Architect (AI Agent)
> 评审日期: 2026-02-19
> 方案版本: 1.0
> 评审结果: ✅ 有条件批准

---

## 执行摘要

本方案正确识别了 LEE Gate 系统的核心问题，并提出了一套切实可行的改进路径。方案 A（最小改动版本）设计合理、风险可控，建议优先实施。方案 B（完整版本）提供了长期演进方向，但需要更详细的实现细节。

**总体评价**: 方案思路清晰、问题分析准确、技术路径可行。建议在实施前关注以下关键点。

---

## 1. 问题分析评审

### ✅ 优点

1. **根因分析准确**: 正确识别了 `reject_gate()` 直接 FAILED 是核心问题
2. **矛盾点清晰**: 数据模型不一致、路由配置未生效等问题分析到位
3. **触发机制合理**: 对"重复执行同一步"的根因推断逻辑成立

### 🔶 建议

补充以下问题分析:

1. **并发安全性**: 当多个用户同时操作同一 gate 时的竞态条件
2. **事务一致性**: rollback 操作的原子性保证
3. **性能影响**: `invalidate_steps_after()` 在大型 workflow 中的性能

---

## 2. 方案 A 评审

### A1. 决策动作枚举 ✅

**评价**: 设计清晰，覆盖主要场景

**建议**:
- 考虑添加 `SKIP_TO_STEP` 动作（跳过某些步骤继续执行）
- 为 `PATCH_ONLY` 添加更详细的语义定义

### A2. 数据模型扩展 ✅

**评价**: 最小化改动，向后兼容

**关键问题**:

1. **缺少 `SUPERSEDED` 状态定义**
   ```python
   # 需要添加到 WorkflowStatus
   class WorkflowStatus(Enum):
       # ... 现有状态
       SUPERSEDED = "superseded"  # 被新工作流替代
   ```

2. **迁移脚本不完整**
   - 缺少回滚脚本
   - 缺少数据完整性检查

3. **索引优化建议**
   ```sql
   CREATE INDEX idx_gate_approvals_action ON gate_approvals(decision_action);
   CREATE INDEX idx_gate_approvals_target ON gate_approvals(target_step);
   ```

### A3. `reject_gate()` 重构 ⚠️

**优点**:
- 动作分发逻辑清晰
- 默认配置回退机制合理

**关键问题**:

1. **`_execute_rollback()` 缺少事务保护**
   ```python
   async def _execute_rollback(...):
       # ❌ 当前实现非原子操作
       await self.state_machine.invalidate_steps_after(...)
       await self.state_machine.set_current_step(...)
       await self.store.update_workflow_status(...)

       # ✅ 建议: 使用事务
       async with self.store.transaction():
           await self.state_machine.invalidate_steps_after(...)
           await self.state_machine.set_current_step(...)
           await self.store.update_workflow_status(...)
   ```

2. **`invalidate_steps_after()` 逻辑问题**
   - 只从 `completed_steps` 中删除，但没有处理 `task_executions` 表
   - 可能导致数据不一致

   **建议补充**:
   ```python
   async def invalidate_steps_after(self, workflow_id: str, step_id: str):
       # 1. 作废内存状态
       completed_steps = [...]
       step_outputs = [...]

       # 2. 作废执行记录
       await self.store.invalidate_task_executions_after(workflow_id, step_id)

       # 3. 清理关联的 gate approvals
       await self.store.invalidate_gates_after(workflow_id, step_id)
   ```

3. **`_execute_spawn_workflow()` 缺少错误处理**
   - 新 workflow 创建失败时的回滚机制
   - parent_workflow_id 关联的完整性

### A4. WorkflowStateMachine 扩展 ⚠️

**问题**:

1. **`invalidate_steps_after()` 假设过于简单**
   ```python
   # 当前: 假设 steps 是线性执行
   completed_steps = ["s1", "s2", "s3", "s4"]

   # 实际: 可能有并行分支
   completed_steps = ["s1", "s2a", "s2b", "s3"]
   ```

   **建议**: 考虑 DAG 结构，需要基于依赖关系作废

2. **缺少 step 状态验证**
   ```python
   async def set_current_step(self, workflow_id: str, step_id: str):
       # ❌ 没有验证 step_id 是否存在
       # ❌ 没有验证依赖是否满足

       # ✅ 建议添加
       if not await self._step_exists(workflow_id, step_id):
           raise StepNotFoundError(step_id)

       if not await self._dependencies_satisfied(workflow_id, step_id):
           raise DependenciesNotSatisfiedError(step_id)
   ```

3. **`increment_step_attempt()` 缺少上限检查**
   ```python
   # ❌ 可能无限重试
   step_attempts[step_id] = current_attempt + 1

   # ✅ 建议
   MAX_ATTEMPTS = 3
   if current_attempt >= MAX_ATTEMPTS:
       raise MaxAttemptsExceededError(step_id, current_attempt)
   ```

### A5. CLI 命令增强 ✅

**评价**: 交互设计友好，用户体验良好

**建议**:
1. 添加 `--dry-run` 选项预览动作效果
2. 添加 `--force` 选项跳过确认（脚本化场景）

---

## 3. 方案 B 评审

### B1. REVISED 状态 ✅

**评价**: 语义清晰，与现有状态一致

**建议**:
- 明确 REVISED 和 REJECTED 的区别
- 定义 REVISED 到其他状态的转换规则

### B2. 路由策略保存 ✅

**评价**: 设计合理，但实现细节不足

**关键问题**:

1. **`GateApproval` 数据类未定义新字段**
   ```python
   # 需要添加
   @dataclass
   class GateApproval:
       # ... 现有字段
       on_reject_action: Optional[str] = None
       on_reject_target: Optional[str] = None
       on_revise_action: Optional[str] = None
       on_revise_target: Optional[str] = None
   ```

2. **数据库迁移未同步更新**
   - 方案 A 的迁移脚本不包含这些字段
   - 需要统一迁移策略

### B3. 结构化反馈 ✅

**评价**: 创新点，能显著改善 AI 理解

**建议**:
1. 考虑添加 `priority` 字段（区分问题严重程度）
2. 添加 `attachment_paths` 支持文件附件
3. 考虑与现有 `checklist` 的整合

---

## 4. 数据一致性评审

### 关键风险点

1. **UNIQUE 约束冲突**
   ```sql
   UNIQUE(workflow_id, gate_id)
   ```
   - spawn 后新 workflow 的 gate_id 可能冲突
   - 建议: 改为 `UNIQUE(workflow_id, gate_id, attempt)`

2. **外键完整性**
   - rollback 后 `task_executions` 记录变成孤儿
   - 建议: 添加 `superseded_by_run_id` 字段追踪

3. **审计链路**
   - 多次 rollback 后历史记录复杂
   - 建议: 添加 `workflow_genealogy` 表记录 lineage

---

## 5. 迁移路径评审

### 时间估算调整

| 阶段 | 原估算 | 调整后 | 理由 |
|------|--------|--------|------|
| 阶段 1 | 1-2 天 | 2-3 天 | 需要更完整的迁移脚本和测试 |
| 阶段 2 | 2-3 天 | 3-5 天 | 需要添加事务处理和错误恢复 |
| 阶段 3 | 1-2 天 | 2-3 天 | CLI 需要更多边界情况处理 |
| 阶段 4 | 2-3 天 | 3-4 天 | 需要并发测试和压力测试 |
| 阶段 5 | 3-5 天 | 5-7 天 | 结构化反馈需要更多设计 |

### 关键里程碑

1. **阶段 1 完成标准**:
   - ✅ 迁移脚本可逆
   - ✅ 所有测试通过
   - ✅ 性能基准测试通过

2. **阶段 2 完成标准**:
   - ✅ 事务完整性测试通过
   - ✅ 并发操作测试通过
   - ✅ 回滚机制测试通过

---

## 6. 风险评估补充

### 新增技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 事务死锁 | 中 | 高 | 添加超时和重试机制 |
| 状态机不一致 | 中 | 高 | 添加状态验证和修复工具 |
| 迁移数据损坏 | 低 | 高 | 完整备份和验证脚本 |
| 性能退化 | 中 | 中 | 性能基准测试和优化 |

### 新增业务风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 用户误操作回退 | 高 | 中 | 添加权限控制和二次确认 |
| 工作流循环 | 低 | 高 | 添加最大回退次数限制 |
| 历史记录混乱 | 中 | 中 | 改进审计日志可视化 |

---

## 7. 架构建议

### 7.1 引入 Gate Decision 模式

```python
@dataclass
class GateDecision:
    """门禁决策（带动作）"""
    option: GateOption  # approve | reject | revise
    action: Optional[GateDecisionAction] = None
    target_step: Optional[str] = None
    comment: str = ""
    structured_feedback: Optional[StructuredFeedback] = None

    def validate(self) -> None:
        """验证决策的合法性"""
        if self.option == GateOption.REJECT and not self.action:
            raise InvalidDecisionError("Reject must specify action")
```

### 7.2 状态机可视化

建议添加状态机图生成工具:

```bash
lee workflow visualize-state-machine wf_task_123 --output state-machine.dot
```

### 7.3 Gate 决策分析

添加决策模式分析:

```bash
lee gates analyze-decisions --workflow-id wf_task_123 --period 7d
```

---

## 8. 测试策略建议

### 单元测试

```python
async def test_rollback_invalidates_dependent_steps():
    """测试回退正确作废依赖步骤"""
    # Arrange
    workflow = await create_test_workflow()
    await complete_steps(workflow, ["s1", "s2", "s3"])

    # Act
    await rollback_to_step(workflow, "s1")

    # Assert
    assert await get_step_status(workflow, "s2") == "invalidated"
    assert await get_step_status(workflow, "s3") == "invalidated"
```

### 集成测试

```python
async def test_reject_with_rollback_action():
    """测试拒绝后执行回退"""
    # Arrange
    gate_id = await create_pending_gate()

    # Act
    result = await reject_gate(
        workflow_id="wf_1",
        gate_id=gate_id,
        action=GateDecisionAction.ROLLBACK_TO_STEP,
        target_step="s1"
    )

    # Assert
    assert result.status == "rollback"
    assert await get_current_step("wf_1") == "s1"
```

### 并发测试

```python
async def test_concurrent_gate_decisions():
    """测试并发决策处理"""
    gate_id = await create_pending_gate()

    # 并发执行两个决策
    results = await asyncio.gather(
        reject_gate(wf_id, gate_id, action="rollback"),
        approve_gate(wf_id, gate_id),
        return_exceptions=True
    )

    # 只有一个应该成功
    successful = [r for r in results if not isinstance(r, Exception)]
    assert len(successful) == 1
```

---

## 9. 实施优先级建议

### P0 - 必须实现

1. ✅ `GateDecisionAction` 枚举
2. ✅ `reject_gate()` 重构（带事务）
3. ✅ `invalidate_steps_after()` 实现（含清理）
4. ✅ CLI `--action` 参数支持

### P1 - 应该实现

1. `SUPERSEDED` 工作流状态
2. 最大尝试次数限制
3. 步骤依赖验证
4. 迁移回滚脚本

### P2 - 可以延后

1. 结构化反馈
2. 状态机可视化
3. 决策分析工具

---

## 10. 批准条件

### 必须修复的问题

1. ⚠️ **添加事务支持**: `rollback` 操作必须原子化
2. ⚠️ **完善数据清理**: `invalidate_steps_after()` 必须清理所有关联表
3. ⚠️ **添加重试上限**: 防止无限重试循环
4. ⚠️ **完善迁移脚本**: 添加回滚和数据验证

### 建议改进的问题

1. 🔶 并发安全性测试
2. 🔶 性能基准测试
3. 🔶 状态机验证工具
4. 🔶 错误恢复机制

---

## 11. 总结与建议

### 方案优势

1. ✅ 问题分析准确，直击核心矛盾
2. ✅ 分阶段实施，风险可控
3. ✅ 向后兼容，平滑升级
4. ✅ 用户体验优化到位

### 需要关注的风险

1. ⚠️ 数据一致性保证不足
2. ⚠️ 并发安全性考虑不充分
3. ⚠️ 错误恢复机制缺失
4. ⚠️ 性能影响评估不足

### 最终建议

**批准方案 A 的实施，但需先完成以下工作**:

1. 补充事务处理和错误恢复机制
2. 完善数据清理逻辑
3. 添加完整的数据迁移和回滚脚本
4. 编写并发测试和性能测试
5. 更新时间估算和里程碑

**方案 B 可作为长期演进方向，建议在方案 A 稳定后再启动**。

---

## 附录: 快速修复清单

### 代码修改优先级

**立即修复** (阻塞发布):

```python
# 1. 添加事务支持
async def _execute_rollback(...):
    async with self.store.transaction():
        # ... 所有操作

# 2. 添加重试上限
MAX_STEP_ATTEMPTS = 3

# 3. 添加 SUPERSEDED 状态
class WorkflowStatus(Enum):
    SUPERSEDED = "superseded"
```

**尽快修复** (影响稳定性):

```python
# 4. 完善数据清理
async def invalidate_steps_after(...):
    # 清理 task_executions
    # 清理 gate_approvals
    # 清理 step_outputs

# 5. 添加验证
async def set_current_step(...):
    # 验证 step 存在
    # 验证依赖满足
```

**后续优化** (改善体验):

```python
# 6. 添加 dry-run
# 7. 添加状态机可视化
# 8. 添加决策分析
```

---

**评审结论**: ✅ 有条件批准 - 修复 P0 问题后可开始实施

**下一步行动**:
1. 修复关键问题
2. 更新设计文档
3. 编写技术规格
4. 启动开发
