---
id: FEAT-163
ssot_type: feat
title: Overlap测试器
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_005
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.736273'
---

# Goal

检测FEAT层与TASK层的功能重叠与边界冲突，确保拆分合理性
# User Value

识别冗余开发和职责不清问题，优化需求拆分质量，提升研发资源利用效率
# Inputs

- 同层节点集合（FEAT层或TASK层）
- 节点功能描述文本
- 重叠检测阈值配置（默认相似度阈值）
- 聚类算法参数（聚类数量、距离度量）
# Processing

- 加载同层节点集合
- 计算节点间功能相似度
- 识别超过阈值的相似节点对
- 执行聚类分析
- 生成重叠关系图
# Outputs

- 重叠节点对列表及相似度评分
- 聚类分析结果
- 合并或重构建议
- 重叠关系可视化数据
- Overlap Rate统计
# Acceptance

- 计算同层节点间的功能相似度
- 识别描述相似度超过阈值的节点对
- 支持FEAT层和TASK层分别检测
- Overlap Rate ≤ 10%
- 检测节点间的职责交叉
# Acceptance Checks

## AC-005-001

- Scenario: 功能重叠检测
- Given: 两个FEAT节点描述高度相似的功能
- When: 执行重叠检测
- Then: 报告重叠节点对及相似度评分
- Trace Hints: TECH, UI, TESTSET

## AC-005-002

- Scenario: 重叠率计算
- Given: 100个FEAT中有8对重叠节点
- When: 计算Overlap Rate
- Then: 输出重叠率为8%，满足≤10%阈值
- Trace Hints: TECH, UI, TESTSET

## AC-005-003

- Scenario: 聚类分析
- Given: 存在多个功能相似的TASK节点
- When: 执行聚类算法
- Then: 输出聚类结果和合并建议
- Trace Hints: TECH, TESTSET

## AC-005-004

- Scenario: 增量重叠检测
- Given: 新增一个FEAT节点
- When: 执行增量检测
- Then: 仅计算与现有节点的相似度，输出重叠风险
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-030
- FEAT-159
- FEAT-162
# Non Goals

- 不自动合并重叠节点
- 不做技术实现层面的重复代码检测
- 不强制要求消除所有重叠（保留合理抽象层级）
