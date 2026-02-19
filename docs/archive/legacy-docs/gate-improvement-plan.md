# LEE Gate 改进方案

> 作者: LEE Team
> 日期: 2026-02-19
> 版本: 1.0
> 状态: 待评审

---

## 目录

1. [问题分析](#问题分析)
2. [改进目标](#改进目标)
3. [方案 A: 最小改动版本](#方案-a-最小改动版本)
4. [方案 B: 完整版本](#方案-b-完整版本)
5. [迁移路径](#迁移路径)
6. [风险评估](#风险评估)

---

## 问题分析

### 当前实现的核心矛盾

#### 1. `reject_gate()` 直接终止工作流

**现状**:
```python
async def reject_gate(...):
    # 更新门禁状态
    await self.store.update_gate_approval(...)
    # 直接标记工作流失败
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)
```

**问题**:
- reject 变成"终止"而非"路由"
- 无法实现"回退重跑/重新规划"
- 文档中提到的 `on_reject: rollback/retry_step` 配置无效

#### 2. 数据模型不一致

**现状**:
- 文档和决策文件定义了 `revised` 状态
- CLI 也提到 `revise` 选项
- 但 `GateStatus(Enum)` 只有 `PENDING/APPROVED/REJECTED`

**问题**:
- "需要修改"在系统层没有稳定语义
- 退化成 reject 或 approve+手动补丁

#### 3. HumanGateRunner 不携带路由信息

**现状**:
```python
class HumanGateRunner:
    async def execute(...):
        # 只暂停工作流、创建审批记录
        await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
        await ctx.store.create_gate_approval(gate_approval)
        return StepResult(status="blocked", ...)
```

**问题**:
- gate config 中的 `on_reject/on_revise` 路由意图未生效
- 没有把路由配置编译进 gate 实例

#### 4. "reject 后重复执行同一步"的根因

**可能的触发机制**:
1. gate step 返回 `blocked`
2. 拒绝后 workflow=FAILED
3. 上层为"继续推进"重新触发同一 workflow
4. 由于 `UNIQUE(workflow_id, gate_id)` 约束，复用旧 gate
5. 执行器回到同一 gate step 或同一步重来

---

## 改进目标

### 核心原则

把 gate 从"布尔门"升级为"带动作的决策点":

| 决策 | 当前语义 | 新语义 |
|------|---------|--------|
| **approve** | 当前 gate 完成，workflow 继续 | 保持不变 |
| **reject** | workflow 失败终止 | 执行指定 action (rollback/spawn) |
| **revise** | 无稳定语义 | 执行指定 action (revise+retry) |

### 支持的场景

1. **回退到某 step**: 作废后续步骤，重新执行
2. **修订后重跑**: 同一步打补丁后重试
3. **派生新 workflow**: 需求变更/范围变化
4. **仅打 patch**: 标记问题但不改变执行路径

---

## 方案 A: 最小改动版本

> 目标: 80% 的问题通过最小改动解决

### A1. 增加决策动作枚举

**新增枚举类** (`src/lee/orchestrator/storage/models.py`):

```python
class GateDecisionAction(Enum):
    """Gate 决策后的执行动作"""
    REVISE_STEP_AND_RETRY = "revise_step_and_retry"  # 同一步修订重跑
    ROLLBACK_TO_STEP = "rollback_to_step"            # 回退到某 step
    SPAWN_CHANGE_REQUEST = "spawn_change_request"    # 派生新 workflow
    PATCH_ONLY = "patch_only"                        # 仅打 patch
```

### A2. 扩展数据模型

**gate_approvals 表新增列**:

```sql
ALTER TABLE gate_approvals ADD COLUMN decision_action TEXT;
ALTER TABLE gate_approvals ADD COLUMN target_step TEXT;
ALTER TABLE gate_approvals ADD COLUMN patch_data TEXT;  -- JSON 格式的补丁数据
```

**迁移脚本** (`src/lee/orchestrator/storage/migrations/add_gate_actions.py`):

```python
async def upgrade():
    """为 gate_approvals 表添加动作相关列"""
    await db.execute("""
        ALTER TABLE gate_approvals
        ADD COLUMN decision_action TEXT DEFAULT NULL
    """)
    await db.execute("""
        ALTER TABLE gate_approvals
        ADD COLUMN target_step TEXT DEFAULT NULL
    """)
    await db.execute("""
        ALTER TABLE gate_approvals
        ADD COLUMN patch_data TEXT DEFAULT NULL
    """)
```

### A3. 修改 reject_gate() 逻辑

**新实现** (`src/lee/orchestrator/execution/gate_operations.py`):

```python
async def reject_gate(
    self,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str,
    action: Optional[GateDecisionAction] = None,
    target_step: Optional[str] = None,
    patch_data: Optional[Dict[str, Any]] = None,
) -> StepResult:
    """
    拒绝人工门禁，执行指定动作

    Args:
        workflow_id: 工作流 ID
        gate_id: 门禁 ID
        rejecter: 拒绝人
        reason: 拒绝原因
        action: 执行动作 (默认从配置读取)
        target_step: 目标步骤 (用于 rollback)
        patch_data: 补丁数据 (用于 patch_only)

    Returns:
        步骤执行结果
    """
    from lee.orchestrator.storage.models import GateStatus, WorkflowStatus

    # 1. 获取 gate 配置中的默认动作
    if action is None:
        action = await self._get_default_reject_action(workflow_id, gate_id)

    # 2. 更新门禁状态
    gate_approval = await self.store.update_gate_approval_with_action(
        workflow_id, gate_id, GateStatus.REJECTED, rejecter, reason,
        action, target_step, patch_data
    )

    # 3. 记录拒绝事件
    self.event_log.log_gate_rejected(
        gate_id=gate_id,
        step_id=gate_approval.step_id,
        approver=rejecter,
        reason=reason,
        action=action.value if action else None,
    )

    # 4. 执行动作 (不再默认 FAILED)
    if action == GateDecisionAction.ROLLBACK_TO_STEP:
        return await self._execute_rollback(
            workflow_id, gate_id, target_step, rejecter, reason
        )
    elif action == GateDecisionAction.REVISE_STEP_AND_RETRY:
        return await self._execute_revise_retry(
            workflow_id, gate_id, target_step or gate_approval.step_id, rejecter, reason
        )
    elif action == GateDecisionAction.SPAWN_CHANGE_REQUEST:
        return await self._execute_spawn_workflow(
            workflow_id, gate_id, rejecter, reason
        )
    elif action == GateDecisionAction.PATCH_ONLY:
        # 仅打 patch，工作流状态保持不变
        return StepResult(
            status="patched",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} patched by {rejecter}",
        )
    else:
        # 无动作或未知动作，才标记 FAILED
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)
        return StepResult(
            status="failed",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} rejected without valid action: {reason}",
        )

async def _execute_rollback(
    self,
    workflow_id: str,
    gate_id: str,
    target_step: str,
    rejecter: str,
    reason: str,
) -> StepResult:
    """执行回退动作"""
    # 1. 作废目标步骤之后的所有步骤
    await self.state_machine.invalidate_steps_after(workflow_id, target_step)

    # 2. 设置当前步骤指针
    await self.state_machine.set_current_step(workflow_id, target_step)

    # 3. 恢复工作流运行状态
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    # 4. 记录回退事件
    self.event_log.log_workflow_rollback(
        workflow_id=workflow_id,
        gate_id=gate_id,
        target_step=target_step,
        reason=reason,
    )

    return StepResult(
        status="rollback",
        step_id=target_step,
        workflow_id=workflow_id,
        message=f"Rollback to {target_step} by {rejecter}: {reason}",
    )

async def _execute_revise_retry(
    self,
    workflow_id: str,
    gate_id: str,
    retry_step: str,
    rejecter: str,
    reason: str,
) -> StepResult:
    """执行修订重试动作"""
    # 1. 增加步骤尝试次数
    await self.state_machine.increment_step_attempt(workflow_id, retry_step)

    # 2. 重置步骤状态为 pending
    await self.state_machine.reset_step_status(workflow_id, retry_step)

    # 3. 设置当前步骤
    await self.state_machine.set_current_step(workflow_id, retry_step)

    # 4. 恢复工作流运行状态
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    return StepResult(
        status="retry",
        step_id=retry_step,
        workflow_id=workflow_id,
        message=f"Revise and retry {retry_step} by {rejecter}: {reason}",
    )

async def _execute_spawn_workflow(
    self,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str,
) -> StepResult:
    """执行派生新 workflow 动作"""
    # 1. 获取当前工作流实例
    instance = await self.store.get_workflow(workflow_id)

    # 2. 创建新工作流实例
    new_workflow_id = await self.orchestrator.create_workflow(
        template_id=instance.template_id,
        project_dir=instance.project_dir,
        parent_workflow_id=workflow_id,
        metadata={"spawned_from_gate": gate_id, "reason": reason},
    )

    # 3. 将原工作流标记为 SUPERSEDED
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.SUPERSEDED)

    return StepResult(
        status="spawned",
        step_id=gate_id,
        workflow_id=workflow_id,
        message=f"Spawned new workflow {new_workflow_id} from gate {gate_id}",
        output={"new_workflow_id": new_workflow_id},
    )

async def _get_default_reject_action(
    self,
    workflow_id: str,
    gate_id: str,
) -> Optional[GateDecisionAction]:
    """从配置中获取默认的 reject 动作"""
    instance = await self.store.get_workflow(workflow_id)
    template = self.template_manager.get_template(instance.template_id)

    if template and hasattr(template, 'steps'):
        for step in template.steps:
            if hasattr(step, 'gate_id') and step.gate_id == gate_id:
                gate_config = getattr(step, 'gate', {})
                on_reject = gate_config.get('on_reject', {})
                action = on_reject.get('action')

                if action == 'rollback':
                    return GateDecisionAction.ROLLBACK_TO_STEP
                elif action == 'retry':
                    return GateDecisionAction.REVISE_STEP_AND_RETRY
                elif action == 'spawn':
                    return GateDecisionAction.SPAWN_CHANGE_REQUEST

    return None
```

### A4. 扩展 WorkflowStateMachine

**新增方法** (`src/lee/orchestrator/execution/state_machine.py`):

```python
class WorkflowStateMachine:
    async def invalidate_steps_after(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """
        作废指定步骤之后的所有步骤

        Args:
            workflow_id: 工作流 ID
            step_id: 基准步骤 ID
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        completed_steps = instance.data.get("completed_steps", [])
        step_outputs = instance.data.get("step_outputs", {})

        # 找到目标步骤在完成列表中的位置
        try:
            target_index = completed_steps.index(step_id)
        except ValueError:
            # 目标步骤未完成，无需作废
            return

        # 作废目标步骤之后的所有步骤
        steps_to_invalidate = completed_steps[target_index + 1:]

        for step in steps_to_invalidate:
            if step in step_outputs:
                del step_outputs[step]

        completed_steps = completed_steps[:target_index + 1]

        # 更新实例数据
        await self.store.update_workflow_data(workflow_id, {
            "completed_steps": completed_steps,
            "step_outputs": step_outputs,
        })

    async def set_current_step(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """
        设置当前步骤指针

        Args:
            workflow_id: 工作流 ID
            step_id: 目标步骤 ID
        """
        await self.store.update_workflow_current_step(workflow_id, step_id)

    async def increment_step_attempt(
        self,
        workflow_id: str,
        step_id: str,
    ) -> int:
        """
        增加步骤尝试次数

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID

        Returns:
            新的尝试次数
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return 1

        step_attempts = instance.data.get("step_attempts", {})
        current_attempt = step_attempts.get(step_id, 0)
        step_attempts[step_id] = current_attempt + 1

        await self.store.update_workflow_data(workflow_id, {
            "step_attempts": step_attempts,
        })

        return step_attempts[step_id]

    async def reset_step_status(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """
        重置步骤状态为 pending

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID
        """
        # 从 completed_steps 中移除
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        completed_steps = instance.data.get("completed_steps", [])
        if step_id in completed_steps:
            completed_steps.remove(step_id)
            await self.store.update_workflow_data(workflow_id, {
                "completed_steps": completed_steps,
            })
```

### A5. CLI 命令增强

**修改 reject 命令** (`src/lee/cli/commands/gates_cmd.py`):

```python
@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="拒绝原因")
@click.option("--action", type=click.Choice([
    "rollback", "revise", "spawn", "patch"
]), help="执行动作")
@click.option("--target-step", help="目标步骤 (用于 rollback/revise)")
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
    """拒绝门禁并执行指定动作"""
    click.echo(f"拒绝门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"审批人: {approver}")
    if comments:
        click.echo(f"原因: {comments}")

    # 显示动作选项
    if not action:
        click.echo("\n请选择执行动作:")
        click.echo("  1. rollback  - 回退到指定步骤")
        click.echo("  2. revise   - 修订后重试当前步骤")
        click.echo("  3. spawn    - 派生新工作流")
        click.echo("  4. patch    - 仅打补丁")

        action_choice = click.prompt("请选择 (1-4)", type=int)
        action_map = {1: "rollback", 2: "revise", 3: "spawn", 4: "patch"}
        action = action_map.get(action_choice)

    # 根据动作获取目标步骤
    if action in ["rollback", "revise"] and not target_step:
        target_step = click.prompt("请输入目标步骤 ID")

    # 确认拒绝
    if not click.confirm(f"\n确认拒绝并执行 {action} 动作？"):
        click.echo("已取消")
        return

    # 调用拒绝 API
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

        click.echo(f"\n✅ 门禁已拒绝，执行动作: {action}")
        if result.get("new_workflow_id"):
            click.echo(f"新工作流 ID: {result.get('new_workflow_id')}")

    except Exception as e:
        click.echo(f"拒绝失败: {e}")
```

---

## 方案 B: 完整版本

> 目标: 完全实现文档中描述的 on_reject/on_revise 配置

### B1. 添加 REVISED 状态

**扩展枚举** (`src/lee/orchestrator/storage/models.py`):

```python
class GateStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"      # 新增: 要求修改
```

### B2. 保存路由策略到 Gate 实例

**修改 HumanGateRunner** (`src/lee/orchestrator/execution/runners/gate_runner.py`):

```python
async def execute(self, workflow_id: str, step, ctx: RunnerContext) -> StepResult:
    """处理 Human Gate 步骤"""
    from lee.orchestrator.storage.models import WorkflowStatus, GateApproval, GateStatus

    # 暂停工作流
    await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

    # 提取完整 gate 配置
    gate_config = step.config.get("gate", {})
    if not gate_config and hasattr(step, 'gate_id'):
        gate_config = {
            "id": step.gate_id,
            "reviewers": step.config.get("reviewers", []),
            "approval_criteria": step.config.get("approval_criteria", []),
            "on_reject": step.config.get("on_reject", {}),
            "on_revise": step.config.get("on_revise", {}),
        }

    # 创建门禁审批记录（包含路由策略）
    gate_approval = GateApproval(
        workflow_id=workflow_id,
        gate_id=step.gate_id or f"gate_{step.id}",
        step_id=step.id,
        status=GateStatus.PENDING,
        approval_criteria=gate_config.get("approval_criteria", []),
        reviewers=gate_config.get("reviewers", []),
        # 新增: 保存路由策略
        on_reject_action=gate_config.get("on_reject", {}).get("action"),
        on_reject_target=gate_config.get("on_reject", {}).get("target_step"),
        on_revise_action=gate_config.get("on_revise", {}).get("action"),
        on_revise_target=gate_config.get("on_revise", {}).get("target_step"),
    )
    await ctx.store.create_gate_approval(gate_approval)

    # 记录门禁触发事件
    ctx.event_log.log_gate_triggered(
        gate_id=step.gate_id or f"gate_{step.id}",
        step_id=step.id,
        gate_type="human",
        blocking=True,
        on_reject_action=gate_approval.on_reject_action,
    )

    return StepResult(
        status="blocked",
        blocked_reason="human_gate",
        step_id=step.id,
        workflow_id=workflow_id,
        message=f"Waiting for human approval at gate: {step.gate_id or step.id}",
    )
```

### B3. 添加结构化反馈支持

**扩展数据模型**:

```python
@dataclass
class StructuredFeedback:
    """结构化反馈"""
    issues: List[str]              # 发现的问题
    expected_changes: List[str]    # 期望的变更
    acceptance_delta: List[str]    # 验收标准变更

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issues": self.issues,
            "expected_changes": self.expected_changes,
            "acceptance_delta": self.acceptance_delta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredFeedback":
        return cls(
            issues=data.get("issues", []),
            expected_changes=data.get("expected_changes", []),
            acceptance_delta=data.get("acceptance_delta", []),
        )
```

**gate_approvals 表新增列**:

```sql
ALTER TABLE gate_approvals ADD COLUMN structured_feedback TEXT;
```

**CLI 支持从文件导入**:

```bash
lee gates reject wf_task_123 gate_id \
  --approver zengle \
  --action rollback \
  --target-step s5_1_plan_commits \
  --feedback-file feedback.json
```

**feedback.json 示例**:

```json
{
  "issues": [
    "commit-001 和 commit-002 应该合并",
    "缺少单元测试覆盖"
  ],
  "expected_changes": [
    "合并 commit-001 和 commit-002",
    "添加单元测试，覆盖率 > 80%"
  ],
  "acceptance_delta": [
    "新增: 单元测试覆盖率要求"
  ]
}
```

### B4. CLI 交互优化

**show 命令增强**:

```python
@gates.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
def show(workflow_id: str, project_dir: str) -> None:
    """显示门禁详情和产物"""
    # ... 现有代码 ...

    # 新增: 显示可用的动作选项
    click.echo("\n🎯 可用的审批选项:")

    # 读取 gate 配置
    gate_config = get_gate_config(workflow_id, current_step)

    if gate_config.get("on_reject"):
        on_reject = gate_config["on_reject"]
        click.echo(f"\n  拒绝后 (reject):")
        click.echo(f"    动作: {on_reject.get('action', '未配置')}")
        click.echo(f"    目标: {on_reject.get('target_step', '未配置')}")

    if gate_config.get("on_revise"):
        on_revise = gate_config["on_revise"]
        click.echo(f"\n  修订后 (revise):")
        click.echo(f"    动作: {on_revise.get('action', '未配置')}")
        click.echo(f"    目标: {on_revise.get('target_step', '未配置')}")

    # 新增: 生成命令模板
    click.echo("\n📝 命令模板:")

    on_reject_action = gate_config.get("on_reject", {}).get("action")
    if on_reject_action == "rollback":
        target = gate_config.get("on_reject", {}).get("target_step")
        click.echo(f"\n  拒绝并回退:")
        click.echo(f"  lee gates reject {workflow_id} {current_step} \\")
        click.echo(f"    --approver <你的名字> \\")
        click.echo(f"    --action rollback \\")
        click.echo(f"    --target-step {target} \\")
        click.echo(f"    --comments '原因'")

    click.echo(f"\n  批准:")
    click.echo(f"  lee gates approve {workflow_id} {current_step} \\")
    click.echo(f"    --approver <你的名字>")
```

---

## 迁移路径

### 阶段 1: 数据模型升级 (1-2 天)

1. 执行数据库迁移脚本
2. 更新 `GateStatus` 枚举
3. 添加 `GateDecisionAction` 枚举
4. 更新 `GateApproval` 数据类

### 阶段 2: 核心逻辑改造 (2-3 天)

1. 实现 `_execute_rollback()`
2. 实现 `_execute_revise_retry()`
3. 实现 `_execute_spawn_workflow()`
4. 扩展 `WorkflowStateMachine`

### 阶段 3: CLI 增强 (1-2 天)

1. 修改 `reject` 命令支持 `--action`
2. 添加 `--target-step` 参数
3. 优化 `show` 命令显示
4. 添加命令模板生成

### 阶段 4: 测试与验证 (2-3 天)

1. 单元测试
2. 集成测试
3. 端到端场景测试
4. 文档更新

### 阶段 5: 完整版本特性 (3-5 天)

1. 添加 `REVISED` 状态支持
2. 实现结构化反馈
3. CLI 交互优化
4. 配置默认路由

---

## 风险评估

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 数据库迁移失败 | 高 | 备份数据库、回滚脚本 |
| 状态机复杂度增加 | 中 | 充分测试、状态机图 |
| 向后兼容性 | 中 | 保留旧 API、渐进迁移 |
| 性能影响 | 低 | 异步操作、索引优化 |

### 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 用户学习成本 | 中 | 详细文档、示例 |
| 工作流不可预测 | 高 | 清晰的动作语义、审计日志 |
| 误操作 | 中 | 确认提示、权限控制 |

---

## 附录

### A. 配置示例

```yaml
steps:
  - id: code_review_gate
    kind: human_gate
    depends_on:
      - run_tests
    name: 代码评审 Gate
    description: 人工评审代码质量和测试结果
    gate:
      reviewers:
        - role: developer
          required: true
        - role: reviewer
          required: true
      approval_criteria:
        - type: checklist
          item: "代码是否符合 PEP 8 规范？"
          required: true
        - type: checklist
          item: "是否包含必要的注释？"
          required: true
      on_reject:
        action: rollback              # 回退到指定步骤
        target_step: generate_code    # 目标步骤
      on_revise:
        action: retry                 # 重试当前步骤
        target_step: run_tests        # 重试的步骤
```

### B. 使用示例

```bash
# 场景 1: 回退重新规划
lee gates reject wf_task_123 gate_s5_2_review_commits \
  --approver zengle \
  --action rollback \
  --target-step s5_1_plan_commits \
  --comments "提交计划需要重新分组"

# 场景 2: 修订后重试
lee gates reject wf_task_123 gate_s4_1_review_code \
  --approver zengle \
  --action revise \
  --target-step s3_1_organize_docs \
  --comments "文档组织需要调整"

# 场景 3: 派生新工作流
lee gates reject wf_task_123 gate_s2_1_requirement_review \
  --approver zengle \
  --action spawn \
  --comments "需求变更，需要新的工作流"

# 场景 4: 结构化反馈
lee gates reject wf_task_123 gate_s5_2_review_commits \
  --approver zengle \
  --action rollback \
  --target-step s5_1_plan_commits \
  --feedback-file feedback.json
```

---

## 下一步行动

1. ✅ 完成改进方案文档
2. ✅ 调用架构师评审
3. ⏳ 根据反馈调整方案
4. ⏳ 开始实施阶段 1

---

## 架构评审反馈 (2026-02-19)

**评审结果**: ✅ 有条件批准

**关键问题修复**:

### 必须修复 (P0)

1. **添加事务支持**
   ```python
   async def _execute_rollback(...):
       async with self.store.transaction():
           await self.state_machine.invalidate_steps_after(...)
           await self.state_machine.set_current_step(...)
           await self.store.update_workflow_status(...)
   ```

2. **完善数据清理逻辑**
   ```python
   async def invalidate_steps_after(...):
       # 清理 task_executions
       await self.store.invalidate_task_executions_after(workflow_id, step_id)
       # 清理 gate_approvals
       await self.store.invalidate_gates_after(workflow_id, step_id)
       # 清理 step_outputs
       step_outputs = {...}
   ```

3. **添加重试上限**
   ```python
   MAX_STEP_ATTEMPTS = 3
   if current_attempt >= MAX_STEP_ATTEMPTS:
       raise MaxAttemptsExceededError(step_id, current_attempt)
   ```

4. **添加 SUPERSEDED 状态**
   ```python
   class WorkflowStatus(Enum):
       SUPERSEDED = "superseded"  # 被新工作流替代
   ```

### 时间估算调整

| 阶段 | 原估算 | 调整后 | 理由 |
|------|--------|--------|------|
| 阶段 1 | 1-2 天 | 2-3 天 | 需要更完整的迁移脚本和测试 |
| 阶段 2 | 2-3 天 | 3-5 天 | 需要添加事务处理和错误恢复 |
| 阶段 3 | 1-2 天 | 2-3 天 | CLI 需要更多边界情况处理 |
| 阶段 4 | 2-3 天 | 3-4 天 | 需要并发测试和压力测试 |
| 阶段 5 | 3-5 天 | 5-7 天 | 结构化反馈需要更多设计 |

详细评审内容请参考: [Gate 改进方案 - 架构评审报告](./gate-improvement-review.md)
