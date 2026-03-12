---
id: FEAT-104
ssot_type: feat
title: Workflow 注册表分层重组
status: frozen
version: v1
parent_id: EPIC-008
derived_from_ids: []
source_refs:
- EPIC-008#scope
owner: null
tags: []
properties:
  contract_key: feat_005
  identity_kind: ssot
frozen_at: '2026-03-12T13:50:05.878670'
---

# Goal

按 raw-to-src / src-to-epic 分层边界重组 workflow 注册表，降低开发者认知负担
# User Value

按 raw-to-src / src-to-epic 分层边界清晰组织注册表，认知负担降低 50% 以上
# Inputs

- 现有 workflow 注册表结构
- 分层架构设计规范
- layer 标签分类定义
# Processing

- 分析现有注册表结构
- 设计分层目录结构（/workflows/raw-to-src/ 和 /workflows/src-to-epic/）
- 实现 layer 标签系统
- 开发按 layer 过滤的检索功能
- 更新注册表文档
# Outputs

- 分层重组后的注册表结构
- layer 标签系统实现
- 按 layer 过滤的检索功能
- 更新的注册表文档
- 认知负担评估报告
# Acceptance

- 注册表按分层结构重组：/workflows/raw-to-src/ 和 /workflows/src-to-epic/ 分离
- 每个 workflow 条目包含明确的 layer 标签（raw-to-src | src-to-epic | epic-to-feat | feat-to-task）
- 检索功能支持按 layer 过滤，查询结果层级清晰
- 注册表文档更新，包含分层架构说明和各 layer 职责边界
- 开发者调研：认知负担量化评估（目标：定位 workflow 时间从平均 2min 降至 <1min）
# Acceptance Checks

## AC-008-005-01

- Scenario: 分层目录结构
- Given: 查看 workflow 注册表目录
- When: 浏览目录结构
- Then: 发现 /workflows/raw-to-src/ 和 /workflows/src-to-epic/ 独立目录
- Trace Hints: TASK, TECH

## AC-008-005-02

- Scenario: Layer 标签系统
- Given: 查看任意 workflow 条目
- When: 检查条目元数据
- Then: 发现明确的 layer 标签（raw-to-src | src-to-epic | epic-to-feat | feat-to-task）
- Trace Hints: TASK, TESTSET, TECH

## AC-008-005-03

- Scenario: 按 layer 过滤检索
- Given: 使用注册表检索功能
- When: 指定 layer 标签作为过滤条件
- Then: 返回结果仅包含该 layer 的 workflow 条目
- Trace Hints: UI, TASK, TESTSET

## AC-008-005-04

- Scenario: 注册表文档更新
- Given: 查看注册表文档
- When: 阅读架构说明部分
- Then: 包含分层架构说明和各 layer 职责边界
- Trace Hints: TECH

## AC-008-005-05

- Scenario: 认知负担量化评估
- Given: 对开发者进行调研
- When: 记录定位 workflow 所需时间
- Then: 平均时间从 2min 降至 <1min
- Trace Hints: TESTSET, UI
# Dependencies

- EPIC-008
- FEAT-008-001
- FEAT-008-002
# Non Goals

- 不修改下游 epic-to-feat / feat-to-task 的注册表组织
- 不实现自动化的注册表优化建议
- 不改变 workflow 的执行机制（仅组织方式变更）
