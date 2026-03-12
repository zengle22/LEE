---
id: FEAT-012-003
ssot_type: feat
title: Kimi 执行器运行时集成适配
status: frozen
version: v1
parent_id: EPIC-012
derived_from_ids: []
source_refs:
- EPIC-012#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T22:32:02.122761'
---

# Goal

将 Kimi CLI 执行器作为标准 coding executor 接入 LEE 框架，通过 canonical executor 架构实现与现有 code runner 和 workflow wiring 的集成
# User Value

Kimi CLI 执行器作为标准 coding executor 接入 LEE 框架，沿用 `claude_code` 同类执行治理方式并复用现有 workflow wiring，保证执行链路一致性，无需为 Kimi 单独维护业务 workflow
# Inputs

- 本地 `kimi-cli` 可执行文件、命令参数与环境变量约定
- 标准 code executor 接口契约定义
- 任务执行上下文（task context、workspace 等）
- 日志与追踪系统接口
# Processing

- 实现标准 code executor 接口（与 `claude_code` 同类执行器契约一致）
- 在 executor 工厂中注册 Kimi 执行器，支持别名解析
- 通过统一工厂创建执行器实例，复用实例化逻辑
- 参考 `ClaudeCodeRunner` 所在执行链路实现 Kimi 的 runner/executor 接线
- 通过本地 `kimi-cli --print` 调用完成任务执行
- 复用 workflow wiring 进行流程编排
# Outputs

- Kimi CLI 执行器实例（实现标准 code executor 接口）
- 执行器工厂注册记录
- 任务执行结果（符合 executor 接口输出规范）
- 执行日志与追踪数据
# Acceptance

- Kimi CLI 执行器实现标准 code executor 接口（与 `claude_code` 同类契约一致）
- 集成 canonical executor 架构，通过统一的 executor 工厂创建
- 运行时通过本地 `kimi-cli --print` 调用 Kimi，而不是通过 Moonshot/OpenAI 兼容 API profile
- coding 步骤复用现有 workflow wiring 进行流程编排
- 兼容现有 qwen 等执行器的别名注册模式
- 执行器输出可被现有日志和追踪系统正确捕获
# Acceptance Checks

## AC-012-003-01

- Scenario: 标准接口实现验证
- Given: 定义了标准 code executor 接口与 CLI 调用约束
- When: Kimi 执行器实现类被加载
- Then: 完整实现接口中定义的行为，并具备 `kimi-cli --print` 调用能力
- Trace Hints: TECH, TASK, TESTSET

## AC-012-003-02

- Scenario: Executor 工厂注册
- Given: executor 工厂已支持 `claude_code`、`codex` 等 code executor 注册
- When: 系统初始化时注册 Kimi 执行器
- Then: Kimi 执行器通过工厂可被正确实例化，支持别名 "kimi" 解析
- Trace Hints: TECH, TASK

## AC-012-003-03

- Scenario: Code runner 接线验证
- Given: 现有 `ClaudeCodeRunner` 已实现 code step 的任务调度与治理约束
- When: Kimi 执行器执行任务
- Then: Kimi 走与 `claude_code` 同类的 code runner/executor 轨道，不走 LangGraph/LLM profile 轨道
- Trace Hints: TECH, TASK, TESTSET

## AC-012-003-04

- Scenario: Workflow wiring 复用
- Given: 现有 coding 步骤模板使用标准 workflow wiring
- When: Kimi 执行器被选用执行 coding 任务
- Then: 复用相同 workflow wiring，步骤模板无需修改
- Trace Hints: TECH, TASK

## AC-012-003-05

- Scenario: 日志与追踪集成
- Given: 现有系统已集成日志和追踪系统
- When: Kimi 执行器执行任务并产生输出
- Then: 输出被正确捕获并记录到日志和追踪系统中
- Trace Hints: TECH, TASK, TESTSET
# Dependencies

- EPIC-012
- FEAT-012-001
- FEAT-012-002
# Non Goals

- 不修改现有业务 workflow 模板
- 不将 Kimi 作为 `llm/qwen` profile 或 Moonshot API 直连接入
- 不修改现有 coding 步骤模板
- 不要求复用 LangGraph Runner
- 不涉及执行器的性能优化
