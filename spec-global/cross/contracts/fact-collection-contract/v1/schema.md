# 事实采集输出契约 (Fact Collection Contract)

> **契约版本**: 1.1.0
> **上游Agent**: fact-collector
> **下游Agent**: 分析类 Agent（trend-analyzer, opportunity-analyzer 等）
> **用途**: 定义从搜索引擎采集的原始市场信号数据格式

---

## 契约说明

本契约定义了事实采集 Agent 的标准输出格式。该 Agent **只负责采集原始事实数据**，不做任何分析或判断。输出的 JSON 文件供下游分析 Agent 使用。

### 设计原则

| 原则 | 说明 |
|------|------|
| **纯事实** | 只记录搜索引擎返回的原始数据 |
| **可追溯** | 每条数据都有来源链接 |
| **不分析** | 不做趋势判断、不做机会评估 |
| **不合并** | 相似关键词保持独立，不合并去重 |
| **结构化** | 扁平结构，便于下游程序化处理 |

---

## 🚨 禁止行为（采集边界）

本契约明确禁止以下行为，采集 Agent 必须严格遵守：

| 禁止行为 | 说明 |
|---------|------|
| **禁止判断用户画像** | 不推测"谁在搜索"、"目标用户是谁" |
| **禁止分析商业价值** | 不评估"值不值得做"、"市场机会大小" |
| **禁止合并相似关键词** | "AI项目管理"和"AI项目管理工具"必须分开记录 |
| **禁止趋势解读** | 只记录原始信号，不判断"上升"还是"下降" |
| **禁止给出建议** | 不输出任何"建议"、"推荐"、"应该"类内容 |

---

## 输出文件定义

### 文件位置与命名

```
output/facts/{YYYY-MM-DD}_{主题}_keywords_raw.json
```

### 顶层结构

```json
{
  "contract_type": "fact-collection",
  "contract_version": "1.1.0",
  "metadata": {
    "collection_id": "FC-YYYYMMDD-XXX",
    "input_keywords": ["关键词1", "关键词2"],
    "collected_at": "2026-01-04T10:30:00Z",
    "sources": ["google", "bing"],
    "total_keywords_found": 50
  },
  "keywords": [],
  "sources_log": []
}
```

---

## 核心数据结构

### Keyword 对象（核心）

每个采集到的关键词使用以下扁平结构：

```typescript
interface Keyword {
  keyword: string;           // 关键词文本（原样记录，不合并不修改）
  trend: "up" | "flat" | "down" | "unknown";  // 趋势信号（基于原始数据推断）
  volume_range: string;      // 搜索量区间（如 "1M-10M", "100K-1M", "unknown"）
  geo: string[];             // 地域分布信号（如 ["中国", "美国"]）
  time_window: string;       // 时间窗口/时效性（如 "2024", "近7天", "unknown"）
  source_links: string[];    // 来源链接列表
}
```

### 字段说明

#### `keyword`
- **原样记录**：搜索引擎返回什么就记录什么
- **不合并**：即使"AI项目管理"和"ai项目管理"很相似，也分开记录
- **不修改**：不纠正拼写、不标准化格式

#### `trend`
基于原始信号判断，规则如下：

| 值 | 判断依据（原始信号） |
|----|--------------------|
| `up` | 自动补全含"2024/2025/最新"、有新闻板块、新闻时间<24小时 |
| `down` | 自动补全含"替代品/过时"、无近期新闻 |
| `flat` | 有稳定搜索量但无明显时效性信号 |
| `unknown` | 信号不足或无法判断 |

**注意**：这是基于原始信号的**机械推断**，不是主观分析。

#### `volume_range`
基于搜索结果数量推断的区间：

| 区间 | 对应搜索结果数 |
|------|---------------|
| `10M+` | ≥ 10,000,000 |
| `1M-10M` | 1,000,000 - 9,999,999 |
| `100K-1M` | 100,000 - 999,999 |
| `10K-100K` | 10,000 - 99,999 |
| `<10K` | < 10,000 |
| `unknown` | 无法获取 |

#### `geo`
从以下信号提取地域：
- 搜索建议中的地区词（如"国内"、"美国"）
- 新闻来源的地域
- 自动补全中的地区关键词

#### `time_window`
从以下信号提取时间窗口：
- 自动补全中的年份（如"2024"）
- 新闻时效性（如"3小时前"）
- 时间相关搜索词（如"最新"）

#### `source_links`
- 记录所有产生此关键词数据的搜索 URL
- 至少包含 1 个有效链接

---

## JSON 完整示例

