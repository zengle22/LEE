# 产品部门 (prd)

> Product Department

## 部门职责

负责产品需求文档（PRD）编写、需求评审和产品目标定义

### 主要职责

- 需求收集与整理
- PRD 编写和维护
- 需求评审
- 产品目标定义
- 用户故事管理

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
| requirement_intake.yaml | 需求录入工作流 | 用户需求 | 需求文档 |
| prd_writing.yaml | PRD 编写工作流 | 需求文档 | PRD |
| requirement_review.yaml | 需求评审工作流 | PRD 草稿 | 评审报告 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| prd_quality_gate.yaml | PRD 质量门禁 | 提交开发前 |
| requirement_completeness_gate.yaml | 需求完整性门禁 | 需求评审前 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| prd-writer.yaml | PRD 编写 | 编写产品需求文档 |
| requirement-reviewer.yaml | 需求评审 | 评审需求文档 |
| product-goal-analyzer.yaml | 产品目标分析 | 分析并定义产品目标 |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| product-planning.yaml | 产品规划技能 |
| requirement-analysis.yaml | 需求分析技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| prd_contract.yaml | PRD 契约 |
| user-story-contract.yaml | 用户故事契约 |
| product-goal-contract.yaml | 产品目标契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| stg | stg-prd 业务需求契约 | 市场到产品 E2E 工作流 |
| ui | prd-ui 设计需求契约 | 产品到设计 E2E 工作流 |
| dev | prd-dev 需求包契约 | 产品到开发 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
