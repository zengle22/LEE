---
id: FEAT-105
ssot_type: feat
title: 分层架构部署配置
status: frozen
version: v1
parent_id: EPIC-008
derived_from_ids: []
source_refs:
- EPIC-008#scope
owner: null
tags: []
properties:
  contract_key: feat_006
  identity_kind: ssot
frozen_at: '2026-03-12T13:50:05.884514'
---

# Goal

提供 raw-to-src 和 src-to-epic 的独立运行配置，支持独立启动、回滚和故障隔离
# User Value

支持 raw-to-src 和 src-to-epic 的独立运行和回滚，故障隔离能力增强
# Inputs

- workflow 运行配置模板
- readiness 健康检查规范
- 运行环境要求
# Processing

- 创建 raw-to-src 独立运行配置
- 创建 src-to-epic 独立运行配置
- 实现层特定的 readiness 健康检查
- 编写运行配置文档
- 验证故障隔离能力
# Outputs

- raw-to-src 运行配置
- src-to-epic 运行配置
- readiness 健康检查实现
- 运行配置文档
- 故障隔离验证报告
# Acceptance

- 提供 raw-to-src 独立运行配置（CLI / script / 或等效配置）
- 提供 src-to-epic 独立运行配置，可独立启动不依赖 raw-to-src 运行时
- 健康检查豁免 HTTP `/health` 服务形态，改为每个 layer 提供可调用的 readiness probe，返回层特定健康状态
- 配置文档：说明独立运行、联合运行、回滚流程
- 验证：模拟 raw-to-src 故障，src-to-epic 仍可正常处理已存在的 SRC 文件
# Acceptance Checks

## AC-008-006-01

- Scenario: Raw-to-src 独立运行
- Given: 提供 workflow 运行环境
- When: 应用 raw-to-src 运行配置
- Then: workflow 成功启动并可独立运行
- Trace Hints: TASK, TECH

## AC-008-006-02

- Scenario: Src-to-epic 独立运行
- Given: 提供 workflow 运行环境
- When: 应用 src-to-epic 运行配置
- Then: workflow 成功启动，不依赖 raw-to-src 运行时
- Trace Hints: TASK, TESTSET, TECH

## AC-008-006-03

- Scenario: 健康检查探针
- Given: 各 layer 运行配置已就绪
- When: 调用 layer readiness probe
- Then: 返回层特定的健康状态信息
- Trace Hints: TASK, TESTSET, TECH

## AC-008-006-04

- Scenario: 运行配置文档
- Given: 查看运行文档
- When: 阅读配置说明
- Then: 包含独立运行、联合运行、回滚流程的完整说明
- Trace Hints: TECH

## AC-008-006-05

- Scenario: 故障隔离验证
- Given: raw-to-src 服务发生故障
- When: src-to-epic 处理已存在的 SRC 文件
- Then: 可正常处理，不受 raw-to-src 故障影响
- Trace Hints: TESTSET, TECH
# Dependencies

- EPIC-008
- FEAT-008-001
- FEAT-008-002
# Non Goals

- 不实现 HTTP 后端服务形态的 `/health`
- 不实现自动扩缩容
- 不实现复杂的蓝绿/金丝雀发布策略
- 不修改现有数据存储 schema（仅配置层面变更）
