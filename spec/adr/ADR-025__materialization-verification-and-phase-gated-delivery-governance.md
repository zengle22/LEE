---
id: ADR-025
ssot_type: adr
title: Materialization Verification 与 Phase-Gated Delivery Governance
status: draft
version: v1
parent_id: null
derived_from_ids:
  - id: ADR-011
    version: v1
  - id: ADR-017
    version: v1
  - id: ADR-020
    version: v1
  - id: ADR-021
    version: v1
  - id: ADR-024
    version: v1
source_refs: []
owner: governance
tags: [governance, workflow, materialization, verification, fitness, gate, evidence, integration]
workflow_instance_id: adr-025-governance
properties:
  adr_kind: governance_design
  decision_scope: materialization_verification_and_phase_gated_delivery
  governs:
    - spec-global/departments/product/workflows/templates/requirement-chain-validation
    - src/lee/orchestrator/execution/artifacts/chain_testing.py
    - src/lee/orchestrator/execution/receipt.py
    - src/lee/orchestrator/execution/gate_engine.py
    - src/lee/cli/commands/verify.py
---

# Materialization Verification 与 Phase-Gated Delivery Governance

## 1. Decision

LEE 建立一条覆盖“分析、设计、实现、物化、验证”的统一交付治理规则，用于约束任何会声称“已完成”“可交付”“可 handoff”“可验证通过”的 workflow、gate、fitness 与 evidence 流程。

本 ADR 冻结以下决策：

1. LEE 不再接受“生成了 spec / patch / report / receipt”即等价于“交付成立”的弱语义。
2. LEE 明确区分：
   - `IR / formal object`：设计对象、规范对象、计划对象、补丁对象、报告对象
   - `materialized result`：被真实消费者、真实执行器或真实后端实际消费后的结果
   - `verification result`：对 materialized result 进行内容级、语义级、结构级验证后的结论
3. 任何试图进入完成态、冻结态、handoff-ready 或 review-pass 的主链 workflow，必须经过 phase gating，不得直接从“实现”跳到“宣布完成”。
4. `exit code = 0`、文件存在、receipt 完整、格式可解析，这些都只能作为局部信号，不能单独构成完成证明。
5. LEE 对外部能力集成采用“优先依赖真实系统的稳定表面，而不是在仓库内重写等价能力”的原则。
6. 当某条 workflow 的完成主张依赖真实工具、真实运行时或真实消费者时，缺依赖应视为阻断失败，而不是静默降级为“部分通过”。

## 2. Context

LEE 当前已经具备若干重要治理能力：

- workflow-first 的阶段化执行入口
- receipt 与 verify 机制
- gate 与 human approval 机制
- artifact placement 与 requirement chain testing
- fitness function 作为完成条件防腐层的方向

但这些能力之间仍存在一个关键空洞：

- 系统能证明“跑过什么”
- 系统能证明“写出了什么”
- 系统能证明“文件没被篡改”

却未总能证明：

- 下游真实消费者是否真的吃到了结果
- 所谓“完成”是否只是中间表示被修改，而不是最终交付物发生了可信变化
- 某个 workflow 的输出是否只停留在 formal object / report / patch 层

这会导致典型的 AI 交付误判：

- 生成了 patch，但没有验证真实运行路径
- 生成了 delivery prep，但没有验证是否可被下游开发或验证链真实消费
- 生成了 validation report，但 report 所依据的结果只证明命令执行过，不证明交付语义成立
- 生成了 receipt，但 receipt 只证明记录完整，不证明结果正确

因此，LEE 当前缺的不是更多“文件生成能力”，而是一条把“实现结果”推进到“真实物化结果”和“内容级验证结果”的统一治理链。

## 3. Problem Statement

### 3.1 Formal Object Is Not Delivery Proof

在 LEE 中，`SRC / EPIC / FEAT / TASK / TESTSET / report / patch / review summary` 都是有价值的正式对象，但它们主要承担：

- 表达约束
- 描述设计
- 记录执行
- 传递上下文

它们不天然等于：

- 真实消费者可用
- 真实工具链可跑
- 真实后端已体现预期变化

若系统不显式承认这层差异，就会把“IR 已更新”误判为“交付已成立”。

### 3.2 Receipt Integrity Is Not Semantic Validity

当前 receipt 与 verify 机制更接近：

- 执行轨迹收据
- 输入输出摘要
- 完整性与追溯性证明

这很重要，但不回答以下问题：

- 输出内容是否符合完成条件
- 目标消费者是否能正确读取
- 关键行为是否真的发生
- 所谓“通过”是否只是脚本没有报错

因此，完整性验证与语义验证不能混为一谈。

### 3.3 Workflow Phases Exist, But Completion Semantics Are Still Too Weak

LEE 已具备 phase / step / gate 结构，但并非所有关键 workflow 都明确要求：

