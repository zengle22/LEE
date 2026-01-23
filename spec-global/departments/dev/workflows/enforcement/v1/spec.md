# Workflow Enforcement Specification v1.0

## 概述

本规范定义了一个**与 CLI 工具无关**的工作流强制执行机制，确保：
- 必选步骤不被跳过
- 人类门禁不被绕过
- Agent 产出物符合契约
- 执行状态可追溯

## 设计原则

1. **CLI 无关性** - 适用于 Claude Code、Cursor、Codex、自定义 Agent 等任何执行环境
2. **文件驱动** - 所有状态通过文件表达，不依赖特定运行时
3. **契约优先** - 使用 JSON Schema 验证状态和产出物
4. **渐进式强制** - 从警告到阻断的渐进强制策略

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Enforcement                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐    │
│  │  Spec Layer   │    │  State Layer  │    │ Validate Layer│    │
│  │               │    │               │    │               │    │
│  │ workflow.yaml │───▶│ execution-    │───▶│ workflow-     │    │
│  │ agent.yaml    │    │ state.yaml    │    │ guard         │    │
│  │ contract.json │    │               │    │               │    │
│  └───────────────┘    └───────────────┘    └───────────────┘    │
│                                                    │              │
│                                                    ▼              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     CLI Adapters                             ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        ││
│  │  │ Claude  │  │ Cursor  │  │ Codex   │  │ Custom  │        ││
│  │  │ Code    │  │         │  │         │  │ Agent   │        ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Execution State (执行状态)

每个 Phase/项目维护一个 `execution-state.yaml` 文件：

```yaml
# {phase_dir}/.workflow/execution-state.yaml
version: "1.0"
schema: "contract.dev.execution_state/v1"

workflow:
  id: workflow.dev.phase_openspec_flow
  version: "1.0"

run:
  id: RUN-20260110-003843
  started_at: "2026-01-10T00:38:43Z"
  status: running  # pending | running | blocked | completed | failed

current_step:
  id: p5_implementation
  agent_id: agent.dev.go_backend_engineer
  status: in_progress
  started_at: "2026-01-10T01:30:00Z"

enforcement:
  mode: strict  # permissive | warning | strict

  # 待验证的必选步骤
  mandatory_steps:
    - step_id: p11_phase_acceptance
      required_outputs:
        - openspec/08-acceptance/acceptance-report.yaml
      validation_schema: contract.dev.acceptance_report/v1
      status: pending

  # 待审批的人类门禁
  pending_gates:
    - gate_id: h5_acceptance_review
      step_id: p11_phase_acceptance
      status: pending
      blocking: true

  # 已通过的检查点
  checkpoints:
    - step_id: p4_openspec_proposal
      gate_id: h3_proposal_review
      passed_at: "2026-01-10T01:30:00Z"
      approver: human
```

### 2. Enforcement Modes (强制模式)

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `permissive` | 仅记录，不阻断 | 初始集成、调试 |
| `warning` | 警告 + 确认继续 | 过渡期 |
| `strict` | 阻断 + 必须修复 | 生产环境 |

### 3. Step Lifecycle (步骤生命周期)

```
pending → starting → in_progress → validating → completed
                          ↓              ↓
                       blocked        failed
                          ↓
                    awaiting_gate → approved → completed
```

**关键验证点**：

| 阶段 | 验证内容 |
|------|----------|
| `starting` | 检查前置步骤是否完成 |
| `validating` | 验证产出物是否存在且符合契约 |
| `awaiting_gate` | 等待人类审批 |

### 4. Output Validation (产出物验证)

每个步骤完成前必须验证：

```python
def validate_step_outputs(step_id, step_def, phase_dir):
    """验证步骤产出物"""
    errors = []

    for output in step_def.get("outputs", []):
        output_path = phase_dir / output

        # 1. 文件存在性检查
        if not output_path.exists():
            errors.append(f"Missing: {output}")
            continue

        # 2. 契约验证 (如果指定了 schema)
        if schema := step_def.get("output_schema"):
            validation_errors = validate_against_schema(
                output_path, schema
            )
            errors.extend(validation_errors)

    return len(errors) == 0, errors
```

### 5. Gate Management (门禁管理)

人类门禁的完整流程：

