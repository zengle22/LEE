# Development Pipeline Enforcement Mechanism

## 问题背景

workflow.yaml 定义了完整的流程规范，但没有运行时强制执行机制。这导致：
- Agent 编排可能被跳过
- 人类门禁可能被忽略
- 产物验证可能被遗漏
- 执行日志可能不完整

## 解决方案：状态驱动 + Hooks 强制

### 1. 执行状态文件 (execution-state.yaml)

每个项目维护一个执行状态文件，记录当前执行进度：

```yaml
# {project}/execution-state.yaml
version: 1.0
workflow_id: workflow.dev.development_pipeline
project_id: ai-marathon-coach
started_at: 2026-01-09T10:00:00Z

current_phase:
  id: phase_2_auth
  status: in_progress
  started_at: 2026-01-09T14:00:00Z

completed_phases:
  - id: phase_1_foundation
    status: completed
    completed_at: 2026-01-09T13:00:00Z
    execution_log: logs/phase_1_execution.json
    validation_status: passed

current_step:
  id: s3_2_1_scheduler_start
  agent_id: agent.dev.development_scheduler
  status: in_progress
  started_at: 2026-01-09T14:30:00Z

pending_gates:
  - gate_id: h1_plan_review
    status: approved
    approved_at: 2026-01-09T11:00:00Z
    approver: human
  - gate_id: h2_integration_review
    status: pending  # 阻断点！

blocked_reason: null  # 或 "等待 h2_integration_review 审批"
```

### 2. Claude Code Hooks 配置

在项目根目录添加 `.claude/settings.json` 或使用 Claude Code hooks：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "command": "python scripts/workflow-guard.py check-state"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "python scripts/workflow-guard.py update-state"
      }
    ]
  }
}
```

### 3. workflow-guard.py 核心逻辑

```python
#!/usr/bin/env python3
"""
Workflow Guard - 流程执行保障脚本

功能：
1. 检查当前执行状态是否允许操作
2. 验证人类门禁是否已通过
3. 更新执行状态
4. 生成执行日志
"""

import yaml
import json
import sys
from pathlib import Path
from datetime import datetime

STATE_FILE = "execution-state.yaml"
WORKFLOW_FILE = "ai-spec/specs/org/development/workflows/development-pipeline/v1/workflow.yaml"

def load_state():
    if not Path(STATE_FILE).exists():
        return None
    with open(STATE_FILE) as f:
        return yaml.safe_load(f)

def load_workflow():
    with open(WORKFLOW_FILE) as f:
        return yaml.safe_load(f)

def check_human_gate(state, workflow):
    """检查是否有未通过的人类门禁阻断执行"""
    pending_gates = state.get("pending_gates", [])
    for gate in pending_gates:
        if gate["status"] == "pending":
            gate_def = find_gate_definition(workflow, gate["gate_id"])
            if gate_def and gate_def.get("gate", {}).get("blocking", True):
                return False, f"执行被阻断: 等待 {gate['gate_id']} 审批"
    return True, None

def check_phase_dependencies(state, workflow):
    """检查当前 Phase 的依赖是否满足"""
    current_phase = state.get("current_phase", {})
    # 检查依赖的 Phase 是否已完成
    # ...
    return True, None

def validate_output_artifacts(state, workflow):
    """验证上一步的产物是否符合契约"""
    # 读取 output_validation 配置
    # 执行 JSON Schema 验证
    # ...
    return True, []

def check_state(args):
    """Pre-hook: 检查是否允许执行"""
    state = load_state()
    if state is None:
        print("WARNING: 未找到 execution-state.yaml，流程状态未初始化")
        return 0  # 允许继续，但警告

    workflow = load_workflow()

    # 检查人类门禁
    ok, reason = check_human_gate(state, workflow)
    if not ok:
        print(f"BLOCKED: {reason}")
        print("请先完成人类审批后再继续执行")
        return 1  # 阻断执行

    # 检查 Phase 依赖
    ok, reason = check_phase_dependencies(state, workflow)
    if not ok:
        print(f"BLOCKED: {reason}")
        return 1

    return 0