1. 先分析真实能力边界与消费者边界
2. 再设计 artifact contract 与验证计划
3. 再生成 IR 或实现产物
4. 再触发真实 materialization
5. 再做内容级验证并供 gate / fitness / supervisor 消费

缺少这个统一骨架时，phase 只是编排顺序，不一定形成完成语义。

### 3.4 Reimplementation Creates Toy Success

当 workflow 需要借助外部工具、外部系统或已有 runtime 时，若选择在 LEE 仓库内重写一个“近似能力”，会出现：

- 本地测试看似通过
- 真实系统行为却不一致
- 结果只对 demo 成立，不对真实工作负载成立

这会让治理系统误把“玩具级成功”当成“生产级完成”。

## 4. Scope

### 4.1 In Scope

- 所有会进入 `completed / frozen / handoff-ready / validation-pass` 的 workflow
- requirement-chain-validation 及其后续演化
- delivery prep 之后与完成主张相关的 gate / fitness / evidence 流程
- receipt、verification、fitness、gate 之间的完成语义分工
- 外部真实系统集成时的最小治理规则

### 4.2 Out Of Scope

- 用本 ADR 直接冻结最终 contract/schema 细节
- 替代 human approval 或 supervisor judgment
- 要求所有只读分析 workflow 都执行真实 materialization
- 一次性改造全部历史 workflow

## 5. Canonical Delivery Semantics

### 5.1 Five-Layer Completion Path

LEE 将“可完成交付”的最小路径统一定义为五层：

1. `analysis`
   - 识别真实消费者、真实执行面、真实完成条件、失败模式
2. `design`
   - 定义 contract、输出对象、验证方法、gate/fitness 消费方式
3. `implementation`
   - 生成 formal object、patch、plan、config、report 或调用脚本
4. `materialization`
   - 通过真实系统、真实执行器、真实消费者、真实 backend 产出可被消费的结果
5. `verification`
   - 对 materialized result 做内容级、结构级、语义级验证

未经过第 4 层与第 5 层的流程，不得声称“交付已成立”。

### 5.2 What Counts As Materialization

materialization 不等于“又写了一个文件”。

它必须满足以下至少一项：

- 被真实 CLI / runtime / backend / downstream tool 成功消费
- 产出了真实消费者会使用的输出
- 经过了真实渲染、真实执行、真实装配、真实回放或真实导出

示例：

- requirement-chain-validation 中，生成 report.json 只是实现层；report 所引用的测试执行结果才属于 materialization 证据的一部分
- 开发交付中，生成 patch 只是实现层；测试、smoke、运行路径、构建物、集成调用结果才是 materialization
- 文档/发布链中，生成 Markdown 只是实现层；平台兼容导出、渲染结果或真实导入结果才属于 materialization

### 5.3 What Counts As Verification

verification 不等于“命令成功退出”。

verification 至少应包含以下一种或多种：

- 结构验证：schema、关键字段、引用闭包、完整性
- 语义验证：关键行为、状态变化、下游消费结果
- 内容验证：关键文本、关键数值、像素/字节/探针结果
- 运行验证：smoke、replay、integration、real backend execution

## 6. Governance Rules

### 6.1 No IR-Only Completion Claim

以下对象单独存在时，不得作为完成证明：

- formal SSOT 文件
- patch
- review summary
- receipt
- scorecard
- report
- gate input bundle

它们只能作为完成链的一部分输入。

### 6.2 No Exit-Code-Only Success

LEE 不接受以下弱判定方式作为最终通过依据：

- 仅根据 `exit code == 0`
- 仅根据输出文件存在
- 仅根据 receipt 校验通过
- 仅根据 agent 自述“已完成”

若 workflow 仍采用上述判定，应视为治理缺口。

### 6.3 Prefer Real Consumer Surfaces

当 workflow 依赖外部能力时，优先级如下：

1. 稳定公开的真实 CLI / API / file format / runtime
2. 稳定的正式 contract surface
3. 最小薄封装
4. 仓库内重写等价能力

其中第 4 项默认不推荐，除非真实系统不存在可用表面，且该重写不承担“完成证明”的职责。

### 6.4 Missing Real Dependency Must Fail Fast

若某条完成主张依赖真实工具链，则：

- 缺少依赖时应阻断
- 不得自动改为 mock pass
- 不得把“未验证”包装为“已通过”

允许的例外只有：

- 该 workflow 明确是分析态或设计态
- 输出状态被显式标记为 `draft / unverified / analysis_only`

## 7. Gate, Fitness, Evidence, Receipt Boundaries

### 7.1 Receipt Boundary

receipt 负责：

- 记录执行事实
- 记录输入输出摘要
- 记录完整性与追溯

receipt 不负责：

- 宣布语义正确
- 宣布 materialization 已成立
- 宣布完成条件已满足

### 7.2 Evidence Boundary

