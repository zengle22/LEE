# 竞品供给分析输出契约 (Output Contract)

> **契约版本**: 1.1.0
> **上游Agent**: google-keyword-searcher
> **本Agent**: supply-analyzer (竞品供给分析Agent)
> **下游Agent**: business-opportunity-analyzer (商业机会分析Agent)
> **用途**: 分析市场现有解决方案，回答"已有解决方案哪里不够好"

---

## 契约说明

本契约定义了竞品供给分析的输出格式，聚焦于一个核心问题：

> **已有解决方案哪里不够好？**

**职责边界**:
- **上游Agent职责**: 收集关键词、长尾词、竞品信息等原始数据
- **本Agent职责**: 分类现有方案，识别明显不足
- **下游Agent职责**: 基于供给分析进行商业机会评估

---

## 数据结构定义

### 顶层结构

```yaml
contract_type: supply-analysis-output
contract_version: "1.1.0"
metadata:
  analysis_id: string           # 分析ID，格式：SA-YYYYMMDD-XXX
  source_contract: string       # 输入契约ID
  generated_at: datetime        # 生成时间 ISO 8601
  keyword: string               # 分析的核心关键词/领域

existing_solutions: ExistingSolutions   # 现有解决方案分类
gaps: Gaps                              # 明显不足/空白
pending_confirmation: PendingConfirmation[]  # 待确认事项
```

### ExistingSolutions 对象

```yaml
ExistingSolutions:
  summary: string                       # 一句话总结供给现状
  total_count: number                   # 发现的解决方案总数

  categories:                           # 按类别分类的解决方案
    - category_name: string             # 类别名称 (如: 独立App、SaaS工具、开源方案)
      solutions:                        # 该类别下的解决方案
        - name: string                  # 产品名称
          description: string           # 简要描述
          pricing: string               # 定价模式
          strengths: string[]           # 优势
          weaknesses: string[]          # 不足
```

### Gaps 对象

```yaml
Gaps:
  unserved_segments:                    # 未被服务的细分市场
    - segment: string                   # 细分描述
      evidence: string                  # 证据（关键词信号/用户反馈）
      opportunity: string               # 机会说明

  poor_ux:                              # 用户体验差的领域
    - issue: string                     # 问题描述
      affected_solutions: string[]      # 受影响的产品
      user_complaints: string[]         # 用户抱怨

  high_cost:                            # 成本过高的问题
    - issue: string                     # 问题描述
      current_pricing: string           # 当前定价情况
      underserved_users: string         # 被排斥的用户群

  poor_integration:                     # 集成/兼容性差
    - issue: string                     # 问题描述
      missing_integrations: string[]    # 缺失的集成
      user_impact: string               # 对用户的影响

  other_gaps:                           # 其他明显不足
    - issue: string                     # 问题描述
      details: string                   # 详细说明
```

### PendingConfirmation 对象

```yaml
PendingConfirmation:
  id: string                            # PC-001
  question: string                      # 问题描述
  impact: string                        # 对结论的影响
  priority: critical | important | nice_to_have
```

---

## Markdown 输出格式

```markdown
# 竞品供给分析报告

---

## 📋 分析概要

| 项目 | 内容 |
|------|------|
| **分析ID** | SA-YYYYMMDD-XXX |
| **分析领域** | {keyword} |
| **分析时间** | YYYY-MM-DD HH:MM |
| **发现方案数** | {total_count} |

**供给现状**: {summary}

---

## Existing Solutions

### Category A: {category_name}

| 产品 | 描述 | 定价 | 优势 | 不足 |
|------|------|------|------|------|
| {name} | {description} | {pricing} | {strengths} | {weaknesses} |

### Category B: {category_name}

| 产品 | 描述 | 定价 | 优势 | 不足 |
|------|------|------|------|------|
| {name} | {description} | {pricing} | {strengths} | {weaknesses} |

### Category C: {category_name}

...

---

## Gaps

### Unserved Segment (被忽视的细分)

| 细分市场 | 证据 | 机会 |
|----------|------|------|
| {segment} | {evidence} | {opportunity} |

### Poor UX (用户体验差)

| 问题 | 受影响产品 | 用户抱怨 |
|------|------------|----------|
| {issue} | {solutions} | {complaints} |

### High Cost (成本过高)

| 问题 | 当前定价 | 被排斥用户 |
|------|----------|------------|
| {issue} | {pricing} | {users} |

### Poor Integration (集成差)

| 问题 | 缺失集成 | 用户影响 |
|------|----------|----------|
| {issue} | {integrations} | {impact} |

### Other Gaps (其他不足)

| 问题 | 详细说明 |
|------|----------|
| {issue} | {details} |

---

## ❓ 待确认事项

| ID | 问题 | 优先级 | 影响 |
|----|------|--------|------|
| PC-001 | {question} | {priority} | {impact} |

---

*本报告由竞品供给分析 Agent 生成*
*契约版本: 1.1.0*
```

---

## 分析指南

### 核心任务

回答一个问题：**已有解决方案哪里不够好？**

### 分类方法 (Existing Solutions)

按以下维度自由分类，选择最能体现市场格局的分类方式：

- **按产品形态**: 独立App / SaaS平台 / 开源工具 / API服务 / 硬件设备
- **按定价模式**: 免费 / Freemium / 订阅制 / 一次性付费
- **按目标用户**: 个人用户 / 小团队 / 企业级
- **按技术路线**: 传统方案 / AI驱动 / 大模型方案

### Gap识别方法

| Gap类型 | 识别方法 |
|---------|----------|
| **Unserved Segment** | 长尾词搜索量高但无专门产品；特定人群抱怨无合适工具 |
| **Poor UX** | 应用商店差评；社交媒体吐槽；上手难、流程繁琐 |
| **High Cost** | 价格带空白；用户反馈"太贵了"；学生/个人无法负担 |
| **Poor Integration** | 与主流工具不兼容；数据迁移困难；API缺失 |
| **Other Gaps** | 功能缺失；本地化不足；性能问题；隐私顾虑 |

### 小团队视角

分析时始终考虑：这个Gap是否适合小团队（1-10人）切入？

---

## 验证规则

1. **必填**: `analysis_id`, `keyword`, `existing_solutions`, `gaps`
2. **分类**: 至少包含2个解决方案分类
3. **Gap**: 至少识别1种类型的Gap
4. **待确认**: 如有不确定项，必须填写

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-04 | 初始版本 |
| 1.1.0 | 2026-01-04 | 简化结构，聚焦于"Existing Solutions + Gaps"两大模块 |
