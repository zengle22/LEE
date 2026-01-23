# 商业机会分析输出契约 (Output Contract)

> **契约版本**: 1.0.0
> **上游Agent**: google-trend-researcher
> **本Agent**: business-opportunity-analyzer (商业机会分析Agent)
> **下游Agent**: prd-designer (产品设计Agent)
> **用途**: 定义商业机会分析结果的标准格式，供下游产品经理做产品设计和原型图使用

---

## 契约说明

本契约定义了商业机会分析的输出格式。本Agent负责基于热词调研数据，从小团队（1-10人）视角评估市场切入机会，并给出具体的切入策略建议，供下游产品设计Agent进行产品规划。

**职责边界**:
- **上游Agent职责**: 收集原始背景信息、市场数据、竞品信息（不做分析）
- **本Agent职责**: 分析商业机会、评估切入可行性、提出差异化策略
- **下游Agent职责**: 基于机会分析进行产品目标定义、用户画像、功能设计

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: business-opportunity-output
contract_version: "1.0.0"
metadata:
  analysis_id: string           # 分析ID，格式：BO-YYYYMMDD-XXX
  source_contract: string       # 输入契约ID (来自trend-research-contract)
  generated_at: datetime        # 生成时间 ISO 8601
  keyword: string               # 分析的核心热词/领域
  analyst: string               # 分析者标识

opportunity_assessment: OpportunityAssessment    # 机会评估
market_analysis: MarketAnalysis                  # 市场分析
competitive_landscape: CompetitiveLandscape      # 竞争格局
entry_strategy: EntryStrategy                    # 切入策略
risk_analysis: RiskAnalysis                      # 风险分析
pending_confirmation: PendingConfirmation[]      # 待确认事项
downstream_handoff: DownstreamHandoff            # 下游交接信息
```

### OpportunityAssessment 对象

```yaml
OpportunityAssessment:
  overall_rating: Rating                # 综合评级 A/B/C/D
  rating_reasoning: string              # 评级理由
  one_line_conclusion: string           # 一句话结论

  scores:
    market_gap: Score                   # 市场空白度
    entry_barrier: Score                # 进入门槛（分数越高门槛越低）
    differentiation_potential: Score    # 差异化潜力
    small_team_fit: Score               # 小团队适配度

  recommendation: Recommendation        # 推荐建议
```

### Score 对象

```yaml
Score:
  value: number                         # 0-100分
  level: ScoreLevel                     # 等级
  summary: string                       # 简要说明
  details: string[]                     # 详细依据
```

### MarketAnalysis 对象

```yaml
MarketAnalysis:
  market_size:
    global: string                      # 全球市场规模
    china: string                       # 中国市场规模
    cagr: string                        # 年增长率
    data_source: string                 # 数据来源

  market_stage: MarketStage             # 市场阶段
  stage_reasoning: string               # 阶段判断依据

  target_segments:                      # 可切入的细分市场
    - segment_name: string
      segment_size: string
      competition_level: string
      opportunity_reasoning: string
```

### CompetitiveLandscape 对象

```yaml
CompetitiveLandscape:
  concentration: ConcentrationLevel     # 市场集中度

  head_players:                         # 头部玩家分析
    - name: string
      market_share: string
      strengths: string[]
      weaknesses: string[]              # 小团队可利用的弱点

  mid_tier_summary:
    count: number
    funding_activity: string
    common_characteristics: string[]

  open_source_alternatives:
    - name: string
      coverage: string                  # 功能覆盖度
      adoption: string                  # 采用情况

  white_space_analysis: string[]        # 市场空白点
```

### EntryStrategy 对象

```yaml
EntryStrategy:
  recommended_positioning: string       # 推荐定位

  target_user:
    primary_persona: string             # 主要用户画像
    user_pain_points: string[]          # 核心痛点
    underserved_needs: string[]         # 未被满足的需求

  differentiation:
    primary_direction: string           # 主要差异化方向
    specific_opportunities: string[]    # 具体机会点

  mvp_suggestion:
    core_features: string[]             # MVP核心功能
    out_of_scope: string[]              # MVP不包含的功能
    estimated_dev_cost: string          # 开发成本估算
    estimated_timeline: string          # 时间周期估算

  pricing_strategy:
    model: string                       # 定价模式建议
    reasoning: string                   # 定价理由

  go_to_market:
    initial_channels: string[]          # 初期获客渠道
    growth_strategy: string             # 增长策略
```

### RiskAnalysis 对象

```yaml
RiskAnalysis:
  risks:
    - type: RiskType
      level: RiskLevel
      description: string
      mitigation: string

  biggest_risk:
    title: string
    detail: string
    recommendation: string

  success_factors: string[]             # 关键成功因素
