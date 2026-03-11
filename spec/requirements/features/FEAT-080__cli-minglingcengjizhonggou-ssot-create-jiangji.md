---
id: FEAT-080
ssot_type: feat
title: CLI 命令层级重构 - ssot create 降级
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-11T15:17:41.912181'
---

# Goal

将 ssot create 从推荐主入口降级为 internal/admin/maintenance 命令，阻止普通用户绕过治理流程
# User Value

普通用户无法通过 ssot create 直接创建正式 SSOT 对象，必须通过 workflow-first 入口
# Inputs

- CLI 命令定义
- 命令分组配置
- --internal/--admin flag 定义
# Processing

- 修改 CLI 命令注册逻辑
- 将 ssot create 移入 Internal/Maintenance 分组
- 添加权限校验逻辑
- 更新帮助文案标记
# Outputs

- 降级后的 ssot create 命令
- 权限校验逻辑
- 更新后的帮助文档
# Acceptance

- ssot create 命令不再出现在 lee --help 的主命令列表中
- 执行 lee ssot create 时返回提示引导用户使用 workflow 入口
- 仅当用户显式传递 --internal 或 --admin flag 时才允许执行
- 帮助文档中 ssot create 标记为 Internal 或 Deprecated
# Acceptance Checks

## AC-001-001

- Scenario: ssot create 不出现在主命令列表
- Given: 用户执行 lee --help
- When: 查看命令列表输出
- Then: ssot create 不在顶层命令列表中显示
- Trace Hints: UI, TESTSET

## AC-001-002

- Scenario: 普通用户执行 ssot create 被阻止
- Given: 用户未携带 --internal 或 --admin flag
- When: 执行 lee ssot create
- Then: 返回提示信息引导用户使用 workflow 入口
- Trace Hints: UI, TECH

## AC-001-003

- Scenario: 内部用户可正常执行 ssot create
- Given: 用户携带 --internal flag
- When: 执行 lee ssot create --internal
- Then: 命令正常执行（内部测试/迁移场景）
- Trace Hints: TECH, TASK
# Dependencies

- None
# Non Goals

- 不在本 FEAT 中删除 ssot create 的底层实现（保留物化能力）
- 不在本 FEAT 中处理其他历史命令的降级
