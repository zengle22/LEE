---
id: ADR-021
ssot_type: adr
title: Run-Scoped Artifact Placement Governance and Directory Audit
status: frozen
version: v1
workflow_instance_id: adr-021-governance
parent_id: null
derived_from_ids:
- ADR-003
- ADR-011
- ADR-020
source_refs: []
owner: governance
tags:
- ssot
- governance
- placement
- workflow
- runtime
- product
properties:
  adr_kind: governance_design
  decision_scope: run_scoped_artifact_directory_governance
  governs:
  - spec-global/departments/product/workflows/templates/requirement-chain-validation
  - spec-global/core/agents
  - src/lee/orchestrator/execution/artifacts
frozen_at: '2026-03-15T23:40:00+08:00'
---

# Run-Scoped Artifact Placement Governance and Directory Audit

## 1. Decision

本 ADR 建立一套覆盖“正式文件 + 中间文件”的统一目录治理方案。

核心决策如下：

1. 正式 SSOT 文件与非正式 workflow 产物的目录规则必须进入统一治理，不再散落在各 workflow prompt、agent prompt 和局部 reviewer 中。
2. 目录治理的真值源分两层：
   - 正式 SSOT 落点规则由 runtime placement policy 统一定义
   - 非正式 workflow 产物落点规则由公共 placement governance policy 统一定义
3. 每次 workflow 运行必须生成 run-scoped placement manifest，记录本次所有中间文件和正式文件的“声明落点 / 实际落点 / 是否合规”。
4. `requirement-chain-validation` 必须增加一个公共目录审计步骤，作为最终 handoff 前的阻断校验之一。
5. 新增公共 agent 负责目录审计，但不负责编排、搬运或自动修复文件。
6. 目录错误的治理策略采用分阶段收紧：
   - 第一阶段：审计 + gate 阻断
   - 第二阶段：运行时对关键正式对象直接 fail fast

## 2. Context

当前仓库已经存在三类相关能力，但尚未形成完整闭环。

### 2.1 已有能力

- runtime 已有大目录级写入保护，能够阻止越界写入未授权区域
- formal SSOT 已有 placement policy，可将主对象路由到 `spec/`、`tests/`、`docs/reports/` 等 canonical 目录
- formal SSOT 已有 front matter lint，可校验文件是否落在预期目录
- 若干 product workflow / agent 已显式要求：
  - 只能写当前 `step_workspace`
  - `TASK` 必须落盘
  - `task_directory` 必须与实际落盘路径一致

### 2.2 当前缺口

现状仍然缺少以下能力：

1. 缺少一个覆盖“本次运行全部文件”的统一审计机制
2. 缺少非正式产物的统一目录真值源
3. 缺少将目录错误纳入主链最终 gate 的统一阻断逻辑
4. 缺少正式对象和中间对象的统一文件清单
5. 缺少一个公共、可复用、跨 workflow 的目录审计 agent

### 2.3 当前症状

当前规则主要分散在：

- runtime 代码
- 局部 workflow 说明
- 个别 agent prompt
- 个别 reviewer 的检查项

这种分散结构会导致：

- 相同规则在多个位置重复
- formal 与 non-formal 产物治理口径不一致
- 某些文件虽然没有越界写入，但仍然写到了错误的 canonical 子目录
- `requirement-chain-validation` 只能校验链路语义，不能校验本次运行的文件落点质量

## 3. Problem Statement

产品主链在 `SRC -> EPIC -> FEAT -> delivery prep -> requirement chain validation` 完成后，不能只回答“对象关系是否正确”，还必须回答：

- 这次运行产生的所有正式文件是否放到了正确目录
- 这次运行产生的所有中间文件是否留在正确的运行时目录
- 是否有正式文件误写到 `step_workspace`
- 是否有中间文件误写到 `spec/` 或其他正式目录
- 是否有 review / report / bundle 文件写进错误目录并被误当作正式交付件

若这些问题无统一答案，则“链路通过”并不等于“交付面可治理”。

## 4. Scope

### 4.1 In Scope

