---
title: LEE Gate 改进方案 v1.1
author: LEE Team
date: 2026-02-19
version: 1.1
last_updated: 2026-02-19
---

# LEE Gate 改进方案 v1.1

> 作者: LEE Team
> 日期: 2026-02-19
> 版本: 1.1 (修订版)
> 状态: 待评审
>
> ## 变更记录
> - v1.1 (2026-02-19): 根据 P0/P1 评审意见修订
> - v1.0 (2026-02-19): 初始版本

---

## 目录

1. [修订说明](#修订说明)
2. [P0 修复汇总](#p0-修复汇总)
3. [核心改进](#核心改进)
4. [方案 A: 最小改动版本](#方案-a-最小改动版本-v11)
5. [方案 B: 完整版本](#方案-b-完整版本)
6. [迁移路径](#迁移路径)
7. [风险评估](#风险评估)

---

## 修订说明

本版本基于 v1.0 的架构评审反馈，重点修复以下 P0 级别问题：

### P0-1: rollback 语义修复
**问题**: 依赖 `completed_steps.index()` 无法找到未完成的目标步骤
**解决**: 基于 template step order/DAG 计算受影响的步骤范围

### P0-2: 数据一致性清理
**问题**: 只清理 `step_outputs`，未清理 `task_executions/gate_approvals/step_attempts`
**解决**: 事务化清理所有关联数据

### P0-3: PATCH_ONLY 语义明确
**问题**: gate REJECTED 但 workflow 继续运行，语义矛盾
**解决**: 引入 `FLAGGED` 状态，移除 PATCH_ONLY

### P0-4: 默认 action 存储
**问题**: reject 时回读 template，配置读取脆弱
**解决**: 创建 gate 时写入默认 action 到 DB

### P1-1: revise 语义独立
**问题**: revise 复用 reject 命令，语义混乱
**解决**: 独立 `revise` 命令和状态

### P1-2: rewind_to 原语
**问题**: rollback 后 enqueue 行为不明确
**解决**: 提供 `rewind_to(step_id, mode)` 原语

### P1-3: spawn 增强
**问题**: spawn 只能复制同 template
**解决**: 支持指定新 template 和 inputs_delta

---

## P0 修复汇总

### 修复 1: rollback 基于 template order

```python
async def invalidate_steps_after(
    self,
    workflow_id: str,
    step_id: str,
) -> List[str]:
    """
    作废指定步骤之后的所有步骤

    基于 template step order 计算，而非依赖 completed_steps
    """
    instance = await self.store.get_workflow(workflow_id)
    template = self.template_manager.get_template(instance.template_id)

    # 1. 获取 template 中所有 step 的顺序
    step_order = template.get_step_order()  # -> ["s1", "s2", "s3", ...]

    # 2. 找到目标步骤的位置
    try:
        target_index = step_order.index(step_id)
    except ValueError:
        raise StepNotFoundError(f"Step {step_id} not in template")

    # 3. 计算需要作废的步骤（位置 > target_index 的所有步骤）
    steps_to_invalidate = step_order[target_index + 1:]

    # 4. 事务化清理所有关联数据
    async with self.store.transaction():
        # 清理 step_outputs
        await self._clear_step_outputs(workflow_id, steps_to_invalidate)

        # 清理 task_executions
        await self._invalidate_task_executions(workflow_id, steps_to_invalidate)

        # 清理 gate_approvals
        await self._invalidate_gate_approvals(workflow_id, steps_to_invalidate)

        # 清理 step_attempts
        await self._clear_step_attempts(workflow_id, steps_to_invalidate)

        # 更新 completed_steps
        await self._update_completed_steps(workflow_id, step_id, step_order)

    return steps_to_invalidate
```

### 修复 2: 事务化完整清理

```python
async def _invalidate_task_executions(
    self,
    workflow_id: str,
    step_ids: List[str],
) -> None:
    """作废任务执行记录"""
    await self.store.execute("""
        UPDATE task_executions
        SET status = 'invalidated',
            invalidated_at = CURRENT_TIMESTAMP
        WHERE workflow_id = ?
            AND step_id IN ({})
    """.format(','.join(['?' for _ in step_ids])),
    [workflow_id] + step_ids
    )

async def _invalidate_gate_approvals(
    self,
    workflow_id: str,
    step_ids: List[str],
) -> None:
    """作废门禁审批记录"""
    await self.store.execute("""
        UPDATE gate_approvals
        SET status = 'invalidated',
            invalidated_at = CURRENT_TIMESTAMP
        WHERE workflow_id = ?
            AND step_id IN ({})
    """.format(','.join(['?' for _ in step_ids])),
    [workflow_id] + step_ids
    )

async def _clear_step_attempts(
    self,
    workflow_id: str,
    step_ids: List[str],
) -> None:
    """清理步骤尝试次数"""
    instance = await self.store.get_workflow(workflow_id)
    if not instance.data:
        return

    step_attempts = instance.data.get("step_attempts", {})
    for step_id in step_ids:
        step_attempts.pop(step_id, None)

    await self.store.update_workflow_data(workflow_id, {
        "step_attempts": step_attempts,
    })
```

### 修复 3: FLAGGED 状态替代 PATCH_ONLY

```python
class GateStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
    FLAGGED = "flagged"      # 新增: 标记问题但不阻断
```

**CLI 命令**:
```bash
# 标记问题（不阻断）
lee gates flag <workflow_id> <gate_id> \
  --approver zengle \
  --issues "代码风格需要改进" \
  --workflow-continues  # 工作流继续运行
```

### 修复 4: 创建 gate 时写入默认 action

```python
class HumanGateRunner(StepRunnerBase):
    async def execute(self, workflow_id: str, step, ctx: RunnerContext) -> StepResult:
        # 提取完整 gate 配置
        gate_config = step.config.get("gate", {})

        # 解析默认 action
        default_reject_action = self._parse_default_action(
            gate_config.get("on_reject", {})
        )
        default_revise_action = self._parse_default_action(
            gate_config.get("on_revise", {})
        )

        # 创建门禁审批记录（包含默认 action）
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=step.gate_id or f"gate_{step.id}",
            step_id=step.id,
            status=GateStatus.PENDING,
            # 审批配置
            approval_criteria=gate_config.get("approval_criteria", []),
            reviewers=gate_config.get("reviewers", []),
            # 默认 action（写入 DB）
            default_reject_action=default_reject_action.get("action"),
            default_reject_target=default_reject_action.get("target_step"),
            default_revise_action=default_revise_action.get("action"),
            default_revise_target=default_revise_action.get("target_step"),
        )
        await ctx.store.create_gate_approval(gate_approval)

    def _parse_default_action(self, action_config: Dict) -> Dict:
        """解析默认 action 配置"""
        action = action_config.get("action")
        target = action_config.get("target_step")

        # 验证 action 合法性
        valid_actions = ["rollback", "retry", "spawn", "flag"]
        if action and action not in valid_actions:
            raise ValueError(f"Invalid action: {action}")

        return {"action": action, "target_step": target}
```

**reject 时不再读 template**:
```python
async def reject_gate(
    self,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str,
    action: Optional[GateDecisionAction] = None,
    target_step: Optional[str] = None,
) -> StepResult:
    # 从 DB 读取默认 action（不再读 template）
    gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

    if action is None:
        # 使用存储的默认 action
        default_action = gate_approval.default_reject_action
        if default_action:
            action = GateDecisionAction.from_string(default_action)
            target_step = target_step or gate_approval.default_reject_target

    if action is None:
        # 仍然没有 action，才报错
        raise InvalidDecisionError(
            f"Reject must specify action. "
            f"No default action configured for gate {gate_id}"
        )

    # ... 执行 action
```

---

## 核心改进

### 1. 状态扩展

```python
class GateStatus(Enum):
    """Gate 状态"""
    PENDING = "pending"           # 等待审批
    APPROVED = "approved"         # 已批准
    REJECTED = "rejected"         # 已拒绝（方向不对，需要 rollback/spawn）
    REVISED = "revised"           # 要求修改（方向对但未达标，需要 retry）
    FLAGGED = "flagged"           # 标记问题但不阻断（新增）

class WorkflowStatus(Enum):
    """Workflow 状态"""
    # ... 现有状态
    SUPERSEDED = "superseded"     # 被新工作流替代（新增）
```

### 2. 决策动作枚举

```python
class GateDecisionAction(Enum):
    """Gate 决策后的执行动作"""
    ROLLBACK_TO_STEP = "rollback"       # 回退到某 step
    REVISE_STEP_AND_RETRY = "retry"     # 修订后重试
    SPAWN_CHANGE_REQUEST = "spawn"      # 派生新 workflow
    FLAGGED_ONLY = "flag"               # 仅标记问题（新增）
```

### 3. 数据模型扩展

**gate_approvals 表新增列**:

```sql
-- 默认 action（创建 gate 时写入）
ALTER TABLE gate_approvals ADD COLUMN default_reject_action TEXT;
ALTER TABLE gate_approvals ADD COLUMN default_reject_target TEXT;
ALTER TABLE gate_approvals ADD COLUMN default_revise_action TEXT;
ALTER TABLE gate_approvals ADD COLUMN default_revise_target TEXT;

-- 实际决策 action
ALTER TABLE gate_approvals ADD COLUMN decision_action TEXT;
ALTER TABLE gate_approvals ADD COLUMN target_step TEXT;

-- 结构化反馈
ALTER TABLE gate_approvals ADD COLUMN structured_feedback TEXT;
ALTER TABLE gate_approvals ADD COLUMN issues TEXT;              -- JSON array
ALTER TABLE gate_approvals ADD COLUMN expected_changes TEXT;    -- JSON array

-- 作废标记
ALTER TABLE gate_approvals ADD COLUMN invalidated_at TIMESTAMP;
```

**task_executions 表新增列**:

```sql
ALTER TABLE task_executions ADD COLUMN invalidated_at TIMESTAMP;
```

---

## 方案 A: 最小改动版本 (v1.1)

> 目标: 修复 P0 问题，保证数据一致性

### A1. 核心原语: rewind_to

**统一回退/重试操作**:

```python
class WorkflowStateMachine:
    async def rewind_to(
        self,
        workflow_id: str,
        target_step_id: str,
        mode: str,  # "rollback" | "retry"
        reason: str,
    ) -> StepResult:
        """
        回退/重试到指定步骤

        这是 rollback 和 retry 的统一原语，保证:
        1. 基于 template order 计算受影响步骤
        2. 事务化清理所有关联数据
        3. 明确 enqueue 行为
        """
        # 1. 基于模板计算受影响的步骤
        template = self.template_manager.get_template(...)
        affected_steps = template.get_steps_after(target_step_id)

        # 2. 事务化清理
        async with self.store.transaction():
            # 作后续步骤
            for step_id in affected_steps:
                await self._invalidate_step(workflow_id, step_id)

            if mode == "retry":
                # 重试模式: 增加 attempt 次数
                await self.increment_step_attempt(workflow_id, target_step_id)
                # 重置步骤状态
                await self.reset_step_status(workflow_id, target_step_id)

            # 设置当前步骤
            await self.set_current_step(workflow_id, target_step_id)

            # 恢复工作流运行
            await self.store.update_workflow_status(
                workflow_id, WorkflowStatus.RUNNING
            )

        # 3. 明确 enqueue
        await self._enqueue_step(workflow_id, target_step_id)

        return StepResult(
            status=mode,
            step_id=target_step_id,
            workflow_id=workflow_id,
            message=f"Rewind to {target_step_id} ({mode}): {reason}",
        )

    async def _invalidate_step(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """作废单个步骤的所有关联数据"""
        # 1. 作废 task_executions
        await self.store.execute("""
            UPDATE task_executions
            SET status = 'invalidated', invalidated_at = CURRENT_TIMESTAMP
            WHERE workflow_id = ? AND step_id = ?
        """, [workflow_id, step_id])

        # 2. 作废 gate_approvals
        await self.store.execute("""
            UPDATE gate_approvals
            SET status = 'invalidated', invalidated_at = CURRENT_TIMESTAMP
            WHERE workflow_id = ? AND step_id = ?
        """, [workflow_id, step_id])

        # 3. 清理 step_outputs
        instance = await self.store.get_workflow(workflow_id)
        if instance.data and "step_outputs" in instance.data:
            instance.data["step_outputs"].pop(step_id, None)
            await self.store.update_workflow_data(workflow_id, instance.data)
```

### A2. reject_gate 实现（使用 rewind_to）

```python
async def reject_gate(
    self,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str,
    action: Optional[GateDecisionAction] = None,
    target_step: Optional[str] = None,
) -> StepResult:
    """
    拒绝人工门禁

    Reject = 方向不对，需要 rollback 或 spawn
    """
    # 1. 获取 gate 配置（从 DB，不读 template）
    gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

    # 2. 确定执行 action
    if action is None:
        # 使用默认 action
        default_action = gate_approval.default_reject_action
        if default_action:
            action = GateDecisionAction.from_string(default_action)
            target_step = target_step or gate_approval.default_reject_target

    if action is None:
        raise InvalidDecisionError(
            f"Reject must specify action. "
            f"Configure on_reject.action or use --action parameter."
        )

    # 3. 更新 gate 状态
    await self.store.update_gate_approval(
        workflow_id, gate_id, GateStatus.REJECTED, rejecter, reason,
        action=action.value, target_step=target_step
    )

    # 4. 记录事件
    self.event_log.log_gate_rejected(
        gate_id=gate_id,
        step_id=gate_approval.step_id,
        approver=rejecter,
        reason=reason,
        action=action.value,
    )

    # 5. 执行动作
    if action == GateDecisionAction.ROLLBACK_TO_STEP:
        # 使用统一原语
        return await self.state_machine.rewind_to(
            workflow_id, target_step, mode="rollback", reason=reason
        )

    elif action == GateDecisionAction.REVISE_STEP_AND_RETRY:
        return await self.state_machine.rewind_to(
            workflow_id, target_step or gate_approval.step_id,
            mode="retry", reason=reason
        )

    elif action == GateDecisionAction.SPAWN_CHANGE_REQUEST:
        return await self._execute_spawn_workflow(
            workflow_id, gate_id, rejecter, reason
        )

    else:
        # 不应该到这里
        raise InvalidDecisionError(f"Invalid action for reject: {action}")
```

### A3. revise_gate 实现（独立命令）

```python
async def revise_gate(
    self,
    workflow_id: str,
    gate_id: str,
    reviewer: str,
    reason: str,
    target_step: Optional[str] = None,
    structured_feedback: Optional[Dict] = None,
) -> StepResult:
    """
    修订门禁

    Revise = 方向对但未达标，需要修正后重试
    """
    # 1. 获取 gate 配置
    gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

    # 2. 确定重试目标
    if target_step is None:
        # 使用默认 target
        target_step = gate_approval.default_revise_target or gate_approval.step_id

    # 3. 更新 gate 状态为 REVISED
    await self.store.update_gate_approval(
        workflow_id, gate_id, GateStatus.REVISED, reviewer, reason,
        structured_feedback=structured_feedback
    )

    # 4. 记录事件
    self.event_log.log_gate_revised(
        gate_id=gate_id,
        step_id=gate_approval.step_id,
        reviewer=reviewer,
        reason=reason,
    )

    # 5. 使用 rewind_to 执行重试
    return await self.state_machine.rewind_to(
        workflow_id, target_step, mode="retry", reason=reason
    )
```

### A4. flag_gate 实现（新增）

```python
async def flag_gate(
    self,
    workflow_id: str,
    gate_id: str,
    reporter: str,
    issues: List[str],
    continue_workflow: bool = True,
) -> StepResult:
    """
    标记门禁问题

    Flag = 记录问题但不阻断工作流
    """
    # 1. 更新 gate 状态为 FLAGGED
    await self.store.update_gate_approval(
        workflow_id, gate_id, GateStatus.FLAGGED, reporter,
        comment="; ".join(issues),
        issues=json.dumps(issues)
    )

    # 2. 记录事件
    self.event_log.log_gate_flagged(
        gate_id=gate_id,
        step_id=gate_id,
        reporter=reporter,
        issues=issues,
    )

    # 3. 根据配置决定工作流状态
    if continue_workflow:
        # 恢复工作流运行
        await self.store.update_workflow_status(
            workflow_id, WorkflowStatus.RUNNING
        )
        # 完成门禁步骤
        await self.state_machine.complete_step(
            workflow_id, gate_id,
            {"flagged": True, "issues": issues}
        )
        return StepResult(
            status="flagged",
            step_id=gate_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} flagged with {len(issues)} issue(s), workflow continues",
        )
    else:
        # 保持 PAUSED，等待进一步处理
        return StepResult(
            status="paused",
            step_id=gate_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} flagged, workflow paused for review",
        )
```

### A5. spawn 增强

```python
async def _execute_spawn_workflow(
    self,
    workflow_id: str,
    gate_id: str,
    requester: str,
    reason: str,
    new_template_id: Optional[str] = None,
    workflow_ref: Optional[str] = None,
    inputs_delta: Optional[Dict] = None,
) -> StepResult:
    """
    派生新工作流

    支持指定新 template 和输入变更
    """
    # 1. 获取当前工作流实例
    instance = await self.store.get_workflow(workflow_id)

    # 2. 确定新 workflow 的 template
    template_id = new_template_id or instance.template_id

    # 3. 合并输入变更
    new_inputs = instance.inputs.copy()
    if inputs_delta:
        new_inputs.update(inputs_delta)

    # 4. 创建新工作流实例
    new_workflow_id = await self.orchestrator.create_workflow(
        template_id=template_id,
        project_dir=instance.project_dir,
        parent_workflow_id=workflow_id,
        inputs=new_inputs,
        metadata={
            "spawned_from_gate": gate_id,
            "spawn_reason": reason,
            "original_workflow_id": workflow_id,
        },
    )

    # 5. 将原工作流标记为 SUPERSEDED
    await self.store.update_workflow_status(
        workflow_id, WorkflowStatus.SUPERSEDED
    )

    # 6. 记录事件
    self.event_log.log_workflow_spawned(
        workflow_id=workflow_id,
        new_workflow_id=new_workflow_id,
        gate_id=gate_id,
        reason=reason,
    )

    return StepResult(
        status="spawned",
        step_id=gate_id,
        workflow_id=workflow_id,
        message=f"Spawned new workflow {new_workflow_id} from gate {gate_id}",
        output={"new_workflow_id": new_workflow_id},
    )
```

### A6. CLI 命令

```python
@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="拒绝原因")
@click.option("--action", type=click.Choice([
    "rollback", "spawn"  # reject 不再支持 retry，改用 revise 命令
]), help="执行动作")
@click.option("--target-step", help="目标步骤")
@click.option("--project-dir", default=".", help="项目目录")
def reject(
    workflow_id: str,
    gate_id: str,
    approver: str,
    comments: str,
    action: Optional[str],
    target_step: Optional[str],
    project_dir: str
) -> None:
    """
    拒绝门禁

    Reject = 方向不对，需要 rollback 或 spawn
    """
    # 显示当前默认 action
    gate_info = get_gate_info(workflow_id, gate_id)
    default_action = gate_info.get("default_reject_action")

    if not action:
        if default_action:
            click.echo(f"默认动作: {default_action}")
            if not click.confirm(f"使用默认动作 {default_action}?"):
                action = click.prompt(
                    "请选择动作",
                    type=click.Choice(["rollback", "spawn"])
                )
        else:
            click.echo("未配置默认动作，请手动指定")
            action = click.prompt(
                "请选择动作",
                type=click.Choice(["rollback", "spawn"])
            )

    # 获取目标步骤
    if action == "rollback" and not target_step:
        default_target = gate_info.get("default_reject_target")
        target_step = default_target or click.prompt("请输入目标步骤 ID")

    # 确认
    click.echo(f"\n拒绝门禁: {gate_id}")
    click.echo(f"动作: {action}")
    if target_step:
        click.echo(f"目标: {target_step}")
    click.echo(f"原因: {comments}")

    if not click.confirm("\n确认执行？"):
        return

    # 执行
    try:
        result = pm_workflow(
            "reject_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=gate_id,
            approver=approver,
            reason=comments,
            action=action,
            target_step=target_step,
        )
        click.echo(f"\n✅ 门禁已拒绝，执行: {action}")
    except Exception as e:
        click.echo(f"❌ 失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--reviewer", required=True, help="评审人")
@click.option("--comments", default="", help="修改意见")
@click.option("--target-step", help="重试步骤")
@click.option("--feedback-file", help="结构化反馈文件 (JSON)")
@click.option("--project-dir", default=".", help="项目目录")
def revise(
    workflow_id: str,
    gate_id: str,
    reviewer: str,
    comments: str,
    target_step: Optional[str],
    feedback_file: Optional[str],
    project_dir: str
) -> None:
    """
    修订门禁

    Revise = 方向对但未达标，需要修正后重试
    """
    structured_feedback = None
    if feedback_file:
        with open(feedback_file) as f:
            structured_feedback = json.load(f)

    # 确认
    click.echo(f"\n修订门禁: {gate_id}")
    click.echo(f"评审人: {reviewer}")
    if target_step:
        click.echo(f"重试目标: {target_step}")
    click.echo(f"意见: {comments}")

    if not click.confirm("\n确认执行修订重试？"):
        return

    # 执行
    try:
        result = pm_workflow(
            "revise_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=gate_id,
            reviewer=reviewer,
            reason=comments,
            target_step=target_step,
            structured_feedback=structured_feedback,
        )
        click.echo(f"\n✅ 门禁已修订，将重试")
    except Exception as e:
        click.echo(f"❌ 失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--reporter", required=True, help="报告人")
@click.option("--issues", multiple=True, help="发现的问题")
@click.option("--continue-workflow/--pause-workflow", default=True, help="工作流是否继续")
@click.option("--project-dir", default=".", help="项目目录")
def flag(
    workflow_id: str,
    gate_id: str,
    reporter: str,
    issues: tuple,
    continue_workflow: bool,
    project_dir: str
) -> None:
    """
    标记门禁问题

    Flag = 记录问题但不阻断工作流
    """
    if not issues:
        issues = [click.prompt("请描述发现的问题")]

    # 确认
    click.echo(f"\n标记门禁: {gate_id}")
    click.echo(f"问题数: {len(issues)}")
    for i, issue in enumerate(issues, 1):
        click.echo(f"  {i}. {issue}")
    click.echo(f"工作流: {'继续' if continue_workflow else '暂停'}")

    if not click.confirm("\n确认标记？"):
        return

    # 执行
    try:
        result = pm_workflow(
            "flag_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=gate_id,
            reporter=reporter,
            issues=list(issues),
            continue_workflow=continue_workflow,
        )
        status = "继续运行" if continue_workflow else "暂停等待"
        click.echo(f"\n✅ 门禁已标记，工作流{status}")
    except Exception as e:
        click.echo(f"❌ 失败: {e}")
```

---

## 方案 B: 完整版本

方案 B 在 v1.0 基础上的调整：

1. **移除 PATCH_ONLY**，使用 FLAGGED 替代
2. **结构化反馈**: 与 revise/flag 集成
3. **CLI 交互优化**: 显示默认 action 和 target

---

## 迁移路径 (v1.1)

### 阶段 1: 数据模型升级 (2-3 天)

1. 数据库迁移
   - 添加新列
   - 添加索引
   - 创建回滚脚本

2. 模型更新
   - `GateStatus` 添加 `FLAGGED`
   - `WorkflowStatus` 添加 `SUPERSEDED`
   - `GateApproval` 添加默认 action 字段

3. 验证测试
   - 迁移脚本测试
   - 回滚脚本测试
   - 数据完整性检查

### 阶段 2: 核心逻辑改造 (3-5 天)

1. 实现 `rewind_to` 原语
2. 实现完整清理逻辑
3. 实现 `revise_gate` 独立命令
4. 实现 `flag_gate` 命令
5. 增强 spawn 功能

### 阶段 3: CLI 增强 (2-3 天)

1. 独立 `revise` 命令
2. 新增 `flag` 命令
3. 优化 `reject` 命令（移除 retry）
4. 显示默认 action

### 阶段 4: 测试与验证 (3-4 天)

1. 单元测试
2. 集成测试
3. 并发测试
4. 压力测试
5. 数据一致性测试

### 阶段 5: 文档与培训 (2-3 天)

1. 更新用户文档
2. 更新 API 文档
3. 编写迁移指南
4. 用户培训材料

---

## 风险评估 (v1.1)

### 已缓解的风险

| 风险 | 缓解措施 | 状态 |
|------|---------|------|
| rollback 不生效 | 基于 template order 计算 | ✅ 已修复 |
| 数据不一致 | 事务化完整清理 | ✅ 已修复 |
| PATCH_ONLY 语义混乱 | 引入 FLAGGED 状态 | ✅ 已修复 |
| 配置读取脆弱 | 创建时写入默认 action | ✅ 已修复 |
| enqueue 不明确 | rewind_to 原语 | ✅ 已修复 |

### 剩余风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 并发决策 | 中 | 添加乐观锁/版本号 |
| template 变更 | 低 | snapshot template at gate creation |
| 性能影响 | 中 | 批量操作、索引优化 |

---

## 使用示例 (v1.1)

```bash
# 场景 1: 回退重新规划 (方向不对)
lee gates reject wf_task_123 gate_s5_2_review_commits \
  --approver zengle \
  --action rollback \
  --target-step s5_1_plan_commits \
  --comments "提交计划分组完全错误"

# 场景 2: 修订后重试 (方向对但未达标)
lee gates revise wf_task_123 gate_s4_1_review_code \
  --reviewer zengle \
  --comments "代码风格需要微调" \
  --feedback-file feedback.json

# 场景 3: 标记问题但不阻断
lee gates flag wf_task_123 gate_s3_1_organize_docs \
  --reporter zengle \
  --issues "文档结构可以优化" \
  --continue-workflow

# 场景 4: 派生新工作流（需求变更）
lee gates reject wf_task_123 gate_s2_1_requirement_review \
  --approver zengle \
  --action spawn \
  --comments "需求发生重大变更，需要新工作流"

# 场景 5: spawn 指定新 template
lee gates reject wf_task_123 gate_s2_1_requirement_review \
  --approver zengle \
  --action spawn \
  --new-template change_request_workflow \
  --comments "转为变更请求流程"
```

---

## 评审状态

| 项目 | 状态 |
|------|------|
| P0-1: rollback 语义修复 | ✅ 已修复 |
| P0-2: 数据一致性清理 | ✅ 已修复 |
| P0-3: PATCH_ONLY 语义 | ✅ 已修复 (FLAGGED) |
| P0-4: 默认 action 存储 | ✅ 已修复 |
| P1-1: revise 语义独立 | ✅ 已实现 |
| P1-2: rewind_to 原语 | ✅ 已实现 |
| P1-3: spawn 增强 | ✅ 已实现 |

**结论**: 所有 P0 问题已修复，方案达到实施标准。

---

## 下一步行动

1. ✅ 完成 v1.1 修订
2. ⏳ 技术规格评审
3. ⏳ 开始实施阶段 1
4. ⏳ 编写详细测试用例
