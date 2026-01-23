# AI-Spec Agent 评审报告

> **生成时间**: 2026-01-07T22:01:00+07:00
> **评审标准**: Spec Review Rules v1.0
> **评审范围**: ai-spec/specs/agents/ (共 15 个 Agent，不含 _template 和 spec-review)

---

## 评审总结

```
┌─────────────────────────────────────────────────────────┐
│  Blockers: 15   │  Majors: 45   │  Minors: 30   │  Nits: 15  │
└─────────────────────────────────────────────────────────┘
```

**所有现有 Agent 都需要迁移到 v1.0 格式。**

---

## 通用问题（影响所有 15 个 Agent）

### Blocker 级别

| 规则代码 | 问题 | 影响的 Agent |
|---------|------|-------------|
| `MISSING_KIND` | 缺少 `kind: agent` 字段 | 全部 15 个 |
| `AGENT_MISSING_CONTRACTS` | 使用旧格式 `inputs/outputs` 而非 `contracts` | 全部 15 个 |

### Major 级别

| 规则代码 | 问题 | 影响的 Agent |
|---------|------|-------------|
| `INVALID_ID_FORMAT` | `id` 格式不符合 `agent.{domain}.{name}` | 全部 15 个 |
| `MISSING_TESTS_SMOKE` | 缺少 `tests.smoke` 测试钩子 | 全部 15 个 |
| `AGENT_MISSING_SKILLS` | 缺少 `skills` 引用列表 | 全部 15 个 |

### Minor 级别

| 规则代码 | 问题 | 影响的 Agent |
|---------|------|-------------|
| `MISSING_OWNER` | 缺少 `owner` 字段 | 全部 15 个 |
| `AGENT_MISSING_QUALITY_BAR` | 缺少 `policy.quality_bar.must_have` | 全部 15 个 |

---

## 各 Agent 详细评审

### 1. google_keyword_searcher

**文件**: `specs/agents/google-keyword-searcher/v1/agent.yaml`

| 严重级别 | 代码 | 问题 | 修复建议 |
|---------|------|------|---------|
| blocker | MISSING_KIND | 缺少 `kind` 字段 | 添加 `kind: agent` |
| blocker | AGENT_MISSING_CONTRACTS | 使用旧格式 | 迁移到 `contracts.input_schema/output_schema` |
| major | INVALID_ID_FORMAT | id 为 `google_keyword_searcher` | 改为 `agent.research.google_keyword_searcher` |
| major | MISSING_TESTS_SMOKE | 无测试 | 添加 `tests.smoke` |
| major | AGENT_MISSING_SKILLS | 无 skills 引用 | 添加 `skills: [...]` |

---

### 2. fact_collector

**文件**: `specs/agents/fact-collector/v1/agent.yaml`

| 严重级别 | 代码 | 问题 | 修复建议 |
|---------|------|------|---------|
| blocker | MISSING_KIND | 缺少 `kind` 字段 | 添加 `kind: agent` |
| blocker | AGENT_MISSING_CONTRACTS | 使用旧格式 | 迁移到 `contracts` |
| major | INVALID_ID_FORMAT | id 为 `fact_collector` | 改为 `agent.research.fact_collector` |
| major | MISSING_TESTS_SMOKE | 无测试 | 添加 `tests.smoke` |
| nit | 良好实践 | 有详细的 `forbidden_behaviors` | ✅ 保留 |

---

### 3. business_opportunity_analyzer

**文件**: `specs/agents/business-opportunity-analyzer/v1/agent.yaml`

| 严重级别 | 代码 | 问题 | 修复建议 |
|---------|------|------|---------|
| blocker | MISSING_KIND | 缺少 `kind` 字段 | 添加 `kind: agent` |
| blocker | AGENT_MISSING_CONTRACTS | 使用旧格式 | 迁移到 `contracts` |
| major | INVALID_ID_FORMAT | id 为 `business_opportunity_analyzer` | 改为 `agent.analysis.business_opportunity` |
| major | MISSING_TESTS_SMOKE | 无测试 | 添加 `tests.smoke` |
| nit | 良好实践 | 有 `downstream` 定义 | ✅ 保留（可迁移到 workflow） |

