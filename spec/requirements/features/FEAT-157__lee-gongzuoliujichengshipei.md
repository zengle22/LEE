---
id: FEAT-157
ssot_type: feat
title: LEE 工作流集成适配
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_007
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现需求链一致性测试与 LEE 工作流的深度集成，包括触发点配置、状态机集成、测试结果关联存储和命令扩展
# User Value

治理团队在工作流中无缝使用测试能力，产品团队在需求冻结前获得质量预检，评审阶段自动关联测试报告
# Inputs

- {'input_name': 'workflow_event', 'description': '工作流事件类型', 'format': 'enum[pre_freeze, post_freeze, on_review, on_change]'}
- {'input_name': 'requirement_ref', 'description': '需求对象引用', 'format': 'string'}
- {'input_name': 'test_config', 'description': '测试配置', 'format': 'JSON'}
- {'input_name': 'workflow_state', 'description': '当前工作流状态', 'format': 'string'}
# Processing

- 监听工作流事件触发测试
- 调用检测引擎执行测试
- 更新工作流测试状态
- 将测试结果与需求对象关联
- 支持测试失败的人工覆盖流程
# Outputs

- 工作流集成结果
- 工作流状态更新
# Acceptance

- LEE 工作流触发点配置（需求冻结前/评审阶段/变更时）功能完整
- 工作流状态机集成（测试状态流转）无缝衔接
- 测试结果与需求对象关联存储实现
- 工作流命令扩展（/test /validate）可用
- 测试失败的人工决策流程支持
# Acceptance Checks

## AC-021-007-001

- Scenario: 冻结前预检测
- Given: 需求处于 draft 状态，用户发起冻结请求
- When: 工作流触发 pre_freeze 事件
- Then: 自动执行一致性测试，结果附在冻结申请中
- Trace Hints: TASK, TESTSET, UI

## AC-021-007-002

- Scenario: 工作流命令扩展
- Given: 用户在 LEE CLI 中
- When: 执行 "/test FEAT-001"
- Then: 触发测试并在工作流中显示结果
- Trace Hints: TASK, TESTSET, TECH

## AC-021-007-003

- Scenario: 人工决策覆盖
- Given: 测试发现严重问题，阻塞流程
- When: 治理团队成员执行覆盖命令
- Then: 流程继续，记录覆盖决策和原因
- Trace Hints: TASK, TESTSET, UI

## AC-021-007-004

- Scenario: 测试结果关联存储
- Given: 测试执行完成
- When: 查看需求对象元数据
- Then: 可在 ssot 存储中找到关联的测试结果引用
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-021
- FEAT-021-006
# Non Goals

- 不修改现有工作流核心状态机
- 不实现新的审批流程（复用现有）
- 不做跨工作流引擎适配（仅 LEE 内部）
- 不替代工作流通知系统
