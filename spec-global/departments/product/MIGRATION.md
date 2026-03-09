# Product Migration Plan

本文档定义 `departments/prd/` 向 `departments/product/` 的迁移原则。

## 迁移动机

- 旧 `prd` 目录的流程中心仍是 `requirement/prd/dev-freeze`
- 全局 SSOT 主链已经固定为 `SRC -> EPIC -> FEAT -> UI / TECH / TASK`
- 旧目录存在重复 workflow 前半段，不适合继续演进

## 迁移阶段

### Phase 1: 建立新 canonical 路径

- 新建 `departments/product/`
- 注册新 workflow 到 `spec-global/_metadata.yaml`
- 将新设计定义为后续增量需求的唯一演进位置

### Phase 2: 切流

- 上游市场/需求入口改为 handoff 到 `workflow.product.product_main_pipeline`
- 下游 UI / Dev / QA 逐步改为消费 `EPIC`、`FEAT`、`UI`、`TECH`、`TASK`
- 停止向 `departments/prd/` 增加新能力

### Phase 3: 废弃旧路径

- 在 `departments/prd/` 文档中标记 deprecated
- 保留历史参考，不再更新
- 待引用清零后再物理删除

## 切流约束

- 不允许长期双轨演进
- 新增 contract 与 workflow 只能进入 `product`
- 若上下游仍依赖 `prd`，只做兼容说明，不在旧路径继续扩展语义