```yaml
# 门禁定义 (in workflow.yaml)
gates:
  h5_acceptance_review:
    type: human_approval
    blocking: true
    timeout: 48h
    required_artifacts:
      - openspec/08-acceptance/acceptance-report.yaml
    approval_command: "workflow-guard approve h5_acceptance_review"
```

**门禁状态**：
- `pending` - 等待审批
- `approved` - 已批准
- `rejected` - 已拒绝 (需要返工)
- `timeout` - 超时 (需要升级)
- `auto_approved` - Agent 自动批准 (条件门禁)
- `skipped` - 跳过 (条件门禁未触发)

### 6. Conditional Gates (条件门禁 / Agent 驱动门禁)

部分门禁可以由 Agent 自主判断是否需要人类介入，而非强制触发。

#### 定义方式

```yaml
# 条件门禁定义 (in workflow.yaml)
conditional_human_gate:
  gate_id: h4_code_review

  # 触发人类审批的条件 (任一满足则触发)
  trigger_conditions:
    - condition: "critical_issues > 0"
      reason: "发现 Critical 级别问题，需要人类确认"
    - condition: "security_vulnerabilities > 0"
      reason: "发现安全漏洞，必须人类确认"
    - condition: "code_quality_score < 6"
      reason: "代码质量评分过低，需要人类审查"

  # 自动通过的条件 (全部满足则自动通过)
  auto_approve_conditions:
    - "critical_issues == 0"
    - "high_issues <= 3"
    - "security_vulnerabilities == 0"
    - "code_quality_score >= 7"
```

#### Agent 判断逻辑

```python
def evaluate_conditional_gate(gate_def, review_result):
    """Agent 评估条件门禁"""

    # 检查是否需要触发人类门禁
    for trigger in gate_def.get("trigger_conditions", []):
        if eval_condition(trigger["condition"], review_result):
            return {
                "action": "trigger_human_gate",
                "reason": trigger["reason"],
                "gate_id": gate_def["gate_id"]
            }

    # 检查是否可以自动通过
    auto_conditions = gate_def.get("auto_approve_conditions", [])
    if all(eval_condition(c, review_result) for c in auto_conditions):
        return {
            "action": "auto_approve",
            "reason": "满足自动通过条件",
            "gate_id": gate_def["gate_id"]
        }

    # 条件不明确，保守触发人类门禁
    return {
        "action": "trigger_human_gate",
        "reason": "无法确定，需人类判断",
        "gate_id": gate_def["gate_id"]
    }
```

#### 执行状态记录

```yaml
# 自动通过的门禁
enforcement:
  auto_approved_gates:
    - gate_id: h4_code_review
      step_id: p7_code_review
      auto_approved_at: "2026-01-10T02:35:00Z"
      reason: "满足自动通过条件"
      review_metrics:
        critical_issues: 0
        high_issues: 2
        code_quality_score: 8
        security_vulnerabilities: 0
```

#### 与强制门禁的区别

| 特性 | 强制门禁 (human_gate) | 条件门禁 (conditional_human_gate) |
|------|----------------------|----------------------------------|
| 触发方式 | 步骤完成时必定触发 | Agent 根据条件判断是否触发 |
| required | true | false |
| 阻断性 | 始终阻断 | 触发时阻断，未触发时继续 |
| 适用场景 | 重大决策、最终验收 | 代码审查、测试审查等 |
| 状态 | pending → approved/rejected | auto_approved / skipped / pending |

### 7. Remediation Loop (整改循环机制)

验收步骤在不满足质量门禁时，应自动触发整改循环，而非直接请求人类介入。

