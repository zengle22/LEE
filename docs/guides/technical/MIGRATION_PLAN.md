---
title: LEE 框架重组迁移计划 v3
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE 框架重组迁移计划 v3

> 生成时间：2026-01-22
> 状态：待审核

## 一、项目定位

**LEE 框架**是一个通用的 AI 工作流编排系统，作为独立仓库维护，会被其他产品项目引用。

```
┌─────────────────────────────────────────────────────────────────┐
│                        架构关系                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   LEE/ (本项目 - 框架仓库)                                       │
│   ├── flowcore/        # 框架核心代码                           │
│   ├── spec-global/      # 全局规范模板（按部门组织）             │
│   ├── config/           # 配置模板                              │
│   ├── docs/             # 框架文档                              │
│   └── changelogs/       # 变更日志                              │
│          ↑                                                     │
│          │ git submodule / pip 依赖                             │
│          │                                                     │
│   running-coach/ (产品项目)                                      │
│   ├── LEE/             # → lee-framework (submodule)           │
│   ├── project/         # 产品专属内容                          │
│   └── runtime/         # 运行时                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 二、目标结构

```
LEE/                                    # ★ LEE 框架根目录（本项目）
│
├── README.md                           # 框架总览
├── CHANGELOG.md                        # 变更日志（总览）
├── LICENSE                             # 许可证
├── pyproject.toml                      # Python 包配置
│
├── flowcore/                           # ★ 核心代码包
│   ├── __init__.py
│   │
│   ├── orchestrator/                   # 工作流编排器
│   │   ├── __init__.py
│   │   ├── README.md                   # 模块使用文档
│   │   ├── ARCHITECTURE.md             # 架构文档
│   │   ├── DESIGN.md                   # 设计文档
│   │   ├── runner.py                   # 工作流运行器（新建）
│   │   ├── dag_executor.py             # DAG 执行器（新建）
│   │   ├── state_store.py              # 状态存储（新建）
│   │   ├── human_gate.py               # 人工门禁处理（新建）
│   │   ├── io_loader.py                # 输入输出加载器（新建）
│   │   ├── workspace_resolver.py       # 工作空间解析器
│   │   ├── state_machine.py            # 状态机
│   │   ├── event_log.py                # 事件日志
│   │   ├── token_manager.py            # Token 管理
│   │   ├── workflow_parser.py          # Workflow 解析器
│   │   ├── workflow_generator.py       # Workflow 生成器
│   │   ├── agent_context.py            # Agent 上下文
│   │   ├── agent_loader.py             # Agent 加载器
│   │   ├── agent_resolver.py           # Agent 解析器
│   │   ├── trace.py                    # 追踪
│   │   └── tracing_integration.py      # 追踪集成
│   │
│   ├── engines/                        # 执行引擎
│   │   ├── __init__.py
│   │   ├── README.md                   # 引擎系统使用文档
│   │   ├── ARCHITECTURE.md             # 引擎架构文档
│   │   ├── base.py                     # LEE 接口定义（新建）
│   │   ├── python_exec.py              # Python/CLI 执行引擎（新建）
│   │   ├── single_agent.py             # 单 Agent 引擎（新建）
│   │   └── metagpt/                    # MetaGPT 适配层
│   │       ├── __init__.py
│   │       ├── README.md               # MetaGPT 集成文档
│   │       ├── protocol.py             # LEE 协议类型
│   │       ├── adapter.py              # 核心适配器
│   │       ├── scenarios.py            # 场景实现
│   │       └── team_configs/           # 通用 team 模板
│   │
│   ├── utils/                          # 工具模块
│   │   ├── __init__.py
│   │   ├── README.md                   # 工具模块文档
│   │   ├── logging.py
│   │   ├── ids.py                      # ID 生成器（新建）
│   │   ├── timeouts.py                 # 超时处理（新建）
│   │   ├── validation.py               # 验证工具（新建）
│   │   ├── event_bus.py                # 事件总线
│   │   └── template_resolver.py        # 模板解析器
│   │
│   └── cli/                            # 命令行工具
│       ├── __init__.py
│       ├── README.md                   # CLI 使用文档
│       ├── main.py                     # CLI 入口
│       └── commands.py                 # 命令实现
│
├── spec-global/                        # ★ 全局规范模板（按部门组织）
│   │
│   ├── core/                           # LEE 基础规范 & 通用积木
│   │   ├── workflows/                  # 非业务、偏技术/平台的通用流程
│   │   │   ├── _template.yaml
│   │   │   └── test_round.yaml
│   │   ├── work_items/                 # 基础对象定义
│   │   │   ├── bug.yaml
│   │   │   ├── feature.yaml
│   │   │   └── incident.yaml
│   │   ├── gates/                      # 通用门禁策略
│   │   │   ├── test_coverage.yaml
│   │   │   └── release_policy.yaml
│   │   ├── contracts/                  # 通用 contract
│   │   │   └── acceptance_report_contract.yaml
│   │   └── teams/                      # 通用 team 模板
│   │       ├── code_impl_team.yaml
│   │       └── arch_debate_team.yaml
│   │
│   ├── departments/                   # ★ 按部门垂直切分
│   │   │
│   │   ├── stg/                         # 战略部门（新增）
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── market_research.yaml
│   │   │   │   ├── opportunity_analysis.yaml
│   │   │   │   └── supply_analysis.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── business_value_check.yaml
│   │   │   │   └── market_fit_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── business-opportunity-analyzer.yaml
│   │   │   │   ├── supply-analyzer.yaml
│   │   │   │   ├── google-keyword-searcher.yaml
│   │   │   │   ├── google-trend-analyzer.yaml
│   │   │   │   ├── industry-structure-analyzer.yaml
│   │   │   │   └── trend-researcher.yaml
│   │   │   ├── skills/
│   │   │   │   └── market-analysis.yaml
│   │   │   └── contracts/
│   │   │       ├── business-opportunity-contract.yaml
│   │   │       ├── supply-analysis-contract.yaml
│   │   │       └── market-insight-contract.yaml
│   │   │
│   │   ├── prd/                         # 产品部门（原 pm 改名）
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── requirement_intake.yaml
│   │   │   │   ├── prd_writing.yaml
│   │   │   │   └── requirement_review.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── prd_quality_gate.yaml
│   │   │   │   └── requirement_completeness_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── prd-writer.yaml
│   │   │   │   ├── requirement-reviewer.yaml
│   │   │   │   └── product-goal-analyzer.yaml
│   │   │   ├── skills/
│   │   │   │   └── product-planning.yaml
│   │   │   └── contracts/
│   │   │       ├── prd_contract.yaml
│   │   │       ├── user-story-contract.yaml
│   │   │       └── product-goal-contract.yaml
│   │   │
│   │   ├── ui/                          # UI 设计部门（新增）
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── ui_design.yaml
│   │   │   │   └── design_review.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── design_quality_gate.yaml
│   │   │   │   └── design_system_compliance_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── ui-designer.yaml
│   │   │   │   ├── icon-generator.yaml
│   │   │   │   ├── ui-contract-generator.yaml
│   │   │   │   └── ui-contract-validator.yaml
│   │   │   ├── skills/
│   │   │   │   └── design-system.yaml
│   │   │   └── contracts/
│   │   │       └── ui-design-contract.yaml
│   │   │
│   │   ├── dev/                        # 开发部门
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── architecture_design.yaml
│   │   │   │   ├── code_implementation.yaml
│   │   │   │   ├── code_review.yaml
│   │   │   │   └── self_testing.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── code_quality_gate.yaml
│   │   │   │   ├── test_coverage_gate.yaml
│   │   │   │   └── security_review_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── tech-architect.yaml
│   │   │   │   ├── backend-engineer.yaml
│   │   │   │   ├── frontend-engineer.yaml
│   │   │   │   └── code-reviewer.yaml
│   │   │   ├── skills/
│   │   │   │   ├── api-design.yaml
│   │   │   │   └── coding-standards.yaml
│   │   │   └── contracts/
│   │   │       ├── api_spec_contract.yaml
│   │   │       └── design_doc_contract.yaml
│   │   │
│   │   ├── qa/                         # 测试部门
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── test_case_design.yaml
│   │   │   │   ├── test_execution.yaml
│   │   │   │   ├── bug_triage.yaml
│   │   │   │   └── test_report.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── test_pass_rate_gate.yaml
│   │   │   │   └── critical_bugs_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── test-case-creator.yaml
│   │   │   │   ├── test-executor.yaml
│   │   │   │   └── bug-analyzer.yaml
│   │   │   ├── skills/
│   │   │   │   └── test-strategy.yaml
│   │   │   └── contracts/
│   │   │       ├── test_plan_contract.yaml
│   │   │       ├── bug_report_contract.yaml
│   │   │       └── test_report_contract.yaml
│   │   │
│   │   ├── ops/                        # 运维部门
│   │   │   ├── README.md               # 部门说明（迁移后创建）
│   │   │   ├── workflows/
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── monitoring_setup.yaml
│   │   │   │   └── incident_response.yaml
│   │   │   ├── gates/                  # 部门门禁
│   │   │   │   ├── deployment_success_gate.yaml
│   │   │   │   └── uptime_sla_gate.yaml
│   │   │   ├── agents/
│   │   │   │   ├── devops-engineer.yaml
│   │   │   │   └── sre.yaml
│   │   │   ├── skills/
│   │   │   │   └── infrastructure.yaml
│   │   │   └── contracts/
│   │   │       └── deployment_plan_contract.yaml
│   │   │
│   │   └── office/                      # 办公室/行政（新增）
│   │       ├── README.md               # 部门说明（迁移后创建）
│   │       ├── workflows/
│   │       ├── gates/
│   │       ├── agents/
│   │       ├── skills/
│   │       └── contracts/
│   │
│   └── cross/                         # ★ 跨部门流程和接口
│       ├── workflows/                  # E2E/跨部门流程
│       │   ├── stg-prd/
│       │   │   └── market_to_product.yaml
│       │   ├── prd-ui-dev/
│       │   │   └── feature_delivery.yaml
│       │   ├── dev-qa-ops/
│       │   │   └── release_pipeline.yaml
│       │   └── all/
│       │       └── incident_response.yaml
│       │
│       ├── interfaces/                 # 部门间接口/契约
│       │   ├── stg-prd/
│       │   │   └── business_requirement_contract.yaml
│       │   ├── prd-dev/
│       │   │   ├── requirement_package_contract.yaml
│       │   │   └── design_feedback_contract.yaml
│       │   ├── prd-ui/
│       │   │   └── design_requirement_contract.yaml
│       │   ├── ui-dev/
│       │   │   └── ui_spec_contract.yaml
│       │   ├── dev-qa/
│       │   │   ├── test_input_contract.yaml
│       │   │   └── bug_report_contract.yaml
│       │   └── qa-ops/
│       │       └── release_readiness_checklist.yaml
│       │
│       └── teams/                      # 跨部门 team 定义
│           ├── feature_squad.yaml
│           └── incident_swat_team.yaml
│
├── config/                             # 框架级配置
│   ├── logging.yaml                    # 日志配置
│   ├── defaults.yaml                   # 默认配置
│   └── workspace.template.yaml         # Workspace 配置模板
│
├── docs/                               # 框架文档
│   ├── AI-CONSTITUTION.md              # AI 宪法
│   ├── LEE-Overview.md                 # 框架总览
│   ├── LEE-Interface-Spec.md           # 接口规范
│   ├── Workflow-Spec-Guide.md          # Workflow 编写指南
│   ├── Orchestrator-Guide.md           # 编排器指南
│   ├── Integration-Guide.md            # 集成指南
│   ├── MetaGPT-Integration.md          # MetaGPT 集成
│   ├── Workspace-Config.md             # Workspace 配置说明
│   └── Spec-Organization.md            # Spec 组织结构说明
│
├── changelogs/                         # 变更日志
│   ├── README.md                       # 变更日志总览
│   ├── v0.1.0.md                       # 版本 0.1.0 变更
│   └── unreleased.md                   # 未发布的变更
│
├── examples/                           # 框架使用示例
│   ├── minimal_workflow/               # 最小工作流示例
│   ├── code_implementation/            # 代码实现示例
│   └── bug_fix/                        # Bug 修复示例
│
├── tools/                              # 工具脚本
│   ├── migrate.sh                      # 迁移脚本
│   └── update_imports.py               # Import 更新脚本
│
└── tests/                              # 框架测试
    ├── test_orchestrator.py
    ├── test_engines_metagpt.py
    └── test_spec_validation.py
