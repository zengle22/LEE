# 冻结分析输出契约 (Frozen Analysis Output Contract)

> **契约版本**: 1.0.0
> **上游Agent**: google-trend-analyzer, business-opportunity-analyzer
> **本Agent**: analysis-freezer (分析冻结Agent)
> **下游Agent**: prd-designer, plan-architect (及所有后续Agent)
> **用途**: 定义最终冻结分析的标准格式，作为后续所有Agent的权威事实基础

---

## 契约说明

本契约定义了分析冻结的输出格式。本Agent负责：
1. **质量评审** - 评审三维分析（竞品供给、行业结构、用户信号）的输出质量
2. **返工管理** - 不合格的分析要求返工，直到达到质量标准
3. **事实整合** - 将三份分析整合为统一的事实基础
4. **冻结锁定** - 输出的分析为最终版本，禁止后续Agent重新解释事实

**🔒 冻结原则**:
- 本契约输出的所有"事实"字段一旦冻结，后续Agent**禁止修改或重新解释**
- 后续Agent只能基于冻结事实进行"决策"和"建议"，不能质疑或修改事实
- 如需修改事实，必须重新触发分析冻结流程

**职责边界**:
- **上游Agent职责**: 收集和分析原始数据，输出各维度分析报告
- **本Agent职责**: 评审质量、要求返工、整合分析、冻结事实
- **下游Agent职责**: 基于冻结事实进行产品设计、规划等决策（不可修改事实）

---

## 🔗 追踪机制

通过 **Contract ID 关联** 实现输入输出报告的追踪：

```
热词调研报告: TR-YYYYMMDD-XXX
    ↓
商业机会报告: BO-YYYYMMDD-XXX
    ↓ 质量评审 + 整合
冻结分析报告: FA-YYYYMMDD-XXX (source_contracts: [TR-xxx, BO-xxx])
```

### 追踪字段说明

| 字段 | 位置 | 格式 | 用途 |
|------|------|------|------|
| `分析ID` | 冻结报告 | `FA-YYYYMMDD-XXX` | 唯一标识冻结分析报告 |
| `来源契约` | 冻结报告 | `[TR-xxx, BO-xxx]` | **关键**：关联到源分析报告 |
| `冻结时间` | 冻结报告 | ISO 8601 | 事实冻结的时间戳 |
| `冻结版本` | 冻结报告 | `v1.0` | 冻结版本号（不可变） |

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: frozen-analysis-output
contract_version: "1.1.0"
metadata:
  analysis_id: string           # 分析ID，格式：FA-YYYYMMDD-XXX
  source_contracts: string[]    # 来源契约ID列表
  frozen_at: datetime           # 冻结时间 ISO 8601
  frozen_version: string        # 冻结版本，格式：v1.0
  keyword: string               # 分析的核心热词/领域
  quality_status: QualityStatus # 质量状态
  review_rounds: number         # 评审轮次（返工次数+1）
  is_frozen: boolean            # 是否已冻结（true表示不可修改）

# 🔑 市场信号冻结元数据 - 关键词集合与假设管理
market_signal_freeze: MarketSignalFreeze

# 质量评审区
quality_review: QualityReview

# 🔒 冻结事实区 - 一旦冻结，后续Agent禁止修改
frozen_facts:
  competitor_supply: CompetitorSupplyFacts    # 竞品供给事实
  industry_structure: IndustryStructureFacts  # 行业结构事实
  user_signals: UserSignalFacts               # 用户信号事实

# 整合洞察区 - 基于三维事实的综合洞察
integrated_insights: IntegratedInsights

