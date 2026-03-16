---
id: TASK-FEAT-SRC-056-002-001
ssot_type: task
title: 实现 Artifact Placement Reviewer Agent 核心模块
status: frozen
version: v1
workflow_instance_id: wf_task_f22cbc5e
parent_id: FEAT-SRC-056-002
derived_from_ids:
  - id: FEAT-SRC-056-002
    version: v1
    required: true
source_refs:
  - FEAT-SRC-056-002#acceptance_criteria
  - TECH-FEAT-SRC-056-002#design
owner: backend-engineer
tags: [agent, implementation, governance]
properties:
  src_root_id: SRC-056
  task_kind: implementation
  workstream: core-runtime
  priority: P0
  milestone: M2-Agent
  estimated_effort: 2 days
  lifecycle_status: frozen
  acceptance_criteria:
    - agent 模块能够读取 placement manifest 并解析 expected artifacts
    - agent 能够扫描指定目录并比对实际文件位置与 manifest 规则
    - agent 输出审计结果报告，包含违规文件列表和合规文件列表
  definition_of_done:
    - agent 核心模块已实现
    - 单元测试通过
    - 集成测试通过
  inputs:
    - TECH-SRC-056-002 design spec
    - placement-manifest-schema.yaml
  outputs:
    - artifact_placement_reviewer.py
    - test_artifact_placement_reviewer.py
frozen_at: '2026-03-16T14:30:00+08:00'
---

# TASK-FEAT-SRC-056-002-001: 实现 Artifact Placement Reviewer Agent 核心模块

## 目标

实现 artifact placement reviewer agent 的核心审计逻辑。

## 验收标准

- agent 模块能够读取 placement manifest 并解析 expected artifacts
- agent 能够扫描指定目录并比对实际文件位置与 manifest 规则
- agent 输出审计结果报告，包含违规文件列表和合规文件列表

## 完成定义

- agent 核心模块已实现
- 单元测试通过
- 集成测试通过

## 输入

- TECH-FEAT-SRC-056-002 design spec
- placement-manifest-schema.yaml

## 输出

- artifact_placement_reviewer.py
- test_artifact_placement_reviewer.py

## 依赖

- TECH-FEAT-SRC-056-001: placement manifest schema
- TECH-FEAT-SRC-056-002: artifact placement reviewer agent technical design
