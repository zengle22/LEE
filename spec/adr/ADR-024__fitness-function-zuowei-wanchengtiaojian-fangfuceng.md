---
id: ADR-024
ssot_type: adr
title: Fitness Function 作为完成条件防腐层
status: draft
version: v1
parent_id: null
derived_from_ids:
  - id: ADR-011
    version: v1
  - id: ADR-015
    version: v1
  - id: ADR-017
    version: v1
  - id: ADR-020
    version: v1
  - id: ADR-021
    version: v1
source_refs: []
owner: governance
tags: [governance, ai-delivery, fitness, completion, gate, evidence, verifier]
workflow_instance_id: wf-adr-024-20260317
properties:
  adr_kind: governance_design
  decision_scope: fitness_function_as_completion_anti_corruption_layer
---

# Fitness Function 作为完成条件防腐层

## 1. Decision

LEE 采纳 `Fitness Function` 方向，但其定位不是替代现有 `gate / evidence / verifier / supervisor` 体系，而是在它们之前补上一层仓库内声明、统一执行、可审计回写的“完成条件防腐层”。

本 ADR 冻结以下决策：

- `Fitness Function` 的职责是把“任务完成条件”从经验判断收敛为仓库内可执行规则。
- Fitness 必须以仓库正式对象或正式规则文件存在，不能只散落在 prompt、CI 配置或人工记忆中。
- Fitness 运行结果本身不直接宣布完成，只能产出 `fitness_result` 并作为 gate、evidence pack 和 supervisor review 的输入。
- LEE 不采纳“Markdown frontmatter 作为唯一真源”的弱结构方案；正式真源应为 schema-friendly 的 YAML/JSON/SSOT 对象，Markdown 可作为人读视图。
- 优先级判断采用两级结论：
  - 整体能力建设归类为 `P1`
  - 与完成误判直接相关的最小阻断切片归类为 `P0`

## 2. Context

LEE 当前已经具备较强的交付治理基础：

- 已有 gate 语义与审批边界
- 已有 evidence pack 与证据引用约束
- 已有 verifier 与 completion checker
- 已有 supervisor gate 思想，强调生成者不能自证完成
- 已在需求链一致性测试、执行性评估、CLI/CI 接入等方向持续推进

但当前仍存在一个中间层缺口：

- gate 更像消费已有上下文的判定器，不是仓库级规则扫描与采样执行器
- verifier 多聚焦单类验证对象，不等于“完成条件统一执行层”
- completion 相关规则散落在 ADR、gate、testset、文档和局部代码里
- evidence 能证明“跑过什么”，但未必统一表达“哪些条件必须满足才算完成”

这会带来一个典型 AI 时代问题：

- agent 容易把“代码写了”“局部测试过了”“报错没了”误读为“任务完成”

因此，LEE 缺的不是 gate，也不是测试本身，而是一层把“完成条件”显式声明、统一执行、回写证据并供下游消费的收口机制。

## 3. Problem

### 3.1 Completion Semantics Are Still Distributed

当前完成语义分散在：

- gate rules
- integration threshold 文档
- testset
- evidence pack 约束
- agent 提示与 reviewer 心智

这会让系统知道很多局部规则，但仍然缺少统一的完成条件入口。

### 3.2 Existing Gates Mainly Consume Results Rather Than Produce Them

当前 gate 更适合做：

- 阻断
- 升级
- 审批
- freeze / reject / revise 决策

但不适合直接承担：

- 扫描仓库规则文件
- 执行命令采样
- 聚合多维度完成条件
- 产出统一 `fitness_result`

### 3.3 Evidence Exists But Completion Proof Is Not Yet Unified

存在证据，不等于存在完成证明。

系统仍可能出现以下状态：

- evidence 很多，但审阅者仍要自己拼接是否真的闭环
- 某些 hard gate 已失败，但未被统一归纳到“不能退出循环”
- 某些关键未验证项未进入统一审查对象

## 4. Positioning Decision

LEE 对 Fitness 的正式定位如下：

```text
repo rules
  -> fitness runner
  -> fitness_result
  -> evidence pack / gate / supervisor
  -> completion decision
```

因此：

- Fitness 不是新的审批系统
- Fitness 不是新的 evidence 系统
- Fitness 不是新的 review 角色
- Fitness 是“完成条件执行层”

它负责把规则解释权从分散文本和人工经验中收回来，交给统一执行器。

## 5. Scope

### 5.1 In Scope

- 完成条件的仓库内声明方式
- 多维度 fitness 规则的统一执行入口
- hard gate 与 score/warn 规则分层
- `fitness_result` 的结构化输出
- fitness 与 gate、evidence pack、supervisor 的对接
- CLI / CI 的最小接入面

### 5.2 Out Of Scope

- 用 fitness 替代人工 approval
- 用 fitness 替代需求链测试体系全部能力
- 在本 ADR 中冻结最终数据库 schema
- 在本 ADR 中冻结最终 UI 控制台形态
- 一次性迁移全部历史 gate / verifier / testset

## 6. Canonical Form Decision

LEE 不采用“仅把 Markdown frontmatter 作为 fitness 真源”的方案。

正式口径如下：

- canonical 规则对象应放在正式治理目录中
- 规则对象应优先使用 machine-readable 结构
- Markdown 说明可作为镜像说明文档，但不应成为唯一执行真源

推荐落点方向：