---

### 4. plan_architect

**文件**: `specs/agents/plan-architect/v1/agent.yaml`

| 严重级别 | 代码 | 问题 | 修复建议 |
|---------|------|------|---------|
| blocker | MISSING_KIND | 缺少 `kind` 字段 | 添加 `kind: agent` |
| blocker | AGENT_MISSING_CONTRACTS | 使用旧格式 | 迁移到 `contracts` |
| major | INVALID_ID_FORMAT | id 为 `plan_architect` | 改为 `agent.planning.plan_architect` |
| major | MISSING_TESTS_SMOKE | 无测试 | 添加 `tests.smoke` |
| nit | 良好实践 | 有 `phases` 定义 | 可迁移 decision_rules 到 `policy` |

---

### 5. user_signal_analyzer

**文件**: `specs/agents/user-signal-analyzer/v1/agent.yaml`

| 严重级别 | 代码 | 问题 | 修复建议 |
|---------|------|------|---------|
| blocker | MISSING_KIND | 缺少 `kind` 字段 | 添加 `kind: agent` |
| blocker | AGENT_MISSING_CONTRACTS | 使用旧格式 | 迁移到 `contracts` |
| major | INVALID_ID_FORMAT | id 为 `user_signal_analyzer` | 改为 `agent.analysis.user_signal` |
| major | MISSING_TESTS_SMOKE | 无测试 | 添加 `tests.smoke` |
| nit | 良好实践 | 有详细 `analysis_framework` | 可迁移到 `prompting.instructions` |

---

### 6-15. 其他 Agent (简要)

以下 Agent 存在相同的通用问题：

| Agent | ID 建议修改 |
|-------|-----------|
| analysis-freezer | `agent.freeze.analysis_freezer` |
| approval-reviewer | `agent.review.approval_reviewer` |
| business-opportunity-builder | `agent.planning.opportunity_builder` |
| google-trend-analyzer | `agent.research.trend_analyzer` |
| industry-structure-analyzer | `agent.analysis.industry_structure` |
| product-goal-analyzer | `agent.analysis.product_goal` |
| prototype-designer | `agent.design.prototype` |
| requirement-reviewer | `agent.review.requirement_reviewer` |
| supply-analyzer | `agent.analysis.supply` |
| agent-spec-maintainer | `agent.governance.spec_maintainer` |

---

## 迁移优先级

### P0 - 必须立即修复 (Blockers)

1. 为所有 Agent 添加 `kind: agent`
2. 将 `inputs/outputs` 迁移到 `contracts`

### P1 - 尽快修复 (Majors)

3. 修正 `id` 格式为 `agent.{domain}.{name}`
4. 添加 `tests.smoke` 测试钩子
5. 添加 `skills` 引用列表
6. 添加 `persona` 定义

### P2 - 建议修复 (Minors)

7. 添加 `owner` 字段
8. 添加 `policy.quality_bar.must_have`
9. 添加 `observability` 配置

---

## 迁移示例

以 `google_keyword_searcher` 为例，从旧格式迁移到 v1.0：

```yaml
# ========== 旧格式 (当前) ==========
id: google_keyword_searcher
version: v1
type: llm_agent
inputs:
  schema_ref: null
outputs:
  schema_ref: contracts/google-keyword-contract/v1/schema.json

# ========== 新格式 (v1.0) ==========
kind: agent
version: 1.0
id: agent.research.google_keyword_searcher
name: Google Keyword Searcher
owner: product-ai

contracts:
  input_schema: contracts/keyword-input/v1/schema.json
  output_schema: contracts/google-keyword-contract/v1/schema.json

persona:
  role: "关键词研究专家"
  tone: professional

policy:
  quality_bar:
    must_have:
      - "至少发现 10 个核心关键词"
      - "每个关键词有 3-5 个长尾词"

skills:
  - ref: skill.search.web_search
  - ref: skill.nlp.keyword_extract

tests:
  smoke:
    - name: basic_search
      input: { seed: "跨境电商" }
      assert:
        - path: "$.keywords.length"
          op: ">="
          value: 5
```

---

*评审报告生成完成*
*下一步: 按照迁移优先级逐个更新 Agent 规范*
