---
id: TECH-FEAT-090-001
ssot_type: tech
title: branch 与 worktree 并行开发下正式 SSOT 编号治理技术方案
status: draft
version: v1
parent_id: FEAT-090
derived_from_ids: []
source_refs:
- FEAT-090
- ADR-013
owner: codex
tags:
- cli
- ssot
- id
- governance
- tech
properties: {}
workflow_instance_id: wf-tech-feat-090-001__branch-yu-worktree-bingxingkaifaxiazhengshi-ssot-b-20260316
---

# Overview

本技术方案为 `FEAT-090` 提供最小可落地实现，目标是在不重做整套 SSOT 存储的前提下，把“branch / worktree 并行开发时正式顺序号冲突”收敛为受控流程问题。

方案原则：

- 对外入口默认采用 `workflow-first`，不把底层 SSOT 原语继续暴露为主入口
- 继续复用内部 `ArtifactManager.create_ssot()`、`SSOTIDGenerator`、`lint_ssot_front_matter()` 和 git hook 校验入口
- 不在 branch / worktree 本地直接定版正式顺序号
- 用临时 ID 作为开发期身份
- 在 merge / freeze 前的 workflow 阶段统一申请正式号并重写引用

# Current Anchors

当前实现可直接复用的锚点：

- `create_ssot()` 负责正式对象物化与 front matter 写入
- `SSOTIDGenerator.generate_id()` 负责正式顺序号生成
- `lint_ssot_front_matter()` 已能校验文件名与 front matter 一致性以及重复正式 ID
- `scripts/git_ssot_hook_checks.py` 已是现有 hook 聚合入口

因此本方案不新增平行系统，而是在对外治理入口之下复用现有内部物化能力，实现“临时 ID + formalize”流程。

# Identity Model

## 1. Two-Phase Identity

顺序型对象采用两阶段身份：

- 开发期身份：`provisional_id`
- 集成期身份：`formal_id`

其中：

- `provisional_id` 只在 branch / worktree 内作为局部稳定引用
- `formal_id` 才是长期 SSOT 主键

## 2. Covered Types

第一阶段覆盖以下独立顺序型对象：

- `EPIC`
- `FEAT`
- `ADR`

`SRC` 是否纳入第一阶段可选，不作为本次最小闭环必需条件。

## 3. Provisional ID Shape

临时 ID 必须满足三点：

- 一眼可识别为非正式 ID
- 在同一变更集内唯一
- 可以稳定映射回目标对象并被批量重写

建议格式：

`TYPE-TMP-<scope>-<seq>`

示例：

- `FEAT-TMP-codex-001`
- `EPIC-TMP-branch42-001`
- `ADR-TMP-worktreea-001`

本 TECH 只冻结“必须显式带 `TMP` 段”的约束，不在本阶段冻结 `<scope>` 的精确来源算法。

# Entry Plan

## 1. Public Entry Boundary

本方案明确区分两层入口：

- 对外入口：workflow-first 命令
- 对内入口：SSOT 物化原语与底层 helper

约束如下：

- `lee ssot create` 不再作为面向普通用户的扩展目标
- `lee ssot create` 仅保留给 internal / admin / maintenance 场景
- 临时 ID 创建与 formalize 需要挂在 workflow 的公开阶段上

可接受的对外入口形态包括：

- 产品链路中的 workflow 阶段，由业务链路生成对象
- merge / freeze 前的 workflow gate 或 finalize 阶段，统一处理身份定版

本 TECH 冻结两条约束：

- 不能继续扩展 `lee ssot create` 作为公开入口
- 默认公开模式采用 `workflow-first`

## 2. Provisional Create Path

对外创建流程应提供“创建临时 ID 对象”的高层入口。

该高层入口内部可以调用现有物化能力，但不应把底层对象创建参数原样暴露给普通用户。

创建行为：

- 若对象类型属于首批覆盖范围且请求创建开发期对象
- 则不走正式 `generate_id()`
- 改为生成临时 ID
- 文件仍落在正式对象目录中
- front matter 增加 `properties.identity_stage: provisional`

分支规则：

