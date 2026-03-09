# PRD Agents Deprecation Notice

`departments/prd/agents/` 已进入兼容保留阶段。

## 原则

- 旧 agent 文件保留用于历史兼容和迁移参考
- 新的 canonical product agent 定义统一进入 `departments/product/agents/`
- 不再在 `departments/prd/agents/` 中扩展前向产品语义

## 已迁移的 canonical 路径

- `agent.analysis.product_goal` -> `departments/product/agents/product-goal-analyzer/v1/agent.yaml`
- `agent.product.requirement_alignment` -> `departments/product/agents/requirement-alignment/v1/agent.yaml`
- `agent.product.requirement_decomposer` -> `departments/product/agents/requirement-decomposer/v1/agent.yaml`
- `agent.product.prd_writer` -> `departments/product/agents/prd-writer/v1/agent.yaml`
- `agent.product.pm_planner` -> `departments/product/agents/pm-planner/v1/agent.yaml`

## 仍保留的公共/兼容角色

- `agent.review.requirement_reviewer`
- 其他仅作历史参考的旧 PRD agent
