# Common Agents 迁移对照表

**原始目录**: `ai-spec/specs/common/agents/` (36 个)
**检查日期**: 2025-01-23

---

## ✅ 已迁移 (36/36)

### → core/agents (6 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `agent-spec-maintainer` | `core/agents/agent-spec-maintainer/v1/` | ✅ |
| `contracts-spec-maintainer` | `core/agents/contracts-spec-maintainer/v1/` | ✅ |
| `gates-spec-maintainer` | `core/agents/gates-spec-maintainer/v1/` | ✅ |
| `skills-spec-maintainer` | `core/agents/skills-spec-maintainer/v1/` | ✅ |
| `spec-review` | `core/agents/spec-review/v1/` | ✅ |
| `workflow-spec-maintainer` | `core/agents/workflow-spec-maintainer/v1/` | ✅ |

### → cross/agents (4 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `analysis-freezer` | `cross/agents/analysis-freezer/v1/` | ✅ |
| `dev-freeze-orchestrator` | `cross/agents/dev-freeze-orchestrator/v1/` | ✅ |
| `execution-observer` | `cross/agents/execution-observer/v1/` | ✅ |
| `fact-collector` | `cross/agents/fact-collector/v1/` | ✅ |

### → departments/stg/agents (7 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `business-opportunity-analyzer` | `departments/stg/agents/business-opportunity-analyzer/v1/` | ✅ |
| `business-opportunity-builder` | `departments/stg/agents/business-opportunity-builder/v1/` | ✅ |
| `google-keyword-searcher` | `departments/stg/agents/google-keyword-searcher/v1/` | ✅ |
| `google-trend-analyzer` | `departments/stg/agents/google-trend-analyzer/v1/` | ✅ |
| `industry-structure-analyzer` | `departments/stg/agents/industry-structure-analyzer/v1/` | ✅ |
| `supply-analyzer` | `departments/stg/agents/supply-analyzer/v1/` | ✅ |
| `user-signal-analyzer` | `departments/stg/agents/user-signal-analyzer/v1/` | ✅ |

### → departments/ui/agents (10 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `icon-generator` | `departments/ui/agents/icon-generator/v1/` | ✅ |
| `prototype-designer` | `departments/ui/agents/prototype-designer/v1/` | ✅ |
| `ui-contract-generator` | `departments/ui/agents/ui-contract-generator/v1/` | ✅ |
| `ui-contract-validator` | `departments/ui/agents/ui-contract-validator/v1/` | ✅ |
| `ui-design-executor` | `departments/ui/agents/ui-design-executor/v1/` | ✅ |
| `ui-designer` | `departments/ui/agents/ui-designer/v1/` | ✅ |
| `ui-gate-runner` | `departments/ui/gates/ui-gate-runner/v1/` | ✅ |
| `ui-test-generator` | `departments/ui/agents/ui-test-generator/v1/` | ✅ |
| `ux-review-agent` | `departments/ui/agents/ux-review-agent/v1/` | ✅ |

### → departments/dev/agents (2 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `plan-architect` | `departments/dev/agents/plan-architect/v1/` | ✅ |
| `tech-architect` | `departments/dev/agents/tech-architect/v1/` | ✅ |

### → departments/prd/agents (3 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `prd-writer` | `departments/prd/agents/prd-writer/v1/` | ✅ |
| `product-goal-analyzer` | `departments/prd/agents/product-goal-analyzer/v1/` | ✅ |
| `requirement-reviewer` | `departments/prd/agents/requirement-reviewer/v1/` | ✅ |

### → departments/qa/agents (2 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `e2e-test-executor` | `departments/qa/agents/e2e-test-executor/v1/` | ✅ |
| `test-case-creator` | `departments/qa/agents/test-case-creator/v1/` | ✅ |

### → departments/office/agents (1 个)

| 原始 Agent | 新位置 | 状态 |
|-----------|--------|------|
| `approval-reviewer` | `departments/office/agents/approval-reviewer/v1/` | ✅ |
| `phase-acceptance-gate` | `departments/office/gates/phase-acceptance/v1/` | ✅ |

---

## 📊 迁移统计

| 目标部门 | 迁移数量 | 状态 |
|---------|---------|------|
| **core/agents** | 6 | ✅ |
| **cross/agents** | 4 | ✅ |
| **departments/stg/agents** | 7 | ✅ |
| **departments/ui/agents** | 9 | ✅ |
| **departments/dev/agents** | 2 | ✅ |
| **departments/prd/agents** | 3 | ✅ |
| **departments/qa/agents** | 2 | ✅ |
| **departments/office/gates** | 1 | ✅ |
| **总计** | **36** | **✅ 100% 完成** |

---

## 📁 新目录结构对照

```
旧结构: ai-spec/specs/common/agents/ (36个)
                    ↓
新结构: spec-global/
├── core/agents/                    (6个)
├── cross/agents/                   (4个)
└── departments/
    ├── stg/agents/                (7个)
    ├── ui/agents/                 (9个)
    ├── dev/agents/                (2个)
    ├── prd/agents/                (3个)
    ├── qa/agents/                 (2个)
    └── office/agents/             (1个)
```

---

## ✅ 结论

**所有 36 个 common agents 都已成功迁移到新的 spec-global 目录！**

每个 agent 都保留了原有的 v1/agent.yaml 结构，可以正常使用。
