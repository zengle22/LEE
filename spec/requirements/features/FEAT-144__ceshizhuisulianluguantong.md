---
id: FEAT-144
ssot_type: feat
title: 测试追溯链路贯通
status: frozen
version: v1
parent_id: EPIC-QA-SSOT-UPGRADE
derived_from_ids: []
source_refs:
- EPIC-QA-SSOT-UPGRADE#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T20:16:11.850824'
---

# Goal

实现 BUG/REPORT/EVI 到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT 的完整双向追溯，区分运行事实与判定结论
# User Value

支持从任意 QA 资产（BUG/REPORT/EVI）快速反查完整的 SSOT 上下文链路，区分运行事实（TSE/runner output/logs/screenshots）与判定结论（REPORT），确保 Release Gate 决策有据可依
# Inputs

- FEAT-QA-SSOT-001 输出的改造后 QA 资产对象
- FEAT-QA-SSOT-003 输出的规范执行入口
- EPIC-QA-SSOT-UPGRADE 定义的追溯约束（CR-005）
- 现有 BUG/REPORT/EVI 数据
- 运行事实数据（TSE, runner output, logs, screenshots）
# Processing

- 建立 BUG 到 SSOT 链路的反向索引（BUG -> TASK -> TESTPLAN -> RELEASE）
- 建立 REPORT 到 SSOT 链路的反向索引
- 建立 EVI 到 SSOT 链路的反向索引
- 实现双向追溯查询接口（正向：FEAT -> TESTSET -> TASK -> REPORT/EVI；反向：BUG/EVI -> TASK -> ...）
- 定义运行事实与判定结论的边界区分规则
# Outputs

- BUG 到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT 的完整反向索引
- REPORT 到 SSOT 链路的完整反向索引
- EVI 到 SSOT 链路的完整反向索引
- 支持正向和反向的追溯查询 API，响应时间 < 500ms
- 区分运行事实（fact）与判定结论（conclusion）的类型系统
# Acceptance

- BUG 必须可反查到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT（追溯链路完整性验证）
- REPORT 必须可反查到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT
- EVI 必须可反查到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT
- 运行事实（TSE/runner output/logs/screenshots）与判定结论（REPORT）的边界清晰可区分
- 追溯查询接口在 500ms 内返回完整链路
# Acceptance Checks

## AC-002-001

- Scenario: BUG 追溯链路完整性验证
- Given: 存在一个已记录的 BUG
- When: 执行反向追溯查询
- Then: 返回的链路包含 release_ref、testplan_ref、task_ref、testset_ref、feat_ref
- Trace Hints: TECH, TASK, TESTSET

## AC-002-002

- Scenario: REPORT 追溯链路完整性验证
- Given: 存在一个已生成的 REPORT
- When: 执行反向追溯查询
- Then: 返回的链路包含完整的 SSOT 上下文引用
- Trace Hints: TECH, TASK, TESTSET

## AC-002-003

- Scenario: EVI 追溯链路完整性验证
- Given: 存在一个已记录的 EVI
- When: 执行反向追溯查询
- Then: 返回的链路包含完整的 SSOT 上下文引用
- Trace Hints: TECH, TASK, TESTSET

## AC-002-004

- Scenario: 事实与判定边界区分验证
- Given: 存在运行事实数据（logs/screenshots）和判定结论（REPORT）
- When: 执行类型标签校验
- Then: 运行事实的 type=fact，REPORT 的 type=conclusion，且 fact 不能替代 conclusion
- Trace Hints: TECH, TASK

## AC-002-005

- Scenario: 追溯查询性能验证
- Given: 系统已建立完整的追溯索引
- When: 执行追溯查询接口请求
- Then: 响应时间在 500ms 以内返回完整链路
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-QA-SSOT-UPGRADE
- FEAT-QA-SSOT-001
- FEAT-QA-SSOT-003
# Non Goals

- 不修改 BUG 本身的处理流程
- 不创建新的证据存储系统
- ADR 作为治理约束输入，不直接替代业务主链对象
- 不修改现有的测试执行引擎
- 不改变测试用例的设计方式