# 下游使用指南
downstream_guidance: DownstreamGuidance
```

### MarketSignalFreeze 对象（市场信号冻结元数据 🔑）

```yaml
MarketSignalFreeze:
  # 关键词集合版本控制
  keyword_set:
    version: string              # 版本号，格式：v1.0, v1.1, v2.0
    included: string[]           # 包含的关键词列表
    excluded: string[]           # 明确排除的关键词列表
    scope_definition: string     # 范围定义说明

  # 接受的假设（冻结时明确接受的假设）
  accepted_assumptions:
    user_problem: string         # 用户问题假设
    industry_stage: MarketStage  # 行业阶段假设
    supply_gap: string           # 供给缺口假设
    target_market: string        # 目标市场假设
    additional: string[]         # 其他假设

  # 置信度评分
  confidence_score:
    data_confidence: ConfidenceStars  # 数据置信度 ★~★★★★★
    assumption_risk: RiskLevel        # 假设风险等级
    overall_reliability: string       # 综合可靠性说明

  # 重新打开条件 - 定义何时需要解冻并重新分析
  reopen_conditions:
    - condition_id: string            # 条件ID，格式：RC-001
      condition_type: ReopenConditionType
      description: string             # 条件描述
      trigger_threshold: string       # 触发阈值
      monitoring_method: string       # 监控方法
      priority: Priority              # 优先级

  # 冻结生命周期
  lifecycle:
    freeze_date: datetime             # 冻结日期
    review_date: datetime             # 建议复审日期
    expiry_date: datetime             # 过期日期（建议重新分析）
    status: FreezeLifecycleStatus     # 生命周期状态
```

### QualityReview 对象（质量评审）

```yaml
QualityReview:
  overall_status: QualityStatus      # 总体质量状态
  overall_score: number              # 总体质量分数 (0-100)

  dimension_reviews:                 # 各维度评审
    competitor_supply:
      status: QualityStatus
      score: number                  # 0-100
      issues: QualityIssue[]         # 发现的问题
      rework_required: boolean       # 是否需要返工
      rework_instructions: string    # 返工指示（如需要）

    industry_structure:
      status: QualityStatus
      score: number
      issues: QualityIssue[]
      rework_required: boolean
      rework_instructions: string

    user_signals:
      status: QualityStatus
      score: number
      issues: QualityIssue[]
      rework_required: boolean
      rework_instructions: string

  review_history:                    # 评审历史
    - round: number                  # 评审轮次
      timestamp: datetime
      status: QualityStatus
      feedback: string
      rework_items: string[]

QualityIssue:
  id: string                         # 问题ID，格式：QI-001
  severity: IssueSeverity            # 严重程度
  dimension: QualityDimension        # 所属维度
  description: string                # 问题描述
  expected: string                   # 期望的内容
  actual: string                     # 实际的内容
  remediation: string                # 修复建议
```

### CompetitorSupplyFacts 对象（竞品供给事实 🔒）

```yaml
CompetitorSupplyFacts:
  _frozen: true                      # 冻结标记
  _frozen_at: datetime
  _version: string                   # v1.0

  market_players:                    # 市场玩家事实
    total_count: number              # 玩家总数
    tier_distribution:               # 层级分布
      tier1_count: number            # 头部玩家数
      tier2_count: number            # 中腰部玩家数
      tier3_count: number            # 长尾玩家数
    concentration: ConcentrationLevel # 集中度
    concentration_data: string       # CR3/CR5数据

  top_products:                      # Top产品事实
    - rank: number
      name: string
      market_share: string
      platform: Platform
      developer: string
      rating: number
      download_count: string
      pricing_model: string
      core_features: string[]
      unique_features: string[]
      launch_date: string
      recent_funding: string
      data_sources: string[]         # 数据来源
      uncertainty_tags: string[]     # 不确定性标注

  supply_gaps:                       # 供给缺口事实
    - gap_description: string
      evidence: string[]
      confidence: ConfidenceLevel

  open_source_alternatives:          # 开源替代品事实
    - name: string
      coverage: string
      adoption: string
      limitations: string[]
