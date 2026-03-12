---
id: FEAT-160
ssot_type: feat
title: Schema测试器
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.708361'
---

# Goal

自动化验证需求链各层节点的结构合规性，确保字段完整性与类型正确
# User Value

在需求流转早期发现字段缺失、类型错误等结构性问题，降低下游返工成本，提升需求文档质量
# Inputs

- 需求链节点数据（SRC/EPIC/FEAT/TASK）
- Schema定义文件（各层节点的字段规范）
- 类型校验规则（字符串、数值、布尔、数组、对象）
- 引用关系映射表（parent_id、derived_from_ids映射）
# Processing

- 解析需求链节点，识别节点层级类型
- 加载对应层级的Schema定义
- 执行字段完整性校验
- 执行字段类型校验
- 执行引用完整性校验
# Outputs

- Schema验证报告（节点ID、字段路径、错误类型、严重程度）
- 合规率统计（按层级、按错误类型汇总）
- 结构问题清单及修复建议
# Acceptance

- 支持SRC/EPIC/FEAT/TASK四层节点的Schema验证
- 支持字符串、数值、布尔值、数组、对象等基础类型校验
- 支持日期时间格式校验（ISO 8601格式）
- 支持枚举值校验（如priority仅允许P0/P1/P2）
- 支持正则表达式模式校验（如ID格式校验）
# Acceptance Checks

## AC-002-001

- Scenario: SRC节点字段完整性验证
- Given: SRC节点包含完整字段集（id、title、problem_statement等）
- When: 执行Schema测试器
- Then: 验证通过，无结构性错误
- Trace Hints: TECH, TESTSET

## AC-002-002

- Scenario: 缺失必填字段检测
- Given: FEAT节点缺少acceptance_criteria字段
- When: 执行Schema测试器
- Then: 报告字段缺失错误，标记严重程度为critical
- Trace Hints: TECH, UI, TESTSET

## AC-002-003

- Scenario: 字段类型错误检测
- Given: EPIC节点的priority字段值为"高"
- When: 执行类型校验
- Then: 报告类型错误，提示仅允许P0/P1/P2
- Trace Hints: TECH, TESTSET

## AC-002-004

- Scenario: 引用完整性验证
- Given: FEAT节点的parent_id指向不存在的EPIC
- When: 执行引用校验
- Then: 报告断链错误，提供修复建议
- Trace Hints: TECH, TASK, TESTSET
# Dependencies

- EPIC-030
- FEAT-159
# Non Goals

- 不验证字段内容的业务合理性（仅验证结构）
- 不自动修复检测到的结构问题
- 不涉及需求链的语义分析
