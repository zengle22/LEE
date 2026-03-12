---
id: FEAT-090
ssot_type: feat
title: branch 与 worktree 并行开发下正式 SSOT 编号治理
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003
- ADR-013
owner: codex
tags:
- cli
- workflow
- governance
- ssot
- id
properties: {}
---

# Goal

将 branch / worktree 并行开发下的 SSOT 正式编号治理收敛为 `workflow-first` 模式：分支阶段使用临时 ID，进入 `main` 前由 workflow 统一 formalize 正式 ID，避免 `EPIC / FEAT / ADR` 等顺序型对象在 merge 时发生主键冲突。

# Scope

- 明确默认采用 `workflow-first` 作为公开入口
- 为顺序型正式对象引入临时 ID 创建路径
- 定义 merge / freeze 前的 formalize workflow 阶段
- 支持从临时 ID 到正式 ID 的文件名、front matter 与内部引用重写
- 在 lint / hook / gate 中阻止重复正式 ID 和未 formalize 的临时 ID 进入 `main`
- 保持现有 `lee ssot` CLI、SSOT 文件结构与落盘目录策略兼容

# Non-Goals

- 本阶段不重做全部 SSOT 类型的 ID 体系
- 本阶段不引入新的 workflow runtime 或额外数据库
- 本阶段不处理历史全量回填，只覆盖新增对象与最小迁移路径

# Acceptance

- branch / worktree 中只能创建不会冒充正式顺序号的临时 ID
- merge / freeze 前的 workflow 阶段会统一 formalize 出唯一正式 `EPIC / FEAT / ADR` 编号
- formalize 会同步更新文件名、front matter 和内部引用
- lint / hook / gate 能阻止重复正式 ID 或未 formalize 的临时 ID 进入 `main`
- CLI 帮助或错误提示能明确区分“临时 ID”和“正式 ID”

# Delivery

- `TASK-FEAT-090-001`：临时 ID 创建与 formalize 流程接入
- `TASK-FEAT-090-002`：正式 ID rewrite 与 lint gate 集成
