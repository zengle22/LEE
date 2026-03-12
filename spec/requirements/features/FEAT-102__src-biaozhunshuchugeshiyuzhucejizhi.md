---
id: FEAT-102
ssot_type: feat
title: SRC 标准输出格式与注册机制
status: frozen
version: v1
parent_id: EPIC-008
derived_from_ids: []
source_refs:
- EPIC-008#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T13:50:05.866561'
---

# Goal

定义 SRC 标准格式规范（v1.0），实现 SRC 注册器支持独立存储、验证和版本追踪
# User Value

SRC 产物可独立存储、review 和版本控制，支持 replay 和审计追踪
# Inputs

- 原始需求处理结果
- 输出路径配置
- 版本追踪选项
# Processing

- 应用 SRC v1 格式规范生成文档
- 验证字段完整性（id, ssot_type, title, content, source_refs）
- 生成标准化文件名（{id}__{slug}.md）
- 写入指定存储路径
- 记录版本历史
# Outputs

- 符合 v1 规范的 SRC 文档文件
- 验证报告
- 版本历史记录
# Acceptance

- SRC 格式规范文档（v1.0）正式发布，包含完整字段定义和验证规则
- SRC 注册器实现：支持将 SRC 写入指定存储路径，文件名遵循 {id}__{slug}.md 规范
- SRC 可独立加载和验证，验证 API 提供明确的错误信息（字段缺失/格式错误/引用无效）
- SRC 产物不携带任何 EPIC 语义字段（如 scope, success_criteria 等）
- 支持 SRC 版本历史查询（基于文件系统或轻量级版本追踪）
# Acceptance Checks

## AC-008-003-01

- Scenario: SRC 格式规范发布
- Given: 格式规范文档已完成编写
- When: 文档经过 review 并发布
- Then: SRC v1.0 规范正式发布，包含完整字段定义和验证规则
- Trace Hints: TASK, TECH

## AC-008-003-02

- Scenario: SRC 注册器写入功能
- Given: 提供有效的 SRC 数据和输出路径配置
- When: 调用 SRC 注册器写入方法
- Then: 文件以 {id}__{slug}.md 命名写入指定路径，格式符合 v1 规范
- Trace Hints: TASK, TESTSET, TECH

## AC-008-003-03

- Scenario: SRC 独立验证
- Given: 提供待验证的 SRC 文档
- When: 调用验证 API
- Then: 返回明确的验证结果，包括字段缺失、格式错误、引用无效等具体问题
- Trace Hints: TASK, TESTSET, TECH

## AC-008-003-04

- Scenario: EPIC 语义字段隔离
- Given: 检查 SRC 输出文档
- When: 扫描文档字段
- Then: 确认不包含 scope、success_criteria 等 EPIC 语义字段
- Trace Hints: TESTSET, TECH

## AC-008-003-05

- Scenario: 版本历史查询
- Given: 已存在多个版本的 SRC 文件
- When: 查询版本历史
- Then: 返回按时间排序的版本列表，支持查看历史版本内容
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-008
# Non Goals

- 不实现复杂版本控制系统（如 Git 集成）
- 不实现 SRC 内容 diff 功能
- 不扩展至非 workflow-engineering 领域
