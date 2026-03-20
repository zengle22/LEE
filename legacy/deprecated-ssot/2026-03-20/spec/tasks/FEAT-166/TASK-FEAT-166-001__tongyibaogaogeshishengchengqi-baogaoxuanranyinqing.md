---
id: TASK-FEAT-166-001
ssot_type: task
title: 统一报告格式生成器-报告渲染引擎
status: frozen
version: v1
parent_id: FEAT-166
derived_from_ids: []
source_refs:
- FEAT-166#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_166_001
  identity_kind: ssot
frozen_at: '2026-03-12T21:40:15.431512'
---

# Objective

实现report.json与scorecard.md标准化输出

# Description

实现报告数据收集、汇总统计计算、JSON结构化报告生成、Markdown评分卡生成(含雷达图)、历史对比分析功能

## Acceptance Mapping
- FEAT-166 / AC-008-001: JSON报告生成
- FEAT-166 / AC-008-002: Markdown评分卡生成
- FEAT-166 / AC-008-003: 历史对比功能
- FEAT-166 / AC-008-004: 报告生成性能

## Dependencies
- TASK-FEAT-159-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-166
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/chain_testing/reporting
```

## Definition Of Done
- Jinja2模板引擎集成
- JSON Schema验证通过
- 雷达图渲染实现
- 性能测试1000+记录<30秒
- TASK文件已冻结
