---
id: TECH-FEAT-173-001
ssot_type: tech
title: Qwen Chat 中文任务与文档场景质量验证与回退技术方案
status: frozen
version: v1
parent_id: FEAT-173
derived_from_ids:
- FEAT-173
- EPIC-022
source_refs:
- FEAT-173
- EPIC-022
- TECH-FEAT-SRC-011
owner: codex
tags:
- qwen
- chinese
- quality
- fallback
- tech
properties:
  manual_backfill: true
  workflow_stage: feat_to_tech_manual
  frozen_at: '2026-03-13T02:10:00+08:00'
---

# Overview

本 TECH 为 `FEAT-173` 定义 `qwen_chat` 在中文任务与文档场景下的质量验证与回退机制，目标是在不放宽 SSOT 约束的前提下，让 `qwen_chat` 成为可用的通用中文对话后端选项。

# Current Anchors

- `spec/source/SRC-011__lee-qwen-zhixingqijieruqiyue.md`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/runtime/executor/profiles/loader.py`
- `src/lee/orchestrator/execution/tests/*`

# Scope

本方案覆盖：

- 中文任务与文档样本输入要求
- 结构化字段完整率与关键字段对齐率评估
- schema 校验失败时的回退
- 评估结果沉淀方式

本方案不覆盖：

- 模型训练或提示词平台
- 线上灰度发布

# Implementation Design

## 1. Benchmark Inputs

质量评估使用固定的中文任务与文档样本集，样本最少覆盖：

- 配置类需求
- workflow 类需求
- 文档生成类任务
- review / gate 类需求

每条样本都必须有基线执行器输出，便于比较关键字段对齐率。

## 2. Quality Metrics

最小评估指标：

- 结构化字段完整率
- 关键字段对齐率
- schema 一次通过率
- 回退触发率

## 3. Validation Pipeline

验证顺序应为：

1. `qwen_chat` 输出归一化
2. schema 校验
3. 关键字段对齐比对
4. 失败时记录原始输出并触发回退

## 4. Fallback Strategy

回退应由配置驱动，至少支持：

- `claude_code`
- `codex`
- `kimi`

回退记录中必须保存：

- 原执行器
- 回退目标
- 失败原因
- 原始输出引用

# File Touchpoints

- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/runtime/executor/profiles/loader.py`
- `src/lee/orchestrator/execution/tests/*`
- `spec/tasks/FEAT-169/*`

# Validation

- `qwen_chat` 中文输出能通过当前步骤既有 schema / contract
- 基准样本完整率与对齐率达到 FEAT 约束
- 失败样本能触发并记录回退
- 回退后下游 workflow 可继续执行

# Risks

- 风险：中文表达多样性导致字段漂移
  - 缓解：先归一化再校验，避免下游直接消费原始输出
- 风险：回退后输出语义与原始执行器混淆
  - 缓解：在 trace 和 review 产物中显式记录执行器来源与回退链
