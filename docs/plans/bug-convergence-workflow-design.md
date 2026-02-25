# LEE 研发/测试闭环工作流设计方案（基于现有架构）

## Context

基于用户提供的需求和现有 LEE 架构深度分析，需要设计一套完整的研发/测试闭环工作流系统，支持 LEE Chat 和 CLI 双入口。

**核心发现：LEE 已有完整的跨工作流循环控制器**

通过代码探索发现，LEE 已经实现了 `CrossWorkflowLoopController`，这是专门用于 L2 层管理 QA-L3 ↔ Dev-L3 乒乓循环的控制器，完全满足用户需求。

**核心需求**：
1. 实现 **L1/L2/L3 分层架构**的串行 QA → Dev → QA 循环
2. **文件驱动 + Git 追踪**的消息传递机制（bug_set.yaml 作为消息载体）
3. 支持通过 **Chat 和 CLI** 触发和监控工作流
4. 完整的**版本级验收报告**输出
5. **生产就绪**：错误处理、重试、超时、回滚机制

**现有可复用资产**：
- ✅ `CrossWorkflowLoopController` - L3 跨工作流收敛循环控制器
- ✅ `SubworkflowMixin` - 子工作流 spawn/执行/回填
- ✅ 完整的 Bug 契约系统（`spec-global/departments/qa/contracts/bug-contract/v1/`）
- ✅ 测试计划/用例契约（`test-plan`, `test-case`, `test-suite`）
- ✅ Orchestrator 执行引擎和状态机
- ✅ Human Gate 审批机制（`human_approval.py`, `gate_engine.py`）
- ✅ PM workflow Chat REPL 和 CLI 命令框架
- ✅ WorktreeManager 和 RepoRegistry（仓库隔离）
- ✅ IR 模型（`CrossWorkflowLoopIR`, `CrossWorkflowLoopPhaseIR`, `CrossWorkflowLoopConvergenceIR`）

**设计原则**：
- 优先复用现有实现，避免重复开发
- L1/L2/L3 作为一级模块显式区分
- Git 追踪 Bug Set（单一文件 `bug_set.yaml`，通过 commit 历史追溯）
- 关键节点审批（QA 结束、Dev 结束、最终发布）
- 生产就绪特性

---

## 架构设计

### 0. 现有架构分析

**LEE 已实现的跨工作流循环机制**（位于 `src/lee/orchestrator/execution/cross_workflow_loop.py`）：

```
CrossWorkflowLoopController 的能力：
├─ 循环控制：while should_continue() { phase → record → advance }
├─ 收敛判定：三层（主条件、辅助条件、最大轮次）
├─ 状态管理：CrossWorkflowLoopState（round, phase_idx, status, bug_counts）
├─ 上下文注入：get_loop_context() 注入子工作流
├─ 证据记录：write_round_evidence() 记录每轮结果
└─ 趋势分析：bug_counts 趋势追踪

YAML 配置格式（已定义在 IR 模型中）：
cross_workflow_loop:
  enabled: true
  max_rounds: 5
  phases:
    - id: qa_test
      workflow_ref: workflow.qa.test_plan_execution_v1
      role: tester
    - id: dev_fix
      workflow_ref: workflow.dev.bug_fix
      role: fixer
      condition: "qa_test.exit_decision == 'fail'"
  convergence:
    check_phase: qa_test
    check_field: exit_decision
    pass_values: [pass]
    secondary_check: "open_bug_count == 0"
  on_exceeded:
    action: human_gate
```

### 1. 分层架构设计（基于现有实现）

```
┌─────────────────────────────────────────────────────────────┐
│ L1: bug-convergence-cycle (项目级)                           │
│ 位置: spec-global/projects/running-master/workflows/...     │
│                                                              │
│ 职责：版本级收敛协调，产出验收报告                            │
│ 输入：convergence-input.yaml                                │
│ 输出：convergence-report.yaml                                │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼──────────────────────────────┐  ┌─────▼──────────────────────────────┐
│ L2: qa/test-cycle (QA-L2)            │  │ L2: dev/bugfix-cycle (Dev-L2)     │
│ 位置: spec-global/departments/qa/... │  │ 位置: spec-global/departments/dev/ │
│                                      │  │                                      │
│ 使用 CrossWorkflowLoopController:     │  │ 使用 CrossWorkflowLoopController:    │
│ ┌─────────────────────────────────┐  │  │ ┌────────────────────────────────┐  │
│ │ Phase 1: run_test_suites        │  │  │ │ Phase 1: load_bug_set         │  │
│ │   → spawn QA-L3 (多个并行)      │  │  │ │ Phase 2: prioritize_bugs      │  │
│ │   → 汇总结果                    │  │  │ │   → spawn Dev-L3 (多个并行)  │  │
│ │ Phase 2: generate_bug_set       │  │  │ │ Phase 3: verify_fixes         │  │
│ │   → 生成 bug_set.yaml           │  │  │ │   → 更新 bug_set.yaml         │  │
│ │   → Git commit                  │  │  │ │   → Git commit                │  │
│ │ Phase 3: qa_summary_gate        │  │  │ │ Phase 4: dev_summary_gate     │  │
│ │   → 人工审批（可选）            │  │  │ │   → 人工审批（可选）          │  │
│ └─────────────────────────────────┘  │  │ └────────────────────────────────┘  │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
        │                                       │
        └───────────┬───────────────────────────┘
                    │ File: bug_set.yaml (Git 追踪)
                    │ 位置: qa/bugsets/bug_set.yaml
                    │
        ┌───────────▼───────────────────────────┐
        │ L3: 任务级工作流（已存在/需新建）      │
        ├───────────────────────────────────────┤
        │ 已存在:                               │
        │ • workflow.qa.test_plan_execution_v1  │
        │ • workflow.dev.feature_*_l3          │
        │                                       │
        │ 需新建:                               │
        │ • qa/execute-test-suite              │
        │ • dev/fix-single-bug                 │
        └───────────────────────────────────────┘
```

### 2. 关键设计决策

#### 2.1 复用 CrossWorkflowLoopController

