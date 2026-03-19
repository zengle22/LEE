# 需求分析报告: Fitness Rule Schema 定义

**模块**: fitness-rule-schema  
**目标 FEAT**: FEAT-SRC-059-001  
**父 EPIC**: EPIC-SRC-059-001  
**SRC 根**: SRC-059  
**报告生成时间**: 2026-03-18  
**状态**: frozen

---

## 1. 需求文档溯源

### 1.1 主要输入文档

| 文档类型 | 文档 ID | 标题 | 版本 | 状态 |
|---------|---------|------|------|------|
| FEAT | FEAT-SRC-059-001 | Fitness Rule Schema 定义 | v1 | frozen |
| EPIC | EPIC-SRC-059-001 | Fitness Function 作为完成条件防腐层 | v1 | frozen |
| SRC | SRC-059 | (父级需求源) | - | - |

### 1.2 需求来源引用

- **FEAT 来源**: EPIC-SRC-059-001#feat_candidates.FEAT-SRC-059-001
- **父级派生**: EPIC-SRC-059-001 派生自 SRC-059
- **工作流实例**: wf_task_920cfdae (FEAT), wf_task_311eceb5 (EPIC)

---

## 2. 模块边界定义 (Module Boundary)

### 2.1 模块名称与目标

**模块名称**: Fitness Rule Schema 定义与验证模块

**模块目标**: 
定义 fitness_rule.yaml 的 JSON Schema 及验证工具，为治理团队和 AI 执行器提供统一的 fitness 规则描述语言，使完成条件可被机器扫描和验证。

### 2.2 范围边界 (Scope)

#### ✅ 范围内 (In Scope)

| 组件 | 说明 |
|------|------|
| Schema 定义 | fitness_rule.schema.json - 完整的 JSON Schema 定义 |
| Schema 验证工具 | validate_fitness_rule.py - 支持 YAML/JSON 双格式的验证脚本 |
| 示例规则文件 | fitness_rule_example.yaml / fitness_rule_example.json |
| 结构化错误输出 | 包含行号和字段路径的验证错误报告 |
| 必需字段约束 | rule_id, rule_type, scan_command, pass_criteria, description |

#### ❌ 范围外 (Out of Scope)

| 组件 | 说明 | 归属模块 |
|------|------|----------|
| 规则执行逻辑实现 | fitness rule 的实际执行 | FEAT-SRC-059-002 |
| 与现有 gate 规则文件迁移 | 历史规则迁移适配 | 后续迭代 |
| fitness_result 生成 | 执行结果结构化输出 | FEAT-SRC-059-004 |
| hard_gate 与 quality_signal 分层 | 规则分层机制 | FEAT-SRC-059-003 |
| CLI 与 CI 集成 | lee fitness run 命令 | FEAT-SRC-059-005 |

### 2.3 接口契约 (Interface Contracts)

#### 输入接口

| 属性 | 定义 |
|------|------|
| 支持格式 | YAML 1.2, JSON |
| Schema 位置 | spec/contracts/fitness-rule/v1/schema.json |
| 编码要求 | UTF-8 |

#### 输出接口

| 场景 | 退出码 | 输出 |
|------|--------|------|
| 验证通过 | 0 | 无输出或成功消息 |
| 验证失败 | 非零 | 结构化错误信息 (JSON) |

#### 结构化错误格式

```json
{
  "valid": false,
  "errors": [
    {
      "line": 12,
      "path": "/rule_id",
      "message": "String does not match pattern ^FIT-[A-Z0-9_-]+$"
    }
  ]
}
```

---

## 3. 功能点提取

### 3.1 核心功能点

基于 FEAT-SRC-059-001 的处理逻辑，提取以下功能点：

| 功能点 ID | 功能描述 | 优先级 | 对应输出 |
|-----------|----------|--------|----------|
| FP-001 | 设计 fitness_rule.yaml 的 JSON schema 结构 | P0 | fitness_rule.schema.json |
| FP-002 | 定义 rule_id 字段类型与约束 | P0 | schema 定义 |
| FP-003 | 定义 rule_type 字段枚举约束 | P0 | schema 定义 |
| FP-004 | 定义 scan_command 字段结构 | P0 | schema 定义 |
| FP-005 | 定义 pass_criteria 字段条件类型 | P0 | schema 定义 |
| FP-006 | 实现 schema 验证工具支持 YAML 格式 | P0 | validate_fitness_rule.py |
| FP-007 | 实现 schema 验证工具支持 JSON 格式 | P0 | validate_fitness_rule.py |
| FP-008 | 实现结构化错误输出包含行号 | P0 | 验证工具功能 |
| FP-009 | 实现结构化错误输出包含字段路径 | P0 | 验证工具功能 |
| FP-010 | 提供 YAML 格式示例规则文件 | P1 | fitness_rule_example.yaml |
| FP-011 | 提供 JSON 格式示例规则文件 | P1 | fitness_rule_example.json |

### 3.2 Schema 字段定义

