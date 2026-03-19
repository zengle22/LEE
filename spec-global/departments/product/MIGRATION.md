# Product Migration Plan

本文档定义 `departments/prd/` 向 `departments/product/` 的迁移原则。

补充说明：

- 本文档同时定义 `spec-global/workflows/core/` 中交付轴模板回收至部门 canonical path 的迁移方案
- 本次回收只处理 spec canonical path、对象归属、gate 归属和 registry 对齐
- 本次回收不改变 Python runtime 的模板渲染机制，不把 checked-in workflow template 变成 runtime instance

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

## Delivery Axis Canonicalization

### 背景

当前仓库存在一组交付轴模板放在 `spec-global/workflows/core/`：

- `feat2plan-l2-template.yaml`
- `feat2release-l3-template.yaml`
- `release2devplan-l3-template.yaml`
- `release2testplan-l3-template.yaml`

这组模板并非 framework-level 的通用抽象，而是直接绑定以下业务 SSOT 与部门协作语义：

- `FEAT`
- `RELEASE`
- `DEVPLAN`
- `TESTPLAN`
- `product -> dev -> qa` handoff

因此它们继续放在 `core` 会造成三类治理问题：

1. `core` 承担了业务链模板，而不是通用模板规范、通用 gate 或通用 contract
2. `departments/product/README.md` 已声明产品 workflow 的 canonical path 在 `departments/product/workflows/templates/`，与现状冲突
3. `departments/dev/` 与 `departments/qa/` 已各自存在 `devplan` / `testplan` 管理模板草案，导致跨目录重复定义

### 迁移目标

迁移完成后，应满足以下目标态：

- `core` 不再承载交付轴业务模板
- 产品部门拥有交付轴入口与上游范围收敛模板
- `DEVPLAN` 相关模板与 gate 归 `dev`
- `TESTPLAN` 相关模板与 gate 归 `qa`
- registry、README、索引文档、gate 引用全部指向新的 canonical path
- 不保留两套同时演进的活跃模板

### 目标归属矩阵

| 当前 canonical path | 目标 canonical path | 目标 owner | 说明 |
| --- | --- | --- | --- |
| `workflows/core/feat2plan-l2-template.yaml` | `departments/product/workflows/templates/feat-to-plan/v1/workflow.yaml` | `product-ai` | 交付桥接层，负责从冻结 FEAT 派生 RELEASE/DEVPLAN/TESTPLAN 的上游编排 |
| `workflows/core/feat2release-l3-template.yaml` | `departments/product/workflows/templates/feat-to-release/v1/workflow.yaml` | `product-ai` | 基于 FEAT Bundle 生成 RELEASE draft / scope freeze 输入 |
| `workflows/core/release2devplan-l3-template.yaml` | `departments/dev/workflows/templates/release-to-devplan/v1/workflow.yaml` | `dev-governance` | `DEVPLAN` 是 dev 主对象，模板应归 dev |
| `workflows/core/release2testplan-l3-template.yaml` | `departments/qa/workflows/templates/release-to-testplan/v1/workflow.yaml` | `qa-governance` | `TESTPLAN` 是 qa 主对象，模板应归 qa |

### 目标 ID 矩阵

建议统一改掉 `core` 命名，避免路径迁移后仍保留错误语义：

| 当前 ID | 目标 ID |
| --- | --- |
| `workflow.core.feat2plan` | `workflow.product.feat_to_plan_pipeline` |
| `template.core.feat2release` | `workflow.product.task.feat_to_release` |
| `template.core.release2devplan` | `workflow.dev.task.release_to_devplan` |
| `template.core.release2testplan` | `workflow.qa.task.release_to_testplan` |

命名约束：

- `product` 入口与桥接流程使用 `workflow.product.*`
- `dev` 计划派生模板使用 `workflow.dev.*`
- `qa` 计划派生模板使用 `workflow.qa.*`
- 不再新增 `template.core.*` 形式的业务链 ID

### Gate 归属矩阵

当前 `core/gates/` 下这组 gate 也与交付轴强绑定，不应继续作为 `core` canonical asset：

| 当前 gate | 目标 canonical path | 归属 |
| --- | --- | --- |
| `gate.core.release_generate_gate` | `departments/product/gates/release-generate-gate/v1/gate.yaml` | `product` |
| `gate.core.release_validate_gate` | `departments/product/gates/release-validate-gate/v1/gate.yaml` | `product` |
| `gate.core.output_contract_gate` | `departments/product/gates/output-contract-gate/v1/gate.yaml` | `product` |
| `gate.dev.task_validate_gate` | `departments/dev/gates/task-validate-gate/v1/gate.yaml` | `dev` |
| `gate.dev.devplan_freeze_gate` | `departments/dev/gates/devplan-freeze-gate/v1/gate.yaml` | `dev` |
| `gate.qa.test_set_validate_gate` | `departments/qa/gates/test-set-validate-gate/v1/gate.yaml` | `qa` |
| `gate.qa.testplan_freeze_gate` | `departments/qa/gates/testplan-freeze-gate/v1/gate.yaml` | `qa` |

