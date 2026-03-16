---
id: FEAT-SRC-056-002
ssot_type: feat
title: Artifact Placement Reviewer Agent Implementation
status: frozen
version: v1
workflow_instance_id: wf_task_21e3e7b1
parent_id: EPIC-SRC-056-001
derived_from_ids:
  - id: EPIC-SRC-056-001
    version: v1
    required: true
source_refs:
  - EPIC-SRC-056-001#scope
  - ADR-021
owner: product-ai
tags: [placement, agent, audit, governance]
properties:
  src_root_id: SRC-056
  goal: 实现独立的 directory audit agent 模块，支持读取 placement manifest 并审计实际文件目录，输出审计结果报告
  user_value: 提供可被多 workflow 复用的目录审计能力，自动检测文件放置违规
  priority: P0
  delivery_slice: mvp
  lifecycle_status: frozen
  acceptance_criteria:
    - agent 模块能够读取 placement manifest 并解析 expected artifacts
    - agent 能够扫描指定目录并比对实际文件位置与 manifest 规则
    - agent 输出审计结果报告，包含违规文件列表和合规文件列表
    - agent 支持 CLI 调用（lee audit --manifest <path> --target <path>）
    - agent 支持 Python API 调用（import artifact_placement_reviewer）
    - agent 可被 requirement-chain-validation workflow 集成调用
  acceptance_checks:
    - id: AC-001
      scenario: agent 读取 manifest 并解析 expected artifacts
      given: 提供符合 schema 的 placement manifest 文件
      when: 调用 agent 的 load_manifest 方法
      then: agent 成功解析 manifest 并返回 expected artifacts 列表
      trace_hints: [TASK, TESTSET, TECH]
    - id: AC-002
      scenario: agent 扫描目录并比对规则
      given: agent 已加载 manifest 且提供目标目录路径
      when: 调用 agent 的 audit 方法
      then: agent 扫描目录并输出违规文件列表和合规文件列表
      trace_hints: [TASK, TESTSET, TECH]
    - id: AC-003
      scenario: agent CLI 调用
      given: agent 模块已安装且 manifest 文件存在
      when: 执行 lee audit --manifest <path> --target <path>
      then: CLI 输出审计结果并生成 report 文件
      trace_hints: [TASK, TESTSET, TECH]
    - id: AC-004
      scenario: agent 被 requirement-chain-validation 调用
      given: requirement-chain-validation workflow 执行到 audit 步骤
      when: workflow 调用 agent API
      then: agent 返回审计结果供后续 gate 决策
      trace_hints: [TASK, TESTSET]
  dependencies:
    - FEAT-SRC-056-001
  non_goals:
    - 自动修复错误文件位置
    - 修改业务对象主链语义
  inputs:
    - placement-manifest-contract.md 和 placement-manifest-schema.yaml
    - 实际 workflow 运行目录结构
    - audit 触发信号（manual 或 automated gate）
  outputs:
    - artifact_placement_reviewer.py agent 核心模块
    - placement_audit_report_schema.yaml 审计结果 schema
    - example-audit-report.yaml 示例审计报告
    - agent-usage-guide.md 使用指南
  derived_object_expectations:
    task_required: true
    testset_required: true
    testset_owner: qa
    qa_seed_required: true
frozen_at: '2026-03-16T12:00:00+08:00'
---

# Artifact Placement Reviewer Agent Implementation

## 目标

实现独立的 directory audit agent 模块，支持读取 placement manifest 并审计实际文件目录，输出审计结果报告。

## 用户价值

提供可被多 workflow 复用的目录审计能力，自动检测文件放置违规。

## 输入

- placement-manifest-contract.md 和 placement-manifest-schema.yaml
- 实际 workflow 运行目录结构
- audit 触发信号（manual 或 automated gate）

## 验收标准

- agent 模块能够读取 placement manifest 并解析 expected artifacts
- agent 能够扫描指定目录并比对实际文件位置与 manifest 规则
- agent 输出审计结果报告，包含违规文件列表和合规文件列表
- agent 支持 CLI 调用（lee audit --manifest <path> --target <path>）
- agent 支持 Python API 调用（import artifact_placement_reviewer）
- agent 可被 requirement-chain-validation workflow 集成调用

## 依赖

- FEAT-SRC-056-001

## 非目标

- 自动修复错误文件位置
- 修改业务对象主链语义
