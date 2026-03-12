---
id: TECH-FEAT-143-004
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

dependencies:
  runtime:
  - click>=8.1
  - pydantic>=1.10,<2
  - pyyaml>=6.0
  - aiosqlite>=0.19
  development:
  - pytest>=7.0
  - pytest-asyncio
  - mypy>=1.0
