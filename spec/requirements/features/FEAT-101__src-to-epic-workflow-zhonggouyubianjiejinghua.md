---
id: FEAT-101
ssot_type: feat
title: Src-to-Epic Workflow 重构与边界净化
status: frozen
version: v1
parent_id: EPIC-008
derived_from_ids: []
source_refs:
- EPIC-008#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T13:50:05.860494'
---

# Goal

重构 src-to-epic workflow，移除 raw input 适配逻辑，使其仅接受 SRC 格式输入，提升代码可维护性
# User Value

EPIC 生成流程专注于已标准化需求，移除 raw input 适配逻辑，提升代码可维护性
# Inputs

- SRC 格式文档（符合 v1 规范）
- EPIC 生成配置参数
- 可选的模板覆盖选项
# Processing

- 验证输入为 SRC 格式（拒绝 raw 格式）
- 解析 SRC 字段并映射到 EPIC 结构
- 执行 EPIC 生成逻辑
- 验证输出 EPIC 格式
- 错误分类与报告
# Outputs

- 标准化 EPIC 文档
- 处理日志与错误信息
- 向后兼容性报告
# Acceptance

- src-to-epic workflow 仅接受 SRC 格式输入，拒绝 raw 格式输入并返回明确错误
- 移除所有 raw-to-src 转换相关代码，代码行数减少 >= 20%
- 现有 EPIC 生成逻辑 100% 向后兼容，已有测试用例全部通过
- 输入 SRC 与输出 EPIC 的映射关系文档化
- 故障时可明确区分 "输入格式错误" 与 "EPIC 生成逻辑错误"
# Acceptance Checks

## AC-008-002-01

- Scenario: SRC 格式输入验证
- Given: src-to-epic workflow 正在运行
- When: 传入 SRC 格式文档作为输入
- Then: 文档被接受并正常处理，返回 EPIC 格式输出
- Trace Hints: TASK, TESTSET, TECH

## AC-008-002-02

- Scenario: Raw 格式输入拒绝
- Given: src-to-epic workflow 正在运行
- When: 传入 raw 格式文档作为输入
- Then: 系统拒绝处理并返回明确的 "输入格式错误" 信息
- Trace Hints: TASK, TESTSET, TECH

## AC-008-002-03

- Scenario: 代码精简验证
- Given: 获取重构前后的代码统计
- When: 对比 raw-to-src 相关代码行数
- Then: 相关代码行数减少 >= 20%
- Trace Hints: TASK, TECH

## AC-008-002-04

- Scenario: 向后兼容性验证
- Given: 运行现有测试套件
- When: 执行所有 src-to-epic 相关测试用例
- Then: 所有测试用例 100% 通过，无回归
- Trace Hints: TESTSET, TECH

## AC-008-002-05

- Scenario: 错误分类机制
- Given: workflow 执行过程中发生错误
- When: 错误信息被捕获和报告
- Then: 可明确区分输入格式错误与 EPIC 生成逻辑错误
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-008
- FEAT-008-001
- FEAT-008-003
# Non Goals

- 不改变 EPIC -> FEAT -> TASK 的下游流程
- 不引入新的 workflow 编排引擎
- 不修改现有数据存储 schema