**不需要重新实现循环控制**，直接使用现有的 `CrossWorkflowLoopController`：

- QA-L2 和 Dev-L2 各自使用独立的 `CrossWorkflowLoopController`
- 通过 `cross_workflow_loop` 配置定义 phases
- L1 负责协调 QA-L2 和 Dev-L2 的串行执行

#### 2.2 Git 追踪 Bug Set

**单一文件 + Git 追踪**模式：
- 文件路径：`qa/bugsets/bug_set.yaml`（始终单一文件名）
- 每次更新：`git add && git commit` 自动提交
- 追溯历史：通过 `git log` 和 `git diff` 查看变更
- 标签管理：`git tag bugset-cycle-N` 标记每轮

#### 2.3 三级人工 Gate

**关键节点审批**：
1. **QA 循环结束 gate**：确认 bug_set 准确性
2. **Dev 循环结束 gate**：确认修复质量
3. **最终发布 gate**：版本级验收

**自动批准条件**（可配置）：
- P0/P1 bug 清零时自动通过 QA gate
- 所有目标 bug 修复完成时自动通过 Dev gate

#### 2.4 L1 协调器实现

**混合模式**：L1 作为 coordinator，不使用显式 while 循环，而是：
1. 执行 QA-L2（内部可能有 L3 循环）
2. 检查收敛条件
3. 如果未收敛，执行 Dev-L2（内部可能有 L3 循环）
4. 回到步骤 1，直到收敛或超限

### 2. 关键文件约定

#### 2.1 L1 输入: `convergence-input.yaml`

位置: `spec-global/projects/running-master/workflows/bug-convergence-cycle/v1/`

```yaml
project: "running-master"
version: "MVP-0.5"

context:
  prd_spec_file: "product/prd/mvp-0.5.md"
  owner: "pm.le"
  created_at: "2026-02-24"

code:
  repos:
    backend: "git@github.com:lee/rm-backend.git"
    frontend: "git@github.com:lee/rm-frontend.git"
  base_branch: "release/mvp-0.5"
  start_commit: "abc123"

environments:
  dev_env_descriptor: "infra/env/dev-mvp-0.5.yaml"
  test_env_descriptor: "infra/env/test-mvp-0.5.yaml"

testing:
  test_plan_file: "qa/plans/mvp-0.5-plan.yaml"
  test_set_root: "qa/testsuites/mvp-0.5/"
  coverage_expectation:
    must_cover_tags:
      - "core-flow"
      - "payment"
      - "training-plan"
    allow_skip_tags:
      - "abtest"

strategy:
  max_iterations: 5
  converge_threshold:
    max_p0_p1: 0
    max_open_bugs: 10
  require_full_regression_before_done: true
```

#### 2.2 L2 传递文件: `bug_set_N.yaml`

位置: `qa/bugsets/`

```yaml
meta:
  bug_set_id: "BUGSET-2026-001"
  cycle_id: "cycle-2026-02-24-01"
  version: "MVP-0.5"
  commit: "abc123"
  generated_at: "2026-02-24T10:00:00Z"

bugs:
  - bug_id: "BUG-2026-0031"
    title: "登录后首页接口返回 500"
    severity: P0
    category: functional
    status: open
    detected_in:
      test_suite: "e2e-chrome"
      test_case_id: "F-P1-001"
    evidence:
      screenshots: ["screenshots/bug-31-1.png"]
      logs_hint: ["api-gateway", "home-service"]

summary:
  total_bugs: 15
  by_severity:
    P0: 2
    P1: 5
    P2: 6
    P3: 2
  by_module:
    login: 3
    payment: 5
    training: 7
```

#### 2.3 Dev 修复后: `bug_set_N_fixed.yaml`

```yaml
# 基于原 bug_set_N.yaml，更新状态
bugs:
  - bug_id: "BUG-2026-0031"
    status: fixed_pending_verify
    fix:
      fix_commit: "def456"
      fix_version: "MVP-0.5-rc2"
      change_summary: "增加缓存预热逻辑"

  # ... 其他 bugs

summary:
  total_fixed: 10
  total_deferred: 3
  total_wontfix: 2
  remaining_open: 0
```

#### 2.4 L1 输出: `convergence-report.yaml`

位置: `reports/running-master/mvp-0.5/`

```yaml
project: "running-master"
version: "MVP-0.5"
status: "converged"

summary:
  total_iterations: 3
  final_commit: "xyz789"
  total_bugs_found: 73
  total_bugs_closed: 65
  remaining_bugs: 8
  remaining_p0_p1: 0

decision:
  release_ready: true
  approved_by: "human.gate.ceo"
  approved_at: "2026-02-28"

links:
  bug_sets:
    - "qa/bugsets/bug_set_01.yaml"
    - "qa/bugsets/bug_set_02.yaml"
    - "qa/bugsets/bug_set_03.yaml"
  qa_summaries:
    - "qa/cycles/cycle-01-summary.yaml"
    - "qa/cycles/cycle-02-summary.yaml"
  dev_summaries:
    - "dev/cycles/dev-01-summary.yaml"
    - "dev/cycles/dev-02-summary.yaml"
```

### 3. 消息驱动机制

```
qa/inbox/
  └── cycle-2026-02-24-01-input.yaml    # L1 → QA-L2

qa/outbox/
  ├── cycle-2026-02-24-01-summary.yaml   # QA-L2 → L1
  └── bug_set_01.yaml                    # QA-L2 → Dev-L2

dev/inbox/
  └── bug_set_01.yaml                    # (从 qa/outbox 复制)

dev/outbox/
  ├── bug_set_01_fixed.yaml              # Dev-L2 → QA-L2
  └── dev-cycle-01-summary.yaml          # Dev-L2 → L1
```

---

## 详细实现计划

### Phase 1: 新增契约定义（最小化）

只需创建少量新契约，复用现有 Bug 契约。

**新增契约**：
1. `spec-global/contracts/bug-set/v1/schema.yaml` - Bug 集合契约（新建）
2. `spec-global/contracts/convergence-input/v1/schema.yaml` - L1 输入契约（新建）
3. `spec-global/contracts/convergence-report/v1/schema.yaml` - L1 输出契约（新建）

