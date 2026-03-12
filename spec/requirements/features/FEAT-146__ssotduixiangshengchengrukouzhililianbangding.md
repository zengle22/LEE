---
id: FEAT-146
ssot_type: feat
title: SSOT对象生成入口治理链绑定
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.584633'
---

# Goal

确保所有formal object(EPIC/FEAT/ADR)的生成必须经过完整的review/gate/freeze治理链，实现registry中对象100%可信度与可追溯性
# User Value

所有formal object(EPIC/FEAT/ADR)必须经过完整的review/gate/freeze治理链，确保registry中对象的可信度与可追溯性
# Inputs

- formal object类型定义(epic/feat/adr)
- 治理链状态模型(review/gate/freeze)
- SSOT对象metadata schema
- workflow治理引擎接口
# Processing

- 定义formal object创建必须经过的治理检查点
- 设计metadata中治理链引用的数据结构
- 实现gate验证拦截器，阻止未通过验证的对象创建
- 实现metadata自动注入机制，将review_id/gate_id/freeze_timestamp写入对象
- 集成workflow治理引擎与SSOT物化接口
# Outputs

- 治理链绑定规范文档
- gate验证拦截器实现
- metadata自动注入模块
- 治理状态查询API
- 治理链一致性校验工具
# Acceptance

- 任何formal object的创建必须通过gate验证
- 对象metadata中包含完整的治理链引用(review_id/gate_id/freeze_timestamp)
- 验收时抽查registry中的对象，100%具备完整治理链引用，无游离对象
# Acceptance Checks

## AC-017-002-01

- Scenario: gate验证拦截
- Given: 一个未通过gate验证的对象创建请求
- When: 请求到达SSOT物化层
- Then: 系统拒绝创建并返回治理链未完成错误
- Trace Hints: TECH, TASK, TESTSET

## AC-017-002-02

- Scenario: metadata完整性验证
- Given: 通过治理链创建的formal object
- When: 查询对象metadata
- Then: 包含review_id、gate_id、freeze_timestamp且值非空
- Trace Hints: TECH, TESTSET

## AC-017-002-03

- Scenario: registry一致性审计
- Given: registry中所有formal object
- When: 执行治理链完整性扫描
- Then: 100%对象具备完整治理链引用，游离对象数量为0
- Trace Hints: TESTSET, TECH
# Dependencies

- FEAT-017-001
# Non Goals

- 不实现跨runtime的分布式SSOT同步
