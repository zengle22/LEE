---
id: UI-FEAT-143-016
ssot_type: ui
title: QA 执行入口规范化 - CLI 交互原型
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
  contract_id: FUIP-20260313-007
  is_frozen: true
  frozen_at: '2026-03-13'
  feat_ref: FEAT-143
  title: QA 执行入口规范化 - CLI 交互原型
  review_status: pending_human_review
  designer_role: 资深 UI/UX 设计师
design_specs:
  interaction_principles:
  - UIP-001 单一入口原则：所有测试执行必须通过 `lee qa execute --task-ref=<task_id>` 发起，无其他旁路入口
  - UIP-002 链路完整原则：必须验证 RELEASE→TESTPLAN→TASK 三级引用链路，缺一不可
  - UIP-003 显式拒绝原则：旁路请求必须明确拒绝并返回规范错误码 (1-5)
  - UIP-004 审计透明原则：每次执行的入口来源、路径链、时间戳、用户必须可追溯
  - UIP-005 渐进校验原则：校验失败时按 task→plan→release 顺序逐级提示，帮助用户定位问题
  - UIP-006 状态可见原则：5 阶段进度反馈必须在每个关键校验节点即时呈现
  - UIP-007 错误前置原则：校验失败时提供清晰的错误定位和修复建议
  - UIP-008 一致性原则：CLI 输出格式、错误码、进度指示器保持统一风格
  core_paths:
  - name: QA 测试执行主路径
    description: 用户通过 CLI 发起测试执行的完整流程，包含 5 个阶段的渐进式校验
    prototype_link: cli://lee-qa-execute/main-flow
    command_syntax: lee qa execute --task-ref=<task_id> [--validate-only] [--json]
      [--verbose]
    critical_states:
    - 'STATE-INIT: 初始状态 - 等待用户输入命令参数'
    - 'STATE-S1: [1/5] 入口校验 - 验证 task_ref 参数存在性和有效性'
    - 'STATE-S2: [2/5] 旁路检测 - 检查 task 是否归属于 TESTPLAN，防止旁路执行'
    - 'STATE-S3: [3/5] 链路校验 - 验证 TESTPLAN 是否归属于 RELEASE，确保链路完整'
    - 'STATE-S4: [4/5] 执行准备 - 初始化执行环境、加载 Registry、分配 execution_id'
    - 'STATE-S5: [5/5] 执行启动 - 测试执行正式开始，移交 ExecutionEngine'
    - 'STATE-SUCCESS: 成功状态 - exit_code=0，显示执行结果摘要和审计 ID'
    - 'STATE-FAILURE: 失败状态 - exit_code=1-5，显示错误详情和修复建议'
  - name: 审计日志查询路径
    description: 用户查询历史执行审计记录，支持多维度过滤
    prototype_link: cli://lee-qa-audit/query-flow
    command_syntax: lee qa audit [--run-id=<id>] [--task-ref=<id>] [--plan-ref=<id>]
      [--release-ref=<id>] [--from=<date>] [--to=<date>]
    critical_states:
    - 'STATE-A1: 查询条件输入 - 支持按 run_id/task_id/testplan_id/release_id/operator 过滤'
    - 'STATE-A2: 结果列表展示 - 显示审计记录摘要 (run_id, task_ref, executed_at, status)'
    - 'STATE-A3: 详情查看 - 展示完整的 SSOT 三轴绑定信息 (RELEASE→TESTPLAN→TASK)'
    - 'STATE-A4: 导出选项 - 支持 JSON/YAML 格式导出审计记录'
  - name: 执行验证模式路径
    description: 使用 --validate-only 时仅执行校验不真正启动测试，用于预检
    prototype_link: cli://lee-qa-execute/validate-only
    command_syntax: lee qa execute --task-ref=<task_id> --validate-only
    critical_states:
    - 'STATE-V1: 执行完整校验链路但不启动实际测试'
    - 'STATE-V2: 返回校验结果摘要，指示是否可以通过'
    - 'STATE-V3: exit_code=0 表示校验通过，exit_code=1-3 表示校验失败'
  secondary_paths_description: '非主路径场景：

    1. 参数缺失场景：用户未提供 --task-ref 时，显示帮助信息并提示必需参数

    2. 验证模式：使用 --validate-only 时仅执行校验不真正启动测试

    3. JSON 输出模式：使用 --json 时输出机器可读的结构化结果

    4. 详细模式：使用 --verbose 时显示调试级别的日志信息

    5. 帮助查询：使用 --help 时显示命令用法和选项说明

    6. 并发执行场景：同一 TASK 并发执行时分配独立 execution_id

    7. 网络异常场景：执行中断时保存进度支持恢复

    8. 权限不足场景：用户无执行权限时返回授权提示'
  component_specs:
    progress_indicator:
      type: staged_progress
      format: '[{current}/{total}] {stage_name}: {status_detail}'
      success_mark: ✓
      error_mark: ✗
      pending_mark: ○
      stages:
      - index: 1
        name: 入口校验
        description: 验证 task_ref 参数存在性和有效性
        error_code: 1
        success_output: '[1/5] ✓ 入口校验通过：task_ref= TASK-001 有效'
        failure_output: '[1/5] ✗ 入口校验失败：{error_detail}

          💡 建议：{suggestion}'
      - index: 2
        name: 旁路检测
        description: 检查 task 是否归属于 TESTPLAN
        error_code: 2
        success_output: '[2/5] ✓ 旁路检测通过：TASK-001 归属于 TESTPLAN-001'
        failure_output: '[2/5] ✗ 旁路检测失败：检测到旁路执行企图

          💡 建议：所有执行必须通过 TESTPLAN->TASK 路径发起'
      - index: 3
        name: 链路校验
        description: 验证 TESTPLAN 是否归属于 RELEASE
        error_code: 3
        success_output: '[3/5] ✓ 链路校验通过：TESTPLAN-001 归属于 RELEASE-001'
        failure_output: '[3/5] ✗ 链路校验失败：{error_detail}

          💡 建议：{suggestion}'
      - index: 4
        name: 执行准备
        description: 初始化执行环境和资源
        error_code: 4
        success_output: '[4/5] ✓ 执行准备完成：execution_id=RUN-20260313-001'
        failure_output: '[4/5] ✗ 执行准备失败：{error_detail}

          💡 建议：{suggestion}'
      - index: 5
        name: 执行启动
        description: 测试执行正式开始
        error_code: 5
        success_output: '[5/5] ✓ 执行启动成功：测试执行已移交 ExecutionEngine'
        failure_output: '[5/5] ✗ 执行启动失败：{error_detail}

          💡 建议：{suggestion}'
    error_messages:
      style: structured
      format: '❌ {stage} 失败：{error_detail}

        💡 建议：{suggestion}

        📋 错误码：{error_code}'
      categories:
      - code: ENTRY-001
        stage: 入口校验
        message: 缺少必需的 task_ref 参数
        suggestion: 使用 --task-ref=<task_id> 指定要执行的任务，例如：lee qa execute --task-ref=TASK-001
      - code: ENTRY-002
        stage: 入口校验
        message: task_ref 不存在或无效
        suggestion: 检查 task_id 是否正确，或确认 task 已定义在 spec/tasks/ 目录中
      - code: ENTRY-003
        stage: 入口校验
        message: task_ref 格式不正确
        suggestion: task_id 应遵循 TASK-XXX 格式，例如 TASK-001
      - code: BYPASS-001
        stage: 旁路检测
        message: 检测到旁路执行企图：task 未归属于任何 TESTPLAN
        suggestion: 确认 task 已在 TESTPLAN 的 tasks 列表中配置
      - code: BYPASS-002
        stage: 旁路检测
        message: 检测到旁路执行企图：task 与 TESTPLAN 的引用关系断裂
        suggestion: 检查 task 的 parent_id 是否指向有效的 TESTPLAN
      - code: CHAIN-001
        stage: 链路校验
        message: 链路校验失败：TESTPLAN 未归属于任何 RELEASE
        suggestion: 确认 testplan 已在 RELEASE 的 testplans 列表中配置
      - code: CHAIN-002
        stage: 链路校验
        message: 链路校验失败：引用的 SSOT 对象不存在
        suggestion: 确认引用的 RELEASE/TESTPLAN/TASK 已在 spec 目录中定义
      - code: CHAIN-003
        stage: 链路校验
        message: 链路校验失败：RELEASE→TESTPLAN→TASK 引用链断裂
        suggestion: 检查三级对象的引用配置是否完整
      - code: EXEC-001
        stage: 执行准备
        message: 执行准备失败：无法初始化执行环境
        suggestion: 检查系统资源是否充足，或联系管理员
      - code: EXEC-002
        stage: 执行准备
        message: 执行准备失败：Registry 同步超时
        suggestion: 检查网络连接，或稍后重试
      - code: EXEC-003
        stage: 执行启动
        message: 执行启动失败：ExecutionEngine 不可用
        suggestion: 检查执行引擎配置，或联系管理员
    exit_codes:
    - code: 0
      meaning: 成功
      description: 测试执行成功启动
    - code: 1
      meaning: 入口校验失败
      description: task_ref 无效、缺失或格式不正确
    - code: 2
      meaning: 旁路阻断
      description: 检测到绕过 TESTPLAN/TASK 的执行企图
    - code: 3
      meaning: 链路校验失败
      description: RELEASE→TESTPLAN→TASK 链路不完整
    - code: 4
      meaning: 执行准备失败
      description: 执行环境初始化或资源加载出错
    - code: 5
      meaning: 执行启动失败
      description: ExecutionEngine 分发失败或内部异常
    help_display:
      usage: lee qa execute --task-ref=<task_id> [选项]
      description: 通过标准执行入口 (RELEASE→TESTPLAN→TASK) 发起测试执行
      required_args:
      - name: --task-ref
        description: 要执行的任务 ID (必需)，格式：TASK-XXX
      optional_args:
      - name: --validate-only
        description: 仅执行校验，不启动实际测试
      - name: --json
        description: 以 JSON 格式输出结果
      - name: --verbose
        description: 显示调试级别的详细日志
      - name: --help
        description: 显示帮助信息
      examples:
      - lee qa execute --task-ref=TASK-001
      - lee qa execute --task-ref=TASK-001 --validate-only
      - lee qa execute --task-ref=TASK-001 --json --verbose
  audit_display_spec:
    description: 审计日志查询的字段定义和查询格式
    fields:
    - name: run_id
      label: 执行 ID
      type: string
      example: RUN-20260313-001
    - name: task_ref
      label: 任务 ID
      type: string
      example: TASK-001
    - name: testplan_ref
      label: 测试计划 ID
      type: string
      example: TESTPLAN-001
    - name: release_ref
      label: 发布 ID
      type: string
      example: RELEASE-001
    - name: feat_id
      label: 特性 ID
      type: string
      example: FEAT-143
    - name: entry_source
      label: 入口来源
      type: string
      example: cli:lee-qa-execute
    - name: path_chain
      label: 路径链
      type: array
      example:
      - RELEASE-001
      - TESTPLAN-001
      - TASK-001
    - name: executed_at
      label: 执行时间
      type: timestamp
      example: '2026-03-13T10:30:00+08:00'
    - name: executor
      label: 操作用户
      type: string
      example: shado
    - name: exit_code
      label: 退出码
      type: integer
      example: 0
    - name: status
      label: 状态
      type: string
      example: success
    query_format: lee qa audit [--run-id=<id>] [--task-ref=<id>] [--plan-ref=<id>]
      [--release-ref=<id>] [--from=<date>] [--to=<date>] [--operator=<user>]
    output_formats:
    - table
    - json
    - yaml
    index_specs:
    - field: run_id
      type: primary_key
    - field: task_ref
      type: btree
    - field: testplan_ref
      type: btree
    - field: release_ref
      type: btree
    - field: executed_at
      type: timestamp
  key_states:
  - id: STATE-INIT
    name: 初始状态
    trigger: 用户输入 lee qa execute 命令
    component: EntryRouter
    ui_feedback: 解析命令参数...
    transitions:
    - STATE-S1
    - STATE-FAILURE(ENTRY-001)
  - id: STATE-S1
    name: 入口校验
    trigger: 参数解析完成
    component: EntryValidator
    ui_feedback: '[1/5] 入口校验中：验证 task_ref...'
    transitions:
    - STATE-S2
    - STATE-FAILURE(ENTRY-002/003)
  - id: STATE-S2
    name: 旁路检测
    trigger: 入口校验通过
    component: BypassBlocker
    ui_feedback: '[2/5] 旁路检测中：检查 task 归属...'
    transitions:
    - STATE-S3
    - STATE-FAILURE(BYPASS-001/002)
  - id: STATE-S3
    name: 链路校验
    trigger: 旁路检测通过
    component: ChainValidator
    ui_feedback: '[3/5] 链路校验中：验证 RELEASE→TESTPLAN→TASK...'
    transitions:
    - STATE-S4
    - STATE-FAILURE(CHAIN-001/002/003)
  - id: STATE-S4
    name: 执行准备
    trigger: 链路校验通过
    component: ExecutionRouter
    ui_feedback: '[4/5] 执行准备中：初始化环境...'
    transitions:
    - STATE-S5
    - STATE-FAILURE(EXEC-001/002)
  - id: STATE-S5
    name: 执行启动
    trigger: 执行准备完成
    component: ExecutionEngine
    ui_feedback: '[5/5] 执行启动：移交 ExecutionEngine...'
    transitions:
    - STATE-SUCCESS
    - STATE-FAILURE(EXEC-003)
  - id: STATE-SUCCESS
    name: 成功状态
    trigger: 执行启动成功
    component: AuditRecorder
    ui_feedback: '✓ 执行启动成功

      执行 ID: RUN-XXX

      审计记录已保存'
    transitions:
    - 终止
  - id: STATE-FAILURE
    name: 失败状态
    trigger: 任一校验阶段失败
    component: ErrorReporter
    ui_feedback: '❌ {stage} 失败：{detail}

      💡 建议：{suggestion}'
    transitions:
    - 终止
  bypass_scenarios:
  - id: BYP-001
    method: 直接调用 runner
    detection: 无 task_ref 参数
    action: 立即阻断，返回 ENTRY-001 错误
    ui_feedback: '❌ 检测到旁路执行企图：缺少 task_ref

      💡 建议：所有执行必须通过 `lee qa execute --task-ref=<task_id>` 发起'
  - id: BYP-002
    method: 旧入口 /api/v1/run
    detection: 路由匹配废弃接口
    action: 返回迁移指引
    ui_feedback: ⚠ 该接口已废弃，请使用新入口：lee qa execute --task-ref=<task_id>
  - id: BYP-003
    method: 脚本层绕过
    detection: 调用栈分析发现非标准入口
    action: 阻断 + 告警
    ui_feedback: '❌ 检测到脚本层绕过企图

      💡 建议：通过标准 CLI 入口发起执行'
  - id: BYP-004
    method: 参数注入攻击
    detection: 参数格式异常 (如 SQL 注入特征)
    action: 安全阻断，记录安全日志
    ui_feedback: '❌ 检测到异常参数，请求已阻断

      🔒 安全日志已记录'
  edge_cases:
  - id: EDGE-001
    name: 自动补全场景
    description: 用户仅提供 task_ref 时自动推导完整链路
    ui_handling: 自动查找 TASK→TESTPLAN→RELEASE 链路，显示推导结果：'自动推导链路：TASK-001 → TESTPLAN-001
      → RELEASE-001'
  - id: EDGE-002
    name: 参数冲突场景
    description: 用户指定参数与自动推导结果冲突
    ui_handling: 显示警告：'⚠ 检测到参数冲突：用户指定的 plan_ref 与 task 归属的 plan 不一致，以 task 归属为准'
  - id: EDGE-003
    name: 并发执行场景
    description: 同一 TASK 并发执行时分配独立 execution_id
    ui_handling: '显示提示：''⚠ 检测到 TASK-001 正在执行中，本次执行将分配独立 execution_id: RUN-XXX-B'''
  - id: EDGE-004
    name: 网络异常场景
    description: 执行中断时保存进度支持恢复
    ui_handling: 显示提示：'⚠ 执行中断，进度已保存。使用 --resume=RUN-XXX 恢复执行'
  - id: EDGE-005
    name: 权限不足场景
    description: 用户无执行权限时返回授权提示
    ui_handling: '显示提示：''❌ 权限不足：您没有执行 TASK-001 的权限

      💡 建议：联系项目管理员申请 QA_EXECUTOR 角色'''
  - id: EDGE-006
    name: Registry 同步延迟场景
    description: 检测到 Registry 过期时自动刷新
    ui_handling: 显示提示：'⚠ Registry 过期，正在同步... 同步完成，继续执行'
ssot_output_contract:
  contract_version: '1.0'
  run_id: ui-design-run-002
  outputs:
  - key: ui
    identity_kind: ssot
    ssot_type: ui
    title: QA 执行入口规范化 - CLI 交互原型
    parent: feat
    implements:
    - FEAT-143
    derived_from:
    - UI-FEAT-143-015
