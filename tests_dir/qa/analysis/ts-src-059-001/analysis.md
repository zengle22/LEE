# 需求分析报告：SRC-059-001 Fitness Rule Schema 定义

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | SRC-059-001 |
| 名称 | Fitness Rule Schema 定义 |
| 分析日期 | 2026-03-18 |
| 分析人员 | 需求分析专家 |
| 关联 FEAT | FEAT-SRC-059-001 |
| 父级 EPIC | EPIC-SRC-059-001 |
| 状态 | 分析完成 |

---

## 1. 需求概述

### 1.1 目标

定义 fitness_rule.yaml 的 JSON schema 及验证工具，为治理团队和 AI 执行器提供统一的 fitness 规则描述语言，使完成条件可被机器扫描和验证。

### 1.2 范围边界

**范围内：**
- 设计 fitness_rule.yaml 的 JSON schema 结构
- 定义 rule_id、rule_type、scan_command、pass_criteria 字段的类型与约束
- 实现 schema 验证工具支持 YAML/JSON 双格式
- 实现结构化错误输出包含行号与字段路径

**范围外：**
- 规则执行逻辑实现（属于 FEAT-SRC-059-002）
- 与现有 gate 规则文件的迁移
- hard_gate 与 quality_signal 分层逻辑（属于 FEAT-SRC-059-003）
- fitness_result 结构化输出（属于 FEAT-SRC-059-004）

---

## 2. 模块边界定义

### 2.1 模块架构图

