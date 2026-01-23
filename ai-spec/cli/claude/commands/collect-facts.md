---
name: collect-facts
description: 事实采集 - 从搜索引擎采集原始市场信号数据（只采集不分析）
arguments:
  - name: keywords
    description: 产业方向、功能或产品关键词，多个关键词用逗号分隔（如：AI项目管理,智能任务分配）
    required: false
---

# 事实采集命令

你正在使用事实采集工具，从 Google/Bing 等主流搜索引擎采集市场正在频繁搜索的显性信号。

## 参数

**keywords**: $keywords

---

## 执行流程

### 1. 如果 keywords 为空

询问用户提供采集目标：

```
🔍 事实采集工具 (Fact Collector)

请提供要采集的产业方向、功能或产品关键词。

输入方式:
- 单个方向: AI项目管理
- 多个关键词: AI项目管理, 智能任务分配, 项目协作工具
- 英文关键词: AI project management, task automation

示例:
/collect-facts AI项目管理
/collect-facts 跑步App, 健身追踪, 运动社交
```

### 2. 如果 keywords 有值

执行事实采集：

#### Step 1: 解析关键词

- 按逗号分隔多个关键词
- 识别语言（中文/英文）
- 为每个关键词规划采集策略

#### Step 2: 调用 fact-collector Agent

使用 `fact-collector` agent 进行：

1. **Google 采集**
   - 搜索结果数量
   - 自动补全建议
   - 相关搜索词
   - People Also Ask
   - 广告数量
   - 新闻时效性

2. **Bing 采集**（补充）
   - 同上维度

3. **趋势信号采集**
   - 时间相关搜索
   - 地域相关搜索

4. **WebSearch 补充**
   - 文本搜索获取更多信号

#### Step 3: 输出结果

按照 `contracts/fact-collection-contract.md` 格式输出：

**文件**: `output/facts/{YYYY-MM-DD}_{主题}_keywords_raw.json`

---

## 输出说明

### 输出内容

| 字段 | 说明 |
|------|------|
| `keywords[]` | 采集到的关键词及其信号 |
| `search_volume` | 搜索量信号（结果数、广告数） |
| `growth_signal` | 增长趋势信号（时效性、新闻） |
| `regional_distribution` | 地域分布信号 |
| `time_trends` | 时间趋势信号 |
| `sources_log` | 完整的来源日志 |

### 下游使用

此 JSON 文件可供以下分析 Agent 使用：
- `google-trend-researcher` - 趋势深度调研
- `business-opportunity-analyzer` - 商业机会分析
- 其他需要原始市场数据的分析 Agent

---

## 重要原则

### 只采集，不分析

本命令**只负责采集原始事实数据**，不做任何分析或判断：

| 会记录 | 不会做 |
|--------|--------|
| 搜索结果数量 | 判断搜索量高低 |
| 广告数量 | 评估商业价值 |
| 时间信号 | 判断趋势走向 |
| 原始文本 | 总结或解读 |

分析工作交给下游 Agent 完成。

---

## 错误处理

| 情况 | 处理 |
|------|------|
| 关键词过于宽泛 | 自动扩展为多个具体关键词 |
| 搜索引擎不可用 | 切换到备用引擎，记录失败状态 |
| 部分采集失败 | 继续其他采集，输出部分结果 |

---

## 使用示例

```bash
# 采集单个产业方向
/collect-facts AI项目管理

# 采集多个关键词
/collect-facts 跑步App, 健身追踪, 运动数据

# 采集英文关键词
/collect-facts AI project management, task automation

# 混合语言采集
/collect-facts AI项目管理, AI project management
```
