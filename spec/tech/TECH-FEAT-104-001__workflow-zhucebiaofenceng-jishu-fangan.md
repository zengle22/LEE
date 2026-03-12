---
id: TECH-FEAT-104-001
ssot_type: tech
title: Workflow 注册表分层重组技术方案
status: draft
version: v1
parent_id: FEAT-104
derived_from_ids:
- TASK-FEAT-104-001
source_refs:
- FEAT-104
- TASK-FEAT-104-001
- ADR-012
owner: codex
tags:
- product
- registry
- workflow
- governance
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
---

# Overview

本 TECH 为 `FEAT-104` 提供 workflow registry 的分层重组方案，目标是在不改执行引擎的前提下，把 `raw-to-src`、`src-to-epic` 等链路入口在注册表和文档层明确分开。

# Current Anchors

- `spec-global/_metadata.yaml`
- `src/lee/cli/commands/workflow_registry.py`
- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`

# Scope

本方案覆盖：

- workflow registry 元数据分层
- layer 标签与检索字段
- 面向开发者的 registry 文档同步

本方案不覆盖：

- 新的 workflow 执行器
- 下游开发态 registry 重构

# Implementation Design

## 1. Registry Model

注册表至少显式区分四层：

- `raw-to-src`
- `src-to-epic`
- `epic-to-feat`
- `feat-to-task`

该分层属于元数据治理，不应改变 workflow template 的业务含义。

## 2. Query Surface

检索入口继续复用现有 CLI / metadata 读取逻辑，只增加 layer 过滤能力。

不新增平行 registry 存储。

## 3. Documentation Sync

当 registry 元数据变化时，需同步更新：

- workflow 列表说明
- 主链阶段说明
- 调用入口文档

避免 registry 已分层而 README 仍保留旧三段模型。

# File Touchpoints

- `spec-global/_metadata.yaml`
- `src/lee/cli/commands/workflow_registry.py`
- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `spec/requirements/features/FEAT-104__workflow-zhucebiaofencengzhongzu.md`

# Validation

应验证：

- layer 标签能被 registry 检索读取
- `raw-to-src` 与 `src-to-epic` 能被独立发现
- 主链文档与 registry 元数据一致

# Risks

- 风险：只改 stage 名称，不改 registry 语义，调用方仍无法明确入口
  - 缓解：把 layer 明确写进 registry 元数据和检索接口
- 风险：文档与 registry 脱节
  - 缓解：将 registry 文档同步纳入同一变更集与回归检查
