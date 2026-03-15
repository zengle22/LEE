---
id: SRC-053
ssot_type: src
title: EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则 - 产品目标分析
status: frozen
version: v1
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-003
- ADR-012
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-003
    - ADR-012
    change_scope: 建立 ADR 到业务主链的正式桥接规则，确保所有正式 EPIC 必须经由冻结后的 SRC 进入主链，同时明确 ADR 作为决策型
      SSOT 不直接充当业务 source object 的边界。当 ADR 需要推动下游进入交付主链时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic
      流程。
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    - TECH
    - TASK
    acceptance_impact:
    - EPIC 注册表中不再出现只引用 ADR 不引用 SRC 的新增对象；桥接 SRC 能够清晰表达上游 ADR、变化范围、下游预期对象、验收影响和非目标
    non_goals:
    - bridge SRC 的最终 schema 字段名冻结
    - 是否需要单独 raw_to_src 子模式来处理 ADR 输入
    - 历史 EPIC 的一次性回补迁移策略
    - FEAT、TECH、TASK 的具体字段补充
frozen_at: '2026-03-15T21:11:17.442475'
---

# EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则 - 产品目标分析

## 问题陈述

建立 ADR 到业务主链的正式桥接规则，确保所有正式 EPIC 必须经由冻结后的 SRC 进入主链，同时明确 ADR 作为决策型 SSOT 不直接充当业务 source object 的边界。当 ADR 需要推动下游进入交付主链时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic 流程。

## 目标用户

- LEE 产品团队、治理团队、研发团队，需要明确 ADR 与业务主链边界的所有相关人员

## 业务动因

当前缺失正式桥接规则导致团队在 ADR 直接派生 EPIC 和每个 ADR 都产生 SRC 两种错误模式间摇摆，需要明确哪些 ADR 需要桥接 SRC、桥接 SRC 的语义边界、以及如何保留 SRC 溯源和 ADR 治理引用

## 关键约束

- ADR-003: 产品主链冻结 (ADR 不进入业务主链)
- ADR-012: 产品前半链相位划分 (raw_to_src, src_to_epic)
- 后续 SRC/EPIC/FEAT/RELEASE contract 变更
- 后续 validator 和 workflow 改造

## Bridge Context

- governed_by_adrs: ADR-003, ADR-012
- change_scope: 建立 ADR 到业务主链的正式桥接规则，确保所有正式 EPIC 必须经由冻结后的 SRC 进入主链，同时明确 ADR 作为决策型 SSOT 不直接充当业务 source object 的边界。当 ADR 需要推动下游进入交付主链时，必须先桥接生成薄 SRC，再由该 SRC 进入 src_to_epic 流程。
- expected_downstream_objects: EPIC, FEAT, RELEASE, TECH, TASK

## 验收与交付影响

- EPIC 注册表中不再出现只引用 ADR 不引用 SRC 的新增对象；桥接 SRC 能够清晰表达上游 ADR、变化范围、下游预期对象、验收影响和非目标

## 非目标

- bridge SRC 的最终 schema 字段名冻结
- 是否需要单独 raw_to_src 子模式来处理 ADR 输入
- 历史 EPIC 的一次性回补迁移策略
- FEAT、TECH、TASK 的具体字段补充