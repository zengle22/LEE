---
id: EPIC-031
ssot_type: epic
title: Kimi Executor 接入与配置能力
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
frozen_at: '2026-03-12T21:09:42.906670'
---

epic_id: EPIC-012
title: Kimi Executor 接入与配置能力
goal: 在 LEE 工作流执行框架内建立 Kimi 执行器的标准接入与配置能力，使其成为可显式选择、可配置为默认、可追溯、可复用的执行能力选项，支撑中文场景下的需求分析与代码执行任务，同时严格遵循现有架构复用原则，实现零侵入复用现有工作流。
scope:
- CLI 命令入口扩展：支持 `--executor kimi` 参数识别与路由
- 配置系统扩展：支持默认 coding executor 的可配置化切换
- Kimi Executor 实现：基于 canonical executor 架构实现 Kimi 执行器
- 执行器别名兼容：兼容现有 `qwen` 等别名模式的设计
- 来源追溯机制：建立 ADR-014 来源追溯链路
- Runner 集成：复用现有 Runner 与 workflow wiring，不创建独立链路
- 现有步骤模板兼容：确保 coding 步骤模板无需修改即可使用 Kimi 执行器
non_goals:
- 不实现 `src_to_epic`、`epic_to_feat`、`feat_to_delivery_prep` 等下游交付步骤
- 不设计发布编排、监控、灰度与告警方案
- 不重构 Claude Code / Codex / Qwen 等其他执行器的历史实现
- 不新增业务 workflow 模板，严格复用现有模板
- 不替换 Claude Code / Codex 存量实现
- 不创建平行 workflow 或平行执行链
- 不涉及业务功能（如手机号登录、支付流程等）的实现
success_metrics:
- CLI 执行 `lee run <wf> --executor kimi` 成功路由到 Kimi 执行器
- 配置修改后，默认 coding executor 自动切换为 Kimi 且生效
- 现有 coding 步骤模板无需任何修改即可使用 Kimi 执行器
- Kimi 执行器输出格式与现有 executor 兼容
- 零侵入复用现有工作流，不创建平行链路或独立 Runner
- ADR-014 来源追溯链路完整可验证
priority: P1
feat_split_principles:
- 按用户触达面拆分：CLI 入口扩展与配置系统扩展为独立 FEAT
- 按架构层次拆分：Executor 实现、Runner 集成、别名兼容分层实现
- 按验证边界拆分：单元验证、集成验证、端到端场景验证分阶段交付
- 保持最小可行：每个 FEAT 交付后可独立验证，不依赖下游步骤
- 遵循开闭原则：新增执行器不修改现有执行器代码，仅扩展配置与路由
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  source_problem: SRC-012
  traceability:
  - ADR-014
  architecture_constraints:
  - 'C-ARCH-01: 复用 canonical executor 架构'
  - 'C-ARCH-02: 不创建平行 workflow'
  - 'C-ARCH-03: 兼容现有别名模式'
