---
id: FEAT-152
ssot_type: feat
title: 语义一致性测试引擎
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现需求文档的语义一致性智能检测，包括术语统一性校验、需求逻辑自洽性分析和可追溯性验证，利用 LLM 能力识别语义层面的不一致问题
# User Value

治理团队在评审阶段可自动发现术语混用、逻辑矛盾等深层问题，产品团队维护统一的项目术语表，提升需求表达的准确性和一致性
# Inputs

- {'input_name': 'requirement_document', 'description': '待检测的需求文档内容', 'format': 'string | file_path'}
- {'input_name': 'document_type', 'description': '需求对象类型', 'format': 'enum[EPIC, FEAT, TASK, ADR]'}
- {'input_name': 'term_glossary', 'description': '项目级术语表定义', 'format': 'JSON/YAML'}
- {'input_name': 'requirement_chain', 'description': '相关需求链文档集合（用于追溯验证）', 'format': 'directory_path | file_path[]'}
- {'input_name': 'enable_llm_analysis', 'description': '是否启用 LLM 语义分析（成本敏感场景可关闭）', 'format': 'boolean', 'default': 'True'}
# Processing

- 提取文档中的专业术语，与术语表比对，标记未定义术语和混用别名
- 分析 goal/scope/non_goals/acceptance_criteria 之间的逻辑一致性，检测矛盾陈述
- 验证子需求的目标是否完整继承父需求，验收标准是否覆盖父需求范围
- 使用 LLM 分析需求描述的语义清晰度和一致性（可配置开关）
- 根据问题严重程度分级为 error/warning/suggestion
# Outputs

- 语义一致性检测报告
- 语义问题列表
# Acceptance

- 项目级术语表管理与一致性检测功能完整
- 需求逻辑自洽性分析（前提条件、冲突检测）实现
- EPIC→FEAT→TASK 纵向追溯链路验证不依赖 LLM，可 100% 离线执行
- 基于 LLM 的语义相似度分析可通过配置开关控制
- 语义问题分级（错误/警告/建议）准确
# Acceptance Checks

## AC-021-002-001

- Scenario: 术语一致性检测发现未定义术语
- Given: 文档中使用术语"数据湖"但术语表中无该定义
- When: 执行术语一致性检测
- Then: 检测报告标记 undefined_term 警告，提示添加术语定义
- Trace Hints: TASK, TESTSET, TECH

## AC-021-002-002

- Scenario: 术语别名混用检测
- Given: 术语表定义"用户故事"别名为"Story"，文档中同时使用两者
- When: 执行术语一致性检测
- Then: 检测报告提示术语混用，建议使用统一术语
- Trace Hints: TASK, TESTSET, TECH

## AC-021-002-003

- Scenario: 逻辑自洽性分析发现冲突
- Given: FEAT 的 non_goals 声明"不支持离线模式"，但 scope 包含"离线数据同步"
- When: 执行逻辑自洽性分析
- Then: 检测报告标记 logic_conflict 错误，指出 scope 与 non_goals 冲突
- Trace Hints: TASK, TESTSET, TECH

## AC-021-002-004

- Scenario: 追溯链路验证
- Given: FEAT 的 goal 与父 EPIC 的 scope 无明确关联
- When: 执行追溯验证
- Then: 检测报告标记 traceability_gap 警告，建议补充追溯关系
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-021
- FEAT-021-001
# Non Goals

- 不涉及语法/格式层面的检测（由 FEAT-021-001 处理）
- 不生成或改写需求内容
- 不判断业务价值合理性
- 不实现通用 NLP 功能，专注需求链场景
