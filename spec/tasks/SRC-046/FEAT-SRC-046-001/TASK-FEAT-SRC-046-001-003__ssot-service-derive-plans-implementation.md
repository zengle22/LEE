---
id: TASK-FEAT-SRC-046-001-003
ssot_type: task
title: SSOTService.derive_plans() 方法实现
status: draft
version: v1
workflow_instance_id: wf_task_src_046_003
parent_id: FEAT-SRC-046-001
derived_from_ids:
- id: FEAT-SRC-046-001
  version: v1
  required: true
source_refs: []
owner: backend
tags: [service, ssot, devplan, testplan]
properties:
  slice_key: feat_src_046_001_v1
  acceptance:
    - "从 RELEASE.derived_from_ids 提取 FEAT 引用"
    - "为每个 FEAT 创建 slice 定义"
    - "查找 FEAT 关联的 TESTSET 并加入 TESTPLAN 引用"
    - "创建或复用 DEVPLAN 对象"
    - "创建或复用 TESTPLAN 对象"
    - "返回 {devplan_id, testplan_id}"
  estimate: 6h
---

# SSOTService.derive_plans() 方法实现

## Goal
实现 SSOTService.derive_plans() 方法，从 RELEASE scope 派生 DEVPLAN/TESTPLAN 骨架。

## User Value
自动化生成开发计划和测试计划，减少手动创建工作。

## Inputs
- FEAT-SRC-046-001 冻结规格
- SSOTService 基类代码
- RELEASE 对象及其 derived_from_ids

## Input Contract
required_artifacts:
  - FEAT-SRC-046-001 frozen spec
  - ssot_service.py base code
required_fields:
  - release_id
  - slice_definition
  - output_format
consumption_rules:
  - 复用 RELEASE 的 derived_from_ids 作为 scope

## Processing
实现 derive_plans() 方法，执行以下步骤：

### 步骤 1: 获取 RELEASE 对象
```python
release = self.manager.get(release_id)
if not release:
    raise ValueError(f"Release {release_id} not found")
```

### 步骤 2: 提取 FEAT 引用
```python
release_refs = _normalize_versioned_refs(release_props.get("derived_from_ids", []))
feat_refs = [ref for ref in release_refs if str(ref.get("id", "")).startswith("FEAT-")]
if not release_refs:
    raise ValueError(f"Release {release_id} has no derived_from_ids")
```

### 步骤 3: 构建 slices
```python
slices = []
for ref in feat_refs:
    feat_id = ref["id"]
    feat_version = ref["version"]
    slice_key = ref.get("slice_key") or f"{feat_id.lower().replace('-', '_')}_{feat_version.lower()}"
    slices.append({
        "slice_key": slice_key,
        "feat_id": feat_id,
        "feat_version": feat_version,
        "required": bool(ref.get("required", True)),
        "dependencies": [],
    })
```

### 步骤 4: 收集 TESTSET 引用用于 TESTPLAN
```python
testplan_refs: List[Dict[str, object]] = list(feat_refs)
for ref in feat_refs:
    feat_id = ref["id"]
    testsets = [
        artifact for artifact in self.manager.registry.get_by_parent(feat_id)
        if artifact.properties.get("ssot_type") == "testset"
    ]
    for testset in testsets:
        testplan_refs.append({
            "id": testset.id,
            "version": testset.properties.get("version", "v1"),
            "required": bool(ref.get("required", True)),
            "slice_key": slice_key,
        })
```

### 步骤 5: 创建或复用 DEVPLAN
```python
existing_children = self.manager.registry.get_by_parent(release_id)
existing_devplan = next((a for a in existing_children if a.properties.get("ssot_type") == "devplan"), None)

if existing_devplan:
    result["devplan_id"] = existing_devplan.id
else:
    devplan = self.manager.create_ssot(
        ssot_type=SSOTType.DEVPLAN,
        title=f"Dev plan for {release_id}",
        content=f"# Dev plan for {release_id}\n",
        run_id=release.run_id or "plan-derive",
        parent_id=release_id,
        derived_from=feat_refs,
        owner=release_props.get("owner", "delivery"),
        tags=release.tags,
        properties={
            "coverage_summary": f"Derived from {release_id}",
            "slices": slices,
        },
    )
    result["devplan_id"] = devplan.id
```

### 步骤 6: 创建或复用 TESTPLAN
```python
existing_testplan = next((a for a in existing_children if a.properties.get("ssot_type") == "testplan"), None)

if existing_testplan:
    result["testplan_id"] = existing_testplan.id
else:
    testplan = self.manager.create_ssot(
        ssot_type=SSOTType.TESTPLAN,
        title=f"Test plan for {release_id}",
        content=f"# Test plan for {release_id}\n",
        run_id=release.run_id or "plan-derive",
        parent_id=release_id,
        derived_from=testplan_refs,
        owner="qa",
        tags=release.tags,
        properties={
            "coverage_summary": f"Derived from {release_id}",
            "environment_matrix": [release_props.get("target_env", "staging")],
            "slices": slices,
        },
    )
    result["testplan_id"] = testplan.id
```

### 步骤 7: 返回结果
```python
return {
    "devplan_id": devplan_id,
    "testplan_id": testplan_id,
}
```

## Outputs
- SSOTService.derive_plans() 方法实现
- 单元测试用例

## Acceptance Criteria
- 正确从 RELEASE 提取 FEAT scope
- 正确构建 slices
- 正确收集 TESTSET 引用
- 已存在计划时复用，否则创建新对象
- 返回包含 devplan_id 和 testplan_id 的字典

## Dependencies
- FEAT-SRC-046-001
- SSOTService base class
- TASK-FEAT-SRC-046-001-001 (Validator P0 rules)

## Non Goals
- release_check() 方法实现
- UI 展示逻辑
