# LEE Framework Spec-Global 迁移完成报告

**迁移日期**: 2025-01-23
**状态**: ✅ 完成
**迁移文件数**: 134 个

---

## 迁移统计

### 总体统计
| 类型 | 原始数量 | 已迁移 |
|------|----------|--------|
| agents | 76 | 76 |
| skills | 18 | 18 |
| workflows | 11 | 11 |
| gates | 9 | 9 |
| contracts | 7 | 7 |
| protocols | 2 | 2 |
| 其他 (schema, template, integration等) | 11 | 11 |
| **总计** | **134** | **134** |

### 按目录统计
| 目录 | 文件数 |
|------|--------|
| core/ | 11 |
| cross/ | 8 |
| departments/dev/ | 37 |
| departments/prd/ | 8 |
| departments/qa/ | 35 |
| departments/ui/ | 24 |
| departments/stg/ | 7 |
| departments/office/ | 4 |

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
    ├── dev/                        # 开发部门 (37)
    │   ├── agents/                 # 26 个 agents
    │   │   ├── acceptance-reviewer/
    │   │   ├── ai-engineer/
    │   │   ├── backend-architect/
    │   │   ├── code-reviewer/
    │   │   ├── database-engineer/
    │   │   ├── frontend-architect/
    │   │   ├── go-backend-engineer/
    │   │   ├── plan-architect/
    │   │   ├── qa-engineer/
    │   │   ├── tech-architect/
    │   │   ├── uniapp-frontend-engineer/
    │   │   └── ... (更多)
    │   ├── contracts/              # 21 个 contracts
    │   │   ├── phase-directory-contract/
    │   │   ├── retest-manifest/
    │   │   └── ... (更多)
    │   ├── gates/                  # 3 个 gates
    │   │   ├── dev-gate/
    │   │   ├── phase-gate/
    │   │   └── release-gate/
    │   ├── skills/                 # 1 个 skill
    │   │   └── planning-methodology/
    │   └── workflows/              # 4 个 workflows
    │       ├── development-pipeline/
    │       ├── dev-retest/
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