- `requirement-chain-validation` 中新增目录审计能力
- 产品需求链运行中产生的正式文件与中间文件
- runtime 生成 run-scoped placement manifest
- 公共目录审计 agent
- formal / non-formal 产物目录规则统一化
- gate 对目录错误的阻断语义

### 4.2 Out of Scope

- 自动搬运已有错误文件
- 自动修复历史存量目录问题
- 用 agent 替代 runtime 进行物理文件写入
- 修改业务对象主链语义
- 在本 ADR 中直接定义所有 contract 细节字段

## 5. Artifact Taxonomy

目录治理首先建立统一产物分类。

### 5.1 Formal SSOT

正式 SSOT 主对象，例如：

- `SRC`
- `EPIC`
- `FEAT`
- `UI`
- `TECH`
- `TASK`
- `TESTSET`
- `TC`
- `BUG`
- `REPORT`
- `ADR`
- `EVI`

这些对象必须落到正式 canonical 内容目录。

### 5.2 Frozen Bundle / Handoff Deliverable

冻结视图、bundle、handoff manifest、review summary 等非主对象正式交付物，例如：

- `delivery_prep_freeze`
- `requirement_chain_validation_report`
- `scorecard`
- review bundle
- validation gate output

这些对象不是 formal SSOT 主文件，但属于正式交付面，不得留在 `step_workspace`。

### 5.3 Run-Scoped Intermediate

运行过程中的中间文件，例如：

- agent 原始输出
- schema repair 中间对象
- 解析中间 YAML / JSON
- step 级工作草稿
- 本次链路校验的临时报告草稿

这些文件应留在本次 workflow instance 的运行时目录，不得误入正式目录。

### 5.4 Runtime Evidence / Cache

运行时缓存与证据，例如：

- `.artifacts/trace/...`
- `.artifacts/cache/...`
- `.workflow/...`
- 运行日志、snapshot、manifest

这些文件属于 runtime 证据面。

## 6. Placement SSOT

### 6.1 Formal Placement Rule

正式 SSOT 文件的目录真值源固定为 runtime placement policy。

即：

- formal SSOT 放置规则必须由 runtime 的 placement resolver 统一回答
- workflow 和 agent 不得各自发明 formal SSOT 目录

### 6.2 Non-Formal Placement Rule

非正式产物新增一份公共 placement governance policy，统一定义：

- frozen bundle 该去哪里
- validation report 该去哪里
- review bundle 该去哪里
- transfer package 该去哪里
- run-scoped intermediate 该留在哪里

这份 policy 是 formal placement policy 的补充，而不是替代。

### 6.3 No Prompt-Only Rule

目录规则不得只存在于 prompt 中。

任何目录规范若要具备治理效力，必须至少进入以下之一：

- runtime placement policy
- 公共 contract
- 公共 governance policy
- validator / gate 逻辑

## 7. Run-Scoped Placement Manifest

### 7.1 Decision

每个产出步骤执行后，runtime 必须生成 placement manifest。

该 manifest 是“本次运行文件落点事实”的唯一审计输入。

### 7.2 Manifest Coverage

manifest 必须覆盖该 step 本次实际产生的所有文件，包括：

- formal SSOT materialization 结果
- declared outputs
- gate output files
- review / report / bundle 文件
- step 内部写出的中间文件

### 7.3 Minimum Fields

manifest 至少记录：

- `workflow_instance_id`
- `workflow_id`
- `run_id`
- `step_id`
- `file_path`
- `artifact_kind`
- `identity_kind`
- `ssot_type`
- `placement_key`
- `expected_dir`
- `actual_dir`
- `is_correct`
- `severity`
- `reason`

### 7.4 Source Priority

manifest 的判定信息优先级如下：

1. runtime materialized formal object metadata
2. `ssot_output_contract`
3. workflow step declared outputs
4. written files fallback detection

即：

- 先信 formal materialization
- 再信结构化输出契约
- 再信 workflow 声明
- 最后再对孤立文件做兜底分类

### 7.5 Storage

manifest 必须作为 run-scoped runtime evidence 落盘。

建议位置：

