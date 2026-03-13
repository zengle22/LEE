---
id: TECH-FEAT-SRC-011
ssot_type: tech
title: SRC-011 Qwen 执行器接入批次技术总览
status: frozen
version: v1
parent_id: SRC-011
derived_from_ids:
- EPIC-022
- FEAT-169
- FEAT-170
- FEAT-171
- FEAT-172
- FEAT-173
source_refs:
- SRC-011
- EPIC-022
- FEAT-169
- FEAT-170
- FEAT-171
- FEAT-172
- FEAT-173
owner: codex
tags:
- product
- qwen
- executor
- tech
properties:
  manual_backfill: true
  batch_scope: src011-qwen-executor
  workflow_stage: feat_to_tech_manual
  frozen_at: '2026-03-13T02:10:00+08:00'
---

# Overview

本 TECH 总览覆盖 `SRC-011 -> EPIC-022` 下的 `FEAT-169` 至 `FEAT-173`，目标是先手动冻结这批功能的技术边界，作为后续 TECH workflow、实现与验证的参考基线。

本批次技术目标分成五层：

- `FEAT-169`：配置层识别、校验与透传 `qwen` 执行器类型
- `FEAT-170`：执行器工厂按配置创建 `qwen` 执行器实例
- `FEAT-171`：Runner 调度 `qwen` 并归一化执行结果
- `FEAT-172`：workflow instance 携带执行器上下文并隔离运行
- `FEAT-173`：中文任务与文档场景下的输出质量评估与回退

# Current Anchors

- `src/lee/orchestrator/config_loader.py`
- `src/lee/orchestrator/execution/executors.py`
- `src/lee/orchestrator/execution/claude_code_executor.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/runtime/executor/profiles/loader.py`
- `spec/source/SRC-011__lee-qwen-zhixingqijieruqiyue.md`
- `spec/requirements/epics/EPIC-022__lee-qwen-zhixingqijieru.md`

# Architecture Slice

## 1. 配置与选择层

该层负责把 `CLI / config / default` 三类来源收敛为唯一执行器选择结果，并显式记录来源与优先级。

对应 FEAT：

- `FEAT-169`
- `FEAT-172`

## 2. 执行器构造层

该层负责把逻辑执行器类型映射到实际 executor 实例，要求与既有 `claude_code`、`codex`、`kimi` 并存，不引入平行工厂体系。

对应 FEAT：

- `FEAT-170`

## 3. 调度与结果归一化层

该层负责在 Runner 中调度 `qwen`，并把输出压回现有 LEE 标准 envelope、trace 与 materialization 语义。

对应 FEAT：

- `FEAT-171`

## 4. 工作流状态隔离层

该层负责让 workflow instance 明确携带 `executor_override`，避免多执行器并行时在 workspace、trace、gate 语义上相互污染。

对应 FEAT：

- `FEAT-172`

## 5. 质量评估与回退层

该层负责中文需求场景下的质量验证、失败样本记录和执行器回退，不把 `qwen` 的质量波动直接暴露给上游 workflow。

对应 FEAT：

- `FEAT-173`

# Cross-Cutting Decisions

- 不替换 `claude_code`、`codex`，只增加一个可切换执行器
- 不新增平行 workflow，继续复用现有 runner / factory / workflow wiring
- 所有执行链都必须保留统一的 `task execution`、`trace`、`ssot materialization` 语义
- 中文场景质量问题通过测试与回退治理解决，不把“模型能力假设”写死到主流程

# File Touchpoints

- `src/lee/orchestrator/config_loader.py`
- `src/lee/orchestrator/execution/executors.py`
- `src/lee/orchestrator/execution/claude_code_executor.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/tests/*`
- `spec/tech/TECH-FEAT-169-004__feat-169-frozen-technical-architecture-xitongpeizh.md`
- `spec/tasks/FEAT-169/*`

# Validation

本批次最小验证基线：

- `product.feat-to-delivery-prep` 可在 `FEAT-169` 上完成到 `delivery_prep_freeze`
- `delivery_plan_validation` 能稳定产出 `pass/revise/reject` 的结构化结果
- `ssot validate` 对新增 TASK / TECH 文档通过
- `qwen` 与既有执行器能在同一仓库中切换且不破坏 workflow 状态连续性

# Risks

- 风险：执行器选择逻辑分散在 CLI、config、runner 多处
  - 缓解：把优先级、来源与错误语义集中在配置层与 TECH 文档中固化
- 风险：`qwen` 输出在中文场景下波动，导致后续 SSOT 产物不稳定
  - 缓解：建立基准样本、schema 校验与回退策略
- 风险：Runner 为兼容多执行器引入过多特判
  - 缓解：优先通过统一结果 envelope 和 helper 归一化处理
