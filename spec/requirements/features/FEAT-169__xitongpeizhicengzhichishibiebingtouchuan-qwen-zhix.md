---
id: FEAT-169
ssot_type: feat
title: 系统配置层支持识别并透传 qwen 执行器类型标识
status: frozen
version: v1
parent_id: EPIC-022
derived_from_ids: []
source_refs:
- EPIC-022#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T22:26:15.230138'
---

# Goal

系统配置层能够识别并透传 qwen 执行器类型标识
# User Value

用户可以通过配置灵活切换执行器
# Inputs

- CLI 参数对象
- 配置文件对象
- 默认执行器设置源
# Processing

- 解析 CLI 参数
- 读取配置文件
- 验证 executor_type
- 透传配置到下游
# Outputs

- validated_executor_config
- executor_selection_source
# Acceptance

- CLI 指定 --executor=qwen 时配置层正确识别
- 配置文件设置 executor: qwen 时配置层正确识别
- 配置错误时返回明确错误信息
- CLI 参数与配置文件同时存在时，优先级遵循 `CLI > 配置文件 > 默认设置`
# Acceptance Checks

## AC-001

- Scenario: CLI 指定执行器类型
- Given: 用户输入 --executor=qwen
- When: 系统解析 CLI 参数
- Then: 配置层识别 executor_type 为 qwen
- Trace Hints: TECH, TESTSET, TASK

## AC-002

- Scenario: 配置文件指定执行器类型
- Given: 配置文件包含 executor: qwen
- When: 系统读取配置文件
- Then: 配置层识别 executor_type 为 qwen
- Trace Hints: TECH, TESTSET, TASK

## AC-003

- Scenario: 执行器来源优先级判定
- Given: CLI 参数指定 `--executor=qwen`，配置文件同时存在 `executor: claude_code`
- When: 系统合并执行器配置来源
- Then: 最终生效值为 `qwen`，并记录来源为 `cli_override`
- Trace Hints: TECH, TESTSET, TASK

## AC-004

- Scenario: 非法执行器配置报错
- Given: 配置文件包含 `executor: invalid_executor`
- When: 系统执行配置校验
- Then: 返回包含非法值与可选值列表的明确错误信息，且不进入 workflow 执行阶段
- Trace Hints: TECH, TESTSET, TASK
# Dependencies

- EPIC-022
# Non Goals

- 不替换现有执行器
- 不新增平行 workflow