def update_state(args):
    """Post-hook: 更新执行状态"""
    state = load_state()
    if state is None:
        return 0

    # 记录执行日志
    # 更新 current_step
    # 检查是否触发人类门禁
    # ...

    with open(STATE_FILE, 'w') as f:
        yaml.dump(state, f, allow_unicode=True)

    return 0

def approve_gate(gate_id):
    """人类审批门禁"""
    state = load_state()
    for gate in state.get("pending_gates", []):
        if gate["gate_id"] == gate_id:
            gate["status"] = "approved"
            gate["approved_at"] = datetime.now().isoformat()
            gate["approver"] = "human"
            break

    with open(STATE_FILE, 'w') as f:
        yaml.dump(state, f, allow_unicode=True)

    print(f"✅ Gate {gate_id} approved")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check-state"
    if cmd == "check-state":
        sys.exit(check_state(sys.argv[2:]))
    elif cmd == "update-state":
        sys.exit(update_state(sys.argv[2:]))
    elif cmd == "approve":
        approve_gate(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
```

### 4. 人类门禁交互流程

```
┌─────────────────────────────────────────────────────────────┐
│                    人类门禁触发流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Agent 完成步骤，触发 human_gate                         │
│     ┌─────────────┐                                        │
│     │ Step 完成   │                                        │
│     │ human_gate: │                                        │
│     │ h1_plan_rev │                                        │
│     └──────┬──────┘                                        │
│            │                                                │
│            ▼                                                │
│  2. workflow-guard 更新状态，标记门禁 pending               │
│     ┌─────────────┐                                        │
│     │ pending_    │                                        │
│     │ gates:      │                                        │
│     │ - h1: pend  │                                        │
│     └──────┬──────┘                                        │
│            │                                                │
│            ▼                                                │
│  3. 后续操作被阻断                                          │
│     ┌─────────────┐                                        │
│     │ BLOCKED:    │                                        │
│     │ 等待审批    │                                        │
│     └──────┬──────┘                                        │
│            │                                                │
│            ▼                                                │
│  4. 人类执行审批命令                                        │
│     ┌─────────────────────────────────────┐                │
│     │ $ python scripts/workflow-guard.py  │                │
│     │   approve h1_plan_review            │                │
│     └──────┬──────────────────────────────┘                │
│            │                                                │
│            ▼                                                │
│  5. 状态更新，执行继续                                      │
│     ┌─────────────┐                                        │
│     │ ✅ Gate     │                                        │
│     │ approved    │                                        │
│     └─────────────┘                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5. Pre-commit 验证

```bash
# .git/hooks/pre-commit
#!/bin/bash

# 验证执行状态
python scripts/workflow-guard.py validate-commit

# 验证产物契约
python scripts/contract-validator.py check-outputs

# 验证执行日志
python scripts/workflow-guard.py check-logs
```

## 实施步骤

1. **创建 scripts/workflow-guard.py** - 核心状态管理脚本
2. **初始化 execution-state.yaml** - 项目级执行状态
3. **配置 Claude Code hooks** - 在 CLAUDE.md 或 settings 中配置
4. **配置 pre-commit hooks** - 提交前验证

## 限制与权衡

| 机制 | 优点 | 限制 |
|------|------|------|
| 状态文件 | 简单、可追溯 | 需要手动维护 |
| Hooks | 自动化程度高 | Claude Code 支持有限 |
| Pre-commit | 阻断不合规提交 | 不能阻断执行过程 |

## 推荐的最小可行方案

1. **execution-state.yaml** - 强制每个项目维护
2. **approve 命令** - 人类门禁审批入口
3. **CLAUDE.md 指令** - 要求 Claude 在执行前检查状态文件
4. **Pre-commit 验证** - 确保提交时状态合法

这样可以在不开发完整 Runtime 的情况下，实现基本的流程保障。
