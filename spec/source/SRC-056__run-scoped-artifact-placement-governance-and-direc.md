---
id: SRC-056
ssot_type: src
title: Run-Scoped Artifact Placement Governance and Directory Audit
status: frozen
version: v1
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-021
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-021
    change_scope: 建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement
      manifest、公共目录审计 agent 和 gate 阻断机制，确保每次 workflow 运行产生的所有文件都落到正确目录，使需求链最终校验从'只看语义'升级为'语义
      + 目录治理'双重保障。
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    - TECH
    - TASK
    acceptance_impact:
    - requirement-chain-validation 流程包含目录审计步骤且 blocker 强阻断
    - 公共 artifact-placement-reviewer agent 投入使用并服务多 workflow
    - placement manifest contract 和 audit report contract 正式生效
    non_goals:
    - 自动搬运已有错误文件
    - 自动修复历史存量目录问题
    - 用 agent 替代 runtime 进行物理文件写入
    - 修改业务对象主链语义
    - 在本 ADR 中直接定义所有 contract 细节字段
frozen_at: '2026-03-16T11:05:38.547148'
---

# Run-Scoped Artifact Placement Governance and Directory Audit

## 问题陈述

建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest、公共目录审计 agent 和 gate 阻断机制，确保每次 workflow 运行产生的所有文件都落到正确目录，使需求链最终校验从'只看语义'升级为'语义 + 目录治理'双重保障。

## 目标用户

- 产品部门 workflow 维护者、SSOT 规范维护者、公共 agent 开发者、requirement-chain-validation 流程使用者、仓库治理审核人员

## 业务动因

当前目录规则散落在多处，formal 与 non-formal 产物治理口径不一致，导致'链路通过'不等于'交付面可治理'，需要统一真值源和审计机制。

## 关键约束

- ADR-003: 运行时写入保护与 SSOT 物化规则
- ADR-011: Requirement Chain Validation 主链设计
- ADR-020: SSOT Output Contract 规范
- TASK canonical 目录真值规则收口（强关联实施项）
- placement manifest contract 和 audit report contract 新增

## Bridge Context

- governed_by_adrs: ADR-021
- change_scope: 建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest、公共目录审计 agent 和 gate 阻断机制，确保每次 workflow 运行产生的所有文件都落到正确目录，使需求链最终校验从'只看语义'升级为'语义 + 目录治理'双重保障。
- expected_downstream_objects: EPIC, FEAT, RELEASE, TECH, TASK

## 验收与交付影响

- requirement-chain-validation 流程包含目录审计步骤且 blocker 强阻断
- 公共 artifact-placement-reviewer agent 投入使用并服务多 workflow
- placement manifest contract 和 audit report contract 正式生效

## 非目标

- 自动搬运已有错误文件
- 自动修复历史存量目录问题
- 用 agent 替代 runtime 进行物理文件写入
- 修改业务对象主链语义
- 在本 ADR 中直接定义所有 contract 细节字段