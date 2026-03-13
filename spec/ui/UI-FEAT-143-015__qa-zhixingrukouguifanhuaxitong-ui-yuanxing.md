---
id: UI-FEAT-143-015
ssot_type: ui
title: QA 执行入口规范化系统 UI 原型
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

contract_type: frozen-ui-prototype
contract_version: v1.0
metadata:
  contract_id: FUIP-20260313-001
  is_frozen: true
  parent_feat: FEAT-143
  title: QA 执行入口规范化系统 UI 原型
  created_at: 2026-03-13
  designer_role: 资深 UI/UX 设计师
design_specs:
  interaction_principles:
  - 单一入口原则：所有测试执行必须通过 lee qa execute 命令发起，无其他旁路入口
  - 渐进式反馈原则：5 阶段进度反馈必须在每个关键校验节点即时呈现
  - 错误前置原则：校验失败时提供清晰的错误定位和修复建议
  - 状态可见原则：执行路径链路状态 (RELEASE->TESTPLAN->TASK) 必须可视化呈现
  - 审计透明原则：用户可随时查询历史执行审计记录
  - 一致性原则：CLI 输出格式、错误码、进度指示器保持统一风格
  core_paths:
  - name: QA 测试执行主路径
    description: 用户通过 CLI 发起测试执行的完整流程
    prototype_link: cli://lee-qa-execute/main-flow
    critical_states:
    - 初始状态：等待用户输入命令参数
    - '[1/5] 入口校验中：验证 task_ref 有效性'
    - '[2/5] 旁路检测中：检查是否存在旁路执行企图'
    - '[3/5] 链路校验中：验证 RELEASE->TESTPLAN->TASK 链路完整性'
    - '[4/5] 执行准备中：初始化执行环境和资源'
    - '[5/5] 执行启动：测试执行正式开始'
    - 成功状态：exit_code=0，显示执行结果摘要
    - 失败状态：exit_code=1-5，显示错误详情和修复建议
  - name: 审计日志查询路径
    description: 用户查询历史执行审计记录
    prototype_link: cli://lee-qa-audit/query-flow
    critical_states:
    - 查询条件输入：支持按 run_id/task_id/testplan_id/release_id 过滤
    - 结果列表展示：显示审计记录摘要
    - 详情查看：展示完整的 SSOT 三轴绑定信息
  secondary_paths_description: '非主路径场景：

    1. 参数缺失场景：用户未提供 --task-ref 时，显示帮助信息并提示必需参数

    2. 验证模式：使用 --validate-only 时仅执行校验不真正启动测试

    3. JSON 输出模式：使用 --json 时输出机器可读的结构化结果

    4. 详细模式：使用 --verbose 时显示调试级别的日志信息

    5. 帮助查询：使用 --help 时显示命令用法和选项说明

    '
  component_specs:
    progress_indicator:
      type: staged_progress
      format: '[{current}/{total}] {stage_name}'
      stages:
      - index: 1
        name: 入口校验
        error_code: 1
      - index: 2
        name: 旁路检测
        error_code: 2
      - index: 3
        name: 链路校验
        error_code: 3
      - index: 4
        name: 执行准备
        error_code: 4
      - index: 5
        name: 执行启动
        error_code: 5
    error_messages:
      style: structured
      format: '❌ {stage} 失败：{error_detail}

        💡 建议：{suggestion}'
      categories:
      - code: ENTRY-001
        message: 缺少必需的 task_ref 参数
        suggestion: 使用 --task-ref=<task_id> 指定要执行的任务
      - code: ENTRY-002
        message: task_ref 不存在或无效
        suggestion: 检查 task_id 是否正确，或确认 task 归属于 testplan
      - code: BYPASS-001
        message: 检测到旁路执行企图：缺少 task_ref
        suggestion: 所有执行必须通过 TESTPLAN->TASK 路径发起
      - code: BYPASS-002
        message: 检测到旁路执行企图：task 不归属于任何 TESTPLAN
        suggestion: 确认 task 已正确配置到 testplan 中
      - code: BYPASS-003
        message: 检测到旁路执行企图：TESTPLAN 不归属于任何 RELEASE
        suggestion: 确认 testplan 已正确配置到 release 中
      - code: CHAIN-001
        message: 链路校验失败：TASK->TESTPLAN 引用断裂
        suggestion: 检查 task 的 parent_id 配置
      - code: CHAIN-002
        message: 链路校验失败：TESTPLAN->RELEASE 引用断裂
        suggestion: 检查 testplan 的 release_ref 配置
      - code: CHAIN-003
        message: 链路校验失败：SSOT 对象不存在
        suggestion: 确认引用的 SSOT 对象已在 spec 目录中定义
    exit_codes:
    - code: 0
      meaning: 成功
      description: 测试执行成功启动
    - code: 1
      meaning: 入口校验失败
      description: task_ref 无效或缺失
    - code: 2
      meaning: 链路校验失败
      description: RELEASE->TESTPLAN->TASK 链路不完整
    - code: 3
      meaning: 旁路阻断
      description: 检测到绕过 TESTPLAN/TASK 的执行企图
    - code: 4
      meaning: 执行失败
      description: 执行准备或启动过程中出错
    - code: 5
      meaning: 内部错误
      description: 系统内部异常
  audit_display_spec:
    fields:
    - name: run_id
      label: 执行 ID
      type: string
    - name: task_id
      label: 任务 ID
      type: string
    - name: testplan_id
      label: 测试计划 ID
      type: string
    - name: release_id
      label: 发布 ID
      type: string
    - name: feat_id
      label: 特性 ID
      type: string
    - name: entry_source
      label: 入口来源
      type: string
    - name: path_chain
      label: 路径链
      type: array
    - name: executed_at
      label: 执行时间
      type: timestamp
    - name: executor
      label: 操作用户
      type: string
    query_format: lee qa audit [--run-id=<id>] [--task-id=<id>] [--plan-id=<id>] [--release-id=<id>]
ssot_output_contract:
  contract_version: '1.0'
  run_id: ui-design-run-001
  outputs:
  - key: ui
    identity_kind: ssot
    ssot_type: ui
    title: QA 执行入口规范化系统 UI 原型
    parent: feat
    implements:
    - FEAT-143
    - TASK-FEAT-143-001
    - TASK-FEAT-143-002
    - TASK-FEAT-143-003
    - TASK-FEAT-143-004
    - TASK-FEAT-143-005
