---
id: UI-FEAT-143-005
ssot_type: ui
title: ui_design
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
  - RELEASE -> PLAN -> TASK 标准执行入口路径
  - 执行入口审计查询路径
  - 旁路请求阻断路径
  interaction_principles:
    entry_uniqueness: 单一路径标识、入口状态显性化、旁路阻断提示
    path_validation: 实时校验反馈、校验详情可展开、阻断原因明确
    audit_traceability: 入口来源记录、旁路尝试审计、审计查询友好
    ssot_binding: 三轴绑定展示、绑定缺失警示、绑定关系可追溯
  key_states:
  - state_id: release_detail_testplan_list
    name: RELEASE详情页-TESTPLAN列表
    triggers:
    - 用户查看RELEASE详情
    elements:
    - TESTPLAN列表
    - 状态标签
    - 查看入口
  - state_id: testplan_detail_path_valid
    name: TESTPLAN详情页-路径完整
    triggers:
    - 用户进入有效的TESTPLAN详情页
    elements:
    - 路径校验通过标识
    - 可执行任务列表
    - 执行按钮
  - state_id: testplan_detail_path_broken
    name: TESTPLAN详情页-路径断裂
    triggers:
    - 用户进入无效的TESTPLAN详情页
    elements:
    - 路径校验失败标识
    - 错误原因
    - 修复指引
    - 禁用执行按钮
  - state_id: task_execution_confirm_valid
    name: TASK执行确认-校验通过
    triggers:
    - 用户点击有效TASK的执行按钮
    elements:
    - 路径链验证
    - SSOT三轴绑定
    - 审计信息
    - 确认/取消按钮
  - state_id: task_execution_confirm_invalid
    name: TASK执行确认-校验失败
    triggers:
    - 入口校验未通过
    elements:
    - 失败节点标识
    - 失败原因
    - 返回指引
  - state_id: execution_progress_audit
    name: 执行进度页-审计展示
    triggers:
    - 用户确认执行后
    elements:
    - 执行入口信息
    - SSOT关联图谱
    - 审计日志ID
    - 执行进度
  - state_id: execution_history_filtered
    name: 执行历史页-入口来源筛选
    triggers:
    - 用户查看执行历史
    elements:
    - 入口来源筛选器
    - 路径链展示
    - BYPASSED警示
  - state_id: bypass_blocked_error
    name: 旁路阻断错误页
    triggers:
    - 外部系统尝试绕过标准入口
    elements:
    - 错误代码
    - 规范说明
    - 正确执行方式
    - 审计日志ID
ui_components:
  path_chain_display:
    type: composite
    elements:
    - release_node
    - plan_node
    - task_node
    - validation_status
    features:
    - expandable_details
    - failure_reasons
    - interactive_nodes
    props_interface: PathChainProps
  entry_source_tag:
    type: tag
    variants:
    - type: task_trigger
      label: 标准入口
      color: '#22C55E'
      bg: '#E6F7E6'
    - type: bypassed_blocked
      label: 旁路阻断
      color: '#EF4444'
      bg: '#FEE2E2'
    - type: api_direct
      label: API调用
      color: '#F59E0B'
      bg: '#FEF3C7'
    - type: manual
      label: 手动触发
      color: '#3B82F6'
      bg: '#DBEAFE'
    props_interface: EntrySourceTagProps
  ssot_axis_binding:
    type: status_panel
    axes:
    - requirement
    - delivery
    - evidence
    states:
    - bound
    - unbound
    - warning
    props_interface: SSOTAxisBindingProps
interaction_flows:
- flow_id: standard_execution_entry
  name: 标准执行入口流程
  steps:
  - RELEASE详情页查看TESTPLAN列表
  - 选择TESTPLAN进入详情页
  - 查看路径校验状态
  - 选择TASK点击执行
  - 执行确认对话框校验
  - 进入执行进度页
- flow_id: audit_query
  name: 审计查询流程
  steps:
  - 进入执行历史页面
  - 选择入口来源筛选条件
  - 查看筛选结果
  - 点击记录查看路径链详情
- flow_id: bypass_blocking
  name: 旁路阻断流程
  steps:
  - 外部系统尝试直接调用API
  - 入口路由规则拦截
  - 返回ENTRY_VIOLATION错误
  - 显示旁路阻断错误页
  - 记录审计日志