- 非 `main` 分支默认只能生成临时 ID
- `main` 只允许正式 ID 对象作为最终落盘结果

## 3. Formalize Path

新增单独命令，例如：

- workflow 中的 `formalize identities` 阶段
- 必要时由内部治理命令承接，但不作为普通用户默认入口

最小闭环建议支持两种输入：

- 指定单个 provisional 对象 ID
- 指定一个目录或变更集，对其中对象统一 formalize

formalize 行为：

- 读取 provisional 对象
- 按对象类型申请正式顺序号
- 计算新文件名
- 扫描并重写同批次对象中的相关引用
- 通过校验后提交落盘

时机约束：

- formalize 必须发生在 merge / freeze 之前
- 未 formalize 的对象不得进入 `main`

# Workflow Stage Design

## 1. Canonical Placement

本方案不新增平行主链，直接挂接现有产品链路：

- `workflow.product.task.src_to_epic`
- `workflow.product.task.epic_to_feat`
- `workflow.product.task.feat_to_delivery_prep`

其中：

- `src_to_epic` 负责 `SRC / EPIC`
- `epic_to_feat` 负责 `FEAT`
- `feat_to_delivery_prep` 只消费已 formalize 的 `FEAT`，继续生成 `UI / TECH / TASK`

## 2. src_to_epic Stage Change

`src_to_epic` 中的 `source_freeze` 保持不变，`epic_design` 与 `epic_freeze` 之间增加一段身份治理收口。

建议阶段顺序：

1. `raw_input_intake`
2. `source_normalization`
3. `source_review`
4. `source_freeze`
5. `problem_alignment`
6. `epic_design`
7. `epic_identity_prepare`
8. `epic_review`
9. `epic_identity_formalize`
10. `epic_freeze`

### 2.1 epic_identity_prepare

职责：

- 在非 `main` 分支上为 `EPIC` candidate 分配临时 ID
- 将临时 ID 注入 candidate 输出和引用上下文
- 形成后续 review 与 freeze 使用的稳定对象引用

输出要求：

- `epic_candidate` 带 provisional identity
- `properties.identity_stage = provisional`

### 2.2 epic_identity_formalize

职责：

- 在 `epic_freeze` 之前将 provisional `EPIC` 转为正式 `EPIC-xxx`
- 重写同批次内的 `EPIC` 引用
- 产出可供 `epic_freeze` 审批的正式身份对象

门禁关系：

- 该步骤依赖 `epic_review`
- `epic_freeze` 依赖 `epic_identity_formalize`

## 3. epic_to_feat Stage Change

`epic_to_feat` 是本次规则的关键路径，因为 `FEAT` 是 `TECH / TASK / TESTSET` 的父节点。

建议阶段顺序：

1. `feat_boundary_design`
2. `feat_spec_generation`
3. `feat_identity_prepare`
4. `feat_review`
5. `feat_identity_formalize`
6. `feat_freeze`

### 3.1 feat_identity_prepare

职责：

- 在非 `main` 分支上为每个 `FEAT` candidate 分配临时 ID
- 用临时 `FEAT` 建立 `source_refs / parent refs / review refs`
- 为后续 `feat_review` 提供稳定对象集

约束：

- 非 `main` 上不得直接分配正式 `FEAT-xxx`
- `feat_review` 评审的是 provisional 对象内容与边界，而不是最终正式顺序号

### 3.2 feat_identity_formalize

职责：

- 在 `feat_freeze` 前将 provisional `FEAT` 批量 formalize 为正式 `FEAT-xxx`
- 统一更新 `feat_specs`、freeze 输入和内部引用
- 产出正式 `feat_freeze_ref`

门禁关系：

- 该步骤依赖 `feat_review`
- `feat_freeze` 只能消费 formalized `FEAT`

## 4. feat_to_delivery_prep Stage Change

`feat_to_delivery_prep` 不负责 `FEAT` 正式号定版，只消费已 formalize 且已 freeze 的 `FEAT`。

新增输入约束：

- `feat_freeze_ref` 必须指向正式 `FEAT-xxx`
- 不允许消费 provisional `FEAT-TMP-*`

新增校验点：

