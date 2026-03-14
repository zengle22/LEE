---
title: QA Execution Entry Specification
status: frozen
version: v1
derived_from_ids:
  - FEAT-143
source_refs:
  - FEAT-143#Acceptance
  - TECH-FEAT-143-016#data_models
owners:
  - qa-runtime-owner
---

# Purpose

定义 `FEAT-143 / TASK-FEAT-143-001` 的执行入口契约，作为后续 `EntryRouter`、`ChainValidator`、`AuditLogger` 和 CLI 集成的共同输入。

# Canonical Runtime Surface

- Python contract module: `src/lee/qa/schemas.py`
- Error registry: `src/lee/qa/error_codes.py`
- Canonical package export: `src/lee/qa/__init__.py`

# Entry Contract

## ExecutionRequest

- `task_ref`: 必填，只接受 `TASK-TESTPLAN-REL-{semver}-*`
- `triggered_by`: 必填，记录操作者或系统身份
- `entry_source`: 必填，枚举值仅允许 `CLI | API | UI`
- `session_id`: 可选，会话追踪
- `metadata`: 可选，扩展上下文

## ExecutionResponse

- `success`: 是否通过入口治理
- `run_id`: 通过后绑定的执行标识
- `status`: `pending | validating | ready | running | completed | failed | blocked`
- `error_code`: 失败时使用 `QA-ENTRY-*`
- `error_message`: 面向调用方的错误描述
- `audit_log_ref`: 审计记录引用
- `validation_result`: 路径校验结果
- `path`: `release_ref -> testplan_ref -> task_ref`
- `axis_binding`: 三轴追踪绑定

# Three-Axis Audit Model

## Requirement Axis

- `requirement_refs`: `FEAT / TESTSET / TC`

## Delivery Axis

- `delivery_refs`: `RELEASE / TESTPLAN / TASK`

## Evidence Axis

- `evidence_refs`: `BUG / REPORT / EVI`

所有执行入口审计必须至少保留完整交付轴路径；需求轴和证据轴可按执行上下文补齐。

# Audit Entry Fields

- `entry_id`
- `timestamp`，UTC ISO 8601
- `entry_source`
- `triggered_by`
- `action`
- `result`
- `error_code`
- `execution_status`
- `path`
- `axis_binding`
- `client_info`
- `metadata`

# Error Registry

- `QA-ENTRY-001`: 缺少 `task_ref`
- `QA-ENTRY-002`: `task_ref` 格式非法或不属于 `TESTPLAN`
- `QA-ENTRY-003` ~ `QA-ENTRY-010`: 链路与状态校验失败
- `QA-ENTRY-011`: 检测到旁路执行尝试
- `QA-ENTRY-012`: 审计日志写入失败

# Scope Boundary

- 本契约只定义模型、枚举、错误码和审计字段
- 不在本任务内实现 Router、Chain 校验或 CLI 命令
- 后续任务必须复用本契约，不得新建平行 schema
