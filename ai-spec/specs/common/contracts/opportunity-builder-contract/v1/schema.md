# 商业机会构建输出契约 (Output Contract)

> **契约版本**: 2.0.0
> **上游Agent**: 各类契约生成Agent（requirement-alignment, trend-researcher, business-opportunity-analyzer等）
> **本Agent**: business-opportunity-builder (商业机会构建Agent)
> **下游使用者**: 产品团队（人工验证）
> **唯一目标**: 构建一个可交给产品部门验证的机会假设

---

## 契约说明

本契约定义了商业机会构建的输出格式。本Agent的唯一目标是：**构建一个可交给产品部门验证的机会假设**。

不是做决策，不是给评分，而是构建一个清晰的假设，让产品团队可以去验证。

**职责边界**:
- **上游Agent职责**: 生成各类契约文档（需求契约、调研契约、分析契约等）
- **本Agent职责**: 读取冻结契约，构建机会假设，准备产品交付文档
- **下游使用者职责**: 产品团队基于假设设计并执行验证实验

**输出包含两部分**:
1. **Business Opportunity** - 机会假设定义
2. **Opportunity Handoff** - 产品团队交付文档

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: opportunity-builder-output
contract_version: "2.0.0"
metadata:
  report_id: string              # 报告ID，格式：OB-YYYYMMDD-XXX
  source_contract: string        # 输入契约文件路径
  generated_at: datetime         # 生成时间 ISO 8601
  keyword: string                # 核心关键词/领域

business_opportunity:            # Part 1: 机会假设定义
  one_liner: string
  target_user_scenario: TargetUserScenario
  why_now: WhyNow[]
  differentiation_hypothesis: DifferentiationHypothesis
  reasons_not_to_do: ReasonsNotToDo
  product_validation_suggestion: ValidationSuggestion

opportunity_handoff:             # Part 2: 产品交付文档
  what_we_believe: Belief[]
  what_we_dont_know: Unknown[]
  what_not_to_build_yet: NotToBuild
  suggested_experiments: Experiment[]
```

### TargetUserScenario 对象

```yaml
TargetUserScenario:
  user: string                   # 用户画像（1-2句话）
  scenario:
    trigger_moment: string       # 触发时刻
    current_action: string       # 正在做什么
    problem_faced: string        # 遇到什么问题
```

### WhyNow 对象

```yaml
WhyNow:
  argument: string               # 时机论据
  evidence: string               # 具体证据
  category: WhyNowCategory       # 论据类型
```

### DifferentiationHypothesis 对象

```yaml
DifferentiationHypothesis:
  hypothesis: string             # 假设陈述："如果我们...，用户会..."
  verification_method: string    # 验证方式
  falsification_signal: string   # 证伪信号
```

### ReasonsNotToDo 对象

```yaml
ReasonsNotToDo:
  risks:                         # 风险
    - name: string
      description: string
      probability: Level
      impact: Level
  uncertainties:                 # 不确定性
    - question: string           # 我们不知道...
  alternative_paths:             # 替代路径
    - option: string
      description: string
```

### ValidationSuggestion 对象

```yaml
ValidationSuggestion:
  target: string                 # 验证目标（一句话）
  method: string                 # 建议方法
  success_signal: string         # 成功信号
  failure_signal: string         # 失败信号
  time_cost: string              # 时间成本
  resource_cost: string          # 资源成本
```

### Belief 对象

```yaml
Belief:
  conclusion: string             # 冻结结论
  source: string                 # 依据来源
```

### Unknown 对象

```yaml
Unknown:
  question: string               # 未知问题
  priority: Priority             # 优先级
  impact: string                 # 影响描述
  suggested_verification: string # 建议验证方式
```

### NotToBuild 对象

```yaml
NotToBuild:
  do_not_build:                  # 不要做
    - item: string
      reason: string
  defer:                         # 暂缓
    - item: string
      condition: string          # 等什么条件满足后再考虑
```

### Experiment 对象

```yaml
Experiment:
  name: string                   # 实验名称
  type: ExperimentType           # 实验类型
  purpose: string                # 验证什么假设
  method: string                 # 具体做法
  success_criteria: string       # 成功标准（量化）
  time_cost: string              # 时间成本
  resource_cost: string          # 资源成本
```

### 枚举定义

```yaml
WhyNowCategory:
  - tech_maturity      # 技术成熟度变化
  - market_window      # 市场窗口打开
  - user_behavior      # 用户行为变化
  - cost_structure     # 成本结构变化

Level:
  - high
  - medium
  - low

Priority:
  - P0                 # 决定是否继续
  - P1                 # 影响方案设计
  - P2                 # 影响实现细节

ExperimentType:
  - landing_page       # 落地页测试
  - user_interview     # 用户访谈
  - fake_door          # 假门测试
  - prototype_test     # 原型测试
  - competitor_analysis # 竞品分析
  - survey             # 问卷调查
