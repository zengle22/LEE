---
name: google-keywords
description: Google 关键词搜索 - 发现热门搜索词和长尾关键词
arguments:
  - name: topic
    description: 要分析的主题、网站类型或 App 功能（如：健身App、电商网站、在线教育）
    required: false
---

# Google 关键词搜索

你正在使用 Google 关键词搜索工具，帮助发现与网站/App 功能相关的热门搜索词和长尾关键词。

## 参数

**topic**: $topic

---

## 执行流程

### 1. 如果 topic 为空

询问用户提供分析主题：

```
🔍 Google 关键词搜索工具

请告诉我您想分析的主题，例如：
- 网站/App 类型（如：健身App、电商网站）
- 产品功能（如：在线支付、视频会议）
- 行业领域（如：在线教育、跨境电商）

示例：/google-keywords 健身App
```

### 2. 如果 topic 有值

执行关键词搜索分析：

#### Step 1: 确认主题
- 从 topic 提取核心关键词种子
- 识别相关同义词和行业术语

#### Step 2: 调用 Agent 执行搜索
使用 `google-keyword-searcher` agent 进行：
1. Google 搜索自动补全分析
2. 相关搜索词提取
3. People Also Ask 问题收集
4. 长尾词扩展

#### Step 3: 输出结果
按照 `google-keyword-contract.md` 定义的标准格式输出：
- 10 个核心关键词
- 每个核心词的长尾词扩展（3-5个）

---

## 输出格式

严格遵循 `agents/google-keyword-contract.md` 中定义的 Contract 格式。

---

## 错误处理

- 如果 Google 访问受限，使用 WebSearch 工具作为备选
- 如果主题过于宽泛，引导用户细化