```

### IndustryStructureFacts 对象（行业结构事实 🔒）

```yaml
IndustryStructureFacts:
  _frozen: true
  _frozen_at: datetime
  _version: string

  porter_five_forces:                # 波特五力事实
    supplier_power:
      level: ForceLevel              # 高/中/低
      key_suppliers: string[]
      concentration: string
      switching_cost: string
      evidence: string[]

    buyer_power:
      level: ForceLevel
      concentration: string
      price_sensitivity: string
      switching_cost: string
      information_availability: string
      evidence: string[]

    new_entrants_threat:
      level: ForceLevel
      recent_entrants: RecentEntrant[]
      entry_barriers: EntryBarrier[]
      capital_requirement: string
      technology_barrier: string
      regulatory_barrier: string
      evidence: string[]

    substitutes_threat:
      level: ForceLevel
      main_substitutes: string[]
      switching_tendency: string
      price_performance: string
      evidence: string[]

    industry_rivalry:
      level: ForceLevel
      competitor_count: string
      market_growth: string
      product_differentiation: string
      exit_barriers: string
      price_competition: string
      evidence: string[]

  market_fundamentals:               # 市场基本面事实
    market_size:
      global: string
      china: string
      data_year: string
      source: string
    growth_rate:
      cagr: string
      period: string
      source: string
    market_stage: MarketStage
    stage_evidence: string[]

  regulatory_environment:            # 监管环境事实
    key_regulations: string[]
    compliance_requirements: string[]
    policy_trends: string[]
```

### UserSignalFacts 对象（用户信号事实 🔒）

```yaml
UserSignalFacts:
  _frozen: true
  _frozen_at: datetime
  _version: string

  user_demographics:                 # 用户人口统计事实
    primary_age_range: string
    gender_distribution: string
    geographic_distribution: string
    income_level: string
    education_level: string
    occupation_types: string[]
    data_sources: string[]

  user_psychographics:               # 用户心理特征事实
    interests: string[]
    values: string[]
    lifestyle_patterns: string[]
    purchase_motivations: string[]

  user_pain_points:                  # 用户痛点事实（核心）
    - pain_point: string
      severity: PainSeverity         # 严重/中等/轻微
      frequency: string              # 发生频率
      current_solutions: string[]    # 现有解决方案
      unmet_degree: string           # 未被满足程度
      evidence: string[]             # 证据来源
      verbatim_quotes: string[]      # 用户原话

  user_behaviors:                    # 用户行为事实
    usage_frequency: string
    usage_duration: string
    usage_scenarios: string[]
    purchase_patterns: string
    brand_loyalty: string
    churn_reasons: string[]

  demand_signals:                    # 需求信号事实
    - signal_type: SignalType        # 显性/隐性
      description: string
      strength: SignalStrength       # 强/中/弱
      trend_direction: TrendDirection # 上升/平稳/下降
      evidence: string[]
```

### IntegratedInsights 对象（整合洞察）

```yaml
IntegratedInsights:
  opportunity_matrix:                # 机会矩阵
    - opportunity_id: string
      description: string
      supporting_facts:
        competitor_facts: string[]   # 支撑的竞品事实
        industry_facts: string[]     # 支撑的行业事实
        user_facts: string[]         # 支撑的用户事实
      confidence: ConfidenceLevel
      priority: Priority

  risk_matrix:                       # 风险矩阵
    - risk_id: string
      description: string
      supporting_facts:
        competitor_facts: string[]
        industry_facts: string[]
        user_facts: string[]
      severity: RiskSeverity
      probability: Probability
      mitigation_hint: string

  strategic_implications:            # 战略启示
    must_do: string[]                # 必须做的事
    must_avoid: string[]             # 必须避免的事
    key_success_factors: string[]    # 关键成功因素

  one_line_summary: string           # 一句话总结
```

### DownstreamGuidance 对象（下游使用指南）

```yaml
DownstreamGuidance:
  frozen_facts_usage:                # 冻结事实使用说明
    must_respect:                    # 必须遵守的事实
      - fact_id: string
        fact_summary: string
        binding_level: BindingLevel  # 强制/建议

    can_interpret:                   # 可以解读的范围
      - area: string
        guidance: string

    cannot_change:                   # 禁止修改的范围
      - area: string
        reason: string

  for_prd_designer:                  # 给PRD设计者
    product_direction_constraints: string[]
    user_persona_foundation: string[]
    feature_priority_hints: string[]

  for_plan_architect:                # 给计划架构师
    technical_constraints: string[]
    resource_assumptions: string[]
    timeline_factors: string[]

  validation_checkpoints:            # 验证检查点
    - checkpoint: string
      validation_method: string
