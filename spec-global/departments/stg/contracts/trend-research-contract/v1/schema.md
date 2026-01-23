# 热词调研输出契约 (Output Contract)

> **契约版本**: 2.0.0
> **上游Agent**: google-trend-researcher (本Agent)
> **下游Agent**: business-opportunity-analyzer (商业机会分析Agent)
> **用途**: 定义热词背景调研结果的标准格式，供下游商业机会分析使用

---

## 契约说明

本契约定义了热词背景调研的输出格式。本Agent负责：
1. **波特五力模型数据收集** - 对每个细分类别收集五力分析所需数据
2. **Top 3 产品深度调研** - 用户画像、主要功能、差异化营销
3. **市场数据整理** - 收集原始市场信息
4. **报告拆分** - 细分类别 > 3 时自动拆分为多份报告

**职责边界**:
- **本Agent职责**: 收集、整理、分类背景信息（不做分析判断）
- **下游Agent职责**: 基于背景信息进行商业机会分析和决策建议

**🚨 完整性要求**:
- Agent必须自主完成全部调研工作，输出完整报告
- 禁止中途询问用户"是否继续"
- 遇到不确定信息时使用疑问标注，而非停止工作
- 细分类别 > 3 时自动拆分为多份报告

---

## 🔗 追踪机制

通过 **Contract ID 关联** 实现输入输出报告的追踪：

```
关键词报告                      调研报告
┌─────────────────────┐       ┌─────────────────────┐
│ 分析ID: KW-20250103-001 │ ───→ │ 输入契约: KW-20250103-001 │
└─────────────────────┘       │ 调研ID: TR-20250103-001  │
                              └─────────────────────┘
```

### 追踪字段说明

| 字段 | 位置 | 格式 | 用途 |
|------|------|------|------|
| `分析ID` | 关键词报告 | `KW-YYYYMMDD-XXX` | 唯一标识关键词报告 |
| `调研ID` | 调研报告 | `TR-YYYYMMDD-XXX` | 唯一标识调研报告 |
| `输入契约` | 调研报告 | `KW-YYYYMMDD-XXX` | **关键**：关联到源关键词报告 |

### 拆分报告追踪

当细分类别 > 3 时，报告会拆分：

```
关键词报告                      调研报告（拆分）
┌─────────────────────┐       ┌─────────────────────┐
│ 分析ID: KW-20250103-001 │ ───→ │ TR-20250103-001-01  │ 细分类别A
└─────────────────────┘       │ TR-20250103-001-02  │ 细分类别B
                              │ TR-20250103-001-03  │ 细分类别C
                              │ TR-20250103-001-04  │ 细分类别D
                              └─────────────────────┘
```

### 追踪规则

1. **唯一性**: 每个关键词报告只生成一份/一组调研报告（除非强制重新调研）
2. **可追溯**: 通过调研报告的`输入契约`字段可追溯到源关键词报告
3. **幂等性**: 重复运行时自动跳过已处理的报告
4. **强制模式**: 使用 `--force` 参数可忽略追踪状态重新调研

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: trend-research-output
contract_version: "2.0.0"
metadata:
  research_id: string           # 调研ID，格式：TR-YYYYMMDD-XXX[-子序号]
  source_contract: string       # 输入契约ID (来自keyword-contract)
  generated_at: datetime        # 生成时间 ISO 8601
  keyword_count: number         # 调研关键词数量
  segment_count: number         # 细分类别数量
  is_split_report: boolean      # 是否为拆分报告
  related_reports: string[]     # 关联的其他拆分报告ID
  total_products_found: number  # 发现的产品总数
  total_sources: number         # 信息来源总数

segments_research: SegmentResearch[]  # 各细分类别的调研结果
summary: ResearchSummary              # 调研汇总
```

### SegmentResearch 对象 (细分类别调研)

```yaml
SegmentResearch:
  segment_name: string              # 细分类别名称
  segment_definition: string        # 细分类别定义
  research_status: ResearchStatus   # 调研状态

  # 背景信息
  background:
    definition: string              # 定义/解释
    origin: string                  # 起源/来源
    popularity_reason: string       # 火起来的原因
    related_events: string[]        # 相关事件/新闻

  # 波特五力分析数据 ⭐ 核心
  porter_five_forces:
    supplier_power: SupplierPower
    buyer_power: BuyerPower
    new_entrants_threat: NewEntrantsThreat
    substitutes_threat: SubstitutesThreat
    industry_rivalry: IndustryRivalry

  # Top 3 产品深度分析 ⭐ 核心
  top_products: TopProduct[]        # 市场占有率前三的产品

  # 市场数据（原始收集，不做分析）
  market_data:
    market_size_info: string[]      # 市场规模相关信息
    growth_info: string[]           # 增长相关信息
    key_players: string[]           # 主要玩家
    investment_news: string[]       # 投融资新闻

  # 信息来源
  sources: Source[]                 # 所有信息来源
