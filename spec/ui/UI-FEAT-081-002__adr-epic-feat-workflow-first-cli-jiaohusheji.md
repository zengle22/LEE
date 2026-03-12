---
id: UI-FEAT-081-002
ssot_type: ui
title: ADR/EPIC/FEAT Workflow-First CLI 交互设计
status: active
version: v1
parent_id: FEAT-081
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui_feat_081_001
  identity_kind: ssot
---

design_specs:
  prototype_id: UI-FEAT-081-001
  title: ADR/EPIC/FEAT Workflow-First CLI 交互设计
  core_paths:
  - 主路径：创建正式对象并进入治理流程
  - 异常路径：用户取消 / 验证失败 / Workflow 启动失败
  interaction_principles:
  - '命令命名一致性: lee <object-type> new'
  - '帮助系统一致性: Workflow Commands 独立分组'
  - '文案风格: 清晰直接、行动导向、透明诚实'
  - '交互反馈: 即时响应、视觉+文字双通道'
  - '防错设计: 显式确认、阻断绕过、环境检查、幂等提示'
  critical_states:
  - MAIN_HELP - 主帮助页面
  - COMMAND_HELP - 命令帮助详情
  - WORKFLOW_RUNNING - 交互流程进行中
  - VALIDATION_FEEDBACK - 验证反馈
  - CONFIRMATION_DIALOG - 确认对话框
  - SUCCESS - 成功完成
  - ERROR - 错误/异常
  design_decisions:
  - 'DD-001: CLI 作为 Workflow 优先入口'
  - 'DD-002: 强制交互式 Workflow'
  - 'DD-003: 帮助文案中明确"治理流程"'
  - 'DD-004: 错误信息的可操作性'
metadata:
  is_frozen: true
  frozen_at: '2026-03-12T00:00:00Z'
  implements:
  - FEAT-081
  acceptance_checklist:
    main_help_workflow_group: true
    help_copy_governance_flow: true
    workflow_progress_indicator: true
    validation_actionable_feedback: true
    confirmation_dialog_complete_info: true
    success_state_next_steps: true
    error_state_diagnostics: true
