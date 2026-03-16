---
id: SRC-054
ssot_type: src
title: EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则 - 产品目标分析
status: frozen
version: v1
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-019
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-019
    change_scope: 建立 ADR 到业务主链的正式桥接规则，明确 EPIC 入口必须经由冻结后的 SRC，规范 ADR 何时应桥接 SRC 以及何时不需要，确保治理决策与业务主链分离且有序衔接
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    - TECH
    - TASK
    acceptance_impact:
    - 所有正式 EPIC 都有至少一个冻结 SRC 作为上游
    - 需触发下游 EPIC/FEAT 设计的 ADR 都生成了桥接 SRC
    - 纯治理/纯说明/纯约束型 ADR 未生成不必要的业务链对象
    - EPIC 关系语义采用 derived_from_ids 包含 SRC、source_refs 指向 SRC、governing_adrs 保留 ADR
    - 进入正式交付的 ADR 触发的变更都物化出可被 RELEASE pin 住的 thin FEAT
    non_goals:
    - Bridge SRC 的最终 schema 字段名冻结
    - 是否需要单独 raw_to_src 子模式处理 ADR 输入
    - 历史 EPIC 的一次性回补迁移策略
    - FEAT/TECH/TASK 的具体字段补充
    - 用 SRC 替代 ADR 的治理地位
    - 要求每个 ADR 都生成 EPIC 或 SRC
frozen_at: '2026-03-15T21:56:43.225725'
---

# EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则 - 产品目标分析

## 问题陈述

建立 ADR 到业务主链的正式桥接规则，明确 EPIC 入口必须经由冻结后的 SRC，规范 ADR 何时应桥接 SRC 以及何时不需要，确保治理决策与业务主链分离且有序衔接

## 目标用户

- 产品治理团队 (governance)、产品主编排者、EPIC/FEAT 设计者、Workflow 维护者、Contract/Schema 维护者、Review Agent 开发者

## 业务动因

当前缺少正式桥接规则明确哪些 ADR 需要桥接 SRC、桥接 SRC 的语义边界是什么、EPIC 如何同时保留 SRC 溯源和 ADR 治理引用。若无此规则，会导致治理来源与业务来源混淆，弱化 SRC 作为正式主链入口的地位，或导致治理污染

## 关键约束

- ADR-003 冻结的产品主链和 ADR 不进入业务主链规则
- ADR-012 冻结的 raw_to_src 和 src_to_epic 分阶段划分
- 现有 SRC/EPIC/FEAT contract 和 schema 体系
- 产品主链 workflow 基础设施

## Bridge Context

- governed_by_adrs: ADR-019
- change_scope: 建立 ADR 到业务主链的正式桥接规则，明确 EPIC 入口必须经由冻结后的 SRC，规范 ADR 何时应桥接 SRC 以及何时不需要，确保治理决策与业务主链分离且有序衔接
- expected_downstream_objects: EPIC, FEAT, RELEASE, TECH, TASK

## 验收与交付影响

- 所有正式 EPIC 都有至少一个冻结 SRC 作为上游
- 需触发下游 EPIC/FEAT 设计的 ADR 都生成了桥接 SRC
- 纯治理/纯说明/纯约束型 ADR 未生成不必要的业务链对象
- EPIC 关系语义采用 derived_from_ids 包含 SRC、source_refs 指向 SRC、governing_adrs 保留 ADR
- 进入正式交付的 ADR 触发的变更都物化出可被 RELEASE pin 住的 thin FEAT

## 非目标

- Bridge SRC 的最终 schema 字段名冻结
- 是否需要单独 raw_to_src 子模式处理 ADR 输入
- 历史 EPIC 的一次性回补迁移策略
- FEAT/TECH/TASK 的具体字段补充
- 用 SRC 替代 ADR 的治理地位
- 要求每个 ADR 都生成 EPIC 或 SRC