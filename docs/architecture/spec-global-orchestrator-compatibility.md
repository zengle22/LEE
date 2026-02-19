---
title: spec-global Orchestrator 能力矩阵
author: LEE Team
date: 2026-02-06
version: 1.0
last_updated: 2026-02-19
---

# spec-global Orchestrator 能力矩阵

> **版本**: 1.0
> **创建日期**: 2026-02-05
> **用途**: 追踪 spec-global 规范在 Orchestrator 中的支持状态
> **更新频率**: 每周更新，或在实现新特性后更新

---

## 📊 能力矩阵总览

### 图例说明

| 状态 | 说明 | 示例 |
|------|------|------|
| ✅ **完全支持** | 已实现并经过测试验证 | 基础步骤执行 |
| 🟡 **部分支持** | 有基础实现，但缺少完整语义 | 简化门禁验证 |
| ❌ **不支持** | 完全未实现 | 状态机循环 |
| 🚧 **实施中** | 正在开发中 | 变量解析器 |
| 📋 **计划中** | 已列入开发计划 | 豁免管理 |

---

## 一、工作流结构特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `kind` | `workflow` | ✅ 已检测 | ✅ 是 | P2 | P0.2 |
| `version` | `1.0` | 🟡 未校验 | ✅ 是 | P2 | P2 |
| `id` | 工作流 ID | ✅ 支持 | ✅ 是 | - | - |
| `name` | 工作流名称 | ✅ 支持 | ✅ 是 | - | - |
| `description` | 工作流描述 | ✅ 支持 | ✅ 是 | - | - |
| `owner` | 负责人 | 🟡 忽略 | ✅ 是 | P2 | P3 |
| `tags` | 标签列表 | 🟡 忽略 | ✅ 是 | P2 | P3 |
| `concepts` | 业务概念定义 | ❌ 不支持 | ✅ 是 | P2 | P3 |

---

## 二、契约系统特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `contracts.inputs` | 输入契约定义 | 🟡 未验证 | ✅ 是 (4个) | P0 | P0.2 |
| `contracts.outputs` | 输出契约定义 | 🟡 未验证 | ✅ 是 (3个) | P1 | P1.2 |
| 契约路径解析 | 相对路径解析 | ❌ 不支持 | ✅ 是 | P0 | P0.3 |
| 契约 schema 验证 | JSON Schema 验证 | ❌ 不支持 | ✅ 是 | P1 | P1.2 |
| 契约结构验证 | 结构完整性检查 | ❌ 不支持 | ✅ 是 | P2 | P2 |

### QA 工作流输入契约

| 契约 ID | 路径 | 必需 | 状态 |
|---------|------|------|------|
| `prd` | `../../../prd/contracts/frozen-detailed-prd-contract/v1/schema.json` | ✅ | 🟡 未验证 |
| `technical_architecture` | `../../../dev/contracts/frozen-technical-architecture-contract/v1/schema.json` | ✅ | 🟡 未验证 |
| `ui_prototype` | `../../../ui/contracts/frozen-ui-prototype-contract/v1/schema.json` | ✅ | 🟡 未验证 |
| `ui_page` | `../../../ui/contracts/ui-page-contract/v1/schema.yaml` | ✅ | 🟡 未验证 |

### QA 工作流输出契约

| 契约 ID | 路径 | 状态 |
|---------|------|------|
| `test_case_design` | `../../contracts/test-case-design-contract/v1/schema.yaml` | 🟡 未验证 |
| `test_cases` | `../../contracts/test-case/v1/schema.yaml` | 🟡 未验证 |
| `e2e_scripts` | `../../contracts/e2e-script-contract/v1/schema.yaml` | 🟡 未验证 |

---

