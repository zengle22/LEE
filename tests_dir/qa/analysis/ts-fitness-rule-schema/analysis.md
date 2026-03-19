# 需求分析报告：fitness-rule-schema 模块

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | fitness-rule-schema |
| 名称 | Fitness Rule Schema 定义 |
| 分析日期 | 2026-03-18 |
| 分析人员 | 需求分析专家 |
| 关联 FEAT | FEAT-SRC-059-001 |
| 关联 EPIC | EPIC-SRC-059-001 |
| 状态 | 分析完成 |

---

## 1. 需求概述

### 1.1 目标

定义 fitness_rule.yaml 的 JSON schema 及验证工具，为治理团队和 AI 执行器提供统一的 fitness 规则描述语言，使完成条件可被机器扫描和验证。

### 1.2 用户价值

为治理团队和 AI 执行器提供统一的 fitness 规则描述语言，使完成条件可被机器扫描和验证。

### 1.3 范围边界

**范围内：**
- 定义 fitness_rule.yaml 的 JSON schema 结构
- 定义 rule_id、rule_type、scan_command、pass_criteria 字段的类型与约束
- 实现 schema 验证工具支持 YAML/JSON 双格式
- 实现结构化错误输出包含行号与字段路径

**范围外：**
- 规则执行逻辑实现
- 与现有 gate 规则文件的迁移

---

## 2. 模块边界定义

### 2.1 模块概述

