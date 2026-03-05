# Test Set Production L3 流程说明

## 一、流程概述

**流程名称**: Test Set Production L3（Test Set 生产流程）

**版本**: v1.2

**ID**: `template.qa.test_set_production`

**职责**: 将模块需求转化为 Test Set 设计资产

**所有者**: `qa-governance`

**标签**: `template`, `qa`, `test-set`, `design-asset`, `l3`

**核心设计原则**:
1. **治理层与执行层分离** - 根节点使用 `stages`（治理层），工作由 `stages[].steps` 执行（执行层）
2. **4 阶段流程** - 需求分析 → 测试策略设计 → Test Set 生成 → Test Set 审评
3. **人类门禁** - 关键节点设置人工审核/批准门禁，确保质量

---

## 二、4 阶段流程概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Test Set Production Pipeline                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐                                               │
│  │ Stage 1          │  分析需求文档，提取可测试特性                 │
│  │ Requirement      │  人类门禁：analysis_review（QA Lead 审核）    │
│  │ Analysis         │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │ Stage 2          │  设计测试策略，识别风险区域                   │
│  │ Test Strategy    │  人类门禁：strategy_review（QA Lead 审核）    │
│  │ Design           │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │ Stage 3          │  从策略生成标准化 Test Set YAML               │
│  │ Test Set         │  无门禁                                       │
│  │ Generation       │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                               │
│  │ Stage 4          │  审评 Test Set 完整性和可执行性              │
│  │ Test Set Review  │  人类门禁：test_set_approval（QA Lead + PM）  │
│  │                  │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ▼                                                          │
│      ┌────────────┐                                                  │
│      │  COMPLETED │                                                  │
│      └────────────┘                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、详细阶段说明

### Stage 1: Requirement Analysis（需求分析）

| 属性 | 值 |
|------|-----|
| **Stage ID** | `requirement_analysis` |
| **名称** | Requirement Analysis |
| **依赖** | 无 |
| **人类门禁** | `gate.qa.analysis_review`（人工审核） |

#### 步骤详情

| 属性 | 值 |
|------|-----|
| **Step ID** | `requirement_analysis` |
| **类型** | Agent |
| **Agent** | `agent.qa.requirement_analyzer` |
| **强制性** | 是 |

**职责**: 分析需求文档，提取可测试特性

**输出**:
| 路径 | 类型 | 格式 | 描述 |
|------|------|------|------|
| `{{ qa_specs_dir }}/test-sets/ts-{{ module }}/analysis.md` | 文件 | Markdown | 需求分析报告（包含模块边界和可测试特性） |

**人类门禁配置**:
- **类型**: `human_review`（人工审核）
- **超时**: 24 小时
- **审批人**: `qa_lead`
- **提示**: "请审核需求分析结果，确认模块边界和可测试特性"

---

### Stage 2: Test Strategy Design（测试策略设计）

| 属性 | 值 |
|------|-----|
| **Stage ID** | `strategy_design` |
| **名称** | Test Strategy Design |
| **依赖** | `requirement_analysis` |
| **人类门禁** | `gate.qa.strategy_review`（人工审核） |

#### 步骤详情

| 属性 | 值 |
|------|-----|
| **Step ID** | `strategy_design` |
| **类型** | Agent |
| **Agent** | `agent.qa.test_strategist` |
| **强制性** | 是 |

**职责**: 设计测试策略，识别风险区域和测试重点

**输出**:
| 路径 | 类型 | 格式 | 描述 |
|------|------|------|------|
| `{{ qa_specs_dir }}/test-sets/ts-{{ module }}/strategy-draft.yaml` | 文件 | YAML | 测试策略草稿（包含测试策略、风险区域和测试重点） |

**人类门禁配置**:
- **类型**: `human_review`（人工审核）
- **超时**: 24 小时
- **审批人**: `qa_lead`
- **提示**: "请审核测试策略，确认测试重点和风险区域"

---

### Stage 3: Test Set Generation（Test Set 生成）

| 属性 | 值 |
|------|-----|
| **Stage ID** | `test_set_generation` |
| **名称** | Test Set Generation |
| **依赖** | `strategy_design` |
| **人类门禁** | 无 |

#### 步骤详情

| 属性 | 值 |
|------|-----|
| **Step ID** | `test_set_generation` |
| **类型** | Agent |
| **Agent** | `agent.qa.test_set_generator` |
| **强制性** | 是 |

**职责**: 从测试策略生成标准化的 Test Set YAML

**输出**:
| 路径 | 类型 | 格式 | 描述 |
|------|------|------|------|
| `{{ qa_specs_dir }}/test-sets/ts-{{ module }}.yaml` | 文件 | YAML | Test Set 设计资产（符合 test-set schema 的标准化 YAML） |

---

### Stage 4: Test Set Review（Test Set 审评）

| 属性 | 值 |
|------|-----|
| **Stage ID** | `test_set_review` |
| **名称** | Test Set Review |
| **依赖** | `test_set_generation` |
| **人类门禁** | `gate.qa.test_set_approval`（人工批准） |

