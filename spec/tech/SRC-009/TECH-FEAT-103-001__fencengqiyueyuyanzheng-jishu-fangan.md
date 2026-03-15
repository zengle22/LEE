---
id: TECH-FEAT-103-001
ssot_type: tech
title: 分层接口契约与验证技术方案
status: draft
version: v1
parent_id: FEAT-103
derived_from_ids:
- TASK-FEAT-103-001
source_refs:
- FEAT-103
- TASK-FEAT-103-001
- ADR-012
owner: codex
tags:
- product
- contract
- validation
- governance
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
workflow_instance_id: wf-tech-feat-103-001__fencengqiyueyuyanzheng-jishu-fangan-20260316
---

# Overview

本 TECH 为 `FEAT-103` 定义 `raw-to-src` 与 `src-to-epic` 之间的分层契约技术边界，目标是把对象真值、schema 校验和错误传播都固定在 runtime 可审计的位置。

# Current Anchors

- `spec-global/departments/product/contracts/raw-source-input-contract/v1/schema.json`
- `spec-global/departments/product/contracts/source-freeze-contract/v1/schema.json`
- `spec-global/departments/product/contracts/epic-contract/v1/schema.json`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/artifacts/ssot_contract.py`

# Scope

本方案覆盖：

- `raw-to-src` 输出契约
- `src-to-epic` 输入契约
- schema 校验与版本标识
- 错误信息穿透

本方案不覆盖：

- 进程外网络协议
- 通用契约管理平台

# Implementation Design

## 1. Contract Boundary

边界定义如下：

- `raw-to-src` 输出：canonical `SRC` 或其 freeze ref
- `src-to-epic` 输入：只接受 canonical `SRC` 视图

禁止直接传递未规范化 raw payload。

## 2. Validation Placement

校验应集中在 runtime，不下沉到业务 agent 提示词里。

建议复用：

- contract discovery
- schema validator
- SSOT parent / scope consistency 校验

## 3. Versioning

第一阶段只要求：

- 契约文件有版本目录
- 运行时错误中带出契约版本
- 破坏性变更由测试而不是人工记忆发现

## 4. Error Propagation

错误返回需要保留：

- 上游步骤 id
- contract 名称
- 失败字段
- canonical ref 或输入来源

这样 `raw-to-src` 失败与 `src-to-epic` 失败不会再混在一起。

# File Touchpoints

- `spec-global/departments/product/contracts/*`
- `src/lee/orchestrator/execution/artifacts/ssot_contract.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/tests/*`

# Validation

最小验证应覆盖：

- 契约变更会触发破坏性测试
- schema 错误能准确定位字段
- 错误上下文可穿透到调用方
- canonical ref 与 contract version 在日志中可追溯

# Risks

- 风险：同一条链路出现多套输入输出语义
  - 缓解：把 truth boundary 固定为 canonical `SRC`
- 风险：错误被包装后丢失上游上下文
  - 缓解：统一 error envelope，并在 runner 中透传 contract/version/source 信息