evidence pack 必须同时容纳三类证据：

- implementation evidence
- materialization evidence
- verification evidence

若 evidence pack 仅包含实现层证据，应显式标记为不完整。

### 7.3 Fitness Boundary

fitness function 负责聚合完成条件，但不得把“缺少 materialization / verification”静默折叠为普通 warning。

对完成主张直接相关的路径：

- materialization 缺失应至少成为 hard gate 或 blocker 级信号
- verification 缺失应至少成为 hard gate 或 blocker 级信号

### 7.4 Gate Boundary

gate 主要负责：

- 阻断
- 升级
- 审批
- 接受或拒绝风险

gate 不应重新发明 materialization 逻辑或 verification 逻辑；它应消费结构化结果，而不是临时解释散落日志。

## 8. Minimum Output Objects

本 ADR 不冻结最终 schema，但冻结最小对象语义。

### 8.1 materialization_result

任何关键 workflow 若宣称“已交付”，应能提供 `materialization_result`，至少表达：

- `subject_refs`
- `consumer_surface`
- `executor_surface`
- `input_refs`
- `output_refs`
- `observed_effects`
- `status`
- `failure_mode`

### 8.2 verification_result

任何关键 workflow 若宣称“已验证”，应能提供 `verification_result`，至少表达：

- `subject_refs`
- `checks`
- `check_runs`
- `assertions`
- `evidence_refs`
- `unverified_items`
- `final_status`

### 8.3 Completion Binding Rule

主链完成态至少应绑定：

- formal object refs
- materialization_result
- verification_result
- gate / fitness / supervisor 所消费的结论对象

缺一时，默认不得闭环。

## 9. Workflow Integration Decision

### 9.1 Requirement Chain Validation

`requirement-chain-validation` 继续保留测试执行、评审、门禁三段式，但其治理语义应升级为：

- 测试执行阶段负责产出可审计的 verification evidence
- 评审阶段负责确认 blocker 清零与未验证项暴露
- 门禁阶段消费结构化结果，而不是只消费“是否生成报告”

### 9.2 Delivery Prep And Dev Completion Paths

凡是从 `FEAT / TASK / TESTSET / code patch / test execution` 走向“可 handoff / 可完成”的路径，都应显式补齐：

- 哪个结果只是 IR
- 哪个步骤是真实 materialization
- 哪个步骤做 semantic verification

### 9.3 Read-Only Analysis Workflows

只读分析 workflow 可以停留在 analysis / design 层，但必须：

- 明确标记自己不构成完成证明
- 不得输出模糊的“已完成交付”话术

## 10. P0 And P1 Decision

### 10.1 Overall Classification

本能力整体归类为 `P1`。

理由：

- LEE 并非完全没有验证、gate、receipt、evidence
- 当前问题是完成语义过弱，容易误把实现层结果当作交付层结果
- 这是治理收紧与语义升级，不是零到一补洞

### 10.2 P0 Slice

以下最小切片应视为 `P0`：

- 所有会宣布 `completed / frozen / handoff-ready` 的主链 workflow，不得缺少 materialization 或 verification 语义
- requirement-chain-validation 不得把“生成 report”误当作“验证通过”
- verify / receipt 相关用户口径不得继续暗示“完整性验证 = 结果正确”

## 11. Rejected Alternatives

### 11.1 Receipt As Completion Proof

不采纳。

原因：

- receipt 证明的是可追溯性，不是结果语义

### 11.2 Human Review Alone

不采纳。

原因：

- 人工 review 可以兜底，但不能替代结构化 materialization 与 verification 输出

### 11.3 Reimplement Downstream Logic Inside LEE

默认不采纳。

原因：

- 容易制造 toy success
- 会模糊真实完成边界
- 长期维护成本高于薄封装真实系统

## 12. Consequences

采纳本 ADR 后，LEE 将获得以下收益：

- 完成主张从“文件写出来了”升级为“真实结果已物化且已验证”
- gate、fitness、evidence、receipt 的职责边界更清晰
- 真实系统集成的治理口径统一
- 主链 workflow 更难出现“看起来完成、实际上未交付”的误判

同时也会引入成本：

- 更多 workflow 需要补 materialization / verification 步骤
- 一些过去的“轻量通过”会被升级为阻断失败
- 需要新增结构化结果对象与测试/校验规则

## 13. Follow-Up

本 ADR 后续应推动但尚未在本文冻结的事项包括：

1. 定义 `materialization_result` 与 `verification_result` 的正式 contract
2. 将 requirement-chain-validation 的 gate 输入从“报告存在”升级为“结构化验证结果存在且 blocker 清零”
3. 评估 `verify` 命令的命名与输出语义，避免把 receipt verification 表述为结果验证
4. 将关键 workflow 的 phase definition 明确补齐到模板或 runtime 约束中
5. 将 materialization / verification 缺失纳入 fitness hard gate