```

## 三、部门结构变化

### 3.1 新增部门

| 部门 | 名称 | 职责 |
|------|------|------|
| **stg** | 战略部门 | 商业机会分析、市场研究、供应链分析、行业洞察 |
| **ui** | UI 设计部门 | UI 设计、设计系统、设计规范 |
| **office** | 办公室/行政 | 暂时不属于其它部门的 spec |

### 3.2 部门重命名

| 原名称 | 新名称 | 说明 |
|--------|--------|------|
| pm | **prd** | 聚焦于产品需求文档（PRD）相关内容 |

### 3.3 每个部门的完整结构

每个部门现在包含 5 个子目录：

```
departments/{dept}/
├── README.md       # 部门说明文档（迁移后创建）
├── workflows/      # 部门工作流
├── gates/          # 部门门禁（新增）
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

### 3.4 Agent 迁移映射

#### 战略部门 (stg)

从 `ai-spec/specs/common/agents/` 迁移到 `spec-global/departments/stg/agents/`：

| 原 Agent | 目标位置 |
|----------|----------|
| business-opportunity-analyzer | stg/agents/ |
| supply-analyzer | stg/agents/ |
| google-keyword-searcher | stg/agents/ |
| google-trend-analyzer | stg/agents/ |
| industry-structure-analyzer | stg/agents/ |
| trend-researcher | stg/agents/ (如果存在) |

