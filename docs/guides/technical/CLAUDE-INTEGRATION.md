---
title: Claude Code + LEE 集成指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Claude Code + LEE 集成指南

本文档说明如何将 LEE 的 PM Agent 和 Gate Assistant 集成到 Claude Code 中，实现两个独立的会话。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                  Claude Code (两个会话)                   │
│                                                         │
│  ┌─────────────────────┐      ┌─────────────────────┐  │
│  │    PM 会话          │      │   Gate 会话         │  │
│  │  (PM Agent)         │      │ (Gate Assistant)    │  │
│  └──────────┬──────────┘      └──────────┬──────────┘  │
│             │                            │             │
└─────────────┼────────────────────────────┼─────────────┘
              │                            │
              ▼                            ▼
    ┌───────────────────────────────────────────────┐
    │         flowcore.api (统一 API 层)            │
    │  ┌─────────────────┐    ┌─────────────────┐ │
    │  │ PM API          │    │ Gate API        │ │
    │  │ - get_state     │    │ - list_pending  │ │
    │  │ - run_step      │    │ - show          │ │
    │  │ - list_ready    │    │ - decide        │ │
    │  └─────────────────┘    └─────────────────┘ │
    └──────────────────────┬────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Orchestrator          │
              │  (状态管理 + 执行编排)   │
              └─────────────────────────┘
```

**关键设计**:
1. PM 会话只能调用 PM API，不能调用 Gate API
2. Gate 会话只能调用 Gate API，不能调用 PM API
3. 两个会话共享同一个 project_dir 和 state
4. Human gate 的状态只能通过 Gate 会话修改

---

## 1. PM 会话配置

### 1.1 创建 PM 会话

在 Claude Code 中创建一个新的会话，命名为 "LEE PM Session" 或类似名称。

### 1.2 配置工具 (PM 会话)

在 Claude Code 的工具配置中，只添加 PM 相关的工具：

```json
{
  "name": "lee_pm_workflow",
  "description": "LEE PM Agent 工作流管理工具",
  "file": "flowcore/api.py",
  "functions": [
    {
      "name": "get_state",
      "description": "获取工作流状态",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string",
            "description": "项目目录路径"
          }
        },
        "required": ["project_dir"]
      }
    },
    {
      "name": "list_ready_steps",
      "description": "列出可执行的步骤",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string",
            "description": "项目目录路径"
          }
        },
        "required": ["project_dir"]
      }
    },
    {
      "name": "run_step",
      "description": "执行特定步骤",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string"
          },
          "step_id": {
            "type": "string"
          }
        },
        "required": ["project_dir", "step_id"]
      }
    }
  ]
}
```

### 1.3 PM 会话的 System Prompt

使用 `docs/PM_AGENT_PROTOCOL.md` 的内容作为 system prompt。

关键约束：
- 不能修改文件
- 不能执行 shell 命令
- **不能调用 gate 工具**
- 遇到 human_gate 必须提示用户切换到 Gate 会话

---

## 2. Gate 会话配置

### 2.1 创建 Gate 会话

在 Claude Code 中创建另一个独立的会话，命名为 "LEE Gate Session"。

### 2.2 配置工具 (Gate 会话)

在 Gate 会话的工具配置中，只添加 Gate 相关的工具：

```json
{
  "name": "lee_gate_approval",
  "description": "LEE Gate Assistant 审批工具",
  "file": "flowcore/api.py",
  "functions": [
    {
      "name": "list_pending",
      "description": "列出待审批的 gate",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string"
          }
        },
        "required": ["project_dir"]
      }
    },
    {
      "name": "show",
      "description": "显示 gate 详情",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string"
          },
          "gate_id": {
            "type": "string"
          }
        },
        "required": ["project_dir", "gate_id"]
      }
    },
    {
      "name": "decide",
      "description": "提交 gate 决策",
      "parameters": {
        "type": "object",
        "properties": {
          "project_dir": {
            "type": "string"
          },
          "gate_id": {
            "type": "string"
          },
          "option": {
            "type": "string",
            "enum": ["approve", "reject", "revise"]
          },
          "comment": {
            "type": "string"
          },
          "decided_by": {
            "type": "string"
          },
          "checklist": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "item": {"type": "string"},
                "ok": {"type": "boolean"}
              }
            }
          }
        },
        "required": ["project_dir", "gate_id", "option", "comment", "decided_by"]
      }
    }
  ]
}
```

### 2.3 Gate 会话的 System Prompt

使用 `docs/GATE_ASSISTANT_PROTOCOL.md` 的内容作为 system prompt。

关键约束：
- 必须等待人类明确表达才能调用 decide
- 不能伪造 decided_by 字段
- 只能通过 gate_decide 修改状态

---

## 3. 使用流程

### 3.1 执行一个包含 human gate 的 workflow

**步骤 1: PM 会话 - 开始执行**

```
你: 帮我执行 dev/phase8 项目的 workflow

