---
id: FEAT-149
ssot_type: feat
title: formal object自动继承机制
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_005
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.610436'
---

# Goal

实现从SRC派生的EPIC/FEAT/ADR自动继承source_refs和父子关系，消除人工维护错误
# User Value

从SRC派生的EPIC/FEAT/ADR自动继承source_refs和父子关系，消除人工维护错误
# Inputs

- SRC对象schema定义
- EPIC/FEAT/ADR schema定义
- 继承规则定义(source_refs, parent_id, derived_from_ids)
- 高层命令创建流程
# Processing

- 分析SRC与formal object间的字段映射关系
- 设计自动继承引擎，支持source_refs继承
- 实现parent_id与derived_from_ids自动填充逻辑
- 在高层命令创建流程中集成自动继承机制
- 实现继承关系可视化查询功能
# Outputs

- 自动继承引擎实现
- 字段继承映射配置
- 继承关系可视化组件
- 继承准确性验证报告
# Acceptance

- 当通过高层命令创建EPIC/FEAT/ADR时，自动从派生来源(SRC或父对象)继承source_refs
- parent_id与derived_from_ids自动填充
- 验收时验证：创建10个派生对象，source_refs继承准确率100%，人工维护字段为空
# Acceptance Checks

## AC-017-005-01

- Scenario: source_refs自动继承
- Given: 从带有source_refs的SRC创建EPIC
- When: 执行lee epic init --from-src SRC-001
- Then: 生成的EPIC自动继承SRC-001的source_refs
- Trace Hints: TECH, TASK, TESTSET

## AC-017-005-02

- Scenario: 父子关系自动填充
- Given: 从EPIC创建FEAT
- When: 执行lee feat init --from-epic EPIC-017
- Then: 生成的FEAT的parent_id自动填充为EPIC-017，derived_from_ids包含EPIC-017
- Trace Hints: TECH, TESTSET

## AC-017-005-03

- Scenario: 继承准确率验证
- Given: 准备10个不同来源的派生对象创建请求
- When: 批量执行创建操作
- Then: source_refs继承准确率100%，无需人工干预
- Trace Hints: TESTSET, TECH
# Dependencies

- FEAT-017-002
# Non Goals

- None
