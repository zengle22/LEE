---
id: ADR-011
ssot_type: adr
title: 需求链一致性测试体系建设
status: frozen
version: v1
parent_id: null
derived_from_ids:
- id: ADR-001
  version: v1
- id: ADR-003
  version: v1
- id: ADR-007
  version: v1
- id: ADR-008
  version: v1
source_refs: []
owner: governance
tags:
- governance
- ssot
- testing
- requirements
- workflow
properties:
  adr_kind: governance_design
  decision_scope: requirement_chain_consistency_testing
frozen_at: '2026-03-12T20:26:53.595672'
---

# 需求链一致性测试体系建设

## 1. Decision

LEE 采纳“需求链一致性测试体系”方向，用自动化测试流水线替代对 `src -> epic -> feat -> task` 链路的大量人工目检。

该决策的核心内容如下：

- 将现有人工评审标准拆分为可执行规则、结构化 judge、抽样对比和稳定性指标
- 将需求链视为正式被测对象，而不是只把单个文档视为审阅对象
- 一致性测试至少分为四层：
  - 结构一致性测试
  - 语义映射一致性测试
  - 重跑稳定性测试
  - 下游可用性测试
- 一致性测试输出必须进入统一 `report.json / scorecard.md`，而不是停留在阶段性 prose review

本 ADR 当前冻结的是治理方向、测试分层和指标边界，不在本文件中直接冻结最终 schema 或最终 CLI 命令名。

## 2. Context

当前项目已经具备：

- 产品主链：`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`
- 分阶段 review/gate：`source_review`、`epic_review`、`feat_review`、`delivery_plan_validation`
- 局部 schema 校验和 SSOT P0/P1 校验

但当前链路仍然存在以下结构性缺口：

- review 主要面向单阶段、单对象，缺少整条链的统一校验视角
- schema validator 主要检查字段和格式，不检查上下游语义漂移
- delivery plan validation 主要判断计划形态是否完整，不等于 task 真正可执行
- 当前没有正式 replay stability 套件，无法判断同一输入重跑后的结构稳定性
- 当前没有统一 scorecard，无法持续观察 trace completeness、alignment、executability 等趋势

因此，当前系统更接近“会生成和评审需求链文档”，而不是“会测试需求链系统”。

## 3. Governing Principle

本 ADR 统一采用以下原则：

> 需求链本身是一个可测试的软件系统。

这意味着 `SRC / EPIC / FEAT / TASK` 的治理不再只依赖：

- 阅读文档
- 人工经验判断
- 一次性 review 结论

而必须补齐：

- 输入样本
- 自动测试规则
- 回归样本集
- 稳定性指标
- 统一报告

## 4. Scope

### 4.1 In Scope

- `src -> epic -> feat -> task` 当前主链的一致性测试
- 结构合法性、引用合法性、trace 完整性
- 上下游语义覆盖、漂移、遗漏、新增假设检测
- task 可执行性检测
- replay stability 测试
- scorecard 指标与回归比较

### 4.2 Out Of Scope

- 直接改写业务需求内容
- 替代产品 owner 的业务价值判断
- 替代 dev / qa 的实现与执行验证
- 把一致性测试等同于 release gate
- 在本 ADR 中直接引入新的业务主链对象

## 5. Required Test Layers

### 5.1 Layer 1: Structure Consistency

目标：

- 检查字段、层级、引用、必填项、ID 和文件结构是否满足要求

该层应由程序规则优先实现，避免依赖 LLM 才能发现基础错误。

最小检查项：

- `SRC` 是否具备来源、事实/假设/未知项、冻结状态和版本信息
- `EPIC` 是否具备目标、范围、非目标、成功标准和 `src` 引用
- `FEAT` 是否具备父 `EPIC`、能力边界、验收锚点和下游派生提示
- `TASK` 是否具备父 `FEAT`、动作、产出、验收映射、依赖和完成定义

### 5.2 Layer 2: Semantic Alignment

目标：

- 检查下游是否忠实承接上游，而不是结构完整但语义漂移

最小检查段：

- `src -> epic`
- `epic -> feat`
- `feat -> task`

每段至少要判断：

- 是否覆盖上游核心意图
- 是否遗漏关键约束
- 是否引入未声明的新目标
- 是否发生边界扩张或过度缩小

### 5.3 Layer 3: Replay Stability

目标：

- 检查同一输入重复运行时，核心结构和意图是否基本一致

该层不要求字面完全相同，只比较：

- 节点数量波动
- 跨 run 的对象匹配覆盖率
- 结构颗粒度变化
- 核心目标和边界的一致性

### 5.4 Layer 4: Downstream Usability

目标：

- 检查 `TASK` 是否真的可供下游消费，而不是只“看起来完整”

最小判断项：

- 是否是明确动作，而非抽象口号
- 是否有清晰 deliverable
- 是否有最低验收标准
- 是否还依赖大量口头解释
- 下游 agent 是否能够据此开工准备

## 6. Canonical Tester Set

当前链路至少需要 6 个测试器。

### 6.1 Schema Validator

职责：

- 校验字段、类型、枚举、必填项和基础格式

### 6.2 Traceability Checker

职责：

- 校验 `task -> feat -> epic -> src` 是否完整可回溯
- 识别 orphan、broken link、cross-chain misbinding

### 6.3 Semantic Alignment Judge

职责：

- 判断上下游是否高一致、轻微偏差或明显漂移

### 6.4 Overlap Or Duplication Detector

职责：

- 检查 FEAT 之间是否重叠
- 检查 TASK 是否重复或 ownership 模糊

### 6.5 Replay Stability Suite

