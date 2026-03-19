# 需求分析报告：SRC-058 Dev Smoke Gate 架构

**分析日期**: 2026-03-18  
**分析师**: Requirement Analysis Agent  
**模块**: SRC-058  
**EPIC**: EPIC-SRC-058-001  
**FEAT Freeze**: FEAT-FREEZE-SRC-058-001  

---

## 1. 执行摘要

本报告分析 SRC-058 模块的 Dev Smoke Gate 架构需求，从 5 个冻结 FEAT 中提取模块边界和可测试特性，为后续 Test Set 设计和测试用例生成提供输入。

**核心目标**: 建立 Dev Smoke Gate 体系，实现 MR 合并前的自动化质量门禁，确保问题代码不进入主干。

---

## 2. 需求文档结构解析

### 2.1 FEAT 清单

| FEAT ID | 标题 | 优先级 | 状态 |
|---------|------|--------|------|
| FEAT-SRC-058-001 | MR Smoke Gate Merge 门禁集成 | P0 | frozen |
| FEAT-SRC-058-002 | 统一 Test Set 资产管理 | P0 | frozen |
| FEAT-SRC-058-003 | Smoke 执行性能优化 | P1 | frozen |
| FEAT-SRC-058-004 | 本地环境检测与一致性校验 | P1 | frozen |
| FEAT-SRC-058-005 | 误报处理与 Flaky Test 治理 | P1 | frozen |

### 2.2 需求层次

```
EPIC-SRC-058-001 (Dev Smoke Gate 架构与测试职责分层)
├── FEAT-SRC-058-001 (Merge 门禁集成)
├── FEAT-SRC-058-002 (Test Set 资产管理) ─┬→ FEAT-SRC-058-003 (性能优化)
│                                        ├→ FEAT-SRC-058-004 (环境检测)
│                                        └→ FEAT-SRC-058-005 (Flaky 治理)
├── FEAT-SRC-058-003 (Smoke 执行性能优化)
├── FEAT-SRC-058-004 (本地环境检测)
└── FEAT-SRC-058-005 (Flaky Test 治理)
```

---

## 3. 模块边界定义

### 3.1 模块名称
**Dev Smoke Gate Architecture (SRC-058)**

### 3.2 模块描述

Dev Smoke Gate 架构与测试职责分层模块，构建从 MR 合并前到本地测试执行的完整质量保障体系，核心能力包括：

1. **Merge 门禁层**: MR 合并前的强制性 Smoke 检查
2. **资产管理层**: 统一的 Test Set 数据模型
3. **执行优化层**: 本地 Smoke 性能优化
4. **环境保障层**: 本地/CI 环境一致性校验
5. **质量治理层**: Flaky Test 识别与误报处理

### 3.3 范围边界

#### 3.3.1 In Scope

| 类别 | 具体内容 |
|------|----------|
| **功能范围** | Merge 流程中的 Smoke Gate 集成 |
| | Test Set 数据模型与 priority 分级 (P0/P1/P2) |
| | P0/P1 用例的 Dev Smoke 执行 |
| | 本地 Smoke 性能测量与优化 |
| | 跨平台环境检测 (Windows/macOS/Linux) |
| | Flaky Test 自动识别与重试机制 |
| **性能范围** | 本地执行时间≤30分钟 |
| | MR Gate 执行时间 3-5分钟 (P0 only) |
| **平台范围** | Windows、macOS、Linux 本地环境 |

#### 3.3.2 Out of Scope

| 类别 | 具体内容 | 原因 |
|------|----------|------|
| 执行范围 | QA Test Run 直接阻塞 merge | 由 QA 部门负责 |
| | P2 用例作为 Dev Smoke 默认执行 | 回归测试范畴 |
| 性能范围 | CI 环境性能优化 | 本机优化为主 |
| | 完整回归测试性能约束 | 仅 Smoke 测试 |
| 环境范围 | 环境自动修复 | 检测为主，修复为辅 |
| | 远程环境检测 | 本地环境为主 |
| 治理范围 | CI 环境 Flaky Test 治理 | 由 QA 负责 |
| | 历史 Flaky Test 数据迁移 | 仅新识别 |

### 3.4 接口定义

#### 3.4.1 输入接口

