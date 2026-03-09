# Product Department System (v2.0)
# 产品部门规范体系（SSOT 重构版）

本目录是产品部门的新 canonical 路径，用于替代 `departments/prd/`。

正式设计说明见项目级 SSOT：

- `spec/adr/ADR-003__product-department-ssot-design.md`

维护规范见：

- `SPEC_MAINTENANCE.md`

设计目标：

- 以 SSOT 主链为核心，而不是以 PRD 文档为核心
- 将产品部门职责收敛到 `SRC -> EPIC -> FEAT -> UI / TECH / TASK`
- 将人类 gate 固定在 `EPIC freeze` 和 `FEAT freeze` 等关键冻结点
- 为研发部门提供更稳定的下游输入，而不是模糊的需求包

## 核心原则

1. 上游 `SRC` 来自市场机会或原始需求，不直接视为 `EPIC`
2. `EPIC` 只聚合多个可独立验收的 `FEAT`
3. `FEAT` 是最小可独立验收能力单元，`User Story` 只是可选视角，`AC` 才是硬约束
4. `UI`、`TECH`、`TASK` 只挂在 `FEAT` 下，不直接挂在 `EPIC`
4. `API` 属于 `TECH` 范畴，不与 `TASK` 平级
5. `frontend` / `backend` 是 `TASK` 的执行拆分，不是 SSOT 主类型
6. `TESTSET` 从 `FEAT` 派生，不直接挂在 `EPIC`
7. `TESTSET` 的治理归属在 `QA`，`product` 负责提供稳定 seed，不在本目录复制 QA 主对象

## 工作流结构

- `product-main-pipeline`
  - 产品部门 L2 主编排模板，只负责串联 L3 子流程
- `src-to-epic`
  - 从 `SRC` 生成 `EPIC` 的 L3 模板，并进行人类冻结
- `epic-to-feat`
  - 从冻结后的 `EPIC` 生成多个 `FEAT` 的 L3 模板，并进行人类冻结
- `feat-to-delivery-prep`
  - 从冻结后的 `FEAT` 生成 `UI`、`TECH(API included)`、`TASK(frontend/backend/integration)` 准备包的 L3 模板

模板物理路径统一放在：

- `departments/product/workflows/templates/`

说明：

- 仓库中的 `workflow.yaml` 定义的是 template，不是运行时 instance
- 真实执行态 workflow 由 Python runtime 根据这些 template 动态生成

## 迁移约定

- 新业务默认只接入 `departments/product/`
- `departments/prd/` 保留兼容窗口，但不再作为新规范的演进位置
- 当所有上下游 handoff 切换完成后，`departments/prd/` 将进入只读废弃状态
