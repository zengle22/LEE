---
id: TECH-FEAT-SRC-041-001
ssot_type: tech
title: ADR-017 Gate 双轴语义与人工审批技术架构
status: frozen
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-001
derived_from_ids:
- id: FEAT-SRC-041-001
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-001
- ADR-017
owner: null
tags:
- gate
- governance
- architecture
properties:
  contract_key: tech_feat_src_041_001_gate_governance
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-16T00:00:00.000000'
---

# 技术架构概述

## 目标

基于 FEAT-SRC-041-001 的冻结规格，设计并实现 Gate 治理语义归一化的技术架构，包括：
1. `purpose` × `decision_mode` 双轴模型的数据结构与验证逻辑
2. Legacy 分类到双轴模型的收敛映射规则
3. 下游规格不得引入第三分类轴的治理门禁

## 架构原则

- **正交分离**: 职责语义（purpose）与参与方式（decision_mode）保持独立正交
- **向后兼容**: 保留旧分类作为兼容入口，但不作为输出语义
- **可审计性**: 所有决策必须可追溯到具体的 purpose 和 decision_mode
- **Fail-Closed**: 缺失必要信息时默认拒绝而非放行

---

## 核心组件设计

### 1. Gate Definition Schema

```yaml
gate_definition:
  required_fields:
    - gate_id: string
    - purpose: enum[review, approval]
    - decision_mode: enum[auto, conditional_human, human_required]

  optional_fields:
    - legacy_type: string (仅兼容用，禁止作为正式语义)
    - description: string
    - owner: string

  validation_rules:
    - purpose 与 decision_mode 必须有且仅有一个值
    - 禁止引入第三条分类轴来表达 gate 职责或参与方式
```

### 2. 双轴模型允许组合

| purpose | decision_mode | 允许 | 说明 |
|---------|---------------|------|------|
| review | auto | ✅ | 自动化质量检查、静态分析 |
| review | conditional_human | ✅ | 自动化检查 + 条件触发人工复审 |
| review | human_required | ✅ | 纯人工质量审查 |
| approval | auto | ❌ | 禁止自动正式放行（默认治理模型） |
| approval | conditional_human | ❌ | 禁止条件触发正式放行 |
| approval | human_required | ✅ | 唯一允许的 approval 模式 |

### 3. Legacy 映射规则

| legacy_type | purpose | decision_mode | 备注 |
|-------------|---------|---------------|------|
| Auto Gate | review | auto | 仅兼容入口，禁止作为输出语义 |
| Review Gate | review | human_required | 仅兼容入口，禁止作为输出语义 |
| Approval Gate | approval | human_required | 仅兼容入口，禁止作为输出语义 |
| auto_check | review | auto | 仅兼容入口，禁止作为输出语义 |
| human_review | review | human_required | 仅兼容入口，禁止作为输出语义 |
| human_approval | approval | human_required | 仅兼容入口，禁止作为输出语义 |
| human_gate | 需推导 | human_required | 必须显式化 purpose |

### 4. 验证逻辑

```python
def validate_gate_definition(gate_def):
    # 检查必填字段
    assert 'purpose' in gate_def and gate_def['purpose'] in ['review', 'approval']
    assert 'decision_mode' in gate_def and gate_def['decision_mode'] in ['auto', 'conditional_human', 'human_required']

    # 禁止组合检查
    if gate_def['purpose'] == 'approval':
        assert gate_def['decision_mode'] == 'human_required', "approval 必须 human_required"

    # 禁止第三分类轴
    assert 'gate_type' not in gate_def or gate_def.get('legacy_only', False)
```

---

## 运行时集成

### Gate 决策流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Gate Trigger                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Parse Gate Definition                          │
│              - Extract purpose                              │
│              - Extract decision_mode                        │
│              - Validate combination                         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐
    │   auto          │             │ human_required  │
    │   Execute       │             │   Generate      │
    │   Automatically │             │   Context       │
    └─────────────────┘             │   Show CLI      │
                                    │   Wait Input    │
                                    └─────────────────┘
```

---

## 风险与缓解

### 高风险

| 风险 ID | 风险描述 | 缓解措施 |
|---------|----------|----------|
| RISK-001 | 历史 human_gate 无法推导 purpose | 提供 purpose_inference 规则 + 手动指定工具 |
| RISK-002 | 现有 workflow 模板使用旧分类 | 建立自动转换层：workflow 解析时自动映射到双轴模型 |
| RISK-003 | 新旧语义共存导致不一致 | 治理门禁检查，禁止新增旧分类定义 |

### 技术不确定性

| 不确定性 | 描述 | 建议方案 |
|----------|------|----------|
| 数据库 Schema | 是否需要新增列 | 新增 purpose/decision_mode 列，保留 gate_type 兼容 |
| 兼容周期 | 旧分类支持多久 | 永久兼容作为只读入口，不主动废弃 |

---

## 实施泳道

### 后端开发

1. Gate Definition Schema 实现
2. 双轴模型验证逻辑
3. Legacy 映射转换器

### CLI 开发

1. `lee gate list` 增强（显示 purpose/decision_mode）
2. 向后兼容显示 legacy_type（如适用）

### 集成测试

1. 双轴模型组合验证
2. Legacy 映射完整性测试
3. 禁止第三分类轴治理检查

---

## 交付产物

| 产物 | 位置 | 描述 |
|------|------|------|
| Gate Schema | `src/lee/governance/gate_schema.py` | 双轴模型数据结构 |
| Validator | `src/lee/governance/gate_validator.py` | 双轴验证逻辑 |
| Legacy Mapper | `src/lee/governance/legacy_mapper.py` | Legacy 映射转换 |

---

## 决策追溯

```yaml
governing_adrs:
  - ADR-017
decision_refs:
  - purpose 与 decision_mode 双轴模型决策
  - Legacy 分类收敛映射决策
  - 禁止第三分类轴治理决策
```

---

## Acceptance Trace

### AC-FEAT-SRC-041-001-01

- **规格要求**: 新增或收敛后的 gate 定义必须显式声明 purpose 与 decision_mode
- **技术实现**: `gate_definition` schema 强制 required_fields
- **验证点**: `validate_gate_definition()` 函数

### AC-FEAT-SRC-041-001-02

- **规格要求**: 历史分类只能作为兼容映射入口，不能作为输出语义
- **技术实现**: `legacy_mapper.py` 单向映射，禁止反向生成
- **验证点**: 治理门禁检查新增 gate 定义是否包含 legacy_type 作为正式字段
