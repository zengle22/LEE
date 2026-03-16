---
id: TECH-FEAT-SRC-056-001
ssot_type: tech
title: Placement Manifest Schema Technical Design
status: frozen
version: v1
workflow_instance_id: wf_task_f22cbc5e
parent_id: FEAT-SRC-056-001
derived_from_ids:
  - id: FEAT-SRC-056-001
    version: v1
    required: true
source_refs:
  - FEAT-SRC-056-001#delivery
  - ADR-021
owner: product-ai
tags: [placement, manifest, schema, technical-design]
properties:
  src_root_id: SRC-056
  tech_kind: schema_design
  priority: P0
  delivery_slice: mvp
  lifecycle_status: frozen
  design_scope:
    - placement manifest schema structure
    - manifest generation timing
    - manifest consumption API
  architecture_decisions:
    - manifest 采用 YAML 格式作为 machine-readable contract
    - manifest 在 workflow 初始化阶段生成
    - manifest 被 audit agent 和 validator 消费
  interfaces:
    - manifest schema definition
    - manifest generation API
    - manifest consumption API
  dependencies: []
frozen_at: '2026-03-16T14:30:00+08:00'
---

# TECH-FEAT-SRC-056-001: Placement Manifest Schema Technical Design

## 1. 设计概述

本技术设计定义了 placement manifest 的 schema 结构、生成时机和消费方式。

## 2. 架构设计

### 2.1 Manifest Schema 结构

```yaml
manifest_id: <workflow-instance-id>-placement-manifest
run_scope:
  workflow_instance_id: <uuid>
  workflow_id: <workflow.key>
  run_id: <run-sequence>
expected_artifacts:
  - artifact_id: <unique-id>
    artifact_kind: formal_ssot | intermediate | deliverable | evidence
    identity_kind: ssot | bundle | intermediate
    ssot_type: SRC | EPIC | FEAT | TECH | TASK | ...
    placement_key: <placement-policy-key>
    expected_dir: <canonical-directory-path>
    required: true | false
    source_refs: [...]
governing_adrs:
  - ADR-021
placement_rules:
  - rule_id: <rule-id>
    rule_kind: formal_placement | intermediate_placement | deliverable_placement
    description: <rule-description>
    enforced: true | false
```

### 2.2 Manifest 生成时机

- **触发点**: workflow 实例初始化完成后
- **生成器**: runtime placement resolver
- **存储位置**: `.workflow/instance/<instance-id>/placement-manifest.yaml`

### 2.3 Manifest 消费方式

- **Audit Agent**: 读取 manifest 并比对实际文件落点
- **Validator**: 引用 manifest 作为 SSOT 校验的输入
- **Gate**: 使用 audit report 作为决策依据

## 3. 接口设计

### 3.1 Manifest Generation API

```python
def generate_placement_manifest(
    workflow_instance_id: str,
    workflow_context: WorkflowContext
) -> PlacementManifest:
    """Generate placement manifest for workflow run"""
```

### 3.2 Manifest Consumption API

```python
def load_placement_manifest(manifest_path: str) -> PlacementManifest:
    """Load and parse placement manifest"""

def audit_directory(
    manifest: PlacementManifest,
    target_path: str
) -> AuditReport:
    """Audit directory against manifest rules"""
```

## 4. 依赖

- ADR-021: Run-Scoped Artifact Placement Governance
- path_policy.py: ALLOWED_WRITE_PREFIXES / FROZEN_PREFIXES

## 5. 实现约束

- manifest 不包含 runtime 实现代码
- manifest 是 machine-readable contract
- manifest 支持 human-readable 解释
