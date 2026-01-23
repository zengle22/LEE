# Spec 迁移报告

**迁移日期**: 2025-01-23
**迁移范围**: `ai-spec/specs/` → `spec-global/`

## 迁移统计

- **原始文件数**: 134 个
- **已迁移**: 69 个项目
- **成功**: 69 个
- **跳过**: 12 个（目标已存在）
- **错误**: 0 个

## 目录结构对比

### 旧结构 (ai-spec/specs/)
```
specs/
├── org/
│   ├── development/    → departments/dev/
│   ├── product/        → departments/prd/
│   ├── testing/        → departments/qa/
│   ├── integration/    → departments/qa/integration/
│   └── bussness/       → departments/stg/ (已废弃)
└── common/
    ├── agents/         → 分散到各部门
    ├── contracts/      → 分散到各部门和 core/
    ├── gates/          → 分散到各部门
    ├── protocols/      → core/protocols/
    ├── skills/         → 分散到各部门
    └── workflows/      → 分散到各部门和 cross/
```

### 新结构 (spec-global/)
```
spec-global/
├── core/                    # 核心基础设施
│   ├── agents/             # Spec 维护 agents (6 个)
│   ├── contracts/          # 核心契约 (2 个)
│   ├── gates/              # 核心门控
│   ├── protocols/          # 核心协议 (2 个)
│   ├── skills/             # 核心技能 (1 个)
│   └── constitution.yaml   # 宪法文件（从 core.yaml 整合）
│
├── cross/                   # 跨部门协作
│   ├── agents/             # 跨部门 agents (4 个)
│   ├── interfaces/         # 跨部门接口
│   ├── skills/             # 跨部门技能 (3 个)
│   ├── teams/              # 跨部门团队
│   └── workflows/          # 跨部门工作流 (1 个)
│
└── departments/             # 各部门
    ├── dev/                # 开发部门
    │   ├── agents/         # 来自 org/development + common/开发相关
    │   ├── contracts/      # 来自 org/development
    │   ├── gates/          # 来自 org/development
    │   ├── skills/         # 来自 common/开发相关
    │   └── workflows/      # 来自 org/development
    │
    ├── prd/                # 产品部门
    │   ├── agents/         # 来自 org/product + common/产品相关
    │   ├── contracts/
    │   ├── gates/
    │   ├── skills/         # 来自 common/产品相关
    │   └── workflows/      # 来自 org/product
    │
    ├── qa/                 # 质量保证部门
    │   ├── agents/         # 来自 org/testing + common/测试相关
    │   ├── contracts/      # 来自 org/testing
    │   ├── gates/          # 来自 org/testing
    │   ├── skills/         # 来自 common/测试相关
    │   ├── workflows/      # 来自 org/testing
    │   └── integration/    # 来自 org/integration
    │
    ├── ui/                 # UI/UX 设计部门 (新增)
    │   ├── agents/         # 来自 common/UI 相关 (10 个)
    │   ├── contracts/      # 来自 common/UI 相关 (2 个)
    │   ├── gates/          # 来自 common/UI 相关 (2 个)
    │   ├── skills/         # 来自 common/UI 相关 (12 个)
    │   └── workflows/      # 来自 common/UI 相关 (1 个)
    │
    ├── stg/                # 策略部门 (新增)
    │   ├── agents/         # 来自 common/策略相关 (7 个)
    │   ├── contracts/
    │   ├── gates/
    │   ├── skills/         # 来自 common/策略相关 (2 个)
    │   └── workflows/
    │
    ├── office/             # 办公室 (新增)
    │   ├── agents/         # 来自 common/审批相关 (1 个)
    │   ├── contracts/
    │   ├── gates/          # 来自 common/审批相关 (1 个)
    │   ├── skills/         # 来自 common/审批相关 (2 个)
    │   └── workflows/
    │
    └── ops/                # 运营部门 (预留)
        ├── agents/
        ├── contracts/
        ├── gates/
        ├── skills/
        └── workflows/
```

## 详细迁移映射