```

### 波特五力数据结构 ⭐

#### SupplierPower (供应商议价能力)

```yaml
SupplierPower:
  key_suppliers: string[]           # 主要供应商/技术提供商列表
  supplier_concentration: string    # 供应商集中度
  switching_cost: string            # 切换成本描述
  supplier_differentiation: string  # 供应商差异化程度
  dependency_level: string          # 依赖程度
  raw_data: RawDataItem[]           # 原始数据及来源
```

#### BuyerPower (买方议价能力)

```yaml
BuyerPower:
  buyer_concentration: string       # 买方集中度
  purchase_volume: string           # 购买量规模
  switching_cost: string            # 用户切换成本
  price_sensitivity: string         # 价格敏感度
  information_availability: string  # 信息透明度
  alternative_options: string[]     # 可选替代方案
  raw_data: RawDataItem[]
```

#### NewEntrantsThreat (新进入者威胁)

```yaml
NewEntrantsThreat:
  recent_entrants: RecentEntrant[]  # 近期新进入者列表
  entry_barriers: EntryBarrier[]    # 进入壁垒清单
  capital_requirements: string      # 资金要求
  technology_barriers: string       # 技术壁垒
  regulatory_barriers: string       # 政策/监管壁垒
  brand_loyalty: string             # 品牌忠诚度
  economies_of_scale: string        # 规模经济
  raw_data: RawDataItem[]

RecentEntrant:
  name: string                      # 公司/产品名
  entry_date: string                # 进入时间
  funding: string                   # 融资情况
  description: string               # 简介

EntryBarrier:
  type: string                      # 壁垒类型
  level: BarrierLevel               # 高/中/低
  description: string               # 描述
```

#### SubstitutesThreat (替代品威胁)

```yaml
SubstitutesThreat:
  substitute_products: SubstituteProduct[]  # 替代品列表
  substitute_performance: string    # 替代品性能对比
  switching_tendency: string        # 用户切换倾向
  price_performance_ratio: string   # 性价比对比
  raw_data: RawDataItem[]

SubstituteProduct:
  name: string                      # 替代品名称
  category: string                  # 类别
  comparison: string                # 与本类别对比
```

#### IndustryRivalry (行业竞争程度)

```yaml
IndustryRivalry:
  competitor_count: string          # 竞争者数量
  market_concentration: string      # 市场集中度(CR3/CR5)
  market_growth_rate: string        # 市场增长率
  product_differentiation: string   # 产品差异化程度
  exit_barriers: string             # 退出壁垒
  competitive_moves: string[]       # 近期竞争动作
  price_competition: string         # 价格竞争程度
  raw_data: RawDataItem[]
