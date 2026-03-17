---
id: ADR-025
ssot_type: adr
title: SSOT Requirement Axis Acceptance Governance
status: draft
version: v1
parent_id: null
derived_from_ids:
- ADR-001
- ADR-003
- ADR-005
owner: product
tags:
- ssot
- quality
- acceptance
- governance
- requirement-axis
workflow_instance_id: wf-adr-025-20260317
properties:
  adr_kind: department_governance
  decision_scope: ssot_requirement_axis_acceptance
  quality_gate: mandatory
frozen_at: null
---

# SSOT 需求轴质量提升治理方案

## 1. Executive Summary

### 1.1 Decision

本 ADR 决定：**需求轴每个 SSOT 文件生成前，都必须经过测试和验收流程**。

验收范围包括：

- 功能逻辑闭环验证
- 用户故事体验达标验证
- 功能完整性检查
- 逻辑漏洞扫描
- 行业实践差异分析
- 改进空间识别

对发现的 P0/P1 问题必须修改后再验收，循环处理直到消除 P0/P1 问题。

验收报告必须放到 Gate 中供审批参考。

### 1.2 Problem Statement

当前 SSOT 生成流程存在的问题：

1. **质量验证缺失**：SSOT 对象生成后直接进入冻结流程，缺乏系统性质量验证
2. **用户体验风险**：用户故事视角的体验标准没有显式验收
3. **行业差距不可见**：与行业最佳实践的差异没有被系统识别和记录
4. **问题修复无闭环**：发现的问题没有分级跟踪和修复验证机制
5. **审批依据不足**：Gate 审批缺乏结构化验收报告作为决策依据

### 1.3 Scope

本 ADR 适用于需求轴以下 SSOT 对象：

- `SRC`（Source Requirement）
- `EPIC`（产品主题）
- `FEAT`（最小可独立验收能力单元）
- `UI`（界面与交互设计）
- `TECH`（技术设计）
- `TASK`（执行任务）

不适用于：

- `ADR`（决策型 SSOT，有独立评审流程）
- `TESTSET`（测试集，由 QA 部门负责）

## 2. Acceptance Framework

### 2.1 Acceptance Dimensions

每个 SSOT 对象必须通过以下维度的验收：

#### 2.1.1 功能逻辑闭环（Functional Closure）

验证目标：确保 SSOT 描述的能力在逻辑上完整、自洽、可执行。

检查项：

- 输入定义是否清晰（数据来源、触发条件、前置依赖）
- 处理逻辑是否完整（主流程、分支流程、异常流程）
- 输出定义是否明确（结果形态、验收标准、可观测性）
- 依赖关系是否可解析（外部系统、内部模块、数据依赖）
- 边界条件是否覆盖（极限值、空值、并发、时序）

验收标准：

- 不存在未定义的输入来源
- 不存在未处理的异常分支
- 不存在无法观测的输出结果
- 依赖关系图可完整解析且无循环依赖

#### 2.1.2 用户故事体验（User Story Experience）

验证目标：确保从用户视角体验流畅、符合预期、无断点。

检查项：

- 用户角色定义是否清晰
- 用户场景描述是否完整（前中后全链路）
- 用户价值是否可感知
- 交互路径是否流畅（步骤数、等待时间、认知负担）
- 错误反馈是否友好（可理解、可操作、可恢复）

验收标准：

- 每个用户行为型 FEAT 必须有 User Story
- User Story 必须符合 INVEST 原则
- 关键交互路径必须有体验指标定义
- 错误场景必须有明确的用户引导

#### 2.1.3 功能完整性（Feature Completeness）

验证目标：确保没有明显功能缺失。

检查项：

- 核心能力是否完整覆盖
- 辅助功能是否满足主功能使用
- 配置能力是否满足运营需求
- 监控能力是否满足运维需求
- 扩展能力是否满足演进需求

验收标准：

- 核心功能缺失 = P0
- 辅助功能缺失 = P1
- 配置/监控/扩展能力缺失 = P2（记录技术债务）

#### 2.1.4 逻辑漏洞扫描（Logic Vulnerability）

验证目标：确保不存在逻辑矛盾、二义性、可被滥用的漏洞。

检查项：