```
┌─────────────────────────────────────────────────────────────┐
│           fitness-rule-schema (FEAT-SRC-059-001)              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │  Schema 定义      │    │  验证工具         │              │
│  │  (JSON Schema)   │    │  (Validator)     │              │
│  └──────────────────┘    └──────────────────┘              │
│                                                              │
│  输入: YAML/JSON fitness_rule 文件                           │
│  输出: 验证结果 (通过/失败) + 结构化错误信息                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块边界明细

| 属性 | 定义 |
|------|------|
| **模块名称** | Fitness Rule Schema 定义 |
| **功能职责** | 定义 fitness_rule.yaml 的 JSON schema 及验证工具 |
| **输入边界** | fitness_rule.yaml (YAML/JSON 格式), JSON Schema Draft 2020-12 |
| **输出边界** | 验证结果 (通过/失败), 结构化错误信息 (含行号和字段路径) |
| **外部依赖** | JSON Schema Draft 2020-12 specification, YAML 1.2 specification |
| **内部依赖** | 无 |
| **归属治理域** | governance |

### 2.3 数据契约

**必需字段:**
- `rule_id`: 规则唯一标识
- `rule_type`: 规则类型 (hard_gate 或 quality_signal 枚举值)
- `scan_command`: 扫描执行的命令
- `pass_criteria`: 通过标准定义
- `description`: 规则描述

**消费规则:**
- schema 必须支持 YAML 和 JSON 两种输入格式
- rule_type 必须为 hard_gate 或 quality_signal 枚举值
- 验证失败时必须输出结构化错误信息包含行号和字段路径

---

## 3. 可测试特性列表

### 3.1 功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 对应验收标准 |
|----|---------|---------|--------|-------------|
| TF-001 | Schema 验证工具验证合法 YAML 文件 | fitness-rule-schema | P0 | AC-001: 验证通过且不输出错误，返回零退出码 |
| TF-002 | Schema 验证工具验证合法 JSON 文件 | fitness-rule-schema | P0 | AC-003: 两种格式均能通过验证 |
| TF-003 | Schema 验证工具检测非法文件 | fitness-rule-schema | P0 | AC-002: 验证失败并输出结构化错误信息包含行号和字段路径 |
| TF-004 | 验证通过返回零退出码 | fitness-rule-schema | P0 | AC-001: 返回零退出码 |
| TF-005 | 验证失败返回非零退出码 | fitness-rule-schema | P0 | AC-002: 返回非零退出码 |
| TF-006 | 结构化错误信息包含字段路径 | fitness-rule-schema | P0 | AC-002: 错误信息包含字段路径 (如 "$.rule_type") |
| TF-007 | 结构化错误信息包含行号 | fitness-rule-schema | P0 | AC-002: 错误信息包含行号 |

### 3.2 必需字段验证特性

| ID | 特性名称 | 描述 | 优先级 |
|----|---------|------|--------|
| TF-008 | rule_id 字段约束验证 | 验证 rule_id 必填且格式正确 | P0 |
| TF-009 | rule_type 字段枚举验证 | 验证 rule_type 必须为 hard_gate 或 quality_signal | P0 |
| TF-010 | scan_command 字段约束验证 | 验证 scan_command 必填且为有效命令格式 | P0 |
| TF-011 | pass_criteria 字段约束验证 | 验证 pass_criteria 必填且结构正确 | P0 |
| TF-012 | description 字段约束验证 | 验证 description 必填 | P0 |

### 3.3 接口特性

| ID | 特性名称 | 接口类型 | 描述 |
|----|---------|---------|------|
| TI-001 | validate_file() 接口 | 内部接口 | 接收文件路径，返回验证结果和错误信息 |
| TI-002 | validate_content() 接口 | 内部接口 | 接收内容字符串，返回验证结果 |
| TI-003 | Error Formatter 接口 | 内部接口 | 将验证错误格式化为结构化输出 |

### 3.4 输出工件验证

| ID | 特性名称 | 描述 | 优先级 |
|----|---------|------|--------|
| TO-001 | fitness_rule.schema.json 存在性 | 验证 schema 文件已生成 | P0 |
| TO-002 | validate_fitness_rule.py 功能 | 验证验证工具脚本功能完整 | P0 |
| TO-003 | fitness_rule_example.yaml 有效性 | 验证 YAML 示例文件通过验证 | P0 |
| TO-004 | fitness_rule_example.json 有效性 | 验证 JSON 示例文件通过验证 | P0 |

---

## 4. 验收标准映射

### 4.1 验收检查表

| 验收标准 ID | 场景 | Given | When | Then | 可测试特性 |
|------------|------|-------|------|------|-----------|
| AC-001 | schema 验证工具验证合法的 fitness rule 文件 | 存在符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证通过且不输出错误，返回零退出码 | TF-001, TF-004 |
| AC-002 | schema 验证工具检测非法 fitness rule 文件 | 存在不符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证失败并输出结构化错误信息包含行号和字段路径 | TF-003, TF-005, TF-006, TF-007 |
| AC-003 | schema 支持 YAML 和 JSON 双格式 | 存在分别符合 schema 的 YAML 和 JSON 格式规则文件 | 对两种格式文件分别执行验证 | 两种格式均能通过验证 | TF-002 |

### 4.2 需求追溯矩阵

| 需求 ID | 需求描述 | 验收标准 | 可测试特性 | 优先级 |
|---------|---------|---------|-----------|--------|
| FEAT-SRC-059-001 | Fitness Rule Schema 定义 | AC-001 | TF-001, TF-004, TF-008~012 | P0 |
| FEAT-SRC-059-001 | Fitness Rule Schema 定义 | AC-002 | TF-003, TF-005~007 | P0 |
| FEAT-SRC-059-001 | Fitness Rule Schema 定义 | AC-003 | TF-002 | P0 |

---

## 5. 约束条件

### 5.1 决策约束

- Fitness Rule 必须支持 YAML 和 JSON 两种输入格式
- 验证失败时必须输出结构化错误信息，包含行号和字段路径
- rule_type 必须为 hard_gate 或 quality_signal 枚举值

### 5.2 架构约束

- FEAT parentage: FEAT-SRC-059-001
- 归属治理域 (governance domain)

### 5.3 流程约束

- 必须覆盖 FEAT-SRC-059-001 的所有验收标准
- Test Set 必须可被自动化执行

---

## 6. 依赖分析

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| EPIC-SRC-059-001 | 父需求 | Fitness Function 作为完成条件防腐层 |
| JSON Schema Draft 2020-12 | 技术规范 | Schema 定义遵循的规范 |
| YAML 1.2 | 技术规范 | YAML 解析遵循的规范 |

---

## 7. 风险评估

| 风险 ID | 风险描述 | 影响程度 | 缓解措施 |
|---------|---------|---------|---------|
| R-001 | Schema 定义不完整导致验证遗漏 | 高 | 覆盖所有必需字段，增加边界测试 |
| R-002 | 错误信息格式不统一 | 中 | 定义标准错误输出格式，提供错误格式化工具 |
| R-003 | YAML/JSON 双格式兼容性问题 | 中 | 分别对两种格式进行全面测试 |
| R-004 | 行号定位不准确 | 中 | 使用成熟的 YAML/JSON 解析库，验证行号准确性 |

---

## 8. 测试策略建议

### 8.1 测试类型分布

| 测试类型 | 覆盖范围 | 优先级 |
|---------|---------|--------|
| 单元测试 | Schema 验证逻辑、字段约束检查 | P0 |
| 集成测试 | 验证工具端到端流程 | P0 |
| 契约测试 | 输入输出格式、错误信息结构 | P0 |
| 负面测试 | 非法输入处理、错误恢复 | P0 |

### 8.2 测试数据需求

| 数据类型 | 描述 | 来源 |
|---------|------|------|
| 合法 YAML 规则文件 | 符合 schema 的 fitness_rule.yaml | 测试工具生成 |
| 合法 JSON 规则文件 | 符合 schema 的 fitness_rule.json | 测试工具生成 |
| 缺少必需字段的文件 | 用于测试字段约束验证 | 测试工具生成 |
| 无效 rule_type 的文件 | 用于测试枚举值验证 | 测试工具生成 |
| 格式错误的文件 | 用于测试解析错误处理 | 测试工具生成 |

---

## 9. 结论与建议

### 9.1 关键发现

1. **模块职责清晰**: fitness-rule-schema 专注于 schema 定义和验证工具实现
2. **验收标准完整**: 3 个 Given-When-Then 格式验收标准覆盖核心功能
3. **可追溯性强**: 需求链完整（EPIC → FEAT → AC → Testable Feature）
4. **输入输出明确**: 明确的输入契约（YAML/JSON）和输出格式（验证结果+错误信息）

### 9.2 测试重点建议

1. **优先级 P0**: Schema 验证正确性、字段约束检查、错误信息格式
2. **核心场景**: 合法文件验证通过、非法文件正确检测、双格式支持
3. **边界场景**: 缺少必需字段、无效枚举值、格式错误文件

### 9.3 下一步行动

1. 基于本分析报告生成 Test Set 设计资产 (ts-fitness-rule-schema.yaml)
2. 制定详细测试计划
3. 准备测试数据和测试环境
4. 开发自动化测试脚本

---

*文档生成时间: 2026-03-18T11:45:00+08:00*
*基于: FEAT-SRC-059-001 frozen spec*
