---
id: ADR-018
ssot_type: adr
title: 本地 hook 绕过治理与 CI 失败回流闭环
status: draft
version: v1
workflow_instance_id: local-hook-governance-20260315
parent_id: null
derived_from_ids:
  - id: ADR-001
    version: v1
  - id: ADR-015
    version: v1
  - id: ADR-017
    version: v1
source_refs: []
owner: governance
tags:
  - governance
  - git-hooks
  - ci
  - developer-experience
  - feedback-loop
properties:
  adr_kind: governance_design
  decision_scope: local_hook_bypass_and_ci_failure_return_loop
---

# 本地 hook 绕过治理与 CI 失败回流闭环

## 1. Decision

LEE 采纳以下本地治理方向：

- 仓库内所有本地 Git hook、安装器和使用文档，不再提供 `--no-verify` 绕过指引。
- 本地检查失败时，统一提示为“先本地修复，再重新提交或推送”，而不是暗示可绕过。
- 本地 hook 视为开发前置门禁，不再把“可临时跳过”作为默认操作路径。

同时，LEE 记录以下后续演进方向：

- 当远端 CI 未通过时，系统应支持把失败结果回流为本地可执行修复任务，而不是停留在“PR 红灯，人工自己看”的弱闭环。

## 2. Context

当前仓库已具备：

- 本地 `pre-commit` / `pre-push` hook
- GitHub Actions 远端校验
- 主干与 PR 的远端检查链路

但本地治理仍存在一个明显问题：

- hook 和安装说明里直接给出 `git commit --no-verify` / `git push --no-verify` 示例

这会产生错误激励：

- 人类开发者会把绕过视为被默认允许的常规逃生口
- agent 更容易把“先过提交，再让远端拦”误认为正常工作流
- 本地门禁从“修复入口”退化成“可忽略提醒”

## 3. Problem

### 3.1 Local Guardrail Signal Is Inverted

如果本地 hook 在失败时直接提示如何跳过，那么它传递出的不是治理约束，而是绕过说明。

### 3.2 Failure Cost Is Shifted To Remote

当开发者或 agent 选择跳过本地检查，问题会被推迟到远端 CI 暴露：

- 反馈更慢
- 失败上下文更分散
- 修复责任更容易被悬空

### 3.3 CI Failure Still Lacks A Return Loop

即使远端已经能拦住不合规变更，当前系统也尚未把“CI 失败”稳定转换成“本地待修任务”或“明确回流工单”。

这意味着：

- 失败被看见了
- 但未必被系统化接住

## 4. Local Governance Decision

本地层面的治理边界冻结如下：

1. 仓库内 canonical hook 文案不得再推荐 `--no-verify`
2. hook 安装器输出不得再把绕过命令作为使用说明
3. 文档应把本地修复作为唯一默认动作
4. 对 agent 的仓库约束中，应将“禁止使用 `--no-verify`”视为显式规则

## 5. Constraint Clarification

需要明确一个技术事实：

- Git 客户端原生支持 `--no-verify`
- 单靠仓库内本地 hook，无法从技术上彻底封死该参数

因此本 ADR 不声称“本地机制已彻底禁止绕过”，而是冻结以下策略：

- 在本地默认路径中去除绕过引导
- 在治理语义上明确绕过属于违规操作
- 把真正的强阻断继续放在远端保护与合并门禁

## 6. Follow-up Direction

后续应补齐“远端失败回流本地修复”的闭环能力，至少覆盖：

- 将 CI 失败摘要转换为结构化修复输入
- 将失败关联到具体分支、提交、任务或 evidence
- 为 agent 或开发者生成明确的本地修复入口
- 修复后自动重新进入本地校验与远端校验链路

这部分能力应在后续 `EPIC / FEAT / TECH / TASK` 中单独设计，不在本 ADR 内直接冻结实现细节。

## 7. Immediate Repository Actions

本 ADR 对当前仓库的直接影响为：

- 更新 `.githooks/` 文案
- 更新 `scripts/install-git-hooks.py` 输出
- 更新本地 lint / hook 使用文档
- 为相关行为补充测试，防止后续回退到“文档鼓励绕过”

## 8. Non-Goals

本 ADR 当前不直接定义：

- 远端 CI 失败回流任务的最终 workflow YAML
- Git 平台规则的具体配置界面步骤
- 所有 agent 提交器的统一实现方式
- 远端失败自动修复是否允许全自动执行

这些内容留待后续专门设计。