- 状态机是否完整（状态定义、转移条件、终态）
- 权限模型是否自洽（角色、资源、操作）
- 数据一致性是否有保障（并发、事务、最终一致性）
- 安全边界是否清晰（认证、授权、审计）
- 竞态条件是否处理（时序依赖、锁、幂等）

验收标准：

- 安全相关漏洞 = P0
- 数据一致性风险 = P0/P1
- 状态机不完整 = P1
- 二义性定义 = P1

#### 2.1.5 行业实践差异（Industry Gap Analysis）

验证目标：识别与行业最佳实践的差距，明确改进方向。

检查项：

- 与同类产品的功能对比
- 与行业标准的技术对比
- 与头部企业的体验对比
- 与开源方案的架构对比

验收标准：

- 必须识别至少 3 个对标对象
- 必须量化差异程度（领先/持平/落后）
- 必须给出改进建议优先级

#### 2.1.6 改进空间识别（Improvement Opportunities）

验证目标：即使当前版本可接受，也要识别长期改进方向。

检查项：

- 技术债务识别
- 架构演进方向
- 体验优化空间
- 性能提升潜力

验收标准：

- 改进项必须分类记录
- 改进项必须评估优先级
- 改进项必须纳入 backlog 跟踪

## 3. Defect Classification

### 3.1 Severity Levels

问题严重性分为四级：

#### P0 - 阻塞级（Blocker）

定义：不修复不能进入下一流程，存在重大风险。

特征：

- 功能逻辑不闭环
- 核心用户体验断裂
- 安全漏洞
- 数据一致性风险
- 关键依赖缺失

处理要求：

- **必须修复**
- 修复后必须重新验收
- 不允许绕过

#### P1 - 严重级（Critical）

定义：严重影响质量，原则上必须修复。

特征：

- 重要功能缺失
- 用户体验明显问题
- 逻辑漏洞但非安全相关
- 状态机不完整
- 关键 AC 不可测试

处理要求：

- **原则上必须修复**
- 特殊情况需 PM + Tech Lead 共同决策可延期
- 延期必须有明确时间表

#### P2 - 一般级（Major）

定义：影响质量但不阻塞流程。

特征：

- 辅助功能缺失
- 体验问题但不影响核心使用
- 文档不完整
- 配置能力不足
- 监控能力不足

处理要求：

- 记录为技术债务
- 纳入 backlog 优先级排序
- 不影响当前流程推进

#### P3 - 建议级（Minor）

定义：优化建议。

特征：

- 性能优化空间
- 代码风格问题
- 文档可改进点
- 长期架构演进建议

处理要求：

- 记录为改进建议
- 可选实施

### 3.2 Classification Matrix

| 维度 | P0 | P1 | P2 | P3 |
|------|------|------|------|------|
| 功能逻辑 | 主流程不通 | 分支流程缺失 | 边界条件未处理 | 注释不完整 |
| 用户体验 | 核心路径断裂 | 重要交互问题 | 次要体验问题 | 体验可优化 |
| 功能完整 | 核心能力缺失 | 辅助能力缺失 | 配置能力不足 | 扩展性待提升 |
| 逻辑漏洞 | 安全/数据风险 | 状态机不完整 | 二义性定义 | 代码 smell |
| 行业差距 | 关键能力落后 | 重要能力落后 | 一般能力落后 | 差异化空间 |

## 4. Acceptance Process

### 4.1 Process Flow

```
┌─────────────┐
│ SSOT Draft  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ Phase 1: Auto Check (Auto Gate) │
│ - Schema validation             │
│ - Contract validation           │
│ - Completeness check            │
│ - Dependency resolution         │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │ Pass          │ Fail
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│ Phase 2     │  │ Revise SSOT │
│ Manual Review│ └─────────────┘
│ (Review Gate)│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ Generate Acceptance Report      │
│ - Defect list (P0/P1/P2/P3)    │
│ - Industry gap analysis         │
│ - Improvement recommendations   │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │ Has P0/P1?    │
       │               │
       │ Yes           │ No
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│ Revise SSOT │  │ Phase 3     │
│ Fix P0/P1   │  │ Approval    │
└──────┬──────┘  │ (Approval   │
       │         │  Gate)      │
       │         └──────┬──────┘
       │                │
       └────────────────┘
                │
                ▼
       ┌────────────────┐
       │ SSOT Freeze    │
       │ + Gate Record  │
       │ + Report Ref   │
       └────────────────┘
```

