# 需求分析报告：SRC-058 Dev Smoke Gate 架构与测试职责分层

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | SRC-058 |
| 名称 | Dev Smoke Gate 架构与测试职责分层 |
| 分析日期 | 2026-03-18 |
| 分析人员 | 需求分析专家 |
| 关联 EPIC | EPIC-SRC-058-001 |
| 关联 FEAT | FEAT-SRC-058-001, FEAT-SRC-058-002, FEAT-SRC-058-003, FEAT-SRC-058-004, FEAT-SRC-058-005 |
| 状态 | 分析完成 |

---

## 1. 需求概述

### 1.1 目标

建立 Dev 主导的 Smoke Gate 架构，明确 Dev 和 QA 测试职责分层，解决 LEE 当前测试流程中职责边界模糊、流程复杂、测试资产不互通、门禁位置靠后和 Handoff 过多等问题，实现快速反馈的质量保障体系。

### 1.2 范围边界

**范围内：**
- Dev Smoke 作为 blocker 门禁集成到 merge 流程
- Dev 和 QA 共享同一套 Test Set 资产
- 分层 Smoke 策略：MR Smoke(P0,3-5min)、Branch Smoke(P0+P1,10-15min)、Nightly Full(全量，30-60min)
- 通过 priority 字段区分 P0/P1 核心用例与 P2 边缘场景用例
- 本地环境检测与一致性校验工具集成
- Flaky Test 自动识别与误报处理机制

**范围外：**
- QA Test Run 不直接阻塞 merge（作为独立发布前质量确认）
- 不区分 smoke 和 full Test Set（单一 Test Set 原则）
- P2 边缘场景用例为 QA 回归可选，Dev Smoke 默认不执行
- 环境自动修复功能
- 远程环境检测
- CI 环境 Flaky Test 治理

---

## 2. 模块边界定义

### 2.1 核心模块划分