```

### TopProduct 对象 ⭐ (Top 3 产品深度分析)

```yaml
TopProduct:
  rank: number                      # 排名 (1, 2, 3)
  name: string                      # 产品名称
  market_share: string              # 市场份额
  platform: Platform                # 平台

  # 基本信息
  basic_info:
    developer: string               # 开发者/公司
    store_url: string               # 商店链接
    official_url: string            # 官网链接
    rating: number                  # 评分 (1-5)
    rating_count: string            # 评分数量
    download_count: string          # 下载量
    founded_date: string            # 成立时间
    headquarters: string            # 总部位置

  # 用户画像深度调研 ⭐
  user_profile:
    demographics:
      age_range: string             # 年龄段
      gender_ratio: string          # 性别比例
      geography: string             # 地域分布
      income_level: string          # 收入水平
      occupation: string[]          # 职业分布
      education: string             # 教育水平
    psychographics:
      interests: string[]           # 兴趣爱好
      values: string[]              # 价值观
      lifestyle: string             # 生活方式
      pain_points: string[]         # 痛点原文
      motivations: string[]         # 使用动机
    behavioral:
      usage_frequency: string       # 使用频率
      usage_scenarios: string[]     # 使用场景
      usage_duration: string        # 使用时长
      purchase_behavior: string     # 购买行为
      brand_loyalty: string         # 品牌忠诚度
      churn_reasons: string[]       # 流失原因
    user_reviews_raw: string[]      # 用户评价原文

  # 主要功能深度调研 ⭐
  features:
    core_features: FeatureItem[]    # 核心功能列表
    unique_features: FeatureItem[]  # 独特/差异化功能
    feature_comparison: string      # 功能对比描述
    technology_stack: string[]      # 技术栈（如可识别）
    api_integrations: string[]      # API/集成能力
    pricing:
      model: string                 # 定价模式
      tiers: PricingTier[]          # 价格层级
      free_features: string[]       # 免费功能
      paid_features: string[]       # 付费功能
    recent_updates: UpdateItem[]    # 近期功能更新
    roadmap: string[]               # 产品路线图（如公开）

  # 差异化营销调研 ⭐
  marketing:
    positioning: string             # 市场定位
    target_segment: string          # 目标细分市场
    unique_selling_points: string[] # 独特卖点USP
    brand_message: string           # 品牌信息/slogan
    brand_personality: string       # 品牌个性
    marketing_channels: MarketingChannel[]  # 营销渠道
    content_strategy: string        # 内容策略
    social_presence: SocialPresence[]       # 社交媒体表现
    partnerships: string[]          # 合作伙伴/代言
    promotions: string[]            # 促销活动
    advertising: string[]           # 广告投放
    differentiation_vs_competitors: DifferentiationItem[]  # 与竞品差异

  # 信息来源
  sources: Source[]

FeatureItem:
  name: string                      # 功能名称
  description: string               # 功能描述
  category: string                  # 功能类别

PricingTier:
  name: string                      # 层级名称
  price: string                     # 价格
  billing_cycle: string             # 计费周期
  features: string[]                # 包含功能

UpdateItem:
  date: string                      # 更新日期
  version: string                   # 版本号
  changes: string[]                 # 更新内容

MarketingChannel:
  channel: string                   # 渠道名称
  description: string               # 渠道描述
  effectiveness: string             # 效果评估

SocialPresence:
  platform: string                  # 平台名称
  followers: string                 # 粉丝数
  engagement: string                # 互动情况
  content_type: string              # 内容类型

DifferentiationItem:
  competitor: string                # 竞品名称
  differences: string[]             # 差异点
```

### Source 对象

```yaml
Source:
  type: SourceType                  # 来源类型
  url: string                       # 链接
  title: string                     # 标题
  snippet: string                   # 摘要
  retrieved_at: datetime            # 获取时间
  reliability: Reliability          # 可靠性评估

RawDataItem:
  content: string                   # 原始内容
  source: Source                    # 来源信息
```

### ResearchSummary 对象

```yaml
ResearchSummary:
  segments_researched: string[]     # 已调研细分类别列表
  segments_skipped: string[]        # 跳过的细分类别及原因
  total_top_products: number        # 调研的Top产品总数
  porter_coverage: PorterCoverage   # 波特五力覆盖情况
  data_freshness: string            # 数据新鲜度说明
  coverage_notes: string            # 覆盖范围说明
  limitations: string[]             # 调研限制说明

PorterCoverage:
  supplier_power: CoverageLevel     # 供应商议价能力覆盖
  buyer_power: CoverageLevel        # 买方议价能力覆盖
  new_entrants: CoverageLevel       # 新进入者威胁覆盖
  substitutes: CoverageLevel        # 替代品威胁覆盖
  rivalry: CoverageLevel            # 行业竞争程度覆盖
```

### 枚举定义

```yaml
ResearchStatus:
  - completed       # 调研完成（波特五力+Top3产品全部完成）
  - partial         # 部分完成（有维度或产品缺失）
  - failed          # 调研失败
  - skipped         # 跳过（原因说明）

Platform:
  - ios             # iOS
  - android         # Android
  - both            # 双平台
  - web             # Web应用
  - desktop         # 桌面应用
  - cross_platform  # 跨平台

