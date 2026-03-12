---
id: FEAT-012-001
ssot_type: feat
title: CLI 显式选择执行器能力
status: frozen
version: v1
parent_id: EPIC-012
derived_from_ids: []
source_refs:
- EPIC-012#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T22:32:02.102833'
---

# Goal

实现 CLI 命令行参数 `--executor <name>` 的解析与路由能力，使用户能够显式指定使用 Kimi 或其他执行器
# User Value

用户可以通过命令行参数显式指定使用 Kimi 或其他执行器，获得灵活的执行器切换能力，无需修改配置文件即可临时切换执行器
# Inputs

- CLI 命令行参数 `--executor <name>`
- 可用执行器名称列表（kimi, qwen, claude 等）
- 默认执行器配置值（作为降级备选）
# Processing

- 解析 CLI 命令行参数，提取 `--executor` 值
- 校验执行器名称有效性（在已注册执行器列表中查找）
- 确定最终执行器选择（CLI 参数 > 默认配置 > 系统预设）
- 将执行器标识传递至 executor router 层
- 触发执行器实例化流程
# Outputs

- 解析后的执行器选择标识（executor_key）
- 执行器路由决策结果
- 无效参数错误提示（当校验失败时）
# Acceptance

- CLI 命令行解析器支持 `--executor <name>` 参数（含 kimi、qwen 等有效值）
- 参数值被正确传递至执行器路由层
- 显式指定的执行器优先级高于默认配置
- 无效执行器名称返回清晰的错误提示
- 执行器输出格式符合现有 executor 接口规范
# Acceptance Checks

## AC-012-001-01

- Scenario: CLI 参数解析与传递
- Given: 用户在命令行输入 `--executor kimi`
- When: CLI 启动并解析参数
- Then: 参数值 "kimi" 被正确解析并传递至执行器路由层
- Trace Hints: TECH, TASK

## AC-012-001-02

- Scenario: 执行器优先级规则
- Given: 配置文件默认执行器为 qwen，CLI 显式指定为 kimi
- When: 执行器选择逻辑执行
- Then: 最终选用 kimi 执行器（CLI 参数优先级更高）
- Trace Hints: TECH, TASK, TESTSET

## AC-012-001-03

- Scenario: 无效执行器错误处理
- Given: 用户输入 `--executor invalid_executor`
- When: 参数校验执行
- Then: 返回错误提示，列出可用执行器列表
- Trace Hints: UI, TECH, TASK

## AC-012-001-04

- Scenario: 与现有执行器实现一致性
- Given: qwen 执行器已实现 CLI 选择能力
- When: kimi 执行器接入 CLI 选择
- Then: 复用相同的路由逻辑，无代码重复或平行链路
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-012
# Non Goals

- 不修改现有 workflow 模板
- 不实现执行器本身的业务逻辑
- 不处理配置持久化
