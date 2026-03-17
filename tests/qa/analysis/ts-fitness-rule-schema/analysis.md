# 需求分析报告: Fitness Rule Schema 模块

**模块 ID**: fitness-rule-schema  
**来源 FEAT**: FEAT-SRC-059-001 (frozen)  
**分析日期**: 2026-03-17  
**分析师**: AI Agent  

---

## 1. 执行摘要

本报告基于 FEAT-SRC-059-001 冻结需求和 TECH-FEAT-SRC-059-001 技术设计文档，对 Fitness Rule Schema 模块进行需求分析，提取模块边界和可测试特性，为 Test Set 设计提供输入。

**核心目标**: 定义 fitness_rule.yaml 的 JSON Schema 及验证工具，为治理团队和 AI 执行器提供统一的 fitness 规则描述语言。

---

## 2. 需求文档结构解析

### 2.1 输入工件清单

| 工件类型 | 工件路径 | 状态 | 用途 |
|---------|---------|------|------|
| FEAT Freeze | `spec/requirements/SRC-059/FEAT-SRC-059-001__fitness-rule-schema-dingyi.md` | frozen | 核心需求源 |
| Tech Design | `spec/tech/SRC-059/FEAT-SRC-059-001/TECH-FEAT-SRC-059-001__fitness-rule-schema-jishu-sheji.md` | draft | 技术实现参考 |
| ADR-024 | 架构决策记录 | frozen | Fitness Function 定义 |
| ADR-015 | 架构决策记录 | frozen | Schema 验证规范 |
| ADR-017 | 架构决策记录 | frozen | Gate 语义 |
| ADR-020 | 架构决策记录 | frozen | Evidence Pack |

### 2.2 验收标准提取

| ID | 场景 | Given | When | Then |
|----|------|-------|------|------|
| AC-001 | schema 验证工具验证合法的 fitness rule 文件 | 存在符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证通过且不输出错误，返回零退出码 |
| AC-002 | schema 验证工具检测非法 fitness rule 文件 | 存在不符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证失败并输出结构化错误信息包含行号和字段路径 |
| AC-003 | schema 支持 YAML 和 JSON 双格式 | 存在分别符合 schema 的 YAML 和 JSON 格式规则文件 | 对两种格式文件分别执行验证 | 两种格式均能通过验证 |

### 2.3 决策约束清单

1. **Fitness Rule 必须支持 YAML 和 JSON 两种输入格式**
2. **验证失败时必须输出结构化错误信息，包含行号和字段路径**
3. **rule_type 必须为 hard_gate 或 quality_signal 枚举值**
4. **Schema 版本必须使用 JSON Schema Draft 2020-12**

---

## 3. 模块边界定义

### 3.1 模块概述

