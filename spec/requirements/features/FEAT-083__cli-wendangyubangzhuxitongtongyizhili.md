---
id: FEAT-083
ssot_type: feat
title: CLI 文档与帮助系统统一治理
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-11T15:17:41.934859'
---

# Goal

统一 CLI help、文档、demo 与测试叙事，传递一致的 workflow-first 治理理念
# User Value

用户在任何入口（CLI help、文档、demo）都能获得一致的 workflow-first 引导
# Inputs

- CLI 帮助文本
- 文档站点内容
- Demo 示例
- 测试用例命名规范
# Processing

- 更新 lee --help 输出分组
- 修改文档站点 Getting Started 章节
- 更新 Demo 示例使用 workflow-first 命令
- 统一测试用例命名规范
- 更新错误提示文案
# Outputs

- 分组后的 CLI 帮助
- 更新的文档内容
- 更新的 Demo 示例
- 更新的测试叙事
# Acceptance

- lee --help 输出中明确区分 Workflow Commands 和 Internal/Maintenance Commands 分组
- 文档站点 Getting Started 章节优先展示 workflow-first 入口
- Demo 示例使用 lee adr new / lee epic new / lee feat new
- 测试用例命名和描述统一使用 workflow-first 术语
- 错误提示文案引导用户使用正确的治理入口
# Acceptance Checks

## AC-004-001

- Scenario: CLI 帮助分组展示
- Given: 用户执行 lee --help
- When: 查看命令分组
- Then: 明确显示 Workflow Commands 和 Internal/Maintenance Commands 两个分组
- Trace Hints: UI, TESTSET

## AC-004-002

- Scenario: 文档优先展示 workflow-first
- Given: 用户访问文档站点 Getting Started
- When: 查看入门指南
- Then: 优先展示 workflow-first 入口命令
- Trace Hints: UI

## AC-004-003

- Scenario: Demo 示例使用新入口
- Given: 用户查看 Demo 示例
- When: 运行示例代码
- Then: 使用 lee adr new / lee epic new / lee feat new 命令
- Trace Hints: UI, TESTSET

## AC-004-004

- Scenario: 错误提示引导用户
- Given: 用户执行了非 workflow-first 路径的操作
- When: 返回错误或提示
- Then: 文案引导用户使用正确的治理入口
- Trace Hints: UI, TESTSET
# Dependencies

- FEAT-003-001
- FEAT-003-002
# Non Goals

- 不重写全部历史文档
- 不修改代码实现细节（仅文档层面）
