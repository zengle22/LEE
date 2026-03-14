---
id: TECH-FEAT-172-001
ssot_type: tech
title: Workflow 实例执行器上下文与隔离运行技术方案
status: frozen
version: v1
parent_id: FEAT-172
derived_from_ids:
- FEAT-172
- EPIC-022
source_refs:
- FEAT-172
- EPIC-022
- TECH-FEAT-SRC-011
owner: codex
tags:
- workflow
- executor
- isolation
- tech
properties:
  manual_backfill: true
  workflow_stage: feat_to_tech_manual
  frozen_at: '2026-03-13T02:10:00+08:00'
---

# Overview

本 TECH 为 `FEAT-172` 定义 workflow instance 如何携带执行器类型，并在多执行器并存时保持状态、workspace 与 trace 的隔离性，同时区分对话执行后端与真正的 coding executor。

# Current Anchors

- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/orchestrator/execution/orchestrator.py`
- `.workflow/orchestrator.db`

# Scope

本方案覆盖：

- workflow data 中的 `executor_override`
- code step 的真正 `coding_executor`
- 并发 scope 下的实例隔离
- trace / evidence 路径中的执行器上下文
- 旧实例重跑时的执行器一致性

本方案不覆盖：

- 执行器内部实现
- UI 展示层

# Implementation Design

## 1. Instance Data Contract

workflow instance 至少应携带：

- `executor_override`
- `run_id`
- `workflow_key`
- `params`

其中 `executor_override` 是对话执行后端选择的权威字段，避免 CLI 参数只在启动瞬间生效。对于 code step，真正的 executor 仍由 `coding_executor` 或显式 code-step override 决定。

## 2. Concurrency Scope

同一 FEAT 或同一业务对象的并发 scope 检查继续复用现有逻辑，但在 `continue / restart` 场景中必须保留旧实例的执行器信息，避免误把 `qwen_chat` 实例恢复成 `claude_code`，或把 code step 误路由到 chat backend。

## 3. Execution Isolation

隔离要求包括：

- `task_executions.executor_type` 可审计
- evidence 目录按 `run_id-step_id` 区分
- workspace 临时文件不跨实例复用

## 4. State Continuity

执行器切换不应影响：

- gate 状态
- step 完成态
- artifact / ssot ref

如果用户明确 `restart`，则允许新实例使用新的执行器上下文重新计算后续步骤。

# File Touchpoints

- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/storage/sqlite_store.py`

# Validation

- 新建 workflow 时 `executor_override` 能写入实例数据
- 同一 FEAT 重跑时可继续或重启，并保持执行器上下文正确
- `task_executions` 中能区分 `qwen_chat` 与其他执行器
- 并行实例不会互相污染 evidence / workspace

# Risks

- 风险：旧实例恢复时丢失执行器上下文
  - 缓解：把 `executor_override` 固定写入实例数据而非临时变量
- 风险：不同执行器在同一并发 scope 下共享历史产物
  - 缓解：继续使用 `run_id-step_id` 级证据目录与实例 workspace
