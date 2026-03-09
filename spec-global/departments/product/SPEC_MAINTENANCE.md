# Product Spec Maintenance

`departments/product/` 的 spec 维护遵循 `spec-global/core/agents/` 中的 canonical maintainer 边界。

推荐入口 skill：

- `C:\Users\shado\.codex\skills\lee-spec-governance\SKILL.md`

## 维护边界

- Workflow 规范
  - 使用 `core/agents/workflow-spec-maintainer`
- Agent 规范
  - 使用 `core/agents/agent-spec-maintainer`
- Contract 规范
  - 使用 `core/agents/contracts-spec-maintainer`
- Gate 规范
  - 使用 `core/agents/gates-spec-maintainer`
- 统一评审
  - 使用 `core/agents/spec-review`

## 关键原则

- Workflow 只定义模板和依赖，不承担运行时编排实现
- 运行时执行由 Python orchestrator / runtime 负责
- Product 业务 agent 只负责生成业务对象，不负责编排 workflow
- 不再引入 `pipeline-orchestrator` 这类重复 workflow engine 职责的 product agent
- 维护 `workflow / agent / contract / gate / skill / review` 类 spec 时，优先通过 `lee-spec-governance` 进入正确的 maintainer 边界
- `ADR` 属于 decision SSOT；维护 agent / skill / workflow / contract 时，应将相关 ADR 作为 `governing_adrs` 或 `decision_refs` 注入维护上下文
- 维护 agent 与 skill 时，不得把 ADR 当作业务需求源，而应当把它当作治理约束和边界说明

## 推荐维护流程

1. 触发 `lee-spec-governance`
2. 识别 spec 类型
3. 路由到对应 core maintainer agent 边界
4. 完成变更后走 `spec-review`
5. 如涉及 canonical path 迁移，同步更新 registry / README / deprecation docs
6. 如变更受正式 ADR 约束，必须在维护上下文和产物 trace 中保留 `governing_adrs` 或 `decision_refs`

## 当前 Product Canonical Spec Surface

- Workflow:
  - `product-main-pipeline`
  - `src-to-epic`
  - `epic-to-feat`
  - `feat-to-delivery-prep`
- Agents:
  - `agent.analysis.product_goal`
  - `agent.product.requirement_alignment`
  - `agent.product.epic_designer`
  - `agent.product.requirement_decomposer`
  - `agent.product.prd_writer`
  - `agent.product.pm_planner`
- Contracts:
  - `raw-source-input-contract`
  - `source-freeze-contract`
  - `problem-definition`
  - `epic-contract`
  - `feat-breakdown-contract`
  - `feat-contract`
  - `product-review-contract`