## 三、状态机特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `state_machine.states` | 状态列表 | ❌ 不支持 | ✅ 是 (11个) | P0 | P1.1 |
| `state_machine.transitions` | 状态转换规则 | ❌ 不支持 | ✅ 是 (17个) | P0 | P1.1 |
| 显式状态转换 | 触发器驱动的转换 | ❌ 不支持 | ✅ 是 | P0 | P1.1 |
| 循环状态转换 | REVIEW_REVISION ↔ REVIEW | ❌ 不支持 | ✅ 是 | P1 | P1.1 |
| BLOCKED 终止态 | 阻塞状态 | 🟡 基础 FAILED | ✅ 是 | P0 | P1.1 |

### QA 工作流状态机

| 状态 | 说明 | 当前支持 |
|------|------|----------|
| INIT | 初始化 | 🟡 PENDING |
| INPUT_VALIDATION | 输入验证 | ❌ |
| REQUIREMENT_ALIGNMENT | 需求对齐 | ❌ |
| FEATURE_CALIBRATION | 功能点校准 | ❌ |
| BRANCH_COVERAGE_DESIGN | 分支覆盖设计 | ❌ |
| SPECIALIZED_TEST_DESIGN | 专项测试设计 | ❌ |
| TEST_CASE_REVIEW | 用例评审 | ❌ |
| REVIEW_REVISION | 评审修订 | ❌ |
| PLAYWRIGHT_GENERATION | Playwright 脚本生成 | ❌ |
| COMPLETED | 完成 | ✅ COMPLETED |
| BLOCKED | 阻塞 | 🟡 FAILED |

---

## 四、步骤执行特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `stages` | 阶段分组 | ❌ 未解析 | ✅ 是 (8个) | P0 | P0.2 |
| `stages[].steps` | 嵌套步骤 | 🟡 展平处理 | ✅ 是 (21个) | P0 | P0.2 |
| `step.id` | 步骤标识 | ✅ 支持 | ✅ 是 | - | - |
| `step.name` | 步骤名称 | ✅ 支持 | ✅ 是 | - | - |
| `step.run` | Agent/Skill 引用 | 🟡 部分支持 | ✅ 是 | P0 | P0.2 |
| `step.condition` | 条件执行 | ❌ 不支持 | ✅ 是 (2个) | P1 | P1.3 |
| `step.inputs` | 输入定义 | 🟡 基础支持 | ✅ 是 | P0 | P0.3 |
| `step.outputs` | 输出定义 | 🟡 基础支持 | ✅ 是 | P0 | P0.3 |
| `step.gate` | 门禁引用 | ❌ 不支持 | ✅ 是 (2个) | P0 | P1.2 |
| `step.post_gate` | 后置门禁 | ❌ 不支持 | ❌ 否 | P1 | P1.2 |
| `step.on_failure` | 失败处理 | ❌ 不支持 | ✅ 是 | P1 | P1.2 |
| `step.dependencies` | 依赖关系 | 🟡 部分支持 | ✅ 是 | P1 | P1.3 |

### QA 工作流条件执行步骤

| 步骤 ID | 条件表达式 | 当前支持 |
|---------|-----------|----------|
| `s2_2_resolve_conflicts` | `consistency_matrix.conflicts > 0` | ❌ |
| `s6_3_incorporate_feedback` | `review_status == 'rejected'` | ❌ |

---

## 五、变量引用特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `$inputs.xxx` | 工作流输入引用 | ❌ 不支持 | ✅ 广泛使用 | P0 | P0.3 |
| `$sX_Y_zzz` | 步骤输出引用 | ❌ 不支持 | ✅ 广泛使用 | P0 | P0.3 |
| 多级嵌套引用 | `consistency_matrix.conflicts` | ❌ 不支持 | ✅ 是 | P0 | P0.3 |
| 条件表达式 | 布尔逻辑表达式 | ❌ 不支持 | ✅ 是 | P1 | P1.3 |

### QA 工作流变量引用示例

| 类型 | 示例 | 当前支持 |
|------|------|----------|
| 输入引用 | `$inputs.prd` | ❌ |
| 简单输出引用 | `$s3_1_extract_features.feature_list` | ❌ |
| 嵌套输出引用 | `$s2_1_validate_consistency.consistency_matrix.conflicts` | ❌ |
| 跨 stage 引用 | `$s3_4_generate_calibration_report.calibration_report` (在 s6 中) | ❌ |

