---
id: SRC-001
ssot_type: src
title: CLI 命令分层与 SSOT 物化边界治理需求
status: draft
version: v1
parent_id:
derived_from_ids: []
source_refs:
  - ADR-006
owner: governance
tags: [cli, governance, workflow, ssot]
properties:
  source_kind: governance_requirement
---
# Background

LEE 当前同时暴露了 workflow 主入口和 `ssot create` 直写入口。

这使普通使用者可以绕过 review、gate、freeze、source chain 和父子关系约束，直接把正式 SSOT 对象落盘到 `spec/` 与 registry。

# Problem Statement

CLI 命令面缺少正式分层，导致“面向用户的治理入口”和“面向系统的物化原语”被混用。

如果继续把 `ssot create` 当主入口，会持续产生以下问题：

- formal object 可直接生成，但治理链未真正执行
- 编号、父子关系、source refs 一致性依赖人工修复
- workflow 已表达的 review / freeze / approval 约束无法被默认强制
- 文档、demo、测试和实际推荐用法长期分裂

# Target User

- LEE CLI 普通使用者
- 产品与治理链路维护者
- 需要生成 `SRC / EPIC / FEAT / ADR` 的 spec 维护者

# Trigger Context

在为 CLI 分层、gate 三分类、freeze ref 语义等治理项补齐正式需求链时，当前仓库已经暴露出一个架构性缺口：

formal SSOT 的生成仍可通过低层命令直接完成，而不是默认绑定到 workflow。

# Business Motivation

如果不先把 CLI 分层和 SSOT 物化边界治理好，后续围绕 product、architecture、qa 的 formal object 生成都会继续出现“文件存在但治理未完成”的问题。

本需求的目标不是美化命令体验，而是把 formal object 的生成条件收回到 workflow/gate 体系中，使 registry 与 `spec/` 中的对象更可信、更可追溯。

# Constraints

- 不删除底层 `ssot create` 能力，但要将其降级为 internal/admin/maintenance 命令
- 面向用户的创建入口必须走 `lee` 高层命令或 `lee run` workflow
- `ADR` 不直接替代 `SRC`，治理型需求仍需先补薄 `SRC`
- formal SSOT ID 分配应与 freeze / approval 边界对齐
- 变更不能破坏现有 workflow template 与 runtime instance 的边界

# Non-Goals

- 本轮不直接删除旧 demo、旧帮助文案或所有历史命令
- 本轮不规定高层命令最终是否命名为 `adr / epic / feat`
- 本轮不直接设计 runtime 内部全部持久化细节

# Success Criteria

- 普通用户默认从 workflow-first 入口创建 `EPIC / FEAT / ADR`
- `ssot create` 明确降级为维护命令，不再作为推荐主入口
- formal object 的 `source_refs`、父子关系和治理链引用由 workflow 自动继承
- CLI、文档和测试叙事统一为“高层入口负责治理，SSOT 原语负责物化”
