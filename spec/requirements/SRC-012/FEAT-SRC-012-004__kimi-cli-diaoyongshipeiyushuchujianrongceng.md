---
id: FEAT-SRC-012-004
ssot_type: feat
title: Kimi CLI 调用适配与输出兼容层
status: frozen
version: v1
parent_id: EPIC-SRC-012
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-13T00:44:58.072453'
---

# Goal

实现 Kimi CLI 调用的适配层，确保输出格式与现有执行器 100% 兼容，零新增 workflow 模板
# User Value

Kimi 执行器的输出与现有执行器输出格式兼容，下游流程无需适配，确保与现有 workflow 的无缝集成
# Inputs

- kimi_cli_interface
- canonical_output_schema
- task_payload
# Processing

- 封装本地 kimi-cli --print 调用
- 将 Kimi CLI 输出转换为 canonical output schema
- 验证输出格式与现有 executor 输出 100% 兼容
- 复用现有 coding 步骤模板，零新增模板
- 确保下游流程无需适配即可消费输出
# Outputs

- canonical_formatted_output
- output_compatibility_report
- execution_artifacts
# Acceptance

- Kimi 执行器输出格式与现有 executor 输出 100% 兼容
- 本地 kimi-cli --print 调用封装正常工作
- 零新增 workflow 模板，完全复用现有 coding 步骤模板
# Acceptance Checks

## AC-SRC-012-004-01

- Scenario: 输出格式兼容性验证
- Given: Kimi 执行器完成一次任务执行
- When: 比较输出与 canonical output schema
- Then: 所有字段类型和结构完全符合规范
- Trace Hints: TECH, TESTSET

## AC-SRC-012-004-02

- Scenario: Kimi CLI 调用封装
- Given: 任务分配给 Kimi 执行器
- When: 执行器调用本地 kimi-cli --print
- Then: 命令正确执行并返回预期输出
- Trace Hints: TECH, TASK

## AC-SRC-012-004-03

- Scenario: 复用现有 workflow 模板
- Given: 使用 Kimi 执行器执行任务
- When: 检查 workflow 模板使用情况
- Then: 未创建新模板，完全复用现有 coding 步骤模板
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-012
- FEAT-SRC-012-001
- FEAT-SRC-012-002
# Non Goals

- 修改现有 workflow 模板
- 远端 Kimi API 的直接调用
- 输出内容的语义改写
