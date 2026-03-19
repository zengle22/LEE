# 需求分析报告：SRC-059 Fitness Function 作为完成条件防腐层

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | SRC-059 |
| 名称 | Fitness Function 作为完成条件防腐层 |
| 分析日期 | 2026-03-18 |
| 分析人员 | 需求分析专家 |
| 关联 EPIC | EPIC-SRC-059-001 |
| 状态 | 分析完成 |

---

## 1. 需求概述

### 1.1 目标

构建统一的 Fitness Runner 执行器，为 LEE 工作流提供集中化的完成条件入口，通过扫描规则文件、执行命令采样、聚合多维度完成条件并产出结构化 fitness_result，解决 agent 将局部完成误判为整体完成的问题，为 Supervisor、Gate 审批者和工程治理团队提供可消费的完成证明。

### 1.2 范围边界

**范围内：**
- 提供集中化完成条件扫描与聚合入口
- 提供 fitness_result 结构化输出格式
- 提供 hard_gate_results 与现有 Gate 语义的对接能力
- 提供 dimension_results 多维度视图
- 提供 fitness_result 回挂到 evidence pack 的能力
- 明确与现有 verifier 与 completion checker 的职责边界
- 为 AI 执行器 (agent) 提供明确的完成信号执行入口

**范围外：**
- 用 Fitness 替代人工 approval 决策
- 用 Fitness 替代需求链测试体系的全部能力
- 冻结最终数据库 schema
- 冻结最终 UI 控制台形态
- 一次性迁移全部历史 gate/verifier/testset 规则
- 承担阻断、升级、审批决策职责（属于 Gate 职责）

---

## 2. 模块边界定义

### 2.1 核心模块划分

