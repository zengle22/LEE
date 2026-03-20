---
id: TECH-FEAT-SRC-059-001
ssot_type: tech
title: Fitness Rule Schema 技术架构设计
status: draft
version: v1
parent_id: FEAT-SRC-059-001
derived_from_ids:
  - id: FEAT-SRC-059-001
    version: v1
    required: true
source_refs:
  - FEAT-SRC-059-001
  - ADR-024
  - ADR-015
  - ADR-017
  - ADR-020
owner: governance
tags: [fitness, schema, validation, p0, tech-design]
properties:
  src_root_id: SRC-059
  priority: P0
  delivery_slice: mvp
workflow_instance_id: wf_task_a485b35b
---

# TECH-FEAT-SRC-059-001: Fitness Rule Schema 技术架构设计

## 1. 架构概述

### 1.1 设计目标

本技术设计基于 `FEAT-SRC-059-001` 的冻结需求，定义 `fitness_rule.yaml` 的 JSON Schema 及验证工具的技术实现方案。

核心目标：
- 提供机器可读的 Fitness Rule 描述语言
- 支持 YAML/JSON 双格式输入
- 输出结构化错误信息（行号、字段路径）
- 与 ADR-024 定义的 Fitness Function 定位一致

### 1.2 架构定位

```
┌─────────────────────────────────────────────────────────────┐
│                    LEE 治理体系                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Fitness     │  │ Gate        │  │ Evidence            │ │
│  │ Rule Schema │→ │ (Consumer)  │  │ Pack                │ │
│  │ (本设计)    │  │ (ADR-017)   │  │ (ADR-020)           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Fitness Function Runner                    │
│  │              (ADR-024 完成条件防腐层)                    │
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块技术实现方案

### 2.1 Schema 定义模块 (`fitness_rule.schema.json`)

#### 2.1.1 Schema 结构设计

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://lee-spec.example.com/contracts/fitness-rule/v1/schema.json",
  "title": "Fitness Rule Schema",
  "description": "JSON Schema for Fitness Rule definition (ADR-024)",
  "type": "object",
  "required": [
    "rule_id",
    "rule_type",
    "scan_command",
    "pass_criteria",
    "description"
  ],
  "properties": {
    "rule_id": {
      "type": "string",
      "pattern": "^FIT-[A-Z0-9_-]+$",
      "description": "唯一规则 ID，遵循 LEE ID 命名规范",
      "examples": ["FIT-CONTRACT-CHECK", "FIT-EVIDENCE-COMPLETE"]
    },
    "rule_type": {
      "type": "string",
      "enum": ["hard_gate", "quality_signal"],
      "description": "规则类型：hard_gate 失败阻断，quality_signal 仅警告"
    },
    "scan_command": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": {
          "type": "string",
          "description": "执行扫描的命令或脚本路径"
        },
        "args": {
          "type": "array",
          "items": {"type": "string"},
          "description": "可选的命令行参数"
        },
        "cwd": {
          "type": "string",
          "description": "可选的工作目录"
        },
        "timeout_seconds": {
          "type": "integer",
          "minimum": 1,
          "default": 300,
          "description": "超时时间（秒）"
        }
      }
    },
    "pass_criteria": {
      "type": "object",
      "required": ["kind"],
      "properties": {
        "kind": {
          "type": "string",
          "enum": ["exit_code", "regex_match", "json_path", "file_exists"]
        },
        "exit_code": {
          "type": "integer",
          "default": 0,
          "description": "期望的退出码（当 kind=exit_code 时）"
        },
        "pattern": {
          "type": "string",
          "description": "正则表达式（当 kind=regex_match 时）"
        },
        "json_path": {
          "type": "string",
          "description": "JSONPath 表达式（当 kind=json_path 时）"
        },
        "expected_value": {
          "description": "期望值（用于 json_path 或 regex_match 比对）"
        },
        "file_path": {
          "type": "string",
          "description": "文件路径（当 kind=file_exists 时）"
        }
      },
      "allOf": [
        {
          "if": {"properties": {"kind": {"const": "exit_code"}}},
          "then": {"required": ["exit_code"]}
        },
        {
          "if": {"properties": {"kind": {"const": "regex_match"}}},
          "then": {"required": ["pattern"]}
        },
        {
          "if": {"properties": {"kind": {"const": "json_path"}}},
          "then": {"required": ["json_path", "expected_value"]}
        },
        {
          "if": {"properties": {"kind": {"const": "file_exists"}}},
          "then": {"required": ["file_path"]}
        }
      ]
    },
    "description": {
      "type": "string",
      "description": "规则描述（人读）"
    },
    "dimension": {
      "type": "string",
      "enum": [
        "contract_consistency",
        "testability",
        "integration_closure",
        "evidence_completeness",
        "path_governance"
      ],
      "description": "规则归属的 Fitness 维度（ADR-024 Section 7.2）"
    },
    "severity": {
      "type": "string",
      "enum": ["blocker", "major", "minor", "nit"],
      "default": "blocker",
      "description": "失败严重性（用于 quality_signal 分类）"
    },
    "evidence_binding": {
      "type": "object",
      "properties": {
        "output_file": {
          "type": "string",
          "description": "扫描输出文件路径（用于 Evidence Pack 引用）"
        },
        "artifact_kind": {
          "type": "string",
          "enum": ["runner_output", "command_log", "test_artifact"],
          "description": "证据类型（ADR-020）"
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "owner": {"type": "string"},
        "version": {"type": "string"}
      }
    }
  }
}
```

#### 2.1.2 技术选型理由

| 选型项 | 决策 | 理由 |
|--------|------|------|
| JSON Schema 版本 | Draft 2020-12 | 最新稳定版，支持条件 schema（if/then/else） |
| rule_id 格式 | `FIT-XXX` | 与 LEE 其他 ID 规范（ADR/SRC/FEAT）对齐 |
| rule_type | hard_gate / quality_signal | 直接映射 ADR-024 Section 7.1 |
| dimension | 5 个固定维度 | ADR-024 Section 7.2 定义 |

---

## 3. 输出工件清单

| 工件 | 路径 | 状态 |
|------|------|------|
| `fitness_rule.schema.json` | `spec/contracts/fitness-rule/v1/schema.json` | 待创建 |
| `validate_fitness_rule.py` | `tools/validate_fitness_rule.py` | 待创建 |
| `fitness_rule_example.yaml` | `spec/contracts/fitness-rule/v1/examples/example.yaml` | 待创建 |
| `fitness_rule_example.json` | `spec/contracts/fitness-rule/v1/examples/example.json` | 待创建 |
| `requirements.txt` | `tools/requirements-fitness.txt` | 待创建 |

---

*Generated by dev-tech-design workflow*
*Workflow Instance: wf_task_a485b35b*
*Parent: FEAT-SRC-059-001*
