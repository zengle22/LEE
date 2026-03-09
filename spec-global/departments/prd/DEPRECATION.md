# PRD Department Deprecation Notice

`departments/prd/` 已进入废弃迁移阶段。

## 状态

- 允许保留历史规范与兼容引用
- 不再作为新 workflow / contract / agent 的演进目录
- 新增产品流程统一进入 `departments/product/`

## 替代路径

- 新 L2 主编排：`workflow.product.product_main_pipeline`
- 新 L3 子流程：
  - `workflow.product.task.src_to_epic`
  - `workflow.product.task.epic_to_feat`
  - `workflow.product.task.feat_to_delivery_prep`
- 新正式设计文档：
  - `spec/adr/ADR-003__product-department-ssot-design.md`

## 迁移原则

- 旧路径只做兼容说明，不继续扩展语义
- 待上下游 handoff 全部切换完成后，再进入只读归档或删除
- 旧 `agents/` 目录的 canonical 替代关系见：
  - `departments/prd/agents/DEPRECATION.md`