额外约束：

- `product` 当前没有 `gates/` 目录，本次迁移必须补建
- gate 的 `trigger.source` 与 `on_fail.return_to` 必须同步切换到新 workflow ID
- 不允许 gate 物理路径已迁走，但 `source` 仍引用 `template.core.*`

### RELEASE 语义边界

本次迁移涉及 `RELEASE`，但不建议在本轮同时重写整个 release domain。采用以下最小边界：

- `product` 负责 `RELEASE` 的上游范围组织语义
- `product` 侧产出的 `RELEASE` 可处于 `draft` 或 `scope_frozen` 之前的准备态
- `dev` 负责 release execution、go/no-go、close 等执行态语义
- `qa` 负责基于 `TESTPLAN` 的测试执行与覆盖结果

为避免语义打架，本次迁移需要补一个最小 `release-contract`，但不要在同一轮把 release runtime 治理一并推倒重来。

### Phase A: Canonical Path Preparation

准备阶段必须先做目录和治理面补齐：

1. 新建 `departments/product/gates/`
2. 新建 `departments/product/contracts/release-contract/v1/`
3. 新建 `departments/product/workflows/templates/feat-to-plan/v1/`
4. 新建 `departments/product/workflows/templates/feat-to-release/v1/`
5. 新建 `departments/dev/workflows/templates/release-to-devplan/v1/`
6. 新建 `departments/qa/workflows/templates/release-to-testplan/v1/`

进入 Phase B 的前置条件：

- 目录结构齐全
- 产品目录已经具备 workflow / contract / gate 三种 canonical surface
- 迁移 owner 已确认 `product/dev/qa` 三方边界

### Phase B: Workflow Migration

#### B1. 迁移 FEAT to RELEASE

源文件：

- `spec-global/workflows/core/feat2release-l3-template.yaml`

目标文件：

- `spec-global/departments/product/workflows/templates/feat-to-release/v1/workflow.yaml`

必改字段：

- `id`
- `name`
- `owner`
- `tags`
- `gate_id`
- `created_by`
- `governing_adrs`
- 任意 `template.core.*` / `workflow.core.*` 引用

#### B2. 迁移 FEAT to PLAN

源文件：

- `spec-global/workflows/core/feat2plan-l2-template.yaml`

目标文件：

- `spec-global/departments/product/workflows/templates/feat-to-plan/v1/workflow.yaml`

必改字段：

- `id`
- `name`
- `owner`
- `tags`
- `l3_template_id`
- `gate_id`
- `downstream_integration`
- `created_by`
- `constitution.id`

#### B3. 迁移 RELEASE to DEVPLAN

源文件：

- `spec-global/workflows/core/release2devplan-l3-template.yaml`

目标文件：

- `spec-global/departments/dev/workflows/templates/release-to-devplan/v1/workflow.yaml`

必改字段：

- `id`
- `name`
- `owner`
- `tags`
- `gate_id`
- `created_by`
- 任意 `template.core.release2devplan` 自引用

#### B4. 迁移 RELEASE to TESTPLAN

源文件：

- `spec-global/workflows/core/release2testplan-l3-template.yaml`

目标文件：

- `spec-global/departments/qa/workflows/templates/release-to-testplan/v1/workflow.yaml`

必改字段：

- `id`
- `name`
- `owner`
- `tags`
- `gate_id`
- `created_by`
- 任意 `template.core.release2testplan` 自引用

### Phase C: Gate Migration

迁移顺序必须跟随 workflow 迁移完成，否则 `trigger.source` 会悬空。

#### C1. Product gates

从 `core/gates/` 迁出：

- `release-generate-gate`
- `release-validate-gate`
- `output-contract-gate`

迁移要求：

- `id` 若保留旧值，也必须更新 `source` 与 `return_to`
- 更推荐同步改成 `gate.product.*`
- `owner` 改为 `product-ai` 或 `product-governance`
- `tags` 去掉 `core`

#### C2. Dev gates

从 `core/gates/` 迁出：

- `task-validate-gate`
- `devplan-freeze-gate`

迁移要求：

- `source` 改指 `workflow.dev.task.release_to_devplan`
- `return_to` 改指 `workflow.dev.task.release_to_devplan`
- 保留 `gate.dev.*` 前缀可接受

#### C3. QA gates

从 `core/gates/` 迁出：

- `test-set-validate-gate`
- `testplan-freeze-gate`

