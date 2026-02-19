---
title: Human Gate 决策文件模板
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Human Gate 决策文件模板

此模板定义了 human gate 的决策文件结构。

---

## 文件位置

```
{project_dir}/.workflow/gates/{gate_id}.yaml
```

---

## 文件结构

```yaml
# Gate 基本信息
gate_id: p08_04_review_gate
step_id: p08_04_review_gate
workflow_id: phase8
project_dir: dev/phase8

# Gate 状态
# - pending: 等待审批
# - approved: 已批准
# - rejected: 已拒绝
# - revised: 要求修改
status: pending

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
  - item: "是否有可执行的验收标准？"
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
  - step_id: p08_02_requirements
    path: dev/phase8/output/requirements.md
    summary: ""

# 决策历史（保留所有修订）
history:
  - version: 1
    status: pending
    decided_by: null
    decided_at: null
    comment: "初始创建"
```

---

## 状态转换规则

```
pending → approved   # 人类批准
pending → rejected   # 人类拒绝
pending → revised    # 人类要求修改

任何状态 → pending   # 可以重新审批（创建新版本）
```

---

## 权限控制

1. **只有人类可以修改决策文件**
   - PM agent 不能调用 gate_decide
   - PM agent 不能直接编辑 gate 文件
   - 只有 Gate 会话的工具可以修改

2. **必需字段验证**
   - `decided_by` 不能为空
   - `option` 必须是 approve/reject/revise 之一
   - `comment` 不能为空

3. **审计要求**
   - 每次状态变更都记录在 history 中
   - 保留完整的决策链路

---

## 与 Orchestrator 的集成

### Orchestrator 读取 gate 状态

```python
def is_gate_completed(gate_id: str) -> bool:
    gate_file = f"{project_dir}/.workflow/gates/{gate_id}.yaml"
    gate_data = load_yaml(gate_file)
    return gate_data["status"] in ["approved", "rejected"]
```

### Orchestrator 更新 step 状态

```python
def update_human_gate_step(step_id: str):
    gate_file = f"{project_dir}/.workflow/gates/{step_id}.yaml"
    gate_data = load_yaml(gate_file)

    if gate_data["status"] in ["approved", "rejected"]:
        mark_step_completed(step_id)
        outputs = [gate_file]
    else:
        mark_step_pending_human(step_id)
```

---

## CLI 工具接口

### 列出 pending gates
```bash
flow gate list ./project
```

### 显示 gate 详情
```bash
flow gate show ./project p08_04_review_gate
```

### 提交决策
```bash
flow gate decide ./project p08_04_review_gate \
  --option approve \
  --by lezeng \
  --comment "方案可行，批准推进" \
  --checklist item1=true item2=true item3=true
```

---

## PM Agent 与 Gate 的关系

### PM Agent 可以做的事
- 查看 gate 状态（通过 orchestrator_get_state）
- 识别 pending human gate
- 提示人类去 Gate 会话审批
- 总结上下文，生成评审建议

### PM Agent 不可以做的事
- 直接调用 gate_decide
- 修改 gate 文件
- 假设 gate 已通过而继续执行后续步骤
- 声称 gate 状态

### Gate Assistant 可以做的事
- 调用 gate_list_pending
- 调用 gate_show
- 在人类明确指示后调用 gate_decide
- 生成评审建议

### Gate Assistant 不可以做的事
- 在人类未明确表达时调用 gate_decide
- 伪造 decided_by 字段
- 通过其他方式修改 gate 状态