**复用现有契约**：
- `spec-global/departments/qa/contracts/bug-contract/v1/schema.yaml` - 单个 Bug 契约
- `spec-global/departments/qa/contracts/test-round/v1/schema.yaml` - 测试轮次契约

### Phase 2: L3 工作流（复用和新建）

**复用现有 L3**：
- `workflow.qa.test_plan_execution_v1` - 已存在的 QA 测试执行 L3

**新建 L3**：
1. `qa/execute-test-suite` - 执行单个测试套件（如果需要更细粒度）
2. `dev/fix-single-bug` - 修复单个 bug（需要新建）

### Phase 3: L2 工作流（核心实现）

使用 **CrossWorkflowLoopController** 实现 QA-L2 和 Dev-L2。

#### QA-L2: `test-cycle`

位置: `spec-global/departments/qa/workflows/test-cycle/v1/workflow.yaml`

```yaml
kind: workflow
version: "1.0"
id: workflow.qa.test_cycle
name: QA Test Cycle (L2)
level: department
department: qa
description: >
  QA 测试循环，使用 CrossWorkflowLoopController 管理 L3 循环。
  Phase 1: 执行测试套件
  Phase 2: 生成 Bug Set 并提交 Git

stages:
  - id: test_execution_stage
    name: "测试执行与 Bug 生成"
    steps:
      - id: qa_loop_step
        name: "QA 跨工作流循环"
        type: sub_workflow
        run: workflow.qa.test_plan_execution_v1  # 复用现有 L3

        # 使用 CrossWorkflowLoopController
        cross_workflow_loop:
          enabled: true
          max_rounds: 1  # QA-L2 只执行一轮测试
          phases:
            - id: run_tests
              workflow_ref: workflow.qa.test_plan_execution_v1
              role: tester
          convergence:
            check_phase: run_tests
            check_field: exit_decision
            pass_values: [pass, conditional_pass]

  - id: bug_set_generation_stage
    name: "Bug Set 生成与 Git 提交"
    dependencies:
      requires: [qa_loop_step]
    steps:
      - id: generate_bug_set
        name: "生成 Bug Set"
        type: skill
        run: skill.qa.generate_bug_set_from_results

      - id: git_commit_bug_set
        name: "提交 Bug Set 到 Git"
        type: skill
        run: skill.git.commit_file
        inputs:
          file_path: "qa/bugsets/bug_set.yaml"
          commit_message: "Bug set update: cycle-{round}, action-{action}"

  - id: qa_summary_gate_stage
    name: "QA 摘要与审批"
    dependencies:
      requires: [git_commit_bug_set]
    steps:
      - id: qa_summary
        name: "生成 QA 循环摘要"
        type: agent
        run: agent.qa.reporter

      - id: qa_completion_gate
        name: "QA 完成审批"
        type: gate
        gate_ref: gate.qa.cycle_completion
        auto_approve_when:
          - "bug_set.summary.by_severity.P0 == 0"
          - "bug_set.summary.by_severity.P1 == 0"

outputs_contract:
  required:
    - file: "qa/bugsets/bug_set.yaml"
      schema: contracts/bug-set/v1/schema.yaml
    - file: "qa/cycles/qa-cycle-summary.yaml"
      schema: contracts/qa-cycle-summary/v1/schema.yaml
```

#### Dev-L2: `bugfix-cycle`

位置: `spec-global/departments/dev/workflows/bugfix-cycle/v1/workflow.yaml`

```yaml
kind: workflow
version: "1.0"
id: workflow.dev.bugfix_cycle
name: Dev Bugfix Cycle (L2)
level: department
department: dev
description: >
  Dev 修复循环，使用 CrossWorkflowLoopController 管理 L3 循环。
  Phase 1: 加载 Bug Set
  Phase 2: 并行修复 Bugs
  Phase 3: 更新 Bug Set 并提交 Git

stages:
  - id: bug_analysis_stage
    name: "Bug 分析与优先级排序"
    steps:
      - id: load_bug_set
        name: "加载 Bug Set"
        type: skill
        run: skill.dev.load_bug_set
        inputs:
          file_path: "qa/bugsets/bug_set.yaml"

      - id: prioritize_bugs
        name: "Bug 优先级排序"
        type: agent
        run: agent.dev.lead
        inputs:
          bug_set: "$outputs.load_bug_set"
        strategy:
          focus_severity: [P0, P1]
          max_parallel_fixes: 5

  - id: bug_fixing_stage
    name: "Bug 修复循环"
    dependencies:
      requires: [prioritize_bugs]
    steps:
      - id: dev_loop_step
        name: "Dev 跨工作流循环"
        type: sub_workflow
        run: workflow.dev.fix_single_bug

        cross_workflow_loop:
          enabled: true
          max_rounds: 3  # 最多 3 轮修复尝试
          phases:
            - id: fix_bug
              workflow_ref: workflow.dev.fix_single_bug
              role: fixer
              inputs_from:
                - phase: prioritize_bugs
                  field: prioritized_bugs
          convergence:
            check_phase: fix_bug
            check_field: all_fixed
            pass_values: [true]
            secondary_check: "open_bug_count == 0"

  - id: bug_set_update_stage
    name: "Bug Set 更新与 Git 提交"
    dependencies:
      requires: [dev_loop_step]
    steps:
      - id: update_bug_set
        name: "更新 Bug Set 状态"
        type: skill
        run: skill.dev.update_bug_set_statuses

      - id: git_commit_bug_set
        name: "提交更新后的 Bug Set 到 Git"
        type: skill
        run: skill.git.commit_file
        inputs:
          file_path: "qa/bugsets/bug_set.yaml"
          commit_message: "Bug set update: cycle-{round}, {fixed_count} bugs fixed"

  - id: dev_summary_gate_stage
    name: "Dev 摘要与审批"
    dependencies:
      requires: [git_commit_bug_set]
    steps:
      - id: dev_summary
        name: "生成 Dev 循环摘要"
        type: agent
        run: agent.dev.reporter

      - id: dev_completion_gate
        name: "Dev 完成审批"
        type: gate
        gate_ref: gate.dev.cycle_completion
        auto_approve_when:
          - "bug_set.summary.remaining_open == 0"

outputs_contract:
  required:
    - file: "qa/bugsets/bug_set.yaml"
      schema: contracts/bug-set/v1/schema.yaml
    - file: "dev/cycles/dev-cycle-summary.yaml"
      schema: contracts/dev-cycle-summary/v1/schema.yaml
```

