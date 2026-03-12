---
id: UI-FEAT-081-001
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
  contract_key: ui_feat_081
  identity_kind: ssot
---

design_specs:
  core_paths:
  - path_id: MAIN-001
    name: 创建正式对象主路径
    flow:
    - 用户执行 lee adr/epic/feat new
    - 显示帮助文案（明确说明治理流程）
    - 启动交互式Workflow Wizard
    - 逐步收集必填/选填字段
    - 实时验证与反馈
    - 创建前确认对话框
    - 成功创建并显示引用ID
  - path_id: ALT-001
    name: 帮助发现路径
    flow:
    - 用户执行 lee --help
    - Workflow Commands分组置顶显示
    - 命令文案包含'通过治理流程'
    - 用户获取命令帮助详情
  - path_id: EXC-001
    name: 异常处理路径
    flow:
    - 用户取消(Ctrl+C) → 优雅退出
    - 验证失败 → 字段级错误反馈 → 重新输入
    - Workflow启动失败 → 诊断信息 → 环境检查建议
  interaction_principles:
  - principle_id: IP-001
    name: 命令命名一致性
    rule: lee <object-type> <action>
    examples:
    - lee adr new
    - lee epic new
    - lee feat new
  - principle_id: IP-002
    name: 帮助系统一致性
    rule: Workflow Commands独立分组，文案包含'通过治理流程'
    requirement: AC-002-001, AC-002-003
  - principle_id: IP-003
    name: 文案风格原则
    rules:
    - 清晰直接：避免技术术语堆砌
    - 行动导向：每条提示告诉用户下一步
    - 透明诚实：明确说明行为后果
  - principle_id: IP-004
    name: 交互反馈原则
    timing:
      immediate: <100ms 响应确认
      short: <1s 操作反馈
      long: '>1s 进度提示'
    visual_modes:
    - spinner(进行中)
    - checkmark(成功)
    - cross(错误)
    - arrow(引导)
  - principle_id: IP-005
    name: 防错原则
    rules:
    - 显式确认：创建前要求用户确认
    - 阻断绕过：命令内部强制调用workflow
    - 环境检查：启动前检查workflow引擎
    - 幂等提示：检测重复创建意图
  critical_states:
  - state_id: STATE-001
    name: MAIN_HELP
    trigger: lee --help
    key_elements:
    - Workflow Commands独立分组置顶
    - 命令文案明确包含'通过治理流程'
    - Emoji视觉标识增强可发现性
    - 底部提示引导深入查看
  - state_id: STATE-002
    name: COMMAND_HELP
    trigger: lee adr new --help
    key_elements:
    - 醒目标题框强调治理流程属性
    - 步骤化描述workflow过程
    - 明确警告提示frozen状态含义
    - 示例覆盖常见使用场景
    - 相关命令链接促进发现
  - state_id: STATE-003
    name: WORKFLOW_RUNNING
    trigger: 用户执行 lee adr new
    key_elements:
    - 清晰的工作流标识[WORKFLOW]
    - 进度指示(Step X/Y)
    - 输入框带视觉引导
    - 占位符文本提示预期内容
    - 底部常驻操作提示
  - state_id: STATE-004
    name: VALIDATION_FEEDBACK
    trigger: 用户输入验证结果
    key_elements:
    - 实时验证，即时反馈
    - 错误信息具体到字段和建议
    - 成功状态有视觉确认
    - 预览最终输出，建立心理预期
  - state_id: STATE-005
    name: CONFIRMATION_DIALOG
    trigger: 信息收集完成，创建前确认
    key_elements:
    - 完整信息汇总展示
    - 明确的警告提示
    - 多选项确认(Y/n/Edit)
    - 提供返回修改的逃生通道
  - state_id: STATE-006
    name: SUCCESS
    trigger: 正式对象创建成功
    key_elements:
    - 庆祝性视觉反馈
    - 核心信息卡片(ID,标题,位置,状态)
    - 下一步操作指引
    - 相关命令快速访问
  - state_id: STATE-007
    name: ERROR
    trigger: 各种异常情况
    key_elements:
    - 明确的错误类型分类
    - 具体的错误原因说明
    - 可执行的解决方案步骤
    - 诊断信息用于问题追踪
  design_decisions:
  - dd_id: DD-001
    decision: CLI作为Workflow优先入口
    choice: lee <object> new 而非 lee new <object>
    rationale: 对象类型优先更符合思维模型，便于后续扩展对象专属子命令
  - dd_id: DD-002
    decision: 强制交互式Workflow
    choice: 命令默认启动交互式wizard，不允许完全静默创建
    rationale: 确保用户理解治理流程，减少误操作
  - dd_id: DD-003
    decision: 帮助文案中明确'治理流程'
    choice: 所有相关帮助文案必须包含'通过治理流程'字样
    rationale: 强化workflow-first心智模型，区分于普通文件创建
  - dd_id: DD-004
    decision: 错误信息的可操作性
    choice: 所有错误必须提供可执行的修复步骤
    rationale: CLI工具无界面引导，错误信息是唯一的帮助渠道
  branch_matrix:
  - entry: lee adr new
    target: ADR记录
    workflow: ADR创建流程
    output: ADR-XXX引用
  - entry: lee epic new
    target: Epic需求
    workflow: Epic创建流程
    output: EPIC-XXX引用
  - entry: lee feat new
    target: Feature需求
    workflow: Feature创建流程
    output: FEAT-XXX引用
  acceptance_checks:
    AC-002-001:
      scenario: workflow-first命令出现在主帮助
      ui_requirements:
      - Workflow Commands分组
      - 命令列表可见
      status: designed
    AC-002-002:
      scenario: 命令启动治理流程
      ui_requirements:
      - 交互式Wizard启动
      - 进度指示
      status: designed
    AC-002-003:
      scenario: 帮助文案说明治理流程
      ui_requirements:
      - 文案包含'通过治理流程'
      - 明确说明将通过治理流程创建正式对象
      status: designed
metadata:
  is_frozen: true
  frozen_at: '2026-03-12T00:00:00Z'
  review_status: approved
  prototype_id: UI-FEAT-081-001
  title: ADR/EPIC/FEAT Workflow-First CLI交互设计
  version: v1.0
