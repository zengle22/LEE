# Acceptance Briefs

Acceptance Briefs are temporary truth anchors for work that has not yet been promoted into the formal SSOT chain.

Use an Acceptance Brief when:

- the task must continue now
- there is no formal `EPIC / FEAT / TESTSET / ...` object yet
- the work still needs explicit scope, acceptance criteria, and evidence requirements

Do not use Acceptance Briefs to replace formal SSOT objects once they exist.

## Naming

Recommended filename:

`AB-YYYYMMDD-{slug}.md`

## Front Matter

Each Acceptance Brief should start with YAML front matter so that runner preflight can match it reliably.

Minimum recommended fields:

```yaml
---
brief_id: task-login-refactor
title: 登录链路重构
status: active
task_type: refactor
scope_in:
  - 登录接口重构
scope_out:
  - 注册流程
human_gate_required: true
evidence_required:
  - changed_files
  - test_results
---
```

## Required migration intent

Each brief should declare one of:

- `none`
- `future_feat`
- `future_testset`
- `future_module_contract`

Use `_TEMPLATE.md` as the starting point.
