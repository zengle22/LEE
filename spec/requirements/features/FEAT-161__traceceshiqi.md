---
id: FEAT-161
ssot_type: feat
title: Trace测试器
status: frozen
version: v1
parent_id: EPIC-030
derived_from_ids: []
source_refs:
- EPIC-030#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.717776'
---

# Goal

验证需求链的纵向追溯完整性，确保SRC→EPIC→FEAT→TASK的链接无断裂
# User Value

确保从原始需求到执行单元的链路完整性，支持快速定位需求缺失环节，满足审计和合规要求
# Inputs

- 完整需求链图谱（四层节点及关联关系）
- 节点父子关系映射表
- 节点来源引用清单（source_refs、derived_from_ids）
- 覆盖率计算配置（各层覆盖率阈值）
# Processing

- 构建需求链图谱，建立节点间关联
- 执行纵向链路追溯，验证四层完整性
- 检测孤儿节点、断链节点、循环引用
- 计算各层覆盖率指标
- 评估链路质量（过度拆分/拆分不足）
# Outputs

- 追溯矩阵（Traceability Matrix）
- 覆盖率统计报告（EPIC层、FEAT层覆盖率）
- 断链节点清单及修复建议
- 链路质量评估报告
# Acceptance

- 验证SRC→EPIC→FEAT→TASK四层链路的完整性
- 检测孤儿节点（无父节点且无有效来源引用）
- 检测断链节点（parent_id存在但父节点缺失）
- 检测循环引用（节点形成闭环依赖）
- 计算并输出各层节点的覆盖率指标
# Acceptance Checks

## AC-003-001

- Scenario: 完整链路追溯验证
- Given: 存在从SRC到TASK的完整需求链
- When: 执行Trace测试器
- Then: 验证链路完整性，覆盖率计算正确
- Trace Hints: TECH, TESTSET

## AC-003-002

- Scenario: 孤儿节点检测
- Given: 存在无parent_id且无source_refs的孤立节点
- When: 执行孤儿节点检测
- Then: 报告孤儿节点清单，标记为需处理
- Trace Hints: TECH, UI, TESTSET

## AC-003-003

- Scenario: 循环引用检测
- Given: FEAT-A的parent指向FEAT-B，FEAT-B的parent指向FEAT-A
- When: 执行循环检测算法
- Then: 报告循环引用位置，提供打破建议
- Trace Hints: TECH, TASK, TESTSET

## AC-003-004

- Scenario: 覆盖率计算
- Given: 100个EPIC中有95个关联至少一个FEAT
- When: 计算EPIC层覆盖率
- Then: 输出覆盖率为95%，满足≥95%阈值
- Trace Hints: TECH, UI, TESTSET
# Dependencies

- EPIC-030
- FEAT-159
- FEAT-160
# Non Goals

- 不验证链路节点的语义一致性（由Semantic测试器处理）
- 不自动创建缺失的链路节点
- 不执行具体TASK内容验证