### Phase 4: L1 工作流（协调器实现）

L1 不使用 `CrossWorkflowLoopController`（这是给 L2 用的），而是通过简单的 **串行步骤 + 条件分支** 实现协调。

#### L1: `bug-convergence-cycle`

位置: `spec-global/projects/running-master/workflows/bug-convergence-cycle/v1/workflow.yaml`

```yaml
kind: workflow
version: "1.0"
id: workflow.project.bug_convergence_cycle
name: Bug Convergence Cycle (L1)
level: project
description: >
  项目级 Bug 收敛循环协调器。
  管理 QA-L2 和 Dev-L2 的串行执行，直到收敛或达到最大迭代次数。

inputs:
  - path: "convergence-input.yaml"
    schema: contracts/convergence-input/v1/schema.yaml

outputs:
  - path: "convergence-report.yaml"
    schema: contracts/convergence-report/v1/schema.yaml

stages:
  # ========== Stage 1: 初始化 ==========
  - id: initialization_stage
    name: "收敛循环初始化"
    steps:
      - id: load_convergence_config
        name: "加载收敛配置"
        type: skill
        run: skill.pm.load_convergence_input
        inputs:
          input_file: "$inputs.convergence_input_file"

      - id: validate_prerequisites
        name: "验证前置条件"
        type: skill
        run: skill.pm.validate_prerequisites
        inputs:
          convergence_config: "$outputs.load_convergence_config"

  # ========== Stage 2: QA 循环 ==========
  - id: qa_cycle_stage
    name: "QA 测试循环"
    dependencies:
      requires: [validate_prerequisites]
    steps:
      - id: qa_cycle
        name: "执行 QA-L2 循环"
        type: sub_workflow
        run: workflow.qa.test_cycle
        inputs:
          test_plan_file: "$outputs.load_convergence_config.testing.test_plan_file"
          test_set_root: "$outputs.load_convergence_config.testing.test_set_root"
          scope: "full-regression"
        outputs:
          - bug_set
          - qa_summary

  # ========== Stage 3: 收敛检查 ==========
  - id: convergence_check_stage
    name: "收敛条件检查"
    dependencies:
      requires: [qa_cycle]
    steps:
      - id: check_convergence
        name: "检查收敛条件"
        type: skill
        run: skill.pm.check_convergence_criteria
        inputs:
          bug_set: "$outputs.qa_cycle.bug_set"
          threshold: "$outputs.load_convergence_config.strategy.converge_threshold"
          iteration: "$context.iteration"
          max_iterations: "$outputs.load_convergence_config.strategy.max_iterations"
        outputs:
          - converged
          - should_continue

      - id: convergence_decision
        name: "收敛决策"
        type: decision
        dependencies:
          requires: [check_convergence]
        decision_logic: |
          IF converged == true:
            next_stage = finalization_stage
            action = "generate_report"
          ELIF should_continue == false:
            next_stage = finalization_stage
            action = "escalate"
          ELSE:
            next_stage = dev_cycle_stage
            action = "continue_to_dev"

  # ========== Stage 4: Dev 循环（条件执行）==========
  - id: dev_cycle_stage
    name: "Dev 修复循环"
    dependencies:
      requires: [convergence_decision]
    condition: "$convergence_decision.action == 'continue_to_dev'"
    steps:
      - id: dev_cycle
        name: "执行 Dev-L2 循环"
        type: sub_workflow
        run: workflow.dev.bugfix_cycle
        inputs:
          bug_set_file: "$outputs.qa_cycle.bug_set"
          strategy:
            focus_severity: [P0, P1]
            max_parallel_fixes: 5
        outputs:
          - bug_set_fixed
          - dev_summary

      - id: increment_iteration
        name: "递增迭代计数"
        type: skill
        run: skill.pm.increment_iteration
        inputs:
          current_iteration: "$context.iteration"

      - id: loop_back_to_qa
        name: "循环回 QA"
        type: control
        action: "goto_stage"
        target_stage: qa_cycle_stage
        condition: "$outputs.increment_iteration.next_iteration < $outputs.load_convergence_config.strategy.max_iterations"

  # ========== Stage 5: 最终化 ==========
  - id: finalization_stage
    name: "最终化与报告"
    steps:
      - id: gather_evidence
        name: "收集所有证据"
        type: skill
        run: skill.pm.gather_cycle_evidence
        inputs:
          all_qa_summaries: "$context.all_qa_summaries"
          all_dev_summaries: "$context.all_dev_summaries"
          all_bug_sets: "$context.all_bug_sets"

      - id: generate_report
        name: "生成收敛报告"
        type: agent
        run: agent.pm.reporter
        inputs:
          convergence_config: "$outputs.load_convergence_config"
          evidence: "$outputs.gather_evidence"
          final_status: "$convergence_decision.action"
        outputs:
          - convergence_report

      - id: release_approval_gate
        name: "最终发布审批"
        type: gate
        gate_ref: gate.project.release_approval
        reviewers: [ceo, cto]
        inputs:
          convergence_report: "$outputs.generate_report"

loop_control:
  convergence:
    max_iterations: 5
    on_max_iterations:
      action: escalate_to_human
      message: "达到最大迭代次数，需要人工审批"

exit_conditions:
  success:
    - condition: "convergence_decision.action == 'generate_report' AND release_approval_gate.status == 'approved'"
      description: "收敛达成且发布审批通过"
  failure:
    - condition: "convergence_decision.action == 'escalate'"
      description: "未达到收敛条件或达到最大迭代次数"
      action: require_human_review
```

### Phase 5: 新增 Skill 实现

#### Bug Set Git 追踪 Skill

