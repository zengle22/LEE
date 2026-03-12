---
id: FEAT-162
ssot_type: feat
title: Semantic测试器
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.727223'
---

# Goal

验证相邻层间的语义一致性，确保需求意图在传递过程中不发生偏差
# User Value

识别需求漂移、理解偏差等问题，确保上层需求的业务意图在向下分解过程中得到准确传达
# Inputs

- 需求链节点文本内容（父节点和子节点）
- 语义相似度模型配置（BERT/SimCSE模型路径或API端点）
- 语义阈值配置（默认90%，支持分层级配置）
- 关键词白名单/黑名单配置
# Processing

- 提取父节点和子节点的文本内容
- 使用预训练模型提取语义向量
- 计算余弦相似度并映射评分
- 提取并验证核心关键词覆盖
- 检测语义偏差并分类（关键词缺失/概念偏移/范围膨胀）
# Outputs

- 语义相似度评分矩阵
- 语义偏差节点对清单
- 偏差类型分类及分析建议
- Semantic Alignment指标统计
# Acceptance

- 支持父节点与直接子节点的文本相似度计算
- 使用预训练语言模型提取语义向量
- 计算余弦相似度并映射到0-100分范围
- Semantic Alignment ≥ 90%
- 提取父节点核心关键词并验证子节点覆盖
# Acceptance Checks

## AC-004-001

- Scenario: 语义相似度计算
- Given: 父节点和子节点描述相似的业务目标
- When: 执行语义计算
- Then: 输出相似度评分≥90分，判定为一致
- Trace Hints: TECH, TESTSET

## AC-004-002

- Scenario: 语义漂移检测
- Given: EPIC描述与FEAT实现方向存在偏差
- When: 执行语义验证
- Then: 报告语义偏差，标记为需关注
- Trace Hints: TECH, UI, TESTSET

## AC-004-003

- Scenario: 关键词覆盖验证
- Given: 父节点核心关键词为"性能优化"
- When: 检查子节点关键词覆盖
- Then: 验证子节点包含"性能"相关关键词
- Trace Hints: TECH, TESTSET

## AC-004-004

- Scenario: 分层级阈值配置
- Given: SRC→EPIC阈值90%，FEAT→TASK阈值85%
- When: 执行分层语义验证
- Then: 按对应阈值判定各层一致性
- Trace Hints: TECH, UI
# Dependencies

- EPIC-030
- FEAT-159
- FEAT-161
# Non Goals

- 不做业务逻辑正确性判断（仅检测语义一致性）
- 不自动修改需求文本内容
- 不涉及代码实现的语义验证