---

## 六、门禁系统特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `gates` | 门禁定义 | ❌ 不支持 | ✅ 是 (2个) | P0 | P1.2 |
| `mandatory_criteria` | 强制标准 (0容忍) | ❌ 不支持 | ✅ 是 | P0 | P1.2 |
| `threshold_criteria` | 阈值标准 (可警告) | ❌ 不支持 | ✅ 是 | P0 | P1.2 |
| `risk_acceptance_criteria` | 风险可接受标准 | ❌ 不支持 | ✅ 是 | P1 | P1.2 |
| `exemption_policy` | 豁免管理 | ❌ 不支持 | ✅ 是 | P1 | P2 |
| `signoff_requirements` | 签字要求 | ❌ 不支持 | ✅ 是 | P1 | P1.4 |
| `checklist` | 检查清单 | ❌ 不支持 | ✅ 是 | P1 | P1.4 |
| `timeout/escalate` | 超时升级 | ❌ 不支持 | ✅ 是 | P2 | P2 |

### QA 工作流门禁

| 门禁 ID | 类型 | 强制标准数 | 阈值标准数 | 当前支持 |
|---------|------|-----------|-----------|----------|
| `gate.qa.design_input_gate` | 输入验证 | 5 | 3 | ❌ |
| `gate.qa.test_case_review_gate` | 用例评审 | 5 | 6 | ❌ |

### design_input_gate 强制标准

| 标准 ID | 名称 | 规则 | 当前支持 |
|---------|------|------|----------|
| C001 | PRD 已冻结 | `prd.is_frozen == true` | ❌ |
| C002 | 技术架构已冻结 | `tech_arch.is_frozen == true` | ❌ |
| C003 | UI 原型已冻结 | `ui_prototype.is_frozen == true` | ❌ |
| C004 | PRD 包含至少 1 个功能点 | `COUNT(prd.features) >= 1` | ❌ |
| C005 | 每个功能点都有验收标准 | `ALL(prd.features) HAVE acceptance_criteria` | ❌ |

---

## 七、人类介入特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `human_in_the_loop` | 人类介入定义 | ❌ 不支持 | ✅ 是 | P1 | P1.4 |
| 审批链 | 多角色签字 | ❌ 不支持 | ✅ 是 | P1 | P1.4 |
| 超时处理 | timeout + escalate | ❌ 不支持 | ✅ 是 | P2 | P2 |
| 升级策略 | 24h/48h/72h | ❌ 不支持 | ✅ 是 | P2 | P2 |
| 审批标准 | 量化标准 | ❌ 不支持 | ✅ 是 | P1 | P1.4 |

### QA 工作流人类介入

| 阶段 | 类型 | 超时 | 审批链 | 当前支持 |
|------|------|------|--------|----------|
| s6_test_case_review | approval | 72h | qa_lead (必需), tech_lead (可选), pm (可选) | ❌ |

---

## 八、错误处理特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `error_handling` | 错误处理策略 | ❌ 不支持 | ✅ 是 (7种) | P1 | P1.2 |
| `block_and_report` | 阻塞并报告 | 🟡 基础 FAILED | ✅ 是 | P1 | P1.2 |
| `retry_with_fallback` | 重试 + 降级 | ❌ 不支持 | ✅ 是 | P2 | P2 |
| `escalate_and_block` | 升级并阻塞 | ❌ 不支持 | ✅ 是 | P1 | P1.2 |
| `partial_delivery` | 部分交付 | ❌ 不支持 | ✅ 是 | P2 | P2 |

### QA 工作流错误处理

| 错误场景 | 动作 | 目标状态 | 当前支持 |
|----------|------|----------|----------|
| input_validation_failed | block_and_report | BLOCKED | 🟡 FAILED |
| requirement_alignment_failed | escalate_and_block | BLOCKED | 🟡 FAILED |
| feature_calibration_failed | escalate_and_block | BLOCKED | 🟡 FAILED |
| branch_coverage_generation_failed | retry_with_fallback (max 3) | - | ❌ |
| specialized_test_generation_failed | partial_delivery | - | ❌ |
| playwright_generation_failed | retry_with_manual_flag (max 2) | - | ❌ |
| review_timeout | escalate | - | ❌ |
| revision_timeout | escalate_to_governance | BLOCKED | ❌ |

