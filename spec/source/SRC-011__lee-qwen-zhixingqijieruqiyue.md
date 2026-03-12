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

在 LEE 工作流执行框架内，建立 `qwen cli` 执行器的标准接入契约，使其成为可显式配置、可追溯、可复用的可选执行器组件，支撑中文场景下的需求归一化与分析任务，同时严格遵循现有架构复用原则，并与 `claude_code`、`codex` 等现有执行器并存。

# User Value

- 为产品分析师提供更适合中文需求归一化的执行能力。
- 为工作流编排者提供可显式指定的 `qwen cli` 执行入口，并可按配置在多个执行器之间切换。
- 为研发团队提供稳定的 SRC 输入，便于后续开展 `src_to_epic` 拆分。

# Inputs

- 原始需求文本或 Markdown 需求说明
- 工作流实例中的执行器选择配置
- 现有 LEE 执行器工厂、Runner、CLI 与 workflow wiring

# Processing

- 识别“接入 `qwen cli` 作为可选执行器组件”属于能力扩展型需求，并归类到 SRC 层级
- 约束接入方案必须复用现有执行器工厂与 Runner 路径
- 明确 CLI / workflow instance / 配置文件中的 `qwen cli` 选择入口
- 定义 `qwen cli` 的输入输出契约、配置映射与验收边界
- 明确 `qwen cli` 与 `claude_code`、`codex` 等执行器并存，而非替换关系

# Outputs

- 可显式选择的 `qwen cli` 执行器组件
- 标准化的配置入口与运行约束
- 可供后续 `src_to_epic` 使用的正式 SRC 文档

# Acceptance

- 能在 LEE 中以显式配置方式选择 `qwen cli`
- `qwen cli` 作为可选执行器组件与 `claude_code` 并存
- 能通过配置在多个执行器之间切换，而不是修改 workflow 结构
- 不创建平行 workflow 或平行执行链
- raw-to-src 仅产出 SRC，不越界产出 EPIC / FEAT / TASK
- 文档明确接入点、配置点、验收边界和非目标

# Constraints

- 必须复用现有执行器工厂、Runner 与 workflow wiring
- 必须保留来源追溯性
- 本阶段不替换或废弃 `claude_code` / `codex` 存量实现
- 本阶段不包含生产发布、灰度或运维策略设计

# Non Goals

- 不在本阶段完成 `src_to_epic`、`epic_to_feat`、`feat_to_delivery_prep`
- 不在本阶段设计发布编排、监控、灰度与告警方案
- 不在本阶段移除或替换其他执行器的历史实现

# Traceability

- Source workflow: `wf_task_702aa3a8`
- Source step: `source_normalization`
- Source artifact: `ART-00398`
- Raw requirement file: `tmp_qwen_raw_requirement.md`

