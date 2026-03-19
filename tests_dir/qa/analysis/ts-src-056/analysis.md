# 需求分析报告：SRC-056 Run-Scoped Artifact Placement Governance and Directory Audit

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | SRC-056 |
| 名称 | Run-Scoped Artifact Placement Governance and Directory Audit |
| 分析日期 | 2026-03-18 |
| 分析人员 | 需求分析专家 |
| 关联 EPIC | EPIC-SRC-056-001 |
| 关联 FEAT | FEAT-SRC-056-001, FEAT-SRC-056-002 |
| 状态 | 分析完成 |

---

## 1. 需求概述

### 1.1 目标

建立一套覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案，通过 run-scoped placement manifest、公共目录审计 agent 和 gate 阻断机制，确保每次 workflow 运行产生的所有文件都落到正确目录，使需求链最终校验从'只看语义'升级为'语义 + 目录治理'双重保障。

### 1.2 范围边界

**范围内：**
- Run-scoped placement manifest contract 设计与实现
- 公共 artifact-placement-reviewer agent 实现
- Requirement-chain-validation 流程集成目录审计步骤
- 目录治理规则固化
- 正式 SSOT 文件目录校验
- 中间产物目录校验
- 交付件目录治理
- Gate 阻断机制实现

**范围外：**
- 自动搬运已有错误文件到正确目录
- 自动修复历史存量目录问题
- 用 agent 替代 runtime 进行物理文件写入
- 修改业务对象主链语义（SRC/EPIC/FEAT 等）
- Runtime manifest 生成实现

---

## 2. 模块边界定义

### 2.1 核心模块划分

