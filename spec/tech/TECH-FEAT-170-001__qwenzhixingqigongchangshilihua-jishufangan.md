---
id: TECH-FEAT-170-001
ssot_type: tech
title: Qwen 执行器工厂实例化技术方案
status: frozen
version: v1
parent_id: FEAT-170
derived_from_ids:
- FEAT-170
- EPIC-022
source_refs:
- FEAT-170
- EPIC-022
- TECH-FEAT-SRC-011
owner: codex
tags:
- qwen
- executor
- factory
- tech
properties:
  manual_backfill: true
  workflow_stage: feat_to_tech_manual
  frozen_at: '2026-03-13T02:10:00+08:00'
---

# Overview

本 TECH 为 `FEAT-170` 定义执行器工厂如何在不破坏现有执行器体系的前提下创建 `qwen cli` 执行器实例。

技术目标不是引入新的工厂框架，而是在现有 `ExecutorFactory` 上扩一条 `qwen` 分支，并复用 `LLMExecutor` / profile loader 的既有能力。

# Current Anchors

- `src/lee/orchestrator/execution/executors.py`
- `src/lee/orchestrator/execution/llm_executor.py`
- `src/lee/runtime/executor/profiles/loader.py`
- `config/llm_config.yaml`

# Scope

本方案覆盖：

- `qwen` 执行器类型注册
- `ExecutorFactory.create("qwen")` 的实例化路径
- `qwen profile` 的默认绑定
- 实例化失败时的错误定位

本方案不覆盖：

- workflow 调度逻辑
- 中文输出质量评估
- gate / review 流程

# Implementation Design

## 1. Factory Registration

在 `ExecutorFactory._executors` 中增加 `qwen` 映射，并确保其构造路径与 `llm` 一致，只是在默认 profile 上强制收敛为 `qwen`。

## 2. Executor Alias

`QwenExecutor` 作为轻量别名即可，不单独维护平行执行协议。其职责只有：

- 默认绑定 `profile="qwen"`
- 复用 `LLMExecutor` 的 provider、token、timeout、fallback 机制

## 3. Profile Resolution

优先级应为：

- 显式 `profile` 参数
- `qwen` 别名默认 profile
- 项目 `llm_config.yaml` 中的 `qwen` profile

若 profile 不存在，错误信息必须包含：

- 请求的执行器类型
- 缺失的 profile 名称
- 当前可用 profile 列表

## 4. Availability Check

工厂创建成功的最小标准是：

- 返回对象实现统一 `execute(input_data)` 接口
- 运行前即可获得 provider / model 配置
- 初始化阶段错误不应延迟到 workflow 深处才暴露

# File Touchpoints

- `src/lee/orchestrator/execution/executors.py`
- `src/lee/orchestrator/execution/llm_executor.py`
- `src/lee/runtime/executor/profiles/loader.py`
- `src/lee/orchestrator/execution/tests/*`

# Validation

- `ExecutorFactory.create("qwen")` 返回可执行实例
- `QwenExecutor` 默认走 `qwen` profile
- profile 缺失时返回可定位错误
- 不影响 `claude_code`、`codex`、`kimi` 的既有实例化逻辑

# Risks

- 风险：`qwen` profile 名称和实际配置文件条目不一致
  - 缓解：在工厂层固定默认 profile 名称，并在 loader 错误里暴露候选列表
- 风险：工厂实例化与运行时 profile 选择出现双重覆盖
  - 缓解：把“执行器类型”和“profile 名称”边界写清，避免两套隐式默认
