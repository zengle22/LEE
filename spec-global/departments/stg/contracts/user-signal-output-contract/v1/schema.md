# 用户信号分析输出契约 (Output Contract)

> **契约版本**: 1.0.0
> **上游Agent**: google-keyword-searcher
> **本Agent**: user-signal-analyzer (用户信号分析Agent)
> **下游Agent**: business-opportunity-analyzer, prd-designer
> **用途**: 定义用户信号分析的输出格式，回答"搜索这个词的人，试图解决什么问题"

---

## 契约说明

本契约定义了用户信号分析的标准输出格式。Agent基于关键词搜索数据，深度分析用户画像、搜索意图和痛点信号，为下游的商业机会分析和产品设计提供洞察。

**核心问题**: 搜索这个词的人，试图解决什么问题？

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: user-signal-output
contract_version: "1.0.0"
metadata:
  analysis_id: string           # 分析ID，格式：USO-YYYYMMDD-XXX
  source_contract: string       # 输入契约ID
  source_domain: string         # 分析的目标领域
  generated_at: datetime        # 生成时间 ISO 8601
  keyword_count: number         # 分析的关键词数量

user_personas: UserPersona[]                # 用户画像假设
intent_analysis: IntentAnalysis             # 搜索意图分析
pain_point_signals: PainPointSignals        # 痛点强度信号
problem_synthesis: ProblemSynthesis         # 问题综合
pending_confirmation: PendingConfirmation[] # 待确认事项
downstream_handoff: DownstreamHandoff       # 下游交接信息
```

### UserPersona 对象

```yaml
UserPersona:
  persona_id: string                  # 画像ID，格式：P1, P2, P3...
  who: WhoProfile                     # 谁
  scenario: ScenarioProfile           # 场景
  confidence: ConfidenceLevel         # 置信度
  evidence: string[]                  # 支撑证据（关键词）
```

### WhoProfile 对象

```yaml
WhoProfile:
  primary_label: string               # 主标签（如：跑步新手）
  demographics:
    age_range: string                 # 年龄段估算
    experience_level: ExperienceLevel # 经验水平
    tech_savviness: TechLevel         # 技术素养
  motivations: string[]               # 动机
  frustrations: string[]              # 挫败点
```

### ScenarioProfile 对象

```yaml
ScenarioProfile:
  context: string                     # 场景描述
  trigger: string                     # 触发搜索的事件
  goal: string                        # 期望达成的目标
  constraints: string[]               # 约束条件
```

### IntentAnalysis 对象

```yaml
IntentAnalysis:
  intent_distribution:                # 意图分布
    informational: IntentDetail       # 信息型
    tool_seeking: IntentDetail        # 工具型
    pre_transaction: IntentDetail     # 交易前型
    navigational: IntentDetail        # 导航型

  intent_patterns:                    # 意图模式
    - pattern_name: string
      description: string
      keywords: string[]
      user_need: string
```

### IntentDetail 对象

```yaml
IntentDetail:
  percentage: number                  # 占比(0-100)
  typical_keywords: string[]          # 典型关键词
  user_mindset: string                # 用户心态
  conversion_readiness: ConversionLevel # 转化准备度
```

### PainPointSignals 对象

```yaml
PainPointSignals:
  frequency_signals:                  # 频率信号
    high_volume_keywords: string[]    # 高搜索量关键词
    repeat_patterns: string[]         # 重复搜索模式
    volume_trend: Trend               # 搜索量趋势
    frequency_score: number           # 频率评分(0-100)

  urgency_signals:                    # 紧急性信号
    urgent_markers: string[]          # 紧急标记词
    time_pressure_indicators: string[] # 时间压力指示
    urgency_score: number             # 紧急评分(0-100)

  failure_cost_signals:               # 失败成本信号
    consequence_keywords: string[]    # 后果相关词
    risk_indicators: string[]         # 风险指示
    emotional_markers: string[]       # 情绪标记
    failure_cost_score: number        # 失败成本评分(0-100)

  overall_pain_intensity: PainIntensity  # 综合痛点强度
```

### ProblemSynthesis 对象

```yaml
ProblemSynthesis:
  core_problem_statement: string      # 核心问题陈述

  problem_tree:                       # 问题树
    root_problem: string              # 根本问题
    sub_problems:                     # 子问题
      - problem: string
        evidence: string[]
        frequency: Frequency

  jobs_to_be_done:                    # 待完成任务
    - job_statement: string           # 任务陈述（When... I want to... So that...）
      importance: Importance
      satisfaction_gap: GapLevel      # 当前满足差距

  opportunity_areas: string[]         # 机会领域
