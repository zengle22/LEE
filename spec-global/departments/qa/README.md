# 测试部门 (qa)

> QA Department

## 部门职责

负责测试用例设计、测试执行、Bug 分析和测试报告编写

### 主要职责

- 测试用例设计
- 测试执行
- Bug 分析和分类
- 测试报告编写
- 自动化测试

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
| test_case_design.yaml | 测试用例设计工作流 | 需求/设计 | 测试用例 |
| test_execution.yaml | 测试执行工作流 | 测试用例 | 测试结果 |
| bug_triage.yaml | Bug 分析工作流 | Bug 报告 | Bug 分类 |
| test_report.yaml | 测试报告工作流 | 测试数据 | 测试报告 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| test_pass_rate_gate.yaml | 测试通过率门禁 | 发布前 |
| critical_bugs_gate.yaml | 关键 Bug 门禁 | 发布前 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| test-case-creator.yaml | 测试用例设计师 | 设计测试用例 |
| test-executor.yaml | 测试执行员 | 执行测试 |
| bug-analyzer.yaml | Bug 分析师 | 分析和分类 Bug |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| test-strategy.yaml | 测试策略技能 |
| automation.yaml | 自动化测试技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| test_plan_contract.yaml | 测试计划契约 |
| bug_report_contract.yaml | Bug 报告契约 |
| test_report_contract.yaml | 测试报告契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| dev | dev-qa 测试输入契约 | 开发到测试 E2E 工作流 |
| ops | qa-ops 发布就绪契约 | 测试到运维 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
