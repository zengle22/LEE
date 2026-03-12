---
id: SRC-012
ssot_type: src
title: Kimi Executor 接入与配置能力
status: frozen
version: v1
parent_id: null
derived_from_ids:
- ADR-014
source_refs:
- ADR-014
owner: null
tags:
- kimi
- executor
- raw-to-src
- cli
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-12T17:38:43.889524'
---

# Goal

在 LEE 工作流执行框架内，建立 Kimi 执行器的标准接入与配置能力，使其成为可显式选择、可配置为默认、可追溯、可复用的执行能力选项，支撑中文场景下的需求分析与代码执行任务，同时严格遵循现有架构复用原则。

# User Value

- 为 CLI 使用者提供显式指定 Kimi 执行器的能力（`--executor kimi`）。
- 为编码任务执行者提供可配置化的默认执行器切换能力。
- 为系统维护者提供零侵入复用现有工作流的执行器扩展方式。

# Inputs

- 原始需求：ADR-014 接入 Kimi 执行器原始需求说明
- 工作流实例中的 `executor` / `llm_profile` 配置
- 现有 LEE 执行器工厂、Runner、CLI 与 workflow wiring

# Processing

- 识别"Kimi 执行器接入"属于能力扩展型需求，并归类到 SRC 层级
- 约束接入方案必须复用现有 canonical executor 架构
- 明确 CLI 支持 `--executor kimi` 命令入口
- 定义配置支持切换默认 coding executor 的能力
- 确保现有业务 workflow 模板零变更复用

# Outputs

- 可显式选择的 Kimi 执行能力（`--executor kimi`）
- 可配置化的默认执行器切换能力
- 标准化的配置入口与运行约束
- 可供后续 `src_to_epic` 使用的正式 SRC 文档

# Acceptance

- CLI 支持 `--executor kimi` 命令且正确路由
- 配置支持切换默认 coding executor 且生效
- 不创建平行 workflow 或平行执行链
- 现有 coding 步骤模板无需修改
- raw-to-src 仅产出 SRC，不越界产出 EPIC / FEAT / TASK
- 文档明确接入点、配置点、验收边界和非目标

# Constraints

- 必须复用现有 canonical executor 架构（C-ARCH-01）
- 必须复用现有 Runner 与 workflow wiring
- 不创建平行 workflow（C-ARCH-02）
- 兼容现有 `qwen` 等别名模式（C-ARCH-03）
- 必须保留来源追溯性
- 本阶段不替换 Claude Code / Codex 存量实现
- 本阶段不包含生产发布、灰度或运维策略设计

# Non Goals

- 不在本阶段完成 `src_to_epic`、`epic_to_feat`、`feat_to_delivery_prep`
- 不在本阶段设计发布编排、监控、灰度与告警方案
- 不在本阶段重构其他执行器的历史实现
- 不新增业务 workflow 模板

# Core Objectives

| 目标 | 类型 | 价值驱动 | 成功标志 |
|------|------|----------|----------|
| 执行器能力补齐 | 能力扩展 | 消除用户选择受限痛点 | `kimi` 被系统识别和路由 |
| 配置化默认执行器切换 | 体验优化 | 降低用户切换成本 | 配置修改后自动使用 Kimi |
| 现有工作流零侵入复用 | 兼容性保证 | 保护现有投资 | 不新增平行工作流 |

# Business Drivers

| 优先级 | 驱动因素 | 当前痛点 | 预期价值 |
|--------|----------|----------|----------|
| P0 | 用户选择权受限 | 无法显式选择 Kimi 作为执行器；默认执行器硬编码，切换困难 | 用户可自由选择执行器 |
| P1 | 执行器心智模型统一 | 架构能力与用户认知存在割裂 | 封装内部实现细节，降低使用门槛 |
| P2 | 架构一致性维护 | 避免为 Kimi 新建独立链路导致架构漂移 | 复用现有 canonical executor 治理方式 |

# Target Users

| 用户角色 | 核心诉求 | 关键场景 | 验收标准 |
|---------|---------|---------|---------|
| CLI 使用者 | 显式指定执行器 | `lee run <wf> --executor kimi` | 命令行参数正确解析路由 |
| 编码任务执行者 | 使用 Kimi 完成代码实现 | 任何 coding step 执行时 | 输出格式兼容现有 executor |
| 系统维护者 | 复用现有架构 | 新增/修改 executor 配置时 | 无新增平行链路，路由逻辑一致 |

# Traceability

- Source workflow: `wf_task_546b61c2`
- Source step: `source_normalization`
- Source artifact: ADR-014
- Normalized at: 2026-03-12