职责：

- 对同一输入执行多轮生成并做标准化比较

### 6.6 Executability Judge

职责：

- 判断 task 是 `executable / partially_executable / not_executable`
- 输出缺失项列表

## 7. Decision On Rule Types

### 7.1 Programmatic Rules First

以下类型优先用规则实现：

- 必填字段
- 类型合法性
- ID 唯一性
- 引用存在性
- 父子关系
- 基础 trace 完整性

### 7.2 Hybrid Rules Preferred

对于成本高但判断价值大的项，优先采用：

- 规则初筛
- LLM 精判

适用范围：

- task 验收标准是否空泛
- feat 是否足以派生测试
- 下游是否新增未经声明的假设

### 7.3 LLM Judge Is Reserved For Semantics

以下项允许由 judge 主判：

- 范围是否清楚
- 语义是否漂移
- task 是否真正可执行
- feat/task 是否高度重叠但换名表达

## 8. Core Metrics

一致性测试不得只输出 pass/fail，必须输出至少以下五类指标。

### 8.1 Trace Completeness

定义：

- 可完整追溯的 task 数 / task 总数

### 8.2 Semantic Alignment Score

定义：

- `src->epic`
- `epic->feat`
- `feat->task`

三段平均分。

### 8.3 Replay Stability Score

定义：

- 同一输入多次运行后，核心结构与意图的一致程度

### 8.4 Overlap Rate

定义：

- FEAT 高重叠率
- TASK 明显重复率

### 8.5 Executability Rate

定义：

- 可直接进入下游准备的 task 数 / task 总数

## 9. Reporting Rule

一致性测试结果必须统一落到结构化报告，而不是只输出自然语言结论。

推荐最小输出：

```text
requirement-chain output
    ->
[1] schema validator
    ->
[2] traceability checker
    ->
[3] overlap detector
    ->
[4] semantic alignment judge
    ->
[5] executability judge
    ->
[6] replay stability suite
    ->
report.json / scorecard.md
```

报告最少要包含：

- 每层 pass/fail
- 发现列表
- 指标摘要
- 样本对比结果
- 本轮与基线的变化趋势

## 10. Sample Strategy

### 10.1 Golden Set

项目必须维护一组黄金样本集，用于回归：

- 至少覆盖多个真实业务场景
- 每个样本保留 `src / epic / feat / task` 参考结果
- 当 workflow、agent、contract、validator 变化时自动重跑

### 10.2 Cost Control

一致性测试按三层成本控制：

- `L0` 规则校验：全量
- `L1` 相似度/轻量筛查：全量
- `L2` LLM judge：异常项、关键样本、抽样项

## 11. Rollout

### 11.1 Phase 1

优先落地：

- schema validator
- traceability checker
- scorecard 输出
- task executability 基础判断

目标：

- 先替代最耗时的人工硬检查

### 11.2 Phase 2

补齐：

- semantic alignment judge
- overlap detector

目标：

- 把“结构正确但语义错”的问题纳入自动发现

### 11.3 Phase 3

补齐：

- replay stability suite
- golden set regression
- 趋势比较

目标：

- 让需求链具备真正的回归测试能力

## 12. Mapping To Current Chain

在当前项目的现役链路中，本 ADR 先约束：

- `source_review`
- `epic_review`
- `feat_review`
- `delivery_plan_validation`

这些节点后续不应只保留 review 结论，还应逐步输出：

- 可执行规则结果
- 结构化评分
- trace 指标
- 可回归比较结果

同时明确：

- 当前 `TASK` 仍挂在 `FEAT` 下时，一致性测试先按当前主链落地
- 待项目正式迁移到 `RELEASE -> DEVPLAN/TESTPLAN -> TASK` 后，再把同一测试体系平移到升级后的交付链

## 13. Consequences

采纳本 ADR 后，后续关于需求链质量的叙事必须从：

- “这份文档写得好不好”

转为：

- “这条需求链是否通过结构、语义、稳定性和可用性测试”

这会带来以下直接影响：

- review agent 需要逐步输出结构化、可比较结果
- validator 需要扩展到 trace 和链路指标
- workflow 变更不能只看生成是否成功，还要看 consistency score 是否退化
- 后续 CI 应逐步接入需求链回归测试

## 14. Follow-Up

本 ADR 后续建议派生的正式工作包括：

1. 一致性测试框架设计稿
2. validator / judge / replay 的 contract 定义
3. scorecard 输出 schema
4. 黄金样本集目录与样本格式
5. CI 接入策略

在这些下游对象形成前，本 ADR 作为治理方向和约束，不直接替代实现 spec。

## 15. Canonical Downstream Materialization

截至 2026-03-12，ADR-011 约束下的正式产品 SSOT 链路以以下对象为准：

- `SRC-016`
- `EPIC-030`
- `FEAT-159` 至 `FEAT-168`
- `TASK-FEAT-159-*` 至 `TASK-FEAT-168-*`

其中：

- `ADR-011` 是治理决策，不直接充当 `EPIC` 的 source object
- `SRC-016` 是当前 canonical 源对象

同日产生的更早试跑对象（如 `SRC-013` 至 `SRC-015`、`EPIC-019` 至 `EPIC-021`、`FEAT-151` 至 `FEAT-158`）仅保留为归档痕迹，不再作为当前 canonical 链路使用。

同时明确：

- 该能力当前属于治理、引擎、CLI、CI 集成类能力
- 当前 canonical 交付面不要求单独 UI 设计文档
- 若后续引入面向人工操作的控制台、评分卡页面或配置界面，再单独派生 `UI` 对象
