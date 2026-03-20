---
id: TECH-FEAT-105-001
ssot_type: tech
title: 分层部署与健康检查技术方案
status: draft
version: v1
parent_id: FEAT-105
derived_from_ids:
- TASK-FEAT-105-001
source_refs:
- FEAT-105
- TASK-FEAT-105-001
- ADR-012
owner: codex
tags:
- product
- deployment
- healthcheck
- workflow
- tech
properties:
  manual_backfill: true
  workflow_stage: task_to_tech_pilot
workflow_instance_id: wf-tech-feat-105-001__fencengbushuhejiankangjiancha-jishu-fangan-20260316
---

# Overview

本 TECH 为 `FEAT-105` 提供分层运行配置与健康检查的最小方案，目标是在当前仓库内表达 `raw-to-src` 和 `src-to-epic` 的独立启动、回滚与隔离能力，而不是引入新的基础设施平台或 HTTP 后端服务。

# Current Anchors

- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/state_machine.py`

# Scope

本方案覆盖：

- 两个 layer 的独立运行配置表达
- readiness 健康检查语义
- 故障隔离验证路径

本方案不覆盖：

- Kubernetes 控制器
- 蓝绿发布
- 数据存储 schema 变更

# Implementation Design

## 1. Deployment Shape

“独立部署”在当前仓库中的最小含义是：

- 两个 workflow 可被独立启动
- 各自配置项、输入对象与输出目录明确
- 回滚时不会要求同步重放另一层

## 2. Health Model

健康检查明确豁免 HTTP `/health` 服务形态，当前阶段定义为 layer-specific readiness probe：

- 模板已注册
- 依赖 contract 可解析
- canonical 输入对象可加载
- 关键 step 可被调度

若后续确实需要 HTTP `/health`，应单独立项并建立在现有运行时之上，而不是在本 FEAT 中先引入独立服务。

## 3. Fault Isolation

故障隔离验证应聚焦对象边界：

- `raw-to-src` 失败不影响已存在 `SRC` 被 `src-to-epic` 消费
- `src-to-epic` 失败不回滚已冻结 `SRC`

# File Touchpoints

- `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`
- `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/state_machine.py`

# Validation

应验证：

- 两个 layer 可分别运行
- 健康检查能准确反映 contract / template / input readiness
- `raw-to-src` 故障时，已有 `SRC` 仍可推进 `src-to-epic`

# Risks

- 风险：把“独立部署”误解成必须新增独立服务栈
  - 缓解：先以 workflow-level isolation 定义部署能力
- 风险：健康检查只检查进程存活，无法反映对象链是否可运行
  - 缓解：健康检查至少覆盖 template、contract 和 canonical input readiness
