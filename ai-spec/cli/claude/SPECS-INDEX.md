# Specs 引用索引

本文件记录 `cli/claude` 目录与 `specs/` 目录的对应关系，确保 Claude Code 可以访问所有通用规范。

## 目录结构关系

```
ai-spec/
├── specs/common/                    # 通用规范（源头）
│   ├── agents/                      # Agent YAML v1.0 规范
│   ├── contracts/                   # 数据契约 (JSON Schema)
│   ├── skills/                      # 技能规范
│   ├── workflows/                   # 工作流定义
│   └── gates/                       # 质量门禁规范 (UI)
│
├── specs/org/                       # 组织/部门专属规范
│   ├── product/                     # 产品部门规范
│   │   ├── agents/                  # 产品 Agents
│   │   ├── contracts/               # 产品契约
│   │   └── workflows/               # 产品流水线
│   │
│   ├── development/                 # 研发部门规范 (新增)
│   │   ├── agents/                  # 研发 Agents (Phase Retrospector 等)
│   │   ├── contracts/               # 研发契约 (Phase Contract)
│   │   ├── skills/                  # 研发技能 (OpenSpec, TDD 等)
│   │   ├── gates/                   # 研发门禁 (Phase/Dev/Release Gate)
│   │   └── workflows/               # 研发流水线 (Development Pipeline)
│   │
│   └── running-coach/ui/            # 跑步AI教练 UI 契约示例
│
└── cli/claude/                      # Claude Code 插件（派生）
    ├── agents/                      # Agent MD 版本（基于 specs 生成）
    ├── skills/                      # Skill MD 版本（基于 specs 生成）
    ├── commands/                    # 命令定义
    └── templates/                   # 模板文件
```

## Agents 对应表

| cli/claude/agents | specs/common/agents | 状态 |
|-------------------|---------------------|------|
| fact-collector.md | fact-collector/v1/agent.yaml | ✅ 同步 |
| google-keyword-searcher.md | google-keyword-searcher/v1/agent.yaml | ✅ 同步 |
| google-trend-analyzer.md | google-trend-analyzer/v1/agent.yaml | ✅ 同步 |
| user-signal-analyzer.md | user-signal-analyzer/v1/agent.yaml | ✅ 同步 |
| supply-analyzer.md | supply-analyzer/v1/agent.yaml | ✅ 同步 |
| industry-structure-analyzer.md | industry-structure-analyzer/v1/agent.yaml | ✅ 同步 |
| business-opportunity-analyzer.md | business-opportunity-analyzer/v1/agent.yaml | ✅ 同步 |
| business-opportunity-builder.md | business-opportunity-builder/v1/agent.yaml | ✅ 同步 |
| product-goal-analyzer.md | product-goal-analyzer/v1/agent.yaml | ✅ 同步 |
| requirement-reviewer.md | requirement-reviewer/v1/agent.yaml | ✅ 同步 |
| approval-reviewer.md | approval-reviewer/v1/agent.yaml | ✅ 同步 |
| analysis-freezer.md | analysis-freezer/v1/agent.yaml | ✅ 同步 |
| plan-architect.md | plan-architect/v1/agent.yaml | ✅ 同步 |
| prototype-designer.md | prototype-designer/v1/agent.yaml | ✅ 同步 |
| prd-writer.md | prd-writer/v1/agent.yaml | ✅ 同步 |
| tech-architect.md | tech-architect/v1/agent.yaml | ✅ 同步 |
| ui-designer.md | ui-designer/v1/agent.yaml | ✅ 同步 |
| **ui-design-executor.md** | **ui-design-executor/v1/agent.yaml** | ✅ 同步 (新增) |
| **ui-contract-generator.md** | **ui-contract-generator/v1/agent.yaml** | ✅ 同步 |
| **ui-contract-validator.md** | **ui-contract-validator/v1/agent.yaml** | ✅ 同步 |
| **ui-test-generator.md** | **ui-test-generator/v1/agent.yaml** | ✅ 同步 |
| **ui-gate-runner.md** | **ui-gate-runner/v1/agent.yaml** | ✅ 同步 |
| dev-freeze-orchestrator.md | dev-freeze-orchestrator/v1/agent.yaml | ✅ 同步 |
| spec-review.md | spec-review/v1/agent.yaml | ✅ 同步 |
| agent-spec-maintainer.md | agent-spec-maintainer/v1/agent.yaml | ✅ 同步 |
| **phase-acceptance-gate.md** | **phase-acceptance-gate/v1/agent.yaml** | ✅ 同步 (新增) |

