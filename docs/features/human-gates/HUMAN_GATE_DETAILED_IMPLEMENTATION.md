---
title: LEE Human Gate 详细实现说明文档
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# LEE Human Gate 详细实现说明文档

> 作者: LEE Team
> 日期: 2026-02-19
> 版本: 1.0

---

## 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [数据模型与存储](#数据模型与存储)
4. [工作流执行流程](#工作流执行流程)
5. [状态机管理](#状态机管理)
6. [CLI 命令接口](#cli-命令接口)
7. [安全机制](#安全机制)
8. [代码结构](#代码结构)
9. [使用示例](#使用示例)

---

## 概述

Human Gate（人工门禁）是 LEE 工作流编排系统中的一种特殊步骤类型，用于在工作流执行过程中插入人工审批点。当工作流执行到 human_gate 步骤时，会自动暂停并等待人类用户进行审批决策。

### 主要特性

- **自动暂停**: 工作流遇到 gate 时自动进入 PAUSED 状态
- **多种决策**: 支持 approve（批准）、reject（拒绝）、revise（要求修改）三种决策
- **审批清单**: 可配置必需的检查项
- **审计追踪**: 完整记录所有决策历史
- **规则评估**: v3.1+ 支持自动化规则评估与人工审批结合
- **事件日志**: 记录所有门禁相关事件

---

## 核心概念

### 1. Gate 状态

```python
class GateStatus(Enum):
    PENDING = "pending"      # 等待审批
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
```

### 2. 状态转换规则

```
pending → approved   # 人类批准
pending → rejected   # 人类拒绝
任何状态 → pending   # 可重新审批（创建新版本）
```

### 3. Gate 类型

1. **human_gate**: 人工审批门禁
2. **compliance_gate**: 合规检查门禁（自动验证 AI 行为）

---

## 数据模型与存储

### 1. 数据库表结构

#### gate_approvals 表

```sql
CREATE TABLE gate_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,        -- 工作流 ID
    gate_id TEXT NOT NULL,            -- 门禁 ID
    step_id TEXT NOT NULL,            -- 步骤 ID
    status TEXT NOT NULL,             -- PENDING | APPROVED | REJECTED
    approval_criteria TEXT,           -- 审批标准（JSON）
    reviewers TEXT,                   -- 审批人列表（JSON）
    approver TEXT,                    -- 实际审批人
    comments TEXT,                    -- 审批意见
    created_at TIMESTAMP,             -- 创建时间
    decided_at TIMESTAMP,             -- 决策时间
    UNIQUE(workflow_id, gate_id)
);
```

**字段说明**:
- `approval_criteria`: 存储审批标准，如 checklist 项
- `reviewers`: 从 workflow.yaml 中复制的审批人配置
- `approver`: 实际执行审批的用户名
- `decided_at`: 决策时间戳，审批/拒绝时更新

### 2. 决策文件格式

决策文件存储在 `{project_dir}/.workflow/gates/{gate_id}.yaml`:

```yaml
gate_id: p08_04_review_gate
step_id: p08_04_review_gate
workflow_id: phase8
project_dir: dev/phase8

# Gate 状态
status: pending  # pending | approved | rejected | revised

# 决策信息
decided_by: null        # 决策人，如 "lezeng"
decided_at: null        # 决策时间，ISO 8601 格式
option: null            # approve | reject | revise
comment: ""             # 决策评语

# 审批清单
checklist:
  - item: "需求是否覆盖了所有场景？"
    ok: null             # true | false | null
    note: ""             # 备注
  - item: "是否有明确的非功能性要求？"
    ok: null
    note: ""

# 审批人配置（来自 workflow.yaml）
approvers:
  - role: pm
    name: null
  - role: architect
    name: null

# 上游产物（自动填充）
upstream_artifacts:
  - step_id: p08_03_proposal
    path: dev/phase8/output/proposal.md
    summary: ""

# 决策历史（保留所有修订）
history:
  - version: 1
    status: pending
    decided_by: null
    decided_at: null
    comment: "初始创建"
```

### 3. 存储层实现

**SQLiteStore 类** (`src/lee/orchestrator/storage/sqlite_store.py`):

```python
async def create_gate_approval(self, approval: GateApproval) -> None:
    """创建门禁审批记录"""

async def get_pending_gates(self, workflow_id: str) -> List[GateApproval]:
    """获取待审批门禁列表"""

async def update_gate_approval(
    self,
    workflow_id: str,
    gate_id: str,
    status: GateStatus,
    approver: str,
    comments: str
) -> GateApproval:
    """更新门禁审批状态"""
```

---

## 工作流执行流程

### 1. HumanGateRunner 执行流程

当工作流执行到 `kind: human_gate` 的步骤时，`HumanGateRunner` 负责处理：

```python
class HumanGateRunner(StepRunnerBase):
    """Human Gate 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "human_gate"

    async def execute(self, workflow_id: str, step, ctx: RunnerContext) -> StepResult:
        # 1. 暂停工作流
        await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        # 2. 提取 gate 配置
        gate_config = step.config.get("gate", {})

        # 3. 创建门禁审批记录
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=step.gate_id or f"gate_{step.id}",
            step_id=step.id,
            status=GateStatus.PENDING,
            approval_criteria=gate_config.get("approval_criteria", []),
            reviewers=gate_config.get("reviewers", []),
        )
        await ctx.store.create_gate_approval(gate_approval)

        # 4. 记录门禁触发事件
        ctx.event_log.log_gate_triggered(
            gate_id=step.gate_id,
            step_id=step.id,
            gate_type="human",
            blocking=True,
        )

        # 5. 返回 blocked 状态
        return StepResult(
            status="blocked",
            blocked_reason="human_gate",
            message=f"Waiting for human approval at gate: {step.gate_id}",
        )
```

### 2. 执行流程图

```
┌─────────────────┐
│ 工作流执行中     │
│ status=RUNNING  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 遇到 human_gate │
│ 步骤            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ HumanGateRunner │
│ .execute()      │
└────────┬────────┘
         │
         ├──► 暂停工作流 (PAUSED)
         │
         ├──► 创建 GateApproval 记录
         │
         ├──► 记录 gate_triggered 事件
         │
         ▼
┌─────────────────┐
│ 返回 blocked    │
│ 状态            │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ 等待人工审批     │
│ (CLI/API)       │
└────────┬────────┘
         │
         ├─────► approve_gate() ──► 恢复工作流 ──► 继续执行
         │
         └─────► reject_gate() ──► 工作流失败 (FAILED)
```

### 3. GateOperationsMixin 操作

**批准门禁** (`approve_gate`):

```python
async def approve_gate(
    self,
    workflow_id: str,
    gate_id: str,
    approver: str,
    comments: str = ""
) -> StepResult:
    # 1. 规则评估（v3.1+）
    gate_evaluation = self.gate_engine.evaluate_gate(gate_ir, eval_context)

    # 2. 更新门禁状态
    gate_approval = await self.store.update_gate_approval(
        workflow_id, gate_id, GateStatus.APPROVED, approver, comments
    )

    # 3. 恢复工作流
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    # 4. 记录审批事件
    self.event_log.log_gate_approved(gate_id, step_id, approver, approval_id)

    # 5. 完成门禁步骤
    result = await self.state_machine.complete_step(
        workflow_id, step_id, gate_output
    )

    return result
```

**拒绝门禁** (`reject_gate`):

```python
async def reject_gate(
    self,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str
) -> StepResult:
    # 1. 更新门禁状态
    gate_approval = await self.store.update_gate_approval(
        workflow_id, gate_id, GateStatus.REJECTED, rejecter, reason
    )

    # 2. 标记工作流失败
    await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)

    # 3. 记录拒绝事件
    self.event_log.log_gate_rejected(gate_id, step_id, rejecter, reason)

    return StepResult(status="failed", message=f"Gate {gate_id} rejected")
```

---

## 状态机管理

### 1. GateStateMachine

`GateStateMachine` 类负责管理门禁的状态转换：

```python
class GateStateMachine:
    """门禁状态机"""

    async def create_gate(
        self,
        workflow_id: str,
        step_id: str,
        context: Dict[str, Any]
    ) -> GateState:
        """创建新的门禁实例"""

    async def approve_gate(
        self,
        gate_id: str,
        context: Dict[str, Any]
    ) -> GateState:
        """批准门禁"""

    async def reject_gate(
        self,
        gate_id: str,
        reason: str
    ) -> GateState:
        """拒绝门禁"""

    async def skip_gate(self, gate_id: str) -> GateState:
        """跳过门禁"""
```

### 2. WorkflowStateMachine

工作流状态机与门禁状态机协同工作：

- 遇到 gate 时工作流进入 `PAUSED` 状态
- 批准后恢复为 `RUNNING` 状态
- 拒绝后变为 `FAILED` 状态

---

## CLI 命令接口

### 统一命令入口: `lee gates`

LEE 提供了 `lee gates` 命令组作为统一的门禁管理入口。

#### 1. 列出门禁

```bash
lee gates list <workflow_id> [--project-dir <path>]
```

**功能**:
- 显示工作流状态
- 列出所有门禁及其状态
- 显示审批人和评论

**示例输出**:
```
工作流: wf_task_738a4957
状态: paused
当前步骤: s5_2_review_commits

门禁列表:
  ⏳ gate_s5_2_review_commits
     状态: pending
```

#### 2. 显示门禁详情

```bash
lee gates show <workflow_id> [--project-dir <path>]
```

**功能**:
- 显示工作流状态
- 列出相关产物文件（artifacts）
- 显示最近执行的步骤
- 显示失败的步骤（如有）

**示例输出**:
```
工作流: wf_task_738a4957
状态: paused
当前步骤: s5_2_review_commits

📂 相关产物文件:

workspace-cleanup/:
  - commit-plan.yaml
  - doc-organization.yaml

tech-debt/:
  - tech-debt-2025-02-19.yaml

📝 最近执行的步骤:
  ✅ s5_1_plan_commits (completed)
  ✅ s4_1_review_code_docs (completed)
```

#### 3. 批准门禁

```bash
lee gates approve <workflow_id> <gate_id> \
  --approver <your-name> \
  [--comments "审批意见"] \
  [--project-dir <path>]
```

**功能**:
- 显示门禁信息
- 显示相关产物文件（如 commit-plan.yaml）
- 提示确认
- 执行批准操作

**示例**:
```bash
lee gates approve wf_task_738a4957 gate_s5_2_review_commits --approver zengle
```

#### 4. 拒绝门禁

```bash
lee gates reject <workflow_id> <gate_id> \
  --approver <your-name> \
  --comments "拒绝原因" \
  [--project-dir <path>]
```

**功能**:
- 显示拒绝后会发生什么
- 提示确认
- 执行拒绝操作

**示例**:
```bash
lee gates reject wf_task_738a4957 gate_s5_2_review_commits \
  --approver zengle \
  --comments "需要调整提交分组"
```

---

## 安全机制

### 1. 工具隔离（Two-Session Architecture）

LEE 使用两个独立的会话来分离 PM 和 Gate 操作：

#### PM Session 工具
- `get_state`: 获取工作流状态
- `run_step`: 运行步骤
- `list_ready_steps`: 列出可执行步骤

#### Gate Session 工具
- `list_pending`: 列出待审批门禁
- `show`: 显示门禁详情
- `decide`: 提交门禁决策

### 2. 权限控制规则

| 操作 | PM Agent | Gate Assistant | 人类用户 |
|------|----------|----------------|----------|
| 查看门禁状态 | ✅ | ✅ | ✅ |
| 创建门禁 | ✅ | ❌ | ❌ |
| 提交决策 | ❌ | ⚠️ (仅人类明确指示) | ✅ |
| 直接修改文件 | ❌ | ❌ | ✅ |

### 3. 必需字段验证

- `decided_by`: 不能为空
- `option`: 必须是 approve/reject/revise 之一
- `comment`: 不能为空

### 4. 审计要求

- 每次状态变更记录在 `history` 中
- 保留完整的决策链路
- 事件日志记录所有门禁相关事件

### 5. 文件保护

- Gate 决策文件只能通过 `api_gate_decide` 修改
- PM agent 不能直接编辑 gate 文件
- 文件锁定防止并发修改

---

## 代码结构

### 核心文件

```
src/lee/orchestrator/
├── execution/
│   ├── gate_api.py              # Gate API 接口
│   ├── gate_operations.py       # 门禁操作 Mixin
│   ├── runners/
│   │   └── gate_runner.py       # Gate 步骤运行器
│   └── state_machine.py         # 状态机（含 GateStateMachine）
├── storage/
│   ├── models.py                # 数据模型（GateApproval, GateInfo）
│   └── sqlite_store.py          # SQLite 存储层
└── template_manager.py          # 模板管理器

src/lee/cli/commands/
└── gates_cmd.py                 # CLI 命令实现
```

### 关键类关系

```
┌─────────────────────────┐
│   Orchestrator          │
│   (gate_operations.py)  │
└───────────┬─────────────┘
            │
            │ 使用
            ▼
┌─────────────────────────┐
│   GateOperationsMixin   │
│   - approve_gate()      │
│   - reject_gate()       │
│   - get_pending_gates() │
└───────────┬─────────────┘
            │
            │ 调用
            ▼
┌─────────────────────────┐
│   GateStateMachine      │
│   - create_gate()       │
│   - approve_gate()      │
│   - reject_gate()       │
└───────────┬─────────────┘
            │
            │ 使用
            ▼
┌─────────────────────────┐
│   SQLiteStore           │
│   - create_gate_approval()│
│   - update_gate_approval()│
│   - get_pending_gates()  │
└─────────────────────────┘
```

---

## 使用示例

### 场景 1: 基本审批流程

```bash
# 1. 工作流执行遇到门禁
lee run my_workflow

# 2. 查看当前状态
lee status wf_task_123

# 3. 查看门禁详情和产物
lee gates show wf_task_123

# 4. 批准门禁
lee gates approve wf_task_123 gate_s5_2_review_commits --approver zengle

# 5. 监控后续执行
lee watch wf_task_123
```

### 场景 2: 拒绝并重新规划

```bash
# 1. 查看门禁详情
lee gates show wf_task_123

# 2. 查看具体产物（如提交计划）
cat workspace-cleanup/commit-plan.yaml

# 3. 拒绝门禁（触发重新规划）
lee gates reject wf_task_123 gate_s5_2_review_commits \
  --approver zengle \
  --comments "commit-001 和 commit-002 应该合并"

# 4. 工作流将返回到 s5_1_plan_commits 重新规划
```

### 场景 3: 批量审批

```bash
# 列出所有待审批门禁
lee gates list wf_task_123

# 逐个审批
for gate in gate_1 gate_2 gate_3; do
  lee gates approve wf_task_123 $gate --approver zengle
done
```

---

## 附录

### A. 配置示例

完整的 workflow.yaml 中 gate 配置示例：

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
        - type: checklist
          item: "测试覆盖率是否足够？"
          required: true
      on_reject:
        action: rollback
        target_step: generate_code
      on_revise:
        action: continue
        target_step: generate_code
```

### B. API 调用示例

```python
from lee.orchestrator.api import pm_workflow

# 批准门禁
result = pm_workflow(
    "approve_gate",
    project_dir=".",
    workflow_id="wf_task_123",
    gate_id="gate_s5_2_review_commits",
    approver="zengle",
    decision="approve",
    comments="方案可行，批准推进"
)

# 拒绝门禁
result = pm_workflow(
    "approve_gate",
    project_dir=".",
    workflow_id="wf_task_123",
    gate_id="gate_s5_2_review_commits",
    approver="zengle",
    decision="reject",
    comments="需要调整提交分组"
)
```

### C. 事件日志示例

门禁相关事件：

```json
{
  "event_type": "gate_triggered",
  "gate_id": "gate_s5_2_review_commits",
  "step_id": "s5_2_review_commits",
  "gate_type": "human",
  "blocking": true,
  "timestamp": "2026-02-19T10:30:00Z"
}

{
  "event_type": "gate_approved",
  "gate_id": "gate_s5_2_review_commits",
  "step_id": "s5_2_review_commits",
  "approver": "zengle",
  "approval_id": "wf_task_123_gate_s5_2_review_commits",
  "timestamp": "2026-02-19T10:35:00Z"
}

{
  "event_type": "gate_rejected",
  "gate_id": "gate_s5_2_review_commits",
  "step_id": "s5_2_review_commits",
  "approver": "zengle",
  "reason": "需要调整提交分组",
  "timestamp": "2026-02-19T10:40:00Z"
}
```

---

## 更新日志

### v1.0 (2026-02-19)
- 初始版本
- 完整记录 human gate 的实现细节
- 包含数据模型、执行流程、CLI 命令等