### 1. 部门直接映射 (org → departments)

| 源路径 | 目标路径 | 数量 |
|--------|----------|------|
| `org/development/agents` | `departments/dev/agents` | 23 个 |
| `org/development/contracts` | `departments/dev/contracts` | 2 个 |
| `org/development/gates` | `departments/dev/gates` | 3 个 |
| `org/development/workflows` | `departments/dev/workflows` | 3 个 |
| `org/product/agents` | `departments/prd/agents` | 2 个 |
| `org/product/workflows` | `departments/prd/workflows` | 2 个 |
| `org/testing/agents` | `departments/qa/agents` | 12 个 |
| `org/testing/contracts` | `departments/qa/contracts` | 6 个 |
| `org/testing/gates` | `departments/qa/gates` | 5 个 |
| `org/testing/workflows` | `departments/qa/workflows` | 3 个 |
| `org/integration` | `departments/qa/integration` | 1 个 |

### 2. Common Agents 迁移

| Agent | 新位置 |
|-------|--------|
| `prd-writer` | `departments/prd/agents/prd-writer/` |
| `product-goal-analyzer` | `departments/prd/agents/product-goal-analyzer/` |
| `requirement-reviewer` | `departments/prd/agents/requirement-reviewer/` |
| `ui-designer` | `departments/ui/agents/ui-designer/` |
| `ui-contract-generator` | `departments/ui/agents/ui-contract-generator/` |
| `ui-contract-validator` | `departments/ui/agents/ui-contract-validator/` |
| `ui-design-executor` | `departments/ui/agents/ui-design-executor/` |
| `ui-gate-runner` | `departments/ui/gates/ui-gate-runner/` |
| `ui-test-generator` | `departments/ui/agents/ui-test-generator/` |
| `ux-review-agent` | `departments/ui/agents/ux-review-agent/` |
| `icon-generator` | `departments/ui/agents/icon-generator/` |
| `prototype-designer` | `departments/ui/agents/prototype-designer/` |
| `tech-architect` | `departments/dev/agents/tech-architect/` |
| `plan-architect` | `departments/dev/agents/plan-architect/` |
| `e2e-test-executor` | `departments/qa/agents/e2e-test-executor/` |
| `test-case-creator` | `departments/qa/agents/test-case-creator/` |
| `business-opportunity-analyzer` | `departments/stg/agents/business-opportunity-analyzer/` |
| `business-opportunity-builder` | `departments/stg/agents/business-opportunity-builder/` |
| `google-keyword-searcher` | `departments/stg/agents/google-keyword-searcher/` |
| `google-trend-analyzer` | `departments/stg/agents/google-trend-analyzer/` |
| `industry-structure-analyzer` | `departments/stg/agents/industry-structure-analyzer/` |
| `supply-analyzer` | `departments/stg/agents/supply-analyzer/` |
| `user-signal-analyzer` | `departments/stg/agents/user-signal-analyzer/` |
| `approval-reviewer` | `departments/office/agents/approval-reviewer/` |
| `phase-acceptance-gate` | `departments/office/gates/phase-acceptance/` |
| `agent-spec-maintainer` | `core/agents/agent-spec-maintainer/` |
| `contracts-spec-maintainer` | `core/agents/contracts-spec-maintainer/` |
| `gates-spec-maintainer` | `core/agents/gates-spec-maintainer/` |
| `skills-spec-maintainer` | `core/agents/skills-spec-maintainer/` |
| `workflow-spec-maintainer` | `core/agents/workflow-spec-maintainer/` |
| `spec-review` | `core/agents/spec-review/` |
| `execution-observer` | `cross/agents/execution-observer/` |
| `dev-freeze-orchestrator` | `cross/agents/dev-freeze-orchestrator/` |
| `analysis-freezer` | `cross/agents/analysis-freezer/` |
| `fact-collector` | `cross/agents/fact-collector/` |

### 3. Common Skills 迁移

