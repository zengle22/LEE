# UI 设计部门 (ui)

> UI Design Department

## 部门职责

负责 UI 设计、设计系统维护和设计规范管理

### 主要职责

- UI 设计
- 设计系统维护
- 设计规范制定
- 原型设计
- 视觉设计

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
| ui_design.yaml | UI 设计工作流 | PRD | UI 设计稿 |
| design_review.yaml | 设计评审工作流 | UI 设计稿 | 评审报告 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| design_quality_gate.yaml | 设计质量门禁 | 提交开发前 |
| design_system_compliance_gate.yaml | 设计系统合规门禁 | 设计评审前 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| ui-designer.yaml | UI 设计师 | 设计用户界面 |
| icon-generator.yaml | 图标生成 | 生成应用图标 |
| ui-contract-generator.yaml | UI 契约生成 | 生成 UI 设计契约 |
| ui-contract-validator.yaml | UI 契约验证 | 验证 UI 设计契约 |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| design-system.yaml | 设计系统技能 |
| visual-design.yaml | 视觉设计技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| ui-design-contract.yaml | UI 设计契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| prd | prd-ui 设计需求契约 | 产品到设计 E2E 工作流 |
| dev | ui-dev UI 规范契约 | 设计到开发 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
