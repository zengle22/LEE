---
id: TASK-FEAT-142-002
ssot_type: task
title: QAP0校验规则集与绑定检查CLI实现
status: frozen
version: v1
parent_id: FEAT-142
derived_from_ids: []
source_refs:
- FEAT-142#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_142_002
  identity_kind: ssot
frozen_at: '2026-03-12T20:25:27.389006'
---

# Objective

实现QA专用的P0校验规则集和绑定关系检查CLI命令

# Description

基于TECH-ARCH-FEAT-142 Phase 1.3-1.4和Section 3.3.3，在ssot_service.py中实现QA-P0-001至QA-P0-006六条硬规则；扩展lee ssot CLI添加binding-check和lint --department=qa命令，支持TESTSET单一FEAT绑定验证、TESTPLAN挂载RELEASE验证、EPIC派生阻断验证

## Acceptance Mapping
- FEAT-142 / AC-001-001: TESTSET单一FEAT绑定校验规则(QA-P0-001)实现并通过测试
- FEAT-142 / AC-001-002: TESTPLAN挂载RELEASE校验规则(QA-P0-003)实现并通过测试
- FEAT-142 / AC-001-004: TESTSET派生路径阻断规则(QA-P0-004)实现，禁止EPIC直接派生
- FEAT-142 / AC-001-005: QA资产元数据完整性校验规则集实现

## Dependencies
- TASK-FEAT-142-001

## Definition Of Done
- ssot_service.py中实现qa_p0_rules列表，包含6条P0校验规则
- CLI扩展binding-check命令，支持TESTSET/TESTPLAN/RELEASE绑定验证
- CLI扩展lint --department=qa命令，执行QA专用校验规则集
- 每条P0规则有对应的单元测试和负面测试用例
- AC-001-001至AC-001-005验证场景全部通过
- 代码审查通过并合并到main分支
- TASK文件已冻结
