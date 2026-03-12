---
id: FEAT-173
ssot_type: feat
title: qwen 执行器在中文需求场景下的输出质量达到可用标准
status: frozen
version: v1
parent_id: EPIC-022
derived_from_ids: []
source_refs:
- EPIC-022#scope
owner: null
tags: []
properties:
  contract_key: feat_005
  identity_kind: ssot
frozen_at: '2026-03-12T22:26:15.269132'
---

# Goal

qwen 执行器在中文场景下输出质量达标
# User Value

用户可使用中文需求获得高质量结果
# Inputs

- chinese_requirement_specs
  - UTF-8 中文原始需求文本
  - 至少包含目标、范围、约束中的 2 类字段
- execution_output
  - qwen 执行后的结构化输出对象
  - 输出字段至少包含 `title`、`content`、`source_refs`
- src_schema_ref
  - `SRC` 规范引用，固定指向 `SRC SSOT` 当前生效 schema / 契约说明
# Processing

- 解析中文原始需求
- 执行 qwen 处理
- 验证归一化输出
- 评估质量水平
# Outputs

- quality_assessment_report
- normalized_src_candidate
# Acceptance

- qwen 可解析中文原始需求
- 归一化输出符合 SRC 规范
- 在 20 条中文需求基准样本上，结构化字段完整率不低于 95%
- 在 20 条中文需求基准样本上，与基线执行器相比，关键字段对齐率不低于 90%
- 任一样本校验失败时，支持通过配置回退到 `claude_code` 或 `codex`
# Acceptance Checks

## AC-001

- Scenario: 中文需求解析
- Given: 输入中文需求文本
- When: 执行 qwen 处理
- Then: 输出可提取 `title`、`scope`、`constraints` 三类核心字段，且字段缺失数不超过 1
- Trace Hints: TESTSET, TECH

## AC-002

- Scenario: 输出质量验证
- Given: 处理完成
- When: 比对输出与规范
- Then: 输出通过 `SRC` schema 校验，且关键字段对齐率达到 90% 以上
- Trace Hints: TESTSET, TASK

## AC-003

- Scenario: 基准样本质量评估
- Given: 20 条中文需求基准样本与基线执行器输出
- When: 运行批量评估
- Then: `qwen` 输出的结构化字段完整率不低于 95%，关键字段对齐率不低于 90%
- Trace Hints: TESTSET, TASK

## AC-004

- Scenario: 回退机制生效
- Given: `qwen` 输出未通过 `SRC` schema 校验
- When: workflow 触发执行器回退
- Then: 系统按配置切换到备用执行器并记录回退原因、原始输出与回退目标
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-022
- FEAT-022-003
# Non Goals

- 不替换现有执行器
- 不新增平行 workflow