位置: `src/lee/skills/git/bug_set_git_tracker.py`

```python
"""
Bug Set Git 追踪技能

负责：
1. 读取/写入 bug_set.yaml
2. 每次更新自动 git commit
3. 提供历史追溯功能
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import subprocess
import yaml
from datetime import datetime, timezone

class BugSetGitTracker:
    def __init__(self, project_root: str, repo_path: str = "."):
        self.project_root = Path(project_root).resolve()
        self.repo_path = Path(repo_path).resolve()
        self.bug_set_path = self.repo_path / "qa" / "bugsets" / "bug_set.yaml"

    def read_bug_set(self) -> Optional[Dict[str, Any]]:
        """读取当前 bug_set.yaml"""
        if not self.bug_set_path.exists():
            return None
        with open(self.bug_set_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def write_bug_set(self, bug_set: Dict[str, Any], cycle_info: Dict[str, Any]) -> str:
        """写入 bug_set.yaml 并提交到 git"""
        # 确保目录存在
        self.bug_set_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(self.bug_set_path, 'w', encoding='utf-8') as f:
            yaml.dump(bug_set, f, allow_unicode=True, default_flow_style=False)

        # Git 提交
        return self._git_commit_bug_set(bug_set, cycle_info)

    def _git_commit_bug_set(self, bug_set: Dict[str, Any], cycle_info: Dict[str, Any]) -> str:
        """Git 提交 bug_set.yaml"""
        summary = bug_set.get('summary', {})
        commit_msg = (
            f"Bug set update: cycle-{cycle_info.get('iteration', '?')}, "
            f"{cycle_info.get('action', 'update')} - "
            f"P0:{summary.get('by_severity', {}).get('P0', 0)} "
            f"P1:{summary.get('by_severity', {}).get('P1', 0)} "
            f"Total:{summary.get('total_bugs', 0)}"
        )

        # git add
        subprocess.run(
            ['git', 'add', str(self.bug_set_path.relative_to(self.repo_path))],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        # git commit
        result = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 获取 commit hash
        commit_hash = result.stdout.strip()

        # 创建标签（可选）
        tag = f"bugset-cycle-{cycle_info.get('iteration', '?')}"
        try:
            subprocess.run(
                ['git', 'tag', '-a', tag, '-m', f"Bug set for cycle {cycle_info.get('iteration', '?')}"],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # 标签可能已存在

        return commit_hash

    def get_bug_set_history(self, max_count: int = 10) -> List[Dict[str, Any]]:
        """获取 bug_set.yaml 的变更历史"""
        result = subprocess.run(
            ['git', 'log', f'-{max_count}', '--pretty=format:%H|%s|%an|%ai', '--', str(self.bug_set_path.relative_to(self.repo_path))],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        history = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 4:
                    history.append({
                        'commit_hash': parts[0],
                        'message': parts[1],
                        'author': parts[2],
                        'timestamp': parts[3]
                    })

        return history

    def compare_bug_sets(self, commit_a: str, commit_b: str) -> Dict[str, Any]:
        """比较两个版本的 bug_set.yaml"""
        result = subprocess.run(
            ['git', 'diff', commit_a, commit_b, '--', str(self.bug_set_path.relative_to(self.repo_path))],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # 解析 diff（简化版本）
        return {
            'diff': result.stdout,
            'has_changes': len(result.stdout.strip()) > 0
        }
```

### Phase 6: Chat 和 CLI 命令扩展

#### Chat 内部命令

在 `src/lee/cli/commands/chat.py` 的 `_handle_internal_command` 方法中添加：

```python
async def _handle_internal_command(self, text: str, session_id: str):
    """Handle internal commands starting with /"""
    parts = text.strip().split()
    cmd = parts[0].lower()

    # 现有命令...

    # 新增：收敛循环命令
    elif cmd == '/convergence':
        await self._cmd_convergence(parts[1:], session_id)

    # 新增：QA/Dev 循环命令
    elif cmd == '/qa':
        await self._cmd_qa(parts[1:], session_id)
    elif cmd == '/dev':
        await self._cmd_dev(parts[1:], session_id)

async def _cmd_convergence(self, args: List[str], session_id: str):
    """处理收敛循环命令"""
    if not args:
        await self.send_message("用法: /convergence <start|status|report|approve> [args]", session_id)
        return

    action = args[0].lower()

    if action == 'start':
        # /convergence start <input_file>
        input_file = args[1] if len(args) > 1 else "convergence-input.yaml"
        workflow_id = await self.orchestrator.create_workflow(
            level=WorkflowLevel.PROJECT,
            template_id="workflow.project.bug_convergence_cycle",
            data={"params": {"convergence_input_file": input_file}}
        )
        await self.send_message(f"✅ 收敛循环已启动: {workflow_id}", session_id)

    elif action == 'status':
        # /convergence status <workflow_id>
        workflow_id = args[1] if len(args) > 1 else None
        status = await self._get_convergence_status(workflow_id)
        await self.send_message(f"📊 收敛状态:\n{status}", session_id)

    elif action == 'report':
        # /convergence report <workflow_id>
        workflow_id = args[1] if len(args) > 1 else None
        report = await self._get_convergence_report(workflow_id)
        await self.send_message(f"📋 收敛报告:\n{report}", session_id)

async def _cmd_qa(self, args: List[str], session_id: str):
    """处理 QA 循环命令"""
    # 类似实现...

async def _cmd_dev(self, args: List[str], session_id: str):
    """处理 Dev 循环命令"""
    # 类似实现...
```

#### CLI 命令

在 `src/lee/cli/commands/` 下新建 `convergence_cmds.py`：