```

### 枚举定义

```yaml
QualityStatus:
  - passed              # 通过 - 可以冻结
  - needs_rework        # 需返工 - 存在质量问题
  - pending_review      # 待评审 - 尚未评审
  - partially_passed    # 部分通过 - 部分维度需返工

IssueSeverity:
  - critical            # 严重 - 必须修复才能冻结
  - major               # 重要 - 应当修复
  - minor               # 轻微 - 建议修复
  - info                # 信息 - 仅供参考

QualityDimension:
  - completeness        # 完整性 - 是否覆盖所有必需内容
  - accuracy            # 准确性 - 数据是否准确
  - consistency         # 一致性 - 数据是否一致
  - timeliness          # 时效性 - 数据是否最新
  - traceability        # 可追溯性 - 是否有来源标注
  - objectivity         # 客观性 - 是否避免主观判断

ConcentrationLevel:
  - monopoly            # 垄断 (CR3 > 70%)
  - oligopoly           # 寡头 (CR3 50-70%)
  - competitive         # 竞争 (CR3 30-50%)
  - fragmented          # 分散 (CR3 < 30%)

ForceLevel:
  - high                # 高
  - medium              # 中
  - low                 # 低

MarketStage:
  - emerging            # 萌芽期
  - growth              # 成长期
  - mature              # 成熟期
  - declining           # 衰退期

PainSeverity:
  - severe              # 严重痛点
  - moderate            # 中等痛点
  - mild                # 轻微痛点

SignalType:
  - explicit            # 显性需求信号
  - implicit            # 隐性需求信号

SignalStrength:
  - strong              # 强信号
  - medium              # 中等信号
  - weak                # 弱信号

TrendDirection:
  - rising              # 上升趋势
  - stable              # 平稳
  - declining           # 下降趋势

ConfidenceLevel:
  - high                # 高置信度 (多源验证)
  - medium              # 中置信度 (部分验证)
  - low                 # 低置信度 (单源/推测)

RiskSeverity:
  - high                # 高风险
  - medium              # 中风险
  - low                 # 低风险

Probability:
  - likely              # 很可能发生 (>60%)
  - possible            # 可能发生 (30-60%)
  - unlikely            # 不太可能 (<30%)

Priority:
  - critical            # 关键优先
  - high                # 高优先
  - medium              # 中优先
  - low                 # 低优先

BindingLevel:
  - mandatory           # 强制遵守
  - recommended         # 建议遵守
  - optional            # 可选参考

Platform:
  - ios
  - android
  - both
  - web
  - desktop
  - cross_platform

# 市场信号冻结相关枚举
ConfidenceStars:
  - "★"                 # 1星 - 极低置信度（单一来源/强推测）
  - "★★"                # 2星 - 低置信度（少量来源/推测成分高）
  - "★★★"               # 3星 - 中等置信度（多源但未完全验证）
  - "★★★★"              # 4星 - 高置信度（多源验证）
  - "★★★★★"             # 5星 - 极高置信度（权威来源+多重验证）

RiskLevel:
  - low                 # 低风险 - 假设基础稳固
  - medium              # 中风险 - 假设有一定不确定性
  - high                # 高风险 - 假设基础薄弱，需密切监控

ReopenConditionType:
  - trend_reversal      # 搜索趋势反转
  - new_competitor      # 新竞品出现
  - market_shift        # 市场格局变化
  - regulation_change   # 监管政策变化
  - technology_disruption # 技术颠覆
  - user_behavior_change # 用户行为变化
  - data_invalidation   # 关键数据失效
  - assumption_violated # 核心假设被证伪

FreezeLifecycleStatus:
  - active              # 活跃 - 冻结有效
  - review_pending      # 待复审 - 接近复审日期
  - expired             # 已过期 - 建议重新分析
  - reopened            # 已重开 - 触发了重开条件
  - superseded          # 已替代 - 被新版本替代
