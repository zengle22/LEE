---
id: TECH-FEAT-SRC-056-002
ssot_type: tech
title: Artifact Placement Reviewer Agent Technical Design
status: frozen
version: v1
workflow_instance_id: wf_task_f22cbc5e
parent_id: FEAT-SRC-056-002
derived_from_ids:
  - id: FEAT-SRC-056-002
    version: v1
    required: true
source_refs:
  - FEAT-SRC-056-002#delivery
  - ADR-021
owner: product-ai
tags: [agent, audit, technical-design]
properties:
  src_root_id: SRC-056
  tech_kind: agent_design
  priority: P0
  delivery_slice: mvp
  lifecycle_status: frozen
  design_scope:
    - agent core module
    - CLI interface
    - Python API
    - audit report schema
  architecture_decisions:
    - agent 模块独立于 runtime
    - 支持 CLI 和 programmatic 两种调用方式
    - audit 结果输出为 machine-readable report
  interfaces:
    - load_manifest(manifest_path) -> Manifest
    - audit(manifest, target_path) -> AuditReport
    - CLI: lee audit --manifest <path> --target <path>
  dependencies:
    - TECH-FEAT-SRC-056-001 (manifest schema)
frozen_at: '2026-03-16T14:30:00+08:00'
---

# TECH-FEAT-SRC-056-002: Artifact Placement Reviewer Agent Technical Design

## 1. 设计概述

本技术设计定义了 artifact placement reviewer agent 的架构、接口和实现方式。

## 2. 架构设计

### 2.1 Agent 模块结构

```
artifact_placement_reviewer/
├── __init__.py
├── core.py           # 核心审计逻辑
├── manifest.py       # Manifest 加载和解析
├── scanner.py        # 目录扫描器
├── reporter.py       # 审计报告生成
└── cli.py            # CLI 接口
```

### 2.2 核心接口

```python
class PlacementAuditor:
    def load_manifest(self, manifest_path: str) -> PlacementManifest
    def scan_directory(self, target_path: str) -> List[FileEntry]
    def audit(self, manifest: PlacementManifest, target_path: str) -> AuditReport
```

### 2.3 CLI 接口

```bash
lee audit --manifest <manifest-path> --target <target-path> [--output <report-path>]
```

## 3. 审计报告 Schema

```yaml
audit_id: <unique-audit-id>
workflow_instance_id: <uuid>
summary:
  total_files: <int>
  compliant_files: <int>
  non_compliant_files: <int>
blockers: []  # blocker 级违规列表
majors: []    # major 级违规列表
minors: []    # minor 级违规列表
misplaced_files:
  - file_path: <path>
    expected_dir: <expected-path>
    actual_dir: <actual-path>
    severity: blocker | major | minor
    reason: <violation-reason>
decision: pass | revise | reject
```

## 4. 依赖

- TECH-FEAT-SRC-056-001: placement manifest schema
- ADR-021: placement governance rules
- path_policy.py: ALLOWED_WRITE_PREFIXES / FROZEN_PREFIXES

## 5. 实现约束

- agent 不自动修复错误文件位置
- agent 不支持修改 runtime 写路径
- agent 输出仅用于审计和 gate 决策
