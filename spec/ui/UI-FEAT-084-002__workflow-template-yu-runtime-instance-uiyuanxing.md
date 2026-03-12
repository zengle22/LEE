---
id: UI-FEAT-084-002
ssot_type: ui
title: Workflow Template 与 Runtime Instance UI原型
status: active
version: v1
parent_id: FEAT-084
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui
  identity_kind: ssot
---

design_specs:
  core_paths:
  - Template List - 模板列表查询流程
  - Instance List - 实例列表查询流程
  - Instance Create - 实例创建与版本冻结流程
  interaction_principles:
  - 'P1: 分层命名空间 - 使用 workflow 子命令隔离操作'
  - 'P2: 统一输出格式 - 支持 --format table/json/yaml'
  - 'P3: 状态颜色编码 - 🟢done 🔵running 🟡pending 🔴failed'
  - 'P4: 人类可读时间 - 相对格式显示 (2h ago, 1d ago)'
  - 'P5: 空状态友好 - 无数据时给出操作引导'
  - 'P6: 错误即文档 - 错误提示包含解决建议'
  key_page_states:
    template_list:
    - Loading - 扫描模板目录中
    - Normal - 正常列表展示
    - Empty - 空状态引导
    - Filtered - 过滤结果展示
    - JSON - JSON格式输出
    instance_list:
    - Loading - 查询数据库中
    - Normal - 正常列表展示(含状态颜色)
    - Filtered - 按状态/模板过滤
    - Empty - 空状态引导
    - Pagination - 分页展示
    instance_create:
    - Template Confirmation - 模板信息确认
    - Version Freeze Confirmation - 版本冻结确认
    - Upgrade Notice - 模板升级提示
    error_states:
    - Template Not Found - 模板不存在
    - Database Connection Failed - 数据库连接失败
    - Version Conflict - 版本冲突提示
  ui_components:
    template_list_columns:
    - NAME
    - VERSION
    - DESCRIPTION
    - LOCATION
    instance_list_columns:
    - ID
    - TEMPLATE
    - STATUS
    - STARTED
    - DURATION
    - AGE
    status_mapping:
      pending:
        color: yellow
        icon: 🟡
      running:
        color: blue
        icon: 🔵
      done:
        color: green
        icon: 🟢
      failed:
        color: red
        icon: 🔴
      cancelled:
        color: gray
        icon: ⚪
      unknown:
        color: default
        icon: ⚫
metadata:
  is_frozen: true
  frozen_at: '2026-03-12T21:00:00Z'
  contract_id: FUI-20260312-084
  parent_feat: FEAT-084
