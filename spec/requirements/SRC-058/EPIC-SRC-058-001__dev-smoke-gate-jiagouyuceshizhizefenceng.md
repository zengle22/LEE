---
id: EPIC-SRC-058-001
ssot_type: epic
title: Dev Smoke Gate 架构与测试职责分层
status: frozen
version: v2
workflow_instance_id: SRC-058-v2
parent_id: SRC-058
derived_from_ids:
- id: SRC-058
  version: v2
  required: true
source_refs:
- SRC-058#scope
owner: null
tags: []
properties:
  src_root_id: SRC-058
frozen_at: '2026-03-17T11:00:00.000000'
---

# Dev Smoke Gate 架构与测试职责分层

## 目标

建立 Dev 主导的 Smoke Gate 架构，明确 Dev 和 QA 测试职责分层，解决 LEE 当前测试流程中职责边界模糊、流程复杂、测试资产不互通、门禁位置靠后和 Handoff 过多等问题，实现快速反馈的质量保障体系。

## 范围

- Dev Smoke 作为 blocker 门禁集成到 merge 流程
- Dev 和 QA 共享同一套 Test Set 资产
- 本地 Smoke 执行时间≤30 分钟
- 通过 priority 字段区分 P0/P1 核心用例与 P2 边缘场景用例
- 本地环境检测与一致性校验工具集成

## 非目标

- QA Test Run 不直接阻塞 merge（作为独立发布前质量确认）
- 不区分 smoke 和 full Test Set（单一 Test Set 原则）
- P2 边缘场景用例为 QA 回归可选，Dev Smoke 默认不执行

## 成功标准

- Dev Smoke 执行时间≤30 分钟
- Smoke Gate 作为 merge 前置条件 100% 覆盖
- Dev 与 QA 共享同一 Test Set 资产，无重复维护
- 测试职责边界清晰，减少跨部门 Handoff