```

### PendingConfirmation 对象

```yaml
PendingConfirmation:
  id: string                          # 待确认项ID
  category: ConfirmationCategory      # 分类
  assumption: string                  # 假设内容
  validation_method: string           # 建议验证方法
  impact: string                      # 对结论的影响
  priority: Priority                  # 优先级
```

### DownstreamHandoff 对象

```yaml
DownstreamHandoff:
  for_business_opportunity:
    target_user_summary: string       # 目标用户总结
    pain_intensity_summary: string    # 痛点强度总结
    demand_validation: string         # 需求验证结论

  for_prd_designer:
    primary_persona: string           # 首要用户画像
    core_jobs: string[]               # 核心任务
    must_solve_problems: string[]     # 必须解决的问题
    value_proposition_hints: string[] # 价值主张提示

  key_insights: string[]              # 关键洞察
  recommended_next_steps: string[]    # 建议下一步
```

### 枚举定义

```yaml
ConfidenceLevel:
  - high        # 高置信：有多个强证据支撑
  - medium      # 中置信：有部分证据支撑
  - low         # 低置信：推测性假设，需验证

ExperienceLevel:
  - beginner    # 新手
  - intermediate # 中级
  - advanced    # 高级
  - expert      # 专家

TechLevel:
  - high        # 高：技术敏感，愿意尝试新工具
  - medium      # 中：普通用户
  - low         # 低：需要简单易用的解决方案

ConversionLevel:
  - ready       # 准备好转化
  - considering # 考虑中
  - exploring   # 探索阶段
  - unaware     # 未意识到需求

PainIntensity:
  - critical    # 极高：必须解决，愿意付费
  - high        # 高：强烈需求，积极寻找方案
  - medium      # 中：有需求，但非紧急
  - low         # 低：nice-to-have

Frequency:
  - very_high   # 极高频
  - high        # 高频
  - medium      # 中频
  - low         # 低频

Importance:
  - critical    # 关键
  - important   # 重要
  - nice_to_have # 锦上添花

GapLevel:
  - large       # 大差距：市场严重未满足
  - medium      # 中差距：有方案但不够好
  - small       # 小差距：已有较好解决方案

Trend:
  - rising      # 上升
  - stable      # 稳定
  - declining   # 下降
  - seasonal    # 季节性

ConfirmationCategory:
  - persona_assumption    # 用户画像假设
  - intent_inference      # 意图推断
  - pain_intensity        # 痛点强度
  - market_signal         # 市场信号

Priority:
  - critical    # 关键
  - important   # 重要
  - nice_to_have # 补充
```

---

## Markdown 输出格式

```markdown
# 用户信号分析报告

---

## 分析概要

| 项目 | 内容 |
|------|------|
| **分析ID** | USO-20260104-001 |
| **输入契约** | USI-20260104-001 |
| **分析领域** | {source_domain} |
| **分析时间** | 2026-01-04 10:30:00 |
| **关键词数量** | {keyword_count} |

**核心发现**: {一句话核心发现}

---

## 用户画像假设

> 基于搜索行为推断的用户画像，需要进一步验证

### P1: {primary_label} [置信度: {confidence}]

**谁**:
- 年龄段: {age_range}
- 经验水平: {experience_level}
- 技术素养: {tech_savviness}

**动机**:
- {motivation_1}
- {motivation_2}

**挫败点**:
- {frustration_1}
- {frustration_2}

**典型场景**:
> 触发: {trigger}
> 场景: {context}
> 目标: {goal}
> 约束: {constraints}

**证据关键词**:
`{keyword_1}` `{keyword_2}` `{keyword_3}`

---

## 搜索意图分析

### 意图分布

```
信息型 ({informational_pct}%)
├── 典型词: {keywords}
└── 心态: {mindset}

工具型 ({tool_seeking_pct}%)
├── 典型词: {keywords}
└── 心态: {mindset}

交易前型 ({pre_transaction_pct}%)
├── 典型词: {keywords}
└── 心态: {mindset}

导航型 ({navigational_pct}%)
├── 典型词: {keywords}
└── 心态: {mindset}
```