---

## 九、可观测性特性

| 特性 | spec-global 定义 | Orchestrator 支持 | QA 工作流使用 | 优先级 | 实施阶段 |
|------|-----------------|------------------|--------------|--------|----------|
| `observability.metrics` | 指标定义 | ❌ 不支持 | ✅ 是 | P2 | P3 |
| `observability.dashboards` | 仪表板定义 | ❌ 不支持 | ✅ 是 | P2 | P3 |
| `observability.alerts` | 告警规则 | ❌ 不支持 | ✅ 是 | P2 | P3 |
| `quality_metrics` | 质量指标 | ❌ 不支持 | ✅ 是 | P2 | P3 |

---

## 十、优先级实施路线图

### P0 - 立即实施（2天内）

| 特性 | 实施内容 | 交付物 |
|------|---------|--------|
| 契约路径解析 | 解析相对路径为绝对路径 | `ContractResolver` |
| 变量引用解析 | 支持 `$inputs.xxx` | `VariableResolver` |
| Stages 展平 | 将 `stages[].steps` 展平为 steps | `SpecGlobalParser` |
| 步骤引用解析 | 支持 `run: agent.qa.xxx` | `SpecGlobalParser` |

### P1 - QA 优先（1-2周）

| 特性 | 实施内容 | 交付物 |
|------|---------|--------|
| 状态机执行 | 支持 11 个状态和转换 | `WorkflowStateMachineV2` |
| 门禁规则引擎 | 强制标准 + 阈值标准 | `GateRuleEngine` |
| 条件执行 | 支持 `condition` 表达式 | `ConditionEvaluator` |
| 人类审批增强 | 审批链 + checklist | `HumanGateV2` |

### P2 - 后续实施（2-4周）

| 特性 | 实施内容 | 交付物 |
|------|---------|--------|
| 豁免管理 | 豁免申请 + 审批 | `ExemptionManager` |
| 超时处理 | timeout + escalate | `TimeoutHandler` |
| 重试机制 | retry_with_fallback | `RetryHandler` |
| 错误处理策略 | 完整错误处理 | `ErrorHandler` |

### P3 - 企业特性（持续）

| 特性 | 实施内容 | 交付物 |
|------|---------|--------|
| 可观测性 | metrics + dashboards | `ObservabilityManager` |
| 质量指标 | 质量评分 | `QualityMetricsManager` |
| 文档完整性验证 | required_sections | `DocumentValidator` |

---

## 十一、进度跟踪

### 当前实施进度

| 阶段 | 计划开始 | 计划完成 | 实际开始 | 实际完成 | 状态 |
|------|---------|---------|---------|---------|------|
| P0.1 | 2026-02-05 | 2026-02-05 | - | - | 📋 计划中 |
| P0.2 | 2026-02-05 | 2026-02-06 | - | - | 📋 计划中 |
| P0.3 | 2026-02-05 | 2026-02-06 | - | - | 📋 计划中 |
| P0.4 | 2026-02-06 | 2026-02-07 | - | - | 📋 计划中 |
| P1.1 | 2026-02-08 | 2026-02-10 | - | - | 📋 讈划中 |
| P1.2 | 2026-02-11 | 2026-02-14 | - | - | 📋 计划中 |
| P1.3 | 2026-02-15 | 2026-02-16 | - | - | 📋 计划中 |
| P1.4 | 2026-02-17 | 2026-02-19 | - | - | 📋 计划中 |

---

## 十二、变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-02-05 | 初始版本，基于 QA 工作流分析创建 | LEE Core Team |

---

**更新说明**: 请在每次实现新特性后，更新对应的状态和支持情况。

**下次审查日期**: 2026-02-07