#### 步骤详情

| 属性 | 值 |
|------|-----|
| **Step ID** | `test_set_review` |
| **类型** | Agent |
| **Agent** | `agent.qa.test_set_reviewer` |
| **强制性** | 是 |

**职责**: 审评 Test Set 的完整性和可执行性

**输出**:
| 路径 | 类型 | 格式 | 描述 |
|------|------|------|------|
| `{{ qa_specs_dir }}/test-sets/ts-{{ module }}/review-report.md` | 文件 | Markdown | Test Set 审评报告（包含审评结果和批准状态） |

**人类门禁配置**:
- **类型**: `human_approval`（人工批准）
- **超时**: 48 小时
- **审批人**: `qa_lead` + `pm`（双人批准）
- **提示**: "请最终确认 Test Set，批准后将正式生效"

---

## 四、输入参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `module` | string | ✅ | 模块名称 |
| `requirement_doc` | string | ✅ | 需求文档路径（PRD/User Story） |
| `tech_design` | string | ❌ | 技术设计文档路径（可选） |

---

## 五、输出契约（Output Contract）

| 输出 | 路径 | Schema | 描述 |
|------|------|--------|------|
| `test_set` | `{{ qa_specs_dir }}/test-sets/ts-{module}.yaml` | `../../contracts/test-set/v1/schema.yaml` | 生成的 Test Set 设计资产 |
| `analysis_report` | `{{ qa_specs_dir }}/test-sets/ts-{module}/analysis.md` | - | 需求分析报告 |
| `strategy_draft` | `{{ qa_specs_dir }}/test-sets/ts-{module}/strategy-draft.yaml` | - | 测试策略草稿 |

---

## 六、输出目录结构

```
{{ qa_specs_dir }}/
└── test-sets/
    ├── ts-{module}.yaml              # Test Set 设计资产（主文件）
    └── ts-{module}/
        ├── analysis.md               # 需求分析报告
        └── strategy-draft.yaml       # 测试策略草稿
```

**说明**:
- `qa_specs_dir` = `spec/qa`（QA 冻结资产目录）
- Test Set 主文件与详细报告分离存放

---

## 七、状态机（State Machine）

### 状态定义

| 状态 | 描述 |
|------|------|
| `INIT` | 初始化 |
| `REQUIREMENT_ANALYSIS` | 需求分析 |
| `STRATEGY_DESIGN` | 测试策略设计 |
| `TEST_SET_GENERATION` | Test Set 生成 |
| `TEST_SET_REVIEW` | Test Set 审评 |
| `COMPLETED` | 完成 |
| `FAILED` | 失败 |

### 状态流转图

```
┌──────────────┐
│    INIT      │
└──────┬───────┘
       │ workflow_started
       ▼
┌──────────────────┐
│ REQUIREMENT_     │◄───────────────┐
│ ANALYSIS         │───────┐        │
└────────┬─────────┘       │        │
         │                 │        │
         │ analysis_approved│        │ analysis_rejected
         ▼                 │        │
┌──────────────────┐       │        │
│ STRATEGY_        │───────┘        │
│ DESIGN           │ strategy_rejected
└────────┬─────────┘
         │ strategy_approved
         ▼
┌──────────────────┐
│ TEST_SET_        │───────────────►│ FAILED │
│ GENERATION       │ generation_failed
└────────┬─────────┘
         │ test_set_generated
         ▼
┌──────────────────┐
│ TEST_SET_        │ test_set_rejected
│ REVIEW           │◄───────────────┐
└────────┬─────────┘               │
         │                         │
         │ test_set_approved       │
         ▼                         │
┌──────────────┐                   │
│  COMPLETED   │                   │
└──────────────┘                   │
                                   │
         ┌─────────────────────────┘
         │ doc_invalid / generation_failed
         ▼
┌──────────────┐
│    FAILED    │
└──────────────┘
```

### 状态流转说明

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|---------|---------|---------|------|
| `INIT` | `workflow_started` | `REQUIREMENT_ANALYSIS` | 工作流启动 |
| `REQUIREMENT_ANALYSIS` | `analysis_approved` | `STRATEGY_DESIGN` | 需求分析通过审核 |
| `REQUIREMENT_ANALYSIS` | `analysis_rejected` | `REQUIREMENT_ANALYSIS` | 需求分析被驳回，重新分析 |
| `REQUIREMENT_ANALYSIS` | `doc_invalid` | `FAILED` | 文档无效，流程失败 |
| `STRATEGY_DESIGN` | `strategy_approved` | `TEST_SET_GENERATION` | 测试策略通过审核 |
| `STRATEGY_DESIGN` | `strategy_rejected` | `STRATEGY_DESIGN` | 测试策略被驳回，重新设计 |
| `TEST_SET_GENERATION` | `test_set_generated` | `TEST_SET_REVIEW` | Test Set 生成完成 |
| `TEST_SET_GENERATION` | `generation_failed` | `FAILED` | 生成失败 |
| `TEST_SET_REVIEW` | `test_set_approved` | `COMPLETED` | Test Set 获得批准 |
| `TEST_SET_REVIEW` | `test_set_rejected` | `TEST_SET_GENERATION` | Test Set 被驳回，重新生成 |