### 意图模式识别

| 模式 | 描述 | 用户需求 |
|------|------|----------|
| {pattern_1} | {description} | {user_need} |
| {pattern_2} | {description} | {user_need} |

---

## 痛点强度信号

### 频率信号 - 评分: {frequency_score}/100

**高搜索量关键词**:
- {keyword_1}
- {keyword_2}

**搜索量趋势**: {trend}

**分析**: {frequency_analysis}

### 紧急性信号 - 评分: {urgency_score}/100

**紧急标记词**:
- {urgent_marker_1}
- {urgent_marker_2}

**时间压力指示**:
- {time_pressure_1}

**分析**: {urgency_analysis}

### 失败成本信号 - 评分: {failure_cost_score}/100

**后果相关词**:
- {consequence_1}

**情绪标记**:
- {emotional_marker_1}

**分析**: {failure_cost_analysis}

### 综合痛点强度: {overall_pain_intensity}

{pain_intensity_explanation}

---

## 问题综合

### 核心问题陈述

> {core_problem_statement}

### 问题树

```
{root_problem}
├── {sub_problem_1} [证据: {evidence}] [频率: {frequency}]
├── {sub_problem_2} [证据: {evidence}] [频率: {frequency}]
└── {sub_problem_3} [证据: {evidence}] [频率: {frequency}]
```

### Jobs to be Done

| 任务陈述 | 重要性 | 满足差距 |
|----------|--------|----------|
| When {situation}, I want to {motivation}, So that {outcome} | {importance} | {gap} |

### 机会领域

1. {opportunity_area_1}
2. {opportunity_area_2}
3. {opportunity_area_3}

---

## 待确认事项

> 以下假设需要进一步验证

| ID | 分类 | 假设 | 验证方法 | 优先级 |
|----|------|------|----------|--------|
| PC-001 | {category} | {assumption} | {validation_method} | {priority} |

---

## 下游交接信息

### 供商业机会分析使用

**目标用户总结**: {target_user_summary}

**痛点强度总结**: {pain_intensity_summary}

**需求验证结论**: {demand_validation}

### 供产品设计使用

**首要用户画像**: {primary_persona}

**核心任务**:
- {core_job_1}
- {core_job_2}

**必须解决的问题**:
- {must_solve_1}
- {must_solve_2}

**价值主张提示**:
- {value_proposition_1}
- {value_proposition_2}

### 关键洞察

1. {insight_1}
2. {insight_2}
3. {insight_3}

### 建议下一步

1. {next_step_1}
2. {next_step_2}

---

*本报告由用户信号分析 Agent 生成*
*契约版本: 1.0.0*
```

---

## 分析指南

### 意图类型判断标准

| 意图类型 | 判断标准 | 典型标记 |
|----------|----------|----------|
| 信息型 (Informational) | 用户想了解、学习某个话题 | 什么是、原理、怎么理解 |
| 工具型 (Tool-seeking) | 用户在寻找工具/方案解决问题 | app、工具、软件、方法 |
| 交易前型 (Pre-transaction) | 用户准备做购买/使用决策 | 哪个好、推荐、对比、评测 |
| 导航型 (Navigational) | 用户想找特定网站/产品 | 品牌名、官网、下载 |

### 痛点强度评估维度

| 维度 | 权重 | 评估要点 |
|------|------|----------|
| 频率 (Frequency) | 35% | 搜索量、重复搜索模式、趋势 |
| 紧急性 (Urgency) | 35% | 时间压力词、紧急标记、即时需求 |
| 失败成本 (Failure Cost) | 30% | 后果严重程度、情绪强度、风险敏感 |

### 置信度判断标准

| 置信度 | 标准 |
|--------|------|
| 高 | 3个以上强证据，多个关键词一致指向 |
| 中 | 1-2个证据，需要补充验证 |
| 低 | 推测性结论，缺乏直接证据 |

---

## 验证规则

1. **必填字段**: `analysis_id`, `source_domain`, `user_personas[]`, `pain_point_signals`
2. **用户画像**: 至少1个，最多5个，每个必须有evidence
3. **意图分析**: 四种意图类型占比总和必须为100%
4. **痛点评分**: 三个维度评分都必须有值(0-100)
5. **待确认事项**: 如有低置信度假设，必须列入pending_confirmation

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-04 | 初始版本 |
