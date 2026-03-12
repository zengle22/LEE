---
id: UI-FEAT-143-002
ssot_type: ui
title: QA执行入口规范化UI原型
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
  - id: path-primary-execution
    name: QA测试执行主路径
    description: 从TESTPLAN的TASK触发测试执行的标准路径
    steps:
    - step: 1
      page: TestPlan详情页
      action: 用户选择特定TestPlan
      outcome: 进入TestPlan视图，展示关联TASK列表
    - step: 2
      page: Task执行入口页
      action: 用户点击TASK的[执行]按钮
      outcome: 触发执行路径校验流程
    - step: 3
      page: 路径校验状态页
      action: 系统验证 RELEASE -> PLAN -> TASK 链路
      outcome: 校验通过则进入执行确认，失败则显示阻断提示
    - step: 4
      page: 执行确认页
      action: 用户确认执行参数
      outcome: 提交执行请求，记录审计日志
  - id: path-audit-query
    name: 执行审计查询路径
    description: 查看执行入口审计日志的查询路径
    steps:
    - step: 1
      page: 审计中心页
      action: 用户进入审计日志模块
      outcome: 展示可审计的操作类型列表
    - step: 2
      page: 执行审计列表页
      action: 用户筛选'执行入口'类型
      outcome: 展示所有执行请求的审计记录
    - step: 3
      page: 审计详情页
      action: 用户点击单条记录
      outcome: 展示完整路径链、入口来源、时间戳、操作用户
  - id: path-bypass-blocked
    name: 旁路执行阻断路径
    description: 尝试绕过标准入口时被系统阻断
    steps:
    - step: 1
      page: 非法入口尝试
      action: 用户尝试直接URL或API触发执行
      outcome: 系统检测缺少有效task_ref
    - step: 2
      page: 阻断提示页
      action: 系统拒绝请求
      outcome: 显示入口规范错误，引导至标准入口
    - step: 3
      page: 审计记录
      action: 系统自动记录
      outcome: 旁路尝试被记录至审计日志
  interaction_principles:
  - id: principle-01
    name: 单一路径引导原则
    description: 所有执行入口必须明确引导至TESTPLAN->TASK路径，不允许存在多个并行的执行入口
    application:
    - 全局导航移除独立的[执行测试]快捷入口
    - TestPlan列表页为每个条目突出显示[查看TASK]按钮
    - TASK卡片为唯一可触发执行的交互元素
  - id: principle-02
    name: 透明化路径校验原则
    description: 用户应清楚了解执行前的校验过程和结果
    application:
    - 校验过程展示进度指示器(验证RELEASE关联...验证PLAN状态...验证TASK有效性...)
    - 校验失败时明确显示断链位置(RELEASE缺失/PLAN未激活/TASK无效)
    - 校验成功时展示完整路径链供用户确认
  - id: principle-03
    name: 阻断友好性原则
    description: 当执行被阻断时，提供清晰的修复指引而非仅显示错误
    application:
    - 旁路阻断提示包含[前往标准入口]快捷按钮
    - 路径不完整时提供[补全关联]操作入口
    - 错误信息使用建设性语言(如何修正)而非仅陈述(什么错误)
  - id: principle-04
    name: 审计可见性原则
    description: 执行行为的审计信息应易于访问和理解
    application:
    - TASK执行历史面板直接展示审计轨迹
    - 执行按钮旁显示[查看审计日志]辅助入口
    - 审计信息使用可视化路径图而非纯文本
  - id: principle-05
    name: 一致性反馈原则
    description: 所有执行相关操作使用统一的反馈模式
    application:
    - 成功执行使用统一的成功提示组件，包含执行ID和审计日志链接
    - 阻断/拒绝使用统一的警告提示组件，包含原因和修复指引
    - 加载/校验中使用统一的进度指示组件
  key_page_states:
  - page_id: page-task-execution-entry
    page_name: TASK执行入口页
    states:
    - state_id: state-ready
      state_name: 可执行状态
      visual:
        primary_action: '[执行测试]按钮 - 主色调、可点击'
        path_indicator: 展示RELEASE->PLAN->TASK完整链路图标
        status_badge: 就绪/可执行
      interactions:
      - 点击[执行测试]进入路径校验流程
      - hover路径节点显示关联对象详情tooltip
      - 点击[查看审计]展开执行历史面板
    - state_id: state-path-missing-release
      state_name: 缺少RELEASE关联
      visual:
        primary_action: '[执行测试]按钮 - 禁用状态、灰色'
        path_indicator: RELEASE节点显示红色断链图标，PLAN/TASK显示灰色
        status_badge: 路径不完整：缺少RELEASE关联
        alert_banner: 顶部警告条：当前TestPlan未关联RELEASE，无法执行测试
      interactions:
      - 点击禁用按钮弹出修复指引模态框
      - '[修复指引]按钮跳转至RELEASE关联页面'
      - 路径节点可点击查看缺失详情
    - state_id: state-plan-inactive
      state_name: PLAN未激活
      visual:
        primary_action: '[执行测试]按钮 - 禁用状态'
        path_indicator: PLAN节点显示黄色警告图标
        status_badge: PLAN状态：未激活/已归档
        alert_banner: 提示：当前TestPlan未处于激活状态
      interactions:
      - 提供[激活PLAN]快捷操作(如用户有权限)
      - 显示PLAN状态变更历史
    - state_id: state-task-invalid
      state_name: TASK无效
      visual:
        primary_action: '[执行测试]按钮 - 禁用状态'
        path_indicator: TASK节点显示红色错误图标
        status_badge: TASK配置无效
        alert_banner: 错误：当前TASK配置不完整或已失效
      interactions:
      - '[查看配置]按钮跳转TASK编辑页'
      - 显示具体配置错误列表
    - state_id: state-executing
      state_name: 执行中状态
      visual:
        primary_action: '[执行测试]按钮 - 加载状态，显示 spinner'
        progress_indicator: 步骤进度条：校验路径 -> 准备环境 -> 启动执行
        status_badge: 执行中...
        cancel_action: 显示[取消]按钮(如支持)
      interactions:
      - 实时更新执行进度
      - 点击[取消]需二次确认
      - 完成后自动跳转执行详情页
    - state_id: state-bypass-detected
      state_name: 旁路执行被阻断
      visual:
        error_icon: 大型阻断图标
        title: 非法执行入口
        message: 系统检测到您尝试通过非标准入口触发测试执行
        details: 显示检测到的入口来源和期望的正确路径
      interactions:
      - '[前往标准入口]按钮跳转至TestPlan列表'
      - '[查看规范]按钮展开入口规范说明'
      - 返回按钮返回上一页
  - page_id: page-path-validation
    page_name: 路径校验状态页
    states:
    - state_id: state-validating
      state_name: 校验进行中
      visual:
        animation: 路径链逐节点高亮动画
        step_1: 验证RELEASE存在性 - 进行中/完成
        step_2: 验证PLAN状态 - 等待中/进行中/完成
        step_3: 验证TASK有效性 - 等待中/进行中/完成
      interactions:
      - 显示预计校验时间
      - 提供[取消校验]选项
    - state_id: state-validation-pass
      state_name: 校验通过
      visual:
        success_icon: 绿色勾选动画
        path_summary: 展示完整的RELEASE->PLAN->TASK路径
        action_buttons: '[确认执行] [返回修改]'
      interactions:
      - 点击[确认执行]正式提交执行请求
      - 点击路径节点查看对象详情
      - 倒计时自动确认(可选)
    - state_id: state-validation-fail
      state_name: 校验失败
      visual:
        error_icon: 红色错误标识
        failed_node: 高亮显示校验失败的节点
        error_details: 列出具体失败原因
        remediation: 显示修复建议
      interactions:
      - '[一键修复]按钮(如支持自动修复)'
      - '[手动修复]跳转至对应配置页'
      - '[返回]返回TASK页'
  - page_id: page-audit-log
    page_name: 执行审计日志页
    states:
    - state_id: state-audit-list
      state_name: 审计列表
      visual:
        filter_bar: 按时间/用户/结果类型筛选
        list_view: 执行记录列表，每行显示：时间、用户、入口来源、路径链、结果
        pagination: 分页控制
      interactions:
      - 点击记录展开详情
      - 导出审计报告
      - 筛选旁路尝试记录
    - state_id: state-audit-detail
      state_name: 审计详情
      visual:
        path_visualization: 图形化展示RELEASE->PLAN->TASK路径
        metadata: 执行ID、时间戳、操作用户、IP地址、入口来源
        chain_validation: 路径校验结果详情
        related_logs: 关联的执行日志链接
      interactions:
      - 点击路径节点跳转对象详情
      - '[查看执行结果]跳转结果页'
      - '[返回列表]返回审计列表'
metadata:
  is_frozen: true
  feature_id: FEAT-143
  title: QA执行入口规范化UI原型
  version: v1
  created_at: '2026-03-12'
  review_status: pending_human_review
