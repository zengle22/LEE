---
id: TASK-FEAT-104-001
ssot_type: task
title: Workflow 注册表分层重组与 layer 标签系统
status: frozen
version: v1
parent_id: FEAT-104
derived_from_ids: []
source_refs:
- FEAT-104#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_104_001
  identity_kind: ssot
frozen_at: '2026-03-12T14:01:00.150413'
---

# Objective

按 raw-to-src / src-to-epic 分层边界重组 workflow 注册表，实现 layer 标签系统

# Description

分析现有注册表结构，设计分层目录结构（/workflows/raw-to-src/ 和 /workflows/src-to-epic/），实现 layer 标签系统，开发按 layer 过滤的检索功能，更新注册表文档

## Acceptance Mapping
- FEAT-104 / AC-008-005-01: 分层目录结构：独立目录分离
- FEAT-104 / AC-008-005-02: Layer 标签系统：条目包含明确 layer 标签
- FEAT-104 / AC-008-005-03: 按 layer 过滤检索：查询结果层级清晰
- FEAT-104 / AC-008-005-04: 注册表文档更新：包含分层架构说明

## Dependencies
- TASK-FEAT-100-001
- TASK-FEAT-101-001

## Definition Of Done
- 注册表分层目录结构完成
- layer 标签系统实现
- 按 layer 过滤检索功能实现
- 注册表文档已更新