```json
{
  "contract_type": "fact-collection",
  "contract_version": "1.1.0",
  "metadata": {
    "collection_id": "FC-20260104-001",
    "input_keywords": ["AI项目管理"],
    "collected_at": "2026-01-04T10:30:00Z",
    "sources": ["google", "bing"],
    "total_keywords_found": 8
  },
  "keywords": [
    {
      "keyword": "AI项目管理工具",
      "trend": "up",
      "volume_range": "1M-10M",
      "geo": ["中国", "美国"],
      "time_window": "2024",
      "source_links": [
        "https://www.google.com/search?q=AI项目管理工具"
      ]
    },
    {
      "keyword": "AI项目管理软件",
      "trend": "up",
      "volume_range": "1M-10M",
      "geo": ["中国"],
      "time_window": "2024",
      "source_links": [
        "https://www.google.com/search?q=AI项目管理软件"
      ]
    },
    {
      "keyword": "ai项目管理",
      "trend": "flat",
      "volume_range": "100K-1M",
      "geo": [],
      "time_window": "unknown",
      "source_links": [
        "https://www.bing.com/search?q=ai项目管理"
      ]
    },
    {
      "keyword": "AI project management tool",
      "trend": "up",
      "volume_range": "10M+",
      "geo": ["USA", "UK"],
      "time_window": "2024",
      "source_links": [
        "https://www.google.com/search?q=AI+project+management+tool"
      ]
    },
    {
      "keyword": "智能项目管理",
      "trend": "unknown",
      "volume_range": "100K-1M",
      "geo": ["中国"],
      "time_window": "unknown",
      "source_links": [
        "https://www.google.com/search?q=智能项目管理"
      ]
    },
    {
      "keyword": "项目管理AI助手",
      "trend": "up",
      "volume_range": "10K-100K",
      "geo": [],
      "time_window": "2024-2025",
      "source_links": [
        "https://www.google.com/search?q=项目管理AI助手"
      ]
    },
    {
      "keyword": "AI项目管理工具推荐",
      "trend": "up",
      "volume_range": "100K-1M",
      "geo": ["中国"],
      "time_window": "2024",
      "source_links": [
        "https://www.google.com/search?q=AI项目管理工具推荐"
      ]
    },
    {
      "keyword": "免费AI项目管理",
      "trend": "up",
      "volume_range": "10K-100K",
      "geo": [],
      "time_window": "2024",
      "source_links": [
        "https://www.google.com/search?q=免费AI项目管理"
      ]
    }
  ],
  "sources_log": [
    {
      "url": "https://www.google.com/search?q=AI项目管理",
      "search_engine": "google",
      "query": "AI项目管理",
      "timestamp": "2026-01-04T10:31:00Z",
      "status": "success"
    },
    {
      "url": "https://www.bing.com/search?q=AI项目管理",
      "search_engine": "bing",
      "query": "AI项目管理",
      "timestamp": "2026-01-04T10:32:00Z",
      "status": "success"
    }
  ]
}
```

---

## SourceLog 来源日志

```typescript
interface SourceLog {
  url: string;                              // 访问的完整 URL
  search_engine: "google" | "bing";         // 搜索引擎
  query: string;                            // 搜索词
  timestamp: string;                        // 访问时间 ISO 8601
  status: "success" | "failed" | "partial"; // 状态
  error_message?: string;                   // 错误信息（如有）
}
```

---

## 验证规则

| 规则 | 要求 |
|------|------|
| `metadata` | 必填，包含 collection_id 和 collected_at |
| `keywords[]` | 必填，至少 1 个 |
| `keyword.keyword` | 非空字符串 |
| `keyword.trend` | 必须是 up/flat/down/unknown 之一 |
| `keyword.source_links` | 至少 1 个有效 URL |
| `sources_log[]` | 每次搜索都需记录 |

---

## 下游使用说明

### 解析方式

下游 Agent 直接遍历 `keywords[]` 数组，每个元素都是独立的关键词记录：

```python
for kw in data["keywords"]:
    print(f"关键词: {kw['keyword']}")
    print(f"趋势: {kw['trend']}")
    print(f"搜索量: {kw['volume_range']}")
    print(f"地域: {kw['geo']}")
```

### 与其他契约的关系

```
┌─────────────────────────────────────┐
│         fact-collection             │
│       (keywords_raw.json)           │
│   纯事实数据 - 不分析不判断          │
└──────────────────┬──────────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│ 关键词   │  │ 趋势     │  │ 商业机会  │
│ 分析     │  │ 调研     │  │ 分析     │
└─────────┘  └──────────┘  └──────────┘
   分析        分析          分析
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-04 | 初始版本 |
| 1.1.0 | 2026-01-04 | 简化 Keyword 结构，增加禁止行为约束 |
