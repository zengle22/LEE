---
id: ADR-020
ssot_type: adr
title: 证据轴 REPORT/EVI 收口与自动回挂规则
status: draft
version: v1
workflow_instance_id: evidence-axis-report-evi-20260315
parent_id: null
derived_from_ids:
  - id: ADR-001
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
  - evidence-axis
  - report
  - evi
  - traceability
properties:
  adr_kind: governance_design
  decision_scope: evidence_axis_report_evi_closure_and_auto_linking
---

# 证据轴 REPORT/EVI 收口与自动回挂规则

## 1. Decision

LEE 拟补充冻结证据轴中 `REPORT` 与 `EVI` 的 canonical 收口规则如下：

- 证据轴的正式结论对象由 `REPORT` 承担，正式附件与原始证据对象由 `EVI` 承担。
- 执行结果不得只停留在散落日志、runner 输出、截图目录或自由文本说明中，必须最终收口为正式 `REPORT / EVI` 对象链。
- 每次正式执行完成后，系统应能够把结果稳定回挂到上游执行单元，最小闭环为：
  - `TASK -> REPORT`
  - `REPORT -> EVI`
- 当结论面向 release 判定时，`REPORT.subject_id` 应直接指向 `RELEASE`，并由 release gate 消费。
- QA 审计与执行落库应最终能回填 `evidence_refs`，不得长期停留在“只记录 delivery_refs”的半成品状态。

本 ADR 当前只聚焦 `REPORT / EVI` 的边界、字段和自动回挂目标态。

本 ADR 当前不冻结：

- `BUG` 的最终轴归属
- bugfix 交付链建模方式
- 各部门具体 workflow YAML 的最终形态

## 2. Context

`ADR-001` 已冻结三轴模型，并明确证据轴回答：

- 实际上做了什么
- 测了什么
- 是否达到发布条件

当前仓库已经具备一部分证据轴基础设施：

- `REPORT / EVI / BUG` 已进入正式对象类型系统
- 正式落盘目录已存在目录策略
- `REPORT` 与 `BUG` 已有部分 validator 规则
- release 级 gate 已经开始消费 `REPORT` 与 `BUG`
- QA 审计模型中已存在 `evidence_refs` 字段

但当前实际运行仍存在明显收口缺口：

- QA 入口侧当前只自动补 `delivery_refs`
- 执行产物还没有系统化稳定回挂成 `TASK -> REPORT -> EVI`
- `EVI` 尚未完全进入与其他正式对象同等级别的 provenance 治理
- checked-in 项目对象中缺少稳定的真实证据轴样板链

因此，仓库当前状态更接近：

- 证据轴对象模型已部分存在
- 证据轴自动收口尚未完成

## 3. Problem

### 3.1 Evidence Still Leaks Into Runtime Files

当前许多执行事实仍然可能停留在：

- runner output
- 日志文件
- 截图目录
- 临时 JSON
- CLI 输出

这些材料可以作为证据原料，但不能替代正式证据对象。

### 3.2 Report And Evidence Are Not Yet Fully Linked Back To Execution

即使 `REPORT / EVI` 已有对象类型，当前系统仍缺一条稳定的自动回挂路径：

- 哪个 `TASK` 产生了哪个 `REPORT`
- 哪个 `REPORT` 消费了哪些 `EVI`
- 哪些 `EVI` 属于 release gate 判定输入

如果这些关系只靠人工脑补，就无法形成硬治理。

### 3.3 Audit Model Exists But Evidence Binding Is Not Closed

QA 审计模型已经有：

- `requirement_refs`
- `delivery_refs`
- `evidence_refs`

但当前入口只稳定生成 `delivery_refs`。

这意味着模型层已经承认三轴绑定，但运行层还没有把证据轴绑定真正补齐。

### 3.4 Release Gate Consumption Is Ahead Of Evidence Production Discipline

当前 release gate 已经会检查：

