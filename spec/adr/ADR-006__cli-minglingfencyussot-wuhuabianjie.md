---
id: ADR-006
ssot_type: adr
title: CLI 命令分层与 SSOT 物化边界
status: draft
version: v1
parent_id:
derived_from_ids:
  - ADR-001
  - ADR-003
  - ADR-005
source_refs: []
owner: governance
tags: [cli, ssot, governance, workflow]
properties:
  adr_kind: governance_design
  decision_scope: cli_entrypoints_and_ssot_materialization
---
# CLI 命令分层与 SSOT 物化边界

## 1. Decision

LEE 正式采用 CLI 分层原则：

- 面向用户的正式入口必须是高层命令或 workflow 命令。
- 面向系统的底层 SSOT 命令只负责对象物化和维护，不承担业务治理。

从现在开始，`ssot create` 不再被视为日常业务入口，而被重新定位为：

- 调试命令
- 数据修复命令
- registry 重建后的补录命令
- 管理员手工导入命令

同时明确以下硬约束：

- `SRC / EPIC / FEAT / ADR` 等正式对象的日常创建，必须经由 workflow 或高层命令触发。
- workflow / gate / review 负责业务治理。
- `ssot create` 和 `ArtifactManager.create_ssot()` 只负责最终 materialize。
- 正式 SSOT ID 分配必须与治理链联动，不能由普通用户绕过 workflow 直接抢占。

本 ADR 的核心原则是：

`ssot create` 不负责业务治理，只负责对象持久化。

## 2. Problem

当前仓库已经有两套能力同时存在：

- 一套是 `lee run ...` + workflow template + gate 的治理链
- 一套是 `lee ssot create` 直接创建正式对象

这种状态会导致命令面和治理面错位。

如果普通用户直接使用 `ssot create`，会天然绕过以下正式约束：

- 不走规定 workflow
- 不经过 review / gate / freeze
- 不自动继承上游上下文
- 不自动校验 source chain
- 不自动保证父子关系和编号策略一致

结果就是：

- 文件可以直接落盘
- registry 可以立刻出现新对象
- 但治理链没有真正执行
- formal object 的语义完整性依赖人工补救

这会把一个本应由系统强制保证的治理问题，降级为“使用者自觉遵守”问题。

## 3. Existing Anchors

当前仓库中已经存在支持本决策的明确实现锚点：

- workflow 模板已表达冻结、评审、gate 和 SSOT 输出约束：
  - [E:/ai/LEE/spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml](E:/ai/LEE/spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml)
  - [E:/ai/LEE/spec-global/departments/product/workflows/templates/epic-to-feat/v1/workflow.yaml](E:/ai/LEE/spec-global/departments/product/workflows/templates/epic-to-feat/v1/workflow.yaml)
- `lee run` 已是 workflow 主入口：
  - [E:/ai/LEE/src/lee/cli/commands/run.py](E:/ai/LEE/src/lee/cli/commands/run.py)
- runtime 已支持由 agent/workflow 输出契约自动物化 SSOT：
  - [E:/ai/LEE/src/lee/orchestrator/execution/runners/llm_runner.py](E:/ai/LEE/src/lee/orchestrator/execution/runners/llm_runner.py)
- `ArtifactManager.create_ssot()` 的职责本质上是 ID、路径、front matter、registry materialize：
  - [E:/ai/LEE/src/lee/orchestrator/execution/artifacts/manager.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/manager.py)
- `lee ssot create` 当前直接暴露正式对象创建能力：
  - [E:/ai/LEE/src/lee/cli/commands/ssot.py](E:/ai/LEE/src/lee/cli/commands/ssot.py)

因此，本 ADR 不是新造体系，而是把现有体系的职责边界正式化。

## 4. Layering Model

### 4.1 User-Facing Layer

面向用户的入口只表达业务语义，不表达底层存储语义。

推荐形态包括：

- `lee adr create`
- `lee epic create`
- `lee feat create`
- `lee run product.src-to-epic`
- `lee run product.epic-to-feat`
- `lee run architecture.decision-proposal`

其中名词型命令若存在，其本质应是 workflow alias，而不是直接写文件的“美化版 create”。

### 4.2 Governance Layer

workflow / review / gate 是正式治理入口。

这一层负责：

- 输入归一化
- 上下文继承
- source refs 透传
- 父子关系约束
- freeze 边界
- 审阅与审批
- formal object 是否允许生成

这一层必须能够决定：

