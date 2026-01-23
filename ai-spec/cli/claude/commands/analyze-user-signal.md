---
name: analyze-user-signal
description: 用户信号分析 - 从关键词数据中挖掘用户画像、搜索意图和痛点强度
arguments:
  - name: input_file
    description: 输入文件路径（keywords_raw.json 或关键词分析报告），留空则自动查找
    required: false
---

# 用户信号分析

你正在使用用户信号分析工具，帮助从关键词搜索数据中挖掘用户洞察。

**核心问题**: 搜索这个词的人，试图解决什么问题？

## 参数

**input_file**: $input_file

---

## 执行流程

### 1. 如果 input_file 为空

自动查找输入文件:

1. 首先查找 `keywords_raw.json`
2. 如果不存在，查找 `output/keywords/` 目录下最新的分析报告

如果都找不到，询问用户:

```
用户信号分析工具

请提供输入数据:
- 方式一: 指定 keywords_raw.json 文件路径
- 方式二: 指定关键词分析报告路径
- 方式三: 描述要分析的领域，我将先进行关键词搜索

示例: /analyze-user-signal output/keywords/2026-01-03_跑步AI产品_关键词分析.md
```

### 2. 如果 input_file 有值

执行用户信号分析:

#### Step 1: 读取输入数据
- 读取指定文件
- 解析关键词数据
- 验证数据格式

#### Step 2: 调用 Agent 执行分析
使用 `user-signal-analyzer` agent 进行:
1. 用户画像推断（谁 + 场景）
2. 搜索意图分析（信息型/工具型/交易前型/导航型）
3. 痛点强度评估（频率/紧急性/失败成本）
4. 问题综合与机会识别

#### Step 3: 输出结果
按照 `contracts/user-signal-output-contract.md` 定义的标准格式输出:
- 用户画像假设（含置信度）
- 意图分布分析
- 痛点强度信号（三维度评分）
- 问题综合（核心问题 + JTBD）
- 下游交接信息

---

## 输出说明

### 输出位置
`output/user-signals/{YYYY-MM-DD}_{领域}_用户信号分析.md`

### 核心输出内容

| 模块 | 内容 | 用途 |
|------|------|------|
| 用户画像 | 谁 + 场景 + 置信度 | 定义目标用户 |
| 意图分析 | 四种意图类型分布 | 理解用户心态 |
| 痛点强度 | 频率/紧急性/失败成本评分 | 评估市场机会 |
| 问题综合 | 核心问题 + JTBD | 产品设计输入 |

### 下游使用

输出报告将作为以下Agent的输入:
- `business-opportunity-analyzer`: 商业机会分析
- `prd-designer`: 产品设计

---

## 错误处理

- 如果输入文件不存在，提示用户先运行 `/google-keywords` 生成关键词数据
- 如果数据格式不匹配，尝试兼容解析或提示格式要求
- 如果关键词数量过少（<5个），建议补充数据

---

## 使用示例

```bash
# 使用默认路径（自动查找）
/analyze-user-signal

# 指定 JSON 输入
/analyze-user-signal keywords_raw.json

# 指定 Markdown 报告
/analyze-user-signal output/keywords/2026-01-03_跑步AI产品_关键词分析.md
```

---

## 相关命令

- `/google-keywords {topic}` - 生成关键词数据（上游）
- `/analyze-opportunity` - 商业机会分析（下游）
