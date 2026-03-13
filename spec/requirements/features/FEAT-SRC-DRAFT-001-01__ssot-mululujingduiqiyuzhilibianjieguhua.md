---
id: FEAT-SRC-DRAFT-001-01
ssot_type: feat
title: SSOT 目录路径对齐与治理边界固化
status: active
version: v1
parent_id: EPIC-071
derived_from_ids: []
source_refs:
- EPIC-071#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
---

# Goal

定义 reverse workflow 输出路径规则并实现与 canonical SSOT 目录的映射，建立路径写入权限控制
# User Value

产品经理和治理审查员可确保输出路径符合现行 SSOT 链标准，避免路径不一致导致的治理问题
# Inputs

- epic_freeze 工件
- canonical SSOT 目录规范
- workspace 路径策略
# Processing

- 解析 epic_freeze 中的路径定义
- 映射 reverse workflow 输出到 canonical SSOT 目录
- 验证路径写入权限符合 workspace 策略
- 生成路径一致性验证报告
# Outputs

- 路径映射规则文档
- 路径一致性验证报告
- 治理审查员验证接口
# Acceptance

- reverse workflow 输出路径与 canonical SSOT 目录 100% 一致
- 所有写入路径都位于当前 step_workspace 内
- 治理审查员路径验证通过率 100%
# Acceptance Checks

## AC-001-01

- Scenario: 路径一致性验证
- Given: epic_freeze 已冻结且包含路径定义
- When: 执行路径映射规则检查
- Then: 所有输出路径与 canonical SSOT 目录完全匹配
- Trace Hints: TASK, TESTSET, TECH

## AC-001-02

- Scenario: workspace 策略合规验证
- Given: step_workspace 已确定
- When: 检查所有 changed_files 写入路径
- Then: 所有路径都位于当前 step_workspace 内，无跨目录写入
- Trace Hints: TASK, TESTSET, TECH

## AC-001-03

- Scenario: 治理审查员验证
- Given: 路径映射规则已生成
- When: 治理审查员执行路径验证
- Then: 验证通过率为 100%
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-071
- epic_freeze
# Non Goals

- 不涉及具体形式化对象内容生成
- 不涉及用户角色权限逻辑实现
