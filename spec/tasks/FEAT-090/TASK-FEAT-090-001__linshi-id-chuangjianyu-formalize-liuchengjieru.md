---
id: TASK-FEAT-090-001
ssot_type: task
title: 临时 ID 创建与 formalize 流程接入
status: active
version: v1
parent_id: FEAT-090
derived_from_ids: []
source_refs:
- FEAT-090#delivery
- ADR-013
owner: null
tags:
- cli
- ssot
- id
- governance
properties: {}
---

# 临时 ID 创建与 formalize 流程接入

- 在 workflow-first 的公开命令面中引入临时 ID 创建入口
- 明确哪些顺序型对象默认走临时 ID 路径
- 增加 merge / freeze 前的 formalize workflow 阶段，在集成边界统一申请正式号
- 保证公开入口下沉到现有 `ArtifactManager / SSOTIDGenerator / placement` 内部路径
- 明确非 `main` 分支默认只生成临时 ID，未 formalize 不得进入 `main`
- 补充命令级验证，避免把临时 ID 误当作正式 ID 使用

## Workflow Mapping

- `workflow.product.task.src_to_epic`
  - 在 `epic_design` 后增加 `epic_identity_prepare`
  - 在 `epic_review` 后、`epic_freeze` 前增加 `epic_identity_formalize`
- `workflow.product.task.epic_to_feat`
  - 在 `feat_spec_generation` 后增加 `feat_identity_prepare`
  - 在 `feat_review` 后、`feat_freeze` 前增加 `feat_identity_formalize`
- `workflow.product.task.feat_to_delivery_prep`
  - 增加前置校验：只接受已 formalize 的 `FEAT`

## Deliverables

- workflow 模板变更草案
- provisional identity 生成逻辑
- freeze 前 formalize 阶段接入
- 分支上下文识别规则
