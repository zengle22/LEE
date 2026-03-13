---
id: EPIC-048
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
frozen_at: '2026-03-13T00:39:09.562669'
---

# Kimi Executor 接入与配置能力

## 目标

建立 Kimi CLI 执行器的标准接入与配置能力，使其成为 LEE 工作流中可显式选择、可配置为默认、可追溯、可复用的通用 coding executor，同时严格遵循现有架构复用原则，不创建平行 workflow 或平行执行链。

## 范围

- Kimi 执行器在 canonical executor 架构中的注册与发现机制
- 用户通过 `--executor kimi` 参数显式指定 Kimi 执行器的能力
- 配置系统支持将 Kimi 设为默认 coding executor
- 本地 `kimi-cli --print` 调用封装与输出格式兼容层
- Kimi 执行器配置 schema 定义与校验
- 执行器切换时的上下文保持与追溯性
- 与现有 claude_code 执行路径的架构对齐

## 非目标

- src_to_epic、epic_to_feat、feat_to_delivery_prep 等下游流程的实现
- 发布编排、监控、灰度与告警方案的设计
- 其他执行器（claude_code、codex、qwen）历史实现的重构
- 新增业务 workflow 模板或修改现有 coding 步骤模板
- 远端 Kimi API 的直接调用（仅通过本地 CLI）
- Claude Code / Codex 存量实现的替换
- 生产发布、灰度或运维策略设计

## 成功标准

- 用户可通过 `--executor kimi` 成功触发 Kimi 执行器完成编码任务
- 配置默认执行器为 kimi 后，无显式参数的任务自动使用 Kimi
- Kimi 执行器输出格式与现有 executor 输出 100% 兼容
- 零新增 workflow 模板，完全复用现有 coding 步骤模板
- 执行器切换时任务上下文完整保留，可追溯来源
- 系统维护者可在不修改 workflow wiring 的情况下扩展 executor 配置
