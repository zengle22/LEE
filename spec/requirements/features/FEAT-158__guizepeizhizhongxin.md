---
id: FEAT-158
ssot_type: feat
title: 规则配置中心
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_008
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现可配置的需求链测试规则体系，支持项目级规则覆盖、规则版本管理和热更新，为不同项目提供定制化的检测标准
# User Value

治理团队定义和维护组织级默认规则，项目负责人根据项目特点覆盖特定规则，规则变更可追溯可回滚
# Inputs

- {'input_name': 'rule_definition', 'description': '规则定义', 'format': 'YAML'}
- {'input_name': 'project_id', 'description': '项目标识', 'format': 'string'}
- {'input_name': 'rule_type', 'description': '规则类型', 'format': 'enum[structure, semantic, scoring, naming]'}
- {'input_name': 'operation', 'description': '操作类型', 'format': 'enum[create, update, delete, validate, publish]'}
# Processing

- 解析规则定义 DSL
- 计算项目级规则与默认规则的合并结果
- 创建规则版本，支持灰度发布
- 刷新规则缓存，使变更即时生效
- 提供规则调试日志与验证工具
# Outputs

- 计算后的规则配置
- 规则验证结果
# Acceptance

- 规则定义 DSL（结构规则、语义规则、评分规则）完整
- 项目级规则覆盖与继承机制实现
- 规则版本管理与灰度发布功能
- 规则热更新与缓存刷新（<30秒）
- 规则效果验证与调试工具可用
# Acceptance Checks

## AC-021-008-001

- Scenario: 规则定义与验证
- Given: 提交一个结构规则定义文件
- When: 执行规则验证
- Then: 验证通过，规则可被激活使用
- Trace Hints: TASK, TESTSET, TECH

## AC-021-008-002

- Scenario: 项目级规则覆盖
- Given: 项目 A 覆盖默认规则的 severity 阈值
- When: 查询项目 A 的有效规则
- Then: 返回的合并配置中显示项目级覆盖值
- Trace Hints: TASK, TESTSET, TECH

## AC-021-008-003

- Scenario: 规则版本管理
- Given: 修改并发布规则新版本
- When: 查询规则历史版本
- Then: 可查看版本差异并执行回滚
- Trace Hints: TASK, TESTSET, TECH

## AC-021-008-004

- Scenario: 规则热更新
- Given: 更新项目规则配置
- When: 等待30秒后执行检测
- Then: 新规则已生效，检测结果反映新规则
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-021
- FEAT-021-001
- FEAT-021-002
- FEAT-021-004
# Non Goals

- 不实现图形化规则编辑器（YAML 配置）
- 不做规则市场/共享机制
- 不实现规则自动推荐
- 不做全局强制规则（项目可覆盖）
