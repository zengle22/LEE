# 开发部门 (dev)

> Development Department

## 部门职责

负责架构设计、代码实现、代码审查和技术文档编写

### 主要职责

- 架构设计
- 代码实现
- 代码审查
- 技术文档编写
- 单元测试

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
| architecture_design.yaml | 架构设计工作流 | PRD | 架构文档 |
| code_implementation.yaml | 代码实现工作流 | 架构文档 | 源代码 |
| code_review.yaml | 代码审查工作流 | 代码 PR | 审查报告 |
| self_testing.yaml | 自测工作流 | 代码 | 测试结果 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| code_quality_gate.yaml | 代码质量门禁 | 提交测试前 |
| test_coverage_gate.yaml | 测试覆盖率门禁 | 合并到主分支前 |
| security_review_gate.yaml | 安全审查门禁 | 发布前 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| tech-architect.yaml | 技术架构师 | 设计系统架构 |
| backend-engineer.yaml | 后端工程师 | 实现后端逻辑 |
| frontend-engineer.yaml | 前端工程师 | 实现前端界面 |
| code-reviewer.yaml | 代码审查员 | 审查代码质量 |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| api-design.yaml | API 设计技能 |
| coding-standards.yaml | 编码规范技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| api_spec_contract.yaml | API 规范契约 |
| design_doc_contract.yaml | 设计文档契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| prd | prd-dev 需求包契约 | 产品到开发 E2E 工作流 |
| ui | ui-dev UI 规范契约 | 设计到开发 E2E 工作流 |
| qa | dev-qa 测试输入契约 | 开发到测试 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
