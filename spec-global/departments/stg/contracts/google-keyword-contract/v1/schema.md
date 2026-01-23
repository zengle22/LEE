# Google 关键词输入契约 (Input Contract)

> **契约版本**: 1.0.0
> **上游Agent**: google-keyword-searcher
> **下游Agent**: google-trend-researcher
> **用途**: 定义从关键词搜索Agent传递给热词调研Agent的数据格式

---

## 契约说明

本契约定义了关键词搜索结果的标准格式，作为热词背景调研Agent的输入源。上游Agent（google-keyword-searcher）生成符合此格式的报告，下游Agent（google-trend-researcher）按此格式解析输入。

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: google-keyword-input
contract_version: "1.0.0"
metadata:
  analysis_id: string        # 分析ID，格式：KW-YYYYMMDD-XXX
  source_domain: string      # 分析的目标领域
  generated_at: datetime     # 生成时间 ISO 8601
  keyword_count: number      # 关键词总数

keywords: Keyword[]          # 关键词列表
categories: Category[]       # 分类汇总
```

### Keyword 对象

```yaml
Keyword:
  id: number                 # 序号 1-N
  keyword: string            # 关键词文本
  intent_type: IntentType    # 搜索意图类型
  heat_level: HeatLevel      # 热度等级
  competition: Competition   # 竞争程度
  longtail_keywords: string[] # 长尾词列表
```

### 枚举定义

```yaml
IntentType:
  - informational    # 信息型：用户想了解某个话题
  - navigational     # 导航型：用户想找到特定网站
  - transactional    # 交易型：用户有购买或使用意图
  - commercial       # 商业调研型：用户在比较选择

HeatLevel:
  - very_high   # 5星 - 极高热度
  - high        # 4星 - 高热度
  - medium      # 3星 - 中等热度
  - low         # 2星 - 较低热度
  - very_low    # 1星 - 低热度

Competition:
  - high        # 高竞争
  - medium      # 中等竞争
  - low         # 低竞争
```

### Category 对象

```yaml
Category:
  type: IntentType           # 分类类型
  keywords: string[]         # 该类别下的关键词列表
  recommended_usage: string  # 推荐用途说明
```

---

## Markdown 格式示例

上游Agent输出的Markdown报告应符合以下结构，以便下游解析：

```markdown
# Google 关键词分析报告

---

## 📋 分析概要

| 项目 | 内容 |
|------|------|
| **分析ID** | KW-20250102-001 |
| **目标领域** | 健身App |
| **分析时间** | 2025-01-02 14:30:00 |
| **核心关键词数** | 10 |
| **长尾词总数** | 30 |

---

## 🎯 核心关键词（Top 10）

| 序号 | 关键词 | 搜索意图 | 热度评估 | 竞争度 |
|------|--------|----------|----------|--------|
| 1 | 健身App | 交易型 | ⭐⭐⭐⭐⭐ | 高 |
| 2 | 居家健身 | 信息型 | ⭐⭐⭐⭐ | 中 |
| 3 | 健身计划 | 信息型 | ⭐⭐⭐⭐ | 中 |

---

## 🌿 长尾关键词扩展

### 1. 健身App

| 长尾词 | 类型 | 搜索意图 |
|--------|------|----------|
| 健身App推荐2024 | 评测 | 商业调研型 |
| 免费健身App | 功能 | 交易型 |
| 健身App哪个好 | 问题 | 商业调研型 |

---

## 📊 关键词分类汇总

### 🔵 信息型关键词
> 适合：博客文章、知识库、FAQ

- 居家健身
- 健身计划
- 健身入门

### 🔴 交易型关键词
> 适合：产品页、落地页、转化页

- 健身App
- 健身App下载

---

*本报告由 Google 关键词搜索 Agent 生成*
```

---

## 解析规则

下游Agent应按以下规则解析输入：

### 1. 提取分析概要
- 从"分析概要"表格中提取 `analysis_id`、`source_domain`、`generated_at`

### 2. 提取核心关键词
- 从"核心关键词"表格的每一行提取：
  - 序号 → `id`
  - 关键词 → `keyword`
  - 搜索意图 → `intent_type`（需映射中文到枚举值）
  - 热度评估 → `heat_level`（星星数量）
  - 竞争度 → `competition`

### 3. 提取长尾词
- 遍历"长尾关键词扩展"下的每个子标题
- 将标题作为核心关键词，表格内容作为其 `longtail_keywords`

### 4. 提取分类
- 解析"关键词分类汇总"下的各分类
- 将emoji后的标题映射到 `intent_type`
- 提取列表项作为 `keywords`

---

## 意图类型映射

| Markdown中的文本 | 枚举值 |
|-----------------|--------|
| 信息型 | informational |
| 导航型 | navigational |
| 交易型 | transactional |
| 商业调研型 | commercial |

---

## 验证规则

输入数据应满足以下验证规则：

1. **必填字段**: `analysis_id`, `source_domain`, `keywords[]`
2. **关键词数量**: 至少1个，建议5-15个
3. **长尾词**: 每个核心关键词至少有1个长尾词
4. **格式一致性**: 热度使用统一的星星符号

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-02 | 初始版本 |
