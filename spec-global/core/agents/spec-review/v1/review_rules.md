# Spec Review Rules v1.0

> 本文档定义 Spec Review Agent 的评审规则清单。
> 可作为 `policy_lint` skill 的规则来源。

---

## A. 通用规则（所有 kind）

### A.1 必填字段检查

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `MISSING_KIND` | `kind` 字段必须存在 | blocker |
| `MISSING_VERSION` | `version` 字段必须存在 | blocker |
| `MISSING_ID` | `id` 字段必须存在 | blocker |
| `MISSING_NAME` | `name` 字段必须存在 | major |
| `MISSING_DESCRIPTION` | `description` 字段必须存在 | minor |
| `MISSING_OWNER` | `owner` 字段必须存在 | minor |

### A.2 命名规范

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `INVALID_ID_FORMAT` | `id` 必须符合 `{kind}.{domain}.{name}` 格式 | major |
| `ID_KIND_MISMATCH` | `id` 前缀必须与 `kind` 一致 | blocker |

### A.3 测试要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `MISSING_TESTS_SMOKE` | `tests.smoke` 必须存在且至少有 1 条测试 | major |

### A.4 治理锚点要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `MISSING_TRUTH_SOURCE` | 实现导向 spec 必须有 formal SSOT truth source，或显式声明 temporary governance anchor | major |
| `MISSING_GOVERNANCE_REFS` | 实现/review/completion 导向 spec 在无 formal SSOT 时，必须引用 `.project/governance/` 规则 | major |
| `MISSING_COMPLETION_EVIDENCE_RULES` | completion 相关 spec 不得省略 evidence / tests / limitations / human gate 字段要求 | blocker |
| `WEAKENED_GATE_SEMANTICS` | 不得静默放宽 mandatory gate、approval、completion promotion 语义 | blocker |

---

## B. Skill 专属规则

### B.1 边界约束（防止 Skill 越界）

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `SKILL_HAS_PERSONA` | Skill 禁止包含 `persona` 字段 | blocker |
| `SKILL_HAS_PROMPTING` | Skill 禁止包含 `prompting` 字段 | blocker |
| `SKILL_HAS_POLICY_RULES` | Skill 禁止包含 `policy.decision_rules` | blocker |
| `SKILL_HAS_SKILLS_REF` | Skill 禁止引用其他 skills | major |

### B.2 必填字段

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `SKILL_MISSING_INTERFACE` | `interface` 字段必须存在 | blocker |
| `SKILL_MISSING_INPUTS` | `interface.inputs` 必须存在 | blocker |
| `SKILL_MISSING_OUTPUTS` | `interface.outputs` 必须存在 | blocker |
| `SKILL_MISSING_RUNTIME` | `runtime` 字段必须存在 | blocker |
| `SKILL_MISSING_CONSTRAINTS` | `constraints` 字段必须存在 | major |
| `SKILL_MISSING_SIDE_EFFECTS` | `constraints.side_effects` 必须声明 | major |

### B.3 输出格式要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `SKILL_UNSTRUCTURED_OUTPUT` | 输出必须是结构化类型（object/array），不能是纯 string blob | major |

---

## C. Agent 专属规则

### C.1 契约要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `AGENT_MISSING_CONTRACTS` | `contracts` 字段必须存在 | blocker |
| `AGENT_MISSING_INPUT_SCHEMA` | `contracts.input_schema` 必须存在 | blocker |
| `AGENT_MISSING_OUTPUT_SCHEMA` | `contracts.output_schema` 必须存在 | blocker |
| `AGENT_INVALID_SCHEMA_REF` | schema 引用路径必须是有效文件 | major |

### C.2 技能引用

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `AGENT_MISSING_SKILLS` | `skills` 列表必须存在（空想型 Agent 无法执行） | major |
| `AGENT_INVALID_SKILL_REF` | 引用的 skill 必须存在 | major |

### C.3 质量保障

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `AGENT_MISSING_QUALITY_BAR` | `policy.quality_bar.must_have` 必须存在 | major |
| `AGENT_INSUFFICIENT_QUALITY_BAR` | `must_have` 至少需要 3 条规则 | minor |

### C.4 引用要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `AGENT_MISSING_GROUNDING` | 若输出需要引用资料，必须设置 `grounding.citations_required: true` | minor |

---

## D. Workflow 专属规则

### D.1 人类介入点

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `WORKFLOW_NO_HUMAN_GATE` | `human_in_the_loop` 必须存在或显式声明 `none` 的理由 | major |
| `WORKFLOW_HUMAN_GATE_NO_PURPOSE` | 每个人类介入点必须有 `purpose` 说明 | minor |

### D.2 错误处理

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `WORKFLOW_MISSING_ERROR_HANDLING` | `error_handling` 字段必须存在 | major |
| `WORKFLOW_STEP_NO_ON_FAILURE` | 每个 step 必须声明 `on_failure` 去向 | major |

### D.3 契约要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `WORKFLOW_MISSING_OUTPUTS_CONTRACT` | `outputs_contract` 必须存在 | major |
| `WORKFLOW_MISSING_INPUTS_CONTRACT` | `inputs_contract` 必须存在 | major |

### D.4 边界约束（防止 Workflow 越界）

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `WORKFLOW_HAS_PROMPTING` | Workflow 禁止包含 `prompting` 字段 | blocker |
| `WORKFLOW_HAS_PERSONA` | Workflow 禁止包含 `persona` 字段 | blocker |
| `WORKFLOW_STEP_HAS_LOGIC` | step 禁止包含业务分析逻辑（应在 Agent 中） | major |

### D.5 测试要求

| 规则代码 | 检查项 | 严重级别 |
|---------|--------|---------|
| `WORKFLOW_MISSING_REPLAY` | `tests.replay` 必须存在（回放测试数据） | minor |

---

## E. 严重级别定义

| 级别 | 含义 | CI 行为 |
|------|------|---------|
| `blocker` | 阻塞级: 必须修复，否则无法合并 | PR 被阻止 |
| `major` | 重要级: 强烈建议修复，影响可维护性/可测试性 | PR 警告 |
| `minor` | 次要级: 建议修复，改善代码质量 | PR 提示 |
| `nit` | 建议级: 可选优化，风格/命名建议 | 仅记录 |

---

## F. CI 集成建议

```yaml
# .github/workflows/spec-review.yml
name: Spec Review
on:
  pull_request:
    paths:
      - 'specs/**/*.yaml'
      - 'specs/**/*.json'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Spec Review
        run: |
          # 调用 Spec Review Agent
          # 输出 blockers=0 才允许合并
          
      - name: Check Blockers
        run: |
          if [ "$BLOCKERS" -gt 0 ]; then
            echo "❌ Found $BLOCKERS blocker(s). PR blocked."
            exit 1
          fi
```

---

*Spec Review Rules v1.0*
*制定日期: 2026-01-07*