#### 整改流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    整改循环流程                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────┐                                               │
│  │ 验收 Agent    │                                               │
│  │ 执行验收检查   │                                               │
│  └───────┬───────┘                                               │
│          │                                                        │
│          ▼                                                        │
│  ┌───────────────┐    Yes    ┌───────────────┐                  │
│  │ 全部通过?     │──────────▶│ PASS          │                  │
│  └───────┬───────┘           │ 进入交接阶段   │                  │
│          │ No                └───────────────┘                   │
│          ▼                                                        │
│  ┌───────────────┐                                               │
│  │ 记录失败项     │                                               │
│  │ 增加尝试次数   │                                               │
│  └───────┬───────┘                                               │
│          │                                                        │
│          ▼                                                        │
│  ┌───────────────┐    Yes    ┌───────────────┐                  │
│  │ 尝试次数 > N?  │──────────▶│ 触发人类门禁   │                  │
│  └───────┬───────┘           │ h5_acceptance  │                  │
│          │ No                └───────────────┘                   │
│          ▼                                                        │
│  ┌───────────────┐                                               │
│  │ 定位责任步骤   │                                               │
│  │ (根据失败项)   │                                               │
│  └───────┬───────┘                                               │
│          │                                                        │
│          ▼                                                        │
│  ┌───────────────┐                                               │
│  │ 触发整改      │───────────────────────────────┐               │
│  │ rollback_to   │                               │               │
│  └───────────────┘                               │               │
│                                                   │               │
│          ┌────────────────────────────────────────┘               │
│          ▼                                                        │
│  ┌───────────────┐                                               │
│  │ 责任步骤重新   │                                               │
│  │ 执行并修复    │                                               │
│  └───────┬───────┘                                               │
│          │                                                        │
│          └────────────────────────▶ 回到验收 Agent                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 整改配置定义

```yaml
# 在步骤中定义整改配置
remediation:
  enabled: true
  max_attempts: 5  # 最大整改次数

  # 失败项 → 责任步骤映射
  step_mapping:
    - issue: "code_coverage < 80"
      responsible_step: "p6_unit_test"
      remediation_action: "补充单元测试"
    - issue: "critical_issues > 0"
      responsible_step: "p5_implementation"
      remediation_action: "修复 Critical 问题"
    - issue: "high_issues > 0"
      responsible_step: "p5_implementation"
      remediation_action: "修复 High 问题"
    - issue: "retrospective_incomplete"
      responsible_step: "p8_retrospective"
      remediation_action: "补充复盘报告"
    - issue: "knowledge_items == 0"
      responsible_step: "p9_knowledge_update"
      remediation_action: "提取知识沉淀"

  # 超过最大整改次数
  on_max_attempts_exceeded:
    action: "trigger_human_gate"
    gate_id: "h5_acceptance_review"
    message: "已整改 {attempt_count} 次仍未通过，需要人类介入"
```

#### Agent 整改判断逻辑

```python
def evaluate_acceptance(phase_dir, quality_gates, remediation_config):
    """验收 Agent 的整改判断逻辑"""

    # 1. 加载当前状态
    state = load_execution_state(phase_dir)
    attempt_count = state.get("remediation", {}).get("attempt_count", 0)

    # 2. 执行验收检查
    failures = []
    for gate in quality_gates:
        result = evaluate_gate(gate, phase_dir)
        if not result.passed:
            failures.append({
                "gate_id": gate["id"],
                "issue": gate["name"],
                "expected": gate["threshold"],
                "actual": result.actual,
                "blocking": gate.get("blocking", True)
            })

    # 3. 全部通过 → PASS
    if not failures:
        return {"verdict": "pass", "next_step": "p12_knowledge_merge"}

    # 4. 只有非阻塞性问题 → CONDITIONAL_PASS
    blocking_failures = [f for f in failures if f["blocking"]]
    if not blocking_failures:
        return {
            "verdict": "conditional_pass",
            "deferred_items": failures,
            "next_step": "p12_knowledge_merge"
        }

    # 5. 检查整改次数
    attempt_count += 1
    max_attempts = remediation_config.get("max_attempts", 5)

    if attempt_count > max_attempts:
        # 触发人类门禁
        return {
            "verdict": "human_intervention_required",
            "attempt_count": attempt_count,
            "failures": blocking_failures,
            "action": "trigger_gate",
            "gate_id": "h5_acceptance_review"
        }

    # 6. 定位责任步骤并触发整改
    step_mapping = remediation_config.get("step_mapping", [])
    remediation_targets = []

    for failure in blocking_failures:
        for mapping in step_mapping:
            if matches_issue(failure["issue"], mapping["issue"]):
                remediation_targets.append({
                    "failure": failure,
                    "responsible_step": mapping["responsible_step"],
                    "action": mapping["remediation_action"]
                })
                break

    return {
        "verdict": "remediation_required",
        "attempt_count": attempt_count,
        "failures": blocking_failures,
        "remediation_targets": remediation_targets,
        "action": "rollback_and_fix"
    }
```

#### 执行状态记录

