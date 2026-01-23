---
name: analyze-opportunity
description: 基于热词调研报告分析商业机会，评估小团队切入可行性，输出供产品设计使用的契约文档
arguments:
  - name: report_path
    description: 热词调研报告文件路径（可选，不填则自动查找根目录下的调研报告）
    required: false
---

# 商业机会分析

你正在帮助用户基于热词调研报告分析商业机会，评估小团队（1-10人）能否切入该领域。

## 契约驱动流程

本命令遵循契约驱动的 Agent 协作模式：

```
输入契约: contracts/trend-research-contract.md
    ↓
分析处理: business-opportunity-analyzer Agent
    ↓
输出契约: contracts/business-opportunity-contract.md
    ↓
下游使用: prd-designer Agent (产品设计)
```

## 输入处理

{{#if report_path}}
用户指定的调研报告路径：**{{report_path}}**

请读取该文件，验证是否符合 `trend-research-contract` 格式，然后开始分析。
{{else}}
用户未指定报告路径，请在项目根目录查找热词调研报告文件。

**查找规则**:
1. 文件名包含 `TR-` 或 `trend-research` 或 `调研报告`
2. 文件格式为 `.md`
3. 内容符合 `contracts/trend-research-contract.md` 定义的格式

如果找到多个文件，列出供用户选择。
如果未找到文件，询问用户：
- 提供调研报告文件路径
- 或提供热词关键词，从头开始在线调研
{{/if}}

## 分析任务

使用 business-opportunity-analyzer Agent 执行以下分析：

### 1. 解析输入契约
- 读取调研报告中的背景信息、趋势数据、用户画像、市场数据、产品调研
- 验证数据完整性，标注缺失项

### 2. 市场分析
- 整合市场规模数据
- 判断市场所处阶段（萌芽/成长/成熟/衰退）
- 识别可切入的细分市场

### 3. 竞争格局分析
- 分析头部玩家的优劣势
- 评估市场集中度
- 识别市场空白点

### 4. 机会评估（量化打分）
- 市场空白度 (0-100)
- 进入门槛 (0-100，越高越容易)
- 差异化潜力 (0-100)
- 小团队适配度 (0-100)

### 5. 策略建议
- 综合评级 (A/B/C/D)
- 推荐定位和差异化方向
- MVP 功能范围和资源估算
- 初期获客策略

### 6. 待确认事项
**重要**: 将分析过程中的不确定项输出到"待确认事项"模块，等待人工确认：
- 数据验证需求
- 策略选择决策
- 假设前提确认
- 风险评估确认

### 7. 下游交接
为 prd-designer Agent 准备：
- 产品目标建议
- 用户画像输入
- 价值主张提示
- 差异化功能建议
- 核心竞争力建议

## 输出要求

- **格式**: 严格遵循 `contracts/business-opportunity-contract.md` 定义
- **位置**: 项目根目录
- **命名**: `{keyword}-opportunity-BO-YYYYMMDD-XXX.md`
- **待确认**: 必须包含待确认事项模块（如无则写"无待确认事项"）

## 使用示例

```bash
# 自动查找调研报告并分析
/analyze-opportunity

# 指定调研报告路径
/analyze-opportunity ./AI写作助手-TR-20250102-001.md

# 如果没有调研报告，会询问是否从头调研
```
