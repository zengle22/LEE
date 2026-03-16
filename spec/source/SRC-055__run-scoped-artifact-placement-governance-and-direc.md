---
id: SRC-055
ssot_type: src
title: Run-Scoped Artifact Placement Governance and Directory Audit
status: active
version: v1
workflow_instance_id: gate-materialize
parent_id: null
derived_from_ids: []
source_refs:
- ADR-021
owner: null
tags: []
properties:
  source_kind: governance_bridge_src
  bridge_context:
    governed_by_adrs:
    - ADR-021
    change_scope: 建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement
      manifest 记录文件落点，新增公共目录审计 agent，并在 requirement-chain-validation 中增加目录审计步骤作为 gate
      阻断条件。
    expected_downstream_objects:
    - EPIC
    - FEAT
    - RELEASE
    - TASK
    acceptance_impact:
    - 每次 workflow 运行可追溯文件落点事实
    - formal 与 non-formal 产物目录规则口径统一
    - 目录审计可复用至其他 workflow
    non_goals:
    - 自动搬运已有错误文件
    - 自动修复历史存量目录问题
    - 用 agent 替代 runtime 进行物理文件写入
    - 修改业务对象主链语义
    - 在本 ADR 中直接定义所有 contract 细节字段
---

# Run-Scoped Artifact Placement Governance and Directory Audit

## 问题陈述

建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest 记录文件落点，新增公共目录审计 agent，并在 requirement-chain-validation 中增加目录审计步骤作为 gate 阻断条件。

## 目标用户

- 产品部门 workflow 执行者、agent 开发者、spec 工程维护者、gate 审批人员

## 业务动因

当前目录规则分散导致文件落点质量不可治理，workflow 运行后无法回答'文件是否放到正确位置'这一基本问题

## 关键约束

- runtime placement policy 作为 formal SSOT 目录真值源
- 公共 placement governance policy 作为 non-formal 产物目录真值源
- artifact-placement-reviewer agent 实现
- placement manifest / audit report contract 定义
- requirement-chain-validation workflow 接入

## Bridge Context

- governed_by_adrs: ADR-021
- change_scope: 建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest 记录文件落点，新增公共目录审计 agent，并在 requirement-chain-validation 中增加目录审计步骤作为 gate 阻断条件。
- expected_downstream_objects: EPIC, FEAT, RELEASE, TASK

## 验收与交付影响

- 每次 workflow 运行可追溯文件落点事实
- formal 与 non-formal 产物目录规则口径统一
- 目录审计可复用至其他 workflow

## 非目标

- 自动搬运已有错误文件
- 自动修复历史存量目录问题
- 用 agent 替代 runtime 进行物理文件写入
- 修改业务对象主链语义
- 在本 ADR 中直接定义所有 contract 细节字段