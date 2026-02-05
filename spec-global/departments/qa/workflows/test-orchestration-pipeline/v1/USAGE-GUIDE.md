# Test Orchestration Pipeline - 使用指南

## 概述

L3 测试编排与结果收敛工作流（Test Orchestration Pipeline）是 LEE 测试体系的核心"骨架"层，负责：

1. **消费测试用例清单** - 从 test-execution-bundle 加载待执行的测试用例
2. **接收执行结果** - 接受来自人工、Claude Code 或未来 Runner 的执行结果
3. **自动生成 Bug** - 将失败用例自动转换为标准化的 Bug 契约
4. **输出测试报告** - 生成机器（JSON）和人类（Markdown）可读的测试报告
5. **门禁判定** - 根据预设规则判定是否满足出测标准

## 核心定位

> **这不是自动化测试执行器，而是测试流程的编排与收敛层。**

```
测试用例（WHAT）
    ↓
执行结果（FACT）← 人工/Claude Code/Runner
    ↓
L3 编排与收敛（DECIDE）← 本工作流
    ↓
Bug 契约 + 测试报告 + 轮次结论
```

## 快速开始

### 步骤 1：准备测试执行输入包

创建 `test-execution-bundle.yaml`：

```yaml
bundle_id: TEB-2026-0001
name: "登录模块测试执行包"
target_version: "v1.0.0-rc1"
target_environment: test

test_cases:
  - case_id: "F-BASE-002"
    title: "开发测试登录 - 验证快速登录流程"
    suite: smoke
    priority: P0
    type: positive
    tags: ["login", "smoke", "core-flow"]

    execution_config:
      automated: true
      script_path: "tests/e2e/login.spec.ts"
      framework: playwright
      timeout_seconds: 60

    description: "验证用户可以通过开发测试快速登录"
    preconditions:
      - "前后端服务均已启动"
    steps:
      - step_num: 1
        action: "访问登录页面"
        expected: "页面加载成功"
      - step_num: 2
        action: "点击开发测试登录按钮"
        expected: "触发登录请求"
      - step_num: 3
        action: "等待页面跳转"
        expected: "跳转到跑者画像页面"
    expected_result: "用户成功登录并进入跑者画像页面"
```

### 步骤 2：执行测试并收集结果

#### 方式 A：人工执行

手工执行测试后，填写 `test-results.yaml`：

```yaml
source: manual
executor: "test-engineer-john"
executed_at: "2026-02-05T14:00:00Z"

environment:
  env_type: test
  target_version: "v1.0.0-rc1"

results:
  - case_id: "F-BASE-002"
    status: pass
    evidence:
      note: "手工验证登录流程正常"

  - case_id: "F-P1-001"
    status: fail
    failure_info:
      error_message: "保存后数据显示异常"
      error_type: assertion_failed
    evidence:
      screenshots: ["manual/f-p1-001.jpg"]
      note: "手工验证发现数据不一致"
```

#### 方式 B：Claude Code 执行

使用 Claude Code 执行测试后，生成 `test-results.yaml`：

```yaml
source: claude_code
executor: "claude-code-agent"
executed_at: "2026-02-05T10:30:00Z"
execution_duration_seconds: 300

environment:
  env_type: test
  target_version: "v1.0.0-rc1"
  base_url: "http://localhost:3000"

results:
  - case_id: "F-BASE-002"
    status: pass
    duration_seconds: 5
    evidence:
      screenshots: ["evidence/f-base-002-pass.png"]

  - case_id: "F-P1-001"
    status: fail
    duration_seconds: 15
    failure_info:
      error_message: "保存后数据未刷新"
      error_type: assertion_failed
      failed_step: 3
      expected: "页面显示新数据"
      actual: "页面仍显示旧数据"
    evidence:
      trace_id: "trace-abc-123"
      screenshots: ["evidence/f-p1-001-fail.png"]
      logs_hint: ["api-runner-profile"]
      note: "API 返回 200，但前端未更新"
```

### 步骤 3：运行 L3 工作流

```bash
# 使用 LEE Orchestrator 运行
lee run workflow test.orchestration_pipeline_v1 \
  --input test-execution-bundle.yaml \
  --input test-results.yaml
```

### 步骤 4：查看输出结果

工作流完成后，查看生成的文件：

```bash
# 轮次权威状态文件
cat test-round.yaml

# JSON 测试报告
cat test-report.json

# Markdown 测试报告
cat test-report.md

# Bug 契约文件
ls bugs/
# BUG-2026-0001.contract.yaml
# BUG-2026-0002.contract.yaml
```

## 输出文件说明

### 1. test-round.yaml

本轮测试的**权威状态文件**，包含：

- `round_id`: 轮次唯一标识
- `status`: 轮次状态（in_progress/completed/blocked）
- `conclusion`: 轮次结论（next_round/release_candidate/blocked）
- `summary`: 测试摘要（用例数、通过率、Bug 数等）
- `suites_executed`: 各套件执行情况

```yaml
round_id: "TSTR-0001"
status: completed
conclusion:
  decision: fail
  rationale: "存在 1 个 P1 Bug"
  exit_criteria_met: false
summary:
  new_bugs: 1
  bug_breakdown:
    p1_open: 1
```