- `.artifacts/trace/placement/<workflow-instance-id>/<step-id>.json`

或等价 trace 目录。

不得将 placement manifest 直接写入 `spec/`。

## 8. Public Directory Audit Agent

### 8.1 Decision

新增公共 agent：

- `spec-global/core/agents/artifact-placement-reviewer/v1/agent.yaml`

### 8.2 Responsibility

该 agent 负责：

- 读取本次运行的 placement manifests
- 按统一目录规则审计文件落点
- 输出结构化目录审计报告
- 区分 blocker / major / minor 级别

### 8.3 Out of Scope

该 agent 不负责：

- 编排 workflow
- 自动移动文件
- 修改 runtime 写路径
- 自行生成 formal object
- 放宽目录约束

### 8.4 Why Common Agent

目录审计属于公共治理能力，而不是 product 私有语义。

因此应放在：

- `spec-global/core/agents`

而不是：

- `spec-global/departments/product/agents`

## 9. Requirement Chain Validation Integration

### 9.1 Decision

`requirement-chain-validation` 必须新增目录审计步骤。

建议顺序为：

1. `requirement_chain_test_execution`
2. `artifact_directory_audit`
3. `requirement_chain_review`
4. `requirement_chain_validation_gate`

### 9.2 Why This Order

该顺序可保证：

- 先完成需求链测试
- 再基于本次实际输出执行目录审计
- 然后由 review 同时看“链路质量 + 目录质量”
- 最后 gate 统一阻断

### 9.3 Gate Binding

`requirement_chain_validation_gate` 必须同时检查：

- requirement chain test 结果
- artifact directory audit 结果

若目录审计存在 blocker，则主流水线不得进入完成态。

## 10. Severity Model

### 10.1 Blocker

以下目录问题为 blocker：

- formal SSOT 主对象写入错误 canonical 目录
- 冻结 bundle / validation report / gate output 写入错误正式目录
- 中间文件误写入 `spec/`、`tests/`、`docs/reports/` 等正式目录并被视为正式产物
- 正式对象仅存在于 `step_workspace`，未物化到 canonical 目录

### 10.2 Major

以下问题默认为 major：

- review bundle 或 support package 放错非 canonical 但仍在允许输出区域
- 同一对象存在多个候选目录，造成主路径歧义
- `task_directory` 声明与实际落盘路径不一致，但未形成正式 gate 输出错误

### 10.3 Minor

以下问题默认为 minor：

- 命名或子目录组织不一致，但未破坏 canonical 识别
- 冗余中间文件保留在运行态目录，且未污染正式目录

## 11. Runtime Enforcement Strategy

### 11.1 Phase 1

第一阶段采用：

- 自动生成 placement manifest
- 公共 agent 审计
- gate 阻断

不做自动搬运，不做自动修复。

### 11.2 Phase 2

第二阶段对高风险对象启用 fail fast：

- formal SSOT 主对象
- 冻结 bundle
- validation gate output

即 runtime 在 materialization 时若发现关键对象目录错误，应直接失败，而不是等最终 review 才发现。

### 11.3 No Silent Rewrite Rule

未经显式设计，runtime 不得静默把 agent 错误写出的文件搬到“看起来更对”的位置。

原因：

- 会掩盖真实目录治理问题
- 会破坏可审计性
- 会制造 agent 已正确输出的假象

## 12. Canonical Directory Rules

### 12.1 Formal SSOT

formal SSOT 目录规则继续由 runtime placement resolver 回答。

任何 workflow / agent 中出现的 formal 目录说明，都只能作为解释，不得成为新的真值源。

### 12.2 Frozen Bundle / Validation Output

非 formal 但正式交付的产物必须有稳定 canonical 输出目录。

例如：

- validation 类产物归入 `output/validation/...`
- frozen package 类产物归入 `output/frozen-packages/...`
- transfer package 类产物归入 `output/...` 下的明确子目录

### 12.3 Step Intermediate

step 中间文件必须限定在当前 `step_workspace` 或 run-scoped runtime evidence 目录。

禁止：