```python
"""收敛循环 CLI 命令"""

import click
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.models import WorkflowLevel

@click.group()
def convergence():
    """Bug 收敛循环管理（L1 项目级）"""
    pass

@convergence.command()
@click.option('--input', 'input_file', required=True, help='收敛输入文件路径')
@click.option('--wait', is_flag=True, help='等待完成')
def start(input_file: str, wait: bool):
    """启动收敛循环"""
    orchestrator = Orchestrator()
    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="workflow.project.bug_convergence_cycle",
        data={"params": {"convergence_input_file": input_file}}
    )
    click.echo(f"✅ 收敛循环已启动: {workflow.id}")

    if wait:
        # 等待完成的逻辑...
        pass

@convergence.command('list')
@click.option('--limit', default=10, help='显示数量')
def list_convergences(limit: int):
    """列出收敛循环"""
    # 列出所有 project 级别的工作流
    pass

@convergence.command()
@click.argument('workflow_id')
def status(workflow_id: str):
    """查看收敛状态"""
    # 获取工作流状态并显示
    pass

# QA 和 Dev 命令组类似实现...
```

在 `main.py` 中注册新命令：

```python
# 新增命令组
from lee.cli.commands.convergence_cmds import convergence, qa, dev

cli.add_command(convergence)
cli.add_command(qa)
cli.add_command(dev)
```

---

## 关键文件路径（更新）

### 新增契约文件
- `spec-global/contracts/bug-set/v1/schema.yaml` - Bug 集合契约
- `spec-global/contracts/convergence-input/v1/schema.yaml` - L1 输入契约
- `spec-global/contracts/convergence-report/v1/schema.yaml` - L1 输出契约

### 新增工作流文件（核心）
- `spec-global/departments/qa/workflows/test-cycle/v1/workflow.yaml` - QA-L2
- `spec-global/departments/dev/workflows/bugfix-cycle/v1/workflow.yaml` - Dev-L2
- `spec-global/projects/running-master/workflows/bug-convergence-cycle/v1/workflow.yaml` - L1

### 新增 L3 工作流（如需要）
- `spec-global/departments/dev/workflows/fix-single-bug/v1/workflow.yaml` - Dev-L3

### 新增代码文件
- `src/lee/skills/git/bug_set_git_tracker.py` - Git 追踪 Bug Set
- `src/lee/skills/pm/convergence_checker.py` - 收敛条件检查
- `src/lee/cli/commands/convergence_cmds.py` - 收敛循环 CLI 命令
- `src/lee/skills/qa/generate_bug_set_from_results.py` - 生成 Bug Set

### 修改代码文件
- `src/lee/cli/commands/chat.py` - 添加内部命令
- `src/lee/main.py` - 注册新命令组

### 复用现有实现（无需修改）
- `src/lee/orchestrator/execution/cross_workflow_loop.py` - 跨工作流循环控制器
- `src/lee/orchestrator/execution/subworkflow_ops.py` - 子工作流操作
- `src/lee/orchestrator/execution/orchestrator.py` - 主调度器
- `src/lee/orchestrator/execution/human_approval.py` - 人工审批
- `src/lee/orchestrator/execution/gate_engine.py` - 门禁引擎
- `src/lee/runtime/worktree_manager.py` - 工作区管理
- `src/lee/runtime/repo_registry.py` - 仓库注册

### 参考现有文件
- `spec-global/departments/qa/contracts/bug-contract/v1/schema.yaml`
- `spec-global/departments/dev/workflows/feature/v2/workflow.yaml` - L2 工作流参考
- `tests/test_cross_workflow_loop.py` - 跨工作流循环测试参考

---

## 用户确认的设计决策

基于用户反馈，以下设计决策已确定：

### 1. 循环控制模式：混合模式
- **L1 作为 coordinator**：不使用显式 while 循环，而是通过检查收敛条件决定是否 spawn 下一轮
- **实现方式**：L1 每次执行一个 "检查 → 决策 → spawn" 的完整周期
- **状态管理**：使用 SQLite 追踪当前迭代数和收敛状态

### 2. Bug Set 文件管理：Git 追踪
- **单一文件名**：始终保持 `qa/bugsets/bug_set.yaml`
- **版本控制**：每次变更自动提交到 git repo
- **追溯机制**：通过 git log 查看历史变更，通过 git diff 查看每轮差异
- **Commit 消息格式**：`"Bug set update: cycle-{N}, {action} - {summary}"`

### 3. Human Gate 审批点：关键节点审批
**三道人工 gate**：
1. **QA 循环结束 gate**：确认 bug_set 准确性，决定是否进入 Dev
2. **Dev 循环结束 gate**：确认修复质量，决定是否进入下一轮 QA
3. **最终发布 gate**：版本级验收，批准发布

**自动批准条件**（可配置）：
- P0/P1 bug 清零时可自动通过 QA gate
- 所有目标 bug 修复完成时可自动通过 Dev gate

### 4. MVP 目标：生产就绪
**必须实现的生产级特性**：
- 错误处理和重试机制（最多 3 次重试）
- 超时保护（每个 L2 最长 2 小时）
- 失败回滚（Dev 修复失败时回退代码）
- 状态恢复（支持从任意断点恢复）
- 完整日志和审计追踪
- 资源清理（临时 worktree、文件等）

---

## 实现细节更新

### L1 Coordinator 实现

```python
# src/lee/orchestrator/execution/convergence_coordinator.py

class ConvergenceCoordinator:
    """L1 收敛循环协调器"""

    async def run_cycle(self, input_file: str):
        """执行收敛循环"""

        iteration = 0
        max_iterations = self.load_config(input_file).strategy.max_iterations
        current_commit = self.load_config(input_file).code.start_commit

        while iteration < max_iterations:
            iteration += 1

            # QA 循环
            qa_result = await self.run_qa_cycle(current_commit, iteration)
            if qa_result.status == "failed":
                return self.handle_failure("qa", qa_result)

            # 检查收敛（第一轮后检查）
            if iteration > 1 and self.check_converged(qa_result.bug_set):
                return self.generate_report(qa_result, converged=True)

            # QA 人工 gate
            if not await self.request_qa_gate(qa_result):
                return self.handle_gate_rejected("qa")

            # Dev 循环
            dev_result = await self.run_dev_cycle(qa_result.bug_set, current_commit)
            if dev_result.status == "failed":
                return self.handle_failure("dev", dev_result)

            # 更新 commit
            current_commit = dev_result.final_commit

            # Dev 人工 gate
            if not await self.request_dev_gate(dev_result):
                return self.handle_gate_rejected("dev")

        # 达到最大迭代次数
        return self.handle_max_iterations_exceeded()
```

