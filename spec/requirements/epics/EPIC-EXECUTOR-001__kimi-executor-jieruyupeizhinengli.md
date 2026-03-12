---
id: EPIC-EXECUTOR-001
ssot_type: epic
title: Kimi Executor 接入与配置能力
status: active
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
---

epic_id: EPIC-EXECUTOR-001
title: Kimi Executor 接入与配置能力
goal: 在 LEE 工作流执行框架内建立 Kimi 执行器的标准接入与配置能力，使其成为可显式选择、可配置为默认的执行能力选项，支撑中文场景下的需求分析与代码执行任务，同时严格遵循现有架构复用原则，实现零侵入式执行器扩展。
scope:
- CLI 执行器参数解析与路由：支持 `lee run <wf> --executor kimi` 显式指定执行器
- 配置化默认执行器切换机制：支持通过配置将 Kimi 设置为 coding step 的默认执行器
- Kimi Executor 核心实现：基于 canonical executor 架构实现 Kimi 执行器适配层
- 执行器别名兼容性：兼容 qwen 等现有别名模式，保持一致的用户体验
- 现有工作流零侵入复用：新增 Kimi executor 时不创建平行 workflow 或平行执行链
- 来源追溯性保留：所有执行器配置和调用均可追溯至配置来源
non_goals:
- 不完成 src_to_epic、epic_to_feat、feat_to_delivery_prep 等下游转换流程
- 不设计发布编排、监控、灰度与告警方案
- 不重构其他执行器（如 Claude Code、Codex）的历史实现
- 不新增业务 workflow 模板
- 不替换 Claude Code / Codex 存量实现
- 不包含生产发布、灰度或运维策略设计
- 不修改现有 coding 步骤模板的业务逻辑
success_metrics:
- CLI 显式指定成功率：执行 `lee run <wf> --executor kimi` 时正确路由到 Kimi 执行器的成功率达到 100%
- 配置切换生效时间：修改默认执行器配置后，coding step 在下一次执行时正确切换至 Kimi 的时间小于 1 秒
- 零侵入验证：现有工作流模板在新增 Kimi executor 后无需任何修改即可正常运行
- 架构复用符合度：Kimi executor 实现完全符合 canonical executor 架构规范，通过架构审查
- 别名兼容性：qwen 等现有别名模式与 Kimi 执行器无冲突，共存运行正常
priority: P1
feat_split_principles:
- 按配置层级拆分：CLI 参数解析、配置文件解析、默认值回退链应拆分为独立 FEAT
- 按执行器生命周期拆分：初始化/配置加载、执行器实例化、任务执行、结果返回应分阶段实现
- 按兼容性维度拆分：核心执行器实现、别名映射层、向后兼容适配应独立交付
- 按用户角色拆分：CLI 使用者体验、编码任务执行者配置、系统维护者扩展点应分别验证
- 保持架构一致性：所有 FEAT 必须复用现有 canonical executor 架构，禁止创建平行实现
source_refs:
- PD-SRC-012
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  derived_from: PD-SRC-012