| 输入名称 | 来源 | 用途 | 关联 FEAT |
|----------|------|------|-----------|
| smoke_test_result | 测试执行引擎 | Gate 判定依据 | FEAT-SRC-058-001 |
| merge_request_context | Git 平台 | MR 信息获取 | FEAT-SRC-058-001 |
| gate_config | 配置文件 | Gate 规则配置 | FEAT-SRC-058-001 |
| feat_prd | 需求文档 | 测试需求来源 | FEAT-SRC-058-002 |
| test_requirement | 需求分析 | 用例设计输入 | FEAT-SRC-058-002 |
| priority_schema | 规范定义 | Priority 分级规则 | FEAT-SRC-058-002 |
| test_execution_metrics | 执行监控 | 性能数据采集 | FEAT-SRC-058-003 |
| environment_config | 环境配置 | 检测基准 | FEAT-SRC-058-004 |
| test_execution_history | 历史记录 | Flaky 分析依据 | FEAT-SRC-058-005 |

#### 3.4.2 输出接口

| 输出名称 | 消费者 | 用途 | 关联 FEAT |
|----------|--------|------|-----------|
| merge_gate_status | Git 平台 | MR 合并控制 | FEAT-SRC-058-001 |
| blocker_issue_report | Dev/QA | 问题追踪 | FEAT-SRC-058-001 |
| gate_visualization | UI 层 | 状态展示 | FEAT-SRC-058-001 |
| unified_test_set_schema | 测试系统 | 资产管理 | FEAT-SRC-058-002 |
| execution_time_metrics | 监控系统 | 性能分析 | FEAT-SRC-058-003 |
| environment_check_result | 执行引擎 | 执行控制 | FEAT-SRC-058-004 |
| flaky_test_list | QA 系统 | 质量治理 | FEAT-SRC-058-005 |
| test_stability_report | 质量看板 | 稳定性分析 | FEAT-SRC-058-005 |

---

## 4. 可测试特性列表

### 4.1 TF-001: MR Smoke Gate Merge Integration

**基本信息**
- **ID**: TF-001
- **名称**: MR Smoke Gate Merge 门禁集成
- **优先级**: P0
- **关联 FEAT**: FEAT-SRC-058-001

**功能描述**
MR Smoke Gate 作为 blocker 门禁集成到 merge 流程，实现 100% merge 请求覆盖，自动拦截 blocker 问题，3-5 分钟内完成。

**验收标准 (AC)**
| AC ID | 描述 | 测试类型 |
|-------|------|----------|
| AC-001 | Smoke Gate 作为 merge 前置条件，未通过时阻止 merge 操作 | 集成测试 |
| AC-002 | 所有 merge 请求 100% 经过 Smoke Gate 检查 | 功能测试 |
| AC-003 | Blocker 问题自动拦截并生成报告 | 功能测试 |
| AC-004 | 门禁状态在 merge 界面可视化展示 | UI 测试 |
| 隐含 | 执行时间≤5 分钟 | 性能测试 |

**测试重点**
- merge_gate_integration: Merge 流程集成点
- blocker_detection: Blocker 问题识别逻辑
- status_visualization: 状态可视化展示
- execution_time_constraint: 执行时间约束验证

**依赖**
- 依赖 FEAT-SRC-058-002: 需要 Test Set 定义测试范围
- 依赖 FEAT-SRC-058-004: 需要环境检测通过

---

### 4.2 TF-002: Unified Test Set Asset Management

**基本信息**
- **ID**: TF-002
- **名称**: 统一 Test Set 资产管理
- **优先级**: P0
- **关联 FEAT**: FEAT-SRC-058-002

**功能描述**
建立单一 Test Set 数据模型，Dev 和 QA 共享同一套测试资产，通过 priority 字段区分使用场景。

**Priority 定义**
| Level | 名称 | 执行方 | 用途 |
|-------|------|--------|------|
| P0 | Critical | Dev | Smoke Gate 必执行，阻塞性 |
| P1 | High | Dev | Smoke Gate 必执行，重要功能 |
| P2 | Medium | QA | 回归测试可选 |

**验收标准 (AC)**
| AC ID | 描述 | 测试类型 |
|-------|------|----------|
| AC-001 | Test Set 数据模型支持 priority 字段定义 | 单元测试 |
| AC-002 | P0/P1 用例自动包含在 Dev Smoke 执行计划中 | 集成测试 |
| AC-003 | P2 用例标记为 QA 回归可选 | 功能测试 |
| AC-004 | Dev 和 QA 共享同一 Test Set 资产，无重复维护 | 集成测试 |
| AC-005 | 测试数据管理策略已实现 | 功能测试 |
| AC-006 | Flaky Test 标记功能正常 | 功能测试 |