### Development Pipeline Agents (org/development)

| specs/org/development/agents | 说明 | 状态 |
|------------------------------|------|------|
| **development-planner/v1/agent.yaml** | 研发计划 Agent (新增) | ✅ 新增 |
| **development-scheduler/v1/agent.yaml** | 研发调度执行 Agent (新增) | ✅ 新增 |
| **requirement-calibrator/v1/agent.yaml** | 需求校准 Agent | ✅ 迁移 |
| **test-contract-generator/v1/agent.yaml** | 测试契约生成 Agent | ✅ 迁移 |
| **openspec-proposal-creator/v1/agent.yaml** | OpenSpec 提案创建 Agent | ✅ 迁移 |
| **implementation-executor/v1/agent.yaml** | 代码实现执行 Agent | ✅ 迁移 |
| **code-reviewer/v1/agent.yaml** | 代码审查 Agent | ✅ 迁移 |
| **phase-retrospector/v1/agent.yaml** | Phase 复盘 Agent | ✅ 迁移 |
| **phase-planner/v1/agent.yaml** | Phase 规划 Agent | ✅ 迁移 |
| **integration-planner/v1/agent.yaml** | 集成规划 Agent | ✅ 迁移 |
| **e2e-test-planner/v1/agent.yaml** | E2E 测试规划 Agent | ✅ 迁移 |
| **acceptance-reviewer/v1/agent.yaml** | 验收审查 Agent | ✅ 迁移 |

### Professional Role Agents (org/development) - v3.4.0 重构版

> **重构原则**: 减少角色重叠、补齐门禁职责、接口/契约做成硬边界、高耦合点前置对齐

#### 核心决策层

| Agent | 说明 | 契约 | 状态 |
|-------|------|------|------|
| **tech-lead/v1/agent.yaml** | **技术负责人** (单点架构决策 + ADR机制) | ADR Output | ✅ 新增 |
| **delivery-gate/v1/agent.yaml** | **交付门禁** (放行判定 + 阻塞项列表) | Gate I/O | ✅ 新增 |

#### 架构师（降级为 Specialist，由 Tech Lead 召唤）

| Agent | 说明 | 契约 | 状态 |
|-------|------|------|------|
| **frontend-architect/v1/agent.yaml** | 前端架构 Specialist (重大变更/疑难问题) | 需人类确认 | ⚠️ 降级 |
| **backend-architect/v1/agent.yaml** | 后端架构 Specialist (重大变更/疑难问题) | 需人类确认 | ⚠️ 降级 |

#### 实现层

| Agent | 说明 | 契约 | 状态 |
|-------|------|------|------|
| **go-backend-engineer/v1/agent.yaml** | Go 后端工程师 (功能实现/Bug修复) | 标准契约 | ✅ |
| **uniapp-frontend-engineer/v1/agent.yaml** | UniApp 前端工程师 (功能实现/Bug修复) | 标准契约 | ✅ |
| **database-engineer/v1/agent.yaml** | **数据 Owner** (Schema设计 + Migration Contract) | Migration Contract | ✅ 升级 |
| **ai-engineer/v1/agent.yaml** | **AI 工程师** (三类Contract: Prompt/Routing/Eval) | AI Contracts | ✅ 升级 |

#### 测试层（硬边界切分）

| Agent | 说明 | 硬边界 | 状态 |
|-------|------|--------|------|
| **qa-engineer/v1/agent.yaml** | **QA** (只负责测试设计) | 产物: Test Case Contract | ✅ 重构 |
| **test-automation-engineer/v1/agent.yaml** | **SDET** (只负责测试代码+稳定性) | 输入: QA Contract | ✅ 重构 |

> **硬边界**: QA 写"标准"，SDET 写"实现"，DevOps 保"场地"

#### 运维与安全层