```

---

## 质量评审标准

### 评审维度与阈值

| 维度 | 合格阈值 | 评审要点 |
|------|----------|----------|
| **完整性** | ≥ 80分 | 所有必填字段是否完整；波特五力是否全覆盖；Top 3是否齐全 |
| **准确性** | ≥ 70分 | 数据是否有来源支撑；是否使用了疑问标注；数值是否合理 |
| **一致性** | ≥ 75分 | 不同来源数据是否一致；前后逻辑是否连贯 |
| **时效性** | ≥ 70分 | 数据是否为近1年内；市场信息是否过时 |
| **可追溯性** | ≥ 80分 | 每条事实是否有来源；来源是否权威 |
| **客观性** | ≥ 75分 | 是否仅陈述事实；是否避免主观判断 |

### 返工触发条件

以下情况**必须返工**：
1. 任一维度分数低于60分
2. 存在 `critical` 严重性的问题
3. 波特五力覆盖不足3个维度
4. Top 3产品分析不足2个
5. 用户痛点分析少于3条
6. 超过30%的数据缺失来源标注

### 返工指示格式

```markdown
## 🔄 返工要求

### 返工原因
{问题描述}

### 具体要求
1. {要求1}
2. {要求2}
3. {要求3}

### 返工范围
- [ ] 竞品供给分析 - {具体问题}
- [ ] 行业结构分析 - {具体问题}
- [ ] 用户信号分析 - {具体问题}

### 返工后重新提交
请修复上述问题后，重新运行 `/freeze-analysis` 进行评审。
```

---

## Markdown 输出格式

```markdown
# 冻结分析报告 🔒

---

## 📋 报告概要

| 项目 | 内容 |
|------|------|
| **分析ID** | FA-20250104-001 |
| **来源契约** | TR-20250103-001, BO-20250103-001 |
| **分析领域** | {keyword} |
| **冻结时间** | 2025-01-04 10:30:00 |
| **冻结版本** | v1.0 |
| **质量状态** | ✅ 已通过 |
| **评审轮次** | 2 |

---

## 🔑 市场信号冻结

> 模板参考: `templates/market-signal-freeze.md`

### Keyword Set

- v{X.Y}

- included:
  - {keyword_1}
  - {keyword_2}
  - {keyword_3}

- excluded:
  - {excluded_1}
  - {excluded_2}

### Accepted Assumptions

- User problem: {用户核心问题假设}

- Industry stage: {行业阶段: 萌芽期/成长期/成熟期/衰退期}

- Supply gap: {供给缺口假设}

### Confidence Score

- Data confidence: ★★★★☆

- Assumption risk: 中

### Re-open Conditions

- 搜索趋势反转
  > 触发: 连续3个月下降>30%

- 新竞品出现
  > 触发: 市占率>5%或融资>$10M

### Lifecycle

- 冻结: {YYYY-MM-DD}
- 复审: {YYYY-MM-DD} (3个月后)
- 过期: {YYYY-MM-DD} (6个月后)
- 状态: 🟢 活跃

---

## 🔍 质量评审结果

### 总体评分: {score}/100 {status_emoji}

| 维度 | 分数 | 状态 | 说明 |
|------|------|------|------|
| 竞品供给分析 | {score}/100 | ✅/⚠️ | {summary} |
| 行业结构分析 | {score}/100 | ✅/⚠️ | {summary} |
| 用户信号分析 | {score}/100 | ✅/⚠️ | {summary} |

### 评审历史

| 轮次 | 时间 | 状态 | 反馈 |
|------|------|------|------|
| 1 | {time} | 🔄 需返工 | {feedback} |
| 2 | {time} | ✅ 通过 | 质量达标，准予冻结 |

---

## 🔒 冻结事实区

> ⚠️ **重要提示**: 以下事实已冻结，后续Agent**禁止修改或重新解释**。
> 只能基于这些事实进行决策和建议。

---

### 🏆 竞品供给事实

#### 市场玩家格局

| 指标 | 数据 | 来源 |
|------|------|------|
| **玩家总数** | {count} | {source} |
| **市场集中度** | {concentration} | {source} |
| **头部玩家数** | {tier1_count} | {source} |
| **CR3** | {cr3_value} | {source} |