```yaml
# 整改状态追踪
remediation:
  enabled: true
  attempt_count: 3
  max_attempts: 5

  history:
    - attempt: 1
      timestamp: "2026-01-10T02:30:00Z"
      failures:
        - gate_id: "QG-004"
          issue: "code_coverage < 80%"
          actual: "65%"
      action: "rollback_to p6_unit_test"

    - attempt: 2
      timestamp: "2026-01-10T02:45:00Z"
      failures:
        - gate_id: "QG-004"
          issue: "code_coverage < 80%"
          actual: "72%"
      action: "rollback_to p6_unit_test"

    - attempt: 3
      timestamp: "2026-01-10T03:00:00Z"
      failures: []
      action: "pass"

  current_rollback:
    target_step: "p6_unit_test"
    reason: "code_coverage = 70%, target >= 80%"
    started_at: "2026-01-10T02:35:00Z"
```

#### 与门禁的协作

整改循环与人类门禁的关系：

| 场景 | 整改循环行为 | 人类门禁触发条件 |
|------|-------------|-----------------|
| 首次验收失败 | 自动整改 (attempt 1) | 不触发 |
| 整改后仍失败 | 继续整改 (attempt 2-N) | 不触发 |
| 达到最大次数 | 停止整改 | **触发 h5** |
| 只有非阻塞问题 | 记录到技术债务 | 不触发 |
| 严重安全漏洞 | 立即触发 | **触发 h5** |

## 工具：workflow-guard

### 命令接口

```bash
# 初始化执行状态
workflow-guard init --workflow <workflow-id> --phase <phase-dir>

# 检查是否可以开始步骤
workflow-guard check-start --step <step-id>

# 验证步骤产出物
workflow-guard validate --step <step-id>

# 标记步骤完成 (自动验证)
workflow-guard complete --step <step-id>

# 审批门禁
workflow-guard approve <gate-id> [--notes "..."]

# 拒绝门禁
workflow-guard reject <gate-id> --reason "..."

# 查看执行状态
workflow-guard status

# 验证整体状态完整性
workflow-guard verify
```

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功/允许继续 |
| 1 | 验证失败 |
| 2 | 被门禁阻断 |
| 3 | 配置错误 |

## CLI 适配

### Claude Code

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "command": "python scripts/workflow-guard.py check-state"
    }]
  }
}
```

### Cursor

```json
// .cursor/settings.json
{
  "workflowGuard": {
    "enabled": true,
    "script": "scripts/workflow-guard.py"
  }
}
```

### Codex

```yaml
# codex.yaml
hooks:
  pre_edit: "python scripts/workflow-guard.py check-state"
  post_edit: "python scripts/workflow-guard.py update-state"
```

### 通用 (Git Hooks)

```bash
# .git/hooks/pre-commit
#!/bin/bash
python scripts/workflow-guard.py verify || exit 1
```

## Agent 集成指令

所有 Agent 规范中必须包含以下指令：

```yaml
# agent.yaml
execution:
  workflow_aware: true

  pre_execution:
    - "检查 execution-state.yaml 确认当前步骤"
    - "验证前置步骤已完成"
    - "确认无阻断门禁"

  post_execution:
    - "验证产出物符合契约"
    - "更新 execution-state.yaml"
    - "如有人类门禁，等待审批"

  on_blocked:
    - "输出阻断原因"
    - "不尝试绕过"
    - "请求人类干预"
```

## 错误处理

### 常见错误场景

| 错误 | 原因 | 处理 |
|------|------|------|
| `STEP_NOT_STARTED` | 尝试完成未开始的步骤 | 先调用 check-start |
| `MISSING_OUTPUT` | 步骤产出物不存在 | 返回生成产出物 |
| `SCHEMA_VIOLATION` | 产出物不符合契约 | 修复产出物格式 |
| `GATE_PENDING` | 人类门禁未通过 | 等待人类审批 |
| `DEPENDENCY_INCOMPLETE` | 前置步骤未完成 | 先完成前置步骤 |

### 恢复机制

```bash
# 重置步骤状态 (需要人类确认)
workflow-guard reset --step <step-id> --reason "..."

# 跳过步骤 (需要管理员权限)
workflow-guard skip --step <step-id> --approver admin --reason "..."
```

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-01-10 | 初始版本 |
