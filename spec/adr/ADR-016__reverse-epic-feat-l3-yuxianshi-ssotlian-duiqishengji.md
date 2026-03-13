---
id: ADR-016
ssot_type: adr
title: reverse-epic-feat-l3 与现行 SSOT 链对齐升级
status: frozen
version: v1
parent_id: null
derived_from_ids:
- id: ADR-001
  version: v1
- id: ADR-003
  version: v1
- id: ADR-006
  version: v1
- id: ADR-012
  version: v1
source_refs: []
owner: governance
tags:
- ssot
- reverse-ssot
- workflow
- core
- governance
properties:
  adr_kind: workflow_design
  decision_scope: core_reverse_ssot_chain_upgrade
frozen_at: '2026-03-13T21:45:57.853155'
---

# reverse-epic-feat-l3 与现行 SSOT 链对齐升级

## 1. Decision

LEE 采纳对 `core` 下现有 `reverse-epic-feat-l3` 工作流进行对齐升级，使其不再只是“EPIC/FEAT 逆向器”，而是“现行 SSOT 文档体系逆向入口”。

本 ADR 冻结以下方向：

- 继续保留当前 workflow key `core.reverse-epic-feat`，但其 canonical 语义升级为“面向现行 SSOT 链的逆向文档工作流”。
- 升级后的 canonical 逆向范围至少覆盖：
  - `repo evidence -> SRC reverse pack -> EPIC -> FEAT -> delivery prep seeds -> QA handoff seeds -> trace / evidence views`
- `SRC / EPIC / FEAT` 允许在 review / gate 通过后物化为正式对象。
- `UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI` 在本工作流中默认只逆向生成 seed、view、index 或 handoff 文档，不直接越权物化为正式主对象。
- 现有“只产出 EPIC / FEAT”的行为保留为兼容模式，而不再是长期 canonical 目标。

## 2. Context

当前仓库中的 `reverse-epic-feat-l3` 仍然明确按旧边界实现：

