---
id: EPIC-038
ssot_type: epic
title: Kimi Executor 接入与配置能力
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-12T21:09:43.097711'
---

# Kimi Executor 接入与配置能力

## 目标

在 LEE 工作流执行框架内建立 Kimi 执行器的标准接入与配置能力，使其成为可显式选择、可配置为默认、可追溯、可复用的执行能力选项，支撑中文场景下的需求分析与代码执行任务，同时严格遵循现有架构复用原则，实现零侵入复用现有工作流。

## 范围

- CLI 命令入口扩展：支持 `--executor kimi` 参数识别与路由
- 配置系统扩展：支持默认 coding executor 的可配置化切换
- Kimi Executor 实现：基于 canonical executor 架构实现 Kimi 执行器
- 执行器别名兼容：兼容现有 `qwen` 等别名模式的设计
- 来源追溯机制：建立 ADR-014 来源追溯链路
- Runner 集成：复用现有 Runner 与 workflow wiring，不创建独立链路
- 现有步骤模板兼容：确保 coding 步骤模板无需修改即可使用 Kimi 执行器

## 非目标

- 不实现 `src_to_epic`、`epic_to_feat`、`feat_to_delivery_prep` 等下游交付步骤
- 不设计发布编排、监控、灰度与告警方案
- 不重构 Claude Code / Codex / Qwen 等其他执行器的历史实现
- 不新增业务 workflow 模板，严格复用现有模板
- 不替换 Claude Code / Codex 存量实现
- 不创建平行 workflow 或平行执行链
- 不涉及业务功能（如手机号登录、支付流程等）的实现

## 成功标准

- CLI 执行 `lee run <wf> --executor kimi` 成功路由到 Kimi 执行器
- 配置修改后，默认 coding executor 自动切换为 Kimi 且生效
- 现有 coding 步骤模板无需任何修改即可使用 Kimi 执行器
- Kimi 执行器输出格式与现有 executor 兼容
- 零侵入复用现有工作流，不创建平行链路或独立 Runner
- ADR-014 来源追溯链路完整可验证
