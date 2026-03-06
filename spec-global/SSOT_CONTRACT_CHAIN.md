# Spec-Global SSOT Contract Chain

## 1. Scope

这份文档定义 `spec-global` 里“哪些 contract 应升格为正式 SSOT 对象，哪些只是交接包/冻结包”，并固定产品主链：

`SRC -> EPIC -> FEAT -> UI / TECH / TASK / TESTSET -> TC -> REPORT / BUG -> EVI`

边界约束：

- `商业机会` 不是 `EPIC`，默认作为上游 `SRC`
- `EPIC` 只聚合多个 `FEAT`，不直接挂 `UI/TECH/TASK/TESTSET`
- 正式 SSOT 主文件落在项目内容目录，不落 `.artifacts/ssot/{type}/`
- `.artifacts/` 只保留 registry、manifest、缓存、运行态索引

## 2. Agent Contract Required Fields

凡是 agent 计划生成正式对象，contract 里必须显式声明治理属性；不要靠目录名或文件名猜。

推荐字段：

- `identity_kind`: `ssot | non_ssot`
- `ssot_type`: `SRC | EPIC | FEAT | UI | TECH | TASK | TESTSET | TC | BUG | REPORT | ADR | EVI`
- `title`: 供 SSOT filename slug 生成
- `parent`: 引用本 contract 内其他输出的符号名
- `derived_from`
- `source_refs`
- `verifies`
- `implements`
- `placement_key`: 可选；只提示目录层，不决定文件名

在 agent spec 里的接入建议：

- 继续保留原业务 `contracts.output_schema`
- 新增 `contracts.ssot_output_schema`
- 用 `ssot_output_contract.example` 给出该 agent 进入正式主链时的最小声明样例

运行时职责：

- contract 负责声明对象类型和关系语义
- runtime 负责分配真实 ID、生成 `[ID]__[slug].[ext]`、写入正式目录

## 3. Canonical Mapping

| Spec-Global Contract / Package | Current Location | Canonical SSOT Role | Parent / Source Rule | Notes |
|---|---|---|---|---|
| `market_signal_freeze` | `departments/stg/contracts/market_signal_freeze/v1` | `SRC` | root | 冻结后的上游市场信号 |
| `business_opportunity` | `departments/stg/contracts/business_opportunity/v1` | `SRC` | `source_refs -> market_signal_freeze` | 商业机会不是 `EPIC` |
| `business_opportunity_freeze` | workflow only | non-SSOT bundle | 引用 `SRC` | 交接包，不做主对象 |
| `frozen-module-requirement-contract` | `departments/prd/contracts/frozen-module-requirement-contract/v1` | `EPIC` | `source_refs -> SRC` | 产品建设层的大块能力/版本主题 |
| `requirement-freeze` | workflow only | `EPIC` freeze view | `derived_from -> EPIC` | 工作流已引用，但 schema 未落盘 |
| `frozen-detailed-prd-contract` | `departments/prd/contracts/frozen-detailed-prd-contract/v1` | `FEAT` or FEAT view | `parent_id -> EPIC` when split | 每个可独立验收功能拆成一个 `FEAT` |
| `problem-definition` | `departments/prd/contracts/problem-definition/v1` | supporting non-SSOT | 引用 `SRC/EPIC` | 分析文档，不是主对象 |
| `requirement-breakdown` | `departments/prd/contracts/requirement-breakdown/v1` | supporting non-SSOT | 引用 `EPIC/FEAT` | 拆解过程文档 |
| `ui-page-contract` | `departments/ui/contracts/ui-page-contract/v1` | `UI` | `parent_id -> FEAT` | 正式 UI 页面定义 |
| `user-flow-contract` | `departments/ui/contracts/user-flow-contract/v1` | `UI` | `parent_id -> FEAT` | 可与页面对象并列或挂同一 FEAT |
| `frozen-ui-prototype-contract` | `departments/ui/contracts/frozen-ui-prototype-contract/v1` | `UI` | `parent_id -> FEAT` | 视为 UI 的冻结主版本 |
| `prototype_freeze_package` | workflow only | non-SSOT bundle | 引用 `UI/FEAT` | 交接包，不做主对象 |
| `frozen-technical-architecture-contract` | `departments/dev/contracts/frozen-technical-architecture-contract/v1` | `TECH` | `parent_id -> FEAT` | 一个 FEAT 一份主技术方案 |
| `api-contract` | `departments/dev/contracts/api-contract/v1` | `TECH` | `parent_id -> FEAT` or `derived_from -> TECH` | API 是技术设计的一部分 |
| `development-plan-contract` | `departments/dev/contracts/development-plan-contract/v1` | `TASK` | `parent_id -> FEAT` | 实施任务/任务包 |
| `frozen-dev-package-contract` | `departments/dev/contracts/frozen-dev-package-contract/v1` | non-SSOT bundle | 引用 `FEAT/UI/TECH/TASK` | 开发移交包 |
| `test-plan` | `departments/qa/contracts/test-plan/v1` | non-SSOT | 引用 `FEAT/TESTSET` | 测试规划文档，不进正式 SSOT |
| `test-set` | `departments/qa/contracts/test-set/v1` | `TESTSET` | `parent_id -> FEAT` | 一个 FEAT 可以有多个测试集 |
| `test-case` / `test-case-contract` | `departments/qa/contracts/test-case*/v1` | `TC` | `parent_id -> TESTSET` and `verifies -> FEAT` | 测试执行树正式节点 |
| `test-report` | `departments/qa/contracts/test-report/v1` | `REPORT` | `parent_id -> FEAT` | 验证/验收结果 |
| `bug-contract` | `departments/qa/contracts/bug-contract/v1` | `BUG` | `parent_id -> TC` or `FEAT` | 缺陷归属到测试或功能范围 |
| evidence bundle / logs / screenshots | workflow outputs | `EVI` | `parent_id -> REPORT / TC / BUG / TECH / TASK` | 证据附件 |
| `test_submission_freeze_package` | workflow only | non-SSOT bundle | 引用 `TESTSET/TC/REPORT` | 提测交接包 |
| `deliverable_release` | cross workflow output | non-SSOT release bundle | 引用发布集合 | 不是 SSOT 主对象 |

## 4. EPIC Rule

`EPIC` 只在下面场景创建：

- 覆盖多个可独立验收的 `FEAT`
- 跨多个迭代或里程碑
- 有统一业务目标、边界和优先级

不要创建 `EPIC` 的场景：

- 只有一个可交付小功能
- 只是单页/单接口范围
- 只是把商业机会机械转抄成研发对象

## 5. Workflow-Only Gaps

当前有一批对象已在 workflow 中被引用，但 contract schema 还没有正式落盘：

- `business_opportunity_freeze`
- `requirement-freeze`
- `prototype_freeze_package`
- `test_submission_freeze_package`
- `product-value-proposal`
- `product-value-freeze`

这些对象在 schema 未补齐前，一律按：

- 正式主对象：按上表映射到 `SRC/EPIC/FEAT/UI/TECH/TASK/TESTSET/TC/BUG/REPORT/EVI`
- 交接包：保持 non-SSOT bundle，不进入主链
