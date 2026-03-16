---
id: TASK-FEAT-SRC-046-001-002
ssot_type: task
title: SSOTService.release_check() 方法实现
status: draft
version: v1
workflow_instance_id: wf_task_src_046_002
parent_id: FEAT-SRC-046-001
derived_from_ids:
- id: FEAT-SRC-046-001
  version: v1
  required: true
source_refs: []
owner: backend
tags: [service, ssot, release]
properties:
  slice_key: feat_src_046_001_v1
  acceptance:
    - "验证 RELEASE 对象存在"
    - "验证 derived_from_ids 齐备"
    - "验证 DEVPLAN coverage - 所有 FEAT 被覆盖"
    - "验证 TESTPLAN coverage - 所有 FEAT 被覆盖"
    - "验证报告齐备性 (release/test_execution/go_no_go)"
    - "验证 blocker bug 状态"
    - "返回 pass/fail 和详细错误列表"
  estimate: 6h
---

# SSOTService.release_check() 方法实现

## Goal
实现 SSOTService.release_check() 方法，执行 RELEASE 级别的聚合校验。

## User Value
提供 go/no-go 决策支持，确保发布版本满足所有交付条件。

## Inputs
- FEAT-SRC-046-001 冻结规格
- SSOTService 基类代码
- SSOTValidator 校验结果

## Input Contract
required_artifacts:
  - FEAT-SRC-046-001 frozen spec
  - ssot_service.py base code
required_fields:
  - release_id
  - check_rules
  - output_format
consumption_rules:
  - 复用 SSOTValidator 的 P0 规则

## Processing
实现 release_check() 方法，执行以下校验：

### 步骤 1: 验证 RELEASE 存在
```python
release = self.manager.get(release_id)
if not release:
    return {"passed": False, "errors": [f"Release {release_id} not found"]}
```

### 步骤 2: 验证 derived_from_ids 齐备
```python
versioned_refs = _normalize_versioned_refs(props.get("derived_from_ids", []))
if not versioned_refs:
    errors.append(f"{release_id} missing derived_from_ids")
```

### 步骤 3: 获取子对象 (DEVPLAN/TESTPLAN/REPORT)
```python
children = self.manager.registry.get_by_parent(release_id)
devplans = [a for a in children if a.properties.get("ssot_type") == "devplan"]
testplans = [a for a in children if a.properties.get("ssot_type") == "testplan"]
reports = [a for a in children if a.properties.get("ssot_type") == "report"]
```

### 步骤 4: 验证 FEAT coverage
```python
feat_ids = {ref["id"] for ref in versioned_refs if str(ref.get("id", "")).startswith("FEAT-")}
devplan_feat_ids = {ref.get("id") for plan in devplans for ref in ...}
testplan_feat_ids = {ref.get("id") for plan in testplans for ref in ...}

for feat_id in sorted(feat_ids - devplan_feat_ids):
    errors.append(f"{release_id} feat {feat_id} not covered by any DEVPLAN")
for feat_id in sorted(feat_ids - testplan_feat_ids):
    errors.append(f"{release_id} feat {feat_id} not covered by any TESTPLAN")
```

### 步骤 5: 验证报告齐备性
```python
report_kinds = {(report.properties or {}).get("report_kind") for report in reports}
required_report_kinds = {"release", "test_execution", "go_no_go"}
for kind in sorted(required_report_kinds - report_kinds):
    errors.append(f"{release_id} missing report_kind={kind}")
```

### 步骤 6: 验证 blocker bug 状态
```python
for artifact in all_artifacts:
    if artifact.properties.get("ssot_type") != "bug":
        continue
    if bug_props.get("found_in_release") != release_id:
        continue
    if bug_props.get("severity") == "blocker" and bug_props.get("bug_state") not in ("closed", "waived"):
        errors.append(f"{release_id} has blocker bug {artifact.id} not closed")
```

### 步骤 7: 返回结果
```python
return {
    "passed": len(errors) == 0,
    "errors": errors,
    "warnings": warnings,
    "release_id": release_id,
    "devplans": [item.id for item in devplans],
    "testplans": [item.id for item in testplans],
}
```

## Outputs
- SSOTService.release_check() 方法实现
- 单元测试用例

## Acceptance Criteria
- 所有校验规则正确实现
- 单元测试覆盖所有规则
- 返回结构化结果包含 pass/fail/errors/warnings

## Dependencies
- FEAT-SRC-046-001
- SSOTService base class
- TASK-FEAT-SRC-046-001-001 (Validator P0 rules)

## Non Goals
- derive_plans() 方法实现
- UI 展示逻辑
