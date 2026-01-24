# Human Gate 快速参考

> 快速查阅 Human Gate 的使用方法、API 和最佳实践

---

## 🔑 核心概念

**Human Gate** 是 workflow 中需要人工审批的步骤，AI 无法自动通过。

**关键特点**:
- AI 不能修改 gate 状态
- 只能在 Gate 会话中审批
- 决策记录在独立的 YAML 文件中

---

## 📁 文件位置

### Gate 决策文件
```
{project_dir}/.workflow/gates/{gate_id}.yaml
```

### State 文件
```
{project_dir}/.workflow/state.yaml
```

---

## 🛠️ API 快速参考

### PM Agent API (只读)

```python
from flowcore.api import api_get_state, api_list_ready_steps, api_run_step_async

# 获取状态
state = api_get_state(project_dir)

# 列出就绪步骤
ready = api_list_ready_steps(project_dir)

# 执行步骤（异步）
result = await api_run_step_async(project_dir, step_id)
```

### Gate Assistant API (可写)

```python
from flowcore.api import api_gate_list_pending, api_gate_show, api_gate_decide

# 列出待审批 gate
pending = api_gate_list_pending(project_dir)

# 显示 gate 详情
detail = api_gate_show(project_dir, "gate_id")

# 提交决策
result = api_gate_decide(
    project_dir=project_dir,
    gate_id="gate_id",
    option="approve",  # approve | reject | revise
    comment="决策说明",
    checklist=[
        {"item": "检查项1", "ok": True},
        {"item": "检查项2", "ok": True}
    ],
    decided_by="user_name"
)
```

---

## 📋 Gate 决策文件结构

```yaml
gate_id: my_gate
status: pending  # pending | approved | rejected | revised

decided_by: null
decided_at: null
option: null
comment: ""

checklist:
  - item: "检查项名称"
    ok: null  # true | false | null
    note: ""

upstream_artifacts:
  - step_id: upstream_step
    path: path/to/artifact
    summary: ""

history:
  - version: 1
    status: pending
    decided_by: null
    decided_at: null
    comment: ""
```

---

## 🔄 标准流程

### PM 会话流程

```python
# 1. 执行步骤直到遇到 gate
result = await api_run_step_async(project_dir, "step1")

# 2. 检查状态
state = api_get_state(project_dir)

# 3. 发现 pending human gate
for step_id, step_data in state["steps"].items():
    if step_data["kind"] == "human_gate" and step_data["status"] == "pending_human":
        print(f"⚠️ 需要审批: {step_id}")
        print("请切换到 Gate 会话完成审批")
```

### Gate 会话流程

```python
# 1. 列出 pending gates
pending = api_gate_list_pending(project_dir)

# 2. 显示 gate 详情
detail = api_gate_show(project_dir, "gate_id")
print(f"Checklist: {detail['checklist']}")
print(f"Artifacts: {detail['upstream_artifacts']}")

# 3. 提交决策（用户确认后）
result = api_gate_decide(
    project_dir=project_dir,
    gate_id="gate_id",
    option="approve",
    comment="批准",
    decided_by="user"
)
```

---

## 🔒 安全规则

### ❌ PM Agent 不能做

- 调用 `api_gate_*` 函数
- 修改 gate YAML 文件
- 假设 gate 已通过
- 继续执行依赖 gate 的步骤

### ❌ Gate Assistant 不能做

- 未经人类确认调用 `api_gate_decide`
- 使用默认 `decided_by` 值
- 伪造决策

### ✅ 正确做法

- PM 只能**检查** gate 状态
- Gate 只能**等待人类明确表达**后提交
- 所有决策必须有真实的 `decided_by`

---

## 📝 示例对话

### PM 会话遇到 Gate

**PM Agent**:
> 当前阻塞在 human gate: `code_review_gate`
>
> **决策文件**: `{project}/.workflow/gates/code_review_gate.yaml`
>
> **审批清单**:
> - 代码是否符合规范？
> - 是否包含注释？
> - 测试覆盖率是否足够？
>
> **请切换到 Gate 会话完成审批**

### Gate 会话审批

**人类**: 有哪些 pending gate？

**Gate Assistant**: [调用 list_pending]
> 当前有 1 个 pending gate:
> - `code_review_gate`: 代码评审

**人类**: 展开这个 gate

**Gate Assistant**: [调用 show]
> **详情**:
> - Checklist:
>   1. [ ] 代码是否符合规范？
>   2. [ ] 是否包含注释？
>   3. [ ] 测试覆盖率是否足够？
>
> **建议**: 代码质量良好，建议批准

**人类**: 批准

**Gate Assistant**: [调用 decide]
> ✅ 已提交决策: approved by user

---

## 🎯 状态转换

```
pending → approved   # 人类批准
pending → rejected   # 人类拒绝
pending → revised    # 人类要求修改

任何状态 → pending   # 可以重新审批
```

---

## 🚨 常见问题

### Q: PM Agent 绕过了 gate？
**A**: 检查是否正确隔离了工具。PM 会话不应该有 gate 工具。

### Q: Gate 决策不生效？
**A**: 检查：
1. `decided_by` 是否为空
2. `comment` 是否为空
3. gate 文件是否正确写入

### Q: 如何重新审批？
**A**: 修改 gate 文件的 `status` 为 `pending`，或使用新版本的决策。

---

## 📚 完整文档

- **规范**: `docs/HUMAN-GATE-SPEC.md`
- **PM 协议**: `docs/PM_AGENT_PROTOCOL.md`
- **Gate 协议**: `docs/GATE_ASSISTANT_PROTOCOL.md`
- **集成指南**: `docs/CLAUDE-INTEGRATION.md`
- **实现报告**: `docs/HUMAN-GATE-IMPLEMENTATION.md`

---

**版本**: v1.0
**更新**: 2025-01-23