**测试重点**
- schema_validation: Test Set Schema 验证
- priority_classification: Priority 分级逻辑
- asset_sharing: 资产共享机制
- test_data_management: 测试数据管理
- flaky_marking: Flaky 标记功能

---

### 4.3 TF-003: Smoke Execution Performance Optimization

**基本信息**
- **ID**: TF-003
- **名称**: Smoke 执行性能优化
- **优先级**: P1
- **关联 FEAT**: FEAT-SRC-058-003

**功能描述**
确保本地 Smoke 执行时间≤30 分钟，在合理反馈时间内完成完整测试覆盖。

**性能规格**
| 指标 | 目标值 | 说明 |
|------|--------|------|
| 本地执行时间 | ≤30 分钟 | 完整 Smoke 测试 |
| MR Gate 时间 | ≤5 分钟 | 仅 P0 用例 |
| 并行度 | 默认 4，最大 8 | pytest-xdist |
| 超时策略 | 动态调整 | 基础 15 分钟 + 按用例增加 |

**验收标准 (AC)**
| AC ID | 描述 | 测试类型 |
|-------|------|----------|
| AC-001 | Smoke 执行时间自动测量并记录 | 性能测试 |
| AC-002 | 执行时间超过 30 分钟时触发告警 | 功能测试 |
| AC-003 | 性能报告生成并可视化 | 功能测试 |
| AC-004 | 并行执行功能正常，支持默认 4 路并行 | 性能测试 |
| AC-005 | 动态超时策略生效 | 功能测试 |

**测试重点**
- execution_time_measurement: 执行时间测量
- performance_alerting: 性能告警
- parallel_execution: 并行执行
- dynamic_timeout: 动态超时
- playwright_optimization: Playwright 优化

---

### 4.4 TF-004: Local Environment Detection

**基本信息**
- **ID**: TF-004
- **名称**: 本地环境检测与一致性校验
- **优先级**: P1
- **关联 FEAT**: FEAT-SRC-058-004

**功能描述**
提供本地环境配置检测工具与本地/CI 环境一致性校验机制，避免因环境差异导致的测试误报或漏报。

**检测范围**
| 检测项 | Windows | macOS | Linux |
|--------|---------|-------|-------|
| 操作系统版本 | ✓ | ✓ | ✓ |
| 路径分隔符 | ✓ | ✓ | ✓ |
| 环境变量兼容性 | ✓ | ✓ | ✓ |
| Docker 环境 | 可选 | 可选 | 可选 |

**验收标准 (AC)**
| AC ID | 描述 | 测试类型 |
|-------|------|----------|
| AC-001 | 本地环境配置自动检测并报告 | 功能测试 |
| AC-002 | 本地/CI 环境一致性校验通过 | 集成测试 |
| AC-003 | 环境检测失败时阻止 Smoke 执行 | 功能测试 |
| AC-004 | 跨平台检测功能正常 | 兼容性测试 |

**测试重点**
- environment_detection: 环境检测逻辑
- consistency_validation: 一致性校验
- execution_blocking: 执行阻塞机制
- cross_platform_support: 跨平台支持

---

### 4.5 TF-005: Flaky Test Governance

**基本信息**
- **ID**: TF-005
- **名称**: 误报处理与 Flaky Test 治理
- **优先级**: P1
- **关联 FEAT**: FEAT-SRC-058-005

**功能描述**
建立 Flaky Test 识别与误报处理机制，减少误报对开发流程的干扰，提升 Smoke Gate 可信度。

**核心机制**
| 机制 | 规格 |
|------|------|
| 自动重试 | 最多 3 次 |
| Flaky 识别 | 连续 5 次执行通过率<80% |
| 失败分类 | Blocker/Critical/Flaky |
| 债务追踪 | 自动生成技术债务工单 |

**验收标准 (AC)**
| AC ID | 描述 | 测试类型 |
|-------|------|----------|
| AC-001 | 单次测试失败后自动重试，最多 3 次 | 功能测试 |
| AC-002 | 自动识别并标记 Flaky Test | 功能测试 |
| AC-003 | 测试失败自动分类 | 功能测试 |
| AC-004 | Flaky Test 自动生成技术债务工单 | 集成测试 |
| AC-005 | Flaky Test 修复后可清除标记 | 功能测试 |

