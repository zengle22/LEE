# Test Execution Skill v1.0
# 测试执行技能规范

## 概述

测试执行技能定义了如何有效执行各类测试用例的方法论和最佳实践。
包括测试准备、执行策略、问题记录、结果分析等核心能力。

## 技能标识

- **ID**: skill.test.test_execution
- **名称**: Test Execution
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.smoke_test_executor
- agent.test.system_test_executor
- agent.test.regression_test_executor

---

## 1. 测试准备

### 1.1 环境检查清单

在执行任何测试之前，必须完成以下检查：

```yaml
environment_checklist:
  deployment:
    - 目标版本已部署: boolean
    - 部署版本与提测版本一致: boolean
    - 服务健康检查通过: boolean

  dependencies:
    - 数据库连接正常: boolean
    - 缓存服务可用: boolean
    - 消息队列可用: boolean
    - 外部API可访问: boolean

  data:
    - 测试数据已准备: boolean
    - 测试账号可用: boolean
    - 数据隔离已配置: boolean

  monitoring:
    - 日志可访问: boolean
    - 监控可用: boolean
    - Trace ID可追踪: boolean
```

### 1.2 测试数据准备

```yaml
test_data_strategy:
  isolation: true  # 测试数据必须隔离
  cleanup: "after_test"  # 测试后清理

  data_sources:
    - type: "fixture"
      description: "预定义的测试数据"
      location: "test-data/fixtures/"

    - type: "generated"
      description: "动态生成的测试数据"
      generator: "test-data-factory"

    - type: "snapshot"
      description: "生产数据脱敏快照"
      location: "test-data/snapshots/"
```

---

## 2. 执行策略

### 2.1 优先级执行

```yaml
priority_execution:
  order: [P0, P1, P2]

  P0:
    description: "核心链路，必须全部通过"
    fail_fast: true
    max_failures: 0

  P1:
    description: "重要功能，需关注"
    fail_fast: false
    max_failures: 3

  P2:
    description: "次要功能，可容忍"
    fail_fast: false
    max_failures: 10
```

### 2.2 模块执行

```yaml
module_execution:
  strategy: "dependency_order"  # 按依赖顺序

  parallel_allowed: true
  max_parallel_modules: 3

  module_isolation:
    enabled: true
    reset_between_modules: true
```

### 2.3 失败处理

```yaml
failure_handling:
  on_failure:
    - capture_screenshot: true
    - capture_logs: true
    - capture_network: true
    - capture_trace_id: true

  retry_policy:
    enabled: true
    max_retries: 2
    retry_on:
      - "NetworkError"
      - "TimeoutError"
    never_retry:
      - "AssertionError"
      - "FunctionalError"

  escalation:
    p0_failure: "immediate"
    p1_consecutive_failures: 3
```

---

## 3. 问题记录

### 3.1 Bug 创建标准

每个失败用例必须创建 Bug 契约，包含：

```yaml
bug_creation_standard:
  required_fields:
    - bug_id: "自动生成"
    - title: "简洁描述问题"
    - severity: "基于测试优先级和影响范围"
    - type: "functional | performance | ..."
    - detected_in: "版本和环境信息"
    - repro: "完整的复现步骤"

  evidence_required:
    - logs: "相关日志片段"
    - screenshots: "UI 问题必须"
    - trace_id: "后端问题必须"
    - network: "API 问题必须"
```

### 3.2 严重级别判定

```yaml
severity_rules:
  P0:
    conditions:
      - "核心功能完全不可用"
      - "系统崩溃或无法启动"
      - "数据损坏或丢失"
      - "安全漏洞"
    examples:
      - "登录功能完全失效"
      - "支付流程中断"
      - "用户数据错乱"

  P1:
    conditions:
      - "主流程可用但有明显错误"
      - "影响大量用户"
      - "有临时规避方案"
    examples:
      - "列表页面排序错误"
      - "导出功能失效"

  P2:
    conditions:
      - "非主流程问题"
      - "体验瑕疵"
      - "影响少量用户"
    examples:
      - "样式不对齐"
      - "提示语不准确"

  P3:
    conditions:
      - "文案错误"
      - "界面美观问题"
      - "优化建议"
```

---

## 4. 结果分析

### 4.1 测试指标

```yaml
test_metrics:
  execution:
    - total_cases: "总用例数"
    - passed_cases: "通过数"
    - failed_cases: "失败数"
    - skipped_cases: "跳过数"
    - blocked_cases: "阻塞数"

  derived:
    - pass_rate: "passed / total * 100"
    - failure_rate: "failed / total * 100"
    - execution_rate: "(total - skipped - blocked) / total * 100"

  by_dimension:
    - by_priority: [P0, P1, P2]
    - by_type: [functional, integration, api, ...]
    - by_module: [auth, order, payment, ...]
```

### 4.2 趋势分析

```yaml
trend_analysis:
  compare_with:
    - previous_cycle: "上一轮测试"
    - previous_version: "上一版本"

  indicators:
    - new_bugs_trend: "新发现 Bug 趋势"
    - fix_rate_trend: "修复率趋势"
    - regression_rate: "回归率"

  alerts:
    - bug_increase_threshold: 20  # Bug 增长超过 20% 报警
    - regression_threshold: 5     # 回归超过 5% 报警
```

---

## 5. 执行工作流

### 5.1 冒烟测试执行流程

```
1. 环境检查
   ├── 部署验证
   ├── 依赖检查
   └── 健康检查

2. 用例执行
   ├── P0 用例 (fail-fast)
   └── P1 用例 (继续执行)

3. 结果处理
   ├── 失败 → 创建 Bug + 打回
   └── 通过 → 进入系统测试
```

### 5.2 系统测试执行流程

```
1. 环境准备
   ├── 数据准备
   └── 环境验证

2. 模块执行
   ├── 按依赖顺序
   ├── 可并行模块
   └── 持续执行

3. 问题处理
   ├── 创建 Bug 契约
   ├── 关联测试用例
   └── 记录证据

4. 结果汇总
   ├── 模块报告
   └── 整体报告
```

### 5.3 回归测试执行流程

```
1. 范围确定
   ├── 变更影响分析
   └── 回归策略选择

2. 用例筛选
   ├── Bug 回归用例
   ├── 影响范围用例
   └── 冒烟用例 (可选)

3. 执行 & 验证
   ├── Bug 修复验证
   └── 回归检测

4. 结果报告
   ├── 验证结果
   ├── 回归问题
   └── 建议
```

---

## 6. 最佳实践

### 6.1 执行效率

- **并行执行**: 无依赖的模块并行执行
- **智能重试**: 区分可重试和不可重试的失败
- **早期发现**: P0 优先执行，fail-fast
- **资源复用**: 测试数据和环境复用

### 6.2 问题定位

- **完整证据**: 每个失败都要收集完整证据
- **可复现性**: 复现步骤必须明确
- **根因分析**: 区分环境问题和代码问题
- **快速反馈**: 阻塞问题立即上报

### 6.3 质量保障

- **100% 执行**: 不跳过任何计划用例
- **独立执行**: 用例之间无依赖
- **数据隔离**: 测试数据不影响其他测试
- **结果可追溯**: 所有结果可审计

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-12 | 初始版本 |