- 写入其他 workflow instance 目录
- 写入历史 run 目录
- 写入正式 SSOT 内容目录

## 13. Existing Rule Consolidation

本 ADR 同时要求收敛现有零散规则。

### 13.1 Product Agent Rules

当前 product agent 中已有：

- `所有 changed_files 和写入路径都必须位于当前 step_workspace`
- `TASK 文件未落盘到 spec/tasks/<FEAT-ID>/ 则 revise`
- `task_directory 与落盘路径一致`

这些规则保留，但解释层级下沉：

- agent prompt 只保留行为提醒
- 真正阻断依据转为公共 placement governance + manifest audit

### 13.2 Formal SSOT Lint

当前 formal SSOT front matter lint 保留，作为全局静态检查。

但它不替代 run-scoped audit。

二者分工为：

- static lint: 扫描仓库当前 formal 文件是否放错目录
- run-scoped audit: 审计本次 workflow 运行是否把文件放对

## 14. TASK Directory Consistency

当前仓库在 TASK canonical 目录表达上存在潜在不一致。

一部分 workflow / agent 表达为：

- `spec/tasks/<FEAT-ID>/`

而 runtime formal placement 可能根据 `src_root_id` 推导更深层目录。

### 14.1 Decision

本 ADR 要求在实施本方案时，同步收敛 TASK canonical 目录规则，只保留一个真值口径。

### 14.2 Rule

在单一真值口径未确定前：

- 不允许继续扩散新的 TASK 目录写法
- requirement-chain-validation 的目录审计必须以最终统一规则为准

该规则收口是本 ADR 的强关联实施项。

## 15. Contracts and Review Output

### 15.1 New Contract Surface

目录审计能力至少需要新增或扩充以下结构化契约之一：

- artifact placement audit report contract
- placement manifest contract

### 15.2 Review Output Shape

目录审计报告至少应输出：

- `audit_id`
- `workflow_instance_id`
- `summary`
- `blockers`
- `majors`
- `minors`
- `misplaced_files`
- `missing_expected_files`
- `unexpected_formal_files`
- `decision`

### 15.3 Decision Values

建议 decision 至少支持：

- `pass`
- `revise`
- `reject`

其中：

- 出现 blocker 时不得为 `pass`

## 16. Governance Boundaries

本方案的维护边界固定如下：

- workflow 结构接入由 workflow-spec-maintainer 约束
- 公共 agent 规范由 agent-spec-maintainer 约束
- placement / audit contract 由 contracts-spec-maintainer 约束
- 最终 spec 工程质量由 spec-review 约束

不得将该目录审计 agent 扩展为 runtime orchestrator 替身。

## 17. Migration Plan

### 17.1 Phase A

建立治理骨架：

- placement manifest contract
- artifact-placement-reviewer agent
- requirement-chain-validation workflow 接入

### 17.2 Phase B

打通 runtime：

- 记录本次 step 的 written files
- 生成 placement manifest
- 在 final validation review 中读取 manifest

### 17.3 Phase C

收紧执行：

- formal object fail fast
- gate 对目录 blocker 强阻断
- 清理旧的 prompt-only 目录规则

## 18. Consequences

### 18.1 Positive

- 需求链最终校验从“只看语义”升级为“语义 + 目录治理”
- formal 与 non-formal 产物都能回答“应该放哪”
- 每次运行都有完整文件落点审计证据
- 公共能力可被其他 workflow 复用

### 18.2 Trade-Offs

- runtime 需要增加 manifest 生成逻辑
- workflow 需要增加一步审计
- 初期会暴露更多历史不一致
- 部分旧 prompt 规则要改为引用公共治理规则

## 19. Follow-up

后续实施必须继续完成：

1. 新增 `artifact-placement-reviewer` 公共 agent
2. 新增 placement manifest / audit report contract
3. 在 runtime 中生成 run-scoped placement manifest
4. 将 `requirement-chain-validation` 接入目录审计步骤
5. 将 gate 绑定目录 blocker
6. 收口 `TASK` canonical 目录真值规则
7. 为 formal placement 与 non-formal placement 增加自动化测试
