---
id: FEAT-133
ssot_type: feat
title: Evidence Pack 收口机制
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-12T19:47:01.821592'
---

# Goal

设计 Evidence Pack 作为证据轴正式收口对象，确保所有交付可审计、可追踪
# User Value

作为证据轴正式收口对象，确保所有交付可审计、可追踪，满足三轴 SSOT 体系的证据完整性要求
# Inputs

- {'formal_ssot_id': '工作流实例 ID'}
- {'source_refs': '来源引用'}
- {'governing_adrs': '相关 ADR 引用'}
- {'delivery_outputs': '阶段交付物列表'}
- {'verification_results': '验证结果'}
# Processing

- 设计 Evidence Pack Schema 定义
- 定义必需证据清单（代码、测试报告、评审记录、部署记录）
- 设计与 L2 工作流的集成接口
- 定义审计追溯规则
- 创建示例 Evidence Pack 模板
# Outputs

- Evidence Pack Schema 定义文档
- 必需证据清单文档
- L2 工作流集成接口规范
- 审计追溯规则文档
- 示例 Evidence Pack 模板
# Acceptance

- Evidence Pack Schema 文档已冻结
- Schema 包含完整的证据类型定义
- 必需证据清单覆盖代码、测试报告、评审记录、部署记录
- L2 工作流集成接口规范完整
- 审计追溯规则文档化
# Acceptance Checks

## AC-004-001

- Scenario: Evidence Pack Schema 冻结
- Given: Evidence Pack 机制设计完成
- When: 提交评审并通过
- Then: Schema 文档标记为 frozen 状态
- Trace Hints: TASK, TECH

## AC-004-002

- Scenario: 必需证据清单完整性
- Given: Evidence Pack 机制文档已冻结
- When: 检查证据清单
- Then: 包含代码、测试报告、评审记录、部署记录四类证据
- Trace Hints: TECH, TESTSET

## AC-004-003

- Scenario: L2 工作流集成接口
- Given: Evidence Pack 机制设计完成
- When: 检查集成接口规范
- Then: 明确定义与 Feature/Bugfix Delivery L2 的集成方式
- Trace Hints: TECH

## AC-004-004

- Scenario: 审计追溯规则定义
- Given: Evidence Pack 机制设计完成
- When: 检查审计追溯章节
- Then: 定义从 Evidence Pack 到上游 FEAT/BUG 的追溯路径
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 实现审计逻辑
- 修改 Evidence Pack 审计规则
- 实现证据收集自动化