| Agent | 说明 | 新增职责 | 状态 |
|-------|------|----------|------|
| **devops-engineer/v1/agent.yaml** | **DevOps** (CI-CD + 测试环境 + 迁移执行) | + 测试环境基础设施 | ✅ 升级 |
| **secops/v1/agent.yaml** | **SecOps (轻量)** (安全扫描 + 阻断策略) | 新增 | ✅ 新增 |

#### 质量审查层

| Agent | 说明 | 契约 | 状态 |
|-------|------|------|------|
| **ui-implementation-reviewer/v1/agent.yaml** | **UI 实现审查** (还原度/设计系统/跨端/A11y) | Review Output | ✅ 新增 |

## Skills 对应表

| cli/claude/skills | specs/common/skills | 状态 |
|-------------------|---------------------|------|
| product-goal-analysis.md | product-goal-analysis/v1/skill.md | ✅ 同步 |
| value-analysis-guide.md | value-analysis-guide/v1/skill.md | ✅ 同步 |
| requirement-discovery.md | requirement-discovery/v1/skill.md | ✅ 同步 |
| planning-methodology.md | planning-methodology/v1/skill.md | ✅ 同步 |
| figma-import-guide.md | figma-import-guide/v1/skill.md | ✅ 同步 |
| agent-spec-creator.md | agent-spec-creator/v1/skill.md | ✅ 同步 |
| commit-all.md | - | ✅ CLI 专属 |
| **dev-execute.md** | - | ✅ CLI 专属 (新增) |
| **product-to-dev.md** | - | ✅ CLI 专属 (新增) |
| **testing-pipeline.md** | - | ✅ CLI 专属 (新增) |

**specs/common/skills 新增 (YAML v1.0 格式)**:

### UI 契约 Skills
| specs skill | 说明 |
|-------------|------|
| figma-parser/v1/skill.yaml | 解析 Figma 设计链接 |
| contract-template/v1/skill.yaml | 生成契约模板 |
| state-validator/v1/skill.yaml | 验证 UI 状态完整性 |

### Gate 检查 Skills
| specs skill | 说明 |
|-------------|------|
| ui-gate-check/v1/skill.yaml | 执行 UI Gate 检查 |
| dev-gate-check/v1/skill.yaml | 执行 Dev Gate 检查 |
| release-gate-check/v1/skill.yaml | 执行 Release Gate 检查 |

### Figma 设计 Skills (新增)
| specs skill | 说明 |
|-------------|------|
| figma-design-system/v1/skill.yaml | Figma 设计系统创建 |
| figma-component-builder/v1/skill.yaml | Figma 组件构建 (Auto Layout + Variants) |
| figma-interaction-design/v1/skill.yaml | Figma 交互原型设计 (hover/focus/disabled/error) |
| design-token-generator/v1/skill.yaml | Design Token 生成 (W3C DTCG 1.0) |
| auto-layout-master/v1/skill.yaml | Figma Auto Layout 技能 |
| variant-system/v1/skill.yaml | Figma 变体系统技能 |

### Development Pipeline Skills (org/development)
| specs/org/development/skills | 说明 | 状态 |
|------------------------------|------|------|
| **openspec-integration/v1/skill.md** | OpenSpec CLI 集成 | ✅ 迁移 |
| **test-driven-development/v1/skill.md** | TDD 方法论 | ✅ 迁移 |
| **knowledge-extraction/v1/skill.md** | 知识提炼转换 | ✅ 迁移 |
| **phase-contract-management/v1/skill.md** | Phase Contract 管理 | ✅ 迁移 |

## UI Contracts

UI 契约存放在 `specs/common/contracts/` 目录：

| 契约 | 路径 | 说明 |
|------|------|------|
| UI Page Contract | ui-page-contract/v1/schema.json | 页面契约规范 |
| UI Component Contract | ui-component-contract/v1/schema.json | 组件契约规范 |
| UI Tokens Contract | ui-tokens-contract/v1/schema.json | 设计 Token 规范 |
| UI Map Contract | ui-map-contract/v1/schema.json | UI 索引规范 |
| UI A11y Contract | ui-a11y-contract/v1/schema.json | 可访问性规范 |

