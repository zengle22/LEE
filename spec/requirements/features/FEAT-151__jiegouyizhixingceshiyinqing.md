---
id: FEAT-151
ssot_type: feat
title: 结构一致性测试引擎
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现需求文档的结构一致性自动化检测，包括 Schema 校验、层级完整性检查和引用有效性验证，确保 EPIC/FEAT/TASK/ADR 四级需求对象符合 LEE 规范定义的结构要求
# User Value

治理团队可在需求编写阶段自动发现结构缺陷，产品团队获得实时的格式合规反馈，降低因结构问题导致的评审返工
# Inputs

- {'input_name': 'requirement_document', 'description': '待检测的需求文档内容（YAML/Markdown 格式）', 'format': 'string | file_path'}
- {'input_name': 'document_type', 'description': '需求对象类型标识', 'format': 'enum[EPIC, FEAT, TASK, ADR]'}
- {'input_name': 'schema_version', 'description': '期望校验的 LEE Schema 版本', 'format': 'string', 'default': 'v1'}
- {'input_name': 'reference_catalog', 'description': '跨文档引用目标目录路径', 'format': 'directory_path'}
# Processing

- 解析输入文档为结构化对象，验证 YAML/Markdown 语法合规性
- 根据 document_type 加载对应 Schema，校验必填字段、字段类型、枚举值
- 验证 parent/derived_from 声明的层级关系是否形成合法树结构
- 验证所有 ssot.parent、ssot.derived_from、source_refs 等引用字段指向存在的文档
- 将检测到的结构问题映射回原始文档行号，提供精确定位
# Outputs

- 结构一致性检测报告
- 发现的结构问题列表
# Acceptance

- EPIC/FEAT/TASK/ADR 四级对象的 Schema 定义与校验规则完整实现
- 需求层级完整性检查（必填字段、层级嵌套关系）准确执行
- 跨文档引用有效性验证（ID 存在性、版本匹配性）准确率≥98%
- YAML/Markdown 格式合规性检测准确识别语法错误
- 基础错误定位与行号映射精度误差≤3行
# Acceptance Checks

## AC-021-001-001

- Scenario: Schema 校验发现必填字段缺失
- Given: 输入一个缺少 title 字段的 FEAT 文档
- When: 执行结构一致性检测
- Then: 检测报告包含 schema_violation 类型错误，定位到缺失字段位置
- Trace Hints: TASK, TESTSET, TECH

## AC-021-001-002

- Scenario: 跨文档引用有效性验证通过
- Given: 输入文档的 ssot.parent 引用存在的 EPIC 文档ID
- When: 执行引用有效性验证
- Then: 检测报告标记该引用为 valid，不产生错误
- Trace Hints: TASK, TESTSET, TECH

## AC-021-001-003

- Scenario: 跨文档引用有效性验证发现无效引用
- Given: 输入文档的 derived_from 引用不存在的 SRC 文档ID
- When: 执行引用有效性验证
- Then: 检测报告包含 invalid_reference 类型警告，提供建议修复
- Trace Hints: TASK, TESTSET, TECH

## AC-021-001-004

- Scenario: 单文档检测性能达标
- Given: 标准大小的 FEAT 文档（约500行）
- When: 执行完整结构检测流程
- Then: 检测完成时间<500ms
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-021
# Non Goals

- 不涉及语义内容分析（术语/逻辑）
- 不涉及文档可读性评分
- 不涉及变更影响分析
- 不实现 LLM 调用逻辑
