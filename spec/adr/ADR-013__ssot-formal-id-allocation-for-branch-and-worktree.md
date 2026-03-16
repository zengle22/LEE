---
id: ADR-013
ssot_type: adr
title: branch 与 worktree 并行开发下的 SSOT 正式编号分配策略
status: draft
version: v1
parent_id: null
derived_from_ids:
  - id: ADR-001
    version: v1
  - id: ADR-003
    version: v1
source_refs: []
owner: governance
tags:
  - governance
  - ssot
  - epic
  - feat
  - branch
  - worktree
properties:
  adr_kind: ssot_identity_governance
  decision_scope: branch_worktree_formal_id_allocation
---

# branch 与 worktree 并行开发下的 SSOT 正式编号分配策略

## 1. Decision

LEE 采纳以下规则：

- `EPIC-xxx`、`FEAT-xxx`、`ADR-xxx` 等正式顺序型 SSOT ID，不允许在各自 branch 或 worktree 本地直接最终定版
- branch / worktree 开发阶段允许使用临时 ID
- 正式顺序号只能在 canonical 集成面统一分配
- merge gate 必须阻止重复正式 ID 进入主线

这意味着：

- “本地递增后再 merge”不再被视为可接受流程
- “先临时占位，集成时再定正式号”成为 canonical 流程

## 2. Context

当前仓库中的 SSOT 编号生成方式，仍以本地序列文件为基础。

其直接结果是：

- 两个从同一基线切出的 branch，可能都生成 `FEAT-013`
- 两个独立 worktree，也可能都生成相同的下一个 `EPIC` 或 `FEAT`
- 冲突通常要等到 merge、lint 或 registry rebuild 时才暴露

这类冲突不是偶发使用问题，而是“分布式并行开发 + 本地顺序号分配”之间的结构性矛盾。

## 3. Problem

如果继续允许在 branch / worktree 中直接产出正式顺序号，会出现三类治理问题。

### 3.1 Formal Identity Collision

两个不同对象可能持有相同正式主键。

一旦正式 ID 已进入：

- 文件名
- front matter
- related_ids / source_refs / derived_from_ids
- registry

后续再修复，就不只是改一个文件名，而是要做跨对象引用重写。

### 3.2 Late Discovery

当前冲突通常在较晚阶段才被发现：

- PR 合并前
- merge 后的 lint
- registry rebuild

这会把“简单编号冲突”放大成“批量引用修复”。

### 3.3 False Stability

顺序号看起来稳定，但在并行开发场景中其实并不稳定。

如果没有全局唯一分配点，本地看到的“下一个编号”只对当前工作副本成立，不对仓库主线成立。

## 4. Decision Principle

本 ADR 采用以下原则：

> 正式 SSOT 主键的分配，必须发生在单一 canonical 集成边界，而不是分散在各自 branch / worktree 本地。

进一步说：

- 并行开发可以分散
- 正式身份定版必须收口

这是治理问题，不是命名偏好问题。

## 5. Canonical Strategy

### 5.1 Two-Phase Identity

SSOT 身份分为两个阶段：

1. 开发阶段身份
2. 集成阶段正式身份

开发阶段身份用于：

- 本地落盘
- 局部引用
- PR 讨论
- 中间产物跟踪

集成阶段正式身份用于：

- 主线合并
- 正式 registry
- 跨对象长期引用
- release / delivery / evidence 链路

### 5.2 Provisional ID Rule

在 branch / worktree 中创建的顺序型对象，默认应使用临时 ID。

临时 ID 只要求：

- 在当前变更集内唯一
- 能被脚本稳定识别和重写

临时 ID 的具体格式可以后续实现时再冻结，但必须满足“不冒充正式顺序号”这一约束。

### 5.3 Formalization Rule

正式号分配只能发生在 canonical 集成边界。

推荐的触发点包括：

- merge 前的显式 finalize 命令
- 主线上的集成 bot / CI job
- 由维护者在主线执行的统一编号命令

无论选择哪一种实现方式，原则都不变：

- 正式编号必须由单点流程统一分配
- 分配后必须同步重写全部内部引用

## 6. Mandatory Governance Rules

后续实现必须满足以下硬规则。

### 6.1 Branch Rule

branch / worktree 中不得把本地推断出的顺序号视为正式真相。

### 6.2 Merge Gate Rule

合并门禁必须阻止：

- 重复正式 ID
- 临时 ID 未完成 formalize 就进入主线
- formalize 后引用未同步更新

### 6.3 Rewrite Rule

从临时 ID 转正式 ID 时，必须重写至少以下位置：

- 文件名中的 ID 段
- front matter `id`
- `parent_id`
- `derived_from_ids`
- `source_refs` 的 base id
- `related_ids`
- `implements`
- `verifies`

### 6.4 Visibility Rule

工具层必须让使用者明确知道：

- 当前对象是否还是临时 ID
- 哪个环节会定正式号
- formalize 是否已完成

## 7. Rejected Option

### 7.1 Continue Local Sequential Allocation

不采纳“继续沿用各 branch / worktree 本地递增正式号，再靠 merge 解决冲突”。

原因很直接：

- 它不能从机制上避免冲突
- 它把冲突发现放得过晚
- 它会把简单编号问题扩散成引用修复问题

### 7.2 Add More Local Locking

也不采纳“给本地 sequence file 增加更多锁”作为根治方案。

原因是：

- 本地锁只能解决同一工作副本内并发
- 不能解决多个 branch / worktree 从共同基线并行前进的问题

## 8. Implementation Direction

本 ADR 先冻结治理方向，不在本文件中冻结最终 CLI 细节。

后续最小实现可以采用以下路径：

- `lee ssot create` 支持显式创建临时 ID
- 新增 `formalize` / `reserve` / `finalize` 一类命令
- git hook / CI 增加“重复正式 ID”和“临时 ID 泄漏到主线”的校验
- 让 `epic_to_feat` 或相关产品链路在集成时统一定版正式号

具体命令面、文件格式和重写算法，交由后续 `FEAT / TASK / TECH` 设计冻结。

## 9. Scope Boundary

本 ADR 只回答一件事：

在 branch / worktree 并行开发下，正式顺序型 SSOT ID 应如何治理。

本 ADR 不直接冻结：

- 临时 ID 的最终字符串格式
- 具体由哪个 agent 或 workflow 执行 formalize
- UI 展示层如何呈现临时 ID

这些属于下游实现设计，不属于本 ADR 的决策面。

## 10. Expected Downstream Work

该 ADR 落地后，至少应派生以下下游工作：

- 一个 `FEAT`：定义 branch / worktree 并行开发下的 SSOT 正式编号治理能力
- 若干 `TASK`：覆盖 CLI、ID rewrite、lint / hook / CI gate、迁移与回填
- 视情况补一个 `TECH`：定义 ID 重写器、引用扫描器和 finalize 流程

## 11. Consequence

采纳该 ADR 后，会得到以下结果：

- 并行开发仍可继续
- 正式主键冲突从“事后发现”转为“流程内避免”
- `EPIC / FEAT` 的正式身份回到单点治理
- merge 时的编号修复成本显著下降

代价也很明确：

- 需要引入临时 ID 阶段
- 需要一次 formalize 流程
- 需要补齐引用重写和门禁校验

本 ADR 的判断是：这些代价小于长期持续处理正式 ID 冲突的成本。
