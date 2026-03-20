---
id: TASK-FEAT-SRC-009-011-001
ssot_type: task
title: 共享输入规范结构定义
status: active
version: v1
parent_id: FEAT-SRC-009-011
derived_from_ids: []
source_refs:
- FEAT-SRC-009-011#delivery
- TECH-FEAT-SRC-009-011-001
owner: null
tags: []
properties:
  contract_key: task_shared_input_schema_spec
  identity_kind: ssot
  materialized_from_workflow: wf_task_4a3a7a74
---

# Objective

定义所有 Dev workflow 共享的输入 schema 结构

# Description

创建 formal_ssot_id、source_refs、governing_adrs、repo_context 的完整 schema 定义，包含格式规则、校验逻辑和类型约束

## Acceptance Mapping
- FEAT-SRC-009-011 / AC-011-002: formal_ssot_id 规范包含格式定义和校验规则
- FEAT-SRC-009-011 / AC-011-003: source_refs 规范包含引用格式和必填性定义
- FEAT-SRC-009-011 / AC-011-001: 共享输入规范文档已冻结

## Prerequisites
- FEAT-SRC-009-011 已冻结
- ADR-008 已冻结

## Dependencies
- TASK-FEAT-SRC-009-001-001

## Definition Of Done
- shared_input_schema.md 规范文档已创建并冻结
- formal_ssot_id 格式规范包含正则约束和校验规则
- source_refs 引用规范包含格式和必填性定义
- governing_adrs ADR 引用规范包含影响范围声明
- repo_context 代码库路径规范包含分支规则
- 文档通过架构评审

## Observability
- execution_unit: task
- log_scope: task-execution
- audit_fields: [run_id, changed_files, evidence_refs]

## Evidence Requirements
- required_refs: [TECH-FEAT-SRC-009-011-001]
- review_required: true

## Rollback Strategy
- mode: revert
- restore_targets: [spec/contracts/shared-input-schema/v1/]