### Git 追踪 Bug Set

```python
# src/lee/skills/qa/git_tracked_bug_set.py

class GitTrackedBugSet:
    """Git 追踪的 Bug Set 管理"""

    def update_bug_set(self, bug_set: BugSet, cycle_info: dict) -> str:
        """更新 bug set 并提交到 git"""

        # 1. 写入文件
        file_path = "qa/bugsets/bug_set.yaml"
        self.write_yaml(file_path, bug_set)

        # 2. Git 提交
        commit_msg = (
            f"Bug set update: cycle-{cycle_info['iteration']}, "
            f"{cycle_info['action']} - "
            f"P0:{bug_set.summary.by_severity.P0} "
            f"P1:{bug_set.summary.by_severity.P1}"
        )

        commit_hash = self.git_add_and_commit(
            file_path,
            commit_msg,
            author=f"lee-automation <lee@{os.getenv('USER')}>"
        )

        # 3. 打标签（可选）
        tag = f"bugset-cycle-{cycle_info['iteration']}"
        self.git_tag(tag, commit_hash)

        return commit_hash

    def get_bug_set_history(self, max_count: int = 10) -> List[dict]:
        """获取 bug set 变更历史"""
        log = self.git_log(
            path="qa/bugsets/bug_set.yaml",
            max_count=max_count,
            format="%H|%s|%an|%ai"
        )

        return [self._parse_log_entry(line) for line in log.split('\n')]

    def compare_bug_sets(self, commit_a: str, commit_b: str) -> dict:
        """比较两个版本的 bug set 差异"""
        diff = self.git_diff(commit_a, commit_b, "qa/bugsets/bug_set.yaml")
        return self._parse_bug_set_diff(diff)
```

### 生产级错误处理

```python
# src/lee/orchestrator/execution/resilient_executor.py

class ResilientExecutor:
    """生产级执行器，带重试和超时"""

    async def execute_with_retry(
        self,
        workflow_id: str,
        max_retries: int = 3,
        timeout: int = 7200  # 2 hours
    ) -> ExecutionResult:
        """带重试和超时的工作流执行"""

        last_error = None

        for attempt in range(max_retries):
            try:
                result = await asyncio.wait_for(
                    self.orchestrator.run_workflow(workflow_id),
                    timeout=timeout
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Workflow {workflow_id} timed out after {timeout}s"
                self.logger.error(last_error)
                await self.orchestrator.pause(workflow_id)

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")

            # 重试前清理
            await self.cleanup_partial_state(workflow_id)

        # 所有重试失败
        return ExecutionResult(
            status="failed",
            error=last_error,
            retry_count=max_retries
        )

    async def cleanup_partial_state(self, workflow_id: str):
        """清理失败的部分状态"""
        # 清理临时 worktree
        worktrees = self.store.get_workflow_worktrees(workflow_id)
        for wt in worktrees:
            self.worktree_manager.prune(wt)

        # 清理临时文件
        temp_files = self.store.get_workflow_temp_files(workflow_id)
        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)
```

### 超时和重试配置

```yaml
# spec-global/runtime/resilience-config.yaml

resilience:
  qa_cycle:
    timeout_seconds: 7200  # 2 hours
    max_retries: 2
    retry_delay_seconds: 60
    failure_action: "escalate_to_human"

  dev_cycle:
    timeout_seconds: 10800  # 3 hours (dev 可能需要更长时间)
    max_retries: 3
    retry_delay_seconds: 120
    failure_action: "rollback_and_escalate"

  l3_task:
    timeout_seconds: 1800  # 30 minutes
    max_retries: 1
    retry_delay_seconds: 30
    failure_action: "mark_failed_and_continue"
```

---

## 关键文件路径（更新）

### 新增/修改代码文件
- `src/lee/orchestrator/execution/convergence_coordinator.py` - L1 协调器
- `src/lee/skills/qa/git_tracked_bug_set.py` - Git 追踪 Bug Set
- `src/lee/orchestrator/execution/resilient_executor.py` - 生产级执行器
- `src/lee/orchestrator/execution/worktree_rollback.py` - 回滚机制
- `src/lee/skills/pm/convergence.py` - PM convergence skill
- `src/lee/cli/commands/chat.py` - 添加新的内部命令
- `src/lee/cli/commands/orchestrator_cmds.py` - 添加新的 CLI 命令
- `src/lee/skills/qa/bug_set_ops.py` - Bug Set 操作
- `src/lee/skills/pm/convergence_checker.py` - 收敛检查

### 新增配置文件
- `spec-global/runtime/resilience-config.yaml` - 容错配置
- `spec-global/runtime/gate-config.yaml` - Gate 配置
- `spec-global/projects/running-master/convergence-presets/default.yaml` - 默认收敛配置

---

## 验证计划

### 1. 单元测试
- 测试 `BugSetGitTracker` 的 Git 操作
- 测试 `ConvergenceChecker` 的收敛判断逻辑
- 测试 `CrossWorkflowLoopController` 的集成（已有测试，可复用）

### 2. 集成测试
- 端到端运行一个完整的收敛循环（使用真实代码库）
- 验证 L2 → L2 的文件传递机制
- 验证 Git 追踪功能（commit 历史、diff、标签）
- 验证状态恢复功能

### 3. 工作流测试
- 测试 QA-L2 的 cross_workflow_loop 配置
- 测试 Dev-L2 的 cross_workflow_loop 配置
- 测试 L1 的条件分支和循环回退
- 测试人工 gate 的审批流程

### 4. 手动验证
1. 通过 Chat 启动一个收敛循环：`/convergence start convergence-input.yaml`
2. 观察 QA-L2 执行，检查 `git log qa/bugsets/bug_set.yaml`
3. 观察 Dev-L2 执行，检查 bug 状态更新
4. 检查最终 `convergence-report.yaml` 的内容
5. 测试 `/convergence status <workflow_id>` 查看状态
6. 测试 `/convergence report <workflow_id>` 查看报告