| Skill | 新位置 |
|-------|--------|
| `figma-component-builder` | `departments/ui/skills/figma-component-builder/` |
| `figma-design-system` | `departments/ui/skills/figma-design-system/` |
| `figma-interaction-design` | `departments/ui/skills/figma-interaction-design/` |
| `figma-parser` | `departments/ui/skills/figma-parser/` |
| `figma-import-guide` | `departments/ui/skills/figma-import-guide/` |
| `design-token-generator` | `departments/ui/skills/design-token-generator/` |
| `auto-layout-master` | `departments/ui/skills/auto-layout-master/` |
| `variant-system` | `departments/ui/skills/variant-system/` |
| `web-prototype-renderer` | `departments/ui/skills/web-prototype-renderer/` |
| `ui-prompt-enhancer` | `departments/ui/skills/ui-prompt-enhancer/` |
| `ui-gate-check` | `departments/ui/skills/ui-gate-check/` |
| `icon-svg-generator` | `departments/ui/skills/icon-svg-generator/` |
| `ui-ux-pro-max-integration` | `departments/ui/skills/ui-ux-pro-max-integration/` |
| `e2e-runner` | `departments/qa/skills/e2e-runner/` |
| `product-goal-analysis` | `departments/stg/skills/product-goal-analysis/` |
| `value-analysis-guide` | `departments/stg/skills/value-analysis-guide/` |
| `requirement-discovery` | `departments/prd/skills/requirement-discovery/` |
| `dev-gate-check` | `departments/office/skills/dev-gate-check/` |
| `release-gate-check` | `departments/office/skills/release-gate-check/` |
| `state-validator` | `cross/skills/state-validator/` |
| `generate-execution-report` | `cross/skills/generate-execution-report/` |
| `contract-template` | `cross/skills/contract-template/` |
| `planning-methodology` | `departments/dev/skills/planning-methodology/` |
| `agent-spec-creator` | `core/skills/agent-spec-creator/` |

### 4. Common Contracts 迁移

| Contract | 新位置 |
|----------|--------|
| `icon-design-token` | `departments/ui/contracts/icon-design-token/` |
| `ux-review-contract` | `departments/ui/contracts/ux-review-contract/` |
| `plan-contract` | `core/contracts/plan-contract/` |
| `execution-trace` | `core/contracts/execution-trace/` |

### 5. Common Gates 迁移

| Gate | 新位置 |
|------|--------|
| `ui-gate` | `departments/ui/gates/ui-gate/` |

### 6. Common Protocols 迁移

| Protocol | 新位置 |
|----------|--------|
| `knowledge-access` | `core/protocols/knowledge-access/` |
| `tool-wrapper` | `core/protocols/tool-wrapper/` |

### 7. Common Workflows 迁移

| Workflow | 新位置 |
|----------|--------|
| `ui-design-pipeline` | `departments/ui/workflows/ui-design-pipeline/` |
| `product-pipeline` | `cross/workflows/product-pipeline/` |

## core.yaml 整合

原 `ai-spec/core.yaml` 的内容已整合进 `spec-global/core/constitution.yaml`，包括：
- 目标与非目标
- 核心原则
- 系统角色
- 工作流模板
- 质量标准
- 治理规则

并新增了：
- 部门组织结构
- 跨部门协作协议
- 版本控制规则

## 后续工作

1. **删除旧目录** (可选，建议先备份验证)
   ```bash
   # 备份
   mv ai-spec/specs ai-spec/specs.backup

   # 验证无误后删除
   # rm -rf ai-spec/specs.backup
   ```

2. **更新引用**
   - 更新代码中的路径引用
   - 更新文档中的路径说明
   - 更新 CI/CD 配置

3. **创建 README**
   - 为每个部门创建 README 说明
   - 为 core/ 和 cross/ 创建说明文档

4. **验证**
   - 检查所有 spec 文件是否正确迁移
   - 验证引用路径是否有效
   - 运行相关测试

## 迁移脚本

迁移脚本保存在: `scripts/migrate_specs.py`

如需重新迁移或调整，可以修改该脚本后重新运行。
