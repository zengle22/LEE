---
id: TECH-FEAT-171-001
ssot_type: tech
title: Runner 调度 Qwen 对话后端与结果归一化技术方案
status: frozen
version: v1
parent_id: FEAT-171
derived_from_ids:
- FEAT-171
- EPIC-022
source_refs:
- FEAT-171
- EPIC-022
- TECH-FEAT-SRC-011
owner: codex
tags:
- qwen
- runner
- normalization
- tech
properties:
  manual_backfill: true
  workflow_stage: feat_to_tech_manual
  frozen_at: '2026-03-13T02:10:00+08:00'
---

# Overview

本 TECH 为 `FEAT-171` 定义 Runner 如何调度 `qwen_chat` 对话后端，并把其输出归一化到现有 LEE 执行结果语义中。

核心约束是：`qwen` 不能绕开现有 `task execution`、`structured payload`、`ssot materialization` 和 `review` 机制，且其无头模式适配必须建立在 `qwen -p/--prompt` 与 `--output-format json|stream-json` 之上，而不是假定存在 `claude --print` 同名参数。

# Current Anchors

- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/runners/base.py`
- `src/lee/orchestrator/execution/trace.py`
- `src/lee/orchestrator/storage/sqlite_store.py`

# Scope

本方案覆盖：

- Runner 对 `executor_override=qwen_chat` 的识别
- `qwen_chat` 输入适配
- 结果 envelope 归一化
- trace / evidence / task execution 记录

本方案不覆盖：

- 工厂实例化
- workflow gate 审批
- 中文质量基准样本管理

# Implementation Design

## 1. Executor Routing

Runner 在 `agent` 类步骤上遇到 `executor_override=qwen_chat` 时，应路由到对话型执行，而不是沿用 code-runner 的命令式假设。`claude_code` 类步骤不应再被 `qwen_chat` 覆盖。

## 2. Input Shape

对 `qwen_chat` 的最小输入应压缩为：

- `system_message`
- `prompt`
- `temperature`
- `max_tokens`

无头调用约定应优先映射为：

- `qwen -p "<prompt>" --output-format json`
- 在需要增量事件时使用 `--output-format stream-json`

避免把 `claude_code` 专属的 MCP、bash 白名单、workspace command policy 直接硬塞给 `qwen_chat`。

## 3. Output Normalization

Runner 需要把 `qwen_chat` 输出统一压回以下语义：

- `business_output`
- `structured_payload`
- `ssot_output_contract`
- `changed_files`
- `execution logs / trace refs`

当 `qwen` 输出字段名漂移时，应通过 helper 做归一化，不应把下游 schema 放宽到接受任意自由格式。

## 4. Materialization Safety

归一化后仍必须走现有 materialization helper，把 `SRC / EPIC / FEAT / TASK` 落盘逻辑保持在统一入口。

## 5. Failure Semantics

执行失败时需要区分：

- provider/profile 错误
- schema 校验错误
- 语义漂移修复失败
- materialization 失败

# File Touchpoints

- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/trace.py`
- `src/lee/orchestrator/storage/sqlite_store.py`
- `src/lee/orchestrator/execution/tests/test_llm_runner_ssot_integration.py`

# Validation

- `executor_override=qwen_chat` 时 Runner 能稳定调度
- 结果可继续通过下游 schema 校验
- `delivery_plan_validation` 等 review 步骤仍能消费归一化结果
- `qwen_chat` 不会破坏既有 `claude_code` 路径，也不会误作为 code-step executor

# Risks

- 风险：Runner 为兼容 `qwen` 引入过多 if/else 特判
  - 缓解：把差异收敛到输入适配和输出归一化 helper
- 风险：结构化输出字段漂移导致 review / freeze 步骤误判
  - 缓解：保持 schema repair 与 normalization 在 Runner 层集中治理