#### UI 设计部门 (ui)

从 `ai-spec/specs/common/agents/` 迁移到 `spec-global/departments/ui/agents/`：

| 原 Agent | 目标位置 |
|----------|----------|
| icon-generator | ui/agents/ |
| ui-contract-generator | ui/agents/ |
| ui-contract-validator | ui/agents/ |

#### 产品部门 (prd)

从 `ai-spec/specs/common/agents/` 迁移到 `spec-global/departments/prd/agents/`：

| 原 Agent | 目标位置 |
|----------|----------|
| prd-writer | prd/agents/ |
| product-goal-analyzer | prd/agents/ |
| requirement-reviewer | prd/agents/ |

#### 开发部门 (dev)

从 `ai-spec/specs/common/agents/` 迁移到 `spec-global/departments/dev/agents/`：

| 原 Agent | 目标位置 |
|----------|----------|
| tech-architect | dev/agents/ |
| plan-architect | dev/agents/ |

#### 测试部门 (qa)

从 `ai-spec/specs/common/agents/` 迁移到 `spec-global/departments/qa/agents/`：

| 原 Agent | 目标位置 |
|----------|----------|
| test-case-creator | qa/agents/ |
| e2e-test-executor | qa/agents/ |

## 四、执行步骤

### 阶段 1：准备工作

