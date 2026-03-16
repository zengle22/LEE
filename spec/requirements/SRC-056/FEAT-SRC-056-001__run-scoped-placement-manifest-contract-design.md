---
id: FEAT-SRC-056-001
ssot_type: feat
title: Run-Scoped Placement Manifest Contract Design
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
tags: [placement, manifest, contract, governance]
properties:
  src_root_id: SRC-056
  goal: 定义 placement manifest 的 schema 结构、生成时机和消费方式，为每次 workflow 运行提供预期的文件放置清单契约
  user_value: 为每次 workflow 运行定义预期的文件放置清单，使目录治理有明确的契约依据
  priority: P0
  delivery_slice: mvp
  lifecycle_status: frozen
  acceptance_criteria:
    - placement manifest schema 包含 manifest_id、run_scope、expected_artifacts、placement_rules 字段
    - contract 文档明确定义 manifest 生成时机为 workflow 初始化阶段
    - contract 文档明确定义 manifest 消费方式为 auditer agent 读取和 validator 引用
    - 提供至少一个完整的示例 manifest 文件
    - 不包含 runtime manifest 生成实现代码
  acceptance_checks:
    - id: AC-001
      scenario: placement manifest schema 结构完整性验证
      given: EPIC scope 定义了 run-scoped artifact 类型清单
      when: 设计 placement manifest contract
      then: schema 包含 manifest_id、run_scope、expected_artifacts、placement_rules 四个核心字段
      trace_hints: [TASK, TESTSET]
    - id: AC-002
      scenario: contract 文档明确定义生成时机和消费方式
      given: manifest schema 结构已确定
      when: 编写 contract 文档
      then: 文档明确说明 manifest 在 workflow 初始化阶段生成，由 auditer agent 和 validator 消费
      trace_hints: [TASK, TESTSET]
    - id: AC-003
      scenario: 提供完整的示例 manifest 文件
      given: manifest schema 和 contract 文档已完成
      when: 创建示例 manifest
      then: 示例文件符合 schema 定义且包含至少 3 种 artifact 类型的放置规则
      trace_hints: [TASK, TESTSET]
  dependencies: []
  non_goals:
    - runtime manifest 生成实现
    - 文件物理写入逻辑
  inputs:
    - EPIC-SRC-056-001 scope 定义的 run-scoped artifact 类型清单
    - workflow 运行上下文参数（run_id、step_workspace、workflow_name）
    - 目录治理政策基线规则
  outputs:
    - placement-manifest-contract.md 规范文档
    - placement-manifest-schema.yaml schema 定义
    - example-placement-manifest-run-001.yaml 示例清单
    - manifest-consumption-guide.md 消费指南
  derived_object_expectations:
    task_required: true
    testset_required: true
    testset_owner: qa
    qa_seed_required: true
frozen_at: '2026-03-16T12:00:00+08:00'
---

# Run-Scoped Placement Manifest Contract Design

## 目标

定义 placement manifest 的 schema 结构、生成时机和消费方式，为每次 workflow 运行提供预期的文件放置清单契约。

## 用户价值

为每次 workflow 运行定义预期的文件放置清单，使目录治理有明确的契约依据。

## 输入

- EPIC-SRC-056-001 scope 定义的 run-scoped artifact 类型清单
- workflow 运行上下文参数（run_id、step_workspace、workflow_name）
- 目录治理政策基线规则

## 输入契约

**必需产物**:
- EPIC-SRC-056-001 frozen scope
- draft run-scoped artifact catalog
- baseline directory governance policy

**必需字段**:
- formal_ssot_id
- source_refs
- governing_adrs
- repo_context
- workflow_run_context

**消费规则**:
- manifest schema 必须被下游 agent 和 validator 引用
- manifest 示例必须可用于 test case 生成
- contract 文档必须支持 gate 逻辑审查

## 处理

- 定义 placement manifest 的核心 schema 结构（manifest_id、run_scope、expected_artifacts、placement_rules）
- 规范 manifest 生成时机（workflow 初始化阶段）
- 定义 manifest 消费方式（auditer agent 读取、validator 引用）
- 输出 contract 文档和示例 manifest

## 输出

- placement-manifest-contract.md 规范文档
- placement-manifest-schema.yaml schema 定义
- example-placement-manifest-run-001.yaml 示例清单
- manifest-consumption-guide.md 消费指南

## 验收标准

- placement manifest schema 包含 manifest_id、run_scope、expected_artifacts、placement_rules 字段
- contract 文档明确定义 manifest 生成时机为 workflow 初始化阶段
- contract 文档明确定义 manifest 消费方式为 auditer agent 读取和 validator 引用
- 提供至少一个完整的示例 manifest 文件
- 不包含 runtime manifest 生成实现代码

## 依赖

无

## 非目标

- runtime manifest 生成实现
- 文件物理写入逻辑

## 派生物期望

- TASK: 必需
- TESTSET: 必需
- TESTSET owner: qa
- QA seed: 必需
