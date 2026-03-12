---
id: UI-FEAT-143-007
ssot_type: ui
title: QA 执行入口规范化
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
contract_version: '1.0'
metadata:
  contract_id: FUIP-20260313-001
  is_frozen: true
  frozen_at: '2026-03-13T00:00:00Z'
  feature_id: FEAT-143
  feature_title: QA 执行入口规范化
  designer: UI/UX Agent
  design_date: '2026-03-13'
design_specs:
  interaction_principles:
  - 'UIP-001: 单一入口原则 - 所有测试执行必须通过 TESTPLAN.TASK.execute() 触发，拒绝无 task_ref 的执行请求'
  - 'UIP-002: 链路完整原则 - 执行前必须验证 RELEASE→PLAN→TASK 三级引用链路的完整性和有效性'
  - 'UIP-003: 显式拒绝原则 - 旁路请求必须明确拒绝，返回规范错误码并记录审计日志'
  - 'UIP-004: 审计透明原则 - 每次执行的入口来源、路径链、时间戳、操作用户必须可追溯审计'
  - 'UIP-005: 渐进校验原则 - 校验失败时按 task→plan→release 顺序逐级提示具体错误'
  - 'UIP-006: 静默失败原则 - 阻断旁路入口时返回友好错误信息，不暴露内部实现细节'
  core_paths:
  - name: 标准执行入口路径
    prototype_link: RELEASE → PLAN → TASK → EXECUTION
    critical_states:
    - 入口参数解析
    - TASK 有效性校验
    - PLAN 归属校验
    - RELEASE 链路校验
    - 审计记录
    - 执行引擎分发
  - name: 旁路阻断路径
    prototype_link: 检测 → 拒绝 → 审计记录 → 返回错误
    critical_states:
    - 旁路请求检测
    - 阻断确认
    - 审计日志写入
    - 规范错误返回
  - name: 审计查询路径
    prototype_link: EXECUTION → AUDIT → QUERY
    critical_states:
    - 执行记录查询
    - 入口来源追溯
    - 路径链展示
    - 时间线审计
  secondary_paths_description: 非标准执行路径包括：仅传 task_ref 自动补全 plan/release 链路的自动校验路径，以及仅做校验不执行
    dry-run 路径。这两类路径均需遵守单一入口原则。
cli_output_standards:
  status_icons:
    success: ✓
    failure: ✗
    warning: ⚠
    processing: →
    pending: ○
  stage_indicators:
  - '[ENTRY] - 入口校验阶段'
  - '[CHAIN] - 链路校验阶段'
  - '[AUDIT] - 审计记录阶段'
  - '[EXEC] - 执行引擎阶段'
  error_codes:
  - code: ERR-ENTRY-001
    message: 缺少 task_ref 参数
    severity: block
    action: 阻断执行，提示使用规范命令
  - code: ERR-ENTRY-002
    message: task_ref 无效或不存在
    severity: block
    action: 阻断执行，提示检查 task_ref
  - code: ERR-ENTRY-003
    message: task 不归属任何 testplan
    severity: block
    action: 阻断执行，提示关联 testplan
  - code: ERR-CHAIN-001
    message: plan_ref 缺失或无效
    severity: block
    action: 链路断裂阻断
  - code: ERR-CHAIN-002
    message: release_ref 缺失或无效
    severity: block
    action: 链路断裂阻断
  - code: ERR-CHAIN-003
    message: 链路断裂 - task/plan/release 不匹配
    severity: block
    action: 链路校验阻断
  - code: ERR-BYPASS-001
    message: 检测到旁路执行尝试
    severity: block
    action: 阻断并记录审计日志
key_states:
- state_id: STATE-001
  name: 执行请求入口解析
  description: 用户提交测试执行请求，系统解析入口参数
  triggers:
  - 用户执行 lee qa execute --task-ref=TASK-xxx
  outputs:
  - task_ref 提取结果
  - plan_ref 提取结果（可选）
  - release_ref 提取结果（可选）
  error_scenarios:
  - 缺少必需参数 task_ref
  - 参数格式错误
  ui_elements:
  - CLI 命令行提示符
  - 参数解析反馈
  - 缺少参数错误提示