- `report_kind=release`
- `report_kind=test_execution`
- `report_kind=go_no_go`

但证据生产链本身还未完全自动化。

这会造成一个结构性问题：

- 下游 gate 已经期待正式证据
- 上游执行却未必稳定地产出正式证据对象

## 4. Scope

本 ADR 只处理以下对象与关系：

- `REPORT`
- `EVI`
- `TASK -> REPORT`
- `REPORT -> EVI`
- `RELEASE -> REPORT`
- QA audit 中的 `evidence_refs`

本 ADR 不处理以下主题：

- `BUG` 是否属于证据轴还是交付轴
- bugfix workflow
- release / plan / task 的全量字段设计
- Dev evidence pack 的完整实现细节

## 5. Canonical Position

### 5.1 REPORT Position

`REPORT` 是证据轴中的正式结论对象。

其职责是：

- 用结构化字段表达一次执行或一次发布判断的结果
- 归并若干 `EVI`
- 为 gate、审计和追溯提供可机读结论

`REPORT` 不是：

- 计划对象
- 需求对象
- 原始日志容器

### 5.2 EVI Position

`EVI` 是证据轴中的正式证据附件对象。

其职责是：

- 挂原始日志
- 挂截图
- 挂命令输出
- 挂测试产物
- 挂部署产物
- 挂 diff 或运行轨迹

`EVI` 不是：

- 结论对象
- gate 决策对象
- 计划对象

### 5.3 Canonical Relationship

本 ADR 采纳以下最小 canonical 关系：

```text
TASK -> REPORT -> EVI
RELEASE -> REPORT -> EVI
```

允许存在以下补充关系：

```text
TASK -> EVI
REPORT -> REPORT (summary / regression / rollup)
```

但不采纳以下弱关系作为主路径：

- 只有 runtime 文件，没有 `REPORT`
- 只有截图目录，没有 `EVI`
- 只有自由文本结论，没有正式 `REPORT`

## 6. Evidence Object Rules

### 6.1 REPORT Mandatory Fields

`REPORT` 至少应具备以下字段：

- `report_kind`
- `subject_id`
- `result`
- `evidence_refs`

建议补充以下字段：

- `task_id`
- `release_id`
- `testplan_id`
- `slice_key`
- `generated_at`
- `generated_by`
- `summary`

字段语义：

- `report_kind`
  - 表示报告类型
  - 典型值：`dev_progress / test_execution / regression / release / go_no_go`
- `subject_id`
  - 本报告面向的主要判定对象
  - 例如 `TASK` 或 `RELEASE`
- `result`
  - 本次执行或判定的结构化结论
- `evidence_refs`
  - 本报告消费的正式 `EVI` 引用

### 6.2 EVI Mandatory Fields

`EVI` 至少应具备以下字段：

- `subject_id`
- `evidence_kind`
- `captured_at`

建议补充以下字段：

- `task_id`
- `release_id`
- `report_id`
- `producer`
- `storage_refs`
- `checksum`
- `summary`

字段语义：

- `subject_id`
  - 本证据所服务的主对象
- `evidence_kind`
  - 证据类别
  - 例如 `runner_output / command_log / screenshot / test_artifact / deploy_artifact / diff`
- `captured_at`
  - 证据采集时间
- `report_id`
  - 若该证据被某个 `REPORT` 正式消费，应显式回挂

## 7. Auto-Linking Rule

### 7.1 Execution Completion Rule

对任何正式执行单元，系统目标态应满足：

- 执行开始时可先建立审计记录
- 执行完成时必须生成或登记正式 `REPORT`
- 相关原始产物必须生成或登记正式 `EVI`
- `REPORT.evidence_refs` 必须引用本次消费的 `EVI`

### 7.2 Task-Centric Rule

当执行入口是 `TASK` 时，系统目标态应形成：

```text
TASK
  -> REPORT(subject_id=TASK or RELEASE)
  -> EVI(...)
```

其中：

