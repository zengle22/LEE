---
id: TASK-FEAT-SRC-056-001-001
ssot_type: task
title: 定义 Placement Manifest Schema 结构
status: frozen
version: v1
workflow_instance_id: wf_task_f22cbc5e
parent_id: FEAT-SRC-056-001
derived_from_ids:
  - id: FEAT-SRC-056-001
    version: v1
    required: true
source_refs:
  - FEAT-SRC-056-001#acceptance_criteria
  - TECH-FEAT-SRC-056-001#design
owner: workflow-architect
tags: [schema, manifest, governance]
properties:
  src_root_id: SRC-056
  task_kind: governance
  workstream: workflow-spec
  priority: P0
  milestone: M1-Contract
  estimated_effort: 0.5 day
  lifecycle_status: frozen
  acceptance_criteria:
    - manifest schema 包含 manifest_id、run_scope、expected_artifacts、placement_rules 字段
    - schema 定义每个字段的数据类型和约束
  definition_of_done:
    - schema YAML 文件已创建
    - schema 通过技术评审
  inputs:
    - FEAT-SRC-056-001 acceptance criteria
    - ADR-021 governance requirements
  outputs:
    - placement-manifest-schema.yaml
frozen_at: '2026-03-16T14:30:00+08:00'
---

# TASK-FEAT-SRC-056-001-001: 定义 Placement Manifest Schema 结构

## 目标

定义 placement manifest 的核心 schema 结构。

## 验收标准

- manifest schema 包含 manifest_id、run_scope、expected_artifacts、placement_rules 字段
- schema 定义每个字段的数据类型和约束

## 完成定义

- schema YAML 文件已创建
- schema 通过技术评审

## 输入

- FEAT-SRC-056-001 acceptance criteria
- ADR-021 governance requirements

## 输出

- placement-manifest-schema.yaml

## 依赖

- TECH-FEAT-SRC-056-001: placement manifest schema technical design
