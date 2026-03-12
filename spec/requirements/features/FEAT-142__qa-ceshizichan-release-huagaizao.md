---
id: FEAT-142
ssot_type: feat
title: QA 测试资产 release 化改造
status: frozen
version: v1
parent_id: EPIC-QA-SSOT-UPGRADE
derived_from_ids: []
source_refs:
- EPIC-QA-SSOT-UPGRADE#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T20:16:11.831948'
---

# Goal

完成 QA 测试资产（TESTSET/TESTPLAN/TASK/REPORT）与 SSOT 主链的 release 化对齐，实现需求轴、交付轴、证据轴的显式分层管理
# User Value

QA 测试资产正式纳入 SSOT 三轴模型管理，确保 TESTSET 只能由 FEAT 派生，TESTPLAN 必须挂在 RELEASE 下，为交付治理提供可信的测试资产溯源能力
# Inputs

- EPIC-QA-SSOT-UPGRADE 定义的边界约束（CR-001, CR-002, CR-006, CR-008）
- 现有 QA 测试资产清单（TESTSET/TESTPLAN/TASK/REPORT）
- SSOT 三轴模型元数据规范
- FEAT 派生 TESTSET 的约束规则
# Processing

- 分析现有 QA 测试资产与 SSOT 三轴模型的映射关系
- 定义 TESTSET 与 FEAT 的 0:N 绑定关系约束
- 定义 TESTPLAN 与 RELEASE 的绑定关系约束
- 为每个 QA 资产对象添加三轴模型元数据标注
- 建立 TESTSET 派生路径验证规则（仅允许从 FEAT 派生）
# Outputs

- 具备 SSOT 三轴模型元数据，绑定单一 FEAT
- 具备 SSOT 三轴模型元数据，挂载到 RELEASE
- 具备 SSOT 三轴模型元数据，归属 TESTPLAN
- 具备 SSOT 三轴模型元数据，归属 TASK
- 用于校验 QA 资产绑定关系的规则配置
# Acceptance

- TESTSET 必须且只能绑定单一 FEAT（0:N 关系验证通过）
- TESTPLAN 必须挂在 RELEASE 下（绑定关系验证通过）
- 需求轴、交付轴、证据轴显式分层且可独立校验
- TESTSET 派生路径验证：只能从 FEAT 派生，禁止从 EPIC 直接生成
- 所有 QA 测试资产对象具备 SSOT 三轴模型的完整元数据
# Acceptance Checks

## AC-001-001

- Scenario: TESTSET 绑定单一 FEAT 验证
- Given: 存在一个已创建的 TESTSET 对象
- When: 执行 SSOT 绑定关系校验
- Then: TESTSET.ssot_binding.feat_ref 存在且指向单一有效 FEAT
- Trace Hints: TECH, TASK, TESTSET

## AC-001-002

- Scenario: TESTPLAN 挂载到 RELEASE 验证
- Given: 存在一个已创建的 TESTPLAN 对象
- When: 执行 SSOT 绑定关系校验
- Then: TESTPLAN.ssot_binding.release_ref 存在且指向有效 RELEASE
- Trace Hints: TECH, TASK, TESTSET

## AC-001-003

- Scenario: 三轴模型分层验证
- Given: 存在 QA 测试资产对象集合
- When: 执行三轴模型元数据校验
- Then: 每个对象的 axis_tag 在 [requirement, delivery, evidence] 中，且分层清晰
- Trace Hints: TECH, TASK

## AC-001-004

- Scenario: TESTSET 派生路径阻断验证
- Given: 尝试从 EPIC 直接派生 TESTSET
- When: 执行派生路径校验
- Then: 系统拒绝该操作并返回约束违反错误
- Trace Hints: TECH, TASK, TESTSET

## AC-001-005

- Scenario: QA 资产 SSOT 元数据完整性验证
- Given: 存在改造后的 QA 测试资产对象
- When: 执行元数据完整性校验
- Then: 所有对象包含 ssot_id、axis_tag、binding_refs、version、status 字段
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-QA-SSOT-UPGRADE
# Non Goals

- 不修改现有 EPIC 级别的粒度
- 不创建独立于 SSOT 的 QA 专用链
- 具体数据库设计和 API 实现在 tech_design 阶段处理
- 不修改 BUG 本身的处理流程
- 不创建新的证据存储系统