- state_id: STATE-002
  name: TASK 有效性校验
  description: 校验 task_ref 指向的 TASK 是否存在且有效
  triggers:
  - 入口参数解析完成
  outputs:
  - TASK 存在性验证结果
  - TASK 状态（active/inactive）
  - TASK 归属的 testplan_id
  error_scenarios:
  - TASK 不存在（ERR-ENTRY-002）
  - TASK 已废弃（ERR-ENTRY-002）
  ui_elements:
  - 任务加载指示器
  - 任务状态反馈
  - 归属 testplan 提示
- state_id: STATE-003
  name: PLAN 归属校验
  description: 验证 TASK 归属的 TESTPLAN 有效性
  triggers:
  - TASK 有效性校验通过
  outputs:
  - testplan_id
  - testplan 存在性
  - testplan 与 task 的关联状态
  error_scenarios:
  - TASK 无归属 PLAN（ERR-ENTRY-003）
  - PLAN 不存在（ERR-CHAIN-001）
  ui_elements:
  - 计划加载指示器
  - 关联关系可视化
  - 链路状态指示
- state_id: STATE-004
  name: RELEASE 链路校验
  description: 验证 TESTPLAN 归属的 RELEASE 有效性
  triggers:
  - PLAN 归属校验通过
  outputs:
  - release_id
  - release 存在性
  - release 与 plan 的关联状态
  - 完整链路状态
  error_scenarios:
  - PLAN 无归属 RELEASE（ERR-CHAIN-002）
  - RELEASE 不存在（ERR-CHAIN-002）
  - 链路不匹配（ERR-CHAIN-003）
  ui_elements:
  - 发布版本加载指示器
  - 完整链路可视化
  - 链路断裂点高亮
- state_id: STATE-005
  name: 旁路执行阻断
  description: 检测并阻断绕过 TESTPLAN/TASK 的直接执行请求
  triggers:
  - 检测到无 task_ref 的执行请求
  - 检测到非 TASK 触发的 runner 调用
  outputs:
  - 阻断确认
  - 审计日志写入
  - 规范错误码返回
  error_scenarios:
  - 直接调用 runner 接口
  - 通过旧入口 /api/v1/run 触发
  - 脚本层绕过 plan/task
  ui_elements:
  - 阻断警告提示
  - 错误码展示
  - 规范入口引导
- state_id: STATE-006
  name: 审计记录
  description: 执行前记录审计日志，绑定 SSOT 三轴关系
  triggers:
  - 链路校验通过
  outputs:
  - execution_id
  - audit_ref
  - SSOT 三轴绑定信息（release/plan/task）
  error_scenarios:
  - 审计日志写入失败
  ui_elements:
  - 审计记录确认
  - execution_id 展示
  - 审计引用号
- state_id: STATE-007
  name: 执行引擎分发
  description: 将验证通过的请求分发至执行引擎
  triggers:
  - 审计记录完成
  outputs:
  - 执行进度
  - 执行结果
  - 详细报告链接
  error_scenarios:
  - 执行失败
  - 环境准备失败
  - 超时
  ui_elements:
  - 执行进度条
  - 状态更新指示
  - 结果报告链接
command_specifications:
  standard_execute: lee qa execute --task-ref=TASK-xxx
  standard_execute_full: lee qa execute --task-ref=TASK-xxx --plan-ref=PLAN-xxx --release-ref=REL-xxx
  validate_only: lee qa execute --task-ref=TASK-xxx --validate-only
  audit_query: lee qa audit log --execution=EXEC-xxx
  audit_query_by_task: lee qa audit log --task-ref=TASK-xxx
  list_tasks: lee qa task list --plan-ref=PLAN-xxx
audit_specification:
  required_fields:
  - execution_id
  - task_ref
  - task_name
  - plan_ref
  - plan_name
  - release_ref
  - release_name
  - entry_source
  - entry_path
  - timestamp
  - operator
  - result
  entry_source_values:
  - CLI_TASK_EXECUTE
  - CLI_TASK_VALIDATE
  - API_TASK_EXECUTE
  - BYPASS_ATTEMPT
  queryable_by:
  - execution_id
  - task_ref
  - plan_ref
  - release_ref
  - operator
  - time_range