```
┌─────────────────────────────────────────────────────────────────┐
│              SRC-059: Fitness Function 完成条件防腐层               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Fitness Rule   │  │  Fitness        │  │  Hard Gate &    │  │
│  │  Schema         │  │  Executor       │  │  Quality Signal │  │
│  │  (FEAT-059-001) │  │  (FEAT-059-002) │  │  (FEAT-059-003) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐                        │
│  │  Fitness Result │  │  CLI & CI       │  │                    │
│  │  Formatter      │  │  Integration    │  │                    │
│  │  (FEAT-059-004) │  │  (FEAT-059-005) │  │                    │
│  └─────────────────┘  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块边界明细

#### 模块 A: Fitness Rule Schema (FEAT-SRC-059-001)

| 属性 | 定义 |
|------|------|
| **模块名称** | Fitness Rule Schema 定义 |
| **功能职责** | 定义 fitness_rule.yaml 的 JSON schema 及验证工具 |
| **输入边界** | fitness_rule.yaml (YAML/JSON), schema 定义 |
| **输出边界** | 验证结果 (通过/失败), 结构化错误信息 |
| **外部依赖** | JSON Schema Draft 2020-12, YAML 1.2 specification |
| **内部依赖** | 无 |

#### 模块 B: Fitness Executor 核心 (FEAT-SRC-059-002)

| 属性 | 定义 |
|------|------|
| **模块名称** | Fitness Executor 核心实现 |
| **功能职责** | 实现 skill.governance.fitness_executor 模块，提供扫描、执行、聚合能力 |
| **输入边界** | rules_dir, rule_files, scan_command |
| **输出边界** | 结构化执行结果 (per-rule + summary), stdout/stderr/exit_code/duration |
| **外部依赖** | Python 3.10+ subprocess module |
| **内部依赖** | Fitness Rule Schema (FEAT-059-001) |

#### 模块 C: Hard Gate & Quality Signal 分层 (FEAT-SRC-059-003)

| 属性 | 定义 |
|------|------|
| **模块名称** | Hard Gate 与 Quality Signal 分层 |
| **功能职责** | 实现规则分层机制，为 Supervisor 和 Gate 审批者提供明确的阻断信号 |
| **输入边界** | rule_type, command_results, dimension_scores |
| **输出边界** | overall_pass, hard_gate_failed, dimension_results |
| **外部依赖** | gate_template.governance.fitness_gate |
| **内部依赖** | Fitness Executor (FEAT-059-002) |

#### 模块 D: Fitness Result 格式化 (FEAT-SRC-059-004)

| 属性 | 定义 |
|------|------|
| **模块名称** | Fitness Result 结构化输出 |
| **功能职责** | 定义 fitness_result.json 的 schema 和输出格式 |
| **输入边界** | aggregated_results, hard_gate_results, dimension_results, evidence_pack_path |
| **输出边界** | fitness_result.json, evidence_links |
| **外部依赖** | evidence pack 存储 |
| **内部依赖** | Fitness Executor (FEAT-059-002), Hard Gate Layering (FEAT-059-003) |

#### 模块 E: CLI & CI 集成 (FEAT-SRC-059-005)

| 属性 | 定义 |
|------|------|
| **模块名称** | CLI 与 CI 集成 |
| **功能职责** | 实现 lee fitness run/validate 命令和 CI 集成 |
| **输入边界** | rules_dir, output_file, CI configuration |
| **输出边界** | fitness_result.json, exit_code, CI execution logs |
| **外部依赖** | GitHub Actions CI/CD |
| **内部依赖** | Fitness Executor (FEAT-059-002), Fitness Result Formatter (FEAT-059-004) |

---

## 3. 可测试特性列表

### 3.1 功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TF-001 | Schema 验证工具验证合法文件 | Fitness Rule Schema | P0 | AC-001: 验证通过且不输出错误，返回零退出码 |
| TF-002 | Schema 验证工具检测非法文件 | Fitness Rule Schema | P0 | AC-002: 验证失败并输出结构化错误信息包含行号和字段路径 |
| TF-003 | Schema 支持 YAML 和 JSON 双格式 | Fitness Rule Schema | P0 | AC-003: 两种格式均能通过验证 |
| TF-004 | 扫描指定目录下的 fitness rule 文件 | Fitness Executor | P0 | AC-001: 返回所有 fitness_rule.yaml 文件的绝对路径列表 |
| TF-005 | 执行规则命令并捕获输出 | Fitness Executor | P0 | AC-002: 返回包含 stdout、stderr、exit_code、duration 的结构化结果 |
| TF-006 | 聚合多个规则的执行结果 | Fitness Executor | P0 | AC-003: 返回包含 per-rule 详情和 summary 统计的结构化输出 |
| TF-007 | hard_gate 失败触发整体阻断 | Hard Gate 分层 | P0 | AC-001: overall_pass=false 且 hard_gate_failed=true |
| TF-008 | quality_signal 失败仅扣分不阻断 | Hard Gate 分层 | P0 | AC-002: overall_pass 不受影响但 dimension_scores 记录扣分 |
| TF-009 | fitness_gate 模板可被下游复用 | Hard Gate 分层 | P0 | AC-003: 模板可被正确导入并提供标准的 gate 接口 |
| TF-010 | 生成符合 schema 的 fitness_result.json | Fitness Result | P0 | AC-001: 生成符合 fitness_result.schema.json 的 JSON 文件 |
| TF-011 | fitness_result 可被现有 gate 语义消费 | Fitness Result | P0 | AC-002: 可正确解析 overall_pass 和 hard_gate_results 字段 |
| TF-012 | evidence_links 支持回挂到 evidence pack | Fitness Result | P0 | AC-003: evidence_links 包含指向 evidence pack 的有效链接 |
| TF-013 | 执行 lee fitness run 命令 | CLI 集成 | P1 | AC-001: 生成 fitness_result.json 并返回零退出码 |
| TF-014 | 执行 lee fitness validate 命令 | CLI 集成 | P1 | AC-002: 验证 schema 并返回验证结果 |
| TF-015 | 执行失败返回非零退出码 | CLI 集成 | P1 | AC-003: 返回非零退出码 |
| TF-016 | CI 模板可在 GitHub Actions 中使用 | CI 集成 | P1 | AC-004: workflow 可正常执行 fitness 检查 |

### 3.2 非功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TNF-001 | 执行性能 | Fitness Executor | P1 | 规则扫描和命令执行在合理时间内完成 (< 30s) |
| TNF-002 | 错误处理 | Fitness Executor | P0 | 命令执行失败时正确捕获异常并记录 |
| TNF-003 | 结果可追溯性 | Fitness Result | P0 | fitness_result 包含 executed_at 和 rules_version |

### 3.3 接口特性

| ID | 特性名称 | 接口类型 | 描述 |
|----|---------|---------|------|
| TI-001 | scan_rules() 接口 | 内部接口 | 扫描指定目录返回 fitness_rule.yaml 文件路径列表 |
| TI-002 | execute_commands() 接口 | 内部接口 | 执行规则命令并捕获 stdout/stderr/exit_code/duration |
| TI-003 | aggregate_results() 接口 | 内部接口 | 聚合多个规则执行结果返回 per-rule + summary 视图 |
| TI-004 | fitness_result schema | 输出接口 | 定义 overall_pass, hard_gate_results, dimension_results 等字段 |
| TI-005 | CLI 命令接口 | 外部接口 | lee fitness run --rules-dir <dir> --output-file <file> |

---

## 4. 需求追溯矩阵

| 需求 ID | 需求描述 | 验收标准 | 可测试特性 | 优先级 |
|---------|---------|---------|-----------|--------|
| FEAT-SRC-059-001 | Fitness Rule Schema 定义 | AC-001~003 | TF-001~003 | P0 |
| FEAT-SRC-059-002 | Fitness Executor 核心实现 | AC-001~003 | TF-004~006 | P0 |
| FEAT-SRC-059-003 | Hard Gate 与 Quality Signal 分层 | AC-001~003 | TF-007~009 | P0 |
| FEAT-SRC-059-004 | Fitness Result 结构化输出 | AC-001~003 | TF-010~012 | P0 |
| FEAT-SRC-059-005 | CLI 与 CI 集成 | AC-001~004 | TF-013~016 | P1 |

---

## 5. 风险评估

| 风险 ID | 风险描述 | 影响程度 | 缓解措施 |
|---------|---------|---------|---------|
| R-001 | 命令执行安全风险 | 高 | 限制可执行命令范围，使用白名单机制，禁止执行危险命令 |
| R-002 | 规则扫描性能问题 | 中 | 实现缓存机制，支持增量扫描，限制递归深度 |
| R-003 | hard_gate/quality_signal 分层逻辑错误 | 高 | 增加边界测试，验证各种组合场景，提供配置验证 |
| R-004 | fitness_result 格式兼容性问题 | 中 | 提供版本号字段，实现向后兼容，增加 schema 验证 |

---

## 6. 测试策略建议

### 6.1 测试类型分布

| 测试类型 | 覆盖范围 | 优先级 |
|---------|---------|--------|
| 单元测试 | 各模块核心逻辑 (scanner, executor, aggregator, layering, formatter) | P0 |
| 集成测试 | 模块间交互、CLI 命令端到端 | P0 |
| 契约测试 | fitness_result schema 验证、gate 语义消费 | P0 |
| 性能测试 | 大规模规则扫描性能 | P1 |
| 安全测试 | 命令执行安全、输入验证 | P0 |

### 6.2 测试数据需求

| 数据类型 | 描述 | 来源 |
|---------|------|------|
| 合法规则文件 | 符合 schema 的 fitness_rule.yaml | 测试工具生成 |
| 非法规则文件 | 不符合 schema 的规则文件（用于负面测试） | 测试工具生成 |
| 模拟命令 | 用于测试命令执行的各种 shell 命令 | 测试工具生成 |
| 执行历史数据 | 用于测试结果聚合的模拟执行结果 | 测试工具生成 |

---

## 7. 结论与建议

### 7.1 关键发现

1. **模块职责清晰**: 5 个 FEAT 模块职责边界明确，形成完整的 fitness function 能力链
2. **验收标准完整**: 每个 FEAT 都有明确的 Given-When-Then 格式验收标准
3. **可追溯性强**: 需求链完整（SRC → EPIC → FEAT → AC → Test Case）
4. **依赖关系合理**: FEAT-001 为基础，FEAT-002/003/004 并行开发，FEAT-005 最后集成

### 7.2 测试重点建议

1. **优先级 P0**: Schema 验证、命令执行、hard_gate 阻断逻辑、fitness_result 格式
2. **核心场景**: 正常执行流程、hard_gate 失败阻断、quality_signal 扣分不阻断
3. **边界场景**: 无效规则文件、命令执行失败、大规模规则扫描

### 7.3 下一步行动

1. 基于本分析报告生成 Test Set 设计资产 (ts-src-059.yaml)
2. 制定详细测试计划
3. 准备测试环境和数据
4. 开发自动化测试脚本

---

*文档生成时间: 2026-03-18T10:59:00+08:00*
