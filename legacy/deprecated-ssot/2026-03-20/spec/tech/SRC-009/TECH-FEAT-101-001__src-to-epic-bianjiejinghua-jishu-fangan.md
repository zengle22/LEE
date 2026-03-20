---
id: TECH-FEAT-101-001
ssot_type: tech
title: Src-to-Epic 边界净化技术方案
status: draft
version: v1
parent_id: FEAT-101
derived_from_ids:
- TASK-FEAT-101-001
- TASK-FEAT-101-002
source_refs:
- FEAT-101
- TASK-FEAT-101-001
- TASK-FEAT-101-002
- ADR-012
owner: codex
tags:
- product
- workflow
- epic
- contract
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
workflow_instance_id: wf-tech-feat-101-001__src-to-epic-bianjiejinghua-jishu-fangan-20260316
---

# Overview

本 TECH 为 `FEAT-101` 提供 `src-to-epic` 收窄方案，目标是把该 workflow 严格限定为“消费冻结 `SRC`，生成 `EPIC`”，不再承担 raw 输入归一化。

核心原则：

- 输入必须是 canonical `SRC` 或其 freeze ref
- 错误应能区分“输入格式错误”与“EPIC 生成失败”
- 不改变 `EPIC -> FEAT` 下游接口

# Current Anchors

- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- `spec-global/departments/product/contracts/source-freeze-contract/v1/schema.json`
- `spec-global/departments/product/contracts/epic-contract/v1/schema.json`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/gate_operations.py`

# Scope

本方案覆盖：

- `src-to-epic` 输入边界收窄
- `SRC -> EPIC` 字段映射与错误分类
- 兼容已存在 canonical `SRC` 与 freeze shell ref

本方案不覆盖：

- 新增 EPIC 建模语义
- `raw-to-src` 的具体实现
- 下游 `epic-to-feat` 改造

# Implementation Design

## 1. Input Contract

`src-to-epic` 入口只接受两类输入：

- canonical `SRC-*`
- 指向 canonical `SRC` 的 `source_freeze_ref`

拒绝项：

- raw markdown / text
- 混入 `scope`、`success_criteria` 等 EPIC 语义的伪 SRC

## 2. Runtime Resolution

runtime 需要先做 canonical resolution：

1. 若输入为 freeze shell，则回溯真实 `SRC`
2. 若输入为 canonical `SRC`，直接进入映射
3. 若缺少 canonical ref，则直接报输入错误

该逻辑应集中在 `llm_runner.py`，避免 template 和 agent prompt 各自实现一套判断。

## 3. Error Model

错误分层：

- `input_validation_error`
- `canonical_resolution_error`
- `epic_generation_error`

调用方看到的错误信息必须保留上游上下文，便于区分是对象不合法还是生成步骤失败。

# File Touchpoints

- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/gate_operations.py`
- `src/lee/orchestrator/execution/tests/*`

# Validation

应补齐以下验证：

- `SRC` 输入可成功生成 `EPIC`
- raw 输入被明确拒绝
- freeze shell 可稳定回溯 canonical `SRC`
- 现有 `src-to-epic` 回归测试全部通过

# Risks

- 风险：兼容层 resolution 不稳定，导致 freeze shell 与 canonical `SRC` 脱钩
  - 缓解：统一使用 canonical ref 回溯 helper，并为 gate 壳文件重写 declared outputs
- 风险：旧调用方仍直接传 raw 输入
  - 缓解：在 CLI 与 runtime 两层都返回明确拒绝错误，并提供迁移提示
