---
id: FEAT-100
ssot_type: feat
title: Raw-to-Src Workflow 独立入口实现
status: frozen
version: v1
workflow_instance_id: feat-100-raw-to-src-impl
parent_id: EPIC-008
derived_from_ids: []
source_refs:
- EPIC-008#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T13:50:05.854373'
---

# Goal

实现 raw-to-src workflow 作为独立的 CLI 入口，支持原始需求文档的独立归一化处理，无需触发完整流水线
# User Value

原始需求可独立进行归一化处理，无需触发完整流水线，提升处理效率和灵活性
# Inputs

- 原始需求文档（markdown/text 格式）
- 可选的配置参数（输出路径、格式选项）
- 来源引用信息（source_refs）
# Processing

- 解析原始需求文档结构
- 提取标题、内容、来源引用等关键字段
- 应用归一化规则转换为标准格式
- 生成与原始输入同题的单一 canonical SRC 输出
- 检测多主题输入并显式返回“需要先拆分原始输入”，而不是自动产出多个 SRC
- 验证输出字段完整性
# Outputs

- 标准化 SRC 文档（符合 v1 规范）
- 处理日志与错误信息
- 执行报告（耗时、状态）
# Acceptance

- raw-to-src workflow 可作为独立 CLI 命令执行，不依赖 src-to-epic 或其他下游流程
- 输入单一主题的原始需求文档（markdown/text），输出 1 份标准化 SRC 文档
- 输出 SRC 与原始输入保持同题，不得将 intake / schema / workflow 方法论漂移为正式 SRC 主题
- 当输入包含多个独立问题域时，流程显式返回“需要先拆分原始输入”，不自动扇出多个 SRC
- 单元测试覆盖率 >= 80%，可在隔离环境中运行（mock 外部依赖）
- SRC 输出格式符合 v1 规范（id, ssot_type, title, content, source_refs 字段完整）
- 执行时间 < 30s（单文档处理）
# Acceptance Checks

## AC-008-001-01

- Scenario: 独立 CLI 执行能力
- Given: 系统已安装 workflow CLI 工具
- When: 用户执行 raw-to-src 命令并传入原始需求文档
- Then: 命令成功执行并返回 SRC 格式输出，无需启动 src-to-epic 或其他下游服务
- Trace Hints: TASK, TESTSET, TECH

## AC-008-001-02

- Scenario: 输入输出格式验证
- Given: 提供有效且单一主题的 markdown 格式原始需求文档
- When: 执行 raw-to-src 转换
- Then: 输出恰好 1 份包含完整字段（id, ssot_type, title, content, source_refs）的 SRC 文档，且主题与原始输入一致
- Trace Hints: TASK, TESTSET, TECH

## AC-008-001-05

- Scenario: 多主题输入不自动拆分
- Given: 提供一份同时包含两个彼此独立问题域的原始需求文档
- When: 执行 raw-to-src 转换
- Then: 流程返回“需要先拆分原始输入”或等价阻塞信号，不生成多个 SRC 文件
- Trace Hints: TASK, TESTSET, TECH

## AC-008-001-03

- Scenario: 单元测试覆盖率
- Given: 代码仓库包含 raw-to-src 模块
- When: 运行单元测试并生成覆盖率报告
- Then: 覆盖率报告显示该模块测试覆盖率 >= 80%
- Trace Hints: TESTSET, TECH

## AC-008-001-04

- Scenario: 执行性能要求
- Given: 提供单份标准大小的原始需求文档（<100KB）
- When: 执行 raw-to-src 转换
- Then: 总执行时间 < 30s
- Trace Hints: TESTSET, TECH
# Dependencies

- EPIC-008
# Non Goals

- 不处理 SRC 到 EPIC 的转换
- 不实现分布式/并发处理
- 不修改现有 EPIC/FEAT 生成逻辑
