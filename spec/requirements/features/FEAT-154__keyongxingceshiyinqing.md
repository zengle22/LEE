---
id: FEAT-154
ssot_type: feat
title: 可用性测试引擎
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现需求文档的可用性自动化评估，包括可读性评分、信息完整性检查和规范符合度评分，帮助作者提升需求文档的易读性和完整度
# User Value

产品团队在编写需求时获得实时可读性反馈，治理团队可量化评估需求文档质量，新成员通过规范性引导更快上手需求编写
# Inputs

- {'input_name': 'requirement_document', 'description': '待评估的需求文档内容', 'format': 'string | file_path'}
- {'input_name': 'document_type', 'description': '需求对象类型', 'format': 'enum[EPIC, FEAT, TASK, ADR]'}
- {'input_name': 'readability_rules', 'description': '可读性评分规则配置', 'format': 'JSON'}
- {'input_name': 'completeness_checklist', 'description': '完整性检查清单', 'format': 'JSON'}
- {'input_name': 'naming_conventions', 'description': '命名规范定义', 'format': 'JSON'}
# Processing

- 统计必填项和建议项的覆盖率
- 评估 goal/scope 等字段的描述充分性
- 检查命名规范、标签规范、元数据规范符合度
- 基于权重配置计算综合可读性评分
- 针对低分项生成具体改进建议
# Outputs

- 可用性评估报告
- 完整性检查结果
# Acceptance

- 文档可读性评分（基于字段完整度、描述长度、格式规范）算法可解释
- 信息完整性检查（必填项、建议项覆盖度）覆盖率 100%
- 规范符合度评分（命名规范、标签规范、元数据规范）准确
- 可读性维度权重可配置
- 可用性改进建议生成具体可行
# Acceptance Checks

## AC-021-004-001

- Scenario: 完整性检查发现缺失必填项
- Given: FEAT 文档缺少 acceptance_criteria 字段
- When: 执行完整性检查
- Then: 检查报告标记 missing_required，覆盖度<100%
- Trace Hints: TASK, TESTSET, TECH

## AC-021-004-002

- Scenario: 命名规范检查
- Given: FEAT ID 为"feat-001"（不符合 FEAT-XXX-XXX 格式）
- When: 执行规范符合度检查
- Then: 检查报告提示 ID 格式不符合命名规范
- Trace Hints: TASK, TESTSET, TECH

## AC-021-004-003

- Scenario: 可读性评分计算
- Given: goal 字段描述超过200字且结构清晰
- When: 执行可读性评分
- Then: 可读性评分较高，提供正面反馈
- Trace Hints: TASK, TESTSET, TECH

## AC-021-004-004

- Scenario: 改进建议生成
- Given: scope 字段只包含1项且描述模糊
- When: 执行可用性评估
- Then: 生成具体建议"建议补充更多范围项，明确边界"
- Trace Hints: TASK, TESTSET, TECH, UI
# Dependencies

- EPIC-021
# Non Goals

- 不涉及内容语义正确性判断
- 不实现文本风格/语法检查
- 不做跨文档一致性检测
- 不评估业务描述清晰度（主观性太强）
