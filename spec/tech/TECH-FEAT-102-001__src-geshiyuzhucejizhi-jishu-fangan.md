---
id: TECH-FEAT-102-001
ssot_type: tech
title: SRC 格式与注册机制技术方案
status: draft
version: v1
parent_id: FEAT-102
derived_from_ids:
- TASK-FEAT-102-001
- TASK-FEAT-102-002
source_refs:
- FEAT-102
- TASK-FEAT-102-001
- TASK-FEAT-102-002
- ADR-012
owner: codex
tags:
- product
- src
- registry
- validation
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
---

# Overview

本 TECH 为 `FEAT-102` 提供 `SRC v1` 的技术落盘方案，目标是让 `SRC` 成为可独立存储、加载、验证和追踪的正式对象，而不是 workflow 中间态。

# Current Anchors

- `spec/source`
- `src/lee/orchestrator/execution/artifacts/placement.py`
- `src/lee/orchestrator/execution/artifacts/id_generator.py`
- `src/lee/orchestrator/execution/artifacts/id_parser.py`
- `src/lee/orchestrator/execution/artifacts/manager.py`
- `spec-global/departments/product/contracts/source-freeze-contract/v1/schema.json`

# Scope

本方案覆盖：

- `SRC` front matter 最小字段约定
- 文件命名与 placement 规则
- 独立验证接口
- 轻量版本追踪入口

本方案不覆盖：

- Git 深度版本管理
- 面向外部系统的 API 服务

# Implementation Design

## 1. Canonical Shape

canonical `SRC` 至少包含：

- `id`
- `ssot_type`
- `title`
- `source_refs`
- 正文内容

禁止混入 EPIC 级语义字段，例如：

- `scope`
- `success_criteria`
- `initiative`

## 2. Placement and Naming

正式文件路径固定为：

- `spec/source/SRC-xxx__{slug}.md`

命名与 placement 统一复用现有 artifact 层，不自行拼路径。

## 3. Validation Layer

建议把校验拆成三段：

- front matter 校验
- ID / 文件名 / placement 一致性校验
- 语义隔离校验，确认 `SRC` 未携带 EPIC 字段

## 4. Version Tracking

第一阶段只做轻量追踪：

- 保留 `frozen_at`
- 复用文件系统历史与 git 变更
- 不额外引入版本数据库

# File Touchpoints

- `src/lee/orchestrator/execution/artifacts/placement.py`
- `src/lee/orchestrator/execution/artifacts/id_generator.py`
- `src/lee/orchestrator/execution/artifacts/id_parser.py`
- `src/lee/orchestrator/execution/artifacts/manager.py`
- `spec/source/*`

# Validation

应验证：

- `SRC` 文件可独立加载
- 文件名、ID、目录三者一致
- 缺字段、错字段、越权字段时能返回明确错误
- 多版本 `SRC` 可通过 git 或历史记录被追溯

# Risks

- 风险：继续把 freeze shell 当成 `SRC` 正文，导致验证与回放混乱
  - 缓解：所有下游一律以 canonical `SRC` 为主，freeze 仅保留引用
- 风险：后续 schema 扩展时把 EPIC 字段回流到 `SRC`
  - 缓解：增加语义隔离测试和字段 denylist 校验
