---
id: FEAT-SRC-058-002
ssot_type: feat
title: 统一 Test Set 资产管理
status: frozen
version: v2
workflow_instance_id: wf_task_fix-p0p1-issues
parent_id: EPIC-SRC-058-001
derived_from_ids:
- id: EPIC-SRC-058-001
  version: v3
  required: true
source_refs:
- EPIC-SRC-058-001#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-17T12:00:00.000000'
---

# Goal

建立单一 Test Set 数据模型，Dev 和 QA 共享同一套测试资产，通过 priority 字段区分使用场景

# User Value

Dev 和 QA 共享同一套 Test Set 资产，通过 priority 字段区分使用场景，消除重复维护和资产不一致问题

# Inputs

- feat_prd
- test_requirement
- priority_schema

# Processing

- 设计单一 Test Set 数据模型
- 实现 priority 字段支持 P0/P1/P2 分级
- P0/P1 定义为 Dev Smoke 必执行用例
- P2 定义为 QA 回归可选用例
- 实现测试数据管理策略
- 实现 Flaky Test 标记字段
- 支持测试用例血缘追踪

# Outputs

- unified_test_set_schema
- priority_classification
- test_case_metadata

# Acceptance

- 单一 Test Set 数据模型已建立
- priority 字段支持 P0/P1/P2 分级
- P0/P1 为 Dev Smoke 必执行
- P2 为 QA 回归可选
- 测试数据管理策略已实现
- Flaky Test 标记功能正常

# Acceptance Checks

## AC-001
Test Set 数据模型支持 priority 字段定义

## AC-002
P0/P1 用例自动包含在 Dev Smoke 执行计划中

## AC-003
P2 用例标记为 QA 回归可选

## AC-004
Dev 和 QA 共享同一 Test Set 资产，无重复维护

## AC-005
测试数据管理策略已实现，支持独立测试数据库和自动清理

## AC-006
Flaky Test 标记功能正常，支持自动识别和手动标记

# Non Goals

- 区分 smoke 和 full Test Set
- P2 用例作为 Dev Smoke 默认执行

# Dependencies

- FEAT-SRC-058-005  # Flaky Test 治理 (使用标记字段)
