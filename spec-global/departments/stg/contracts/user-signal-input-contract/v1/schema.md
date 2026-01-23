# 用户信号分析输入契约 (Input Contract)

> **契约版本**: 1.0.0
> **上游Agent**: google-keyword-searcher
> **本Agent**: user-signal-analyzer (用户信号分析Agent)
> **下游Agent**: business-opportunity-analyzer
> **用途**: 定义从关键词搜索结果中提取的原始数据格式，作为用户信号分析的输入

---

## 契约说明

本契约定义了 `keywords_raw.json` 的标准格式。该文件包含关键词搜索的原始信息，由关键词搜索Agent产出，供用户信号分析Agent解析和深度分析。

**核心目标**: 从搜索行为推断用户真实需求——"搜索这个词的人，试图解决什么问题？"

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: user-signal-input
contract_version: "1.0.0"
metadata:
  analysis_id: string           # 分析ID，格式：USI-YYYYMMDD-XXX
  source_domain: string         # 分析的目标领域
  generated_at: datetime        # 生成时间 ISO 8601
  data_source: string           # 数据来源（如：google-autocomplete, webSearch）

keywords_raw: KeywordRaw[]      # 原始关键词数据列表
search_context: SearchContext   # 搜索上下文信息
```

### KeywordRaw 对象

```yaml
KeywordRaw:
  keyword: string               # 关键词文本
  search_volume: SearchVolume   # 搜索量级估算
  intent_signals:               # 意图信号
    raw_intent_type: string     # 原始意图分类
    question_markers: string[]  # 问题标记词（如：怎么、为什么、如何）
    action_markers: string[]    # 动作标记词（如：下载、购买、注册）
    comparison_markers: string[] # 对比标记词（如：vs、哪个好、推荐）
  longtail_variants: string[]   # 长尾变体词列表
  related_queries: string[]     # 相关搜索查询
  source_type: SourceType       # 来源类型
```

### SearchVolume 对象

```yaml
SearchVolume:
  level: VolumeLevel            # 搜索量等级
  estimated_monthly: string     # 月搜索量估算（如：100-500）
  trend: Trend                  # 趋势方向
```

### SearchContext 对象

```yaml
SearchContext:
  market: string                # 目标市场（如：中国、全球）
  language: string              # 搜索语言
  device_hints: string[]        # 设备倾向提示
  time_sensitivity: boolean     # 是否具有时间敏感性
  seasonality: string           # 季节性特征
```

### 枚举定义

```yaml
VolumeLevel:
  - very_high   # 月搜索 > 10000
  - high        # 月搜索 1000-10000
  - medium      # 月搜索 100-1000
  - low         # 月搜索 10-100
  - very_low    # 月搜索 < 10

Trend:
  - rising      # 上升趋势
  - stable      # 稳定
  - declining   # 下降趋势
  - seasonal    # 季节性波动

SourceType:
  - autocomplete        # Google自动补全
  - related_search      # 相关搜索
  - people_also_ask     # 用户还在问
  - longtail_expansion  # 长尾词扩展
  - competitor_analysis # 竞品分析
```

---

## JSON 示例

```json
{
  "contract_type": "user-signal-input",
  "contract_version": "1.0.0",
  "metadata": {
    "analysis_id": "USI-20260104-001",
    "source_domain": "AI跑步教练",
    "generated_at": "2026-01-04T10:00:00Z",
    "data_source": "google-autocomplete + webSearch"
  },
  "keywords_raw": [
    {
      "keyword": "AI跑步教练哪个好",
      "search_volume": {
        "level": "high",
        "estimated_monthly": "1000-5000",
        "trend": "rising"
      },
      "intent_signals": {
        "raw_intent_type": "commercial",
        "question_markers": ["哪个好"],
        "action_markers": [],
        "comparison_markers": ["哪个好", "推荐"]
      },
      "longtail_variants": [
        "AI跑步教练app推荐2026",
        "免费AI跑步教练",
        "国内AI跑步教练"
      ],
      "related_queries": [
        "Keep AI教练怎么样",
        "咕咚AI配速好用吗"
      ],
      "source_type": "autocomplete"
    },
    {
      "keyword": "跑步膝怎么预防",
      "search_volume": {
        "level": "medium",
        "estimated_monthly": "500-1000",
        "trend": "stable"
      },
      "intent_signals": {
        "raw_intent_type": "informational",
        "question_markers": ["怎么", "预防"],
        "action_markers": [],
        "comparison_markers": []
      },
      "longtail_variants": [
        "跑步膝康复训练",
        "AI预防跑步伤害",
        "跑姿分析预防受伤"
      ],
      "related_queries": [
        "跑步膝多久能恢复",
        "跑步膝还能继续跑吗"
      ],
      "source_type": "people_also_ask"
    }
  ],
  "search_context": {
    "market": "中国",
    "language": "zh-CN",
    "device_hints": ["mobile", "app"],
    "time_sensitivity": true,
    "seasonality": "马拉松赛季前搜索量上升"
  }
}
```

---

## 意图信号标记词库

### 问题标记词 (Question Markers)

| 类型 | 标记词 | 信号含义 |
|------|--------|----------|
| 方法类 | 怎么、如何、怎样 | 寻求解决方案 |
| 原因类 | 为什么、为啥 | 寻求理解 |
| 选择类 | 哪个、哪种、什么 | 决策困难 |
| 程度类 | 多久、多少、多大 | 评估成本/效果 |

### 动作标记词 (Action Markers)

| 类型 | 标记词 | 信号含义 |
|------|--------|----------|
| 获取类 | 下载、安装、注册 | 准备使用 |
| 购买类 | 购买、订阅、价格 | 交易意图 |
| 学习类 | 教程、入门、学习 | 技能需求 |
| 评估类 | 测评、体验、试用 | 验证需求 |

### 对比标记词 (Comparison Markers)

| 类型 | 标记词 | 信号含义 |
|------|--------|----------|
| 直接对比 | vs、对比、和...比 | 明确对比意图 |
| 推荐类 | 推荐、最好、排行 | 寻求权威意见 |
| 评价类 | 好用吗、值得吗 | 需要决策支持 |

---

## 验证规则

1. **必填字段**: `analysis_id`, `source_domain`, `keywords_raw[]`
2. **关键词数量**: 至少1个，建议10-50个
3. **意图信号**: 每个关键词至少有一个意图标记
4. **来源标注**: 每个关键词必须标注source_type

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-04 | 初始版本 |
