---
id: FEAT-LEE-SRC-FREEZE-20260313-002
ssot_type: feat
title: 冻结输入元数据合规性验证
status: active
version: v1
parent_id: EPIC-064
derived_from_ids: []
source_refs:
- EPIC-064#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
---

# Goal

验证 frozen_inputs 元数据是否符合预定义 schema，确保数据完整性
# User Value

输入不符合 schema 的元数据时返回明确错误码，标记验证状态为 invalid 但不阻断执行步骤
# Inputs

- frozen_inputs_payload
- schema_definition
- validation_rules
# Processing

- 加载 frozen_inputs schema 定义
- 校验元数据字段完整性
- 生成验证结果报告
- 标记验证状态为 valid 或 invalid
# Outputs

- validation_report
- validation_status
# Acceptance

- 输入不符合 schema 的元数据时验证模块返回明确错误码
- 不阻断执行步骤但标记验证状态为 invalid
- 元数据校验准确率 100%
- 错误码覆盖率达到 100%
# Acceptance Checks

## AC-001

- Scenario: 元数据 schema 合规性验证
- Given: 输入 frozen_inputs 元数据 payload
- When: 执行 schema 验证逻辑
- Then: 系统返回验证结果报告并标记状态为 valid 或 invalid
- Trace Hints: TASK, TESTSET, TECH

## AC-002

- Scenario: 错误码覆盖验证
- Given: 输入包含缺失必填字段的元数据
- When: 执行字段完整性检查
- Then: 系统返回明确错误码标识缺失字段
- Trace Hints: TESTSET, TECH
# Dependencies

- EPIC-LEE-SRC-FREEZE-20260313-001
- FEAT-LEE-SRC-FREEZE-20260313-001
# Non Goals

- 修改元数据结构
- 执行自动批准动作
