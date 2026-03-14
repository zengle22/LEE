---
id: SRC-011
ssot_type: src
title: LEE Qwen 对话执行后端接入契约
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

在 LEE 工作流执行框架内，建立 `qwen cli` 作为对话型执行后端的标准接入契约，使其通过统一配置进入现有 workflow / runner / executor factory 体系，在文档生成、结构化评审、需求分析和中文任务处理等场景中复用；同时明确真正的 coding executors 仍是 `claude_code`、`codex` 与 `kimi`。

# User Value

- 为工作流使用者提供一个可配置切换的通用对话执行后端，而不是额外维护一条专用执行链。
- 为文档、评审、需求分析和中文任务处理场景提供更合适的执行能力。
- 为研发团队保留统一的执行结果、追溯、审计和 SSOT 物化语义。

# Inputs

- 工作流任务目标、结构化上下文和显式执行器选择配置
- 工作流实例中的执行器选择配置
- 现有 LEE 执行器工厂、Runner、CLI 与 workflow wiring

# Processing

- 约束接入方案必须复用现有执行器工厂与 Runner 路径
- 明确 CLI / workflow instance / 配置文件中的 `qwen_chat` 选择入口，并兼容历史别名 `qwen`
- 定义 `qwen cli` 的无头对话调用契约、输入输出契约、配置映射与验收边界
- 明确 `qwen_chat` 与 `claude_code`、`codex`、`kimi` 并存，而非替换关系
- 明确 `qwen_chat` 不作为 coding executor 直接修改文件或执行命令；工具调用、落盘和命令执行由 LEE runtime 统一负责

# Outputs

- 可显式选择的 `qwen_chat` 对话执行后端组件
- 标准化的配置入口与运行约束
- 与现有执行器一致的执行结果、追溯与物化语义

# Acceptance

- 能在 LEE 中以显式配置方式选择 `qwen_chat`
- `qwen_chat` 作为可选对话执行后端与 `claude_code`、`codex`、`kimi` 并存
- 能通过配置在多个执行器之间切换，而不是修改 workflow 结构
- `qwen cli` 具备可自动化调用的无头模式，不依赖交互式终端会话
- `qwen cli` 可被通用 workflow 复用，而不是只服务于 EPIC / FEAT / SRC 等 SSOT 文档生成
- `qwen cli` 在 LEE 中默认被当作对话/结构化输出后端使用，不承担真正的 coding agent 职责
- 真正的 coding executors 明确为 `claude_code`、`codex`、`kimi`
- 不创建平行 workflow 或平行执行链
- 文档明确接入点、配置点、验收边界和非目标

# Constraints

- 必须复用现有执行器工厂、Runner 与 workflow wiring
- 必须保留来源追溯性
- 本阶段不替换或废弃 `claude_code` / `codex` / `kimi` 存量实现
- 本阶段不包含生产发布、灰度或运维策略设计

# Non Goals

- 不在本阶段要求所有历史 workflow 都强制切换到 `qwen_chat`
- 不在本阶段把 `qwen cli` 当成文件编辑型 coding executor 接入
- 不在本阶段设计发布编排、监控、灰度与告警方案
- 不在本阶段移除或替换其他执行器的历史实现

# Traceability

- Source workflow: `wf_task_702aa3a8`
- Source step: `source_normalization`
- Source artifact: `ART-00398`
- Raw requirement file: `tmp_qwen_raw_requirement.md`