SourceType:
  - search_result   # 搜索结果
  - app_store       # App商店
  - news_article    # 新闻文章
  - official_site   # 官方网站
  - review_site     # 评测网站
  - forum           # 论坛/社区
  - report          # 行业报告
  - social_media    # 社交媒体
  - investor_report # 投资者报告

Reliability:
  - high            # 高可靠（官方/权威来源）
  - medium          # 中等可靠
  - low             # 低可靠（需验证）
  - unverified      # 未验证

BarrierLevel:
  - high            # 高壁垒
  - medium          # 中等壁垒
  - low             # 低壁垒

CoverageLevel:
  - full            # 完全覆盖
  - partial         # 部分覆盖
  - minimal         # 最低覆盖
  - none            # 无数据

UncertaintyTag:
  - "[?]"           # 数据存疑
  - "[待验证]"      # 需要验证
  - "[推测]"        # 推测信息
  - "[缺失]"        # 信息缺失
  - "[来源冲突]"    # 来源冲突
```

---

## 🔶 疑问标注规范

当收集到的信息存在不确定性时，**必须使用标准化的疑问标注**，而不是停止工作或询问用户。

### 标注类型

| 标注 | 含义 | 使用场景 | 示例 |
|------|------|----------|------|
| `[?]` | 数据存疑 | 数据来源不权威或数值可疑 | `市场规模: 50亿 [?]` |
| `[待验证]` | 需要验证 | 信息可能过时或未经多方证实 | `增长率: 30% [待验证]` |
| `[推测]` | 推测信息 | 基于有限信息的合理推断 | `用户年龄: 25-35岁 [推测]` |
| `[缺失]` | 信息缺失 | 搜索后仍未找到相关信息 | `融资情况: [缺失]` |
| `[来源冲突]` | 来源冲突 | 不同来源给出矛盾数据 | `用户数: 100万/500万 [来源冲突]` |

### 使用规则

1. **标注位置**: 紧跟在存疑数据后，用空格分隔
2. **附加说明**: 可在括号内补充具体原因
3. **多重标注**: 同一数据可有多个标注
4. **必须标注**: 有疑问就标注，不得省略

### 示例

```markdown
#### 🎯 波特五力分析数据

##### 🔵 行业竞争程度
| 维度 | 数据 |
|------|------|
| 市场集中度 | CR3 约65% [来源冲突] (来源A说65%，来源B说45%) |
| 竞争者数量 | 约50家 [待验证] (2023年数据) |
| 增长率 | [缺失] 未找到权威数据 |

#### 🏆 Top 3 产品深度分析

##### 第1名: ProductX

**👥 用户画像**
- 年龄段: 25-35岁 [推测] (基于评论分析)
- 性别比例: 6:4 男女 [?] (样本量较小)
- 月活用户: 500万/800万 [来源冲突]
```

### 下游处理建议

下游Agent在处理带标注的数据时应：
- `[?]` `[来源冲突]`: 需谨慎使用，建议进一步调研
- `[待验证]`: 可参考，但结论需注明不确定性
- `[推测]`: 仅作为参考，不作为决策依据
- `[缺失]`: 视为空值，需说明数据局限性

---

## Markdown 输出格式

### 单份报告格式（细分类别 ≤ 3）

```markdown
# 热词背景调研报告

---

## 📋 调研概要

| 项目 | 内容 |
|------|------|
| **调研ID** | TR-20250103-001 |
| **输入契约** | KW-20250103-001 |
| **调研时间** | 2025-01-03 15:30:00 |
| **关键词** | {keyword} |
| **细分类别数** | 3 |
| **调研产品数** | 9 (每类别Top 3) |

---

## 🔍 细分类别调研

---

### 细分类别 1: {segment_name}

**调研状态**: ✅ 完成 / ⚠️ 部分完成

#### 📖 背景信息

| 维度 | 内容 |
|------|------|
| **定义** | {definition} |
| **起源** | {origin} |
| **火起来的原因** | {popularity_reason} |

**相关事件/新闻**:
- {event_1}
- {event_2}

#### 🎯 波特五力分析数据

##### 🔴 供应商议价能力 (Supplier Power)

| 维度 | 数据 |
|------|------|
| **主要供应商** | {suppliers} |
| **集中度** | {concentration} |
| **切换成本** | {switching_cost} |
| **差异化程度** | {differentiation} |

##### 🟠 买方议价能力 (Buyer Power)