**测试重点**
- auto_retry_mechanism: 自动重试机制
- flaky_detection: Flaky 检测算法
- failure_classification: 失败分类
- debt_tracking: 债务追踪
- flaky_recovery: Flaky 恢复

---

## 5. 依赖关系分析

### 5.1 FEAT 间依赖

```
FEAT-SRC-058-002 (Test Set 资产管理)
├── 被 FEAT-SRC-058-003 依赖 → 提供 Test Set 定义用于性能基线
├── 被 FEAT-SRC-058-004 依赖 → 提供 Test Set 定义检测目标
└── 被 FEAT-SRC-058-005 依赖 → 存储 Flaky 标记

FEAT-SRC-058-003 (性能优化)
└── 被 FEAT-SRC-058-005 依赖 → 重试影响执行时间
```

### 5.2 测试依赖

| 测试项 | 依赖项 | 依赖原因 |
|--------|--------|----------|
| TF-001 (Merge Gate) | TF-002 | 需要 Test Set 定义测试范围 |
| TF-001 (Merge Gate) | TF-004 | 需要环境检测通过 |
| TF-003 (性能优化) | TF-002 | 需要 Test Set 进行性能基线测量 |
| TF-005 (Flaky 治理) | TF-002 | 需要 Test Set 存储 Flaky 标记 |
| TF-005 (Flaky 治理) | TF-003 | 重试机制影响执行时间 |

---

## 6. 测试数据需求

### 6.1 测试数据策略

| 项目 | 规格 |
|------|------|
| 数据隔离 | 独立测试数据库 |
| 数据清理 | 自动清理 |
| 数据生成 | 基于 Fixture |

### 6.2 Fixtures 需求

| Fixture | 用途 | 关联 TF |
|---------|------|---------|
| sample_merge_requests | 模拟 MR 数据 | TF-001 |
| mock_test_results | 模拟测试结果 | TF-001, TF-005 |
| environment_configs | 环境配置数据 | TF-004 |
| priority_test_cases | 分级测试用例 | TF-002 |
| flaky_test_samples | Flaky 测试样本 | TF-005 |

### 6.3 测试环境

| 环境 | 用途 | 平台 |
|------|------|------|
| local_windows | 本地测试 | Windows |
| local_macos | 本地测试 | macOS |
| local_linux | 本地测试 | Linux |
| ci_simulation | CI 模拟 | 跨平台 |

---

## 7. 风险与注意事项

### 7.1 测试风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 跨平台行为差异 | 测试不稳定 | 在三大平台分别验证 |
| 执行时间波动 | 性能测试不可靠 | 多次采样取平均 |
| Flaky 检测滞后 | 早期误判 | 结合人工复核 |
| 环境检测过度严格 | 阻碍正常开发 | 配置化白名单 |

### 7.2 测试建议

1. **优先级**: 优先测试 P0 特性 (TF-001, TF-002)
2. **并行**: TF-003, TF-004, TF-005 可并行测试
3. **回归**: 建立稳定的回归测试基线
4. **监控**: 持续监控 Flaky Test 率

---

## 8. 结论

本分析报告从 5 个冻结 FEAT 中提取了 5 个可测试特性 (TF-001 ~ TF-005)，定义了完整的模块边界和测试范围。

**核心交付物**:
1. 模块边界定义 (Module Boundary)
2. 可测试特性列表 (Testable Features)
3. 依赖关系映射 (Dependencies)
4. 测试数据需求 (Data Requirements)

**下一步**: 基于本分析报告，可进行详细的 Test Set 设计和测试用例生成。

---

## 附录

### A. 参考文档

- EPIC-SRC-058-001: Dev Smoke Gate 架构与测试职责分层
- FEAT-SRC-058-001: MR Smoke Gate Merge 门禁集成
- FEAT-SRC-058-002: 统一 Test Set 资产管理
- FEAT-SRC-058-003: Smoke 执行性能优化
- FEAT-SRC-058-004: 本地环境检测与一致性校验
- FEAT-SRC-058-005: 误报处理与 Flaky Test 治理

### B. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-18 | 初始版本，完成需求分析 |
