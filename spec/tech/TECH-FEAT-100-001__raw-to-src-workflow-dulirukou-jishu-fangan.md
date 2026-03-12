---
id: TECH-FEAT-100-001
ssot_type: tech
title: Raw-to-Src Workflow 独立入口技术方案
status: draft
version: v1
parent_id: FEAT-100
derived_from_ids:
- TASK-FEAT-100-001
- TASK-FEAT-100-002
source_refs:
- FEAT-100
- TASK-FEAT-100-001
- TASK-FEAT-100-002
- ADR-012
owner: codex
tags:
- product
- workflow
- src
- cli
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
---

# Overview

本 TECH 为 `FEAT-100` 提供最小可落地技术方案，目标是在现有仓库内补出 `raw-to-src` 独立入口，而不是继续复用 `src-to-epic` 中的前置归一化逻辑。

约束如下：

- 不引入新服务栈，不新增数据库、缓存、网关或 UI
- 复用现有 workflow runtime、artifact materialization 和 contract 校验能力
- 输出对象仍是 canonical `SRC` 文档，落在 `spec/source`

# Current Anchors

当前实现可直接复用的锚点：

- `spec-global/departments/product/contracts/raw-source-input-contract/v1/schema.json`
- `spec-global/departments/product/contracts/source-freeze-contract/v1/schema.json`
- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/artifacts/manager.py`
- `src/lee/orchestrator/execution/artifacts/placement.py`
- `src/lee/cli/commands/run.py`

# Scope

本方案覆盖：

- 新增 `raw-to-src` workflow template 与 registry entry
- 为 CLI 提供独立执行入口
- 将 raw 输入归一化为 canonical `SRC`
- 为该链路补齐 repo-scoped 单元测试与验证

本方案不覆盖：

- `SRC -> EPIC` 生成
- 分布式并发处理
- 长驻服务部署

# Implementation Design

## 1. Workflow Template

新增独立模板：

- `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`

建议只保留与 `SRC` 冻结相关的最小步骤：

1. `raw_input_intake`
2. `source_normalization`
3. `source_review`
4. `source_freeze`

`src-to-epic` 不再承载 raw 输入适配职责。

## 2. CLI Boundary

独立入口继续走现有 `lee run workflow ...` 能力，不新增平行执行器。

若需要公开命令别名，入口应挂在：

- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

实现原则：

- CLI 只负责解析输入路径、workflow id 和输出位置
- 输入校验与对象物化仍由 runtime 负责

## 3. SRC Materialization

`raw-to-src` 的最终产物必须是 canonical `SRC`：

- `spec/source/SRC-xxx__*.md`

物化继续复用：

- `ArtifactManager.create_ssot()`
- `resolve_ssot_relative_dir(SSOTType.SRC)`

`source_freeze` 仍可保留为兼容层，但不得替代 canonical `SRC` 正文。

## 4. Validation Strategy

校验链分三层：

- 输入层：raw 文档字段、路径和引用合法性
- 归一化层：生成结果必须符合 SRC front matter 约定
- 落盘层：文件名、ID、front matter 与 placement 一致

性能要求按 FEAT 保持单文档 `< 30s`，以本地隔离环境为准。

# File Touchpoints

预计主要改动面：

- `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/artifacts/manager.py`
- `src/lee/orchestrator/execution/tests/*`

# Validation

最小验证应覆盖：

- raw 文档可独立生成 canonical `SRC`
- `raw-to-src` 可脱离 `src-to-epic` 运行
- 生成的 `SRC` 能被现有 `src-to-epic` 正常消费
- 单测覆盖 parser、normalizer、materializer 和 CLI 边界

# Risks

- 风险：继续在 `src-to-epic` 内残留 raw 适配逻辑，导致职责再次混淆
  - 缓解：把 raw 相关逻辑迁移到独立模板，并对 `src-to-epic` 增加输入类型拒绝校验
- 风险：freeze 壳文件再次被误当成正式 `SRC`
  - 缓解：在文档、runtime 和 gate 输出中明确 canonical `SRC` ref