```

### PendingConfirmation 对象

```yaml
PendingConfirmation:
  id: string                            # 待确认项ID，格式：PC-001
  category: ConfirmationCategory        # 分类
  question: string                      # 问题描述
  context: string                       # 背景说明
  options: string[]                     # 可选方案（如适用）
  impact: string                        # 对分析结论的影响
  priority: Priority                    # 优先级
```

### DownstreamHandoff 对象

```yaml
DownstreamHandoff:
  for_prd_designer:
    product_goal_suggestions: string[]      # 产品目标建议
    user_persona_inputs: string[]           # 用户画像输入
    value_proposition_hints: string[]       # 价值主张提示
    differentiation_features: string[]      # 差异化功能建议
    competitive_advantages: string[]        # 核心竞争力建议

  key_constraints:
    - constraint: string
      reason: string

  recommended_next_steps: string[]
```

### 枚举定义

```yaml
Rating:
  - A     # 强烈推荐：机会明确，门槛适中，小团队可切入
  - B     # 值得尝试：有一定机会，需要找准差异化定位
  - C     # 谨慎考虑：挑战较大，需要特定优势才能入场
  - D     # 不建议：风险过高或不适合小团队

ScoreLevel:
  - excellent    # 90-100: 极好
  - good         # 70-89: 良好
  - moderate     # 50-69: 中等
  - poor         # 30-49: 较差
  - very_poor    # 0-29: 很差

MarketStage:
  - emerging     # 萌芽期
  - growth       # 成长期
  - mature       # 成熟期
  - declining    # 衰退期

ConcentrationLevel:
  - monopoly          # 垄断（CR3 > 70%）
  - oligopoly         # 寡头（CR3 50-70%）
  - competitive       # 竞争（CR3 30-50%）
  - fragmented        # 分散（CR3 < 30%）

RiskType:
  - giant_entry       # 巨头入场
  - tech_disruption   # 技术颠覆
  - policy_change     # 政策变化
  - economic_cycle    # 经济周期
  - funding_pressure  # 资金压力
  - talent_shortage   # 人才短缺

RiskLevel:
  - high              # 高风险
  - medium            # 中风险
  - low               # 低风险

ConfirmationCategory:
  - market_data       # 市场数据待验证
  - user_assumption   # 用户假设待验证
  - tech_feasibility  # 技术可行性待确认
  - strategy_choice   # 策略选择待决策
  - resource_estimate # 资源估算待确认

Priority:
  - critical          # 关键：影响核心结论
  - important         # 重要：影响部分建议
  - nice_to_have      # 补充：完善分析
```

---

## Markdown 输出格式

```markdown
# 商业机会分析报告

---

## 📋 分析概要

| 项目 | 内容 |
|------|------|
| **分析ID** | BO-20250102-001 |
| **输入契约** | TR-20250102-001 |
| **分析领域** | {keyword} |
| **分析时间** | 2025-01-02 16:00:00 |
| **综合评级** | {rating} |

**一句话结论**: {one_line_conclusion}

---

## 🎯 机会评估总览

| 评估维度 | 得分 | 等级 | 说明 |
|----------|------|------|------|
| 市场空白度 | {score}/100 | {level} | {summary} |
| 进入门槛 | {score}/100 | {level} | {summary} |
| 差异化潜力 | {score}/100 | {level} | {summary} |
| 小团队适配度 | {score}/100 | {level} | {summary} |

### 综合评级: {rating}

**评级说明**:
- **A（强烈推荐）**: 机会明确，门槛适中，小团队可切入
- **B（值得尝试）**: 有一定机会，需要找准差异化定位
- **C（谨慎考虑）**: 挑战较大，需要特定优势才能入场
- **D（不建议）**: 风险过高或不适合小团队

**本领域评级理由**:
{rating_reasoning}

---

## 📊 市场分析

### 市场规模

| 指标 | 数值 | 来源 |
|------|------|------|
| 全球市场规模 | {global_size} | {source} |
| 中国市场规模 | {china_size} | {source} |
| 年增长率(CAGR) | {cagr} | {source} |

### 市场阶段判断

**当前阶段**: {market_stage}

**判断依据**:
{stage_reasoning}

### 可切入的细分市场

| 细分市场 | 市场规模 | 竞争程度 | 机会说明 |
|----------|----------|----------|----------|
| {segment_1} | {size} | {competition} | {reasoning} |
| {segment_2} | {size} | {competition} | {reasoning} |

---

## 🏆 竞争格局

### 市场集中度: {concentration_level}

### 头部玩家分析

| 玩家 | 市占率 | 核心优势 | 可利用弱点 |
|------|--------|----------|------------|
| {player_1} | {share} | {strengths} | {weaknesses} |
| {player_2} | {share} | {strengths} | {weaknesses} |

### 中腰部玩家概况

