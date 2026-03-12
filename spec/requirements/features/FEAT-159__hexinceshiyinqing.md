---
id: FEAT-159
ssot_type: feat
title: 核心测试引擎
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.698893'
---

# Goal

为需求链测试体系提供可扩展、高性能的基础执行引擎，通过智能采样降低测试成本，通过缓存机制加速重复执行，通过增量测试支持高效回归验证
# User Value

确保测试体系在大规模需求链场景下的可持续运行，降低测试执行成本，提升测试反馈速度
# Inputs

- 需求链数据集合（SRC/EPIC/FEAT/TASK节点）
- 测试器配置清单（启用的测试器列表及参数）
- 采样策略配置（采样率、采样维度、随机种子）
- 缓存配置（缓存层级、TTL、存储路径）
- 增量基准版本（可选，用于增量测试对比）
# Processing

- 接收并解析需求链数据和测试配置
- 执行采样控制，按配置策略筛选待测节点
- 检查缓存，复用未变更节点的历史结果
- 执行增量检测，识别变更节点及影响范围
- 并发调度测试器执行测试任务
# Outputs

- 测试执行报告（原始结果数据）
- 缓存状态更新记录
- 性能统计指标（执行时间、缓存命中率、并发度）
- 测试器执行日志
# Acceptance

- 采样控制模块支持按需求链ID、层级、时间范围配置采样策略
- 实现分层采样算法（随机采样/重要性采样/分层采样）
- 采样率可配置范围10%-100%，默认采样率可针对不同层级独立设置
- 采样结果可重现，相同种子产生相同采样集合
- 支持测试结果的多级缓存（内存缓存/文件缓存）
# Acceptance Checks

## AC-001-001

- Scenario: 采样策略配置与执行
- Given: 需求链数据集已加载，采样策略配置完成
- When: 执行采样控制模块
- Then: 返回符合策略的采样集合，相同种子产生一致结果
- Trace Hints: TECH, TASK, TESTSET

## AC-001-002

- Scenario: 缓存机制生效
- Given: 相同需求链节点已存在缓存结果
- When: 再次执行相同测试
- Then: 直接返回缓存结果，不重复执行测试逻辑
- Trace Hints: TECH, TESTSET

## AC-001-003

- Scenario: 增量测试触发
- Given: 基准版本与当前版本存在差异
- When: 执行增量测试
- Then: 仅对变更节点及其影响范围执行测试
- Trace Hints: TECH, TASK

## AC-001-004

- Scenario: 测试器动态注册
- Given: 新测试器实现符合注册接口
- When: 调用测试器注册接口
- Then: 新测试器成功挂载并可被调度执行
- Trace Hints: TECH, UI
# Dependencies

- EPIC-030
# Non Goals

- 不实现具体测试逻辑（由各测试器FEAT实现）
- 不直接生成最终报告（由报告生成器FEAT实现）
- 不维护测试样本数据（由黄金样本集FEAT维护）
- 不提供告警通知功能
