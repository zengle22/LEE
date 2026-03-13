---
id: UI-FEAT-082-005
ssot_type: ui
title: ui_design
status: active
version: v1
parent_id: FEAT-082
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui_prototype
  identity_kind: ssot
---

design_specs:
  interaction_principles:
  - 'P1: 元数据自动展示 - 创建结果页必须默认展开显示自动继承的元数据'
  - 'P2: 注入字段高亮 - 系统自动注入的字段必须使用视觉区分'
  - 'P3: 追溯链可视化 - derived_from_ids 必须以链式图或树形图展示'
  - 'I1: 智能过滤 - parent_id 选择器只显示符合层级关系的候选对象'
  - 'I2: 继承预览 - 提交前预览 source_refs 的传递结果'
  - 'I3: 冲突提示 - 多个可能的 source_refs 时提示用户确认'
  - 'E1: 层级违规拦截 - 显示明确的层级规则说明'
  - 'E2: 继承失败回滚 - 不允许创建对象，显示具体失败原因'
  - 'E3: 追溯链断裂检测 - 指向已删除对象时显示警告'
  - 'S1: 加载态骨架屏 - 元数据加载时使用 skeleton 模式'
  - 'S2: 空态引导 - 无 derived_from_ids 时显示友好提示'
  - 'S3: 成功态反馈 - 使用 toast + 页面双重反馈'
  core_paths:
  - name: 创建 Formal Object 主路径
    prototype_link: '#2-核心流转路径-core-paths'
    critical_states:
    - default
    - validating
    - inheriting
    - success
    - failure
  - name: 'Path A: 创建 EPIC（自动绑定 SRC）'
    prototype_link: '#22-关键原型路径描述'
    critical_states:
    - default
    - filtered
    - success
  - name: 'Path B: 创建 FEAT（自动绑定 EPIC 和 source_refs）'
    prototype_link: '#22-关键原型路径描述'
    critical_states:
    - default
    - inheriting
    - success
  - name: 'Path C: 创建带 derived_from_ids 的新版本 FEAT'
    prototype_link: '#22-关键原型路径描述'
    critical_states:
    - default
    - inheriting
    - success
  secondary_paths_description: 批量创建场景、跨 workspace 引用场景、历史追溯场景、元数据修复场景详见第 6 节
  pages:
  - id: page.workflow_executor
    route: /workflow/executor
    states:
    - default
    - loading
    - empty
    - error
  - id: page.object_type_selector
    route: /workflow/create/:workflow_id/type
    states:
    - default
    - filtered
    - loading
    - error
  - id: page.object_creation_form
    route: /workflow/create/:workflow_id/type/:type
    states:
    - default
    - validating
    - inheriting
    - success
    - failure
  - id: page.execution_result
    route: /workflow/result/:execution_id
    states:
    - success
    - partial_success
    - failure
    - timeout
  - id: page.object_detail
    route: /object/:id
    states:
    - default
    - loading
    - not_found
    - archived
  - id: page.traceability_graph
    route: /object/:id/traceability
    states:
    - default
    - loading
    - empty
    - complex
metadata:
  is_frozen: true
  feat_ref: FEAT-082
  design_version: v1
  designer_role: ui-ux-designer