```
┌─────────────────────────────────────────────────────────────────┐
│                    SRC-058: Dev Smoke Gate 架构                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Merge Gate     │  │  Test Set       │  │  Performance    │  │
│  │  Integration    │  │  Management     │  │  Optimization   │  │
│  │  (FEAT-058-001) │  │  (FEAT-058-002) │  │  (FEAT-058-003) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐                        │
│  │  Environment    │  │  Flaky Test     │  │                    │
│  │  Check          │  │  Governance     │  │                    │
│  │  (FEAT-058-004) │  │  (FEAT-058-005) │  │                    │
│  └─────────────────┘  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块边界明细

#### 模块 A: Merge Gate Integration (FEAT-SRC-058-001)

| 属性 | 定义 |
|------|------|
| **模块名称** | MR Smoke Gate Merge 门禁集成 |
| **功能职责** | 将 MR Smoke Gate(P0 only) 作为 blocker 门禁集成到 merge 流程 |
| **输入边界** | smoke_test_result, merge_request_context, gate_config |
| **输出边界** | merge_gate_status, blocker_issue_report, gate_visualization |
| **外部依赖** | Git 平台 API、CI/CD 流水线 |
| **内部依赖** | Test Set Management (获取 P0 用例) |

#### 模块 B: Test Set Management (FEAT-SRC-058-002)

| 属性 | 定义 |
|------|------|
| **模块名称** | 统一 Test Set 资产管理 |
| **功能职责** | 建立单一 Test Set 数据模型，Dev 和 QA 共享同一套测试资产 |
| **输入边界** | feat_prd, test_requirement, priority_schema |
| **输出边界** | unified_test_set_schema, priority_classification, test_case_metadata |
| **外部依赖** | 需求管理系统 |
| **内部依赖** | 无 |

#### 模块 C: Performance Optimization (FEAT-SRC-058-003)

| 属性 | 定义 |
|------|------|
| **模块名称** | Smoke 执行性能优化 |
| **功能职责** | 确保本地 Smoke 执行时间≤30 分钟，支持并行执行 |
| **输入边界** | test_execution_metrics, performance_threshold, timeout_config |
| **输出边界** | execution_time_metrics, performance_report, timeout_alerts |
| **外部依赖** | Playwright (多浏览器实例)、pytest-xdist |
| **内部依赖** | Test Set Management |

#### 模块 D: Environment Check (FEAT-SRC-058-004)

| 属性 | 定义 |
|------|------|
| **模块名称** | 本地环境检测与一致性校验 |
| **功能职责** | 提供本地环境配置检测工具与本地/CI 环境一致性校验机制 |
| **输入边界** | environment_config, consistency_check_rules, environment_detection_schema |
| **输出边界** | environment_check_result, consistency_report, execution_blocker |
| **外部依赖** | 操作系统 API (Windows/macOS/Linux) |
| **内部依赖** | Test Set Management、Performance Optimization |

#### 模块 E: Flaky Test Governance (FEAT-SRC-058-005)

| 属性 | 定义 |
|------|------|
| **模块名称** | 误报处理与 Flaky Test 治理 |
| **功能职责** | 建立 Flaky Test 识别与误报处理机制，减少误报对开发流程的干扰 |
| **输入边界** | test_execution_history, failure_pattern_analysis, retry_configuration |
| **输出边界** | retry_execution_results, flaky_test_list, test_stability_report, auto_generated_bug_tickets |
| **外部依赖** | Bug 追踪系统 |
| **内部依赖** | Test Set Management、Performance Optimization |

---

## 3. 可测试特性列表

### 3.1 功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TF-001 | Smoke Gate 作为 merge 前置条件 | Merge Gate Integration | P0 | AC-001: 未通过时阻止 merge 操作 |
| TF-002 | 100% merge 请求覆盖 | Merge Gate Integration | P0 | AC-002: 所有 merge 请求经过 Smoke Gate 检查 |
| TF-003 | Blocker 问题自动拦截 | Merge Gate Integration | P0 | AC-003: Blocker 问题自动拦截并生成报告 |
| TF-004 | 门禁状态可视化 | Merge Gate Integration | P0 | AC-004: 门禁状态在 merge 界面可视化展示 |
| TF-005 | Test Set 数据模型支持 priority 字段 | Test Set Management | P0 | AC-001: priority 字段支持 P0/P1/P2 分级 |
| TF-006 | P0/P1 用例自动包含在 Dev Smoke 执行计划 | Test Set Management | P0 | AC-002: P0/P1 用例自动包含在 Dev Smoke 执行计划中 |
| TF-007 | P2 用例标记为 QA 回归可选 | Test Set Management | P0 | AC-003: P2 用例标记为 QA 回归可选 |
| TF-008 | Dev 和 QA 共享同一 Test Set 资产 | Test Set Management | P0 | AC-004: Dev 和 QA 共享同一 Test Set 资产，无重复维护 |
| TF-009 | 测试数据管理策略实现 | Test Set Management | P0 | AC-005: 支持独立测试数据库和自动清理 |
| TF-010 | Flaky Test 标记功能 | Test Set Management | P0 | AC-006: Flaky Test 标记功能正常 |
| TF-011 | Smoke 执行时间自动测量 | Performance Optimization | P0 | AC-001: Smoke 执行时间自动测量并记录 |
| TF-012 | 执行时间超过 30 分钟时触发告警 | Performance Optimization | P0 | AC-002: 执行时间超过 30 分钟时触发告警 |
| TF-013 | 并行执行功能 | Performance Optimization | P0 | AC-004: 并行执行功能正常，支持默认 4 路并行 |
| TF-014 | 动态超时策略 | Performance Optimization | P0 | AC-005: 动态超时策略生效，根据用例数量自动调整超时阈值 |
| TF-015 | 本地环境配置自动检测 | Environment Check | P0 | AC-001: 本地环境配置自动检测并报告 |
| TF-016 | 本地/CI 环境一致性校验 | Environment Check | P0 | AC-002: 本地/CI 环境一致性校验通过 |
| TF-017 | 环境检测失败时阻止 Smoke 执行 | Environment Check | P0 | AC-003: 环境检测失败时阻止 Smoke 执行 |
| TF-018 | 跨平台检测功能 | Environment Check | P0 | AC-004: 跨平台检测功能正常，支持 Windows/macOS/Linux |
| TF-019 | 自动重试机制 | Flaky Test Governance | P0 | AC-001: 单次测试失败后自动重试，最多 3 次 |
| TF-020 | Flaky Test 自动识别 | Flaky Test Governance | P0 | AC-002: 自动识别并标记 Flaky Test（通过率<80% 持续 5 次执行） |
| TF-021 | 误报分类 | Flaky Test Governance | P0 | AC-003: 测试失败自动分类为 Blocker/Critical/Flaky |
| TF-022 | 技术债务追踪 | Flaky Test Governance | P0 | AC-004: Flaky Test 自动生成技术债务工单并通知 QA 负责人 |
| TF-023 | Flaky Test 恢复机制 | Flaky Test Governance | P0 | AC-005: Flaky Test 修复后可手动或自动清除标记 |

### 3.2 非功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TNF-001 | 分层 Smoke 执行时间 | Performance | P0 | MR Smoke≤5min、Branch Smoke≤15min、Nightly Full≤60min |
| TNF-002 | 并行执行性能提升 | Performance | P0 | 并行执行时间减少 60% 以上 |
| TNF-003 | 重试机制执行时间控制 | Performance | P0 | 重试不影响整体执行时间约束 |

### 3.3 接口特性

| ID | 特性名称 | 接口类型 | 描述 |
|----|---------|---------|------|
| TI-001 | Git 平台 Merge 请求 API | 外部接口 | 获取 MR 上下文、设置门禁状态 |
| TI-002 | Test Set 数据模型接口 | 内部接口 | 提供统一的测试用例查询接口 |
| TI-003 | 环境检测接口 | 内部接口 | 提供跨平台环境检测能力 |
| TI-004 | 性能指标采集接口 | 内部接口 | 采集和报告执行时间指标 |
| TI-005 | Bug 系统工单创建接口 | 外部接口 | 自动创建 Flaky Test 技术债务工单 |

---

## 4. 需求追溯矩阵

| 需求 ID | 需求描述 | 验收标准 | 可测试特性 | 优先级 |
|---------|---------|---------|-----------|--------|
| FEAT-SRC-058-001 | MR Smoke Gate Merge 门禁集成 | AC-001~004 | TF-001~004 | P0 |
| FEAT-SRC-058-002 | 统一 Test Set 资产管理 | AC-001~006 | TF-005~010 | P0 |
| FEAT-SRC-058-003 | Smoke 执行性能优化 | AC-001~005 | TF-011~014 | P0 |
| FEAT-SRC-058-004 | 本地环境检测与一致性校验 | AC-001~004 | TF-015~018 | P0 |
| FEAT-SRC-058-005 | 误报处理与 Flaky Test 治理 | AC-001~005 | TF-019~023 | P0 |

---

## 5. 风险评估

| 风险 ID | 风险描述 | 影响程度 | 缓解措施 |
|---------|---------|---------|---------|
| R-001 | 并行执行可能引入资源竞争问题 | 中 | 限制并行数（默认 4，最大 8），实现资源隔离 |
| R-002 | Flaky Test 自动标记可能误伤稳定用例 | 中 | 设置 5 次执行阈值，通过率<80% 才标记，支持人工复核 |
| R-003 | 环境检测过于严格可能影响开发效率 | 低 | 提供环境检测跳过选项（需审批），记录跳过日志 |
| R-004 | 重试机制可能掩盖真实问题 | 中 | 重试次数限制为 3 次，记录每次重试结果，生成稳定性报告 |

---

## 6. 测试策略建议

### 6.1 测试类型分布

| 测试类型 | 覆盖范围 | 优先级 |
|---------|---------|--------|
| 单元测试 | 各模块核心逻辑 | P0 |
| 集成测试 | 模块间交互、Git 平台集成 | P0 |
| 契约测试 | 接口契约验证 | P0 |
| 性能测试 | 执行时间、并发性能 | P0 |
| 兼容性测试 | 跨平台环境检测 | P1 |

### 6.2 测试数据需求

| 数据类型 | 描述 | 来源 |
|---------|------|------|
| Mock MR 数据 | 模拟 Merge 请求上下文 | 测试工具生成 |
| 测试用例样本 | 覆盖 P0/P1/P2 优先级的用例 | Test Set 资产 |
| 历史执行数据 | 用于 Flaky Test 识别测试 | 历史记录/模拟数据 |
| 环境配置样本 | 不同 OS 的环境配置 | 实际环境/容器模拟 |

---

## 7. 结论与建议

### 7.1 关键发现

1. **模块职责清晰**: 5 个 FEAT 模块职责边界明确，相互依赖关系合理
2. **验收标准完整**: 每个 FEAT 都有明确的验收标准（AC），可直接转化为测试用例
3. **可追溯性强**: 需求链完整（SRC → EPIC → FEAT → AC → Test Case）
4. **风险可控**: 主要风险已识别并有缓解措施

### 7.2 测试重点建议

1. **优先级 P0**: Merge Gate 拦截逻辑、Test Set priority 分级、执行时间约束
2. **核心场景**: 正常通过流程、Blocker 拦截流程、Flaky Test 识别流程
3. **边界场景**: 超时处理、重试耗尽、环境检测失败

### 7.3 下一步行动

1. 基于本分析报告生成 Test Set 设计资产
2. 制定详细测试计划
3. 准备测试环境和数据
4. 开发自动化测试脚本

---

*文档生成时间: 2026-03-18T11:54:00+08:00*
