# 需求分析报告：SRC-056 Artifact Placement Governance

> **模块**: SRC-056 Artifact Placement Governance  
> **分析日期**: 2026-03-18  
> **分析专家**: 需求分析专家  
> **关联 EPIC**: EPIC-SRC-056-001  
> **关联 FEATs**: FEAT-SRC-056-001, FEAT-SRC-056-002

---

## 1. 需求文档结构解析

### 1.1 文档层级关系

```
SRC-056 (需求源)
└── EPIC-SRC-056-001: Run-Scoped Artifact Placement Governance and Directory Audit
    ├── FEAT-SRC-056-001: Run-Scoped Placement Manifest Contract Design
    └── FEAT-SRC-056-002: Artifact Placement Reviewer Agent Implementation
```

### 1.2 文档元数据

| 属性 | EPIC-SRC-056-001 | FEAT-SRC-056-001 | FEAT-SRC-056-002 |
|------|------------------|------------------|------------------|
| 类型 | EPIC | FEAT | FEAT |
| 状态 | frozen | frozen | frozen |
| 版本 | v1 | v1 | v1 |
| 优先级 | - | P0 | P0 |
| 交付切片 | - | mvp | mvp |

---

## 2. 模块边界定义

### 2.1 模块标识

- **模块 ID**: `src-056-artifact-placement`
- **模块名称**: Run-Scoped Artifact Placement Governance
- **模块描述**: 建立覆盖正式 SSOT 文件与非正式 workflow 产物的统一目录治理方案

### 2.2 功能边界

#### 2.2.1 模块内功能（In Scope）

| 功能域 | 功能描述 | 关联 FEAT |
|--------|----------|-----------|
| **Manifest Contract** | 定义 placement manifest 的 schema 结构、生成时机和消费方式 | FEAT-SRC-056-001 |
| **Schema 定义** | 包含 manifest_id、run_scope、expected_artifacts、placement_rules 字段 | FEAT-SRC-056-001 |
| **Agent 实现** | 独立的 directory audit agent 模块 | FEAT-SRC-056-002 |
| **Manifest 解析** | 读取 placement manifest 并解析 expected artifacts | FEAT-SRC-056-002 |
| **目录扫描** | 扫描指定目录并比对实际文件位置与 manifest 规则 | FEAT-SRC-056-002 |
| **审计报告** | 输出审计结果报告，包含违规文件列表和合规文件列表 | FEAT-SRC-056-002 |
| **CLI 接口** | 支持 `lee audit --manifest <path> --target <path>` 调用 | FEAT-SRC-056-002 |
| **Python API** | 支持 `import artifact_placement_reviewer` 调用 | FEAT-SRC-056-002 |
| **Workflow 集成** | 可被 requirement-chain-validation workflow 集成调用 | FEAT-SRC-056-002 |

#### 2.2.2 模块外功能（Out of Scope）

| 功能描述 | 排除原因 |
|----------|----------|
| 自动搬运已有错误文件到正确目录 | 非目标 |
| 自动修复历史存量目录问题 | 非目标 |
| 用 agent 替代 runtime 进行物理文件写入 | 非目标 |
| 修改业务对象主链语义（SRC/EPIC/FEAT 等） | 非目标 |
| runtime manifest 生成实现 | FEAT-001 非目标 |
| 文件物理写入逻辑 | FEAT-001 非目标 |
| 自动修复错误文件位置 | FEAT-002 非目标 |

### 2.3 接口边界

#### 2.3.1 输入接口

| 接口名称 | 类型 | 描述 | 来源 |
|----------|------|------|------|
| `placement-manifest-schema.yaml` | Schema | Manifest 结构定义 | FEAT-SRC-056-001 输出 |
| `placement-manifest.json/yaml` | Data | 实际 manifest 文件 | Workflow 运行时生成 |
| `--manifest <path>` | CLI 参数 | Manifest 文件路径 | 用户/Workflow 传入 |
| `--target <path>` | CLI 参数 | 目标审计目录路径 | 用户/Workflow 传入 |
| `audit trigger signal` | Event | 审计触发信号 | Manual 或 Automated gate |

#### 2.3.2 输出接口

| 接口名称 | 类型 | 描述 | 消费者 |
|----------|------|------|--------|
| `placement_audit_report_schema.yaml` | Schema | 审计结果 schema 定义 | Validator/Gate |
| `audit-report.json/yaml` | Data | 审计结果报告 | Validator/Gate |
| CLI stdout | Output | 审计结果输出 | 用户/CI 系统 |
| Python API 返回值 | Object | 审计结果对象 | 集成代码 |

### 2.4 数据边界

#### 2.4.1 核心数据结构

**Manifest Schema 核心字段**:
```yaml
manifest_id: string        # 唯一标识
run_scope: object          # 运行上下文
expected_artifacts: array  # 预期产物列表
placement_rules: object    # 放置规则定义
```