#### 必需字段 (Required Fields)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| rule_id | string | Pattern: `^FIT-[A-Z0-9_-]+$` | 规则唯一标识符 |
| rule_type | string | Enum: [hard_gate, quality_signal] | 规则类型 |
| scan_command | object | 包含 command 字段 | 扫描命令定义 |
| pass_criteria | object | 条件类型相关字段 | 通过条件定义 |
| description | string | MinLength: 1 | 规则描述 |

#### 可选字段 (Optional Fields)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| dimension | string | Enum: [contract_consistency, testability, integration_closure, evidence_completeness, path_governance] | 治理维度 |
| severity | string | Enum: [blocker, major, minor, nit] | 严重级别 |
| evidence_binding | object | 包含 artifact_kind 等 | 证据绑定配置 |
| metadata | object | 任意 KV | 元数据 |

#### 条件字段 (Conditional Fields)

**scan_command 结构:**
```yaml
scan_command:
  command: string (required)
  timeout_seconds: integer (default: 300)
  working_dir: string (optional)
```

**pass_criteria 变体:**

| kind | 必需子字段 | 说明 |
|------|-----------|------|
| exit_code | exit_code: integer | 命令退出码匹配 |
| regex_match | pattern: string | 正则匹配输出 |
| json_path | json_path: string, expected_value: any | JSON Path 值匹配 |
| file_exists | file_path: string | 文件存在检查 |

---

## 4. 验收标准分析

### 4.1 验收标准矩阵

| 验收标准 ID | 场景 | Given | When | Then | 覆盖状态 |
|-------------|------|-------|------|------|----------|
| AC-001 | schema 验证工具验证合法的 fitness rule 文件 | 存在符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证通过且不输出错误，返回零退出码 | 待测试 |
| AC-002 | schema 验证工具检测非法 fitness rule 文件 | 存在不符合 schema 的 fitness_rule.yaml 文件 | 执行 validate_fitness_rule.py 验证该文件 | 验证失败并输出结构化错误信息包含行号和字段路径 | 待测试 |
| AC-003 | schema 支持 YAML 和 JSON 双格式 | 存在分别符合 schema 的 YAML 和 JSON 格式规则文件 | 对两种格式文件分别执行验证 | 两种格式均能通过验证 | 待测试 |

### 4.2 验收标准与功能点映射

```
AC-001 → FP-001, FP-006, FP-007
AC-002 → FP-002, FP-003, FP-004, FP-005, FP-008, FP-009
AC-003 → FP-006, FP-007
```

---

## 5. 可测试特性列表 (Testable Features)

### 5.1 Schema 结构验证特性

| 特性 ID | 特性名称 | 描述 | 优先级 | 测试类型 |
|---------|----------|------|--------|----------|
| TF-SCHEMA-001 | 必需字段验证 | 验证 rule_id, rule_type, scan_command, pass_criteria, description 为必需字段 | P0 | 负面测试 |
| TF-SCHEMA-002 | rule_id 格式验证 | 验证 rule_id 必须符合 pattern `^FIT-[A-Z0-9_-]+$` | P0 | 正/负面测试 |
| TF-SCHEMA-003 | rule_type 枚举验证 | 验证 rule_type 仅允许 hard_gate 或 quality_signal | P0 | 正/负面测试 |
| TF-SCHEMA-004 | dimension 枚举验证 | 验证 dimension 为 5 个固定维度之一 | P1 | 正/负面测试 |
| TF-SCHEMA-005 | severity 枚举验证 | 验证 severity 为 4 个严重级别之一 | P1 | 正/负面测试 |

### 5.2 格式支持特性

| 特性 ID | 特性名称 | 描述 | 优先级 | 测试类型 |
|---------|----------|------|--------|----------|
| TF-FORMAT-001 | YAML 格式支持 | 验证工具可正确解析 YAML 格式的 fitness rule 文件 | P0 | 正面测试 |
| TF-FORMAT-002 | JSON 格式支持 | 验证工具可正确解析 JSON 格式的 fitness rule 文件 | P0 | 正面测试 |
| TF-FORMAT-003 | 非法格式拒绝 | 非法格式应返回验证失败和结构化错误 | P0 | 负面测试 |

### 5.3 错误报告特性

| 特性 ID | 特性名称 | 描述 | 优先级 | 测试类型 |
|---------|----------|------|--------|----------|
| TF-ERROR-001 | 行号信息 | 验证失败时错误报告包含 YAML/JSON 行号 | P0 | 负面测试 |
| TF-ERROR-002 | 字段路径 | 验证失败时错误报告包含字段路径 (JSON Pointer) | P0 | 负面测试 |
| TF-ERROR-003 | 结构化输出 | 错误信息必须为结构化 JSON 格式 | P0 | 负面测试 |

### 5.4 字段约束特性

