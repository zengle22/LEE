---
id: FEAT-125
ssot_type: feat
title: Integration L3 Stage Definition
status: active
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_007
  identity_kind: ssot
---

# Goal

定义 Feature 交付流程中的 Integration L3 阶段，确保前后端协同完成端到端功能验证
# User Value

Feature 交付流程获得标准化的集成验证阶段，确保前后端协同完成端到端功能验证
# Inputs

- Inputs defined by EPIC scope
# Processing

- 绑定 tech_spec_ref、contract_freeze_ref 与 FE/BE artifacts
- 按 contract/mock 模式或 environment-backed 模式执行 Integration tests
- 在存在 env_ref、base_url、runtime_config_ref 时执行 E2E tests
- 收集 Performance baseline
- 验证 Acceptance criteria，并输出 integration_outputs 与 verification_results
# Outputs

- Integration test report
- E2E test results
- Performance baseline
- Acceptance verification record
- integration_outputs
- verification_results
# Acceptance

- Integration L3 阶段定义冻结
- 包含输入规范（tech_spec_ref + contract_freeze_ref + FE/BE artifacts + 可选环境输入）
- 包含输出物（Integration test report + E2E test results + Performance baseline + integration_outputs + verification_results）
- 包含完成标准（All tests passed + Acceptance criteria met）
- 包含阶段流转条件
# Acceptance Checks

## AC-SRC-009-007-01

- Scenario: 阶段定义文档冻结
- Given: EPIC-SRC-009-007 进入验收阶段
- When: 评审 Integration L3 阶段定义
- Then: 文档包含输入规范、输出物、完成标准、流转条件完整定义
- Trace Hints: TASK, TECH

## AC-SRC-009-007-02

- Scenario: 示例 FEAT 集成验证执行
- Given: 提供示例 FEAT 的 tech_spec_ref、contract_freeze_ref 和前后端产物
- When: 执行 Integration 阶段
- Then: 完成集成测试、按条件执行 E2E 测试、性能基线收集，并生成 integration_outputs 与 verification_results
- Trace Hints: TASK, TESTSET, TECH

## AC-SRC-009-007-03

- Scenario: Acceptance criteria 验证
- Given: 集成测试完成
- When: 对比 Acceptance criteria
- Then: 所有验收标准已满足
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-005
- FEAT-SRC-009-006
# Non Goals

- 不实现 E2E 自动化框架
- 不规定具体测试工具
- 不介入性能优化