### 5. 压力测试
- 大量 bug（50+）的处理能力
- 多轮迭代的稳定性
- 失败场景的回滚和恢复

---

## 风险和注意事项

### 1. 复用现有实现的兼容性
**风险**：`CrossWorkflowLoopController` 主要用于 L3 循环，L2 循环可能需要适配

**缓解**：
- L2 循环配置与 L3 相同（都是 phases → convergence → on_exceeded）
- 复用相同的 IR 模型（`CrossWorkflowLoopIR` 等）
- 测试验证 L2 层的 `sub_workflow` 类型步骤支持

### 2. Git 追踪的性能影响
**风险**：每次 bug set 变更都提交 git 可能影响性能

**缓解**：
- 使用 `git commit --allow-empty` 减少对象创建
- 批量提交（多个 bug 一起提交）
- 考虑使用 `git hash-object` 而非完整提交

### 3. Orchestrator 扩展需求
**风险**：L1 的条件分支和循环回退需要 Orchestrator 支持

**缓解**：
- L1 使用 `decision` 类型步骤和 `condition` 字段（已有支持）
- 循环回退使用 `control` 类型的 `goto_stage` 动作（可能需要扩展）
- 或者使用 L1 也启用 `cross_workflow_loop`（将 QA-L2 和 Dev-L2 作为 phases）

### 4. L1 协调器实现方案
**备选方案**：如果 Orchestrator 不支持 `goto_stage`，L1 也可以使用 `CrossWorkflowLoopController`

```yaml
# L1 使用 CrossWorkflowLoopController 的备选方案
stages:
  - id: convergence_loop_stage
    name: "收敛循环"
    steps:
      - id: convergence_loop
        name: "L1 收敛循环"
        type: sub_workflow

        cross_workflow_loop:
          enabled: true
          max_rounds: 5
          phases:
            - id: qa_phase
              workflow_ref: workflow.qa.test_cycle
              role: tester
            - id: dev_phase
              workflow_ref: workflow.dev.bugfix_cycle
              role: fixer
              condition: "qa_phase.exit_decision == 'continue'"
              inputs_from:
                - phase: qa_phase
                  field: bug_set
          convergence:
            check_phase: qa_phase
            check_field: converged
            pass_values: [true]
            secondary_check: "bug_set.open_bug_count == 0"
```

### 5. 生产级特性的实现
**风险**：完整的错误处理、重试、超时机制增加复杂度

**缓解**：
- 复用 Orchestrator 现有的 `timeout` 配置
- 复用 `SubworkflowMixin` 的 `run_until_blocked` 逻辑
- 使用 WorktreeManager 的回滚机制
- 分阶段实现：先核心流程，再容错特性

---

## 实施顺序建议

### 第一步：契约定义（1-2天）
1. 创建 `bug-set` 契约 schema
2. 创建 `convergence-input` 契约 schema
3. 创建 `convergence-report` 契约 schema
4. 创建示例文件用于测试

### 第二步：核心 Skill 实现（2-3天）
1. 实现 `BugSetGitTracker`
2. 实现 `ConvergenceChecker`
3. 实现 `GenerateBugSetFromResults`
4. 单元测试

### 第三步：L3 工作流（2-3天）
1. 评估现有 QA-L3 是否满足需求
2. 创建 Dev-L3 `fix-single-bug` 工作流
3. 集成测试

### 第四步：L2 工作流（3-4天）
1. 创建 QA-L2 `test-cycle`（使用 cross_workflow_loop）
2. 创建 Dev-L2 `bugfix-cycle`（使用 cross_workflow_loop）
3. 配置人工 gate
4. 集成测试

### 第五步：L1 工作流（2-3天）
1. 创建 L1 `bug-convergence-cycle`
2. 配置条件分支和收敛检查
3. 配置最终发布 gate
4. 端到端测试

### 第六步：Chat 和 CLI 集成（2-3天）
1. 扩展 Chat 内部命令
2. 创建 CLI 命令组
3. 测试交互体验

### 第七步：生产就绪特性（3-5天）
1. 错误处理和重试
2. 超时保护
3. 失败回滚
4. 状态恢复
5. 压力测试

**总计：约 15-23 天**

### 1. 单元测试
- 测试 GitTrackedBugSet 的 git 操作
- 测试 ResilientExecutor 的重试和超时逻辑
- 测试 ConvergenceChecker 的收敛判断
- 测试回滚机制

### 2. 集成测试
- 端到端运行一个完整的收敛循环（使用真实代码库）
- 模拟各种失败场景（超时、异常、人工拒绝）
- 验证 git 历史追溯功能
- 验证状态恢复功能

### 3. 压力测试
- 大量 bug（50+）的处理能力
- 多轮迭代的稳定性
- 并发场景下的文件锁机制

### 4. 生产演练
- 在 demo 项目上运行完整流程
- 邀请实际用户测试 Chat 和 CLI 交互
- 收集反馈并优化

---

## 风险和注意事项（更新）

### 1. Git 追踪的性能影响
**风险**：每次 bug set 变更都提交 git 可能影响性能

**缓解**：
- 使用 git commit --allow-empty 减少对象创建
- 批量提交（多个 bug 一起提交）
- 考虑使用 git hash-object 而非完整提交

### 2. Orchestrator 扩展需求
**风险**：混合模式需要扩展 Orchestrator 的 coordinator 能力

**缓解**：
- ConvergenceCoordinator 作为 Orchestrator 的上层封装
- 复用现有 Orchestrator 的 workflow_spawn 能力
- 避免修改 Orchestrator 核心逻辑

### 3. 生产级特性的复杂性
**风险**：完整的生产特性可能大幅增加开发工作量

**缓解**：
- 分阶段实现：先核心流程，再容错特性
- 复用现有组件（如 WorktreeManager）
- 使用成熟库（如 tenacity 用于重试）

### 4. Agent 能力依赖
**风险**：QA/Dev agent 可能无法高质量完成 L3 任务

**缓解**：
- 第一版允许 L3 任务使用人工辅助
- 提供 L3 任务的模板和最佳实践
- 逐步提升 agent 自主程度
