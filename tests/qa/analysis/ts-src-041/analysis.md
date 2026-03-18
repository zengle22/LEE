# 需求分析报告：SRC-041 Gate 治理语义归一化模块

## 文档信息

| 属性 | 值 |
|------|-----|
| 模块 | SRC-041 |
| EPIC | EPIC-SRC-041-016 |
| 标题 | ADR-017 Gate 治理语义归一化与人工审批上下文统一治理 |
| 分析日期 | 2026-03-18 |
| 分析状态 | 完成 |

## 1. 需求文档结构解析

### 1.1 文档层次

```
SRC-041 (Source Requirement)
└── EPIC-SRC-041-016 (ADR-017 Gate 治理语义归一化与人工审批上下文统一治理)
    ├── FEAT-SRC-041-001: Gate purpose 与 decision_mode 目标语义冻结
    ├── FEAT-SRC-041-002: human_gate_context 人工决策前置上下文强制化
    ├── FEAT-SRC-041-003: 正式边界动作的 approval plus human_required 约束
    ├── FEAT-SRC-041-004: 待审批 gate 的最小可判断摘要统一
    └── FEAT-SRC-041-005: 人工 gate 决策结果的统一 gate_result 输出
```

### 1.2 核心概念定义

| 概念 | 定义 | 来源 |
|------|------|------|
| **purpose** | 职责语义轴，覆盖 approval、review、check 等可审计职责边界 | FEAT-001 |
| **decision_mode** | 参与方式轴，区分 auto、human_required 等决策参与模式 | FEAT-001 |
| **human_gate_context** | 人工决策前置上下文，包含 subject、why_now、evidence、risk、next_action | FEAT-002 |
| **gate_result** | 人工决策的统一输出对象，包含 subject_refs、evidence_refs、next_action | FEAT-005 |
| **正式边界动作** | freeze、release、merge、risk acceptance 等高风险动作 | FEAT-003 |

### 1.3 旧分类到新模型映射

| 旧分类 | purpose | decision_mode |
|--------|---------|---------------|
| Auto Gate | check | auto |
| Review Gate | review | human_required |
| Approval Gate | approval | human_required |
| auto_check | check | auto |
| human_review | review | human_required |
| human_approval | approval | human_required |
| human_gate | approval | human_required |

## 2. 功能点提取

### 2.1 FEAT-SRC-041-001 功能点

| 功能点 ID | 功能描述 | 优先级 |
|-----------|----------|--------|
| FP-001-01 | 定义 purpose 作为职责语义轴 | P0 |
| FP-001-02 | 定义 decision_mode 作为参与方式轴 | P0 |
| FP-001-03 | 建立旧分类到双轴模型的收敛映射规则 | P0 |
| FP-001-04 | 禁止继续扩散旧分类语义的规则 | P0 |

### 2.2 FEAT-SRC-041-002 功能点

| 功能点 ID | 功能描述 | 优先级 |
|-----------|----------|--------|
| FP-002-01 | 定义 human_gate_context 最小信息边界 | P0 |
| FP-002-02 | 区分原生人工决策与自动升级决策入口 | P0 |
| FP-002-03 | 建立 gate 可审批前的上下文校验规则 | P0 |
| FP-002-04 | human_gate_context 作为共享消费对象 | P0 |

### 2.3 FEAT-SRC-041-003 功能点

| 功能点 ID | 功能描述 | 优先级 |
|-----------|----------|--------|
| FP-003-01 | 识别正式边界动作集合并绑定 purpose=approval | P0 |
| FP-003-02 | 正式边界动作 decision_mode 固定为 human_required | P0 |
| FP-003-03 | 定义 review 与 approval 的边界 | P0 |
| FP-003-04 | 输出正式动作分类约束供下游消费 | P0 |

### 2.4 FEAT-SRC-041-004 功能点

| 功能点 ID | 功能描述 | 优先级 |
|-----------|----------|--------|
| FP-004-01 | 定义待审批 gate 最小可判断摘要模型 | P0 |
| FP-004-02 | 约束 list/show/decide 复用同一判断语义 | P0 |
| FP-004-03 | 摘要字段绑定到 human_gate_context 与双轴语义 | P0 |
| FP-004-04 | 建立审批者无需追问的判断边界 | P0 |