**Audit Report 核心字段**:
```yaml
audit_id: string           # 审计唯一标识
manifest_ref: string       # 关联 manifest
compliant_files: array     # 合规文件列表
violation_files: array     # 违规文件列表
audit_timestamp: string    # 审计时间戳
summary: object            # 统计摘要
```

---

## 3. 可测试特性列表

### 3.1 测试特性总览

| 特性 ID | 特性名称 | 优先级 | 测试类型 | 关联 FEAT |
|---------|----------|--------|----------|-----------|
| TF-001 | Manifest Schema 结构完整性 | P0 | 静态验证 | FEAT-SRC-056-001 |
| TF-002 | Manifest 生成时机规范 | P0 | 文档审查 | FEAT-SRC-056-001 |
| TF-003 | Manifest 消费方式规范 | P0 | 文档审查 | FEAT-SRC-056-001 |
| TF-004 | Manifest 示例有效性 | P0 | 示例验证 | FEAT-SRC-056-001 |
| TF-005 | Manifest 解析功能 | P0 | 功能测试 | FEAT-SRC-056-002 |
| TF-006 | 目录扫描功能 | P0 | 功能测试 | FEAT-SRC-056-002 |
| TF-007 | 文件位置比对逻辑 | P0 | 功能测试 | FEAT-SRC-056-002 |
| TF-008 | 审计报告生成 | P0 | 功能测试 | FEAT-SRC-056-002 |
| TF-009 | CLI 接口功能 | P0 | 集成测试 | FEAT-SRC-056-002 |
| TF-010 | Python API 功能 | P0 | 集成测试 | FEAT-SRC-056-002 |
| TF-011 | Workflow 集成功能 | P0 | 集成测试 | FEAT-SRC-056-002 |
| TF-012 | Gate 阻断机制 | P0 | E2E 测试 | EPIC-SRC-056-001 |

### 3.2 详细可测试特性

#### TF-001: Manifest Schema 结构完整性

**描述**: 验证 placement manifest schema 包含所有必需字段

**验收标准**:
- Schema 包含 `manifest_id` 字段
- Schema 包含 `run_scope` 字段
- Schema 包含 `expected_artifacts` 字段
- Schema 包含 `placement_rules` 字段

**测试方法**:
- Schema 静态验证
- YAML 语法检查
- 字段完整性检查

#### TF-002: Manifest 生成时机规范

**描述**: 验证 contract 文档明确定义 manifest 生成时机为 workflow 初始化阶段

**验收标准**:
- 文档明确说明生成时机
- 生成时机符合 workflow 生命周期

**测试方法**:
- 文档审查
- 规范一致性检查

#### TF-003: Manifest 消费方式规范

**描述**: 验证 contract 文档明确定义 manifest 消费方式

**验收标准**:
- 文档明确说明 auditer agent 读取方式
- 文档明确说明 validator 引用方式

**测试方法**:
- 文档审查
- 消费链路验证

#### TF-004: Manifest 示例有效性

**描述**: 验证示例 manifest 文件符合 schema 且包含至少 3 种 artifact 类型

**验收标准**:
- 示例符合 schema 定义
- 包含 ≥3 种 artifact 类型
- 放置规则定义完整

**测试方法**:
- 示例验证
- Schema 校验

#### TF-005: Manifest 解析功能

**描述**: 验证 agent 能够读取 placement manifest 并解析 expected artifacts

**验收标准**:
- 成功加载有效 manifest 文件
- 正确解析 expected artifacts 列表
- 错误 manifest 返回适当错误

**测试方法**:
- 单元测试
- 边界值测试（空文件、无效 YAML、缺失字段）

#### TF-006: 目录扫描功能

**描述**: 验证 agent 能够扫描指定目录

**验收标准**:
- 递归扫描目标目录
- 识别所有文件类型
- 正确处理符号链接
- 处理权限错误

**测试方法**:
- 单元测试
- 边界值测试（空目录、深层嵌套、大量文件）

#### TF-007: 文件位置比对逻辑

**描述**: 验证 agent 能够比对实际文件位置与 manifest 规则

**验收标准**:
- 正确识别合规文件
- 正确识别违规文件
- 支持多种匹配规则（精确、模式、前缀）
- 正确处理文件名/路径大小写

**测试方法**:
- 单元测试
- 组合测试（多种规则组合）

#### TF-008: 审计报告生成

**描述**: 验证 agent 输出审计结果报告

**验收标准**:
- 报告包含违规文件列表
- 报告包含合规文件列表
- 报告格式符合 schema
- 报告包含统计摘要

**测试方法**:
- 单元测试
- 报告 schema 验证

#### TF-009: CLI 接口功能

**描述**: 验证 agent 支持 CLI 调用

