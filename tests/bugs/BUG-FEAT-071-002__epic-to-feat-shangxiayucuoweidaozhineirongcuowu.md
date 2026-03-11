---
id: BUG-FEAT-071-002
ssot_type: bug
title: epic-to-feat 上下文错位导致 FEAT 内容错误
status: active
version: v1
parent_id: FEAT-071
derived_from_ids:
  - FEAT-071
source_refs:
  - FEAT-071#scope
owner: codex
tags: [workflow, epic-to-feat, ssot, generation-bug]
properties:
  severity: high
  source_report_id: REPORT-FEAT-071-20260311-B
  bug_state: open
---

# Summary

`product.epic-to-feat` 在 workflow `wf_task_c6ab8764` 中虽然引用了 `EPIC-003`，但最终生成的 `FEAT-072` 到 `FEAT-079` 内容却是短信验证码与手机号登录能力，与 `EPIC-003` 的 CLI / Gate 治理主题不一致。

# Impact

- 形成了编号合法但语义错误的正式 FEAT SSOT 文件
- 污染了 `spec/requirements/features` 与 registry
- 说明当前 `epic-to-feat` 在正式物化前缺少“上游 EPIC 语义一致性校验”

# Evidence

- workflow: `wf_task_c6ab8764`
- rendered output workspace:
  - `.workflow/workspace/wf_task_c6ab8764/feat_boundary_design/business_output.yaml`
  - `.workflow/workspace/wf_task_c6ab8764/feat_spec_generation/business_output.yaml`
- wrong artifacts:
  - `FEAT-072` to `FEAT-079`

# Expected

基于 `EPIC-003` 生成的 FEAT 应持续围绕 CLI workflow-first、Gate 三分类、freeze 状态语义和治理约束，不应生成短信/登录业务能力。

# Actual

workflow 使用 `EPIC-003` 作为上游引用，但输出内容漂移到另一条登录业务主题，并被正式物化为 FEAT 文件。

# Follow-up

- 在 `epic-to-feat` 正式写入 FEAT 前增加语义一致性校验
- 将 EPIC 关键主题提取为 machine-checkable summary，校验 FEAT title / goal / acceptance 是否与 EPIC scope 对齐
- 对 freeze_ref / workflow context 绑定增加来源显式性，避免“ID 正确、内容错位”
