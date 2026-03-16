---
id: FEAT-SRC-046-001
ssot_type: feat
title: 交付主链建立与对象绑定一致性治理
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
  delivery_slice: governance-core
---

# 交付主链建立与对象绑定一致性治理

## Goal
建立以 RELEASE 为起点的交付主链，确保交付对象绑定一致性和 scope 完整性

## User Value
确保所有正式发布版本通过统一的交付主链进行交付，交付链上各对象 (RELEASE/DEVPLAN/TESTPLAN/TASK) 的绑定关系可追溯、可验证

## Inputs
- 已冻结的 FEAT 对象 (FEAT@version)
- ADR-001 治理基线
- 现有 RELEASE/DEVPLAN/TESTPLAN/TASK 对象基础

## Processing
- 创建 RELEASE 对象并初始化 scope
- Pin 住 FEAT@version 到 derived_from_ids
- 执行 scope validate 校验
- 执行 scope freeze 冻结范围
- 派生 DEVPLAN 和 TESTPLAN 骨架

## Outputs
- REL-{version} (RELEASE 对象，scope_frozen 状态)
- DEVPLAN-REL-{version} (开发计划)
- TESTPLAN-REL-{version} (测试计划)

## Acceptance Criteria
- 100% 的正式发布版本通过交付主链完成交付
- 交付对象绑定关系可追溯、可验证
- RELEASE 为唯一起点，无其他入口

## Acceptance Checks
- AC-001: 创建 RELEASE 并绑定 FEAT 版本
- AC-002: 校验交付对象绑定一致性
- AC-003: 验证 scope 冻结
