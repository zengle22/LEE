---
name: build-opportunity
description: 基于冻结后的合同文件构建商业机会假设，输出可交给产品团队验证的 Opportunity Handoff 文档
arguments:
  - name: contract_path
    description: 已冻结的契约文件路径（必填）
    required: true
---

# 商业机会构建

## 唯一目标

**构建一个可交给产品部门验证的机会假设。**

不是做决策，不是给评分，而是构建一个清晰的假设，让产品团队可以去验证。

## 契约驱动流程

```
输入契约: 用户指定的已冻结契约文件
    ↓
分析处理: business-opportunity-builder Agent
    ↓
输出: {keyword}-opportunity-{YYYYMMDD}.md
    ↓
下游使用: 产品团队设计验证实验
```

## 输入处理

用户指定的契约文件路径：**{{contract_path}}**

请执行以下步骤：

1. **读取契约文件**
   - 验证文件存在且可读
   - 确认契约状态为"已确认"或"已冻结"（如有状态字段）

2. **提取关键约束**
   - 范围约束：功能边界、明确排除项
   - 技术约束：技术栈限制、性能要求
   - 资源约束：时间、人力、资金限制
   - 市场约束：竞争格局、用户规模
   - 合规约束：法规要求、资质限制

3. **补充信息搜索**（如契约信息不全）
   - 使用 WebSearch 补充市场数据和时机论据
   - 使用 WebFetch 获取竞品详情

---

## Part 1: Business Opportunity（机会假设定义）

使用 business-opportunity-builder Agent 构建以下内容：

### 1. One-liner
- 一句话机会定义（不超过30字）
- 格式：[用户] 需要 [解决方案] 来 [获得价值]

### 2. Target User & Scenario
- **谁**: 用户画像（1-2句话）
- **在什么情境下**: 触发时刻 + 正在做什么 + 遇到什么问题

### 3. Why Now
- 必须回答"为什么是现在，而不是一年前或一年后"
- 可能角度：技术成熟度、市场窗口、用户行为、成本结构
- 每个论据必须有具体证据支撑

### 4. Differentiation Hypothesis
- **假设**: 如果我们 [做什么不同的事]，[目标用户] 会 [产生什么行为/获得什么价值]
- **验证方式**: 如何知道假设是对的
- **证伪信号**: 什么情况说明假设错了

### 5. Reasons NOT to Do
- **风险**: 可能导致失败的外部因素（概率 + 影响）
- **不确定性**: 我们不知道答案的关键问题
- **替代路径**: 如果不做这个，还可以做什么

### 6. Product Validation Suggestion
- **验证目标**: 一句话说明要验证什么
- **建议方法**: 具体的验证方式
- **成功信号**: 什么情况说明值得继续
- **失败信号**: 什么情况说明应该放弃
- **预计成本**: 时间 + 资源

---

## Part 2: Opportunity Handoff（产品团队交付文档）

### What we believe（冻结结论）
- 列出已确认的、不需要再讨论的结论
- 产品团队可以直接基于这些结论行动

### What we don't know（明确未知）
- 列出关键未知项，需要产品团队去验证
- 每个未知项标注优先级（P0/P1/P2）和建议验证方式

### What NOT to build yet（防止过早实现）
- 🚫 **不要做**: 在假设验证前不应该构建的事项
- ⏸️ **暂缓**: 等某些条件满足后再考虑的事项

### Suggested Experiments（建议实验）
列出3-5个可快速执行的验证实验：
- **Landing Page**: 测试用户兴趣和转化意愿
- **User Interview**: 深入理解用户痛点和需求
- **Fake Door Test**: 测试用户对特定功能的需求
- **Prototype Test**: 用原型验证交互假设
- **Competitor Analysis**: 验证市场空白点

每个实验需包含：类型、目的、做法、成功标准、预计成本

---

## 输出要求

- **格式**: 严格遵循 Business Opportunity + Opportunity Handoff 双部分结构
- **位置**: 项目根目录
- **命名**: `{keyword}-opportunity-{YYYYMMDD}.md`
- **契约版本**: 2.0.0

---

## 使用示例

```bash
# 基于需求契约构建商业机会假设
/build-opportunity ./contracts/xxx-requirement-contract.md

# 基于热词调研契约构建
/build-opportunity ./output/trend-research/xxx-TR-20260103.md

# 基于商业机会分析契约构建
/build-opportunity ./xxx-opportunity-BO-20260103-001.md
```

---

## 核心原则

| 原则 | 说明 |
|------|------|
| 假设优于结论 | 我们的工作是构建假设，不是下结论 |
| 边界清晰 | 明确区分"已知"和"未知" |
| 防止过早实现 | 在验证前不要让产品团队开始构建 |
| 实验导向 | 每个输出都应该指向一个可执行的验证实验 |
| 约束驱动 | 所有分析必须基于契约中的实际约束 |