PM Agent: [调用 get_state]
当前状态：workflow 未初始化

我建议先执行第一个步骤：generate_code
[调用 run_step("generate_code")]

✅ 步骤完成，耗时 15 秒
```

**步骤 2: 继续执行直到遇到 human gate**

```
PM Agent: [调用 run_step("run_tests")]

✅ 测试通过

现在检查下一步...
[调用 get_state]

⚠️ 当前阻塞在 human_gate: p08_04_review_gate

**这是一个需要人工审批的节点**

决策文件位置：dev/phase8/.workflow/gates/p08_04_review_gate.yaml

审批清单：
- 需求是否覆盖？
- 风险是否列出？
- 是否有验收标准？

**请切换到 Gate 会话完成审批**。审批完成后，
回到此会话，我将检查 gate 状态并继续执行 workflow。
```

**步骤 3: Gate 会话 - 完成审批**

```
你: [切换到 Gate 会话] 有哪些 pending gate？

Gate Assistant: [调用 list_pending]

当前有 1 个 pending gate：
- p08_04_review_gate: 方案评审 gate

你: 展开这个 gate

Gate Assistant: [调用 show("p08_04_review_gate")]

**Gate 详情**

描述：方案评审 gate

**审批清单**：
1. 需求是否覆盖？[未评估]
2. 风险是否列出？[未评估]
3. 是否有验收标准？[未评估]

**上游产物**：
- proposal.md: 方案采用模块化架构...
- requirements.md: 系统需要支持...

---

**我的评审建议**：

根据分析：
✅ 需求覆盖较全面
✅ 架构设计合理
⚠️ 风险部分略显简略
⚠️ 建议补充验收标准

**建议**: 可以批准，但建议在后续步骤中完善。

---

你打算批准还是打回修改？

你: 批准

Gate Assistant: [调用 decide(
  gate_id="p08_04_review_gate",
  option="approve",
  comment="方案可行，批准推进",
  decided_by="lezeng",
  checklist=[...]
)]

✅ **已提交决策**
- Gate: p08_04_review_gate
- 状态: approved
- 决策人: lezeng
- 时间: 2025-01-23T10:15:00Z

回到 PM 会话后，workflow 将继续执行。
```

**步骤 4: PM 会话 - 继续执行**

```
你: [切换回 PM 会话] 继续执行 workflow

PM Agent: [调用 get_state]

✅ gate p08_04_review_gate 已批准

当前可以执行的步骤：p08_06_implementation

[调用 run_step("p08_06_implementation")]

✅ 实施步骤开始执行...
```

---

## 4. 安全机制

### 4.1 工具隔离

**PM 会话工具**:
```python
- api_get_state
- api_list_ready_steps
- api_run_step
- api_next_step
```

**Gate 会话工具**:
```python
- api_gate_list_pending
- api_gate_show
- api_gate_decide
```

两个工具集**完全不重叠**，确保：
- PM agent 无法修改 gate 状态
- Gate assistant 无法执行 workflow 步骤

### 4.2 状态机保护

Orchestrator 中的状态机逻辑：

```python
def execute_human_gate_step(step_id):
    gate_file = load_gate_file(step_id)
    gate_status = gate_file["status"]

    # 只能读取，不能自动推进
    if gate_status in ["approved", "rejected"]:
        mark_step_completed(step_id)
    else:
        mark_step_pending_human(step_id)
        # 不会自动执行任何操作
