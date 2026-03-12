---
id: FEAT-166
ssot_type: feat
title: 统一报告格式生成器
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_008
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.764056'
---

# Goal

实现report.json结构化报告与scorecard.md评分卡标准化输出
# User Value

支持自动化集成和人工阅读，支持历史趋势追踪和跨项目对比
# Inputs

- 各测试器原始结果数据
- 报告模板配置
- 历史报告数据（可选，用于趋势对比）
- 输出格式配置（JSON/Markdown/两者）
# Processing

- 收集各测试器结果数据
- 计算汇总统计指标
- 生成report.json结构化报告
- 生成scorecard.md评分卡
- 执行历史对比分析（如配置）
# Outputs

- report.json结构化报告
- scorecard.md评分卡
- 质量雷达图数据
- 历史对比结果
# Acceptance

- 生成符合Schema的report.json，包含元数据、汇总结果、详细结果、问题列表
- 生成Markdown格式的scorecard.md，包含执行摘要、质量雷达图、问题详情
- 支持输出路径自定义
- 支持同时生成多种格式
- 支持报告内容筛选
# Acceptance Checks

## AC-008-001

- Scenario: JSON报告生成
- Given: 各测试器结果数据已收集
- When: 执行report.json生成
- Then: 输出符合Schema的结构化报告
- Trace Hints: TECH, TESTSET

## AC-008-002

- Scenario: Markdown评分卡生成
- Given: 测试执行完成，结果数据可用
- When: 执行scorecard.md生成
- Then: 输出包含雷达图、问题列表的评分卡
- Trace Hints: TECH, UI, TESTSET

## AC-008-003

- Scenario: 历史对比功能
- Given: 存在历史报告数据
- When: 生成当前报告
- Then: 包含与历史指标的对比分析
- Trace Hints: TECH, UI

## AC-008-004

- Scenario: 报告生成性能
- Given: 大容量测试结果（1000+条记录）
- When: 执行报告生成
- Then: 生成时间≤30秒，结果正确
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-030
- FEAT-159
# Non Goals

- 不直接执行测试（仅处理测试结果）
- 不提供实时通知功能
- 不做报告的长期存储（由外部系统处理）