### Development Pipeline Contracts (org/development)
| 契约 | 路径 | 说明 |
|------|------|------|
| **Phase Directory Structure** | **specs/org/development/contracts/phase-directory-structure/v1/spec.md** | Phase 目录结构规范 ✅ 新增 |
| **Execution State Contract** | **specs/org/development/contracts/execution-state/v1/schema.json** | 工作流执行状态契约 ✅ 新增 |
| **Development Plan Contract** | **specs/org/development/contracts/development-plan-contract/v1/schema.json** | 研发计划契约 |
| **Phase Contract** | **specs/org/development/contracts/phase-contract/v1/schema.json** | Phase 研发契约 |

### Professional Role Contracts (org/development) - v3.5.0 新增

> **核心决策层契约**

| 契约 | 路径 | 用途 |
|------|------|------|
| **ADR Output** | specs/org/development/contracts/adr-output/v1/schema.json | Tech Lead 架构决策记录 |
| **Delivery Gate Input** | specs/org/development/contracts/delivery-gate-input/v1/schema.json | 交付门禁输入 (覆盖率/E2E/安全) |
| **Delivery Gate Output** | specs/org/development/contracts/delivery-gate-output/v1/schema.json | 交付门禁判定 (PASS/FAIL/阻塞项) |

> **测试层契约（硬边界）**

| 契约 | 路径 | 用途 |
|------|------|------|
| **QA Input** | specs/org/development/contracts/qa-input/v1/schema.json | QA 工程师输入 (需求/变更/Bug) |
| **Test Case Contract** | specs/org/development/contracts/test-case-contract/v1/schema.json | QA→SDET 测试用例契约 |

> **数据层契约**

| 契约 | 路径 | 用途 |
|------|------|------|
| **Migration Contract** | specs/org/development/contracts/migration-contract/v1/schema.json | 数据库迁移契约 (可逆/兼容/分阶段) |

> **AI 工程契约**

| 契约 | 路径 | 用途 |
|------|------|------|
| **AI Engineering Output** | specs/org/development/contracts/ai-engineering-output/v1/schema.json | AI 工程师三类契约输出 |

> **安全与质量审查契约**

| 契约 | 路径 | 用途 |
|------|------|------|
| **Security Check Input** | specs/org/development/contracts/security-check-input/v1/schema.json | SecOps 安全扫描输入 |
| **Security Report Output** | specs/org/development/contracts/security-report-output/v1/schema.json | SecOps 安全报告输出 |
| **UI Review Input** | specs/org/development/contracts/ui-review-input/v1/schema.json | UI 实现审查输入 |
| **UI Review Output** | specs/org/development/contracts/ui-review-output/v1/schema.json | UI 实现审查输出 |

## Gates

### Common Gates (specs/common/gates/)

| Gate | 路径 | 说明 |
|------|------|------|
| UI Gate | ui-gate/v1/gate.yaml | 设计阶段门禁 |

### Development Gates (specs/org/development/gates/)

| Gate | 路径 | 说明 |
|------|------|------|
| **Phase Gate** | **phase-gate/v1/gate.yaml** | Phase 完成门禁 |
| **Dev Gate** | **dev-gate/v1/gate.yaml** | 开发阶段门禁 (PR) |
| **Release Gate** | **release-gate/v1/gate.yaml** | 发布阶段门禁 |

每个 Gate 包含:
- `gate.yaml` - 机器可读的规则定义

## Workflows 引用

### Common Workflows (specs/common/workflows/)

| Workflow | 路径 | 说明 |
|----------|------|------|
| Product Pipeline | product-pipeline/v1/workflow.yaml | 产品决策流水线 (Stage 2) |
| **UI Design Pipeline** | **ui-design-pipeline/v1/workflow.yaml** | UI 设计流水线 |

### Product Workflows (specs/org/product/workflows/)

| Workflow | 路径 | 说明 |
|----------|------|------|
| **Product Pipeline** | **product-pipeline/v1/workflow.yaml** | 产品流水线 (需求冻结) |
| **Product to Dev Pipeline** | **product-to-dev-pipeline/v1/workflow.yaml** | 产品到研发全流程 ✅ 新增 |

### Development Workflows (specs/org/development/workflows/)