```
┌─────────────────────────────────────────────────────────────────┐
│          SRC-056: Run-Scoped Artifact Placement Governance       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Placement Manifest     │  │  Artifact Placement         │  │
│  │  Contract Design        │  │  Reviewer Agent             │  │
│  │  (FEAT-SRC-056-001)     │  │  (FEAT-SRC-056-002)         │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Directory Audit        │  │  Requirement Chain          │  │
│  │  Core Logic             │  │  Validation Integration     │  │
│  │                         │  │                             │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块边界明细

#### 模块 A: Placement Manifest Contract Design (FEAT-SRC-056-001)

| 属性 | 定义 |
|------|------|
| **模块名称** | Placement Manifest Contract Design |
| **功能职责** | 定义 placement manifest 的 schema 结构、生成时机和消费方式 |
| **输入边界** | EPIC scope 定义的 artifact 类型清单、workflow 运行上下文、目录治理政策 |
| **输出边界** | placement-manifest-contract.md、placement-manifest-schema.yaml、示例 manifest |
| **外部依赖** | EPIC-SRC-056-001 frozen scope、directory governance policy |
| **内部依赖** | 无 |

#### 模块 B: Artifact Placement Reviewer Agent (FEAT-SRC-056-002)

| 属性 | 定义 |
|------|------|
| **模块名称** | Artifact Placement Reviewer Agent Implementation |
| **功能职责** | 实现独立的 directory audit agent 模块，支持读取 manifest 并审计目录 |
| **输入边界** | placement-manifest-contract.md、目标目录路径、audit 触发信号 |
| **输出边界** | artifact_placement_reviewer.py、placement_audit_report_schema.yaml、审计报告 |
| **外部依赖** | FEAT-SRC-056-001 输出的 contract 和 schema |
| **内部依赖** | Placement Manifest Contract Design |

#### 模块 C: Directory Audit Core Logic

| 属性 | 定义 |
|------|------|
| **模块名称** | Directory Audit Core Logic |
| **功能职责** | 扫描目录并比对实际文件位置与 manifest 规则 |
| **输入边界** | 已加载的 manifest、目标目录路径 |
| **输出边界** | 违规文件列表、合规文件列表、审计状态 |
| **外部依赖** | 操作系统文件系统 API |
| **内部依赖** | Agent Manifest Loading |

#### 模块 D: Requirement Chain Validation Integration

| 属性 | 定义 |
|------|------|
| **模块名称** | Requirement Chain Validation Integration |
| **功能职责** | 将目录审计集成到 requirement-chain-validation workflow |
| **输入边界** | workflow 执行上下文、agent 审计结果 |
| **输出边界** | gate 决策输入、阻断信号 |
| **外部依赖** | requirement-chain-validation workflow |
| **内部依赖** | Artifact Placement Reviewer Agent |

---

## 3. 可测试特性列表

### 3.1 功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TF-001 | Placement Manifest Schema Definition | Manifest Contract | P0 | Schema 包含四个核心字段且可解析 |
| TF-002 | Placement Manifest Contract Documentation | Manifest Contract | P0 | 文档明确定义生成时机和消费方式 |
| TF-003 | Manifest Example Completeness | Manifest Contract | P0 | 示例文件符合 schema 且覆盖 3+ 种 artifact 类型 |
| TF-004 | Agent Manifest Loading | Reviewer Agent | P0 | Agent 成功加载并解析 manifest |
| TF-005 | Directory Audit Core Logic | Reviewer Agent | P0 | Agent 正确扫描目录并识别违规/合规文件 |
| TF-006 | Audit Report Generation | Reviewer Agent | P0 | 报告包含完整的违规/合规文件列表 |
| TF-007 | CLI Interface Support | Reviewer Agent | P0 | 支持 lee audit --manifest --target 调用 |
| TF-008 | Python API Support | Reviewer Agent | P0 | 支持 import 和 API 调用 |
| TF-009 | Requirement Chain Validation Integration | Integration | P0 | Workflow 可集成调用并支持 gate 阻断 |
| TF-010 | Formal File Directory Validation | Audit Logic | P1 | 正式文件误写检测率达到 100% |
| TF-011 | Intermediate Artifact Directory Validation | Audit Logic | P1 | 中间产物误写检测率达到 100% |

### 3.2 非功能特性

| ID | 特性名称 | 所属模块 | 优先级 | 验收标准 |
|----|---------|---------|--------|---------|
| TNF-001 | Agent 可复用性 | Reviewer Agent | P0 | Agent 可被多个 workflow 复用 |
| TNF-002 | 审计性能 | Reviewer Agent | P1 | 目录审计在合理时间内完成（<30s） |
| TNF-003 | 错误处理 | Reviewer Agent | P1 | 提供明确的错误信息和异常处理 |

### 3.3 接口特性

| ID | 特性名称 | 接口类型 | 描述 |
|----|---------|---------|------|
| TI-001 | Manifest Schema Interface | Contract | YAML schema 定义接口 |
| TI-002 | Agent CLI Interface | External | lee audit 命令行接口 |
| TI-003 | Agent Python API | External | Python 模块导入和方法调用接口 |
| TI-004 | Audit Report Schema | Internal | 审计报告数据结构接口 |
| TI-005 | Workflow Integration API | External | Requirement chain validation 调用接口 |

---

## 4. 需求追溯矩阵

| 需求 ID | 需求描述 | 验收标准 | 可测试特性 | 优先级 |
|---------|---------|---------|-----------|--------|
| FEAT-SRC-056-001 | Placement Manifest Contract Design | AC-001~003 | TF-001~003 | P0 |
| FEAT-SRC-056-002 | Artifact Placement Reviewer Agent | AC-001~004 | TF-004~009 | P0 |
| EPIC-SRC-056-001 | Run-Scoped Artifact Placement Governance | 成功标准 | TF-001~011 | P0/P1 |

---

## 5. 风险评估

| 风险 ID | 风险描述 | 影响程度 | 缓解措施 |
|---------|---------|---------|---------|
| R-001 | Manifest schema 变更可能影响下游 agent | 中 | 版本控制、向后兼容设计 |
| R-002 | 目录结构复杂导致审计性能问题 | 低 | 优化扫描算法、支持增量审计 |
| R-003 | 误报率过高影响用户体验 | 中 | 精细化的规则配置、白名单机制 |
| R-004 | Workflow 集成时阻塞正常流程 | 中 | 支持跳过选项（需审批）、渐进式启用 |

---

## 6. 测试策略建议

### 6.1 测试类型分布

| 测试类型 | 覆盖范围 | 优先级 |
|---------|---------|--------|
| 单元测试 | Agent 核心逻辑、manifest 解析 | P0 |
| 集成测试 | Workflow 集成、CLI 接口 | P0 |
| 契约测试 | Schema 验证、API 契约 | P0 |
| 合规测试 | 目录治理规则验证 | P1 |

### 6.2 测试数据需求

| 数据类型 | 描述 | 来源 |
|---------|------|------|
| Valid Manifests | 符合 schema 的 placement manifest 样本 | 测试工具生成 |
| Invalid Manifests | 故意损坏的 manifest 用于错误处理测试 | 测试工具生成 |
| Sample Directories | 模拟的目录结构样本 | 测试工具生成 |
| Expected Reports | 预期审计结果用于断言 | 手工定义 |

---

## 7. 结论与建议

### 7.1 关键发现

1. **模块职责清晰**: 两个 FEAT 模块职责边界明确，FEAT-001 负责契约定义，FEAT-002 负责 agent 实现
2. **依赖关系合理**: FEAT-002 依赖 FEAT-001 的输出，无循环依赖
3. **验收标准完整**: 每个 FEAT 都有明确的验收标准（AC），可直接转化为测试用例
4. **可追溯性强**: 需求链完整（SRC → EPIC → FEAT → AC → Test Case）

### 7.2 测试重点建议

1. **优先级 P0**: Manifest schema 完整性、Agent 核心功能、CLI/API 接口、Workflow 集成
2. **核心场景**: 正常审计通过流程、违规检测流程、Gate 阻断流程
3. **边界场景**: 空目录处理、大量文件处理、manifest 格式错误处理

### 7.3 下一步行动

1. 基于本分析报告生成 Test Set 设计资产
2. 制定详细测试计划
3. 准备测试环境和数据
4. 开发自动化测试脚本

---

*文档生成时间: 2026-03-18T12:06:00+08:00*