### 4.2 Phase 1: Auto Check

**Gate Type**: Auto Gate

**执行时机**: SSOT Draft 完成后

**检查内容**:

1. Schema 验证
   - 必填字段完整性
   - 字段类型正确性
   - 枚举值合法性

2. Contract 验证
   - 符合对应 SSOT 类型的 contract
   - 符合 ADR 治理约束

3. 完整性检查
   - 必要章节存在性
   - 必要引用存在性
   - 版本号连续性

4. 依赖解析
   - derived_from_ids 可解析
   - parent_id 可解析
   - 无循环依赖

**输出**:

- `auto_check_result`
- `schema_errors`
- `contract_violations`
- `dependency_graph`

**决策**:

- `pass`: 进入 Phase 2
- `fail`: 返回修订
- `escalate`: 进入 Review Gate（边界情况）

### 4.3 Phase 2: Manual Review

**Gate Type**: Review Gate

**执行时机**: Auto Check 通过后

**参与角色**:

- Product Owner（必须）
- Tech Lead（必须）
- Design Lead（如涉及 UI）
- QA Lead（可选）

**检查内容**:

基于 2.1 六个维度进行人工评审

**输出**:

- `acceptance_report`
- `defect_list`
- `industry_gap_analysis`
- `improvement_backlog`

**决策**:

- `approve`: 无 P0/P1，进入 Phase 3
- `revise`: 有 P0/P1，返回修订
- `reject`: 存在根本性问题，重新设计
- `flag`: 有风险但可接受，记录后进入 Phase 3

### 4.4 Phase 3: Approval

**Gate Type**: Approval Gate

**执行时机**: Review Gate approve 后

**参与角色**:

- Product Owner（必须）
- 根据 SSOT 类型可能需要其他审批人

**检查内容**:

- 验收报告完整性
- P0/P1 问题已修复
- 风险已识别并有应对方案

**输出**:

- `approval_record`
- `freeze_ref`

**决策**:

- `approve`: SSOT 冻结
- `reject`: 返回修订

## 5. Acceptance Report Contract

### 5.1 Report Structure

验收报告必须包含以下结构：

```yaml
acceptance_report:
  ssot_id: <string>
  ssot_type: <SRC|EPIC|FEAT|UI|TECH|TASK>
  ssot_version: <string>

  review_info:
    review_date: <datetime>
    reviewers:
      - role: <string>
        name: <string>
        decision: <approve|revise|reject|flag>

  auto_check:
    status: <pass|fail|escalate>
    schema_validation: <pass|fail>
    contract_validation: <pass|fail>
    completeness_check: <pass|fail>
    dependency_resolution: <pass|fail>

  manual_review:
    dimensions:
      functional_closure:
        status: <pass|fail>
        findings:
          - severity: <P0|P1|P2|P3>
            description: <string>
            location: <string>
            suggestion: <string>
      user_story_experience:
        status: <pass|fail>
        findings: []
      feature_completeness:
        status: <pass|fail>
        findings: []
      logic_vulnerability:
        status: <pass|fail>
        findings: []
      industry_gap:
        status: <pass|fail>
        benchmarks:
          - target: <string>
            dimension: <string>
            gap_level: <leading|equal|behind>
            description: <string>
        findings: []
      improvement_opportunities:
        status: <pass|fail>
        items:
          - category: <technical_debt|architecture|experience|performance>
            priority: <high|medium|low>
            description: <string>

  defect_summary:
    p0_count: <int>
    p1_count: <int>
    p2_count: <int>
    p3_count: <int>
    total_count: <int>

  overall_decision:
    decision: <approved|revised|rejected|flagged>
    rationale: <string>

  defect_list:
    - id: <string>
      severity: <P0|P1|P2|P3>
      dimension: <string>
      title: <string>
      description: <string>
      location: <string>
      suggestion: <string>
      status: <open|fixed|deferred>
      fix_version: <string|null>

  industry_gap_analysis:
    benchmarks: []
    gap_summary: <string>
    recommendations:
      - priority: <high|medium|low>
        description: <string>

  improvement_backlog:
    items: []

  gate_reference:
    auto_gate_id: <string>
    review_gate_id: <string>
    approval_gate_id: <string>
```

