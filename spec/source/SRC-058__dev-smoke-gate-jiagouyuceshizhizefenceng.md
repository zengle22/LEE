---
id: SRC-058
ssot_type: src
title: Dev Smoke Gate 架构与测试职责分层
status: active
version: v2
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-023
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-023
    change_scope: 建立 Dev 主导的 Smoke Gate 架构，明确 Dev 和 QA 测试职责分层，解决 LEE 当前测试流程中职责边界模糊、流程复杂、测试资产不互通、门禁位置靠后和
      Handoff 过多等问题，实现快速反馈的质量保障体系。
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    acceptance_impact:
    - Dev Smoke 作为 blocker 门禁成功集成到 merge 流程；Dev 和 QA 共享同一套 Test Set 资产；本地 Smoke 执行时间≤30
      分钟。
    non_goals:
    - QA Test Run 不直接阻塞 merge（作为独立发布前质量确认）
    - 不区分 smoke 和 full Test Set（单一 Test Set 原则，通过 priority 字段区分）
    - P2 边缘场景用例为 QA 回归可选，Dev Smoke 默认不执行
---

# Dev Smoke Gate 架构与测试职责分层

## 问题陈述

建立 Dev 主导的 Smoke Gate 架构，明确 Dev 和 QA 测试职责分层，解决 LEE 当前测试流程中职责边界模糊、流程复杂、测试资产不互通、门禁位置靠后和 Handoff 过多等问题，实现快速反馈的质量保障体系。

## 目标用户

- Dev 部门（执行 Smoke Test）、QA 部门（设计 Test Set）、Engineering Governance 部门（定义门禁策略）

## 业务动因

解决 Dev 和 QA 协作效率低下的根本问题，减少重复测试和 Handoff，实现快速反馈的质量保障。

## 关键约束

- ADR-005: Gate 三分类治理模型
- ADR-007: QA Department SSOT Alignment
- ADR-008: Dev Department SSOT Alignment
- ADR-011: 需求联测一致性测试体系建设
- Test Set YAML 设计资产生成能力
- 本地环境检测与一致性校验工具

## Bridge Context

- governed_by_adrs: ADR-023
- change_scope: 建立 Dev 主导的 Smoke Gate 架构，明确 Dev 和 QA 测试职责分层，解决 LEE 当前测试流程中职责边界模糊、流程复杂、测试资产不互通、门禁位置靠后和 Handoff 过多等问题，实现快速反馈的质量保障体系。
- expected_downstream_objects: EPIC, FEAT, RELEASE

## 验收与交付影响

- Dev Smoke 作为 blocker 门禁成功集成到 merge 流程；Dev 和 QA 共享同一套 Test Set 资产；本地 Smoke 执行时间≤30 分钟。

## 非目标

- QA Test Run 不直接阻塞 merge（作为独立发布前质量确认）
- 不区分 smoke 和 full Test Set（单一 Test Set 原则，通过 priority 字段区分）
- P2 边缘场景用例为 QA 回归可选，Dev Smoke 默认不执行