- **玩家数量**: {count} 家
- **融资活跃度**: {funding_activity}
- **共同特征**: {characteristics}

### 开源/免费替代方案

| 方案 | 功能覆盖 | 采用情况 |
|------|----------|----------|
| {name} | {coverage} | {adoption} |

### 市场空白点

1. {white_space_1}
2. {white_space_2}
3. {white_space_3}

---

## 🚀 切入策略建议

### 推荐定位

{recommended_positioning}

### 目标用户

**主要用户画像**: {primary_persona}

**核心痛点**:
- {pain_point_1}
- {pain_point_2}

**未被满足的需求**:
- {need_1}
- {need_2}

### 差异化方向

**主要差异化方向**: {primary_direction}

**具体机会点**:
- {opportunity_1}
- {opportunity_2}

### MVP 建议

**核心功能（必须有）**:
- {feature_1}
- {feature_2}
- {feature_3}

**暂不包含（后续迭代）**:
- {out_of_scope_1}
- {out_of_scope_2}

**资源估算**:
| 项目 | 估算 |
|------|------|
| 开发成本 | {cost} |
| 开发周期 | {timeline} |

### 定价策略

**推荐模式**: {pricing_model}

**理由**: {pricing_reasoning}

### 初期获客

**推荐渠道**:
- {channel_1}
- {channel_2}

**增长策略**: {growth_strategy}

---

## ⚠️ 风险分析

### 风险清单

| 风险类型 | 风险等级 | 描述 | 缓解措施 |
|----------|----------|------|----------|
| {type_1} | {level} | {desc} | {mitigation} |
| {type_2} | {level} | {desc} | {mitigation} |

### 最大风险警示

🚨 **{biggest_risk_title}**

{biggest_risk_detail}

**应对建议**: {recommendation}

### 关键成功因素

小团队切入该领域需要具备:

1. {factor_1}
2. {factor_2}
3. {factor_3}

---

## ❓ 待确认事项

> 以下事项需要人工确认后，分析结论将更加准确

| ID | 分类 | 问题 | 优先级 | 影响 |
|----|------|------|--------|------|
| PC-001 | {category} | {question} | {priority} | {impact} |
| PC-002 | {category} | {question} | {priority} | {impact} |

### PC-001: {question}

**背景**: {context}

**可选方案**:
- 方案A: {option_a}
- 方案B: {option_b}

**对结论的影响**: {impact}

---

## 📤 下游交接信息

> 以下信息供 prd-designer Agent 使用

### 产品设计输入

#### 产品目标建议
- {goal_1}
- {goal_2}

#### 用户画像输入
- {persona_1}
- {persona_2}

#### 价值主张提示
- {value_1}
- {value_2}

#### 差异化功能建议
- {feature_1}
- {feature_2}

#### 核心竞争力建议
- {advantage_1}
- {advantage_2}

### 关键约束

| 约束 | 原因 |
|------|------|
| {constraint_1} | {reason_1} |
| {constraint_2} | {reason_2} |

### 建议下一步

1. {next_step_1}
2. {next_step_2}
3. {next_step_3}

---

## 📚 数据来源

{data_sources}

---

*本报告由商业机会分析 Agent 生成*
*分析时间: {timestamp}*
*契约版本: 1.0.0*
*输入契约: {source_contract}*

**免责声明**: 本报告基于公开信息分析，仅供参考，不构成投资建议。
```

---

## 分析指南

### 本Agent应做的分析

| 类别 | 分析内容 | 输出形式 |
|------|----------|----------|
| 机会评估 | 多维度打分评级 | 0-100分 + A/B/C/D评级 |
| 市场分析 | 细分市场识别、阶段判断 | 结构化表格 |
| 竞争分析 | 格局分析、空白点识别 | 列表 + 分析 |
| 策略建议 | 定位、MVP、定价、获客 | 具体建议 |
| 风险分析 | 识别风险、提供缓解 | 风险矩阵 |

### 不确定时的处理

1. **数据不足**: 在"待确认事项"中列出，标注影响
2. **多种可能**: 列出选项，说明各自影响，请求人工决策
3. **假设依赖**: 明确标注假设前提

### 小团队视角原则

1. **资源约束**: 假设团队1-10人，资金有限
2. **速度优先**: MVP要小而快
3. **差异化优先**: 不正面竞争，找蓝海
4. **可执行性**: 建议要具体可操作

---

## 验证规则

1. **必填字段**: `analysis_id`, `keyword`, `overall_rating`, `one_line_conclusion`
2. **评分字段**: 所有Score必须有value(0-100)和summary
3. **待确认事项**: 如有不确定项，必须填写pending_confirmation
4. **下游交接**: downstream_handoff必须包含至少3条产品目标建议

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-02 | 初始版本 |
