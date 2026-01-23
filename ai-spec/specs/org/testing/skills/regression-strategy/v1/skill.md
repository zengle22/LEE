# Regression Strategy Skill v1.0
# 回归策略技能规范

## 概述

回归策略技能定义了如何确定回归测试范围、选择回归策略、执行回归测试的方法论。
确保代码变更不引入新问题，已修复的 Bug 不再复现。

## 技能标识

- **ID**: skill.test.regression_strategy
- **名称**: Regression Strategy
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.regression_test_executor
- agent.test.bug_manager

---

## 1. 回归策略类型

### 1.1 策略概览

```yaml
regression_strategies:
  minimal:
    name: "最小回归"
    scope: "直接相关"
    time: "快"
    risk: "可能遗漏间接影响"
    when: "单个 Bug 修复，影响范围明确"

  risk:
    name: "风险回归"
    scope: "相关 + 风险区域"
    time: "中"
    risk: "平衡"
    when: "涉及公共模块，多处修改"

  full:
    name: "完整回归"
    scope: "全部"
    time: "长"
    risk: "最低"
    when: "基础设施变更，大版本发布"

  smoke:
    name: "冒烟回归"
    scope: "核心链路"
    time: "最快"
    risk: "只验证核心"
    when: "紧急修复，环境变更"
```

### 1.2 策略选择决策树

```
变更类型?
├── 单个 Bug 修复
│   ├── 影响范围明确 → minimal
│   └── 涉及公共模块 → risk
│
├── 多个 Bug 修复
│   ├── 相互独立 → 每个 minimal
│   └── 有关联 → risk
│
├── 功能变更
│   ├── 小改动 → risk
│   └── 大改动 → full
│
├── 基础设施变更
│   └── → full
│
├── 紧急修复
│   └── → smoke + 目标 Bug 验证
│
└── 配置变更
    ├── 功能开关 → smoke
    └── 环境配置 → smoke + 相关模块
```

---

## 2. 回归范围确定

### 2.1 变更影响分析

```yaml
impact_analysis:
  inputs:
    - changed_files: "变更文件列表"
    - commit_message: "提交信息"
    - bug_info: "关联 Bug 信息"

  analysis_steps:
    1_direct_impact:
      description: "直接影响 - 变更文件本身"
      method: "文件路径映射到模块"

    2_caller_impact:
      description: "调用方影响 - 谁调用了变更的代码"
      method: "调用链分析"

    3_data_impact:
      description: "数据影响 - 数据结构变更的影响"
      method: "Schema 变更分析"

    4_config_impact:
      description: "配置影响 - 配置变更的影响"
      method: "配置依赖分析"

  outputs:
    - affected_modules: ["auth", "order"]
    - affected_paths: ["login", "checkout"]
    - risk_level: "low | medium | high"
```

### 2.2 模块依赖映射

```yaml
module_dependencies:
  auth:
    depends_on: ["database", "cache"]
    depended_by: ["order", "user", "payment"]
    core_path: true

  order:
    depends_on: ["auth", "product", "inventory"]
    depended_by: ["payment", "shipping"]
    core_path: true

  payment:
    depends_on: ["auth", "order"]
    depended_by: ["notification"]
    core_path: true

  # ... 其他模块
```

### 2.3 范围计算示例

```yaml
# 示例: 修改了 auth/login.go

impact_calculation:
  changed_file: "auth/login.go"
  direct_module: "auth"

  minimal_scope:
    - "auth/login 相关用例"
    - "Bug 回归用例 (如有)"

  risk_scope:
    - "minimal 范围"
    - "order 模块登录相关"
    - "payment 模块认证相关"
    - "冒烟用例"

  full_scope:
    - "所有回归用例"
```

---

## 3. 回归用例管理

### 3.1 回归用例库结构

```yaml
regression_suite:
  structure:
    smoke:
      description: "冒烟回归用例"
      count: 20-30
      priority: P0
      execution_time: "< 30min"

    core:
      description: "核心链路回归"
      count: 50-100
      priority: P0-P1
      execution_time: "1-2h"

    module:
      description: "模块级回归"
      per_module: 20-50
      priority: P1-P2
      execution_time: "varies"

    bug:
      description: "Bug 回归用例"
      source: "已修复 Bug"
      priority: "继承原 Bug"
      tags: ["regression", "bug-fix"]
```

### 3.2 Bug 回归用例创建

```yaml
bug_regression_case:
  id: "REG-{BUG_ID}"
  source: "bug.contract.yaml"
  type: "bug_regression"

  mapping:
    title: "从 bug.title"
    priority: "从 bug.severity"
    module: "从 bug.detected_in.test_case_id 推导"
    preconditions: "从 bug.repro.preconditions"
    steps: "从 bug.repro.steps"
    expected: "从 bug.repro.expected"

  enrichment:
    related_bug_id: "{BUG_ID}"
    fix_commit: "从 bug.fix.fix_commit"
    fix_version: "从 bug.fix.fix_version"
    tags: ["regression", "bug-fix", "{module}"]
```