**验收标准**:
- 支持 `lee audit --manifest <path> --target <path>`
- 支持帮助信息输出
- 支持错误处理和退出码
- 支持报告文件输出

**测试方法**:
- CLI 集成测试
- 参数验证测试
- 退出码验证

#### TF-010: Python API 功能

**描述**: 验证 agent 支持 Python API 调用

**验收标准**:
- 支持 `import artifact_placement_reviewer`
- 提供 `load_manifest()` 方法
- 提供 `audit()` 方法
- 返回结构化结果对象

**测试方法**:
- API 集成测试
- 返回值验证
- 异常处理测试

#### TF-011: Workflow 集成功能

**描述**: 验证 agent 可被 requirement-chain-validation workflow 集成调用

**验收标准**:
- 支持 workflow 调用 API
- 返回结果可供 gate 决策
- 支持异步/同步调用模式

**测试方法**:
- Workflow 集成测试
- Mock workflow 环境测试

#### TF-012: Gate 阻断机制

**描述**: 验证 requirement-chain-validation 流程中目录审计步骤作为 blocker

**验收标准**:
- 审计不通过时阻断 workflow
- 审计通过时允许 workflow 继续
- 阻断时提供明确的错误信息

**测试方法**:
- E2E 测试
- Gate 逻辑测试

---

## 4. 测试覆盖矩阵

### 4.1 FEAT-SRC-056-001 覆盖矩阵

| 验收检查 ID | 验收场景 | 覆盖特性 | 测试类型 |
|-------------|----------|----------|----------|
| AC-001 | placement manifest schema 结构完整性验证 | TF-001 | Schema 验证 |
| AC-002 | contract 文档明确定义生成时机和消费方式 | TF-002, TF-003 | 文档审查 |
| AC-003 | 提供完整的示例 manifest 文件 | TF-004 | 示例验证 |

### 4.2 FEAT-SRC-056-002 覆盖矩阵

| 验收检查 ID | 验收场景 | 覆盖特性 | 测试类型 |
|-------------|----------|----------|----------|
| AC-001 | agent 读取 manifest 并解析 expected artifacts | TF-005 | 功能测试 |
| AC-002 | agent 扫描目录并比对规则 | TF-006, TF-007, TF-008 | 功能测试 |
| AC-003 | agent CLI 调用 | TF-009 | 集成测试 |
| AC-004 | agent 被 requirement-chain-validation 调用 | TF-010, TF-011 | 集成测试 |

---

## 5. 依赖与约束

### 5.1 测试依赖

| 依赖项 | 描述 | 影响特性 |
|--------|------|----------|
| FEAT-SRC-056-001 | Manifest Contract 必须先完成 | TF-005 ~ TF-012 |
| ADR-021 | Run-Scoped Artifact Placement | 全部 |
| placement-manifest-schema.yaml | Schema 文件必须存在 | TF-001, TF-005 |

### 5.2 测试约束

| 约束类型 | 约束描述 |
|----------|----------|
| 环境约束 | 需要模拟 workflow 运行环境 |
| 数据约束 | 需要准备测试用 manifest 文件 |
| 权限约束 | 需要文件系统读写权限 |
| 集成约束 | 需要与 workflow 框架集成测试 |

---

## 6. 风险评估

### 6.1 测试风险

| 风险 ID | 风险描述 | 影响 | 缓解措施 |
|---------|----------|------|----------|
| R-001 | Manifest schema 变更导致测试失效 | 高 | 使用 schema 版本控制 |
| R-002 | Workflow 集成复杂度高 | 中 | 使用 mock 框架隔离测试 |
| R-003 | 文件系统操作平台差异 | 中 | 多平台 CI 测试 |

---

## 7. 总结

### 7.1 关键发现

1. **模块边界清晰**: SRC-056 Artifact Placement Governance 模块功能边界明确，分为 Contract 设计和 Agent 实现两个 FEAT
2. **验收标准完整**: 每个 FEAT 都有明确的验收标准和验收检查点
3. **可测试特性丰富**: 共识别 12 个可测试特性，覆盖 schema 验证、功能测试、集成测试和 E2E 测试
4. **依赖关系明确**: FEAT-002 依赖于 FEAT-001，测试执行需要遵循此顺序

### 7.2 测试建议

1. **优先测试**: TF-001 (Schema 验证)、TF-005 (Manifest 解析)、TF-007 (比对逻辑)
2. **重点集成**: TF-011 (Workflow 集成)、TF-012 (Gate 阻断)
3. **自动化程度**: 建议全部 12 个特性实现自动化测试

### 7.3 输出产物

本分析报告为 Test Set 设计提供输入，后续将生成：
- `qa_specs_dir/test-sets/ts-src-056-artifact-placement.yaml` - Test Set 设计资产

---

*报告生成完成*
