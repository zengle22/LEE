---
id: SRC-052
ssot_type: src
title: ADR 桥接 SRC 规则 - 产品目标分析
status: active
version: v1
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-019
- ADR-003
- ADR-012
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-019
    - ADR-003
    - ADR-012
    change_scope: 建立 ADR 到业务主链的正式桥接规则，确保所有 EPIC 必须经由冻结后的 SRC 进入主链，同时保留 ADR 的治理决策地位。当
      ADR 需要触发下游业务交付时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic 流程。
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    - TECH
    - TASK
    acceptance_impact:
    - 新增 EPIC 全部通过 SRC 入口；bridge SRC 语义清晰且与业务 SRC 可区分；历史只挂 ADR 的 EPIC 完成迁移或标记
    non_goals:
    - bridge SRC 的最终 schema 字段名冻结
    - 是否需要单独 raw_to_src 子模式处理 ADR 输入
    - 历史 EPIC 的一次性回补迁移策略
    - FEAT/TECH/TASK 的具体字段补充
---

# ADR 桥接 SRC 规则 - 产品目标分析

## 问题陈述

建立 ADR 到业务主链的正式桥接规则，确保所有 EPIC 必须经由冻结后的 SRC 进入主链，同时保留 ADR 的治理决策地位。当 ADR 需要触发下游业务交付时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic 流程。

## 目标用户

- 产品部门、治理团队、workflow 设计者、需求分析师

## 业务动因

避免 ADR 直接充当 EPIC 业务 source object 导致业务来源与治理来源混淆，同时防止每个 ADR 都产生 SRC 造成治理污染

## 关键约束

- ADR-003 (产品主链冻结)
- ADR-012 (前半链 workflow 划分)
- ADR-001 (SSOT 基础设计)
- 后续 SRC/EPIC contract 变更
- workflow 入口适配

## Bridge Context

- governed_by_adrs: ADR-019, ADR-003, ADR-012
- change_scope: 建立 ADR 到业务主链的正式桥接规则，确保所有 EPIC 必须经由冻结后的 SRC 进入主链，同时保留 ADR 的治理决策地位。当 ADR 需要触发下游业务交付时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic 流程。
- expected_downstream_objects: EPIC, FEAT, RELEASE, TECH, TASK

## 验收与交付影响

- 新增 EPIC 全部通过 SRC 入口；bridge SRC 语义清晰且与业务 SRC 可区分；历史只挂 ADR 的 EPIC 完成迁移或标记

## 非目标

- bridge SRC 的最终 schema 字段名冻结
- 是否需要单独 raw_to_src 子模式处理 ADR 输入
- 历史 EPIC 的一次性回补迁移策略
- FEAT/TECH/TASK 的具体字段补充