### 3.3 回归用例维护

```yaml
maintenance:
  add_triggers:
    - "Bug 修复验证通过后"
    - "severity in [P0, P1]"

  remove_triggers:
    - "功能下线"
    - "需求变更导致用例失效"
    - "长期稳定 (>6个月无失败)"

  review_cycle: "每迭代一次"
```

---

## 4. 执行策略

### 4.1 执行优先级

```yaml
execution_priority:
  1_bug_verification:
    description: "验证修复的 Bug"
    scope: "关联的 Bug 回归用例"
    fail_action: "打回修复，重新打开 Bug"

  2_affected_smoke:
    description: "受影响的冒烟用例"
    scope: "变更影响的核心链路"
    fail_action: "阻塞，需要分析"

  3_risk_regression:
    description: "风险区域回归"
    scope: "调用链上下游"
    fail_action: "创建新 Bug"

  4_full_regression:
    description: "完整回归 (如需)"
    scope: "全部回归用例"
    fail_action: "创建新 Bug"
```

### 4.2 并行执行

```yaml
parallel_execution:
  enabled: true
  max_parallel: 5

  grouping:
    - bug_verification: "顺序执行"
    - smoke_regression: "可并行"
    - module_regression: "按模块并行"

  isolation:
    - "每个并行任务使用独立数据"
    - "避免资源竞争"
```

### 4.3 失败处理

```yaml
failure_handling:
  bug_verification_fail:
    action: "reopen_bug"
    bug_update:
      status: "assigned"
      verification:
        verification_result: "fail"
        verification_notes: "回归验证失败"

  regression_fail:
    new_bug: true
    analysis:
      - "是否为回归问题"
      - "是否为已知问题"
      - "是否为环境问题"

  flaky_detection:
    retry_count: 2
    if_intermittent:
      - "标记为 flaky"
      - "单独处理"
```

---

## 5. 结果分析

### 5.1 回归指标

```yaml
regression_metrics:
  primary:
    - pass_rate: "通过率"
    - regression_count: "发现的回归问题数"
    - verification_pass_rate: "Bug 验证通过率"

  derived:
    - regression_rate: "regression_count / total_changes"
    - fix_quality: "verification_pass / verification_total"

  trends:
    - week_over_week: "周环比"
    - version_over_version: "版本环比"
```

### 5.2 回归问题分类

```yaml
regression_classification:
  true_regression:
    description: "之前工作正常，现在不工作"
    action: "创建 P1+ Bug"
    priority: "高"

  related_regression:
    description: "与变更相关但非直接因果"
    action: "创建 Bug，分析根因"
    priority: "中"

  unrelated_failure:
    description: "与变更无关的失败"
    action: "归入原有 Bug 或新建"
    priority: "正常"

  environment_issue:
    description: "环境导致的失败"
    action: "不创建 Bug，修复环境"
    priority: "低"
```

### 5.3 回归报告

```yaml
regression_report:
  sections:
    summary:
      - regression_type: "策略类型"
      - total_cases: "总用例数"
      - pass_rate: "通过率"

    bug_verifications:
      - bug_id: "Bug ID"
      - verification_result: "验证结果"
      - notes: "备注"

    regressions_found:
      - case_id: "用例 ID"
      - description: "问题描述"
      - new_bug_id: "新建 Bug ID"

    verdict:
      - pass: "全部通过"
      - fail: "存在未解决问题"
      - partial: "部分问题需跟进"

    recommendation:
      - proceed: "可以继续"
      - fix_and_retest: "修复后重测"
      - block: "阻塞发布"
```

---

## 6. 最佳实践

### 6.1 策略选择

- **小改动优先 minimal**: 减少不必要的测试时间
- **不确定时选 risk**: 平衡效率和覆盖
- **关键发布用 full**: 降低风险
- **紧急修复先 smoke**: 快速验证

### 6.2 范围确定

- **基于变更分析**: 不要凭感觉
- **考虑调用链**: 上下游都要覆盖
- **关注历史问题区**: 易出问题的地方多测
- **听取开发建议**: 他们更了解风险点

### 6.3 执行效率

- **Bug 验证优先**: 先确认修复是否有效
- **合理并行**: 无依赖的可并行
- **智能重试**: 区分真失败和偶发
- **及时反馈**: 发现问题立即上报

### 6.4 用例维护

- **及时添加**: Bug 修复后立即添加回归用例
- **定期清理**: 移除过时用例
- **保持精简**: 回归用例要精不要多
- **标签清晰**: 方便筛选和统计

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-12 | 初始版本 |