#### Top 3 产品事实

##### 🥇 第1名: {product_name}

| 维度 | 事实 | 置信度 |
|------|------|--------|
| **市场份额** | {share} | ⭐⭐⭐ |
| **平台** | {platform} | ⭐⭐⭐ |
| **评分** | {rating} ⭐ | ⭐⭐⭐ |
| **下载量** | {downloads} | ⭐⭐ |
| **定价模式** | {pricing} | ⭐⭐⭐ |

**核心功能**:
- {feature_1}
- {feature_2}
- {feature_3}

**独特功能**:
- {unique_1}
- {unique_2}

##### 🥈 第2名: {product_name}
[同上结构]

##### 🥉 第3名: {product_name}
[同上结构]

#### 供给缺口事实

| # | 缺口描述 | 证据 | 置信度 |
|---|----------|------|--------|
| 1 | {gap_1} | {evidence} | ⭐⭐⭐/⭐⭐/⭐ |
| 2 | {gap_2} | {evidence} | ⭐⭐⭐/⭐⭐/⭐ |

---

### 📊 行业结构事实

#### 波特五力分析

| 力量 | 强度 | 关键事实 | 证据来源 |
|------|------|----------|----------|
| 🔴 供应商议价能力 | {level} | {key_fact} | {source} |
| 🟠 买方议价能力 | {level} | {key_fact} | {source} |
| 🟡 新进入者威胁 | {level} | {key_fact} | {source} |
| 🟢 替代品威胁 | {level} | {key_fact} | {source} |
| 🔵 行业竞争程度 | {level} | {key_fact} | {source} |

##### 🔴 供应商议价能力详情

| 维度 | 事实 |
|------|------|
| **主要供应商** | {suppliers} |
| **集中度** | {concentration} |
| **切换成本** | {switching_cost} |

**证据**:
- {evidence_1}
- {evidence_2}

[其他四力类似结构]

#### 市场基本面

| 指标 | 数据 | 来源 |
|------|------|------|
| **全球市场规模** | {global_size} | {source} |
| **中国市场规模** | {china_size} | {source} |
| **CAGR** | {cagr} | {source} |
| **市场阶段** | {stage} | {evidence} |

---

### 👥 用户信号事实

#### 用户画像事实

**人口统计特征**:

| 维度 | 事实 | 来源 |
|------|------|------|
| **年龄段** | {age_range} | {source} |
| **性别分布** | {gender} | {source} |
| **地域分布** | {geography} | {source} |
| **收入水平** | {income} | {source} |
| **职业类型** | {occupation} | {source} |

**心理特征**:
- **兴趣**: {interests}
- **价值观**: {values}
- **生活方式**: {lifestyle}

#### 用户痛点事实 ⭐

| # | 痛点描述 | 严重度 | 现有解决方案 | 未被满足程度 |
|---|----------|--------|--------------|--------------|
| 1 | {pain_1} | 🔴 严重 | {solutions} | {unmet} |
| 2 | {pain_2} | 🟠 中等 | {solutions} | {unmet} |
| 3 | {pain_3} | 🟡 轻微 | {solutions} | {unmet} |

**用户原话**:
> "{verbatim_quote_1}"
> "{verbatim_quote_2}"

#### 需求信号事实

| 信号类型 | 描述 | 强度 | 趋势 | 证据 |
|----------|------|------|------|------|
| 显性 | {signal_1} | 🔴 强 | ↗️ 上升 | {evidence} |
| 隐性 | {signal_2} | 🟠 中 | ➡️ 平稳 | {evidence} |

---

## 💡 整合洞察

### 机会矩阵

| # | 机会描述 | 支撑事实 | 置信度 | 优先级 |
|---|----------|----------|--------|--------|
| 1 | {opportunity_1} | [竞品]{fact}, [行业]{fact}, [用户]{fact} | ⭐⭐⭐ | 🔴 关键 |
| 2 | {opportunity_2} | [竞品]{fact}, [用户]{fact} | ⭐⭐ | 🟠 高 |