```bash
# 1. 创建备份
cp -r . ../LEE-backup-$(date +%Y%m%d)

# 2. 创建新目录结构
mkdir -p flowcore/{orchestrator,engines/metagpt,utils,cli}
mkdir -p spec-global/core/{workflows,work_items,gates,contracts,teams}
mkdir -p spec-global/departments/{stg,prd,ui,dev,qa,ops,office}/{workflows,gates,agents,skills,contracts}
mkdir -p spec-global/cross/{workflows,interfaces,teams}
mkdir -p config docs changelogs examples tools tests
```

### 阶段 2：迁移 orchestrator

```bash
# 2.1 移动核心文件（扁平化）
cp orchestrator/core/*.py flowcore/orchestrator/
cp orchestrator/*.py flowcore/orchestrator/ 2>/dev/null || true

# 2.2 移动 CLI
cp orchestrator/__main__.py flowcore/cli/main.py
cp orchestrator/cli.py flowcore/cli/commands.py

# 2.3 移动文档
cp orchestrator/docs/*.md docs/ 2>/dev/null || true
cp orchestrator/README.md docs/Orchestrator-Guide.md
cp orchestrator/INTEGRATION.md docs/Integration-Guide.md

# 2.4 移动示例
cp -r orchestrator/examples/* examples/ 2>/dev/null || true
```

