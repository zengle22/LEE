---
id: EPIC-SRC-056-001
ssot_type: epic
title: Run-Scoped Artifact Placement Governance and Directory Audit
status: frozen
version: v1
workflow_instance_id: SRC-056
parent_id: SRC-056
derived_from_ids:
- id: SRC-056
  version: v1
  required: true
source_refs:
- SRC-056
owner: null
tags: []
properties:
  src_root_id: SRC-056
frozen_at: '2026-03-16T11:05:38.567201'
---

# Run-Scoped Artifact Placement Governance and Directory Audit

## 目标

建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest、公共目录审计 agent 和 gate 阻断机制，确保每次 workflow 运行产生的所有文件都落到正确目录，使需求链最终校验从'只看语义'升级为'语义 + 目录治理'双重保障。

## 范围

- run-scoped placement manifest contract 设计与实现：为每次 workflow 运行定义预期的文件放置清单
- 公共 artifact-placement-reviewer agent 实现：服务多 workflow 的目录审计能力
- requirement-chain-validation 流程集成目录审计步骤：在最终校验中增加 blocker 级目录检查
- 目录治理规则固化：将目录规则从 prompt 迁移到 runtime placement policy、公共 contract、governance policy 或 validator/gate 逻辑
- 正式 SSOT 文件目录校验：检测正式文件是否误写到 step_workspace 等运行时目录
- 中间产物目录校验：检测中间文件是否误写到 spec/ 或其他正式目录
- 交付件目录治理：检测 review/report/bundle 文件是否写入错误目录并被误当作正式交付件
- gate 阻断机制实现：目录审计不通过时阻断 workflow 继续推进

## 非目标

- 自动搬运已有错误文件到正确目录
- 自动修复历史存量目录问题
- 用 agent 替代 runtime 进行物理文件写入
- 修改业务对象主链语义（SRC/EPIC/FEAT 等）
- 在本 EPIC 中直接定义所有 contract 细节字段（由下游 FEAT 细化）

## 成功标准

- 产品主链运行完成后，目录审计能够准确识别所有正式文件是否位于正确目录
- 目录审计能够准确识别所有中间产物是否位于正确运行时目录
- 正式文件误写到 step_workspace 的检测率达到 100%
- 中间文件误写到 spec/ 或其他正式目录的检测率达到 100%
- review/report/bundle 文件误写检测率达到 100%
- requirement-chain-validation 流程中目录审计步骤作为 blocker 成功阻断不合规运行
- artifact-placement-reviewer agent 能够被多个 workflow 复用
