---
id: SRC-011
ssot_type: src
title: LEE Qwen 执行器接入契约
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- ART-00398
owner: null
tags:
- qwen
- executor
- raw-to-src
properties: {}
frozen_at: '2026-03-12T20:45:07.520959'
---

# Goal

在 LEE 工作流执行框架内，建立 `qwen cli` 执行器的标准接入契约，使其成为与 `claude_code`、`codex` 等并列的通用可选执行器组件，可通过统一配置进入现有 workflow / runner / executor factory 体系，并在文档生成、结构化评审、实现辅助和中文任务处理等场景中复用。

# User Value

- 为工作流使用者提供一个可配置切换的通用执行器选项，而不是额外维护一条专用执行链。
- 为文档、评审、实现辅助和中文任务处理场景提供更合适的执行能力。
- 为研发团队保留统一的执行结果、追溯、审计和 SSOT 物化语义。

# Inputs

- 工作流任务目标、结构化上下文和显式执行器选择配置
- 工作流实例中的执行器选择配置
- 现有 LEE 执行器工厂、Runner、CLI 与 workflow wiring

# Processing

- 约束接入方案必须复用现有执行器工厂与 Runner 路径
- 明确 CLI / workflow instance / 配置文件中的 `qwen cli` 选择入口
- 定义 `qwen cli` 的无头调用契约、输入输出契约、配置映射与验收边界
- 明确 `qwen cli` 与 `claude_code`、`codex` 等执行器并存，而非替换关系
- 明确 `qwen cli` 不是仅面向 `raw-to-src`、`epic-to-feat` 或 SSOT 生成的专用执行器，而是可被多个通用 workflow 复用

# Outputs

- 可显式选择的 `qwen cli` 执行器组件
- 标准化的配置入口与运行约束
- 与现有执行器一致的执行结果、追溯与物化语义

# Acceptance

- 能在 LEE 中以显式配置方式选择 `qwen cli`
- `qwen cli` 作为可选执行器组件与 `claude_code` 并存
- 能通过配置在多个执行器之间切换，而不是修改 workflow 结构
- `qwen cli` 具备可自动化调用的无头模式，不依赖交互式终端会话
- `qwen cli` 可被通用 workflow 复用，而不是只服务于 EPIC / FEAT / SRC 等 SSOT 文档生成
- 不创建平行 workflow 或平行执行链
- 文档明确接入点、配置点、验收边界和非目标

# Constraints

- 必须复用现有执行器工厂、Runner 与 workflow wiring
- 必须保留来源追溯性
- 本阶段不替换或废弃 `claude_code` / `codex` 存量实现
- 本阶段不包含生产发布、灰度或运维策略设计

# Non Goals

- 不在本阶段要求所有历史 workflow 都强制切换到 `qwen`
- 不在本阶段设计发布编排、监控、灰度与告警方案
- 不在本阶段移除或替换其他执行器的历史实现

# Traceability

- Source workflow: `wf_task_702aa3a8`
- Source step: `source_normalization`
- Source artifact: `ART-00398`
- Raw requirement file: `tmp_qwen_raw_requirement.md`