- 当前产物只是 candidate
- 还是已经允许变成正式 SSOT

### 4.3 Materialization Layer

`ssot create`、`ArtifactManager.create_ssot()`、registry rebuild/sync 都属于 materialization / maintenance 层。

这一层只负责：

- ID 分配
- 路径解析
- front matter 生成
- 正式文件落盘
- registry 写入
- registry 重建与同步

这一层不负责：

- 业务合法性判断
- workflow 前置条件
- review 是否充分
- freeze 是否通过
- 用户是否处于允许创建 formal object 的上下文

## 5. Formal Object Creation Rule

正式 SSOT 对象的生成必须满足以下规则：

1. candidate 可以在 workflow 内生成，但 candidate 不应直接占用正式 SSOT ID。
2. formal object 只能在约定的 freeze / approval 边界之后生成。
3. formal object 的 `parent_id`、`derived_from_ids`、`source_refs` 必须来自上游 workflow 上下文，而不是依赖手工输入拼装。
4. 如果对象属于业务主链，其生成必须可追溯到对应 workflow instance、review 结果和 gate 决策。

该规则适用于：

- `SRC`
- `EPIC`
- `FEAT`
- 后续类似的业务或交付正式对象

`ADR` 虽然是决策型 SSOT，但若通过高层治理流程创建，也应遵守相同分层原则。

## 5.1 ADR And SRC Boundary

`ADR` 不是 `SRC`。

两者必须保持以下职责边界：

- `SRC` 表达业务源输入、问题定义、目标、场景、约束和成功标准
- `ADR` 表达治理、架构、流程或方案决策

因此，默认规则是：

- 即使某个需求最初由治理或架构讨论触发，也仍应先补一份薄 `SRC`
- 该 `SRC` 负责把决策背景归一为下游 `EPIC / FEAT` 可消费的业务输入
- `ADR` 作为 governing decision input 被引用，而不是直接充当业务主链 source object

推荐关系语义：

- `ADR governs SRC`
- `SRC derives EPIC`
- `EPIC derives FEAT`

不推荐：

- `ADR is SRC`
- `ADR derives FEAT` 作为默认主链

对于由治理或架构驱动的建设项，允许 `SRC` 采用薄形态，但不得省略其作为业务主链源对象的职责。

薄 `SRC` 至少应收敛以下内容：

- 背景与当前痛点
- 目标与非目标
- 关键约束
- 成功标准
- 关联 `ADR`

## 6. Command Classification

### 6.1 User Commands

面向普通用户的命令：

- 应默认走 workflow
- 应默认继承治理上下文
- 应默认生成 review / gate 所需引用
- 不应要求用户手工拼装底层关系字段

### 6.2 System Commands

面向系统维护或管理员的命令：

- `lee ssot create`
- `lee ssot rebuild-registry`
- `lee ssot sync`

这些命令允许存在，但必须被文档和帮助文本明确标注为：

- internal
- admin
- maintenance

它们不应继续被宣传为推荐主入口。

## 7. Consequences

采纳本 ADR 后，CLI 和治理系统需要满足以下方向：

- 日常创建路径从 `ssot create` 迁移到 workflow-first。
- 高层 `adr / epic / feat` 命令若引入，必须封装 workflow，而不是旁路 workflow。
- `ssot create` 的帮助文案、文档定位和测试叙事应降级为维护工具。
- formal object 编号冲突、source chain 漏传、父子关系漂移等问题，应优先通过 workflow 约束消除，而不是依赖事后 lint 和人工修复。

长期效果是：

- CLI 语义更稳定
- 治理链更难被绕过
- formal object 的生成条件更清晰
- registry 中对象更可信

## 8. Non-Goals

本 ADR 当前不直接规定：

- 高层命令的最终命名是否一定采用 `adr / epic / feat`
- runtime 内部具体如何延迟分配正式 ID
- 旧文档和旧 demo 是否一次性全部迁移
- `ssot create` 是否立即删除

这些属于后续 FEAT 的实施问题，不属于本 ADR 的决策边界。

## 9. Follow-Up Work

建议后续至少派生以下实施项：

- FEAT: 将 `lee ssot create` 降级为 internal/admin 命令
- FEAT: 为 `SRC / EPIC / FEAT / ADR` 提供 workflow-first 的高层入口或 alias
- FEAT: 让 formal SSOT ID 分配与 freeze / approval 边界对齐
- FEAT: 调整文档、demo、CLI help 和测试，统一为 workflow-first 叙事
