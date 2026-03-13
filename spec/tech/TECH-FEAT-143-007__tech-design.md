---
id: TECH-FEAT-143-007
ssot_type: tech
title: tech_design
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

运行时依赖:
  python: '>= 3.10'
  pydantic: '>= 2.0'
  sqlite: 内置
项目内依赖:
- SSOT Registry (运行时索引)
- ArtifactManager (对象物化)
- SSOTService (校验服务)
- Lee CLI (命令入口)
- ExecutionEngine (下游执行引擎)
