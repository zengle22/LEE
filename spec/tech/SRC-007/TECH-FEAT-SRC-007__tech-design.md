---
id: TECH-FEAT-SRC-007
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-011
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:54.190681'
workflow_instance_id: wf-tech-feat-src-007__tech-design-20260316
---

shared_input_schema:
  formal_ssot_id:
    type: string
    pattern: ^(FEAT|BUG|TASK|TECH|EPIC|RAW|SRC)-[A-Z0-9]+(-[0-9]+)?$
    description: 正式 SSOT 对象唯一标识符
    validation_rules:
    - SSOT-FMT-001: 必须符合 SSOT ID 命名规范
    - SSOT-EXIST-001: 对应 SSOT 对象必须存在
    - SSOT-STATE-001: 对象状态必须为 frozen 或 active
  source_refs:
    type: array
    items:
      type: string
      pattern: ^[A-Z]+-[A-Z0-9-]+(#[a-z0-9_-]+)?$
    min_items: 1
    description: 需求来源引用列表
    validation_rules:
    - REF-FMT-001: 每个引用必须是合法 SSOT ID 可选带锚点
    - REF-EXIST-001: 每个引用必须对应存在的对象
    - REF-NONEMPTY-001: 至少包含一个来源引用
  governing_adrs:
    type: array
    items:
      type: string
      pattern: ^ADR-[0-9]+$
    min_items: 0
    description: 约束本 workflow 的架构决策记录
    validation_rules:
    - ADR-FMT-001: 每个引用必须是 ADR-XXX 格式
    - ADR-EXIST-001: 每个 ADR 必须存在且状态为 frozen
    - ADR-SCOPE-001: ADR 的影响范围必须包含本 workflow 类型
  repo_context:
    type: object
    required:
    - repo_path
    - branch
    properties:
      repo_path:
        type: string
        description: 代码库相对路径
      branch:
        type: string
        pattern: ^[a-zA-Z0-9/_-]+$
        description: 目标分支名称
      base_commit:
        type: string
        pattern: ^[a-f0-9]{7,40}$
        description: 基准 commit hash (可选)
    validation_rules:
    - REPO-PATH-001: repo_path 必须指向存在的目录
    - REPO-BRANCH-001: branch 必须存在或可创建
  task_refs:
    type: array
    items:
      type: string
      pattern: ^TASK-[A-Z0-9-]+$
    description: 关联的 TASK 对象列表
  acceptance_brief_ref:
    type: string
    description: 验收简报引用路径
  workflow_catalog:
    type: array
    items:
      type: string
    description: Dev workflow 清单 (用于共享规范校验)