### 阶段 3：迁移 MetaGPT 适配层

```bash
# 3.1 移动适配器代码
cp -r MetaGPT/metagpt/lee/*.py flowcore/engines/metagpt/

# 3.2 移动文档
cp MetaGPT/LEE_ADAPTER_SUMMARY.md docs/MetaGPT-Integration.md
```

### 阶段 4：迁移 ai-spec（按部门重组）

```bash
# 4.1 迁移战略部门 (stg) agents
# 商业机会分析相关
find ai-spec/specs/common/agents -name "*business-opportunity*" -exec cp {} spec-global/departments/stg/agents/ \;
find ai-spec/specs/common/agents -name "*supply*" -exec cp {} spec-global/departments/stg/agents/ \;
find ai-spec/specs/common/agents -name "*google*" -exec cp {} spec-global/departments/stg/agents/ \;
find ai-spec/specs/common/agents -name "*industry*" -exec cp {} spec-global/departments/stg/agents/ \;
find ai-spec/specs/common/agents -name "*trend*" -exec cp {} spec-global/departments/stg/agents/ \;

# 4.2 迁移 UI 设计部门 (ui) agents
find ai-spec/specs/common/agents -name "*ui*" -o -name "*icon*" | xargs -I {} cp {} spec-global/departments/ui/agents/

# 4.3 迁移产品部门 (prd) agents
find ai-spec/specs/common/agents -name "*prd*" -exec cp {} spec-global/departments/prd/agents/ \;
find ai-spec/specs/common/agents -name "*requirement*" -exec cp {} spec-global/departments/prd/agents/ \;
find ai-spec/specs/common/agents -name "*product*" -exec cp {} spec-global/departments/prd/agents/ \;

# 4.4 迁移开发部门 (dev) agents
find ai-spec/specs/common/agents -name "*architect*" -exec cp {} spec-global/departments/dev/agents/ \;
find ai-spec/specs/common/agents -name "*plan*" -exec cp {} spec-global/departments/dev/agents/ \;

# 4.5 迁移测试部门 (qa) agents
find ai-spec/specs/common/agents -name "*test*" -exec cp {} spec-global/departments/qa/agents/ \;
find ai-spec/specs/common/agents -name "*e2e*" -exec cp {} spec-global/departments/qa/agents/ \;

# 4.6 迁移 contracts
find ai-spec/specs/common/contracts -name "*business*" -exec cp {} spec-global/departments/stg/contracts/ \;
find ai-spec/specs/common/contracts -name "*prd*" -o -name "*product*" | xargs -I {} cp {} spec-global/departments/prd/contracts/
find ai-spec/specs/common/contracts -name "*ui*" -exec cp {} spec-global/departments/ui/contracts/ \;

# 4.7 移动核心文档
cp ai-spec/AI-CONSTITUTION.md docs/
cp ai-spec/core.yaml config/defaults.yaml

# 4.8 移动工具（通用部分）
cp -r ai-spec/tools/* tools/ 2>/dev/null || true
```

