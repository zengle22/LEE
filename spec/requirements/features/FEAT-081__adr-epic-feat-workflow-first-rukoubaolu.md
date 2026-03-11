---
id: FEAT-081
ssot_type: feat
title: ADR/EPIC/FEAT Workflow-First 入口暴露
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-11T15:17:41.920309'
---

# Goal

为 ADR、EPIC、FEAT 三类正式对象提供 workflow-first 高层入口，使普通用户默认通过治理流程创建对象
# User Value

用户通过 lee adr new / lee epic new / lee feat new 命令创建正式对象，自动进入治理流程
# Inputs

- ADR/EPIC/FEAT 命令定义
- Workflow 模板关联
- 命令帮助文案
# Processing

- 实现 lee adr new / lee epic new / lee feat new 命令
- 命令内部调用对应的 workflow 模板启动流程
- 添加治理流程说明文案
- 阻止绕过 workflow 直接创建对象
# Outputs

- lee adr new 命令
- lee epic new 命令
- lee feat new 命令
- 命令帮助文档
# Acceptance

- lee adr new / lee epic new / lee feat new 命令可用且出现在主 help 中
- 每个命令内部调用对应的 workflow 模板启动流程
- 命令帮助文案明确说明此命令将通过治理流程创建正式对象
- 用户无法通过这些命令绕过 workflow 直接创建对象
# Acceptance Checks

## AC-002-001

- Scenario: workflow-first 命令出现在主帮助
- Given: 用户执行 lee --help
- When: 查看命令列表
- Then: lee adr new / lee epic new / lee feat new 出现在 Workflow Commands 分组中
- Trace Hints: UI, TESTSET

## AC-002-002

- Scenario: 命令启动治理流程
- Given: 用户执行 lee adr new
- When: 命令执行
- Then: 启动对应的 ADR 创建 workflow 模板流程
- Trace Hints: TASK, TECH

## AC-002-003

- Scenario: 帮助文案说明治理流程
- Given: 用户执行 lee adr new --help
- When: 查看帮助输出
- Then: 文案明确说明将通过治理流程创建正式对象
- Trace Hints: UI, TESTSET
# Dependencies

- FEAT-003-001
# Non Goals

- 不处理 ADR/EPIC/FEAT 对象的 runtime 存储实现
- 不定义具体的 workflow 模板内容