- 若输入 `FEAT` 仍处于 provisional identity，则在 `tech_design` 前直接阻断
- `UI / TECH / TASK` 只能挂正式 `FEAT`

## 5. L2 Main Pipeline Impact

`workflow.product.product_main_pipeline` 的 L2 phase 拓扑不需要新增新 phase，但需要补阶段约束：

- `src_to_epic` 输出的 `epic_freeze_bundle` 必须已 formalize
- `epic_to_feat` 输出的 `feat_freeze_bundle` 必须已 formalize
- `feat_to_delivery_prep` 不再承担上游身份修复职责

换句话说，identity formalize 是各自 L3 内部的 freeze 前步骤，不是单独拆出的第四条 L3 主链。

## 6. Branch-to-Main Rule

workflow 运行时需要识别当前执行上下文：

- 若目标分支不是 `main`
  - `EPIC / FEAT / ADR` 默认走 provisional identity
- 若目标分支是 `main`
  - freeze 输出必须是 formal identity

最小决策规则：

- branch 内可 review provisional objects
- 进入 `main` 前必须完成 formalize
- `main` 上不接受新的 provisional 顺序型对象落盘

## 7. Runtime Boundary

以上设计描述的是 workflow template 的责任分配，不是把 formalize 结果直接固化成 checked-in runtime instance。

checked-in spec 只需要表达：

- 哪个 L3 模板在何处创建 provisional identity
- 哪个 freeze 前步骤负责 formalize
- 哪个 gate 负责阻断未 formalize 对象

实际对象扫描、rewrite、落盘和回滚仍由运行时与内部物化层执行。

# Rewrite Contract

formalize 时至少必须重写以下字段：

- 文件名中的 ID 段
- front matter `id`
- front matter `parent_id`
- front matter `derived_from_ids`
- front matter `source_refs` 的 base id
- front matter `related_ids`
- front matter `implements`
- front matter `verifies`
- Markdown 正文中显式出现的同批次 provisional ID 引用

重写顺序建议为：

1. 建立 provisional -> formal 映射表
2. 先重写 front matter 数据结构
3. 再重写文件名
4. 最后做 lint / P0 校验

# Validation Plan

## 1. Lint Extension

在现有 `ssot lint` / `lint_ssot_front_matter()` 之上补两类规则：

- 主线或正式检查模式下，不允许 `*-TMP-*`
- formalize 后若仍存在旧 provisional 引用，则报错

## 2. Hook / Gate Extension

在 `scripts/git_ssot_hook_checks.py` 中补充：

- 检查重复正式 ID
- 检查进入 `main` 的变更中是否包含未 formalize 的临时 ID
- 检查 formalize 后的引用是否已同步完成

## 3. Safety Rule

若 formalize 过程中任意一步失败：

- 不应留下半重写状态
- 应中止并回滚到原文件集

最小实现可先采用“先生成新内容并全部校验，再统一替换”的方式避免中间态污染。

# Data Compatibility

本方案对现有系统的兼容边界如下：

- 正式对象的长期格式仍保持现有 SSOT 结构
- 现有正式对象不要求立即迁移
- 现有 `generate_id()` 只负责正式号，不直接负责临时号
- 现有 `create_ssot()` 作为内部物化函数保留，但不应继续扩展为对外主入口
- provisional 状态通过 front matter `properties` 扩展承载，避免破坏基础 schema

# Testing Plan

至少补以下自动化测试：

- 高层入口能正确生成带 `TMP` 的 provisional 对象
- 同一批次 formalize 后生成唯一正式号
- formalize 会同步改写 front matter 与文件名
- formalize 会改写 `source_refs / parent_id / derived_from_ids / implements / verifies`
- lint / hook 能拦截重复正式 ID
- lint / hook 能拦截未 formalize 的临时 ID 进入 `main`

# Open Points

以下细节保留给实现时定稿：

- `<scope>` 是否取 branch 名、worktree 名还是短随机串
- formalize 是按单对象、目录还是 git staged files 运行
- 是否需要为 review 展示单独增加“临时 ID -> 正式 ID”映射报告

这些开放项不影响当前最小实现方向。