| 特性 ID | 特性名称 | 描述 | 优先级 | 测试类型 |
|---------|----------|------|--------|----------|
| TF-PASS-001 | exit_code 条件验证 | 当 kind=exit_code 时，必须包含 exit_code 字段 | P1 | 负面测试 |
| TF-PASS-002 | regex_match 条件验证 | 当 kind=regex_match 时，必须包含 pattern 字段 | P1 | 负面测试 |
| TF-PASS-003 | json_path 条件验证 | 当 kind=json_path 时，必须包含 json_path 和 expected_value 字段 | P1 | 负面测试 |
| TF-PASS-004 | file_exists 条件验证 | 当 kind=file_exists 时，必须包含 file_path 字段 | P1 | 负面测试 |
| TF-SCAN-001 | command 字段必需 | scan_command 对象必须包含 command 字段 | P0 | 负面测试 |
| TF-SCAN-002 | timeout 默认值 | timeout_seconds 字段默认值为 300 秒 | P1 | 默认值测试 |
| TF-EVIDENCE-001 | artifact_kind 枚举 | artifact_kind 必须为 3 种证据类型之一 | P2 | 正/负面测试 |

### 5.5 特性优先级分布

```
P0 (核心): 10 项 - 必须实现和测试
P1 (重要): 6 项  - 建议实现和测试
P2 (可选): 1 项  - 条件允许时实现
```

---

## 6. 依赖与约束

### 6.1 外部依赖

| 依赖项 | 版本/要求 | 说明 |
|--------|-----------|------|
| JSON Schema Draft 2020-12 | spec | Schema 定义遵循的规范 |
| YAML 1.2 | spec | YAML 解析遵循的规范 |
| EPIC-SRC-059-001 | v1 frozen | 父级需求文档 |

### 6.2 内部依赖

| 依赖项 | 关系 | 说明 |
|--------|------|------|
| FEAT-SRC-059-002 | 后继 | Schema 定义完成后，执行器实现依赖本模块输出 |
| FEAT-SRC-059-003 | 后继 | 规则分层机制依赖 Schema 定义 |
| FEAT-SRC-059-004 | 后继 | fitness_result 输出格式依赖 Schema 定义 |
| FEAT-SRC-059-005 | 后继 | CLI 集成依赖验证工具 |

### 6.3 约束条件

1. **格式约束**: 必须同时支持 YAML 和 JSON 两种输入格式
2. **枚举约束**: rule_type 必须为 hard_gate 或 quality_signal
3. **错误约束**: 验证失败时必须输出结构化错误信息包含行号和字段路径
4. **退出码约束**: 验证通过返回 0，失败返回非零

---

## 7. 风险评估

### 7.1 技术风险

| 风险项 | 等级 | 说明 | 缓解措施 |
|--------|------|------|----------|
| YAML/JSON 解析一致性 | 中 | 不同解析器对边缘情况处理可能不同 | 使用成熟库，定义明确的测试用例 |
| 行号映射准确性 | 中 | YAML 别名、锚点可能导致行号偏移 | 测试验证行号准确性 |
| Schema 版本兼容性 | 低 | JSON Schema Draft 2020-12 广泛支持 | 明确声明 schema 版本 |

### 7.2 需求风险

| 风险项 | 等级 | 说明 | 缓解措施 |
|--------|------|------|----------|
| 字段约束变更 | 中 | FEAT 处于 frozen 状态，但仍可能变更 | 建立变更追踪机制 |
| 与执行器集成问题 | 中 | Schema 设计与实际执行需求可能不匹配 | 早期与 FEAT-059-002 团队对齐 |

---

## 8. 下一步行动建议

### 8.1 测试设计阶段

1. **Test Set 设计审核** (QA Owner)
   - 审核可测试特性完整性
   - 确认优先级划分合理性
   - 验证与验收标准映射关系

2. **测试用例设计** (Test Designer)
   - 为每个可测试特性设计具体测试用例
   - 生成正/负面测试数据文件
   - 定义预期结果断言

3. **测试数据准备** (Test Data Manager)
   - 创建合法规则文件样本
   - 创建非法规则文件样本（每种错误类型）
   - 建立测试数据版本控制

### 8.2 开发阶段依赖

- 等待 `fitness_rule.schema.json` 实现完成
- 等待 `validate_fitness_rule.py` 实现完成
- 与 Schema 设计团队保持同步

---

## 附录 A: 术语表

| 术语 | 定义 |
|------|------|
| Fitness Rule | 定义完成条件的规则，用于验证工作流是否满足完成标准 |
| hard_gate | 硬性门槛，失败会阻断工作流继续执行 |
| quality_signal | 质量信号，失败仅作为参考不阻断执行 |
| scan_command | 执行扫描/采样的命令定义 |
| pass_criteria | 判定扫描结果是否通过的条件 |
| JSON Pointer | RFC 6901 定义的 JSON 文档路径表示法 |

## 附录 B: 参考文档

1. [FEAT-SRC-059-001](file:///spec/requirements/SRC-059/FEAT-SRC-059-001__fitness-rule-schema-dingyi.md) - Fitness Rule Schema 定义
2. [EPIC-SRC-059-001](file:///spec/requirements/SRC-059/EPIC-SRC-059-001__fitness-function-zuoweiwanchengtiaojianfangfuceng.md) - Fitness Function 作为完成条件防腐层
3. [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/schema) - JSON Schema 规范

---

*报告生成: requirement_analysis_agent*  
*审核状态: 待 QA 审核*