### 2.5 FEAT-SRC-041-005 功能点

| 功能点 ID | 功能描述 | 优先级 |
|-----------|----------|--------|
| FP-005-01 | 定义 gate_result 作为统一输出对象 | P0 |
| FP-005-02 | 固定 subject_refs、evidence_refs、next_action 为最小必备信息 | P0 |
| FP-005-03 | 批准/拒绝/补充信息/风险接受采用统一结构 | P0 |
| FP-005-04 | gate_result 作为 runtime/CLI/审计的稳定消费边界 | P0 |

## 3. 验收标准汇总

### 3.1 Acceptance Checks 清单

| AC ID | 场景 | Given | When | Then | Trace Hints |
|-------|------|-------|------|------|-------------|
| AC-001-01 | 新增 gate 定义按双轴模型冻结 | 存在新增或待收敛的 gate 定义 | 规格作者编写正式定义 | 定义可直接读取 purpose 与 decision_mode，无需依赖旧分类 | TASK, TESTSET, TECH |
| AC-001-02 | 历史分类限制为兼容映射入口 | 存在旧模型的 gate 分类值 | 系统或规格消费这些旧值 | 消费结果只能映射到 purpose 与 decision_mode，旧值不能继续发布为正式治理语义 | TASK, TESTSET, TECH |
| AC-002-01 | 人工 gate 审批前具备统一上下文 | gate 定义为 decision_mode=human_required | gate 进入待审批状态 | 审批者可消费包含 subject、why_now、evidence、risk、next_action 的 human_gate_context | TASK, TESTSET, TECH |
| AC-002-02 | 自动升级补齐上下文 | 自动检查因风险/异常升级到人工决策 | 系统生成待审批 gate | human_gate_context 包含 escalation_reason，可连接到 subject_refs 与 evidence_refs | TASK, TESTSET, TECH |
| AC-003-01 | 正式边界动作约束到审批语义 | 存在 freeze/release/merge/risk acceptance gate | 规格系统校验 gate 分类 | 校验要求 purpose=approval 且 decision_mode=human_required，否则不合规 | TASK, TESTSET, TECH |
| AC-003-02 | review 无法表达正式放行 | 有人尝试用 review 语义定义正式边界动作 | 定义进入规格审核或运行时消费链路 | 系统或审核规则明确拒绝，要求改为 approval + human_required | TASK, TESTSET, TECH |
| AC-004-01 | list 阶段展示最小可判断摘要 | 存在待审批 gate | 审批者查看待办列表 | 列表项可直接读取 purpose、decision_mode、subject 与 why_now 摘要 | UI, TASK, TESTSET, TECH |
| AC-004-02 | show 与 decide 延续同一语义 | 审批者从 list 进入 show 或 decide | 系统展示详情或接收决策 | 字段保持同名同义，无平行语义 | UI, TASK, TESTSET, TECH |
| AC-005-01 | 人工 gate 输出统一结果对象 | 人工 gate 已产生审批结论 | 系统输出结论供 runtime/CLI/审计消费 | 输出对象为统一 gate_result，非特定 gate 私有结构 | TASK, TESTSET, TECH |
| AC-005-02 | 统一结果对象包含最小治理字段 | 存在已生成的 gate_result | 下游系统消费该结果 | 可直接读取 subject_refs、evidence_refs 与 next_action，并追溯到审批对象和证据 | TASK, TESTSET, TECH |

### 3.2 EPIC 成功标准

| 标准 ID | 描述 | 目标值 |
|---------|------|--------|
| SC-001 | 新增或收敛后的 gate 定义显式声明 purpose 与 decision_mode | 100% |
| SC-002 | decision_mode=human_required 或升级到人工决策的 gate 生成 human_gate_context | 100% |
| SC-003 | 待审批 gate 在 list 阶段可见 purpose、decision_mode、subject 与 why_now 摘要 | 100% |
| SC-004 | 人工 gate 决策结果输出统一 gate_result，包含 subject_refs、evidence_refs 与 next_action | 100% |
| SC-005 | freeze、release、merge、risk acceptance 等正式边界动作映射为 approval + human_required | 100% |

## 4. 模块边界定义

### 4.1 模块名称与描述

**模块名称**: Gate 治理语义归一化与人工审批上下文统一治理模块