### 5.2 Report Placement

验收报告的存放位置：

```
.artifacts/active/<department>/<ssot-type>/<ssot-id>/
├── <ssot-id>.md              # SSOT 本体
├── acceptance-report-<version>.yaml  # 验收报告
└── gate-records/
    ├── auto-gate-<id>.yaml
    ├── review-gate-<id>.yaml
    └── approval-gate-<id>.yaml
```

### 5.3 Gate Record Integration

Gate 记录必须引用验收报告：

```yaml
gate_record:
  gate_id: <string>
  gate_type: <auto|review|approval>
  subject:
    ssot_id: <string>
    ssot_type: <string>
  evidence_refs:
    - acceptance_report: <path>
  decision: <string>
  decision_by: <string>
  decision_at: <datetime>
  comments: <string>
```

## 6. Iterative Fix Process

### 6.1 Fix Loop

当发现 P0/P1 问题时，进入修复循环：

```
┌─────────────┐
│ P0/P1 Found │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Assign Fix  │ ──→ 记录缺陷 ID 和责任人
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Implement   │ ──→ 修订 SSOT 版本
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Re-Verify   │ ──→ 只验证修复项和相关项
└──────┬──────┘
       │
       ├───────┐
       │       │
   Pass      Fail
       │       │
       ▼       │
   ┌─────┐    │
   │ Done│    │
   └─────┘    │
              │
              └──→ 重新进入 Fix Loop
```

### 6.2 Re-Verification Scope

重新验收的范围：

- 必须验证：修复项本身
- 建议验证：修复项影响的相关功能
- 不必验证：与修复无关的其他功能

### 6.3 Version Tracking

SSOT 修订版本必须记录：

```yaml
ssot_metadata:
  version: v1.1  # 小修订
  superseded_by: null
  supersedes: v1.0

  change_log:
    - version: v1.1
      date: <datetime>
      changes:
        - fix_defect: DEFECT-001
          description: "修复 XXX 问题"
      acceptance_report: acceptance-report-v1.1.yaml
```

## 7. Industry Benchmark Framework

### 7.1 Benchmark Selection

选择对标对象的原则：

1. **同类产品的功能对比**
   - 选择 2-3 个直接竞品
   - 选择 1 个行业领导者

2. **与行业标准的技术对比**
   - 参考 RFC、ISO、IEEE 等标准
   - 参考行业白皮书

3. **与头部企业的体验对比**
   - 选择用户体验口碑好的企业
   - 参考 NN/g、Baymard 等研究机构

4. **与开源方案的架构对比**
   - 选择成熟的开源项目
   - 参考其架构决策记录

### 7.2 Gap Assessment

差异评估方法：

```yaml
gap_assessment:
  dimension: <功能|技术|体验|架构>
  benchmark_target: <对标对象>
  capability: <具体能力>

  our_status:
    maturity: <none|basic|intermediate|advanced|leading>
    description: <string>

  benchmark_status:
    maturity: <none|basic|intermediate|advanced|leading>
    description: <string>

  gap_level: <leading|equal|slightly_behind|behind|significantly_behind>

  impact:
    user_impact: <high|medium|low>
    business_impact: <high|medium|low>
    technical_impact: <high|medium|low>

  recommendation:
    priority: <immediate|short_term|medium_term|long_term>
    action: <string>
    estimated_effort: <small|medium|large>
```

### 7.3 Gap Report

差异分析报告模板：

```yaml
industry_gap_report:
  ssot_id: <string>
  assessment_date: <datetime>

  benchmarks:
    - name: <对标对象 1>
      type: <competitor|industry_leader|open_source|standard>
      description: <string>

  gap_matrix:
    <capability_area>:
      - benchmark: <对标对象>
        gap_level: <string>
        notes: <string>

  summary:
    leading_areas: []
    equal_areas: []
    behind_areas: []

  recommendations:
    immediate_actions: []
    short_term_goals: []
    long_term_vision: []
```

