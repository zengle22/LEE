---
id: UI-FEAT-169-004
ssot_type: ui
title: ui_design
status: frozen
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui_prototype
  identity_kind: ssot
frozen_at: '2026-03-13T01:36:39.419484'
---

valid_executor_types:
- type: claude_code
  description: Claude Code 执行器，使用 Anthropic Claude API
  is_default: true
  display_name: Claude Code (Default)
- type: qwen
  description: 通义千问执行器，使用阿里云 Qwen API
  is_default: false
  display_name: Qwen (通义千问)
- type: kimi
  description: Moonshot Kimi 执行器，使用 Kimi API
  is_default: false
  display_name: Kimi (Moonshot)
- type: codex
  description: OpenAI Codex 执行器，使用 Codex API
  is_default: false
  display_name: Codex (OpenAI)
- type: langgraph
  description: LangGraph 执行器，使用 LangGraph 框架
  is_default: false
  display_name: LangGraph
- type: shell
  description: Shell 命令执行器，本地执行
  is_default: false
  display_name: Shell (Local)
- type: llm
  description: 通用 LLM 执行器，可配置模型
  is_default: false
  display_name: LLM (Generic)
