# Product to Dev Skill

> 产品到研发全流程技能 - 将原始需求或商业机会转化为研发冻结包

## 概述

这个 Skill 封装了完整的产品到研发流程，将原始需求或商业机会经过系统化的分析、设计、冻结，最终输出可执行的研发冻结包。

## 触发命令

```
/product-to-dev <需求描述> [options]
```

## 核心价值

将模糊的需求转化为清晰的、可执行的研发输入：

```
原始需求/商业机会
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 价值与需求定义                                      │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│  │ 价值分析 │ → │ 问题翻译 │ → │ 需求拆解 │ → │ 需求评审 │      │
│  └────┬────┘   └─────────┘   └─────────┘   └────┬────┘      │
│       ▼ 🔒                                      ▼ 🔒         │
│   价值冻结                                   需求冻结         │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 详细设计 (可并行)                                   │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                    │
│  │ PRD编写 │   │技术架构 │   │ UI设计  │                     │
│  └────┬────┘   └────┬────┘   └────┬────┘                    │
│       ▼ 🔒          ▼ 🔒          ▼ 🔒                       │
│   PRD冻结       架构冻结        UI冻结                        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 研发冻结                                           │
│  ┌──────────────────┐   ┌──────────────────┐                │
│  │ 冻结包组装 + 5问  │ → │   团队评审确认    │                │
│  └────────┬─────────┘   └────────┬─────────┘                │
│           │                      ▼ 🔒                        │
│           └─────────────→  研发冻结包                         │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
研发冻结包 (JSON + Markdown)
```

## 执行流程详解

### Phase 1: 价值与需求定义

#### Step 1.1: 产品价值分析

**Agent**: `agent.analysis.product_goal`

**输入**: 原始需求或商业机会冻结文档

**输出**: `output/analysis/product-value-proposal.md`

**关键产出**:
- 产品愿景
- 目标用户画像
- 核心价值主张
- 成功指标定义

**思考边界**:
- ✅ 可以思考：产品解决什么问题、目标用户、价值主张
- ❌ 禁止思考：用什么技术、界面设计、具体功能

#### Step 1.2: 产品价值冻结 🔒

**人工门禁**: `h1_value_freeze`

**审批内容**: 产品价值主张是否清晰、正确

**审批选项**:
- 确认价值主张 → 继续
- 返回重新分析
- 终止流程

#### Step 1.3: 问题空间翻译

**Agent**: `agent.product.requirement_alignment`

**输入**: 价值冻结文档

**输出**: `output/analysis/problem-definition.md`

**关键产出**:
- 用户面临的核心问题
- 问题根因分析
- Before/After 用户旅程
- 明确的非目标

#### Step 1.4: 需求单元拆解

**Agent**: `agent.product.requirement_decomposer`

**输入**: 问题定义

**输出**: `output/analysis/requirement-breakdown.md`

**关键产出**:
- 结构化需求列表
- 需求单元边界
- 需求间依赖关系

#### Step 1.5: 需求评审

**Agent**: `agent.review.requirement_reviewer`

**输入**: 价值冻结 + 需求拆解

**输出**: `output/analysis/requirement-review.md`

**关键产出**:
- 需求与价值对齐验证
- 讨论点汇总
- 遗漏项检查

#### Step 1.6: 需求冻结 🔒

**人工门禁**: `h2_requirement_freeze`

**审批内容**: 需求是否与价值目标对齐

### Phase 2: 详细设计 (可并行)

需求冻结后，以下三个步骤可以并行执行：

#### Step 2.1: PRD 详细编写

**Agent**: `agent.product.prd_writer`

**输入**: 需求冻结 + 价值冻结

**输出**:
- `output/prds/{project}-detailed-prd.md`
- `output/prds/{project}-detailed-prd.json`

**关键产出**:
- 功能需求 (P0/P1/P2 分级)
- 非功能需求
- 验收标准
- Out of Scope (为 Q1 提供答案)

#### Step 2.2: PRD 冻结 🔒

**人工门禁**: `h3_prd_freeze`

**审批人**: 产品负责人

#### Step 2.3: 技术架构设计

**Agent**: `agent.dev.tech_architect`

**输入**: 需求冻结 + PRD (可选)

**输出**:
- `output/architecture/{project}-tech-architecture.md`
- `output/architecture/{project}-tech-architecture.json`

**关键产出**:
- 技术选型
- 系统架构图
- API 契约
- 风险评估
- 简化点 (为 Q2 提供答案)
- 不确定性 (为 Q3 提供答案)

#### Step 2.4: 技术架构冻结 🔒

**人工门禁**: `h4_architecture_freeze`

**审批人**: 技术负责人

#### Step 2.5: UI/UX 设计

**Agent**: `agent.design.ui_designer`

**输入**: 需求冻结 + PRD (可选)

**输出**:
- `output/ui-specs/{project}-ui-design.md`
- `output/ui-specs/{project}-ui-design.json`

**关键产出**:
- 用户流程图
- 线框图/原型
- 设计原则
- 组件清单
- UI 优先级划分 (为 Q4 提供答案)

#### Step 2.6: UI 设计冻结 🔒

**人工门禁**: `h5_ui_freeze`

**审批人**: 设计负责人

### Phase 3: 研发冻结

#### Step 3.1: 研发冻结包组装

**Agent**: `agent.dev.freeze_orchestrator`

**输入**: 所有冻结产物

**输出**:
- `output/frozen-packages/{project}-dev-freeze.json`
- `output/frozen-packages/{project}-dev-freeze-review.md`

**5 问排期校验**:

| # | 问题 | 来源 | 校验要点 |
|---|------|------|----------|
| Q1 | 不做什么？ | PRD.out_of_scope | 不能为空 |
| Q2 | 哪些允许先简化？ | 架构.simplification | 至少 1 项 |
| Q3 | 技术最不确定的点？ | 架构.uncertainties | 至少 1 项 |
| Q4 | UI 优先级划分？ | UI.priorities | 必须分类 |
| Q5 | 延期砍减顺序？ | 综合判断 | 必须明确 |

#### Step 3.2: 研发冻结包验证 🔒

**人工门禁**: `h6_dev_freeze`

**审批人**: 产品负责人 + 技术负责人 + 设计负责人

**团队评审检查清单**:
- [ ] PRD 已冻结
- [ ] 技术架构已冻结
- [ ] UI 设计已冻结
- [ ] 5 个问题均有明确答案
- [ ] 团队达成共识

## 输出产物

### 冻结文件清单

```
output/
├── analysis/                           # 分析产物
│   ├── product-value-proposal.md
│   ├── problem-definition.md
│   ├── requirement-breakdown.md
│   └── requirement-review.md
│
├── design-frozen/                      # 设计冻结
│   ├── {project}-value-freeze.md       # 🔒 价值冻结
│   ├── {project}-requirement-freeze.md # 🔒 需求冻结
│   ├── {project}-prd-freeze.md         # 🔒 PRD冻结
│   ├── {project}-architecture-freeze.md # 🔒 架构冻结
│   └── {project}-ui-freeze.md          # 🔒 UI冻结
│
├── prds/                               # PRD 详细文档
│   ├── {project}-detailed-prd.md
│   └── {project}-detailed-prd.json
│
├── architecture/                       # 技术架构
│   ├── {project}-tech-architecture.md
│   └── {project}-tech-architecture.json
│
├── ui-specs/                           # UI 设计
│   ├── {project}-ui-design.md
│   └── {project}-ui-design.json
│
└── frozen-packages/                    # 研发冻结包
    ├── {project}-dev-freeze.json       # 🔒 最终包 (机器可读)
    ├── {project}-dev-freeze-review.md  # 评审文档 (人类可读)
    └── {project}-dev-freeze-final.md   # 🔒 最终确认
```

### 研发冻结包结构

```json
{
  "contract_type": "frozen-dev-package",
  "contract_version": "1.0.0",
  "metadata": {
    "product_name": "产品名称",
    "package_version": "1.0",
    "created_at": "2026-01-13T18:00:00Z",
    "is_frozen": true
  },
  "package_content": {
    "value_freeze_ref": "output/design-frozen/{project}-value-freeze.md",
    "requirement_freeze_ref": "output/design-frozen/{project}-requirement-freeze.md",
    "prd_ref": "output/prds/{project}-detailed-prd.json",
    "tech_arch_ref": "output/architecture/{project}-tech-architecture.json",
    "ui_spec_ref": "output/ui-specs/{project}-ui-design.json"
  },
  "scheduling_validation": {
    "q1_non_goals": ["..."],
    "q2_simplification_points": ["..."],
    "q3_core_uncertainties": ["..."],
    "q4_ui_priorities": {
      "must_define_now": ["..."],
      "can_defer": ["..."]
    },
    "q5_cut_sequence": ["..."],
    "validation_passed": true
  }
}
```

## 使用示例

### 基本用法

```
/product-to-dev 开发一个智能跑步教练App，帮助用户制定训练计划
```

### 从商业机会开始

```
/product-to-dev --from-opportunity output/discovery-frozen/running-coach-opportunity-freeze.md
```

### 指定项目名称

```
/product-to-dev 实现用户订阅支付功能 --project subscription-module
```

## 人工门禁汇总

| 门禁 | 步骤 | 审批人 | 审批内容 |
|------|------|--------|----------|
| h1 | 价值冻结 | 产品负责人 | 价值主张是否清晰正确 |
| h2 | 需求冻结 | 产品负责人 | 需求是否与价值对齐 |
| h3 | PRD冻结 | 产品负责人 | PRD 内容是否完整准确 |
| h4 | 架构冻结 | 技术负责人 | 技术方案是否可行 |
| h5 | UI冻结 | 设计负责人 | UI 设计是否合理 |
| h6 | 研发冻结 | 全体负责人 | 研发包是否可执行 |

## 错误处理

### 审批被拒绝

如果某个冻结步骤被拒绝：

1. 分析拒绝原因
2. 回退到对应的设计步骤
3. 修改后重新提交审批
4. 不影响已完成的其他并行任务

### 5 问校验失败

如果研发冻结包 5 问校验失败：

1. 识别缺失的问题答案
2. 追溯到对应的设计产物补充
3. 重新组装冻结包

## 后续衔接

研发冻结包完成后，可以：

1. 使用 `/dev-execute` 启动研发执行
2. 研发冻结包作为 Phase 的输入依据
3. 进入 Development Pipeline 执行

## 相关资源

- 工作流定义: `ai-spec/specs/org/product/workflows/product-to-dev-pipeline/v1/workflow.yaml`
- 研发冻结协调器: `ai-spec/cli/claude/agents/dev-freeze-orchestrator.md`
- PRD 编写器: `ai-spec/cli/claude/agents/prd-writer.md`
- 技术架构师: `ai-spec/cli/claude/agents/tech-architect.md`
- UI 设计师: `ai-spec/cli/claude/agents/ui-designer.md`

## 预估时间

| 阶段 | 步骤数 | 预估时间 |
|------|--------|----------|
| Phase 1: 价值与需求 | 6 | 4-8 小时 |
| Phase 2: 详细设计 | 6 | 8-16 小时 (可并行) |
| Phase 3: 研发冻结 | 2 | 2-4 小时 |
| **总计** | **14** | **14-28 小时** |

*注: 包含人类审批等待时间*