```

---

## Markdown 输出格式

```markdown
# Business Opportunity: {keyword}

> **构建时间**: YYYY-MM-DD
> **输入契约**: {contract_file}
> **唯一目标**: 构建可交给产品部门验证的机会假设

---

## One-liner

{一句话机会定义，不超过30字}

---

## Target User & Scenario

**用户**: {用户画像，1-2句话}

**情境**:
- 触发时刻: {什么时候}
- 正在做: {做什么}
- 遇到问题: {什么问题}

---

## Why Now

为什么此刻值得做（而不是一年前或一年后）：

1. **{论据1类型}**: {论据描述}
   - 证据: {具体证据}

2. **{论据2类型}**: {论据描述}
   - 证据: {具体证据}

---

## Differentiation Hypothesis

**假设**: 如果我们 {做什么不同的事}，{目标用户} 会 {产生什么行为/获得什么价值}

**验证方式**: {如何知道这个假设是对的}

**证伪信号**: {什么情况说明假设错了}

---

## Reasons NOT to Do

### 风险
| 风险 | 描述 | 概率 | 影响 |
|------|------|------|------|
| {风险1} | {描述} | 高/中/低 | 高/中/低 |
| {风险2} | {描述} | 高/中/低 | 高/中/低 |

### 不确定性
- 我们不知道: {问题1}
- 我们不知道: {问题2}

### 替代路径
- **{选项1}**: {描述}
- **{选项2}**: {描述}

---

## Product Validation Suggestion

**验证目标**: {一句话说明要验证什么}

**建议方法**: {具体的验证方式}

**成功信号**: {什么情况说明值得继续}

**失败信号**: {什么情况说明应该放弃}

**预计成本**: {时间} + {资源}

---

# Opportunity Handoff

---

## What we believe

> 以下是冻结结论，不需要再讨论，产品团队可以直接基于这些结论行动。

- ✅ {结论1}: 依据 {来源}
- ✅ {结论2}: 依据 {来源}
- ✅ {结论3}: 依据 {来源}

---

## What we don't know

> 以下是关键未知项，需要产品团队去验证。

| 未知项 | 优先级 | 影响 | 建议验证方式 |
|--------|--------|------|--------------|
| {问题1} | P0 | {影响} | {方法} |
| {问题2} | P1 | {影响} | {方法} |

---

## What NOT to build yet

> 防止产品团队在验证假设前就开始构建。

🚫 **不要做**:
- {事项1}: 因为 {原因}
- {事项2}: 因为 {原因}

⏸️ **暂缓**:
- {事项1}: 等 {条件} 满足后再考虑
- {事项2}: 等 {条件} 满足后再考虑

---

## Suggested Experiments

### 实验1: {名称}
- **类型**: {Landing Page / User Interview / Fake Door / ...}
- **目的**: 验证 {什么假设}
- **做法**: {具体步骤}
- **成功标准**: {量化指标}
- **预计成本**: {时间} + {资源}

### 实验2: {名称}
- **类型**: {类型}
- **目的**: 验证 {什么假设}
- **做法**: {具体步骤}
- **成功标准**: {量化指标}
- **预计成本**: {时间} + {资源}

### 实验3: {名称}
- **类型**: {类型}
- **目的**: 验证 {什么假设}
- **做法**: {具体步骤}
- **成功标准**: {量化指标}
- **预计成本**: {时间} + {资源}

---

*本文档由商业机会构建 Agent 生成*
*生成时间: {timestamp}*
*输入契约: {source_contract}*
*契约版本: 2.0.0*

**说明**: 本文档的目标是构建可验证的机会假设，而非给出最终决策。产品团队应基于 Suggested Experiments 执行验证，然后决定是否继续。
```

---

## 验证规则

1. **必填字段**: `report_id`, `source_contract`, `one_liner`, `target_user_scenario`
2. **假设格式**: `differentiation_hypothesis` 必须包含假设陈述、验证方式、证伪信号
3. **Why Now**: 必须至少有1个时机论据，每个论据必须有证据支撑
4. **风险完整**: `reasons_not_to_do` 必须包含风险、不确定性、替代路径三部分
5. **Handoff完整**: 四个部分都必须填写（what we believe, what we don't know, what NOT to build yet, suggested experiments）
6. **实验可执行**: 每个实验必须有量化的成功标准

---

## 设计原则

| 原则 | 说明 |
|------|------|
| 假设优于结论 | 我们的工作是构建假设，不是下结论 |
| 边界清晰 | 明确区分"已知"和"未知" |
| 防止过早实现 | 在验证前不要让产品团队开始构建 |
| 实验导向 | 每个输出都应该指向一个可执行的验证实验 |
| 约束驱动 | 所有分析必须基于契约中的实际约束 |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-04 | 初始版本（6问结构） |
| 2.0.0 | 2026-01-04 | 重构为 Business Opportunity + Opportunity Handoff 双部分结构 |
