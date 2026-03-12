---
id: UI-FEAT-143-004
ssot_type: ui
title: QA 执行入口规范化 UI/UX 原型
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui_prototype
  identity_kind: ssot
---

design_specs:
  core_paths:
  - RELEASE → TESTPLAN → TASK → 执行确认 → 执行触发 → 执行监控
  - 入口验证路径：task_ref 验证 → release_ref 验证 → testplan_ref 验证 → 执行就绪
  interaction_principles:
  - category: 路径引导原则
    principles:
    - 链式可见：用户在任何步骤都能看到完整路径链
    - 渐进披露：按层级逐步展示选项，避免信息过载
    - 状态同步：每一步操作实时反映到路径状态
    - 阻断明确：校验失败时明确告知阻断位置和原因
  - category: 操作约束原则
    principles:
    - 前置锁定：上级未选择时，下级选项禁用
    - 强制校验：进入执行前必须通过全部校验
    - 审计透明：用户可随时查看执行路径审计信息
    - 不可绕过：无直接执行入口，所有路径必须经过验证
  - category: 反馈即时原则
    principles:
    - 校验即反馈：每次选择后立即校验并反馈
    - 错误即引导：错误发生时提供修复路径
    - 进度可视化：执行前审核展示完整链路预览
  key_page_states:
  - state_id: ENTRY_EMPTY
    name: 执行入口初始状态
    description: 用户刚进入执行入口页面，未进行任何选择
  - state_id: ENTRY_RELEASE_SELECTED
    name: RELEASE 已选择
    description: 用户已选择 RELEASE，链路校验通过
  - state_id: ENTRY_CHAIN_COMPLETE
    name: 完整链路已选择
    description: RELEASE → PLAN → TASK 全部选择并验证通过
  - state_id: VALIDATION_ENTRY_ERROR
    name: 入口规范错误阻断
    description: 执行请求未包含有效的 TASK 引用
  - state_id: VALIDATION_CHAIN_ERROR
    name: 链路完整性错误阻断
    description: 链路中某一环节失效或不匹配
  - state_id: EXECUTION_REVIEW
    name: 执行前审核确认
    description: 展示完整链路预览，等待用户最终确认
  - state_id: BYPASS_BLOCKED
    name: 旁路入口已移除提示
    description: 用户尝试访问已移除的直接执行入口
  - state_id: AUDIT_SIDEBAR
    name: 审计日志侧边栏
    description: 展示执行入口审计历史
metadata:
  is_frozen: true
  frozen_at: '2026-03-12T20:45:00+08:00'
  review_status: approved
