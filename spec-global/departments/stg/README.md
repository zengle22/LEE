# 战略部门 (stg)

> Strategy Department

## 部门职责

负责商业机会分析、市场研究、供应链分析、行业洞察和趋势研究

### 主要职责

- 市场机会识别与评估
- 商业洞察生成
- 供应链分析
- 行业趋势研究
- 竞争分析

## 目录结构

```
{dept_id}/
├── workflows/      # 部门工作流
├── gates/          # 部门门禁
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

## 工作流 (workflows)

| 工作流 | 说明 | 输入 | 输出 |
|--------|------|------|------|
| market_research.yaml | 市场研究工作流 | 市场研究需求 | 市场研究报告 |
| opportunity_analysis.yaml | 机会分析工作流 | 业务机会 | 机会评估报告 |
| supply_analysis.yaml | 供应链分析工作流 | 供应链数据 | 供应链分析报告 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| business_value_check.yaml | 商业价值检查 | 提交 PRD 前 |
| market_fit_gate.yaml | 市场契合度检查 | 产品发布前 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| business-opportunity-analyzer.yaml | 商业机会分析 | 识别和分析商业机会 |
| supply-analyzer.yaml | 供应链分析 | 分析供应链结构和成本 |
| google-keyword-searcher.yaml | 关键词搜索 | 搜索市场关键词数据 |
| google-trend-analyzer.yaml | 趋势分析 | 分析市场趋势 |
| industry-structure-analyzer.yaml | 行业结构分析 | 分析行业结构和竞争格局 |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| market-analysis.yaml | 市场分析技能 |
| competitive-intelligence.yaml | 竞争情报技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| business-opportunity-contract.yaml | 商业机会契约 |
| supply-analysis-contract.yaml | 供应链分析契约 |
| market-insight-contract.yaml | 市场洞察契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| prd | stg-prd 业务需求契约 | 市场到产品 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