```

### 4.3 文件权限控制

Gate 决策文件：
- 位置：`{project_dir}/.workflow/gates/{gate_id}.yaml`
- 只能通过 `api_gate_decide` 修改
- PM agent 没有写入权限

---

## 5. 配置文件示例

### 5.1 Workflow 配置 (包含 human gate)

```yaml
# workflows/phase8/workflow.yaml
workflow:
  id: phase8
  name: Phase 8 - Implementation
  version: 1.0

steps:
  - id: p08_01_design
    kind: agent
    agent: architect
    description: 生成设计文档

  - id: p08_02_proposal
    kind: agent
    agent: architect
    depends_on: [p08_01_design]
    description: 生成方案文档

  - id: p08_03_review_gate
    kind: human_gate
    depends_on: [p08_02_proposal]
    description: 方案评审 gate
    gate:
      approvers:
        - role: pm
        - role: architect
      options: [approve, reject, revise]
      checklist:
        - item: "需求是否覆盖？"
          required: true
        - item: "风险是否列出？"
          required: true
        - item: "是否有验收标准？"
          required: true

  - id: p08_04_implementation
    kind: agent
    agent: developer
    depends_on: [p08_03_review_gate]
    description: 实现功能

  - id: p08_05_acceptance_gate
    kind: human_gate
    depends_on: [p08_04_implementation]
    description: 验收 gate
    gate:
      approvers:
        - role: pm
        - role: qa
      options: [approve, reject]
      checklist:
        - item: "所有测试通过？"
        - item: "文档完整？"
        - item: "性能达标？"
```

### 5.2 Gate 决策文件 (模板)

```yaml
# .workflow/gates/p08_03_review_gate.yaml
gate_id: p08_03_review_gate
step_id: p08_03_review_gate
workflow_id: phase8

# Gate 状态
status: pending  # pending | approved | rejected | revised

# 决策信息
decided_by: null
decided_at: null
option: null
comment: ""

# 审批清单
checklist:
  - item: "需求是否覆盖？"
    ok: null
    note: ""
  - item: "风险是否列出？"
    ok: null
    note: ""
  - item: "是否有验收标准？"
    ok: null
    note: ""

# 审批人配置
approvers:
  - role: pm
    name: null
  - role: architect
    name: null

# 上游产物（自动填充）
upstream_artifacts:
  - step_id: p08_02_proposal
    path: dev/phase8/output/proposal.md
    summary: ""

# 决策历史
history:
  - version: 1
    status: pending
    decided_by: null
    decided_at: null
    comment: "初始创建"
```

---

## 6. 故障排查

### 问题 1: PM agent 假设 gate 已通过

**症状**: PM agent 继续执行依赖 gate 的步骤

**原因**: PM agent 没有正确检查 gate 状态

**解决**:
1. 确保 PM_AGENT_PROTOCOL.md 中的约束已明确说明
2. 在 PM agent 的 system prompt 中强调：
   - 必须等待 gate 显示 completed 状态
   - 不能假设或推断 gate 状态

### 问题 2: Gate 决策不生效

**症状**: Gate 会话提交决策后，PM 会话看不到更新

**原因**: State 文件没有正确更新

**解决**:
1. 检查 `api_gate_decide` 是否正确更新了 state.yaml
2. 确保 PM agent 调用 `api_get_state` 时读取的是最新 state

### 问题 3: 工具调用混乱

**症状**: PM agent 调用了 gate 工具

**原因**: 工具配置没有正确隔离

**解决**:
1. 确保两个会话的工具配置完全不重叠
2. 在 system prompt 中明确说明哪些工具可用/不可用

---

## 7. 验证清单

部署前验证：

- [ ] PM 会话只有 PM API 工具
- [ ] Gate 会话只有 Gate API 工具
- [ ] PM Agent 协议包含 human gate 约束
- [ ] Gate Assistant 协议包含权限约束
- [ ] orchestrator 正确处理 human_gate 步骤
- [ ] gate 决策文件结构正确
- [ ] state 正确更新 gate 状态
- [ ] 两个会话共享同一个 project_dir

---

## 8. 下一步

1. 在 Claude Code 中创建两个独立会话
2. 配置各自的工具和 system prompt
3. 测试一个包含 human gate 的 workflow
4. 验证安全机制有效

---

**文档版本**: v1.0
**最后更新**: 2025-01-23