### 风险矩阵

| # | 风险描述 | 支撑事实 | 严重性 | 概率 | 缓解提示 |
|---|----------|----------|--------|------|----------|
| 1 | {risk_1} | [行业]{fact} | 🔴 高 | 很可能 | {hint} |
| 2 | {risk_2} | [竞品]{fact} | 🟠 中 | 可能 | {hint} |

### 战略启示

**必须做的事**:
- {must_do_1}
- {must_do_2}

**必须避免的事**:
- {must_avoid_1}
- {must_avoid_2}

**关键成功因素**:
1. {ksf_1}
2. {ksf_2}
3. {ksf_3}

### 一句话总结

> {one_line_summary}

---

## 📤 下游使用指南

### 🔒 必须遵守的事实

以下事实为**强制约束**，后续Agent不可违背：

| 事实 | 约束级别 | 说明 |
|------|----------|------|
| {fact_1} | 🔴 强制 | {explanation} |
| {fact_2} | 🔴 强制 | {explanation} |
| {fact_3} | 🟠 建议 | {explanation} |

### ✅ 可以解读的范围

以下领域允许后续Agent进行解读和决策：

- **产品定位**: 可基于事实选择差异化方向
- **功能优先级**: 可基于痛点严重度排序
- **市场策略**: 可基于竞争格局制定进入策略

### ❌ 禁止修改的范围

以下内容**禁止后续Agent修改**：

- ❌ 市场规模数据
- ❌ 竞品功能和定价事实
- ❌ 用户痛点描述
- ❌ 波特五力评级结果
- ❌ 所有标注为🔒的事实

### 给PRD设计者

**产品方向约束**:
- {constraint_1}
- {constraint_2}

**用户画像基础**:
- {persona_foundation_1}
- {persona_foundation_2}

**功能优先级提示**:
- {feature_hint_1}
- {feature_hint_2}

### 给计划架构师

**技术约束**:
- {tech_constraint_1}
- {tech_constraint_2}

**资源假设**:
- {resource_assumption_1}
- {resource_assumption_2}

---

## 📚 数据来源汇总

| 类型 | 来源数量 | 可靠性分布 |
|------|----------|------------|
| 官方数据 | {count} | ⭐⭐⭐ |
| 行业报告 | {count} | ⭐⭐⭐ |
| 新闻资讯 | {count} | ⭐⭐ |
| 用户评论 | {count} | ⭐⭐ |
| 推测信息 | {count} | ⭐ |

---

*本报告由分析冻结 Agent 生成*
*冻结时间: {frozen_at}*
*契约版本: 1.0.0*
*来源契约: {source_contracts}*

**🔒 冻结声明**: 本报告事实区内容已冻结，后续Agent必须遵守，不可擅自修改。
如需更新事实，请重新运行分析流水线并触发冻结流程。
```

---

## 验证规则

### 冻结前验证

1. **质量验证**:
   - 所有维度评审分数 ≥ 60分
   - 无 `critical` 级别问题
   - 总体分数 ≥ 70分

2. **完整性验证**:
   - `frozen_facts` 三个维度均有内容
   - 波特五力覆盖 ≥ 3个
   - Top产品 ≥ 2个
   - 用户痛点 ≥ 3条

3. **追溯性验证**:
   - 所有 `source_contracts` 必须存在对应报告
   - 所有事实必须有 `evidence` 或 `data_sources`

### 冻结后验证

1. **不可变性验证**:
   - `_frozen` 标记为 `true`
   - `_frozen_at` 时间戳存在
   - `_version` 版本号存在

2. **下游合规验证**:
   - 下游Agent输出不得与冻结事实冲突
   - 下游Agent引用事实时需标注来源

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-04 | 初始版本 |
| 1.1.0 | 2025-01-04 | 新增市场信号冻结元数据 (MarketSignalFreeze)：Keyword Set版本控制、Accepted Assumptions假设管理、Confidence Score置信度评分、Re-open Conditions重开条件、Lifecycle生命周期管理 |