**模块描述**:
本模块负责将 gate 的职责语义与参与方式归一化为 purpose 与 decision_mode 双轴模型，将 human_gate_context 固定为人工决策场景的强制前置物，并统一待审批 gate 的最小可判断摘要与决策结果输出格式。

### 4.2 范围边界

**In Scope**:
- Gate 双轴语义（purpose / decision_mode）的定义与约束
- human_gate_context 最小信息边界与强制化规则
- 正式边界动作（freeze/release/merge/risk acceptance）的 approval + human_required 约束
- 待审批 gate 最小可判断摘要（purpose、decision_mode、subject、why_now）的统一
- 人工 gate 统一决策结果（gate_result）的定义，包含 subject_refs、evidence_refs、next_action
- 旧分类（Auto/Review/Approval Gate、auto_check 等）到双轴模型的收敛映射

**Out of Scope**:
- 技术架构设计与具体实现方案定版
- 数据库最终列名、存储结构或一次性历史数据迁移方案
- 前端 UI 样式、交互视觉设计或终端展现美化
- 研发排期、资源拆分或跨团队执行计划
- CLI 命令交互样式细节
- 审批界面设计
- 审计报表设计
- 数据库落表细节
- 历史结果回填策略

### 4.3 接口边界

**输入接口**:
| 输入项 | 类型 | 描述 |
|--------|------|------|
| gate_definition | Object | Gate 定义对象，包含 purpose、decision_mode 字段 |
| legacy_classification | String | 旧分类值（Auto Gate、review 等） |
| human_decision_request | Object | 人工决策请求，包含 gate_id、decision_context |
| escalation_trigger | Object | 自动升级触发条件与原因 |

**输出接口**:
| 输出项 | 类型 | 描述 |
|--------|------|------|
| normalized_gate_def | Object | 归一化后的 gate 定义 |
| human_gate_context | Object | 包含 subject、why_now、evidence、risk、next_action 的上下文对象 |
| gate_summary | Object | 待审批 gate 最小可判断摘要 |
| gate_result | Object | 统一决策结果，包含 subject_refs、evidence_refs、next_action |
| validation_result | Object | 合规校验结果 |

### 4.4 依赖关系

```
FEAT-SRC-041-001 (双轴语义)
    ↑
    ├── FEAT-SRC-041-002 (human_gate_context 强制化)
    │       ↑
    │       ├── FEAT-SRC-041-003 (正式边界动作约束)
    │       │
    │       ├── FEAT-SRC-041-004 (最小可判断摘要)
    │       │
    │       └── FEAT-SRC-041-005 (统一 gate_result)
```

## 5. 可测试特性清单

### 5.1 特性列表概览

| 特性 ID | 名称 | 所属 FEAT | 优先级 |
|---------|------|-----------|--------|
| TF-001 | Gate 双轴语义定义验证 | FEAT-001 | P0 |
| TF-002 | 新增 Gate 双轴语义冻结 | FEAT-001 | P0 |
| TF-003 | 历史分类兼容映射限制 | FEAT-001 | P0 |
| TF-004 | human_gate_context 最小信息边界 | FEAT-002 | P0 |
| TF-005 | 人工 Gate 审批前上下文强制校验 | FEAT-002 | P0 |
| TF-006 | 自动升级到人工决策的上下文补齐 | FEAT-002 | P0 |
| TF-007 | 正式边界动作分类约束 | FEAT-003 | P0 |
| TF-008 | review 语义无法表达正式放行验证 | FEAT-003 | P0 |
| TF-009 | 待审批 Gate 最小可判断摘要 | FEAT-004 | P0 |
| TF-010 | list/show/decide 链路语义一致性 | FEAT-004 | P0 |
| TF-011 | Gate 决策结果统一输出 | FEAT-005 | P0 |
| TF-012 | Gate 结果最小治理字段验证 | FEAT-005 | P0 |

### 5.2 特性详细描述

#### TF-001: Gate 双轴语义定义验证
- **描述**: 验证 purpose 与 decision_mode 双轴模型的正确定义
- **验收标准**: 
  - purpose 字段支持 approval、review、check 等值
  - decision_mode 字段支持 auto、human_required 等值
  - 字段定义符合治理约束文档