| 维度 | 数据 |
|------|------|
| **买方集中度** | {concentration} |
| **价格敏感度** | {sensitivity} |
| **切换成本** | {switching_cost} |
| **信息透明度** | {information} |

##### 🟡 新进入者威胁 (Threat of New Entrants)

| 维度 | 数据 |
|------|------|
| **近期新进入者** | {entrants} |
| **资金壁垒** | {capital} |
| **技术壁垒** | {tech} |
| **监管壁垒** | {regulatory} |

**近期新进入者详情**:
| 公司/产品 | 进入时间 | 融资情况 |
|-----------|----------|----------|
| {name} | {date} | {funding} |

##### 🟢 替代品威胁 (Threat of Substitutes)

| 维度 | 数据 |
|------|------|
| **主要替代品** | {substitutes} |
| **性价比对比** | {comparison} |
| **切换倾向** | {tendency} |

##### 🔵 行业竞争程度 (Industry Rivalry)

| 维度 | 数据 |
|------|------|
| **市场集中度** | {CR3/CR5} |
| **竞争者数量** | {count} |
| **增长率** | {growth} |
| **差异化程度** | {differentiation} |

#### 🏆 Top 3 产品深度分析

---

##### 🥇 第1名: {product_name}

**📊 基本信息**

| 项目 | 内容 |
|------|------|
| **市场份额** | {share} |
| **平台** | {platform} |
| **评分** | {rating} ⭐ ({rating_count} 评价) |
| **下载量** | {downloads} |
| **开发者** | {developer} |
| **官网** | [{url}]({url}) |

**👥 用户画像**

*人口统计特征*:
| 维度 | 数据 |
|------|------|
| 年龄段 | {age_range} |
| 性别比例 | {gender_ratio} |
| 地域分布 | {geography} |
| 收入水平 | {income_level} |
| 职业分布 | {occupation} |

*心理特征*:
- **兴趣爱好**: {interests}
- **价值观**: {values}
- **生活方式**: {lifestyle}

*痛点原文*:
> "{pain_point_1}"
> "{pain_point_2}"

*行为特征*:
| 维度 | 数据 |
|------|------|
| 使用频率 | {usage_frequency} |
| 使用场景 | {usage_scenarios} |
| 购买行为 | {purchase_behavior} |
| 品牌忠诚度 | {brand_loyalty} |

**⚡ 主要功能**

*核心功能*:
| 功能 | 描述 |
|------|------|
| {feature_1} | {description_1} |
| {feature_2} | {description_2} |

*独特功能*:
- {unique_feature_1}
- {unique_feature_2}

*定价策略*:
| 层级 | 价格 | 包含功能 |
|------|------|----------|
| 免费版 | $0 | {free_features} |
| 专业版 | ${price}/月 | {pro_features} |
| 企业版 | 定制 | {enterprise_features} |

*近期更新*:
| 时间 | 版本 | 更新内容 |
|------|------|----------|
| {date} | {version} | {changes} |

**📣 差异化营销**

| 维度 | 内容 |
|------|------|
| **市场定位** | {positioning} |
| **目标人群** | {target_segment} |
| **品牌Slogan** | "{slogan}" |

*独特卖点 (USP)*:
1. {usp_1}
2. {usp_2}
3. {usp_3}

*营销渠道*:
| 渠道 | 描述 | 效果 |
|------|------|------|
| {channel_1} | {description} | {effectiveness} |

*社交媒体表现*:
| 平台 | 粉丝数 | 互动情况 |
|------|--------|----------|
| {platform} | {followers} | {engagement} |

*与竞品差异*:
| 对比竞品 | 差异点 |
|----------|--------|
| {competitor_1} | {differences} |
| {competitor_2} | {differences} |

---

##### 🥈 第2名: {product_name}
[同上结构]

---

##### 🥉 第3名: {product_name}
[同上结构]

---

#### 📚 信息来源

| 类型 | 标题 | 可靠性 | 链接 |
|------|------|--------|------|
| {type} | {title} | ⭐⭐⭐ | [链接]({url}) |

---

{重复以上结构处理其他细分类别}

---

## 📊 调研汇总

### 覆盖情况

| 指标 | 数量 |
|------|------|
| 已调研细分类别 | {count} |
| 跳过的细分类别 | {count} |
| Top 3产品总数 | {count} |
| 波特五力完整度 | {percentage} |