- 若报告结论只面向本任务，可令 `REPORT.subject_id = TASK`
- 若报告结论直接面向 release 判定，可令 `REPORT.subject_id = RELEASE`
- 即便 `subject_id = RELEASE`，仍建议保留 `task_id` 以保留执行来源

### 7.3 Release-Centric Rule

release 级 gate 消费的 `REPORT` 应直接挂在 `RELEASE` 下，并满足最小集合：

- `report_kind=release`
- `report_kind=test_execution`
- `report_kind=go_no_go`

这些 release 级 `REPORT` 应引用下游 `EVI`，不得只给文字性结论。

### 7.4 Audit Binding Rule

QA 审计中的 `evidence_refs` 不应在 entry routing 阶段强行伪造。

本 ADR 采纳以下时机划分：

- 入口校验阶段：允许仅有 `requirement_refs / delivery_refs`
- 执行完成阶段：补齐 `evidence_refs`
- 归档或审计固化阶段：将 `evidence_refs` 视为正式闭环字段

## 8. Governance Rule

### 8.1 Formal SSOT Governance

`REPORT / EVI` 一旦作为正式对象写入仓库，应进入与其他正式 SSOT 对象同级别的治理体系，包括：

- front matter lint
- registry rebuild
- provenance lint
- workflow-first 检查

### 8.2 EVI Governance Gap

当前 `EVI` 尚未完全进入 workflow provenance 白名单。

本 ADR 认定这是必须补齐的治理缺口，而不是可长期容忍的临时状态。

### 8.3 No Free-Text Closure

任何以下材料都不得单独作为 closure 判定依据：

- CLI 控制台输出
- 聊天消息
- 人工总结段落
- 目录截图

这些材料只有在被正式登记为 `EVI` 并被 `REPORT` 消费后，才进入正式证据链。

## 9. Current Repository Gap

结合当前仓库状态，至少存在以下待补项：

1. QA entry 只自动补 `delivery_refs`，尚未补齐 `evidence_refs`
2. `REPORT / EVI` 与 `TASK` 的自动回挂尚未形成统一实现
3. `EVI` 尚未完全纳入 provenance 治理
4. checked-in 项目对象中缺少稳定真实的 `REPORT / EVI` 样板链
5. 各部门运行产物与正式证据对象之间仍存在转换缺口

## 10. Follow-up Direction

后续实施应至少分为三层：

### 10.1 Layer A: Object Discipline

- 固化 `REPORT / EVI` 的最小 machine-readable 字段
- 明确 `subject_id / task_id / release_id / report_id` 的使用约定

### 10.2 Layer B: Runtime Closure

- 在执行完成阶段自动生成或登记 `REPORT`
- 自动登记相关 `EVI`
- 自动回填 `REPORT.evidence_refs`
- 自动回填审计记录中的 `evidence_refs`

### 10.3 Layer C: Governance Closure

- 将 `EVI` 纳入 workflow provenance 治理
- 为真实 checked-in `REPORT / EVI` 样板补测试
- 让 release gate 只消费正式证据对象而非散落运行产物

## 11. Immediate Non-Goals

本 ADR 当前不直接冻结以下内容：

- `BUG` 的轴归属
- bugfix task 与 bug lifecycle 的统一字段
- Dev evidence pack 与 `EVI` 的一一映射策略
- 所有部门运行时目录到正式证据对象的最终迁移计划

这些内容应在后续单独设计，避免在本 ADR 内混入尚未对齐的交付轴争议。

## 12. Acceptance Signal

当未来实施完成后，证据轴至少应能满足以下判定信号：

1. 任一正式执行任务都能反查到至少一个正式 `REPORT`
2. 任一正式 `REPORT` 都能反查到其消费的 `EVI`
3. release gate 不再依赖散落文件或自由文本做最终判定
4. QA 审计中 `evidence_refs` 能在执行闭环后稳定补齐
5. `EVI` 与 `REPORT` 被纳入正式治理，而非仅作为运行附件存在
