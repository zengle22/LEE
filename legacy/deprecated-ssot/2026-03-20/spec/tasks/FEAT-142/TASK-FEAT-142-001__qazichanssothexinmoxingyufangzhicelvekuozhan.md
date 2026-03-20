---
id: TASK-FEAT-142-001
ssot_type: task
title: QA资产SSOT核心模型与放置策略扩展
status: frozen
version: v1
parent_id: FEAT-142
derived_from_ids: []
source_refs:
- FEAT-142#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_142_001
  identity_kind: ssot
frozen_at: '2026-03-12T20:25:27.380249'
---

# Objective

扩展SSOT类型系统和文件放置策略以支持QA测试资产的三轴模型对齐

# Description

基于TECH-ARCH-FEAT-142 Phase 1.1-1.2，修改types.py中ObjectCategory的parent_requirements，确立TESTSET->FEAT、TESTPLAN->RELEASE、TASK->TESTPLAN|DEVPLAN的绑定约束；扩展placement.py添加spec/testing/testsets、spec/delivery/testplans等QA对象目录的放置规则

## Acceptance Mapping
- FEAT-142 / AC-001-001: TESTSET单一FEAT绑定约束在ObjectCategory中定义完成
- FEAT-142 / AC-001-002: TESTPLAN挂载RELEASE的父对象约束在类型系统中固化
- FEAT-142 / AC-001-003: 三轴标签(axis_tag)在类型模型中有明确定义和校验

## Definition Of Done
- types.py中ObjectCategory.parent_requirements更新，包含TESTSET/TESTPLAN/TASK的父对象约束
- placement.py中PLACEMENT_RULES新增QA对象目录映射
- 单元测试覆盖新的parent_requirements校验逻辑
- 代码审查通过并合并到main分支
- TASK文件已冻结