---

## 八、人类门禁配置（Human Gates）

### 1. Analysis Review（需求分析审核）

| 属性 | 值 |
|------|-----|
| **Gate ID** | `gate.qa.analysis_review` |
| **类型** | `human_review`（人工审核） |
| **超时** | 24 小时 |
| **审批人** | `qa_lead` |
| **提示** | "请审核需求分析结果，确认模块边界和可测试特性" |

### 2. Strategy Review（测试策略审核）

| 属性 | 值 |
|------|-----|
| **Gate ID** | `gate.qa.strategy_review` |
| **类型** | `human_review`（人工审核） |
| **超时** | 24 小时 |
| **审批人** | `qa_lead` |
| **提示** | "请审核测试策略，确认测试重点和风险区域" |

### 3. Test Set Approval（Test Set 批准）⭐

| 属性 | 值 |
|------|-----|
| **Gate ID** | `gate.qa.test_set_approval` |
| **类型** | `human_approval`（人工批准） |
| **超时** | 48 小时 |
| **审批人** | `qa_lead` + `pm`（双人批准） |
| **提示** | "请最终确认 Test Set，批准后将正式生效" |

**说明**:
- `human_review`（审核）: 可以驳回修改，但不阻止流程继续
- `human_approval`（批准）: 必须获得批准才能继续，否则流程阻塞

---

## 九、Instance Schema

### 必填字段
| 字段 | 描述 |
|------|------|
| `id` | 实例 ID |
| `template_id` | 模板 ID |
| `name` | 实例名称 |
| `status` | 状态 |

### 上下文字段
| 字段 | 描述 |
|------|------|
| `module` | 模块名称 |
| `requirement_doc` | 需求文档路径 |
| `tech_design` | 技术设计文档路径（可选） |

### 输出字段
| 字段 | 描述 |
|------|------|
| `test_set_path` | Test Set 文件路径 |
| `analysis_report_path` | 需求分析报告路径 |
| `strategy_draft_path` | 测试策略草稿路径 |
| `review_status` | 审评状态 |

---

## 十、关联 Agent

| Agent ID | 职责 | 所属阶段 |
|---------|------|---------|
| `agent.qa.requirement_analyzer` | 需求分析，提取可测试特性 | Stage 1 |
| `agent.qa.test_strategist` | 测试策略设计，识别风险区域 | Stage 2 |
| `agent.qa.test_set_generator` | 生成标准化 Test Set YAML | Stage 3 |
| `agent.qa.test_set_reviewer` | 审评 Test Set 完整性和可执行性 | Stage 4 |

---

## 十一、与 Test Set L3 执行流程的区别

| 特性 | **Production L3**（本流程） | **Execution L3** |
|------|--------------------------|-----------------|
| **职责** | 生成 Test Set **设计资产** | 执行 Test Set **运行测试** |
| **阶段数** | 4 阶段 | 7 步骤（单阶段） |
| **产出物** | `ts-{module}.yaml`（设计文件） | TSE（执行结果）+ Bug Drafts |
| **人类门禁** | 3 个（审核 + 批准） | 0 个（自动执行） |
| **执行频率** | 一次性（设计阶段） | 多次（每次测试运行） |
| **路径变量** | `{{ qa_specs_dir }}` | `{{ qa_specs_dir }}` + `{{ artifacts_dir }}` |

**关系**:
```
Production L3（设计）          Execution L3（执行）
      ↓                              ↓
生成 Test Set 设计资产    →    执行 Test Set 产生 TSE
(spec/qa/test-sets/)              (.artifacts/qa/test-runs/)
```

---

## 十二、关键设计要点

### 1. 分层治理（Layered Governance）

- **治理层**: `stages` 定义阶段和人类门禁
- **执行层**: `stages[].steps` 执行具体工作
- **优势**: 清晰的职责分离，便于管理和审计

### 2. 人类门禁分级（Human Gate Levels）

| 级别 | 类型 | 作用 | 示例 |
|------|------|------|------|
| **审核** | `human_review` | 提供反馈，可驳回 | 需求分析审核、策略审核 |
| **批准** | `human_approval` | 强制门禁，必须通过 | Test Set 最终批准 |

### 3. 双人批准（Dual Approval）

- Test Set 批准需要 `qa_lead` + `pm` 双人批准
- 确保测试设计同时满足质量和产品需求

### 4. 路径变量化

- 使用 `{{ qa_specs_dir }}` 指向 `spec/qa`（冻结资产目录）
- 使用 `{{ module }}` 动态生成模块相关路径
- 符合 LEE 框架路径变量化规范

---

## 十三、相关文件

- **模板位置**: `spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml`
- **关联 Contract**: `spec-global/departments/qa/contracts/test-set/v1/schema.yaml`
- **关联文档**: `test-set-l3-template.md`（Test Set 执行流程说明）

---

*文档由 LEE 框架自动生成 | 最后更新：2026-03-05*
