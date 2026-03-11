---
id: FEAT-068
ssot_type: feat
title: CLI 命令分层重构
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
frozen_at: '2026-03-11T14:48:58.894988'
---

# Goal

重构 LEE CLI 命令入口体系，统一 workflow 入口与 ssot create 直写入口的治理语义，确立分层命令结构
# User Value

消除用户对 CLI 入口混淆的困惑，明确 workflow 入口与 SSOT 直写入口的治理差异
# Inputs

- CLI 命令参数 (ssot create)
- 用户当前工作目录
- 用户角色/权限信息
# Processing

- 解析 CLI 命令参数，识别 ssot create 操作
- 判断是否存在未完成的 Gate 审查流程
- 根据用户权限和当前状态决定引导路径
- 输出引导信息或拒绝直写
# Outputs

- 引导至 Gate 审查流程的通知
- CLI 帮助文档更新
- 拒绝直写的错误消息
# Acceptance

- 用户通过 CLI 执行 ssot create 时，系统自动引导至 Gate 审查流程
- CLI 帮助文档明确区分 workflow 入口与 SSOT 入口的治理差异
- 绕过 Gate 的直写行为被明确约束或拒绝
# Acceptance Checks

## AC-CLI-001

- Scenario: 用户执行 ssot create 命令时触发引导
- Given: 用户在 CLI 中输入 ssot create 命令
- When: 系统解析命令并识别为 SSOT 物化操作
- Then: 系统返回 Gate 审查引导信息，而非直接创建
- Trace Hints: UI, TECH

## AC-CLI-002

- Scenario: CLI 帮助文档区分入口语义
- Given: 用户查看 CLI 帮助信息
- When: 执行 help 命令或查看子命令列表
- Then: 帮助文档清晰说明 workflow 入口与 SSOT 入口的治理差异
- Trace Hints: UI, TASK

## AC-CLI-003

- Scenario: 直写行为被约束
- Given: 用户尝试绕过 Gate 直接创建 SSOT
- When: 系统检测到直写意图
- Then: 系统拒绝操作并返回明确错误消息
- Trace Hints: TECH, TASK
# Dependencies

- None
# Non Goals

- 不涉及 Gate 类型的具体实现逻辑
- 不处理 CLI 命令的具体代码实现
- 不覆盖 Runtime 层面的行为约束