- `spec/fitness/`
- 或 `spec-global/departments/dev/contracts/fitness-rule/`
- 或由正式 contract/schema 驱动的规则目录

最低要求：

- 每个规则必须有稳定 ID
- 每个规则必须声明 dimension、severity、execution method、evidence binding
- 每个规则必须可被 runner 和 gate 同时消费

## 7. Fitness Model

### 7.1 Rule Classes

LEE 统一将 fitness 规则分为两类：

1. `hard_gate`
   - 任一失败都阻断当前完成主张
2. `quality_signal`
   - 进入评分、警告或趋势观察，但不单独定义完成

### 7.2 Minimum Dimensions

第一阶段至少支持以下维度：

- `contract_consistency`
- `testability`
- `integration_closure`
- `evidence_completeness`
- `path_governance`

### 7.3 Output Object

fitness 统一输出 `fitness_result`，至少包括：

- `subject_refs`
- `dimension_results`
- `hard_gate_results`
- `warnings`
- `command_runs`
- `evidence_refs`
- `summary`
- `final_status`

其中：

- `final_status` 只表示 fitness 层结论
- 不直接等价为 workflow completion

## 8. Integration Decision

### 8.1 With Gate

Fitness 不替代 gate，而是成为 gate 的上游输入。

最小规则：

- hard gate 失败必须可被 auto gate 直接消费
- gate 不再自行重复解释 fitness 规则正文
- gate 主要负责阻断、升级和决策，不负责再次发明采样逻辑

### 8.2 With Evidence Pack

Fitness 结果必须进入 evidence pack。

最低要求：

- evidence pack 必须可引用 `fitness_result`
- `command_runs` 或 tester 输出必须可追溯
- 未验证项必须显式暴露，而不是只记录通过项

### 8.3 With Supervisor

Supervisor 仍保留最终独立关闭边界。

规则如下：

- `fitness_result = pass` 不自动等于 `PASS`
- supervisor 必须继续审查未验证风险、影响面和关闭边界
- 任何试图用 fitness 取代 supervisor 的设计都不采纳

## 9. P0 And P1 Decision

### 9.1 Overall Classification

本能力整体归类为 `P1`。

理由：

- LEE 当前并非没有 gate、verifier、evidence 或 completion checker
- 系统还能工作，问题是完成条件分散、解释权不统一、审查成本偏高
- 这属于治理增强与统一收口，不是零到一补洞

### 9.2 P0 Slice

但以下最小切片应视为 `P0`：

- 将现有 blocker 条件统一收口为 machine-readable fitness hard gate
- 至少覆盖：
  - contract parity
  - unit / integration / smoke 必要验证
  - evidence completeness
  - canonical / forbidden path 检查
- 让 agent loop 不能在这些条件失败时宣布可退出

该 P0 切片的本质不是“上新功能”，而是修补当前 AI 交付中最危险的完成误判缺口。

### 9.3 Implementation Priority Rule

因此优先级建议固定为：

1. `P0`
   - 统一 hard gate 收口
   - 产出最小 `fitness_result`
   - 接入现有 auto gate
2. `P1`
   - 维度扩展
   - scorecard
   - richer rule object
   - CLI / CI 模板完善
   - 与 tester engine 深度集成

## 10. Rejected Options

### 10.1 Keep Rules Only In CI

不采纳“只把规则写在 CI 配置里”。

原因：

- agent 本地不可读
- 仓库治理不可审计
- 规则难以被 evidence 和 gate 复用

### 10.2 Keep Rules Only In Prompt

不采纳“继续主要依赖 prompt 告诉 agent 完成条件”。

原因：

- 规则不可回放
- 易漂移
- 无法形成统一机器执行面

### 10.3 Replace Gate With Fitness

不采纳“fitness 直接取代 gate / approval / supervisor”。

原因：

- fitness 解决的是规则执行，不是责任承担
- review / approval 的人机边界不能被吞并

### 10.4 Markdown Frontmatter As Sole Canonical Source

不采纳“前期就把 frontmatter 作为唯一正式真源”。

原因：

- 与 LEE 当前 schema-first 治理方向不一致
- 规则演进、校验与复用会受限

## 11. Rollout

### 11.1 Phase A: P0 Minimum Closure

- 建立最小 fitness rule schema
- 实现 fitness runner
- 输出 `fitness_result`
- 接入现有 gate
- 将结果回写 evidence pack

### 11.2 Phase B: P1 Structured Expansion

- 扩展 dimensions
- 增加 score / warn
- 接入 tester engine
- 补 CLI / CI 模板
- 补回归样板与测试

### 11.3 Phase C: Governance Tightening

- 逐步让更多 workflow 默认依赖 fitness_result
- 把零散 completion 条件迁移到统一 fitness 规则对象
- 对高风险主链启用 fail fast

## 12. Acceptance Signal

当本 ADR 对应能力落地后，至少应满足以下信号：

1. agent 无法仅凭“局部测试通过”就宣布可完成
2. hard gate 条件存在统一仓库内真源
3. gate 能直接消费统一 `fitness_result`
4. evidence pack 能回挂 fitness 执行结果
5. supervisor 审查时不再需要手工拼接主要完成条件

## 13. Final Rule

LEE 对 Fitness 的最终原则只有一句话：

> Fitness Function 不负责替系统做最终责任判断，但必须负责把“何时不允许说自己完成了”变成统一、可执行、可审计的工程信号。
