---
id: SRC-015
ssot_type: src
title: SRC
status: archived
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
  superseded_by: SRC-016
  superseded_reason: Replaced by the latest ADR-011 source draft retained for downstream cleanup.
frozen_at: '2026-03-12T20:19:28.042819'
---

status: success
iterations_used: 1
changed_files:
- .workflow/workspace/wf_task_8a0c9276/source_normalization/product_goal_analysis.yaml
commands_run:
- cmd: mkdir -p .workflow/workspace/wf_task_8a0c9276/source_normalization
  exit_code: 0
  stdout: ''
test_results:
  passed: 0
  failed: 0
error: null
analysis_summary:
  source_id: ADR-011
  source_title: 需求链一致性测试体系建设
  requirement_category: 治理能力建设类需求
  recommended_priority: P1
  core_goals_count: 4
  primary_users:
  - 治理团队
  - 产品团队
  - 开发团队
  key_constraints:
  - 不替代人工判断
  - 不作为唯一release gate
  main_risks:
  - 语义判断主观性
  - LLM成本控制
normalization_ready: true
next_step: SRC冻结流程