#### TF-002: 新增 Gate 双轴语义冻结
- **描述**: 验证新增或收敛后的 gate 定义必须显式声明 purpose 与 decision_mode
- **验收标准**:
  - 定义可直接读取 purpose 与 decision_mode
  - 无需依赖旧分类字段解释职责

#### TF-003: 历史分类兼容映射限制
- **描述**: 验证旧分类值只能映射到双轴模型，不能继续发布为正式语义
- **验收标准**:
  - 旧分类值映射结果只包含 purpose 与 decision_mode
  - 系统拒绝将旧值作为正式治理语义发布

#### TF-004: human_gate_context 最小信息边界
- **描述**: 验证人工决策前置上下文包含完整的五类判断信息
- **验收标准**:
  - 上下文包含 subject、why_now、evidence、risk、next_action
  - 原生人工决策与自动升级场景使用统一前置物要求

#### TF-005: 人工 Gate 审批前上下文强制校验
- **描述**: 验证 decision_mode=human_required 的 gate 必须具备 human_gate_context
- **验收标准**:
  - 缺少 human_gate_context 时阻断人工决策流转
  - gate 进入待审批状态前完成上下文校验

#### TF-006: 自动升级到人工决策的上下文补齐
- **描述**: 验证自动检查升级到人工决策时补齐 human_gate_context
- **验收标准**:
  - human_gate_context 包含 escalation_reason
  - 可连接到 subject_refs 与 evidence_refs

#### TF-007: 正式边界动作分类约束
- **描述**: 验证 freeze、release、merge、risk acceptance 的 purpose=approval 且 decision_mode=human_required 约束
- **验收标准**:
  - 正式边界动作校验要求 purpose=approval
  - 正式边界动作 decision_mode 固定为 human_required
  - 违规分类被判定为不合规

#### TF-008: review 语义无法表达正式放行验证
- **描述**: 验证 review 语义不得再表达正式放行动作
- **验收标准**:
  - 用 review 语义定义正式边界动作时被拒绝
  - 系统要求改为 approval + human_required

#### TF-009: 待审批 Gate 最小可判断摘要
- **描述**: 验证 list 阶段展示 purpose、decision_mode、subject 与 why_now
- **验收标准**:
  - 待审批 gate 在 list 阶段可见四字段摘要
  - 审批者无需追问即可识别 gate 职责、参与方式、对象与原因

#### TF-010: list/show/decide 链路语义一致性
- **描述**: 验证 list、show、decide 三个链路复用同一判断语义与字段来源
- **验收标准**:
  - 字段保持同名同义
  - 无平行语义或重新命名字段

#### TF-011: Gate 决策结果统一输出
- **描述**: 验证所有人工 gate 决策结果统一输出为 gate_result
- **验收标准**:
  - 输出对象为统一 gate_result 结构
  - 非特定 gate 私有结构

#### TF-012: Gate 结果最小治理字段验证
- **描述**: 验证 gate_result 包含 subject_refs、evidence_refs 与 next_action
- **验收标准**:
  - 下游系统可直接读取三个字段
  - 可追溯到对应审批对象和证据

## 6. 风险与约束

### 6.1 测试风险

| 风险 ID | 风险描述 | 缓解措施 |
|---------|----------|----------|
| R-001 | 旧分类映射规则复杂，可能存在边界情况 | 增加映射规则边界测试用例 |
| R-002 | human_gate_context 字段扩展可能影响兼容性 | 验证最小字段集合的稳定性 |
| R-003 | 多 FEAT 依赖关系复杂 | 按依赖顺序执行测试 |

### 6.2 治理约束

- 下游 FEAT 不得重新引入第三条分类轴
- 禁止继续扩散旧分类语义
- 100% 正式边界动作必须满足 approval + human_required

## 7. 分析结论

本模块包含 5 个 FEAT，共 10 个 Acceptance Checks，可提取 12 个可测试特性（全部 P0 优先级）。模块核心验证目标包括：

1. **语义归一化**: purpose / decision_mode 双轴模型正确性
2. **上下文强制化**: human_gate_context 完整性与前置校验
3. **边界动作约束**: 正式边界动作的 approval + human_required 约束
4. **摘要统一性**: 待审批 gate 最小可判断摘要一致性
5. **结果标准化**: gate_result 统一输出与最小字段验证

建议测试执行顺序遵循 FEAT 依赖关系：001 → 002 → (003, 004, 005)。
