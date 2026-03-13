# Shared Input Spec

## Status

- State: frozen
- Governing ADR: `ADR-008`
- Canonical Schema: `spec/contracts/shared-input-schema/v1/schema.json`
- Canonical Checklist: `spec/contracts/shared-input-schema/v1/checklist/input_validation_checklist.yaml`

## Purpose

共享输入规范用于统一 Dev 部门所有 canonical workflow 的业务锚点与执行上下文，避免不同模板各自定义输入字段，导致 `formal_ssot_id`、`source_refs`、`governing_adrs`、`repo_context` 漂移。

当前必须绑定该规范的现役模板包括：

- `template.dev.feature_delivery_l2`
- `template.dev.bugfix_delivery_l2`
- `template.dev.tech_design_l3`
- `template.dev.feature_contract_l3`
- `template.dev.feature_be_l3`
- `template.dev.feature_fe_l3`
- `template.dev.feature_integration_l3`
- `template.dev.evidence_pack_l3`

## Schema 定义

共享输入 schema 固定要求 4 个字段：

- `formal_ssot_id`
  作用：唯一标识当前 workflow 处理的正式 SSOT 对象
- `source_refs`
  作用：声明上游事实源和可追溯引用
- `governing_adrs`
  作用：声明本次执行必须服从的 ADR 约束
- `repo_context`
  作用：声明执行仓库、分支和模块上下文

规则摘要：

- `formal_ssot_id` 必须符合 canonical SSOT ID 模式
- `source_refs` 至少 1 条，允许 `#anchor`
- `governing_adrs` 至少 1 条，且必须显式写为 `ADR-*`
- `repo_context.branch` 只能使用 `main`、`master`、`develop`、`codex/*`、`feature/*`、`bugfix/*`

## Validation Checklist

共享输入 checklist 是 schema 的执行层补充，当前冻结检查项如下：

- `formal_ssot_id_present`
- `formal_ssot_id_format`
- `source_refs_present`
- `source_refs_format`
- `governing_adrs_present`
- `governing_adrs_format`
- `repo_context_present`
- `repo_context_branch_rule`

使用规则：

- checklist 不替代 schema
- schema 负责结构合法性
- checklist 负责把必查项显式化，供 review、gate 和 testset 复用

## Usage Guide

在 Dev workflow 中使用共享输入规范时，必须同时满足下面 3 条：

1. template 的 `contracts.shared_input_schema` 必须指向 canonical schema 文件。
2. 运行输入必须提供 4 个共享字段，不允许用 prompt 文本代替。
3. 下游 handoff 只能追加阶段专属字段，不能覆盖共享字段语义。

推荐输入样例：

```yaml
formal_ssot_id: FEAT-SRC-009-011
source_refs:
  - FEAT-SRC-009-011#delivery
  - TECH-FEAT-SRC-009-011-001
governing_adrs:
  - ADR-008
repo_context:
  repo_id: lee
  branch: codex/src009-execution
  module: spec-global/departments/dev
```

## Migration Guide

历史模板迁移到共享输入规范时，按下面顺序处理：

1. 删除模板内局部重复定义的 SSOT 锚点字段。
2. 接入 `contracts.shared_input_schema` 到 canonical schema。
3. 将原模板特有输入收口到阶段专属字段，不要复写共享字段。
4. 为迁移后的模板补测试，至少覆盖 schema 引用和关键必填项。
5. 更新 README 或阶段文档，把共享输入规范列为正式依赖。

不允许的迁移方式：

- 新建第二套“输入规范 v2”
- 继续在旧模板里保留一套平级字段语义
- 通过 reviewer 口头约定替代 schema/checklist

## Test And Review

当前共享输入规范的最小验证资产：

- `tests/unit/test_shared_input_checklist.py`
- `tests/unit/test_shared_input_schema_validation.py`
- `spec/testing/testsets/TESTSET-FEAT-SRC-009-011-001__shared-input-schema-testset.md`

文档评审要求：

- 新增 canonical template 时，必须确认是否绑定共享输入规范
- 若模板不绑定，需要在 ADR 或治理文档中说明例外原因