- `config/workflow-registry.yaml` 将 `core.reverse-epic-feat` 描述为“反向生成 EPIC/FEAT SSOT 工作流”。
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml` 在 description、boundary、output_contract 中都把输出限定为 `EPIC / FEAT`。
- `scripts/reverse_epic_feat.py` 的 `run_materialize()` 只写入 `epic` 与 `feat` 两类输出。
- 同脚本的 `run_review()` 明确阻断除 `epic` / `feat` 之外的 `ssot_type`。

但项目级正式 SSOT 设计已经前移：

- `ADR-003` 已冻结产品主链为 `raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`
- `ADR-012` 已将 `raw -> SRC` 与 `SRC -> EPIC` 拆分为两个独立 workflow 责任层
- `ADR-006` 已冻结 workflow-first 与 materialization 分层边界
- `spec-global/SSOT_CONTRACT_CHAIN.md` 已将当前文档体系固定为：
  - `SRC -> EPIC -> FEAT -> UI / TECH / TASK / TESTSET -> TC -> REPORT / BUG -> EVI`
  - `ADR` 作为独立 decision SSOT 链存在

这意味着：

- 现有 core reverse workflow 的对象边界已经落后于项目真实 SSOT 链
- 它当前只能逆向一段中间链路，无法完整支撑“当前文档体系”的回填、重建、审计和迁移

## 3. Problem

### 3.1 Reverse Scope 过窄

当前 workflow 从命名到实现都把逆向目标锁定在 `EPIC / FEAT`。

这会导致：

- `SRC` 缺位，无法回填主链正式源头
- `delivery prep` 侧的 `UI / TECH / TASK` 没有逆向文档种子
- `QA` 侧 `TESTSET` 与后续 `TC / REPORT / BUG / EVI` 只能留在链外

结果是：即使逆向跑通，也只能得到中段文档，而不是“当前 SSOT 链文档体系”。

### 3.2 Canonical Path 与 Canonical Object 不一致

现有模板和脚本把逆向输出集中写入：

- `spec/requirements/feature-registry.md`
- `spec/requirements/*.md`
- `docs/reports/reverse-epic-feat-*.json|md`

但现行链路已经要求：

- `SRC` 进入 `spec/source/`
- `EPIC` 进入 `spec/requirements/epics/`
- `FEAT` 进入 `spec/requirements/features/`
- 下游对象进入其各自 canonical 路径或至少生成对应 seed/view

如果 reverse workflow 继续沿用旧放置模型，就会把“已升级的对象体系”重新压回“旧目录心智”。

### 3.3 Governance Boundary 不完整

按 `ADR-006` 和 `FEAT-148` 的边界，workflow 负责治理流程，SSOT 原语负责最终物化。

当前 reverse workflow 只解决了：

- repo evidence 扫描
- capability / feature 拆解
- EPIC / FEAT bundle 物化与 review

但没有解决：

- 哪些逆向结果可以直接成为 formal object
- 哪些结果只能作为下游 workflow 的 seed
- 如何把当前链路中的 `governing_adrs / decision_refs / source freeze refs` 注入逆向结果

这会让“逆向文档体系”在治理上重新变成一半 formal、一半隐式推断的混合态。

### 3.4 Review Contract 仍然绑定旧世界

当前 review 规则默认检查：

- 只允许 `epic / feat`
- FEAT 必须带 evidence_layers / primary_refs
- 只产出 `reverse-epic-feat-review.json`

它没有检查：

- `SRC` 是否被正确建立为正式上游
- `delivery prep seeds` 是否满足 `UI / TECH / TASK` 下游最小输入
- `qa handoff seeds` 是否足够支持 `TESTSET` 派生
- evidence views 是否覆盖 `REPORT / BUG / EVI` 的回填入口

因此 review 通过，并不等价于“当前 SSOT 文档体系可被完整逆向”。

## 4. Target Upgrade

### 4.1 Canonical Reverse Boundary

升级后的 `core.reverse-epic-feat` 应采用以下 canonical 逆向边界：

`repo evidence -> reverse source pack -> SRC draft/freeze -> EPIC -> FEAT -> delivery prep seeds -> qa handoff seeds -> evidence/trace views`

其中对象职责固定为：

- `SRC / EPIC / FEAT`
  - formal reverse object
  - 允许在 gate 后落为正式对象
- `delivery prep seeds`
  - 为 `UI / TECH / TASK` 提供逆向文档基础
  - 默认不直接替代下游正式对象
- `qa handoff seeds`
  - 为 `TESTSET` 生成提供最小输入
  - 默认不直接替代 QA 正式对象
- `evidence / trace views`
  - 用于索引 `TC / REPORT / BUG / EVI` 相关事实
  - 提供映射与回填入口，不直接越权 freeze

### 4.2 Stage Shape

建议将现有 stage 升级为以下结构：

1. `evidence_scan`
   - 收集代码、文档、测试、运行产物
2. `source_reconstruction`
   - 归纳 raw inputs、问题空间、约束、成功标准
   - 生成 reverse source pack 与 `SRC candidate`
3. `source_review_and_freeze`
   - review `SRC`
   - freeze formal `SRC`
4. `epic_modeling`
   - 从冻结 `SRC` 生成 `EPIC`
5. `feat_modeling`
   - 从 `EPIC` 生成 `FEAT`
6. `delivery_prep_seed_generation`
   - 为每个 `FEAT` 逆向生成 `UI / TECH / TASK` seed
7. `qa_seed_and_evidence_views`
   - 生成 `TESTSET seed`
   - 输出 `TC / REPORT / BUG / EVI` 对应的 evidence views / coverage views
8. `chain_review_and_publish`
   - 统一 review、gate、publish/freeze

### 4.3 Output Model

升级后输出不再只有一个 `reverse-epic-feat-ssot-output.json`，而应升级为：

- `reverse-source-pack.json`
- `reverse-src-ssot-output.json`
- `reverse-epic-feat-ssot-output.json`
- `reverse-delivery-prep-seed.json`
- `reverse-qa-handoff-seed.json`
- `reverse-evidence-view.json`
- `reverse-ssot-chain-manifest.json`
- `reverse-ssot-chain-review.json`
- `reverse-ssot-chain-completion.md`

其中 manifest 作为统一索引，必须明确：

- 本次逆向覆盖了哪些链路层级
- 哪些是 formal object
- 哪些只是 seed/view
- 每个输出引用哪些 `source_refs / primary_refs / decision_refs`

## 5. Formality Boundary

### 5.1 What This Workflow May Materialize

本工作流在 canonical 模式下只直接物化：

- `SRC`
- `EPIC`
- `FEAT`

理由：

- 这三类对象属于当前 reverse 需求建模主线
- 它们可由 repo evidence 与文档证据较稳定回推
- 它们与 `ADR-003` / `ADR-012` 的主链边界一致

### 5.2 What This Workflow Must Not Directly Freeze

本工作流默认不得直接 formalize：

- `UI`
- `TECH`
- `TASK`
- `TESTSET`
- `TC`
- `REPORT`
- `BUG`
- `EVI`

理由：

- `UI / TECH / TASK` 应由 `feat-to-delivery-prep` 体系承接
- `TESTSET / TC / REPORT / BUG` 应由 QA 体系承接
- `EVI` 属于事实快照，不应由 reverse workflow 冒充生产

因此 reverse workflow 对这些层级的职责是：

- 生成 seed
- 生成 coverage / trace / mapping view
- 生成下游 workflow 的标准输入包

而不是直接替代下游正式治理流程。

## 6. Contract Changes

### 6.1 Input Contract

建议新增以下参数：

- `reverse_scope`
  - `legacy_epic_feat | src_epic_feat | full_ssot_docs`
- `materialize_formal_objects`
  - 默认只允许 `src,epic,feat`
- `emit_delivery_prep_seeds`
  - 是否输出 `UI / TECH / TASK` seeds
- `emit_qa_handoff_seeds`
  - 是否输出 `TESTSET` seed 与 QA handoff 文档
- `emit_evidence_views`
  - 是否输出 `TC / REPORT / BUG / EVI` 相关索引视图
- `governing_adrs`
  - 注入项目级正式决策

兼容策略：

- `objective: reverse_epic_feat` 在第一阶段保留
- 但内部执行可根据 `reverse_scope` 进入新 stage

### 6.2 Output Contract

建议新增统一 contract，至少具备：

- `artifact_key`
- `artifact_kind`
  - `formal_object | seed | view | manifest | review_report`
- `ssot_type`
  - formal object 才必填
- `chain_layer`
  - `source | epic | feat | delivery_prep_seed | qa_seed | evidence_view`
- `parent_refs`
- `derived_from_ids`
- `source_refs`
- `primary_refs`
- `decision_refs`
- `placement_path`
- `materialization_status`

### 6.3 Review Contract

review 规则必须从“只审 EPIC / FEAT”升级为“审整条 reverse chain”：

- `SRC` 是否具备目标、约束、成功标准
- `EPIC / FEAT` 父子关系是否正确
- `delivery prep seed` 是否满足下游 `UI / TECH / TASK` 的最小输入
- `qa handoff seed` 是否满足 `TESTSET` 生成最小输入
- evidence views 是否可追溯到实际文件和运行事实
- formal / seed / view 边界是否被明确标注

## 7. Implementation Surfaces

后续实施至少会涉及以下 canonical 面：

- `config/workflow-registry.yaml`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.design.md`
- `scripts/reverse_epic_feat.py`
- `spec-global/core/contracts/`
  - 新增或扩展 reverse source / seed / manifest / review contract
- `tests/test_reverse_epic_feat_review_schema_source.py`
- 与 reverse workflow 相关的 CLI / help / skill 说明

如需兼容旧调用方，应将兼容逻辑显式收敛在 template 参数与 contract 适配层，避免复制第二套 workflow。

## 8. Rollout

### Phase 1: 兼容扩展

- 保留 `core.reverse-epic-feat`
- 引入 `reverse_scope`
- 补 `SRC` 与 manifest 输出
- 保持默认行为仍可兼容旧 `EPIC / FEAT` 调用

### Phase 2: 全链文档化

- 增加 `delivery prep seed`
- 增加 `qa handoff seed`
- 增加 `evidence views`
- review 改为面向整条链

### Phase 3: Canonical Default 切换

- 将 `full_ssot_docs` 升级为默认模式
- 旧 `legacy_epic_feat` 只保留兼容语义
- 更新 skill、CLI help、demo 和测试叙事

## 9. Non-Goals

本 ADR 当前不直接决定：

- 直接 reverse 出 `RELEASE / DEVPLAN / TESTPLAN`
- 由 core reverse workflow 直接替代 `feat-to-delivery-prep` 或 `qa.test-set-production`
- 将 evidence views 直接提升为正式事实对象
- 删除现有 `core.reverse-epic-feat` key

这些应由后续 workflow / contract / runtime 变更单独承接。

## 10. Upgrade Plan Summary

建议按以下顺序实施：

1. 先升级 workflow template 与 design note，冻结新边界
2. 再升级 `scripts/reverse_epic_feat.py` 的 stage、bundle 和 review 逻辑
3. 补 reverse source / seed / manifest contracts
4. 调整输出路径到当前 canonical 目录
5. 增加兼容模式测试与整链 review 测试
6. 最后再更新 CLI、技能说明和迁移文档

## 11. Final Rule

关于 `reverse-epic-feat-l3`，本 ADR 固定三条规则：

- 它必须对齐现行 SSOT 链，而不是继续停留在旧 EPIC/FEAT-only 语义。
- 它必须明确区分 formal object、seed、view，不能借“逆向补文档”越权改写治理边界。
- 它必须把当前链路的正式对象体系完整表达出来，否则不能再被描述为“当前 SSOT 链的逆向工作流”。