### 2. test-report.json

机器可读的测试报告，包含完整的测试数据。

### 3. test-report.md

人类可读的测试报告，包含：

- **执行概要** - 关键指标和结论
- **用例执行统计** - 通过率、按优先级/套件统计
- **失败用例详情** - 每个失败的详细信息
- **Bug 清单** - 生成的 Bug 列表
- **风险评估** - 遗留风险分析
- **改进建议** - 测试改进建议

### 4. bugs/*.contract.yaml

自动生成的 Bug 契约文件：

```yaml
bug_id: "BUG-2026-0001"
title: "[F-P1-001] 跑者画像保存后数据未刷新"
severity: P1
category: functional
status: new

detected_in:
  round_id: "TSTR-0001"
  version: "v1.0.0-rc1"
  test_case_id: "F-P1-001"

evidence:
  trace_id: "trace-abc-123"
  screenshots: ["evidence/f-p1-001-fail.png"]
  logs_hint: ["api-runner-profile"]
  reproduction_steps: |
    1. 访问跑者画像页面
    2. 修改数据并保存
    3. 预期：页面刷新显示新数据
    4. 实际：页面仍显示旧数据
```

## 门禁规则

工作流使用 `test-execution-gate` 进行门禁判定：

### 强制标准（0 容忍）

| 标准 | 规则 | 说明 |
|------|------|------|
| P0 Bug 清零 | `p0_bugs == 0` | P0 Bug 必须为零 |
| 冒烟 100% | `smoke_pass_rate == 100` | 冒烟测试必须全部通过 |
| 核心流程 100% | `core_flow_pass_rate == 100` | 核心流程必须全部通过 |
| P0/P1 完整性 | `p0_p1_missing == 0` | P0/P1 用例必须执行 |

### 阈值标准（可配置）

| 标准 | 默认阈值 | 说明 |
|------|----------|------|
| P1 Bug 数 | `<= 3` | P1 Bug 数量不超过阈值 |
| 整体通过率 | `>= 90%` | 整体通过率不低于阈值 |
| P1 通过率 | `>= 95%` | P1 用例通过率不低于阈值 |
| P2 Bug 数 | `<= 10` | P2 Bug 数量不超过阈值 |

### 结论判定

- **PASS** - 满足所有强制标准和阈值标准
- **CONDITIONAL_PASS** - 基本满足标准，但存在风险，需人类审批
- **FAIL** - 不满足出测标准，需要修复并重新测试

## 阈值配置

可以通过修改配置使用不同的阈值：

```yaml
# 保守模式（更严格）
thresholds:
  p1_threshold: 1
  p2_threshold: 5
  pass_rate_threshold: 95

# 激进模式（更宽松）
thresholds:
  p1_threshold: 5
  p2_threshold: 20
  pass_rate_threshold: 85
```

## 常见问题

### Q: 如何处理缺失的 P2/P3 用例结果？

A: P2/P3 用例结果缺失会生成警告，但不会阻塞工作流。P0/P1 用例结果缺失会阻塞并要求补充。

### Q: 如何合并相似的失败用例？

A: 工作流会自动按错误相似度分组失败用例，相似度 > 80% 的失败会合并为一个 Bug。

### Q: 如何自定义 Bug 严重程度映射？

A: 默认规则是用例优先级直接映射到 Bug 严重程度（P0 → P0）。可以在 `bug_generation_rules` 中自定义映射逻辑。

### Q: 有条件通过后如何获得人类审批？

A: 当结论为 `CONDITIONAL_PASS` 时，工作流会触发 `human_in_the_loop`，需要指定的审批人（qa_lead、pm）审批后才能继续。

### Q: 如何处理需要跳过的用例？

A: 在 `test-results.yaml` 中标记 `status: skipped` 并填写 `skipped_info`：

```yaml
- case_id: "F-P2-003"
  status: skipped
  skipped_info:
    reason: dependency_blocked
    note: "依赖的上游 Bug 未修复"
```

## 最佳实践

1. **优先使用自动化** - 能自动化的用例尽量自动化，减少人工工作量
2. **充分收集证据** - 失败用例务必提供截图、日志、trace_id 等证据
3. **合理标记优先级** - 准确标记用例优先级，影响后续的 Bug 严重程度
4. **及时处理 Bug** - 生成的 Bug 契约应及时处理，避免累积
5. **定期审查门禁规则** - 根据项目进展调整阈值配置

## 后续演进

当有了自动化 Runner 后：

1. Runner 只需要输出符合 `test-result` schema 的结果文件
2. L3 工作流**完全不用改**
3. 实现了"先定接口，再换实现"的架构设计

## 参考资料

- 工作流定义：`workflow.yaml`
- 执行包契约：`../../contracts/test-execution-bundle/v1/schema.yaml`
- 执行结果契约：`../../contracts/test-result/v1/schema.yaml`
- 门禁规则：`../../gates/test-execution-gate/v1/gate.yaml`
- Result Aggregator Agent：`../../agents/test-result-aggregator/v1/agent.yaml`
