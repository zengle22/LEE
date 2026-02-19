---
title: Commit Planning Fix Summary
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# Commit Planning Fix Summary

## 问题描述

在 workspace-cleanup 工作流中，s5_1_plan_commits 步骤原本应该只**规划**提交，但实际上它执行了提交操作，导致在人工审核（s5_2）之前就已经完成了提交。

### 错误的流程
```
s3_1_organize_docs (修改文件)
    ↓
s4_1_review_code_docs (审查，只读)
    ↓
s5_1_plan_commits (规划提交) ❌ 实际上执行了提交！
    ↓
s5_2_review_commits (人工审核) ⚠️  但提交已经完成了
    ↓
s5_3_execute_commits (执行提交) ⚠️  无事可做
```

### 正确的流程
```
s3_1_organize_docs (修改文件)
    ↓
s4_1_review_code_docs (审查，只读)
    ↓
s5_1_plan_commits (✅ 仅规划，生成 commit-plan.yaml)
    ↓
s5_2_review_commits (✅ 人工审核提交计划)
    ↓
s5_3_execute_commits (✅ 执行已批准的提交)
```

## 根本原因

`agent.office.git_atomic_committer` 的提交流程有 4 个阶段：
1. 分析更改
2. 分组规划
3. 生成提交信息
4. **执行提交** ← 问题在这里

在 s5_1_plan_commits 步骤中，agent 执行了所有 4 个阶段，包括第 4 阶段的执行提交。

## 解决方案

### 1. Agent 支持两种模式

修改 `agent.office.git_atomic_committer` 支持两种工作模式：

#### Plan 模式 (规划)
- 分析工作区更改（git status, git diff）
- 分组相关更改
- 规划原子化提交
- **生成提交计划文件** (commit-plan.yaml)
- **不执行任何 git commit**

#### Execute 模式 (执行)
- 读取提交计划文件
- 按顺序执行规划的提交
- 记录实际提交 ID

### 2. 修改的文件

#### `spec-global/departments/office/agents/git-atomic-committer/v1/agent.yaml`

**添加 mode 参数：**
```yaml
input_schema:
  properties:
    mode:
      type: string
      enum: [plan, execute]
      description: "模式：plan=仅规划不执行, execute=执行提交"
      default: "plan"
    commit_plan:
      type: string
      description: "执行模式下的提交计划文件路径"
```

**更新系统提示词：**
```yaml
prompting:
  system: |
    {% if mode == "plan" %}
    PLANNING MODE - Your responsibilities:
    1. Analyze changes in the workspace
    2. Group related changes together
    3. Plan atomic commits
    4. Generate commit plan YAML file
    5. DO NOT execute any git commits
    {% else %}
    EXECUTION MODE - Your responsibilities:
    1. Read the commit plan file
    2. Execute each commit in order
    3. Record actual commit IDs
    {% endif %}
```

**更新提交流程：**
```yaml
commit_workflow:
  plan_mode:
    stages:
      - 分析更改
      - 分组规划
      - 生成提交信息
      - 生成计划文件 ← 不执行提交

  execute_mode:
    stages:
      - 读取计划
      - 执行提交
      - 记录结果
```

#### `spec-global/departments/office/workflows/workspace-cleanup/v1/workflow.yaml`

**s5_1 传入 mode: plan：**
```yaml
- id: s5_1_plan_commits
  name: "规划提交"
  run: agent.office.git_atomic_committer
  inputs:
    - workspace_path: "{{ params.workspace_path }}"
    - mode: "plan"  # ← 仅规划
  outputs:
    - path: "workspace-cleanup/commit-plan.yaml"
```

**s5_3 传入 mode: execute：**
```yaml
- id: s5_3_execute_commits
  name: "执行提交"
  run: agent.office.git_atomic_committer
  inputs:
    - workspace_path: "{{ params.workspace_path }}"
    - mode: "execute"  # ← 执行模式
    - commit_plan: "workspace-cleanup/commit-plan.yaml"
  outputs:
    - path: "workspace-cleanup/commit-history.yaml"
```

## 验证

修复后的流程：
1. s5_1_plan_commits 运行时，只会生成 `commit-plan.yaml`，不执行 git commit
2. s5_2_review_commits 人工审核计划文件
3. s5_3_execute_commits 根据批准的计划执行实际的 git commit

## 影响

- ✅ 人工审核在提交执行前进行
- ✅ 提交计划可以被修改或拒绝
- ✅ 拒绝后返回 s5_1 重新规划（不会回到 s4）
- ✅ 符合"先规划，后执行"的最佳实践

## 相关文档

- 工作流定义：`spec-global/departments/office/workflows/workspace-cleanup/v1/workflow.yaml`
- Agent 定义：`spec-global/departments/office/agents/git-atomic-committer/v1/agent.yaml`
- 门禁管理：`GATE_MANAGEMENT_GUIDE.md`
