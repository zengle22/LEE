# LEE Framework Spec-Global 迁移完成报告

**迁移日期**: 2025-01-23
**更新日期**: 2026-02-11
**状态**: ✅ 完成
**迁移文件数**: 134 个 + DevOps 部门新增 + Dev L2+L3 升级

---

## SSOT 链路补充

- `spec-global` 当前仍是 workflow/contract-first 组织
- 正式 SSOT 主链与 contract 映射见 [SSOT_CONTRACT_CHAIN.md](SSOT_CONTRACT_CHAIN.md)

---

## 迁移统计

### 总体统计
| 类型 | 原始数量 | 已迁移 | 新增 |
|------|----------|--------|------|
| agents | 76 | 76 | 7 |
| skills | 18 | 18 | 0 |
| workflows | 11 | 11 | 4 |
| gates | 9 | 9 | 2 |
| contracts | 7 | 7 | 6 |
| protocols | 2 | 2 | 0 |
| 其他 (schema, template, integration等) | 11 | 11 | 5 |
| **总计** | **134** | **134** | **24** |

### 按目录统计
| 目录 | 文件数 | 说明 |
|------|--------|------|
| core/ | 11 | 核心基础设施 |
| cross/ | 8 | 跨部门协作 |
| departments/dev/ | 48 | 开发部门 (含 L2+L3 升级) |
| departments/prd/ | 8 | 产品部门 |
| departments/qa/ | 35 | 质量保证部门 |
| departments/ui/ | 24 | UI/UX 设计部门 |
| departments/stg/ | 7 | 策略部门 |
| departments/office/ | 4 | 办公室 |
| **departments/devops/** | **~30** | **DevOps 部门（新增）** |

---

## 新目录结构

```
spec-global/
├── core/                           # 核心基础设施
│   ├── constitution.yaml           # 宪法文件
│   ├── agents/                     # Spec 维护类 agents (6)
│   │   ├── agent-spec-maintainer/
│   │   ├── contracts-spec-maintainer/
│   │   ├── gates-spec-maintainer/
│   │   ├── skills-spec-maintainer/
│   │   ├── spec-review/
│   │   └── workflow-spec-maintainer/
│   ├── contracts/                  # 核心契约 (2)
│   │   ├── execution-trace/
│   │   └── plan-contract/
│   ├── protocols/                  # 核心协议 (2)
│   │   ├── knowledge-access/
│   │   └── tool-wrapper/
│   └── skills/                     # 核心技能 (1)
│       └── agent-spec-creator/
│
├── cross/                          # 跨部门协作
│   ├── agents/                     # 跨部门 agents (4)
│   │   ├── analysis-freezer/
│   │   ├── dev-freeze-orchestrator/
│   │   ├── execution-observer/
│   │   └── fact-collector/
│   ├── skills/                     # 跨部门 skills (3)
│   │   ├── contract-template/
│   │   ├── generate-execution-report/
│   │   └── state-validator/
│   └── workflows/                  # 跨部门 workflows (1)
│       └── product-pipeline/
│
└── departments/                    # 各部门 spec
    ├── dev/                        # 开发部门 (48, 含 L2+L3 升级)
    │   ├── rnd_l2_l3_spec.md       # L2+L3 执行规范文档 【新增】
    │   ├── agents/                 # 29 个 agents (含 3 个新增)
    │   │   ├── acceptance-reviewer/
    │   │   ├── ai-engineer/
    │   │   ├── backend-architect/
    │   │   ├── bug-triage/          # 【新增】Bug 分流 Agent
    │   │   ├── code-reviewer/
    │   │   ├── contract-designer/   # 【新增】协议设计 Agent
    │   │   ├── database-engineer/
    │   │   ├── frontend-architect/
    │   │   ├── go-backend-engineer/ # 【v1.2 升级】含 contract 约束
    │   │   ├── plan-architect/
    │   │   ├── qa-engineer/
    │   │   ├── smoke-tester/        # 【新增】冒烟测试 Agent
    │   │   ├── tech-architect/
    │   │   ├── uniapp-frontend-engineer/ # 【v1.3 升级】含 contract 约束
    │   │   └── ... (更多)
    │   ├── contracts/              # 24 个 contracts (含 3 个新增)
    │   │   ├── api-contract/        # 【新增】API 协议 Schema
    │   │   ├── bug-triage-output/   # 【新增】Bug 分流输出 Schema
    │   │   ├── phase-directory-contract/
    │   │   ├── retest-manifest/
    │   │   ├── smoke-test-result/   # 【新增】冒烟结果 Schema
    │   │   └── ... (更多)
    │   ├── gates/                  # 5 个 gates (含 2 个新增)
    │   │   ├── contract-freeze-gate/ # 【新增】协议冻结门禁
    │   │   ├── dev-gate/
    │   │   ├── phase-gate/
    │   │   ├── release-gate/
    │   │   └── smoke-gate/          # 【新增】冒烟测试门禁
    │   ├── skills/                 # 1 个 skill
    │   │   └── planning-methodology/
    │   └── workflows/              # 7 个 workflows (含 2 个 v2)
    │       ├── bug-fix/v1/          # v1 原始版本
    │       ├── bug-fix/v2/          # 【v2 新增】含 Bug 分流
    │       ├── development-pipeline/
    │       ├── dev-retest/
    │       ├── feature/v2/          # 【v2 新增】L2 编排 4 阶段
    │       ├── feature-be-l3/
    │       ├── feature-fe-l3/
    │       ├── feature-integration-l3/
    │       └── ... (更多)
    │
    ├── prd/                        # 产品部门 (8)
    │   ├── agents/                 # 4 个 agents
    │   │   ├── prd-writer/
    │   │   ├── product-goal-analyzer/
    │   │   ├── requirement-alignment/
    │   │   └── requirement-reviewer/
    │   ├── skills/                 # 1 个 skill
    │   │   └── requirement-discovery/
    │   └── workflows/              # 3 个 workflows
    │       ├── product-pipeline/
    │       └── product-to-dev-pipeline/
    │
    ├── qa/                         # 质量保证部门 (35)
    │   ├── agents/                 # 14 个 agents
    │   │   ├── bug-manager/
    │   │   ├── bug-triager/
    │   │   ├── debug-agent/
    │   │   ├── e2e-test-executor/
    │   │   ├── regression-test-executor/
    │   │   ├── smoke-test-executor/
    │   │   ├── system-test-executor/
    │   │   ├── test-case-creator/
    │   │   └── ... (更多)
    │   ├── contracts/              # 15 个 contracts
    │   │   ├── bug-contract/
    │   │   ├── devops-config/
    │   │   ├── test-case/
    │   │   ├── test-plan/
    │   │   └── ... (更多)
    │   ├── gates/                  # 4 个 gates
    │   │   ├── e2e-gate/
    │   │   ├── exit-gate/
    │   │   ├── smoke-gate/
    │   │   └── submission-gate/
    │   └── workflows/              # 4 个 workflows
    │       ├── testing-pipeline/
    │       ├── test-main-pipeline/
    │       └── ... (更多)
    │
    ├── ui/                         # UI/UX 设计部门 (24)
    │   ├── agents/                 # 10 个 agents
    │   │   ├── icon-generator/
    │   │   ├── prototype-designer/
    │   │   ├── ui-contract-generator/
    │   │   ├── ui-contract-validator/
    │   │   ├── ui-design-executor/
    │   │   ├── ui-designer/
    │   │   ├── ui-test-generator/
    │   │   └── ux-review-agent/
    │   ├── contracts/              # 2 个 contracts
    │   │   ├── icon-design-token/
    │   │   └── ux-review-contract/
    │   ├── gates/                  # 2 个 gates
    │   │   ├── ui-gate/
    │   │   └── ui-gate-runner/
    │   ├── skills/                 # 12 个 skills
    │   │   ├── auto-layout-master/
    │   │   ├── design-token-generator/
    │   │   ├── figma-component-builder/
    │   │   ├── figma-design-system/
    │   │   ├── figma-interaction-design/
    │   │   ├── figma-parser/
    │   │   ├── icon-svg-generator/
    │   │   ├── ui-gate-check/
    │   │   ├── ui-prompt-enhancer/
    │   │   ├── variant-system/
    │   │   └── web-prototype-renderer/
    │   └── workflows/              # 1 个 workflow
    │       └── ui-design-pipeline/
    │
    ├── stg/                        # 策略部门 (7)
    │   ├── agents/                 # 7 个 agents
    │   │   ├── business-opportunity-analyzer/
    │   │   ├── business-opportunity-builder/
    │   │   ├── google-keyword-searcher/
    │   │   ├── google-trend-analyzer/
    │   │   ├── industry-structure-analyzer/
    │   │   ├── supply-analyzer/
    │   │   └── user-signal-analyzer/
    │   └── skills/                 # 2 个 skills
    │       ├── product-goal-analysis/
    │       └── value-analysis-guide/
    │
    ├── devops/                     # DevOps 部门 (30+) 【新增】
    │   ├── agents/                 # 5 个 agents
    │   │   ├── devops-architect.agent.yaml        # 架构师
    │   │   ├── devops-implementation.agent.yaml   # 实施工程师
    │   │   ├── devops-verification.agent.yaml    # 验收工程师
    │   │   └── devops-reviewer.agent.yaml        # AI 审查 Agent
    │   ├── contracts/              # 3 个 contracts
    │   │   ├── phase1.architecture.v1.yaml       # Phase 1 验证契约
    │   │   ├── phase2.cicd.v1.yaml               # Phase 2 验证契约
    │   │   └── devops-execution.contract.yaml    # 执行契约
    │   ├── verifier/               # Verifier System 【新增】
    │   │   ├── engine.py                        # 验证引擎
    │   │   ├── config.yaml                       # 引擎配置
    │   │   └── rules/                            # 验证规则
    │   │       ├── devops_phase1_structure.py   # Phase 1 规则
    │   │       └── devops_phase2_structure.py   # Phase 2 规则
    │   ├── workflows/              # 1 个 workflow
    │   │   └── devops-deployment/v1/workflow.yaml # L2 部署工作流
    │   ├── checklists/             # 2 个 checklists
    │   │   ├── devops-human-gate.checklist.yaml
    │   │   └── devops-release-freeze.checklist.yaml
    │   ├── templates/              # 4 个 templates
    │   │   ├── env-config.template.yaml
    │   │   ├── release-version.template.yaml
    │   │   ├── deploy-plan.template.md
    │   │   └── rollback-plan.template.md
    │   ├── examples/               # 6 个 examples
    │   │   ├── docker-compose.yml
    │   │   ├── env-config.dev.yaml
    │   │   ├── env-config.test.yaml
    │   │   ├── deploy-dev-test.sh
    │   │   ├── rollback-dev-test.sh
    │   │   └── ci-cd-github-actions.yaml
    │   ├── demo/                   # 演示文件
    │   │   ├── 00-inputs/
    │   │   ├── 01-architecture/
    │   │   └── test-phase1/
    │   └── docs/                   # 文档
    │       ├── orchestrator-integration.md
    │       ├── verifier-quickstart.md
    │       └── verifier-system-integration.md
    │
    └── office/                     # 办公室 (4)
        ├── agents/                 # 1 个 agent
        │   └── approval-reviewer/
        ├── gates/                  # 1 个 gate
        │   └── phase-acceptance/
        └── skills/                 # 2 个 skills
            ├── dev-gate-check/
            └── release-gate-check/
```

---

## 验证结果

### 文件完整性 ✅
- 所有 134 个源文件都已迁移
- YAML 语法正确
- 文件内容完整

### 示例验证

#### Agent Spec
```yaml
# spec-global/departments/dev/agents/ai-engineer/v1/agent.yaml
kind: agent
version: 1.1
id: agent.dev.ai_engineer
name: AI Engineer
description: AI 工程师，负责 AI 算法实现、Prompt 工程...
```

#### Contract Spec
```yaml
# spec-global/departments/qa/contracts/bug-contract/v1/schema.yaml
kind: contract_schema
version: 1.0
schema:
  type: object
  required: [bug_id, title, severity, ...]
```

#### Gate Spec
```yaml
# spec-global/departments/dev/gates/dev-gate/v1/gate.yaml
kind: gate
version: 1.0
id: gate.dev.dev_gate
name: Dev Gate
description: 代码合并前的开发质量门禁...
```

---

## 使用方式

### 1. 查找 Spec

```bash
# 查找开发部门的 agent
find spec-global/departments/dev/agents -name "agent.yaml"

# 查找所有 gates
find spec-global -name "gate.yaml"

# 查找所有 workflows
find spec-global -name "workflow.yaml"
```

### 2. 引用路径

**旧路径 (已废弃)**:
```
ai-spec/specs/org/development/agents/ai-engineer/v1/agent.yaml
```

**新路径**:
```
spec-global/departments/dev/agents/ai-engineer/v1/agent.yaml
```

### 3. 部门映射

| 旧部门 | 新部门 | 路径 |
|--------|--------|------|
| org/development | dev | `departments/dev/` |
| org/product | prd | `departments/prd/` |
| org/testing | qa | `departments/qa/` |
| common/* (UI相关) | ui | `departments/ui/` |
| common/* (策略相关) | stg | `departments/stg/` |
| common/* (审批相关) | office | `departments/office/` |
| common/* (基础设施) | core | `core/` |
| common/* (跨部门) | cross | `cross/` |
| - | devops | `departments/devops/` (新增) |

### DevOps 部门 (新增)

DevOps 部门负责基础设施和 CI/CD 相关的规范和流程。

**核心特性**:
- **Verifier System**: AI 产物质量验证系统
- **三 Agent 模型**: Architect → Implementation → Verification
- **六阶段工作流**: 从架构设计到版本冻结的完整流程
- **安全边界**: AI 生成模板，人类注入凭证

**主要组件**:
- **Agents**: `devops-architect`, `devops-implementation`, `devops-verification`, `devops-reviewer`
- **Workflow**: `workflow.devops.deployment` (L2 部署工作流)
- **Verifier System**: 自动验证 AI 生成的架构和代码产物
- **Contracts**: 验证契约定义验证规则和标准
- **Examples**: Docker Compose, CI/CD Pipeline, 部署脚本示例

### Dev L2+L3 架构升级 (2026-02-11 新增)

开发部门全面引入 **L2+L3 执行规范**，核心变化：

**核心原则**: 协议先行 (Contract-First)
- Phase 1: Contract 设计 & 冻结
- Phase 2: 前后端并行开发（强制 contract 约束）
- Phase 3: 连调验证
- Phase 4: 冒烟守门（失败不允许 merge）

**新增 Agents (3)**:
- `contract-designer` — 协议设计与版本管理
- `smoke-tester` — 主流程冒烟测试 & merge 守门
- `bug-triage` — Bug 分流（实现 Bug / 协议 Bug）

**升级 Agents (2)**:
- `go-backend-engineer` v1.2 — 返回数据必须符合 contract schema
- `uniapp-frontend-engineer` v1.3 — 类型必须从 contract 生成

**新增 Contracts (3)**:
- `api-contract/v1/schema.json` — API 协议结构定义
- `smoke-test-result/v1/schema.json` — 冒烟测试结果
- `bug-triage-output/v1/schema.json` — Bug 分流输出

**新增 Gates (2)**:
- `contract-freeze-gate` — 协议完整性 & 版本升级检查
- `smoke-gate` — 冒烟通过才允许 merge

**新增/升级 Workflows (2)**:
- `feature/v2/workflow.yaml` — L2 主工作流（4 阶段编排）
- `bug-fix/v2/workflow.yaml` — 含 Bug 分流阶段

**详细规范**: `departments/dev/rnd_l2_l3_spec.md`

---

## 配置系统

LEE 框架使用统一配置文件管理 Executor 和 Agent 的 LLM 配置。

### 配置文件位置

```
lee/config/llm_config.yaml
```

### 配置结构

配置文件使用 YAML 格式，包含以下层级：

| 层级 | 说明 | 示例 |
|------|------|--------|
| **default** | 默认配置，未指定 profile 时使用 | `gpt-4o` |
| **provider** | 预定义 Provider 配置 | `openai`, `anthropic`, `zhipu`, `deepseek`, `antigravity` |
| **agent.* | Agent 级别配置，覆盖 default | `agent.dev`, `agent.prd`, `agent.qa` |

### 环境变量

配置支持通过环境变量覆盖，**优先级：环境变量 > 配置文件默认值**

| 环境变量 | 作用 | 示例 |
|----------|------|--------|
| **LLM_BASE_URL** | API 基础 URL | `https://api.openai.com/v1` |
| **LLM_API_KEY** | API 密钥 | `sk-...` |
| **LLM_MODEL** | 模型名称 | `gpt-4o` |
| **LLM_TEMPERATURE** | 温度参数 (0.0-1.0) | `0.7` |
| **LLM_MAX_TOKENS** | 最大 token 数 | `4000` |
| **LLM_TIMEOUT** | 请求超时(秒) | `60` |
| **LLM_PROFILE** | 默认 profile | `dev` |

### Provider 专用环境变量

| Provider | 环境变量前缀 | 说明 |
|----------|--------------|------|
| OpenAI | `OPENAI_*` | GPT 模型 |
| Anthropic | `ANTHROPIC_*` | Claude 模型 |
| 智谱 GLM | `ZHIPU_*` | 智谱 GLM |
| DeepSeek | `DEEPSEEK_*` | DeepSeek Coder |
| 本地反代 | `ANTIGRAVITY_*` | 开发调试用 |

### Agent 级别配置

不同 Agent 可使用专用配置覆盖默认值：

| Agent | 环境变量 | 温度 | 说明 |
|-------|----------|--------|------|
| `agent.dev` | `DEV_MODEL`, `DEV_TEMPERATURE` | 开发使用较低温度 (0.5) 获得稳定代码 |
| `agent.prd` | `PRD_MODEL`, `PRD_TEMPERATURE` | PRD 需求分析 |
| `agent.qa` | `QA_MODEL`, `QA_TEMPERATURE` | QA 测试分析 |
| `agent.ui` | `UI_MODEL`, `UI_TEMPERATURE` | UI 使用较高温度 (0.8) 获得创意 |
| `agent.devops` | `DEVOPS_MODEL`, `DEVOPS_TEMPERATURE` | DevOps 使用低温度 (0.3) 获得精确配置 |

### 使用示例

#### 方式 1: 使用默认配置

```bash
# 设置通用环境变量
export LLM_API_KEY="sk-your-api-key"
export LLM_MODEL="gpt-4o"

# Executor 将使用 default profile
```

#### 方式 2: 使用指定 Provider

```bash
# 使用智谱 GLM
export ZHIPU_API_KEY="your-zhipu-key"
export LLM_PROFILE="zhipu"

# 使用 DeepSeek
export DEEPSEEK_API_KEY="your-deepseek-key"
export LLM_PROFILE="deepseek"
```

#### 方式 3: Agent 级别配置

```bash
# 为 Dev 部门 Agent 设置专用模型
export DEV_MODEL="gpt-4o"
export DEV_TEMPERATURE="0.3"
export DEV_MAX_TOKENS="8000"

# Agent executor 会自动使用 agent.dev profile
```

### Demo 模式

```bash
# 启用 Mock Executor (跳过真实 LLM 调用)
export LEE_LLM_MOCK="1"

# 或启用 Demo 模式
export LEE_DEMO_MODE="1"
```

### 配置文件示例

```yaml
# config/llm_config.yaml

default:
  type: llm
  provider: openai
  base_url: ${LLM_BASE_URL:-https://api.openai.com/v1}
  api_key: ${LLM_API_KEY}
  model: ${LLM_MODEL:-gpt-4o}
  temperature: ${LLM_TEMPERATURE:-0.7}
  max_tokens: ${LLM_MAX_TOKENS:-4000}
  timeout: ${LLM_TIMEOUT:-60}

# 智谱 GLM (低优先级)
zhipu:
  type: llm
  provider: zhipu
  api_key: ${ZHIPU_API_KEY:-06bc11ad44e3431d8f685bfe3405284e.KlPI5clCIbAb4aOa}
  model: ${ZHIPU_MODEL:-glm-4-plus}
  # ...

# 本地 Ollama (最低优先级，兜底）
ollama:
  type: llm
  provider: ollama
  base_url: ${OLLAMA_BASE_URL:-http://localhost:11434}
  model: ${OLLAMA_MODEL:-qwen2.5}
  # ...

# 华为 DeepSeek (高优先级）
huawei_deepseek:
  type: llm
  provider: huawei_deepseek
  base_url: ${HUWEI_DEEPSEEK_BASE_URL:-https://api.modelarts-maas.com/v2/chat/completions}
  api_key: ${HUWEI_DEEPSEEK_API_KEY:-RgYnotRfG6L7SB-qWJDAt5goaF-z6zpaUlS9QzpfbZtnw3RJk2OtZmR4CKx-vamjWvzqwZpDSkeumPMIHU0MlQ}
  model: ${HUWEI_DEEPSEEK_MODEL:-DeepSeek-R1}
  # ...

agent.dev:
  type: llm
  provider: openai
  model: ${DEV_MODEL:-gpt-4o}
  temperature: ${DEV_TEMPERATURE:-0.5}
  # ...
```

### Profile 优先级

当未指定 `LLM_PROFILE` 时，Executor 按以下顺序尝试不同 Provider（从高到低）：

| 顺序 | Provider | 模型 | 说明 |
|------|----------|------|------|
| 1 | `huawei_deepseek` | DeepSeek-R1 | 华为 ModelArts（需配置 key） |
| 2 | `deepseek` | deepseek-coder-v2 | DeepSeek 官方（需配置 key） |
| 3 | `openai` | gpt-4o | OpenAI GPT-4 |
| 3 | `anthropic` | claude-sonnet-4-5-20250514 | Anthropic Claude |
| 4 | `zhipu` | glm-4-plus | 智谱 GLM-4（需配置 key） |
| 5 | `antigravity` | llama3-70b | 本地反代服务（调试用） |
| 6 | `ollama` | qwen2.5 | 本地 Ollama（兜底） |
| 7 | `default` | gpt-4o | 默认 OpenAI 配置（兜底） |

**注意**：
- 高优先级 Provider (1-4) 需要在 Agent spec 或环境变量中显式指定
- 低优先级 Provider (5-7) 会自动按顺序尝试
- 所有 Provider 都需要配置有效的 API Key

### 代码中使用

```python
from lee.orchestrator.execution.executors import ExecutorFactory

# 使用默认配置
executor = ExecutorFactory.create("llm", profile="default")

# 使用指定 provider
executor = ExecutorFactory.create("llm", profile="zhipu")

# Agent executor (自动选择 agent.dev profile)
executor = ExecutorFactory.create("llm", profile="agent.dev")
```

---

## 后续步骤

### 1. 更新代码引用
需要更新所有引用旧路径的代码：
- Python 代码中的路径字符串
- 配置文件中的路径
- 文档中的路径引用

### 2. 备份旧目录（可选）
```bash
# 备份
mv ai-spec/specs ai-spec/specs.backup

# 验证无误后可以删除
# rm -rf ai-spec/specs.backup
```

### 3. 创建部门 README
为每个部门创建 README.md 说明：
- 部门职责
- 包含的 agents/skills/contracts/gates/workflows
- 使用方式

### 4. 更新 CI/CD
如果有 CI/CD 流程依赖这些 spec，需要更新路径配置。

---

## 迁移脚本

迁移脚本保存在: `scripts/migrate_specs_complete.py`

如需重新迁移：
```bash
python scripts/migrate_specs_complete.py
```

---

## 宪法文件

原 `ai-spec/core.yaml` 已整合进:
```
spec-global/core/constitution.yaml
```

包含：
- 目标与非目标
- 核心原则
- 系统角色
- 工作流模板
- 质量标准
- 治理规则
- 部门组织结构
- 跨部门协作协议

---

## 联系方式

如有问题，请查阅：
- 架构文档: `docs/architecture.md`
- PM Agent 协议: `docs/PM_AGENT_PROTOCOL.md`
- 迁移指南: `docs/ARCHITECTURE-MIGRATION-GUIDE.md`
