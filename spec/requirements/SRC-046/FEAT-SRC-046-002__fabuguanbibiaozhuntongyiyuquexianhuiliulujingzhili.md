---
id: FEAT-SRC-046-002
ssot_type: feat
title: 发布关闭标准统一与缺陷回流路径治理
status: draft
version: v1
workflow_instance_id: wf_task_288ce199
parent_id: EPIC-SRC-046-001
derived_from_ids:
- id: EPIC-SRC-046-001
  version: v1
source_refs:
- EPIC-SRC-046-001#scope
owner: null
tags: []
properties:
  src_root_id: SRC-046
  priority: P0
  delivery_slice: governance-closeout
---

# 发布关闭标准统一与缺陷回流路径治理

## Goal
统一缺陷回流路径和发布关闭标准，形成可审计的治理闭环

## User Value
所有发布关闭操作遵循统一治理路径，无例外通道，100% 的 bugfix 可明确归属到对应交付版本并重新进入交付轴闭环

## Inputs
- 已冻结的 RELEASE 对象 (scope_frozen 状态)
- 已完成的 TESTPLAN 对象
- BUG 对象 (found_in_release 指向当前 RELEASE)

## Processing
- 校验 blocker bug 状态
- 校验发布报告完整性 (release/test_execution/go_no_go)
- 执行 release-check 聚合校验
- 执行 release-close 关闭发布

## Outputs
- RELEASE 对象 (released 状态)
- RELEASE_REPORT (发布报告)
- GO_NO_GO_REPORT (发布判定报告)

## Acceptance Criteria
- 所有发布关闭操作遵循统一治理路径
- 无例外通道存在
- 100% bugfix 可归属到交付版本并进入闭环

## Acceptance Checks
- AC-001: 执行 release-check 校验
- AC-002: 豁免 blocker bug
- AC-003: 发布报告完整性校验