### 波特五力覆盖情况

| 维度 | 覆盖程度 |
|------|----------|
| 供应商议价能力 | ✅ 完全 / ⚠️ 部分 / ❌ 缺失 |
| 买方议价能力 | ✅ 完全 / ⚠️ 部分 / ❌ 缺失 |
| 新进入者威胁 | ✅ 完全 / ⚠️ 部分 / ❌ 缺失 |
| 替代品威胁 | ✅ 完全 / ⚠️ 部分 / ❌ 缺失 |
| 行业竞争程度 | ✅ 完全 / ⚠️ 部分 / ❌ 缺失 |

### 数据质量说明

**数据新鲜度**: {freshness_description}

**覆盖范围说明**: {coverage_notes}

**调研限制**:
- {limitation_1}
- {limitation_2}

---

## ⚠️ 下游使用说明

本报告仅提供原始背景信息收集，**不包含商业分析和决策建议**。

下游Agent（business-opportunity-analyzer）应基于本报告进行：
1. **波特五力综合分析** - 基于收集的数据进行行业吸引力评估
2. **商业机会识别** - 从数据中发现市场空白和机会
3. **竞争格局分析** - 基于Top 3产品数据进行深度竞争分析
4. **市场进入策略建议** - 结合壁垒数据给出进入建议
5. **风险评估与应对** - 基于五力数据评估风险

---

*本报告由 Google 热词调研 Agent 生成*
*调研时间: {timestamp}*
*契约版本: 2.0.0*
```

### 拆分报告格式（细分类别 > 3）

每个细分类别单独一份报告：

```markdown
# 热词背景调研报告 - {细分类别名称}

---

## 📋 调研概要

| 项目 | 内容 |
|------|------|
| **调研ID** | TR-20250103-001-01 |
| **输入契约** | KW-20250103-001 |
| **细分类别** | {segment_name} |
| **报告序号** | 1 / {total} |
| **调研时间** | 2025-01-03 15:30:00 |

### 📂 关联报告

本关键词共拆分为 {n} 份报告：

| 序号 | 细分类别 | 报告ID | 文件名 |
|------|----------|--------|--------|
| 1 | {segment_1} | TR-xxx-01 | {filename_1} |
| 2 | {segment_2} | TR-xxx-02 | {filename_2} |
| ... | ... | ... | ... |

---

## 🎯 {细分类别} 深度调研

[波特五力分析数据 - 同单份报告格式]

[Top 3 产品深度分析 - 同单份报告格式]

[市场数据]

[信息来源]

---

*本报告为系列报告之一*
*系列: {关键词} 调研报告 ({序号}/{总数})*
*契约版本: 2.0.0*
```

---

## 质量标准

### 波特五力数据要求

| 维度 | 最低要求 | 完全覆盖要求 |
|------|----------|--------------|
| 供应商议价能力 | 识别≥3个供应商 | 集中度+切换成本+差异化 |
| 买方议价能力 | 价格敏感度数据 | 切换成本+信息透明度 |
| 新进入者威胁 | 识别近1年新进入者 | 3种壁垒数据 |
| 替代品威胁 | 列出≥2个替代方案 | 性价比+切换倾向 |
| 行业竞争程度 | 市场集中度数据 | CR3/CR5+增长率+差异化 |

### Top 3 产品调研要求

| 调研维度 | 最低要求 | 完全覆盖要求 |
|----------|----------|--------------|
| 用户画像 | 年龄+场景+痛点 | 人口+心理+行为全覆盖 |
| 主要功能 | 核心功能+定价 | 独特功能+更新历史 |
| 差异化营销 | 定位+USP | 渠道+社交+竞品差异 |

### 状态标注规则

| 状态 | 条件 |
|------|------|
| ✅ 完成 | 波特五力5个维度 + Top 3产品3维度全部完成 |
| ⚠️ 部分完成 | 有2个以上维度或产品分析不完整 |
| ❌ 失败 | 无法获取有效信息 |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-02 | 初始版本 |
| 1.1.0 | 2025-01-02 | 增加疑问标注规范；增加完整性要求 |
| 1.2.0 | 2025-01-03 | 增加追踪机制；明确Contract ID关联规则 |
| 2.0.0 | 2025-01-03 | **重大升级**：增加波特五力模型；Top 3产品深度分析；报告拆分机制 |