### 阶段 5：创建新文件

```bash
# 5.1 创建基础接口（手动编写）
# flowcore/engines/base.py

# 5.2 创建配置文件
# config/logging.yaml
# config/workspace.template.yaml

# 5.3 创建包配置
# pyproject.toml
```

### 阶段 6：创建部门 README 文档

```bash
# 迁移完成后，为每个部门创建 README
# (详见第五部分：部门 README 文档结构)
```

### 阶段 7：更新 Import

```bash
# 7.1 更新所有 Python 文件的 import
python tools/update_imports.py

# 7.2 验证语法
python -m py_compile flowcore/**/*.py
```

### 阶段 8：清理和验证

```bash
# 8.1 删除空目录
find . -type d -empty -delete

# 8.2 生成迁移报告
```

## 五、部门 README 文档结构

迁移完成后，为每个部门创建 README.md：

### 5.1 部门 README 模板

每个部门的 README.md 应包含：

```markdown
# {部门名称} (stg/prd/ui/dev/qa/ops/office)

## 部门职责

简要描述该部门的职责和定位。

## 目录结构

```
{部门}/
├── workflows/      # 部门工作流
├── gates/          # 部门门禁
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

## 工作流 (workflows)

列出该部门的所有工作流：

| 工作流 | 说明 | 输入 | 输出 |
|--------|------|------|------|

## 门禁 (gates)

列出该部门的所有门禁：

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|

## Agent 列表

列出该部门的所有 agent：

| Agent | 职责 | 工具 |
|-------|------|------|

## 技能 (skills)

列出该部门的技能：

| 技能 | 说明 |
|------|------|

## 契约 (contracts)

列出该部门的契约：

| 契约 | 说明 | Schema |
|------|------|--------|

## 跨部门协作

列出该部门与其他部门的协作关系：

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
```

### 5.2 各部门 README 重点

#### stg/README.md - 战略部门

- 市场机会分析工作流
- 商业洞察生成流程
- 供应链分析
- 行业趋势研究
- 与 prd 部门的协作接口

#### prd/README.md - 产品部门

- 需求录入流程
- PRD 编写工作流
- 需求评审门禁
- 与 stg/dev/ui 部门的协作

#### ui/README.md - UI 设计部门

- UI 设计工作流
- 设计规范
- 与 prd/dev 部门的协作接口
- 设计系统维护

#### dev/README.md - 开发部门

- 架构设计工作流
- 代码实现流程
- 代码审查门禁
- 与 prd/ui/qa 部门的协作

#### qa/README.md - 测试部门

- 测试用例设计
- 测试执行工作流
- Bug 分析流程
- 与 dev/ops 部门的协作

#### ops/README.md - 运维部门

- 部署工作流
- 监控配置
- 故障响应
- 与 qa 部门的协作

#### office/README.md - 办公室/行政

- 暂时存放不属于其他部门的 spec
- 未来可以独立成新的部门

## 六、Import 路径变化

### 原始

```python
from orchestrator.core.state_machine import StateMachine
from metagpt.lee.protocol import LEERequest
```

### 目标

```python
from flowcore.orchestrator.state_machine import StateMachine
from flowcore.engines.metagpt.protocol import LEERequest
```

## 七、后续工作

迁移完成后：

1. **创建部门 README**：为每个部门创建完善的 README.md
2. **完善代码**：创建 `flowcore/engines/base.py` 等新文件
3. **编写测试**：在 `tests/` 目录添加单元测试
4. **定义跨部门接口**：创建 cross/interfaces/ 下的契约
5. **创建 E2E 工作流**：在 cross/workflows/ 下创建跨部门流程

---

**下一步**：审核本计划，确认后执行 `bash tools/migrate.sh`