| Workflow | 路径 | 说明 |
|----------|------|------|
| **Development Pipeline** | **development-pipeline/v1/workflow.yaml** | 研发流水线 (Stage 3) |
| **Phase OpenSpec Flow** | **phase-openspec-flow/v1/workflow.yaml** | Phase 内 OpenSpec 子流程 |
| **Workflow Enforcement** | **enforcement/v1/spec.md** | 通用工作流强制执行规范 ✅ 新增 |
| **CLI Adapters** | **enforcement/v1/adapters.md** | CLI 适配层文档 (Claude/Cursor/Codex) ✅ 新增 |

### Testing Workflows (specs/org/testing/workflows/)

| Workflow | 路径 | 说明 |
|----------|------|------|
| **Testing Pipeline** | **testing-pipeline/v1/workflow.yaml** | 测试流水线 (研发下游) ✅ 新增 |

### Testing Agents (specs/common/agents/ + specs/org/testing/agents/)

| Agent | 路径 | 说明 |
|-------|------|------|
| **e2e-test-executor** | **specs/common/agents/e2e-test-executor/v1/agent.yaml** | E2E 测试执行器 (Docker + Playwright) ✅ 新增 |
| **Test Env Admin** | **specs/org/testing/agents/test-env-admin/v1/agent.yaml** | 测试环境管理员 ✅ 新增 |
| **E2E Test Executor (legacy)** | **specs/org/testing/agents/e2e-test-executor/v1/agent.yaml** | E2E 测试执行器（旧版） |
| **Smoke Test Executor** | **specs/org/testing/agents/smoke-test-executor/v1/agent.yaml** | 冒烟测试执行器 |
| **System Test Executor** | **specs/org/testing/agents/system-test-executor/v1/agent.yaml** | 系统测试执行器 |
| **Debug Agent** | **specs/org/testing/agents/debug-agent/v1/agent.yaml** | 缺陷诊断 Agent |
| **Bug Manager** | **specs/org/testing/agents/bug-manager/v1/agent.yaml** | Bug 管理 Agent |
| **Regression Test Executor** | **specs/org/testing/agents/regression-test-executor/v1/agent.yaml** | 回归测试执行器 |
| **Test Report Generator** | **specs/org/testing/agents/test-report-generator/v1/agent.yaml** | 测试报告生成器 |
| **Release Manifest Reviewer** | **specs/org/testing/agents/release-manifest-reviewer/v1/agent.yaml** | 提测包审核 Agent |
| **Release Gate Reviewer** | **specs/org/testing/agents/release-gate-reviewer/v1/agent.yaml** | 出测门禁审核 Agent |

### Testing Skills (specs/common/skills/ + specs/org/testing/skills/)

| Skill | 路径 | 说明 |
|-------|------|------|
| **e2e-runner** | **specs/common/skills/e2e-runner/v1/skill.yaml** | E2E Runner (Docker + Playwright) ✅ 新增 |
| **Server Connect** | **specs/org/testing/skills/server-connect/v1/skill.md** | SSH 服务器连接 ✅ 新增 |
| **Docker Deploy** | **specs/org/testing/skills/docker-deploy/v1/skill.md** | Docker 容器部署 ✅ 新增 |
| **Health Check** | **specs/org/testing/skills/health-check/v1/skill.md** | 服务健康检查 ✅ 新增 |
| **DB Init** | **specs/org/testing/skills/db-init/v1/skill.md** | 数据库初始化 ✅ 新增 |
| **Config Inject** | **specs/org/testing/skills/config-inject/v1/skill.md** | 配置注入 ✅ 新增 |
| **Browser Runner** | **specs/org/testing/skills/browser-runner/v1/skill.md** | Chrome 浏览器自动化 |
| **WeChat Sandbox Runner** | **specs/org/testing/skills/wechat-sandbox-runner/v1/skill.md** | 微信小程序沙箱 |
| **Selector Page Model** | **specs/org/testing/skills/selector-page-model/v1/skill.md** | 页面对象模型 |
| **Assertion Oracle** | **specs/org/testing/skills/assertion-oracle/v1/skill.md** | 断言规则 |
| **Reporting Artifact** | **specs/org/testing/skills/reporting-artifact/v1/skill.md** | 报告生成 |
| **Env Provision** | **specs/org/testing/skills/env-provision/v1/skill.md** | 环境准备 |
| **Frontend Observability** | **specs/org/testing/skills/frontend-observability/v1/skill.md** | 前端可观测性 |

