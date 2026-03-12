---
id: UI-FEAT-080-002
ssot_type: ui
title: CLI 命令层级重构 - ssot create 降级
status: active
version: v1
parent_id: FEAT-080
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
  - workflow-first 推荐主路径
  - ssot create 降级阻止路径
  - internal/admin flag 放行路径
  - 分层帮助查看路径
  interaction_principles:
    visibility:
      main_commands: 顶层命令列表，workflow 高亮推荐
      public_subcommands: 子命令列表正常显示
      internal_commands: 折叠分组，需显式查看
      deprecated_commands: 标记 Internal/Deprecated
    permission_check:
      default_deny: 所有内部命令默认拒绝执行
      explicit_allow: 必须携带 --internal 或 --admin flag
      no_cascade: 权限 flag 不级联到子命令
      friendly_error: 拒绝时提供清晰引导而非技术错误
    help_consistency:
      layered_display: 主帮助 → 分组帮助 → 命令帮助
      marking_standard: 内部命令使用 ⚠ 标记
      guided_closure: 每个阻止场景都提供替代方案
      version_sync: 帮助信息与代码同步更新
    output_format:
      success: 结构化输出 + 退出码 0
      blocked: 友好文案 + 引导建议 + 退出码非零
      error: 错误类型 + 消息 + 调试提示
      help: 使用说明 + 示例 + 相关链接
  key_page_states:
  - state_id: S-001
    name: lee --help (主帮助)
    description: 用户查看主帮助信息，ssot create 不在顶层显示
    visual_spec:
      main_commands: 正常字体，workflow 高亮(绿色/粗体)
      internal_section: 灰色/折叠显示，标记 Internal Commands
      ssot_create_visibility: 仅在 Internal 分组显示
    output_template: "LEE - CLI Tool v1.0\n\nUSAGE:\n  lee <command> [options]\n\n\
      MAIN COMMANDS:\n  workflow    Start a new SSOT workflow (推荐)\n  attempt    \
      \ Manage attempts\n  ...\n\nINTERNAL COMMANDS (使用 --internal 查看):\n  ssot create\
      \ Create SSOT object (已降级)\n\nRun 'lee <command> --help' for more information."
  - state_id: S-002
    name: lee ssot create (无 flag - 被阻止)
    description: 普通用户尝试执行降级命令，被阻止并引导至 workflow
    visual_spec:
      error_header: '红色标题 ''Error: ssot create 已降级为内部命令'''
      guided_command: 代码块高亮 lee workflow start
      permission_hint: 灰色提示，列出 --internal 和 --admin 选项
    exit_code: 1
    output_template: "Error: ssot create 已降级为内部命令\n\n此命令已从主入口移至内部维护命令。\n如需创建 SSOT\
      \ 对象，请使用推荐入口:\n\n  lee workflow start\n\n如确需使用此命令，请添加权限 flag:\n  lee ssot create\
      \ --internal <args>   # 内部用户\n  lee ssot create --admin <args>      # 管理员\n\n\
      查看帮助: lee ssot create --help"
  - state_id: S-003
    name: lee ssot create --internal (内部执行)
    description: 内部用户携带 --internal flag 执行，正常执行创建逻辑
    visual_spec:
      execution_output: 标准结构化输出
      success_indicator: 绿色成功提示
    exit_code: 0
    output_template: '[执行 ssot create 逻辑...]


      SSOT 对象创建成功

      ID: ssot_xxxxxx

      Name: xxx

      Created: 2026-03-11

      Status: active'
  - state_id: S-004
    name: lee ssot create --help (内部命令帮助)
    description: 查看降级命令的帮助信息，显著标记为 Internal
    visual_spec:
      warning_icon: 黄色/橙色 ⚠ 警告图标
      internal_badge: 显著 'INTERNAL COMMAND' 标记
      warning_section: 详细说明降级原因和使用限制
    output_template: "⚠ INTERNAL COMMAND\n\nlee ssot create - 创建 SSOT 对象 (仅供内部使用)\n\
      \nUSAGE:\n  lee ssot create [options] <args>\n\nOPTIONS:\n  --internal    内部用户权限验证\n\
      \  --admin       管理员权限验证\n  --help        显示帮助信息\n\nDESCRIPTION:\n  此命令已从推荐入口降级为内部维护命令。\n\
      \  普通用户请使用 lee workflow start 创建 SSOT。\n\nEXAMPLES:\n  lee ssot create --internal\
      \ --name \"my-ssot\"\n  lee ssot create --admin --name \"my-ssot\"\n\nWARNINGS:\n\
      \  - 此命令仅供内部测试和迁移使用\n  - 外部用户使用此命令将被阻止"
  - state_id: S-005
    name: lee ssot --help (子命令帮助)
    description: 查看 ssot 分组的帮助信息，create 命令标记为 Internal
    visual_spec:
      public_commands: 正常显示 [公开]
      internal_command: create 命令标记 [⚠ Internal]
    output_template: "lee ssot - SSOT 对象管理\n\nUSAGE:\n  lee ssot <command> [options]\n\
      \nCOMMANDS:\n  list    列出 SSOT 对象        [公开]\n  get     获取 SSOT 对象详情    [公开]\n\
      \  create  创建 SSOT 对象        [⚠ Internal]\n\nNOTE:\n  ssot create 已降级为内部命令。\n\
      \  使用 lee ssot create --help 查看详情。\n\nRun 'lee ssot <command> --help' for more\
      \ information."
  edge_cases:
  - scenario: 同时使用 --internal 和 --admin
    handling: 接受任意一个，建议使用 --internal
  - scenario: flag 拼写错误
    handling: 提示'未知 flag'，列出可用 flag
  - scenario: 多次执行被阻止
    handling: 每次都返回引导，不缓存拒绝
  - scenario: 子命令权限断裂
    handling: 每个子命令独立校验
  ac_mapping:
  - ac_id: AC-001-001
    state_id: S-001
    validation: ssot create 不在顶层命令列表
  - ac_id: AC-001-002
    state_id: S-002
    validation: 返回引导信息，退出码非零
  - ac_id: AC-001-003
    state_id: S-003
    validation: --internal flag 正常执行
metadata:
  is_frozen: true
  feat_id: FEAT-080
  title: CLI 命令层级重构 - ssot create 降级
  frozen_at: '2026-03-12T00:00:00Z'
  designer: UI/UX Designer (Claude Agent)
  reviewer: 待人类评审
  version: v1.0
