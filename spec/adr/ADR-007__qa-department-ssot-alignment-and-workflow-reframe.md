---
id: ADR-007
ssot_type: adr
title: QA department SSOT alignment and workflow reframe
status: frozen
version: v1
parent_id: null
derived_from_ids:
- ADR-001
- ADR-003
source_refs:
- ADR-001#4-1-three-axis-model
- ADR-001#12-1-p0-blocking-rules
- ADR-003#11-9-feat-to-testset-derivation-rules
owner: qa
tags:
- qa
- ssot
- workflow
- governance
properties:
  adr_kind: department_design
  decision_scope: qa_department_canonical_path
  analyzed_at: 2026-03-11 00:00:00+08:00
frozen_at: '2026-03-11T14:29:43.807158'
---

# QA 部门接入升级版 SSOT 的系统梳理

## 1. Decision

QA 部门后续的 canonical 链路调整为三轴并行、单点收口：

- 需求轴：`FEAT -> TESTSET -> TC`
- 交付轴：`RELEASE -> TESTPLAN -> TASK`
- 证据轴：`TASK / TC / TSE -> BUG / REPORT / EVI`

其中：

- `TESTSET` 是 `FEAT` 的正式测试真源，必须且只能验证单一 `FEAT`
- `TESTPLAN` 是 `RELEASE` 下的正式验证承诺，不再只是非 SSOT 的规划文档
- QA 执行任务必须挂在 `TESTPLAN` 下的 `TASK`，不能再直接从 `FEAT` 或自由输入开工
- `TSE`、执行日志、截图、runner 输出、回归结论属于运行时事实或证据层，不替代 `TESTSET / TESTPLAN`
- `BUG / REPORT / EVI` 必须能反查到 `RELEASE / TESTPLAN / TASK / TESTSET / FEAT`

QA 的所有 workflow 都必须围绕这条规则重排，而不是继续维持“测试计划文档 + 测试集文档 + 运行目录”各自为政。

## 2. Current State

结合仓库当前实现，QA 已经有一部分升级基础，但仍处于“半对齐”状态。

### 2.1 已经对齐的部分

- `spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml`
  - 已明确 `feat_freeze` 为首选输入
  - 已要求 `TESTSET` trace 到单一 `FEAT`
  - 已引入 `governing_adrs / decision_refs / decision_constraints`
- `spec-global/departments/qa/contracts/test-set/v1/schema.yaml`
  - 已增加 `feature_ids`
  - 已强制 `feature_ids LENGTH == 1`
  - 已强制 `acceptance_criteria_refs`
- `spec-global/departments/qa/agents/test-set-generator/v1/agent.yaml`
  - 已接入 `ssot_output_schema`
  - 已要求输出挂在真实 `FEAT ID` 下
- `spec-global/departments/qa/workflows/templates/test-set-execute-l3-template.yaml`
  - 已把执行态拆成 `case_generation -> script_translation -> script_execution -> result_judgment -> tse_assembly -> bug_drafting`
  - 已建立反 mock、证据完整性、角色分离约束

### 2.2 未对齐的部分

- `spec-global/departments/qa/contracts/test-plan/v1/schema.yaml`
  - 仍是旧的测试规划文档模型
  - 没有 `RELEASE` 归属、`derived_from_ids[{id,version}]`、slice coverage、entry gate、go/no-go 绑定
  - 与 ADR-001 中 `TESTPLAN` 正式对象定义不一致
- `spec-global/departments/qa/contracts/test-run/v1/schema.yaml`
  - 仍是运行批次视角，缺少对 `RELEASE / TESTPLAN / TASK` 的正式 trace
- `spec-global/departments/qa/contracts/test-set-execution/v1/schema.yaml`
  - 仍把 `TSE` 当作执行汇总对象，但缺少 `task_id`、`release_id`、`testplan_id`、`decision_refs`
- `spec-global/departments/qa/docs/test-case-management-guide.md`
  - 仍以 `PRD / REQ / requirement_id` 为主线
  - 仍在写“需求文档 -> 测试计划 -> 测试套件 -> 测试用例”
  - 没有切到 `FEAT / RELEASE / TESTPLAN`
- `spec-global/departments/qa/README.md`
  - 宣称 `test-plan` 是 contract 化产物，但仍将其当作主入口
  - 文档中“自动化追溯”与当前 SSOT 三轴模型还未完全打通
- `runtime/departments/qa/workflows/README.md`
  - 仍引用旧的 `test-set-l3-template.yaml` 名称
- `spec/testing/testsets/*.md`
  - 项目级 TESTSET 样本目前只有最薄 front matter
  - `derived_from_ids / source_refs / acceptance / risk / strategy / decision trace` 基本未落正文

## 3. QA Workflow Reframe

QA 部门的 workflow 应重构为 5 类，而不是只理解成一个“执行测试”的部门。

