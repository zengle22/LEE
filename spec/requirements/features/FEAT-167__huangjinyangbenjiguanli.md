---
id: FEAT-167
ssot_type: feat
title: 黄金样本集管理
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_009
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.773961'
---

# Goal

建立并维护覆盖典型场景的标准化测试样本
# User Value

为测试体系提供可靠的基准数据，支持测试正确性验证、回归测试和性能基准测试
# Inputs

- 样本数据（正样本/负样本/边界样本）
- 样本分类标签
- 样本元数据（创建时间、用途、预期结果）
- 版本标签
# Processing

- 加载样本数据并分类
- 执行样本有效性校验
- 管理样本版本和变更历史
- 提供样本动态加载接口
- 执行样本评审流程
# Outputs

- 分类样本集合
- 样本版本历史
- 样本有效性报告
- 样本使用情况统计
# Acceptance

- 支持按需求链层级、场景、测试器分类
- 覆盖比例：正常样本60%、异常样本25%、边界样本15%
- 正样本不少于50个
- 负样本不少于30个（每种问题类型至少5个）
- 边界样本不少于20个
# Acceptance Checks

## AC-009-001

- Scenario: 样本分类管理
- Given: 新增正样本、负样本、边界样本
- When: 执行样本分类
- Then: 样本按类型正确归类，比例符合要求
- Trace Hints: TECH, TESTSET

## AC-009-002

- Scenario: 样本版本管理
- Given: 样本内容需要更新
- When: 执行版本更新
- Then: 保留历史版本，生成新版本标签
- Trace Hints: TECH, TASK

## AC-009-003

- Scenario: 样本动态加载
- Given: 测试器请求加载特定场景样本
- When: 执行样本加载
- Then: 返回匹配的样本集合
- Trace Hints: TECH, TESTSET

## AC-009-004

- Scenario: 样本有效性校验
- Given: 样本集存在不符合schema的样本
- When: 执行有效性校验
- Then: 报告无效样本清单，阻止其进入测试流程
- Trace Hints: TECH, UI, TESTSET
# Dependencies

- EPIC-030
- FEAT-160
# Non Goals

- 不生成需求内容（仅管理已有样本）
- 不替代实际生产数据的测试
- 不自动修复样本中的问题