## 8. Metrics and KPIs

### 8.1 Quality Metrics

| 指标 | 定义 | 目标 |
|------|------|------|
| P0 缺陷密度 | P0 缺陷数 / SSOT 规模 | 0 |
| P1 缺陷密度 | P1 缺陷数 / SSOT 规模 | < 0.1 |
| 一次通过率 | 首次验收即通过的 SSOT 比例 | > 60% |
| 平均修复轮次 | 从 Draft 到 Freeze 的平均修订次数 | < 2 |
| 验收覆盖率 | 经过完整验收的 SSOT 比例 | 100% |
| 行业差距记录率 | 有行业差距分析的 SSOT 比例 | 100% |

### 8.2 Process Metrics

| 指标 | 定义 | 目标 |
|------|------|------|
| Auto Gate 通过率 | 通过 Auto Gate 的比例 | > 90% |
| Review Gate 周期 | 从 Review 开始到 decision 的时间 | < 3 天 |
| P0 平均修复时间 | 从发现到修复完成的时间 | < 1 天 |
| P1 平均修复时间 | 从发现到修复完成的时间 | < 3 天 |
| Gate 审批通过率 | Gate approve 的比例 | > 85% |

## 9. Tooling Requirements

### 9.1 Auto Check Tooling

需要开发的工具：

1. **Schema Validator**
   - 验证 SSOT YAML frontmatter
   - 验证 SSOT 正文结构

2. **Contract Validator**
   - 验证 SSOT 符合对应 contract
   - 验证 ADR 约束遵守

3. **Dependency Resolver**
   - 解析 SSOT 依赖图
   - 检测循环依赖

4. **Completeness Checker**
   - 检查必填章节
   - 检查必填字段

### 9.2 Review Tooling

需要开发的工具：

1. **Acceptance Report Generator**
   - 生成验收报告模板
   - 自动填充检查结果

2. **Defect Tracker**
   - 记录缺陷
   - 跟踪修复状态

3. **Gap Analysis Assistant**
   - 辅助识别行业差距
   - 提供对标对象建议

### 9.3 Gate Integration

Gate 系统需要支持：

1. **验收报告引用**
   - Gate 记录必须包含验收报告引用

2. **缺陷状态检查**
   - Approval Gate 前检查 P0/P1 状态

3. **版本追溯**
   - 记录 SSOT 修订历史

## 10. Implementation Plan

### 10.1 Phase 1: Foundation

- 定义验收报告 schema
- 定义 Gate 记录 schema
- 定义缺陷分类标准

### 10.2 Phase 2: Auto Check

- 实现 Schema Validator
- 实现 Contract Validator
- 实现 Auto Gate 集成

### 10.3 Phase 3: Review Process

- 实现 Review Gate 流程
- 实现验收报告生成
- 实现缺陷跟踪

### 10.4 Phase 4: Industry Benchmark

- 建立对标对象库
- 实现差距分析框架
- 建立改进建议库

### 10.5 Phase 5: Metrics

- 实现质量指标采集
- 实现过程指标采集
- 建立度量仪表板

## 11. Governance Rules

### 11.1 Mandatory Rules

1. **无验收不冻结**
   - 没有验收报告的 SSOT 不能进入冻结流程

2. **P0/P1 必修复**
   - P0 问题必须修复
   - P1 问题原则必须修复

3. **验收报告入 Gate**
   - 验收报告是 Gate 审批的必要输入

4. **版本可追溯**
   - SSOT 修订必须有版本记录
   - 缺陷修复必须有版本关联

### 11.2 Enforcement

1. **Auto Gate 强制执行**
   - Auto Check 失败不能进入 Review

2. **Gate 记录强制引用**
   - Gate 记录没有验收报告引用 = 无效

3. **指标定期审查**
   - 质量指标纳入团队考核

## 12. Follow-up

需要继续完成的工作：

1. 实现 Auto Check 工具链
2. 建立对标对象库
3. 集成 Gate 系统
4. 培训团队使用新流程

## 13. References

- ADR-001: SSOT Delivery Chain Hard Governance
- ADR-003: Product Department SSOT Design
- ADR-005: Gate 三分类治理模型
