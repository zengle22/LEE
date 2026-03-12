---
id: FEAT-091
ssot_type: feat
title: QA 测试资产 release 化改造
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T00:13:22.001091'
---

# Goal

完成 TESTSET/TESTPLAN/TASK/REPORT 与 SSOT 主链的 release 化对齐，建立三轴分层结构
# User Value

QA 部门能够将测试资产正式纳入 SSOT 管理，实现 Release Gate 的可追溯决策基础
# Inputs

- FEAT 定义（作为 TESTSET 的 parent）
- RELEASE 定义（作为 TESTPLAN 的 parent）
- 现有 TESTSET/TESTPLAN 数据
# Processing

- TESTSET 模型增加 parent_feat_id 字段并设置为必填
- TESTSET 创建接口校验 parent_feat_id 有效性
- TESTPLAN 模型增加 parent_release_id 字段并设置为必填
- TESTPLAN 创建接口校验 parent_release_id 有效性
- 实现需求轴/交付轴/证据轴的显式分层存储
# Outputs

- 符合 CR-001 的 TESTSET 模型（绑定单一 FEAT）
- 符合 CR-002 的 TESTPLAN 模型（挂在 RELEASE 下）
- 三轴分层数据结构
- 数据迁移报告
# Acceptance

- TESTSET 必须且只能绑定单一 FEAT（0:N 关系验证）
- TESTPLAN 必须挂在 RELEASE 下（绑定关系验证）
- 需求轴、交付轴、证据轴必须显式分层
- TESTSET 由 FEAT 派生，QA 不得从 EPIC 直接生成测试真源
# Acceptance Checks

## AC-001-001

- Scenario: TESTSET 绑定单一 FEAT 验证
- Given: 系统已部署新版 TESTSET 模型
- When: 创建 TESTSET 时提供有效的 parent_feat_id
- Then: TESTSET 创建成功且 parent_feat_id 不可为空
- Trace Hints: TECH, TESTSET

## AC-001-002

- Scenario: TESTSET 拒绝无效 FEAT 绑定
- Given: 系统已部署新版 TESTSET 模型
- When: 创建 TESTSET 时提供无效的 parent_feat_id
- Then: 创建被拒绝并返回校验错误
- Trace Hints: TECH, TESTSET

## AC-001-003

- Scenario: TESTPLAN 挂在 RELEASE 下验证
- Given: 系统已部署新版 TESTPLAN 模型
- When: 创建 TESTPLAN 时提供有效的 parent_release_id
- Then: TESTPLAN 创建成功且 parent_release_id 不可为空
- Trace Hints: TECH, TESTSET

## AC-001-004

- Scenario: 三轴模型显式分层验证
- Given: 系统已实现三轴存储结构
- When: 查询任意 TESTSET/TESTPLAN 的轴属性
- Then: 返回明确的需求轴/交付轴/证据轴标识
- Trace Hints: TECH, TESTSET

## AC-001-005

- Scenario: 现有数据迁移完成
- Given: 存在历史 TESTSET/TESTPLAN 数据
- When: 执行数据迁移脚本
- Then: 所有数据符合新约束或标记为待处理
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-QA-SSOT-UPGRADE
# Non Goals

- 追溯链路的完整性验证（由 FEAT-002 负责）
- QA 执行入口的收敛（由 FEAT-003 负责）
- BUG/REPORT/EVI 的反查能力（由 FEAT-002 负责）
- 具体数据库设计细节