## 示例项目

跑步AI教练 UI 契约示例存放在 `specs/org/running-coach/ui/` 目录：

```
running-coach/ui/
├── ui.map.yaml              # UI 索引文件
├── pages/
│   ├── home.page.yaml       # 首页契约
│   └── run-session.page.yaml # 跑步页契约
├── components/
│   └── training-card.component.yaml # 训练卡片契约
└── tokens/
    └── tokens.json          # 设计 Token
```

## 同步规则

### 更新时机

当 `specs/common` 目录下的规范发生变更时，需要同步更新 `cli/claude` 目录：

1. **新增 Agent**: 在 `cli/claude/agents/` 创建对应的 MD 文件
2. **更新 Agent**: 确保 MD 文件内容与 YAML 规范一致
3. **新增 Skill**: 在 `cli/claude/skills/` 创建对应的 MD 文件
4. **更新契约**: 确保 Agent 引用的契约路径正确
5. **新增 Gate**: 在 `specs/common/gates/` 创建 YAML + MD 文件

### 格式转换规则

YAML → MD 转换时保留以下内容：

| YAML 字段 | MD 对应内容 |
|-----------|-------------|
| `id`, `name`, `description` | frontmatter 中的 name, description |
| `persona.role` | MD 正文中的角色描述 |
| `policy.quality_bar` | MD 正文中的质量标准 |
| `forbidden_behaviors` | MD 正文中的禁止行为表格 |
| `prompting.instructions` | MD 正文中的工作流程 |
| `responsibility.out_of_scope` | MD 正文中的"不应该做的" |
| `contracts` | MD 正文中的输入输出契约引用 |

### 权威来源

- **specs/common** 是所有规范的**权威来源 (Single Source of Truth)**
- **cli/claude** 是面向 Claude Code 的**派生版本**
- 发生冲突时，以 **specs/common** 为准

## 版本记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-16 | 3.14.0 | **新增 E2E Runner Skill + E2E Test Executor Agent**: 基于 Docker + Playwright 的 E2E UI 测试体系；新增 e2e-runner.md skill 和 e2e-test-executor.md agent；提供 Docker 镜像、示例测试、契约定义、知识库 (pitfalls/patterns) |
| 2026-01-14 | 3.13.0 | **新增 Test Env Admin Agent**: 测试环境管理员，负责测试环境搭建、部署和维护；新增 5 个 Skills (server-connect, docker-deploy, health-check, db-init, config-inject) |
| 2026-01-14 | 3.12.0 | **新增 testing-pipeline Skill**: 测试流水线执行技能，接收研发交付包执行完整测试流程；新增 /run-testing 命令入口；定义完整输入(release-manifest)和输出(test-report)契约 |
| 2026-01-13 | 3.11.0 | **新增 product-to-dev Skill**: 产品到研发全流程技能，从原始需求到研发冻结包，包含 3 阶段 14 步 6 个冻结点；新增 Product to Dev Pipeline Workflow |
| 2026-01-13 | 3.10.0 | **新增 dev-execute Skill**: 临时研发需求执行技能，按照标准 OpenSpec 13 步流程执行，使用 Orchestrator 管理流程 |
| 2026-01-10 | 3.9.0 | **强化整改循环 (Remediation Loop)**: workflow-guard v2.1 新增整改命令 (remediate/rollback/check-remediation); Workflow v1.4 详细配置 step_mapping; 验收失败自动整改 5 次后触发人类门禁 |
| 2026-01-10 | 3.8.0 | **条件门禁 (Agent 驱动)**: Code Review 门禁改为可选，由 Agent 判断是否需要人类介入; 更新 Enforcement Spec 和 Execution State Contract 支持 auto_approved_gates |
| 2026-01-10 | 3.7.0 | **新增 Workflow Enforcement 规范**: 通用工作流强制执行机制 (CLI 无关) + Execution State Contract + workflow-guard.py 工具 + CLI Adapters (Claude/Cursor/Codex) |
| 2026-01-09 | 3.6.0 | **新增 Phase Acceptance Gate Agent**: 验收 Phase 交付物和指标是否达标，支持整改循环和人类介入门禁 |
| 2026-01-09 | 3.5.0 | **新增 11 个 JSON Schema 契约**: ADR Output, Delivery Gate I/O, QA Input, Test Case Contract, Migration Contract, AI Engineering Output, Security Check I/O, UI Review I/O |
| 2026-01-09 | 3.4.0 | **重构专业角色 Agents**: 新增 Tech Lead (ADR机制) + Delivery Gate + SecOps + UI Reviewer; 升级 DB (Migration Contract) + AI (三类Contract); 重构 QA/SDET 硬边界; DevOps +测试环境 |
| 2026-01-09 | 3.3.0 | 新增 9 个专业角色 Agents: Frontend/Backend Architect, Go/UniApp Engineer, Database/AI/QA/Test Automation/DevOps Engineer |
| 2026-01-09 | 3.2.0 | **新增研发计划与调度 Agents**: Development Planner + Development Scheduler + Development Plan Contract |
| 2026-01-09 | 3.1.0 | **迁移 Development Pipeline 到 org/development**: Agents、Skills、Gates、Workflows、Contracts 迁移到部门专属目录 |
| 2026-01-08 | 3.0.0 | **新增 Development Pipeline**: 10 个 Agents + 4 个 Skills + 2 个 Workflows + 2 个 Gates + Phase Contract |
| 2026-01-08 | 2.7.0 | 新增 UI Design Executor Agent 和 6 个 Figma Skills |
| 2026-01-08 | 2.6.0 | 新增 UI 契约、Gates、UI Agents、UI Skills、UI Workflow |
| 2026-01-07 | 2.5.0 | 同步 specs 所有 agents 和 skills，新增 6 个 agents |
| 2026-01-04 | 2.4.0 | 初始版本 |

