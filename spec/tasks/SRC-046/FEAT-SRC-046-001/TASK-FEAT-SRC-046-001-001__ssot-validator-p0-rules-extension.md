---
id: TASK-FEAT-SRC-046-001-001
ssot_type: task
title: SSOT Validator P0 规则扩展 - 交付链对象校验
status: draft
version: v1
workflow_instance_id: wf_task_src_046_001
parent_id: FEAT-SRC-046-001
derived_from_ids:
- id: FEAT-SRC-046-001
  version: v1
  required: true
source_refs: []
owner: backend
tags: [validator, ssot, p0]
properties:
  slice_key: feat_src_046_001_v1
  acceptance:
    - "RELEASE 对象必须声明 derived_from_ids 且只能 pin FEAT"
    - "DEVPLAN.derived_from_ids 至少包含一个 FEAT"
    - "TESTPLAN.derived_from_ids 必须同时包含 FEAT 和 TESTSET"
    - "TASK 必须有 slice_key"
    - "BUG 必须有 severity 和 source_report_id"
    - "REPORT 必须有 report_kind/subject_id/result/evidence_refs"
    - "RECUT 记录必须包含完整字段"
  estimate: 4h
---

# SSOT Validator P0 规则扩展 - 交付链对象校验

## Goal
扩展 SSOTValidator.validate_p0() 方法，增加对 RELEASE/DEVPLAN/TESTPLAN/TASK/BUG/REPORT 对象的 P0 校验规则。

## User Value
确保交付主链上的所有对象符合治理规范，非法对象被 P0 规则阻断。

## Inputs
- FEAT-SRC-046-001 冻结规格
- SSOTValidator 基类代码
- SSOTType 枚举定义

## Input Contract
required_artifacts:
  - FEAT-SRC-046-001 frozen spec
  - ssot_validator.py base code
required_fields:
  - validation_rules
  - test_cases
consumption_rules:
  - 直接复用 FEAT 规格中的验收标准

## Processing
实现以下 P0 校验规则：

### 规则 R-RELEASE-001: RELEASE 必须声明 derived_from_ids
```python
if ssot_type == SSOTType.RELEASE:
    if not refs:
        result.add_error("RELEASE 必须声明 derived_from_ids")
```

### 规则 R-RELEASE-002: RELEASE derived_from_ids 只能 pin FEAT
```python
for ref in refs:
    if not str(ref.get("id", "")).startswith("FEAT-"):
        result.add_error(f"RELEASE derived_from_ids 只能 pin FEAT，当前为 {ref.get('id')}")
```

### 规则 R-RELEASE-003: RECUT 记录完整性
```python
required_recut_fields = {"recut_id", "reason", "old_refs", "new_refs", "approved_by", "changed_at"}
for recut in properties.get("recuts", []):
    missing = required_recut_fields - set(recut.keys())
    if missing:
        result.add_error(f"RELEASE recut 缺少字段：{', '.join(sorted(missing))}")
```

### 规则 R-DEVPLAN-001: DEVPLAN 必须覆盖至少一个 FEAT
```python
if ssot_type == SSOTType.DEVPLAN:
    if not any(str(ref.get("id", "")).startswith("FEAT-") for ref in refs):
        result.add_error("DEVPLAN.derived_from_ids 至少包含一个 FEAT")
```

### 规则 R-TESTPLAN-001: TESTPLAN 必须同时覆盖 FEAT 和 TESTSET
```python
if ssot_type == SSOTType.TESTPLAN:
    has_feat = any(str(ref.get("id", "")).startswith("FEAT-") for ref in refs)
    has_testset = any(str(ref.get("id", "")).startswith("TESTSET-") for ref in refs)
    if not has_feat or not has_testset:
        result.add_error("TESTPLAN.derived_from_ids 必须同时包含 FEAT 和 TESTSET")
```

### 规则 R-TASK-001: TASK 必须有 slice_key
```python
if ssot_type == SSOTType.TASK:
    if not properties.get("slice_key"):
        result.add_warning("TASK 缺少 slice_key")
```

### 规则 R-BUG-001: BUG 必须有 severity 和 source_report_id
```python
if ssot_type == SSOTType.BUG:
    if not properties.get("severity"):
        result.add_error("BUG 缺少 severity")
    if not properties.get("source_report_id"):
        result.add_error("BUG 缺少 source_report_id")
```

### 规则 R-BUG-002: WAIVED BUG 必须有 waiver 元数据
```python
if properties.get("bug_state") == "waived":
    if not properties.get("waiver_reason") or not properties.get("waiver_approved_by"):
        result.add_error("BUG waived 时必须包含 waiver_reason 和 waiver_approved_by")
```

### 规则 R-REPORT-001: REPORT 必须有核心字段
```python
if ssot_type == SSOTType.REPORT:
    required_fields = ("report_kind", "subject_id", "result")
    for field in required_fields:
        if not properties.get(field):
            result.add_error(f"REPORT 缺少 properties.{field}")
    if "evidence_refs" not in properties:
        result.add_error("REPORT 缺少 properties.evidence_refs")
```

## Outputs
- 扩展后的 SSOTValidator.validate_p0() 方法
- 单元测试用例

## Acceptance Criteria
- 所有 P0 规则正确实现
- 单元测试覆盖所有规则
- 非法对象被正确阻断

## Dependencies
- FEAT-SRC-046-001
- SSOTValidator base class

## Non Goals
- P1 规则实现（由其他 TASK 负责）
- SSOTService 方法实现