### 3.1 Workflow A: Test Set Production

目标：

- 从 `FEAT freeze + delivery_prep_bundle + governing_adrs` 派生正式 `TESTSET`

输入：

- `FEAT`
- `Acceptance Criteria`
- `delivery prep seed`
- `TECH / integration points`
- `ADR constraints`

输出：

- `TESTSET`
- 可选 `TC skeleton` 或覆盖切片说明

强约束：

- 一个 `TESTSET` 只能属于一个 `FEAT`
- `TESTSET` 必须声明覆盖的 `AC refs`
- `TESTSET` 不得从 `EPIC` 直接派生

现状判断：

- 当前 `test-set-production-l3-template` 是正确方向
- 但项目级 TESTSET 正文模板和冻结门槛还没跟上

### 3.2 Workflow B: Release Test Planning

目标：

- 将 `RELEASE` 纳入的 `FEAT@version + TESTSET` 转成正式 `TESTPLAN`

输入：

- `RELEASE`
- `TESTSET`
- 环境矩阵
- 风险、入口条件、阻断条件

输出：

- `TESTPLAN`
- `TASK-TESTPLAN-*`
- slice coverage 视图

强约束：

- `TESTPLAN.parent_id` 必须是 `RELEASE`
- `TESTPLAN.derived_from_ids` 必须至少覆盖本次 release 的 `FEAT@version` 和对应 `TESTSET`
- 每个必需 slice 都要有验证任务

现状判断：

- 当前 `test-plan-l2-template` 已经有 L2 编排能力
- 但绑定对象还是 `test_run` 驱动，不是 `RELEASE / TESTPLAN / TASK` 驱动
- 这是 QA 接入升级版 SSOT 的最大断点

### 3.3 Workflow C: Test Task Execution

目标：

- 对 `TESTPLAN` 下的验证任务执行一次正式验证

输入：

- `TASK-TESTPLAN-*`
- 绑定的 `TESTSET`
- 目标 `build / env / slice`

输出：

- `TSE`
- `REPORT(test_execution)`
- `EVI`
- `BUG`

强约束：

- 执行入口应该是 `TASK`，而不是随手给一个 `test_set_id`
- `TSE` 必须保留 `task_id / testplan_id / release_id`
- `REPORT` 是测试结论真源，`runner-output.json` 只是证据

现状判断：

- 当前 `test-set-execute-l3-template` 的执行分层是合理的
- 但它还缺一个正式上游：`TASK`

### 3.4 Workflow D: Bug Triage And Regression

目标：

- 把执行失败转成可审计的缺陷闭环，并驱动定向回归

输入：

- `BUG`
- 上游 `TSE / REPORT / EVI`
- 受影响 `FEAT / RELEASE / slice`

输出：

- 分流结果
- 回归任务或豁免结论
- 更新后的 `REPORT / EVI`

强约束：

- `BUG` 必须能追溯到发现它的 `REPORT`，并最终反查到 `RELEASE`
- 回归不是“再跑一遍测试”，而是 `TESTPLAN` 下的新验证任务
- waiver 必须有 `waiver_reason + waiver_approved_by`

现状判断：

- README 中有 bug 子流程概念
- 但 contract 与 workflow 还没按 `RELEASE / TESTPLAN / TASK` 真正建模

### 3.5 Workflow E: Exit Evaluation And Release Gate

目标：

- 形成 release 级 QA 判定，而不是 test run 级经验结论

输入：

- `TESTPLAN` 完成情况
- `REPORT(test_execution / regression / go_no_go)`
- blocker bug 状态
- 关键 `EVI`

输出：

- `REPORT(go_no_go)`
- 更新 `RELEASE` 判定输入

强约束：

- QA 不能再用自由文本“可出测”替代 release gate 事实
- release 级判定必须以 `RELEASE` 为 subject，而不是以 `Test Run` 为 subject

现状判断：

- 当前 `exit_evaluation` 更像测试轮次总结
- 需要升级为 release gate 输入

## 4. Canonical Object Mapping

QA 侧对象边界统一如下：

| 对象 | 正式定位 | 父对象 | 备注 |
|---|---|---|---|
| `TESTSET` | 需求轴测试真源 | `FEAT` | 单 FEAT、冻结后不可原地改 |
| `TC` | `TESTSET` 下的正式测试用例对象 | `TESTSET` | 可选固定化，不强制所有执行态 case 都入主链 |
| `TESTPLAN` | 交付轴正式验证计划 | `RELEASE` | 本次版本验证承诺 |
| `TASK` | 交付轴 QA 执行单元 | `TESTPLAN` | 每个 slice 至少一个验证任务 |
| `TSE` | 运行态执行实例/汇总 | 非主链对象或 `REPORT/EVI` 附属 | 不替代 `TESTPLAN / TASK / TESTSET` |
| `BUG` | 证据轴正式对象 | `FEAT` 或 `REPORT` 范围下 | 必须有 release/slice 来源 |
| `REPORT` | 证据轴正式结论 | `RELEASE` 或 `TASK` | `test_execution / regression / go_no_go` |
| `EVI` | 证据轴正式证据对象 | `REPORT / BUG / TASK` | 挂 runner 输出、日志、截图、命令轨迹 |

