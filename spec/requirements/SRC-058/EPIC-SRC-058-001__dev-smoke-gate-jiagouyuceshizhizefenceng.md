---
id: EPIC-SRC-058-001
ssot_type: epic
title: Dev Smoke Gate 架构与测试职责分层
status: frozen
version: v3
workflow_instance_id: wf_task_fix-p0p1-issues
parent_id: SRC-058
derived_from_ids:
- id: SRC-058
  version: v3
  required: true
source_refs:
- SRC-058#scope
owner: null
tags: []
properties:
  src_root_id: SRC-058
frozen_at: '2026-03-17T12:00:00.000000'
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

## Blocker 定义

### Blocker (阻塞 merge)

以下情况触发 blocker，自动拒绝 merge：

- **P0 测试用例失败**: 核心功能测试失败，直接影响产品质量
- **P1 测试用例连续失败 3 次**: 同一用例在 3 次独立执行中均失败，判定为稳定性问题
- **环境检测失败**: 本地环境与 CI 标准环境不一致

### Critical (建议修复但不阻塞)

以下情况触发 critical 告警，允许 merge 但记录技术债务：

- **P1 测试用例单次失败**: 可能为偶发问题，建议修复但不强制阻塞
- **P2 测试用例失败**: 边缘场景问题，在 QA 回归阶段处理
- **Flaky Test 标记用例失败**: 已识别的不稳定测试，不阻塞但自动创建 bug

### 误报处理机制

- 单次失败的 P0/P1 用例自动触发重试 (最多 3 次)
- 3 次重试全部失败才判定为 blocker
- 连续 5 次执行通过率<80% 的用例自动标记为 flaky test
- Flaky test 不阻塞 merge，但生成技术债务工单并通知 QA
