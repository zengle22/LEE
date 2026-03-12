---
id: FEAT-150
ssot_type: feat
title: CLI帮助文档与demo叙事统一
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_006
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.618747'
---

# Goal

统一CLI帮助文档与demo示例的叙事，将用户引导至规范的workflow-first入口，形成一致的治理习惯
# User Value

用户通过统一的帮助文档和demo示例，自然采用规范的workflow-first入口，形成一致的治理习惯
# Inputs

- 现有CLI帮助文本
- 现有demo示例代码
- 分层设计架构文档
- 高层命令使用指南
# Processing

- 审计现有CLI帮助文本，识别需要更新的部分
- 审计现有demo示例，识别使用ssot create作为推荐入口的示例
- 重写ssot create帮助文本，明确标注为internal/admin用途
- 重写高层命令(lee epic/lee feat/lee adr)帮助文本，突出workflow-first理念
- 更新demo示例和quickstart，统一使用高层入口
# Outputs

- 更新后的CLI帮助文本
- 重写后的demo示例
- 用户引导文档
- 分层设计叙事指南
- 帮助文本一致性检查工具
# Acceptance

- CLI帮助文本中ssot create不再作为推荐主入口展示
- demo示例和quickstart统一使用lee epic/lee feat/lee adr
- --help输出中体现分层设计思想
- 验收时验证：新用户根据help和demo首次操作即使用高层入口，无需纠正
# Acceptance Checks

## AC-017-006-01

- Scenario: ssot create帮助文本更新
- Given: 用户查看ssot create --help
- When: 帮助文本显示
- Then: 明确标注为internal/admin用途，并指向高层入口
- Trace Hints: UI, TASK, TESTSET

## AC-017-006-02

- Scenario: demo示例一致性
- Given: 新用户阅读quickstart文档
- When: 按照示例执行操作
- Then: 示例使用lee epic init而非ssot create epic
- Trace Hints: UI, TESTSET

## AC-017-006-03

- Scenario: 首次使用引导效果
- Given: 5名未接触过系统的新用户
- When: 根据help和demo独立完成首次formal object创建
- Then: 100%用户直接使用高层入口，无需纠正
- Trace Hints: UI, TESTSET
# Dependencies

- FEAT-017-001
- FEAT-017-003
# Non Goals

- 不直接删除旧帮助文案或所有历史命令
