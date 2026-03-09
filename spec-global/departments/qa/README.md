# Testing Framework - Complete Guide
# 完整的测试框架使用指南

> **版本:** v2.1
> **更新日期:** 2026-03-03
> **状态:** 生产就绪
> **重大升级:** v2.0 → v2.1 增强 L3 输出验证、DAG 依赖、可观测性

---

## 📋 目录

- [概述](#概述)
- [测试主流程](#测试主流程)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [文件组织](#文件组织)
- [实际示例](#实际示例)
- [文档索引](#文档索引)
- [常见问题](#常见问题)
- [版本变更](#版本变更)

---

## 概述

### 什么是Testing Framework v2.0？

这是一个**工程化的多轮循环测试框架**，支持从需求分析到出测发布的完整测试生命周期管理。

### 核心特性

✅ **双流程架构**
- Test Main Pipeline (主流程) - 管理测试轮次和门禁
- Bug Sub-workflow (子流程) - 独立Bug生命周期管理

✅ **多轮循环机制**
- 支持最多10轮测试迭代
- 渐进式质量收敛，不强制一次性修完所有Bug

✅ **风险回归策略**
- 智能选择回归范围，避免重复劳动
- 效率提升60%

✅ **完整用例管理**
- 需求→计划→套件→用例→脚本→执行→Bug
- 全流程契约化、可追溯

✅ **严格质量门禁**
- 强制标准（0容忍）
- 阈值标准（可豁免）
- 风险可接受标准（需签字）

### 门禁边界更新

新 QA template 流程不再依赖 `_metadata.yaml` 中旧的
`design_input_gate`、`regression_gate`、`test_case_review_gate` 注册项。

当前推荐做法是：

- 在 workflow template 内声明 gate
- 由运行时根据 template 动态生成 gate instance
- 不再为旧 QA workflow id 维护平行 metadata gate 注册

### v2.0 新特性

| 特性 | v1.0 | v2.0 |
|------|------|------|
| 测试轮次 | 单次通过 | 最多10轮循环 |
| Bug处理 | 阻塞式 | 并行式（事件驱动） |
| 回归策略 | 全量回归 | 风险回归 |
| 出测标准 | 修完所有Bug | P0=0, P1≤3, 风险可接受 |
| 用例管理 | 无体系 | 完整契约化 |
| 需求追溯 | 手工维护 | 自动化追溯 |

---

## 测试主流程

### 🎯 全流程概览（从项目启动到出测）

```
┌─────────────────────────────────────────────────────────────┐
│  阶段0: 准备阶段（项目启动后）                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  1. 需求分析 (PRD Review)                                   │
│  2. 编写测试计划 (Test Plan)                                │
│  3. 设计测试用例 (Test Cases)                               │
│  4. 组织测试套件 (Test Suites)                              │
│  5. 实现自动化脚本                                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段1: 提测（研发完成开发）                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  研发提交: release-manifest.yaml                            │
│    - 版本号、Git commit、变更区域                           │
│    - 已知风险、制品清单                                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌═════════════════════════════════════════════════════════════┐
║  循环: Round 1, 2, 3... (最多10轮)                          ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                              ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Round Start: 轮次初始化                             │  ║
║  │  - 创建 test-rounds/round-N/ 目录                   │  ║
║  │  - 创建 test-round.yaml 轮次记录                    │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 1: 提测包预检 (PRECHECK_MANIFEST)             │  ║
║  │  - 验证 release-manifest.yaml 完整性                │  ║
║  │  - 检查必填字段、变更区域、已知风险                  │  ║
║  │  ✅ 通过 → 继续                                     │  ║
║  │  ❌ 失败 → BLOCKED (退回研发)                       │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 2: 环境准备 (ENV_READY)                       │  ║
║  │  - 部署测试版本到测试环境                            │  ║
║  │  - 健康检查 (health check)                          │  ║
║  │  - 准备测试数据                                      │  ║
║  │  ✅ 健康 → 继续                                     │  ║
║  │  ❌ 不健康 → 重试3次 → BLOCKED                      │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 3: 冒烟测试 (SMOKE) ⚠️ 准入门禁               │  ║
║  │  - 执行 SUITE-SMOKE-001 (5-15个P0/P1用例)          │  ║
║  │  - 顺序执行, fail_fast=true                         │  ║
║  │  ✅ 100%通过 → 继续                                 │  ║
║  │  ❌ 任何失败 → BLOCKED (退回研发)                   │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 4: 系统测试执行 (IN_TEST_EXECUTION)           │  ║
║  │  并行执行:                                           │  ║
║  │    ├─ API 测试                                      │  ║
║  │    ├─ E2E 测试 (Chrome/微信)                        │  ║
║  │    └─ 回归测试 (风险回归，非全量)                    │  ║
║  │                                                      │  ║
║  │  测试失败时:                                         │  ║
║  │    → 自动创建 Bug契约 (bugs/BUG-YYYY-NNNN.yaml)    │  ║
║  │    → 发布 test_failure 事件                         │  ║
║  │    → 触发 Bug子流程 (并行运行，不阻塞)               │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 5: 轮次同步 (TRIAGE_SYNC)                     │  ║
║  │  - 盘点所有新发现的Bug                               │  ║
║  │  - 确保所有Bug已分流 (status != new)                │  ║
║  │  - P0/P1 Bug触发Debug Agent分析                     │  ║
║  │  ⏳ 等待所有Bug分流完成                              │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 6: 修复验证循环 (FIX_VERIFY_LOOP)             │  ║
║  │  轮内短循环 (最多5次):                               │  ║
║  │    1. 等待开发修复 (外部等待)                        │  ║
║  │    2. 验证修复 (Fix Verifier Agent)                 │  ║
║  │    3. 回归重跑 (Bug相关用例)                         │  ║
║  │                                                      │  ║
║  │  循环条件:                                           │  ║
║  │    - P0 Bug > 0 → 继续循环                          │  ║
║  │    - 或 P1 Bug > 0 且 循环次数 < 5                  │  ║
║  │  退出条件:                                           │  ║
║  │    - P0 = 0 且 P1 可接受 → 退出循环                 │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Step 7: 轮次签字 (ROUND_SIGNOFF)                   │  ║
║  │  - Exit Evaluator Agent 评估出测标准                │  ║
║  │  - 生成 exit-evaluation.yaml                        │  ║
║  │                                                      │  ║
║  │  决策分支:                                           │  ║
║  │    ✅ 所有标准满足 → RELEASE_CANDIDATE (人类签字)   │  ║
║  │    ⚠️  部分标准未满足 → NEXT_ROUND (下一轮)         │  ║
║  │    ❌ 强制标准未满足 → FAIL (修复后重测)            │  ║
║  │    🚫 超时/无法解决 → BLOCKED (人类决策)            │  ║
║  └────────────────────┬────────────────────────────────┘  ║
║                       ↓                                     ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │  Round End: 轮次归档                                │  ║
║  │  - 冻结 test-rounds/round-N/ 所有文件               │  ║
║  │  - 更新 round_conclusion.yaml                       │  ║
║  │  - 如果 decision=next_round → 回到 Round Start      │  ║
║  │  - 如果 decision=release_candidate → 继续下一阶段   │  ║
║  └─────────────────────────────────────────────────────┘  ║
║                                                              ║
╚══════════════════════════╧═══════════════════════════════════╝
                           ↓ (decision=release_candidate)
┌─────────────────────────────────────────────────────────────┐
│  阶段2: 人类最终签字                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  必需签字:                                                   │
│    ✍️  QA Lead - 质量保证                                   │
│    ✍️  PM - 产品验收                                        │
│    ✍️  Tech Lead - 技术风险                                 │
│                                                              │
│  可选签字:                                                   │
│    ✍️  Security Officer (如有安全Bug)                       │
│    ✍️  Compliance Officer (如有合规要求)                    │
│                                                              │
│  输入材料:                                                   │
│    - test-report-final.yaml                                 │
│    - bugs/ (所有遗留Bug)                                    │
│    - risk-assessment.md                                     │
│    - regression-evidence/                                   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓ (所有签字完成)
┌─────────────────────────────────────────────────────────────┐
│  阶段3: 发布                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  - 生成最终测试报告                                           │
│  - 归档所有测试产物到 test-frozen/                            │
│  - 状态: RELEASED                                            │
└─────────────────────────────────────────────────────────────┘
```

### 🔄 Bug并行流程（独立于主流程）

```
测试失败 (E2E test failed)
  ↓ 自动触发
创建Bug契约 (bugs/BUG-2026-0001.yaml)
  ↓ status: NEW
Bug Triager分流 (自动/人工)
  ↓ status: TRIAGED
  ├─ category=requirement → BLOCKED_PM (产品澄清)
  ├─ needs_human=true → BLOCKED_HUMAN (人类审批)
  ├─ category=env → BLOCKED_ENV (环境修复)
  └─ 正常流程 → ROUTED
       ↓
Debug Agent诊断 (P0/P1自动触发)
  ↓ status: DEBUGGED
Dev修复
  ↓ status: FIXING → FIXED
等待下一轮
  ↓
Fix Verifier验证 (Round N)
  ↓ status: VERIFYING → VERIFIED
关闭
  ↓ status: CLOSED
```

**关键点：**
- Bug流程**并行运行**，不阻塞主流程
- 主流程在TRIAGE_SYNC点**读取**Bug状态
- 主流程在ROUND_SIGNOFF点**评估**Bug是否阻塞出测

---

## 快速开始

### 3步快速启动测试

#### Step 1: 准备测试计划和用例

```bash
# 1. 创建项目测试目录
mkdir -p project/my-project/testing/{test-plans,test-suites,test-cases,test-rounds,bugs}

# 2. 编写测试计划
vi project/my-project/testing/test-plans/PLAN-2026-001.yaml
# 参考: contracts/test-plan/v1/schema.yaml

# 3. 设计测试用例
vi project/my-project/testing/test-cases/F-MODULE-001.yaml
# 参考: contracts/test-case/v1/schema.yaml

# 4. 组织测试套件
vi project/my-project/testing/test-suites/SUITE-SMOKE-001.yaml
# 参考: contracts/test-suite/v1/schema.yaml
```

#### Step 2: 研发提测

```yaml
# project/my-project/testing/release-manifest.yaml
manifest_id: MAN-2026-001
release_version: "1.0.0"
git_commit: a1b2c3d4
target_env: test
changed_areas:
  - module-a
  - module-b
known_risks:
  - risk: "新功能未经生产验证"
    mitigation: "充分回归测试"
```

#### Step 3: 执行测试

```bash
# 方式1: 使用Orchestrator (推荐，如果已实现v2.0)
cd project/my-project/testing
python -m orchestrator init . --workflow ../../../ai-spec/specs/org/testing/workflows/test-main-pipeline/v2/workflow.yaml

# 方式2: 手工执行
npx playwright test tests/smoke/
npx playwright test tests/e2e/

# 测试失败时，手工创建Bug契约
vi bugs/BUG-2026-0001.yaml
```

### 完整示例参考

参考 `../../project/AI跑步教练/testing-v2/` 目录，包含完整的实战示例。

---

## 核心概念

### 1. 契约化管理

所有测试产物都有明确的契约定义：

| 契约类型 | Schema文件 | 用途 |
|---------|-----------|------|
| Test Plan | `contracts/test-plan/v1/schema.yaml` | 整体测试计划 |
| Test Suite | `contracts/test-suite/v1/schema.yaml` | 测试套件组织 |
| Test Case | `contracts/test-case/v1/schema.yaml` | 单个测试用例 |
| Bug Contract | `contracts/bug-contract/v1/schema.yaml` | Bug生命周期 |
| Test Round | `contracts/test-round/v1/schema.yaml` | 测试轮次记录 |

### 2. 双向追溯

**正向追溯（需求→用例）:**
```yaml
# test-cases/F-MODULE-001.yaml
traceability:
  requirement_id: "REQ-2026-001"
  feature_id: "login"
```

**反向追溯（用例→需求）:**
```bash
# 查询某需求的所有用例
find test-cases/ -name "*.yaml" | \
  xargs grep -l "requirement_id: \"REQ-2026-001\""
```

### 3. 出测标准 (Exit Gate v2.0)

#### 强制标准（0容忍，不可豁免）

| 标准 | 要求 | 说明 |
|------|------|------|
| C001: P0 Bug清零 | P0 = 0 | 阻塞核心流程 |
| C002: 冒烟100% | smoke_pass_rate = 100% | 基础环境验证 |
| C003: 核心流程100% | core_flow_pass_rate = 100% | 最小可用产品 |
| C004: 人类介入已决策 | needs_human=true 全部有approver | 高风险Bug背书 |
| C005: API契约无违反 | api_contract_violations = 0 | 集成不破坏 |

#### 阈值标准（可豁免，需人类审批）

| 标准 | 默认阈值 | 保守 | 激进 |
|------|---------|------|------|
| T001: P1 Bug | ≤3 | ≤1 | ≤5 |
| T002: P2 Bug | ≤10 | ≤5 | ≤20 |
| T003: 回归通过率 | ≥95% | ≥98% | ≥90% |
| T004: E2E通过率 | ≥90% | ≥95% | ≥85% |

---

## 文件组织

### 目录结构

```
specs/org/testing/
├── agents/                      # Agent规范 (YAML v1.0)
│   ├── bug-triager/v1/          # Bug分流Agent
│   ├── fix-verifier/v1/         # 修复验证Agent
│   ├── exit-evaluator/v1/       # 出测评估Agent
│   └── ... (更多Agents)
│
├── contracts/                   # 数据契约 (JSON Schema)
│   ├── test-plan/v1/            # 测试计划契约
│   ├── test-suite/v1/           # 测试套件契约
│   ├── test-case/v1/            # 测试用例契约
│   ├── bug-contract/v1/         # Bug契约
│   ├── test-round/v1/           # 测试轮次契约
│   └── release-manifest/v1/     # 提测包清单契约
│
├── gates/                       # 质量门禁
│   ├── submission-gate/v1/      # 提测包完整性门禁
│   ├── smoke-gate/v1/           # 冒烟测试门禁
│   └── exit-gate/v2/            # 出测门禁 v2.0
│
├── workflows/                   # 工作流定义
│   ├── test-main-pipeline/v2/   # 主流程 v2.0
│   ├── test-orchestration-pipeline/v1/  # L3 测试编排工作流 v1.0
│   └── bug-sub-workflow/v1/     # Bug子流程 v1.0
│
├── guides/                      # 使用指南
│   └── test-case-management-guide.md  # 用例管理完整指南
│
└── README.md                    # 本文档
```

### 项目测试目录

```
project/my-project/testing/
├── test-plans/                  # 测试计划
│   └── PLAN-2026-001.yaml
│
├── test-suites/                 # 测试套件
│   ├── SUITE-SMOKE-001.yaml
│   ├── SUITE-E2E-001.yaml
│   └── SUITE-REGRESSION-001.yaml
│
├── test-cases/                  # 测试用例
│   ├── F-BASE-001.yaml
│   ├── F-BASE-002.yaml
│   └── F-MODULE-*.yaml
│
├── test-rounds/                 # 测试轮次记录
│   ├── round-001/
│   │   ├── test-round.yaml
│   │   ├── smoke-report.json
│   │   └── evidence/
│   └── round-002/
│
├── bugs/                        # Bug契约
│   ├── BUG-2026-0001.yaml
│   └── BUG-2026-*.yaml
│
├── release-manifest.yaml        # 提测包清单
└── test-report-final.yaml       # 最终测试报告
```

---

## 实际示例

### AI Marathon Coach v1.1 实战

查看完整实战示例：
- [Testing Summary](../../project/AI跑步教练/testing-v2/TESTING-SUMMARY.md)
- [Test Case Management](../../project/AI跑步教练/testing-v2/TEST-CASE-MANAGEMENT-SUMMARY.md)

**关键成果：**
- 2轮测试完成（1天）
- 1个P0 Bug修复验证
- 测试通过率: 冒烟100%, E2E 100%, 回归100%
- 所有出测标准满足 ✅

---

## 文档索引

### 核心规范

| 文档 | 路径 | 用途 |
|------|------|------|
| Test Main Pipeline v2.0 | `workflows/test-main-pipeline/v2/workflow.yaml` | 主流程定义 |
| Test Orchestration Pipeline v1.0 (L3) | `workflows/test-orchestration-pipeline/v1/workflow.yaml` | 测试编排与结果收敛 |
| Bug Sub-workflow v1.0 | `workflows/bug-sub-workflow/v1/workflow.yaml` | Bug子流程 |
| Bug Contract Schema | `contracts/bug-contract/v1/schema.yaml` | Bug契约格式 |
| Test Case Schema | `contracts/test-case/v1/schema.yaml` | 测试用例格式 |
| Test Result Schema | `contracts/test-result/v1/schema.yaml` | 测试执行结果格式 |
| Test Execution Bundle Schema | `contracts/test-execution-bundle/v1/schema.yaml` | 测试执行输入包格式 |
| Exit Gate v2.0 | `gates/exit-gate/v2/gate.yaml` | 出测标准 |
| Test Execution Gate v1.0 | `gates/test-execution-gate/v1/gate.yaml` | 测试执行门禁规则 |

### 使用指南

| 文档 | 字数 | 内容 |
|------|------|------|
| [Workflow USAGE-GUIDE](workflows/test-main-pipeline/v2/USAGE-GUIDE.md) | 10,000+ | 双流程架构、7个阶段详解 |
| [L3 Test Orchestration USAGE-GUIDE](workflows/test-orchestration-pipeline/v1/USAGE-GUIDE.md) | 8,000+ | 测试编排与结果收敛工作流使用指南 |
| [Test Case Management Guide](guides/test-case-management-guide.md) | 15,000+ | 需求→用例全流程 |

---

## 常见问题

### Q1: v2.0与v1.0的主要区别？

**A:**

| 特性 | v1.0 | v2.0 |
|------|------|------|
| 架构 | 单流程 | 双流程（主流程+Bug子流程） |
| Bug处理 | 阻塞式 | 并行式 |
| 测试轮次 | 单次 | 最多10轮 |
| 用例管理 | 无 | 完整契约化 |

### Q2: 如何开始使用v2.0？

**A:** 参考 [快速开始](#快速开始) 章节

### Q3: 测试用例如何管理？

**A:** 参考 [Test Case Management Guide](guides/test-case-management-guide.md)

### Q4: 如何防止自证闭环？

**A:** 严格角色权限，验证规则: `verified_by != owner_agent`

---

## 版本管理规则

### 文件命名规范

所有规范文件（contracts、agents、skills、gates、workflows）遵循以下命名规则：

1. **不带版本号后缀**：文件名不包含版本号，如 `test-plan-l2-template.yaml`
2. **版本在文件内部声明**：通过 `version` 字段注明当前版本
3. **只保留最新版本**：目录中只保留一个最新版本的文件

### 示例

```yaml
# test-plan-l2-template.yaml
kind: l2_workflow_template
version: "2.1"  # 版本号在此声明
id: template.qa.test_plan_l2
name: Test Plan Execution L2 Template
...
```

### 版本升级流程

1. 直接修改现有文件，更新 `version` 字段
2. 在 README.md 的「版本变更」章节记录变更内容
3. **不要**创建带版本号后缀的新文件（如 `-v2.1`）

### 为什么这样设计？

- ✅ 避免文件冗余（无需同时维护多个版本）
- ✅ 简化引用路径（`workflow-registry.yaml` 无需更新）
- ✅ 强制使用最新版本（防止误用旧版本）
- ✅ 历史记录通过 Git 管理（无需文件级版本存档）

---

## 版本变更

### v2.0 (2026-01-15) - 重大升级

**新增:**
- ✅ 双流程架构（主流程 + Bug子流程）
- ✅ 多轮循环机制（最多10轮）
- ✅ 风险回归策略
- ✅ 完整用例管理体系（Test Plan/Suite/Case Contract）
- ✅ 3个新Agent（Bug Triager, Fix Verifier, Exit Evaluator）
- ✅ Orchestrator v2.0支持（Event Bus, Template Resolver）
- ✅ 需求追溯矩阵

**改进:**
- 出测标准工程化（强制/阈值/风险三层）
- Bug契约增强（防自证、角色权限）
- 测试轮次记录标准化

**文档:**
- 2个完整使用指南（25,000+ words）
- 实战示例（AI Marathon Coach）

### v1.0 (2025-12-01) - 初始版本

- 基础测试流程
- Bug契约管理
- 简单门禁控制

---

## 📞 联系与反馈

- **维护者:** test-governance
- **最后更新:** 2026-01-15
- **版本:** v2.0
- **反馈:** 提交Issue到项目仓库

---

**🎉 Testing Framework v2.0 - 生产就绪，可投入使用！**