迁移要求：

- `source` 改指 `workflow.qa.task.release_to_testplan`
- `return_to` 改指 `workflow.qa.task.release_to_testplan`
- 保留 `gate.qa.*` 前缀可接受

### Phase D: Registry and Documentation Update

必须同步更新以下索引面：

- `spec-global/_metadata.yaml`
- `spec-global/WORKFLOWS.md`
- `spec-global/departments/product/README.md`
- `spec-global/departments/product/SPEC_MAINTENANCE.md`
- `spec-global/departments/product/MIGRATION.md`

如 dev/qa 的 README 或 workflow index 中引用旧路径，也必须一并修正。

registry 更新规则：

1. 先注册新路径
2. 确认所有引用已切到新 ID
3. 再删除旧 `core` registry 项
4. 不允许新旧 registry 长期同时标记为 canonical

### Phase E: Overlap Resolution

当前存在三组潜在重叠模板：

- `departments/product/workflows/templates/feat-to-plan/*`
- `departments/dev/workflows/templates/devplan-management-l2-template.yaml`
- `departments/qa/workflows/templates/testplan-management-l2-template.yaml`
- `departments/dev/workflows/templates/release-delivery-l1-template.yaml`

本阶段不要求一次性合并所有设计，但必须做 canonical 判定：

- `feat-to-plan` 负责从冻结 FEAT 派生计划对象
- `release-to-devplan` 负责 dev 侧计划对象生成
- `release-to-testplan` 负责 qa 侧计划对象生成
- `devplan-management-l2` 和 `testplan-management-l2` 若保留，应标记为执行期管理模板，不得再次承担 canonical 派生职责
- `release-delivery-l1` 若继续存在，应改为 release execution 主链，而不是重复定义上游 plan derivation canonical path

如果无法在本轮完成合并，至少要在相关文件顶部加入非 canonical 说明，避免继续双轨演进。

### 实施顺序

推荐执行顺序：

1. 建目录与补 contract
2. 迁移 product workflow
3. 迁移 dev workflow
4. 迁移 qa workflow
5. 迁移 product gates
6. 迁移 dev gates
7. 迁移 qa gates
8. 更新 metadata 与 WORKFLOWS 索引
9. 更新 README / MIGRATION / SPEC_MAINTENANCE
10. 删除旧 `core` workflow 与已废弃 gate spec

### 迁移验收标准

以下条件全部满足，才可视为迁移完成：

- 全局不再出现 `workflow.core.feat2plan`
- 全局不再出现 `template.core.feat2release`
- 全局不再出现 `template.core.release2devplan`
- 全局不再出现 `template.core.release2testplan`
- `spec-global/workflows/core/` 不再承载交付轴业务模板
- `spec-global/core/gates/` 不再承载交付轴专用 gate
- `spec-global/_metadata.yaml` 的 canonical path 全部指向部门目录
- `spec-global/WORKFLOWS.md` 不再宣传旧 `core` 路径
- `product`、`dev`、`qa` 的 README 对对象归属描述一致
- 不存在新旧两套同时标记为 active/canonical 的模板

### 验证清单

迁移提交前必须至少执行以下检查：

1. 全局检索旧 ID：
   - `workflow.core.feat2plan`
   - `template.core.feat2release`
   - `template.core.release2devplan`
   - `template.core.release2testplan`
2. 全局检索旧路径：
   - `spec-global/workflows/core/feat2plan-l2-template.yaml`
   - `spec-global/workflows/core/feat2release-l3-template.yaml`
   - `spec-global/workflows/core/release2devplan-l3-template.yaml`
   - `spec-global/workflows/core/release2testplan-l3-template.yaml`
3. 检查 gate 的 `trigger.source`
4. 检查 gate 的 `on_fail.return_to`
5. 检查 `_metadata.yaml` 中是否仅保留新 canonical path
6. 检查 `WORKFLOWS.md` 是否仅展示新 canonical path
7. 运行一次 `spec-review` 风格评审，重点检查 template/runtime 边界和 gate 弱化风险

### 非目标

以下内容不在本次迁移内：

- 重写 Python runtime 编排器
- 将 checked-in workflow spec 固化为 runtime instance
- 一次性重写全部 dev/qa release execution 模板
- 在没有边界决议的情况下引入新的 release object taxonomy

### 风险与升级条件

出现以下情况时，应暂停迁移并升级处理：

- 同一个 workflow 仍有两个被主文档声明为 canonical 的文件
- `RELEASE` 语义在 `product` 与 `dev` 侧出现不可调和冲突
- 迁移必须依赖弱化人类 gate 才能完成
- `devplan-management-l2` / `testplan-management-l2` 的现有消费者无法切换
- `core` 仍被要求承载业务模板作为长期方案