```
┌─────────────────────────────────────────────────────────────┐
│           FEAT-SRC-059-001: Fitness Rule Schema 定义          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Schema Definition │    │   Validation Tool           │ │
│  │   (schema.json)     │    │   (validate_fitness_rule.py)│ │
│  │                     │    │                             │ │
│  │  - rule_id          │    │  - YAML/JSON parser         │ │
│  │  - rule_type        │◄──►│  - Schema validator         │ │
│  │  - scan_command     │    │  - Error formatter          │ │
│  │  - pass_criteria    │    │  - Exit code handler        │ │
│  │  - description      │    │                             │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Example Files     │    │   Output Artifacts          │ │
│  │                     │    │                             │ │
│  │  - example.yaml     │    │  - Validation result        │ │
│  │  - example.json     │    │  - Structured errors        │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块边界明细

#### 输入边界

| 输入类型 | 格式 | 必需性 | 描述 |
|----------|------|--------|------|
| fitness_rule.yaml | YAML | 条件必需 | YAML 格式的规则定义文件 |
| fitness_rule.json | JSON | 条件必需 | JSON 格式的规则定义文件 |
| fitness_rule.schema.json | JSON Schema | 必需 | Schema 定义文件 |

#### 输出边界

| 输出类型 | 格式 | 描述 |
|----------|------|------|
| 验证结果 | Exit Code | 0=通过，非0=失败 |
| 错误信息 | Structured Text | 包含字段路径和行号的结构化错误 |
| 示例文件 | YAML/JSON | 符合 schema 的示例规则文件 |

#### 外部依赖

| 依赖项 | 用途 | 版本要求 |
|--------|------|----------|
| JSON Schema Draft 2020-12 | Schema 定义规范 | Draft 2020-12 |
| YAML 1.2 specification | YAML 解析规范 | 1.2 |

---

## 3. 可测试特性列表

### 3.1 功能特性

| ID | 特性名称 | 验收标准 | 优先级 |
|----|---------|---------|--------|
| TF-001 | Schema 包含所有必需字段 | fitness_rule.schema.json 包含 rule_id, rule_type, scan_command, pass_criteria, description | P0 |
| TF-002 | rule_type 枚举值约束 | rule_type 必须是 hard_gate 或 quality_signal | P0 |
| TF-003 | 验证工具验证合法 YAML 文件 | 对符合 schema 的 YAML 文件返回零退出码 | P0 |
| TF-004 | 验证工具验证合法 JSON 文件 | 对符合 schema 的 JSON 文件返回零退出码 | P0 |
| TF-005 | 验证工具检测缺少必需字段 | 对缺少必需字段的文件返回非零退出码并报告缺失字段 | P0 |
| TF-006 | 验证工具检测非法枚举值 | 对 rule_type 不是 hard_gate/quality_signal 的文件报错 | P0 |
| TF-007 | 错误信息包含字段路径 | 错误输出包含 JSON Path 格式的字段路径（如 $.rule_id） | P0 |
| TF-008 | 错误信息包含行号 | 错误输出包含 YAML/JSON 文件中的具体行号 | P0 |
| TF-009 | 支持 YAML 锚点和引用 | 验证工具能正确解析 YAML 的 &anchor 和 *alias 语法 | P1 |
| TF-010 | 提供 YAML 示例文件 | fitness_rule_example.yaml 存在且符合 schema | P1 |
| TF-011 | 提供 JSON 示例文件 | fitness_rule_example.json 存在且符合 schema | P1 |

### 3.2 非功能特性

| ID | 特性名称 | 描述 | 优先级 |
|----|---------|------|--------|
| TNF-001 | 验证性能 | 单个文件的验证时间 < 1s | P1 |
| TNF-002 | 错误可读性 | 错误信息清晰，便于定位问题 | P0 |
| TNF-003 | Schema 兼容性 | Schema 符合 JSON Schema Draft 2020-12 规范 | P0 |

### 3.3 接口特性

| ID | 接口名称 | 类型 | 描述 |
|----|---------|------|------|
| TI-001 | validate_fitness_rule.py | CLI | 命令行验证工具 |
| TI-002 | fitness_rule.schema.json | Schema | JSON Schema 定义文件 |
| TI-003 | validate() | Python API | Python 接口用于程序化验证 |

---

## 4. 需求追溯矩阵

| 需求 ID | 需求描述 | 验收标准 | 可测试特性 | 优先级 |
|---------|---------|---------|-----------|--------|
| FEAT-SRC-059-001 | Schema 结构定义 | 定义必需字段 | TF-001, TF-002 | P0 |
| FEAT-SRC-059-001 | 验证工具实现 | AC-001 | TF-003, TF-004 | P0 |
| FEAT-SRC-059-001 | 非法文件检测 | AC-002 | TF-005, TF-006, TF-007, TF-008 | P0 |
| FEAT-SRC-059-001 | 双格式支持 | AC-003 | TF-003, TF-004, TF-009 | P0 |

---

## 5. 验收标准分析

### AC-001: Schema 验证工具验证合法的 fitness rule 文件

**Given**: 存在符合 schema 的 fitness_rule.yaml 文件
**When**: 执行 validate_fitness_rule.py 验证该文件
**Then**: 验证通过且不输出错误，返回零退出码

**测试覆盖**: TC-059-001-001, TC-059-001-002, TC-059-001-003

### AC-002: Schema 验证工具检测非法 fitness rule 文件

**Given**: 存在不符合 schema 的 fitness_rule.yaml 文件
**When**: 执行 validate_fitness_rule.py 验证该文件
**Then**: 验证失败并输出结构化错误信息包含行号和字段路径

**测试覆盖**: TC-059-001-004, TC-059-001-005, TC-059-001-006, TC-059-001-010

### AC-003: Schema 支持 YAML 和 JSON 双格式

**Given**: 存在分别符合 schema 的 YAML 和 JSON 格式规则文件
**When**: 对两种格式文件分别执行验证
**Then**: 两种格式均能通过验证

**测试覆盖**: TC-059-001-007, TC-059-001-008, TC-059-001-009

---

## 6. 风险评估

| 风险 ID | 风险描述 | 影响程度 | 缓解措施 |
|---------|---------|---------|---------|
| R-001 | Schema 定义不完整或模糊 | 高 | 基于 EPIC 需求明确定义所有字段约束，提供示例文件 |
| R-002 | YAML/JSON 解析器差异 | 中 | 使用标准库，测试边界情况，明确支持的 YAML 特性 |
| R-003 | 错误信息格式不统一 | 中 | 定义统一的错误输出格式，包含字段路径和行号 |
| R-004 | 与后续 FEAT 的 schema 兼容性问题 | 中 | 设计可扩展的 schema 结构，预留字段扩展能力 |

---

## 7. 测试策略建议

### 7.1 测试类型分布

| 测试类型 | 覆盖范围 | 优先级 |
|---------|---------|--------|
| 单元测试 | Schema 验证逻辑、格式解析、错误格式化 | P0 |
| 契约测试 | Schema 定义验证、示例文件合规性 | P0 |
| 边界测试 | 空文件、超大文件、特殊字符、嵌套深度 | P1 |

### 7.2 测试数据需求

| 数据类型 | 描述 | 来源 |
|---------|------|------|
| 合法规则文件 | 符合 schema 的 YAML/JSON 文件 | 测试工具生成 |
| 非法规则文件 | 缺少字段、错误类型、格式错误 | 测试工具生成 |
| 复杂 YAML 结构 | 锚点、引用、嵌套 | 手工编写 |
| 边界值数据 | 空值、超长字符串、特殊字符 | 测试工具生成 |

---

## 8. 结论与建议

### 8.1 关键发现

1. **模块职责单一**: FEAT-SRC-059-001 专注于 Schema 定义和验证工具，职责边界清晰
2. **验收标准明确**: 3 个 AC 覆盖了验证工具的核心能力（合法文件通过、非法文件检测、双格式支持）
3. **可追溯性强**: 需求链完整（SRC-059 → EPIC-SRC-059-001 → FEAT-SRC-059-001 → AC → Test Case）
4. **依赖关系简单**: 作为 EPIC 的第一个 FEAT，仅依赖 JSON Schema 和 YAML 规范，无内部依赖

### 8.2 测试重点建议

1. **优先级 P0**: 
   - Schema 结构完整性（所有必需字段定义）
   - 验证工具正确识别合法/非法文件
   - 错误信息包含字段路径和行号
   - YAML 和 JSON 双格式支持

2. **边界场景**:
   - 空文件和最小文件
   - 非法 rule_type 值
   - 缺少必需字段
   - YAML 语法错误

### 8.3 下一步行动

1. 基于本分析报告生成 Test Set 设计资产 (ts-src-059-001.yaml) ✓
2. 准备测试数据（合法/非法规则文件）
3. 开发 validate_fitness_rule.py 验证工具
4. 创建 fitness_rule.schema.json Schema 定义
5. 执行测试用例并验证结果

---

*文档生成时间: 2026-03-18T12:19:00+08:00*
*分析对象: FEAT-SRC-059-001*