## 5. Mandatory Traceability Rules

QA 接入升级版 SSOT 后，至少新增以下硬规则：

1. `TESTSET` 必须且只能 `derived_from` 一个 `FEAT@version`
2. `TESTPLAN` 必须 `parent -> RELEASE`
3. `TESTPLAN` 必须覆盖 release 中所有必需 `FEAT slice`
4. QA 执行入口必须是 `TASK-TESTPLAN-*`
5. `TSE` 必须引用 `task_id + testplan_id + release_id + test_set_id`
6. `BUG` 必须引用 `source_report_id + found_in_release`
7. `REPORT(test_execution)` 必须能回溯到 `TASK`
8. `REPORT(go_no_go)` 的 `subject_id` 必须是 `RELEASE`
9. `EVI` 只能作为证据载体，不能代替 `REPORT`
10. 若有 `governing_adrs`，则 `decision_refs / decision_constraints` 必须可审计

## 6. Required Refactors

### 6.1 Contracts

优先级最高的 contract 改造面：

- `test-plan/v1`
  - 升格为正式 `TESTPLAN` schema
  - 增加 `parent_id=RELEASE`
  - 增加 `derived_from_ids[{id,version}]`
  - 增加 `environment_matrix / entry_conditions / blocker_rules / slices / go_no_go_inputs`
- `test-run/v1`
  - 明确降级为 runtime object，或补齐对 `TESTPLAN / RELEASE` 的 trace
- `test-set-execution/v1`
  - 增加 `task_id / testplan_id / release_id / decision_refs / evidence_refs`
- `test-report/v1`
  - 对齐 `REPORT` 正式对象语义

### 6.2 Workflows

- `test-plan-l2-template`
  - 从 “test run orchestration” 重写为 “TESTPLAN execution orchestration”
- `test-set-execute-l3-template`
  - 输入从 `test_run_id + test_set_id` 扩成 `task_id + testplan_id + release_id + test_set_ref`
- bug 子流程
  - 从 README 说明升级为正式 workflow template

### 6.3 Agents

- `requirement-analyzer`
  - 输入口径从 `requirement_doc` 迁到 `feat_freeze + delivery_prep_bundle`
- `tse-assembler`
  - 输出不只组装 `TSE`，还要保证能形成 `REPORT / EVI` 的引用基础
- `exit-evaluator`
  - 结论主体切换到 `RELEASE`

### 6.4 Project-Level SSOT Assets

- `spec/testing/testsets/*.md`
  - 需要从“空壳 front matter”补成真正可冻结的 `TESTSET` 正文
- 新增 `spec/delivery/testplans/`
  - 作为正式 `TESTPLAN` 落点
- 新增或规范 `docs/reports/testing/`
  - 作为 `REPORT` 正式落点

## 7. Migration Order

建议按下面顺序推进：

1. 先冻结 QA 对象边界
   - 明确 `TESTSET / TESTPLAN / TASK / REPORT / EVI / BUG / TSE` 的真源归属
2. 再升级 contract
   - 先 `test-plan`
   - 再 `test-set-execution`
   - 再 `test-report / bug-contract`
3. 再升级 workflow template
   - 先 L2
   - 再 L3
   - 最后 bug / release gate
4. 再迁移项目级样本
   - 补齐 `spec/testing/testsets`
   - 新建 `TESTPLAN` 样本
5. 最后接 validator / CLI / CI
   - 阻断“无 release、无 task、无 trace 的 QA 执行”

## 8. Immediate Next Actions

下一轮应直接开工的事项：

- 起草 `QA TESTPLAN` 正式 schema
- 为 `test-plan-l2-template` 增加 `RELEASE / TASK` 绑定语义
- 定义 `TSE -> REPORT / EVI / BUG` 的最小字段集
- 补一个完整项目级 `TESTSET` 样本，验证单 FEAT trace
- 清理 QA 文档中所有 `PRD / requirement_id` 为主线的旧表述

## 9. Conclusion

QA 当前不是“没有 workflow”，而是“已有 workflow 模板、contract、执行器，但正式 SSOT 主链仍未彻底切换”。

最大的结构性问题只有一个：

> `TESTSET` 已经基本完成 FEAT 化，但 `TESTPLAN / TASK / REPORT` 还没有完成 release 化。

如果不补上这一层，QA 后续所有 test set 及其派生产物虽然看起来“可追溯”，实际上仍只能追到局部文件，不能进入升级后的正式 SSOT 判定链。