---

## Development Pipeline 架构概述

### 三层架构

```
L0: Project Flow (主流程)
    ├── 研发冻结包 + UI 原型
    │       ↓
    ├── [Development Planner] → Development Plan Contract
    │       ↓
    ├── [Development Scheduler] → Phase 调度执行
    │       ↓
    ├── Phase 并行执行 (L1) ← 调度器触发
    │       ↓
    ├── 集成 & E2E 测试
    │       ↓
    └── 验收 & 发布

L1: Phase OpenSpec Flow (OpenSpec 子流程)
    ├── Requirement Calibration
    ├── Test Contract Generation
    ├── OpenSpec Proposal
    ├── Implementation
    ├── Unit Test + Code Review
    ├── Retrospective + Knowledge Update
    └── OpenSpec Archive

L2: Agent / Contract / Skill (执行层)
```

### 核心 Agents

```
研发计划 Agent (Development Planner)
  输入: 研发冻结包 + UI 原型图
  输出: Development Plan Contract
  职责: Phase 划分、排期、Agent 编排、交付标准

研发调度 Agent (Development Scheduler)
  输入: Development Plan Contract
  输出: 执行状态、进度报告
  职责: 按计划推进、监控进度、处理阻塞、协调执行
```

### OpenSpec 定位

```
OpenSpec = Phase 级"临时但可追溯的工作空间"
         ≠ 项目级方法论
         ≠ 长期知识库

每个 Phase 独立实例化一个 OpenSpec 工作空间
通过 phase.yaml 定义输入边界
通过 handover.yaml 输出到主流程
```

### 详细文档

- **研发部门 README**: `specs/org/development/README.md`
- **Workflow 定义**: `specs/org/development/workflows/development-pipeline/v1/workflow.yaml`
- **OpenSpec 集成点**: `specs/org/development/workflows/development-pipeline/v1/openspec-integration.md`
- **Phase 子流程**: `specs/org/development/workflows/phase-openspec-flow/v1/workflow.yaml`
- **Development Plan Contract**: `specs/org/development/contracts/development-plan-contract/v1/schema.json`
- **Phase Contract Schema**: `specs/org/development/contracts/phase-contract/v1/schema.json`