```
┌─────────────────────────────────────────────────────────────┐
│              Fitness Rule Schema 模块                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │ Schema Definition│    │ Validation Tool             │    │
│  │                 │    │                             │    │
│  │ • fitness_rule  │    │ • validate_fitness_rule.py  │    │
│  │   .schema.json  │───▶│ • YAML/JSON parser          │    │
│  │                 │    │ • Error formatter           │    │
│  └─────────────────┘    └─────────────────────────────┘    │
│           │                         │                       │
│           ▼                         ▼                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               输出: 结构化验证结果                   │   │
│  │  {valid: bool, errors: [], line_numbers: [],         │   │
│  │   field_paths: [], exit_code: int}                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 模块范围

**范围内 (In Scope)**:
- fitness_rule.schema.json JSON Schema 定义
- validate_fitness_rule.py 验证工具脚本
- YAML 格式规则文件验证
- JSON 格式规则文件验证
- 结构化错误输出（含行号、字段路径）
- rule_type 枚举值校验（hard_gate, quality_signal）
- pass_criteria 多类型条件验证
- rule_id 格式校验（FIT-[A-Z0-9_-]+）

**范围外 (Out of Scope)**:
- 规则执行逻辑实现
- 与现有 gate 规则文件的迁移
- Fitness Function Runner 实现
- Evidence Pack 生成

### 3.3 接口定义

#### 输入接口

| 接口名称 | 格式 | 必需字段 | 约束 |
|---------|------|---------|------|
| fitness_rule.yaml | YAML 1.2 | rule_id, rule_type, scan_command, pass_criteria, description | 符合 JSON Schema Draft 2020-12 |
| fitness_rule.json | JSON | rule_id, rule_type, scan_command, pass_criteria, description | 符合 JSON Schema Draft 2020-12 |

#### 输出接口

| 接口名称 | 类型 | 描述 |
|---------|------|------|
| validation_result | JSON | {valid: bool, errors: array, line_numbers: array, field_paths: array} |
| exit_code | integer | 0 表示成功，非零表示失败 |

### 3.4 字段详细规范

#### 必需字段

| 字段名 | 类型 | 约束 | 描述 |
|-------|------|------|------|
| rule_id | string | Pattern: `^FIT-[A-Z0-9_-]+$` | 唯一规则 ID |
| rule_type | string | Enum: [hard_gate, quality_signal] | 规则类型 |
| scan_command | object | Required: [command] | 扫描命令定义 |
| pass_criteria | object | Required: [kind] | 通过标准定义 |
| description | string | - | 规则描述 |

#### 可选字段

| 字段名 | 类型 | 默认值 | 约束 |
|-------|------|--------|------|
| dimension | string | - | Enum: [contract_consistency, testability, integration_closure, evidence_completeness, path_governance] |
| severity | string | blocker | Enum: [blocker, major, minor, nit] |
| evidence_binding | object | - | 证据绑定配置 |
| metadata | object | - | 元数据信息 |

---

## 4. 可测试特性列表

### 4.1 特性总览

| 特性 ID | 特性名称 | 优先级 | 验收标准映射 |
|--------|---------|--------|-------------|
| TF-001 | Schema 结构完整性验证 | P0 | AC-001 |
| TF-002 | YAML 格式规则文件验证 | P0 | AC-001, AC-002, AC-003 |
| TF-003 | JSON 格式规则文件验证 | P0 | AC-001, AC-002, AC-003 |
| TF-004 | rule_type 枚举值验证 | P0 | AC-002 |
| TF-005 | pass_criteria 类型条件验证 | P1 | AC-001, AC-002 |
| TF-006 | 验证结果输出格式 | P0 | AC-001, AC-002 |
| TF-007 | rule_id 格式验证 | P1 | AC-002 |
| TF-008 | 可选字段验证 | P2 | AC-001 |

### 4.2 特性详细说明

#### TF-001: Schema 结构完整性验证

**描述**: 验证 fitness_rule.schema.json 定义包含所有必需字段

**测试要点**:
1. rule_id 字段存在且符合 FIT-XXX 格式
2. rule_type 字段存在且为枚举值
3. scan_command 字段存在且结构正确
4. pass_criteria 字段存在且支持多类型
5. description 字段存在

**预期输入**: 符合 schema 的合法规则文件
**预期输出**: 验证通过，exit_code = 0

#### TF-002: YAML 格式规则文件验证

**描述**: 验证工具能够正确验证 YAML 格式的 fitness rule 文件

**测试要点**:
1. 合法的 YAML 文件验证通过
2. 非法的 YAML 文件验证失败
3. 错误信息包含行号
4. 错误信息包含字段路径

**测试场景**:
- 场景 1: 完整合法的 YAML 文件
- 场景 2: 缺少必需字段的 YAML 文件
- 场景 3: 字段类型错误的 YAML 文件
- 场景 4: 格式错误的 YAML 文件（语法错误）

#### TF-003: JSON 格式规则文件验证

**描述**: 验证工具能够正确验证 JSON 格式的 fitness rule 文件

**测试要点**:
1. 合法的 JSON 文件验证通过
2. 非法的 JSON 文件验证失败
3. 错误信息包含行号
4. 错误信息包含字段路径

**测试场景**:
- 场景 1: 完整合法的 JSON 文件
- 场景 2: 缺少必需字段的 JSON 文件
- 场景 3: 字段类型错误的 JSON 文件
- 场景 4: 格式错误的 JSON 文件（语法错误）

#### TF-004: rule_type 枚举值验证

**描述**: 验证 rule_type 字段只接受 hard_gate 或 quality_signal

**测试要点**:
1. hard_gate 值被接受
2. quality_signal 值被接受
3. 其他值被拒绝并报告错误

**测试数据**:
- 有效值: "hard_gate", "quality_signal"
- 无效值: "soft_gate", "warning", "error", "", null, 123

#### TF-005: pass_criteria 类型条件验证

**描述**: 验证 pass_criteria 根据 kind 值要求不同的必填字段

**条件矩阵**:

| kind 值 | 必填字段 | 可选字段 |
|---------|---------|---------|
| exit_code | exit_code | - |
| regex_match | pattern | - |
| json_path | json_path, expected_value | - |
| file_exists | file_path | - |

**测试要点**:
1. 每种 kind 值缺少必填字段时验证失败
2. 每种 kind 值包含所有必填字段时验证通过

#### TF-006: 验证结果输出格式

**描述**: 验证验证工具输出符合预期的结构化格式

**成功输出格式**:
```json
{
  "valid": true,
  "errors": [],
  "line_numbers": [],
  "field_paths": []
}
```

**失败输出格式**:
```json
{
  "valid": false,
  "errors": ["error message 1", "error message 2"],
  "line_numbers": [10, 25],
  "field_paths": ["$.rule_type", "$.pass_criteria.kind"]
}
```

**测试要点**:
1. 验证通过时返回零退出码
2. 验证失败时返回非零退出码
3. 错误输出为结构化 JSON
4. 包含行号信息
5. 包含字段路径信息

#### TF-007: rule_id 格式验证

**描述**: 验证 rule_id 符合 FIT-[A-Z0-9_-]+ 格式规范

**测试数据**:
- 有效 ID: "FIT-CONTRACT-CHECK", "FIT-001", "FIT_TEST_1"
- 无效 ID: "fit-lowercase", "ABC-001", "FIT-", "", null

#### TF-008: 可选字段验证

**描述**: 验证可选字段的正确处理

**测试要点**:
1. dimension 字段可选但必须是枚举值
2. severity 字段可选且默认为 blocker
3. evidence_binding 字段可选
4. metadata 字段可选

---

## 5. 风险识别与缓解

### 5.1 技术风险

| 风险 ID | 描述 | 可能性 | 影响 | 缓解措施 |
|--------|------|--------|------|---------|
| RISK-001 | YAML/JSON 格式边界情况处理不当 | 中 | 高 | 测试空文件、嵌套深度过大、特殊字符等边界情况 |
| RISK-002 | 结构化错误信息准确性不足 | 中 | 高 | 确保行号和字段路径与实际错误位置一致 |
| RISK-003 | Schema 条件验证逻辑错误 | 低 | 高 | 验证 if/then/else 条件 schema 的正确应用 |

### 5.2 测试重点建议

1. **优先测试**: YAML/JSON 双格式验证的正确性
2. **优先测试**: 错误信息包含准确的行号和字段路径
3. **重点测试**: 条件 schema（if/then/else）的正确应用
4. **边界测试**: 空文件、超大文件、特殊字符、嵌套深度

---

## 6. 依赖与前置条件

### 6.1 外部依赖

| 依赖项 | 用途 | 状态 |
|-------|------|------|
| JSON Schema Draft 2020-12 | Schema 定义标准 | 已冻结 |
| YAML 1.2 specification | YAML 解析标准 | 已冻结 |

### 6.2 内部依赖

| 依赖项 | 类型 | 状态 |
|-------|------|------|
| EPIC-SRC-059-001 | Parent | frozen |
| ADR-024 | Architecture Decision | frozen |

---

## 7. 结论与建议

### 7.1 关键发现

1. **模块边界清晰**: Fitness Rule Schema 模块专注于 Schema 定义和验证工具，不包含执行逻辑
2. **验收标准明确**: 3 个验收标准覆盖了核心功能验证点
3. **格式支持全面**: 同时支持 YAML 和 JSON 两种格式
4. **错误输出规范**: 要求结构化错误信息包含行号和字段路径

### 7.2 Test Set 设计建议

1. **高优先级测试**:
   - YAML/JSON 双格式验证
   - 错误信息准确性（行号、字段路径）
   - 枚举值验证（rule_type）

2. **中等优先级测试**:
   - 条件字段验证（pass_criteria）
   - rule_id 格式验证

3. **低优先级测试**:
   - 可选字段验证
   - 边界情况处理

---

**报告生成完成**  
*下一步: 基于本分析报告设计具体测试用例*
