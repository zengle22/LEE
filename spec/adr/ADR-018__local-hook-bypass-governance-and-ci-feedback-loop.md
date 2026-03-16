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

## 9. Current Repository Entry Points

为避免“知道方向，但不知道怎么执行”，当前仓库统一认可以下操作入口。

### 9.1 Repository-Local Canonical Entry

仓库内 canonical 命令为：

```bash
python scripts/pr_flow.py --base dev --body "本次改动摘要"
```

该命令用于：

- 推送当前 branch
- 创建或复用到 `dev` / `main` 的 PR
- 轮询当前提交对应的 GitHub check-runs
- 在 checks 通过、失败或超时后给出明确结果

当需要复用已有 PR 或只观察远端状态时，可使用：

```bash
python scripts/pr_flow.py --base dev --no-push
python scripts/pr_flow.py --base dev --no-watch
python scripts/pr_flow.py --base main --body-file .pr_description.md
```

### 9.2 Skill Entry

对 agent 使用场景，当前仓库外部包装入口统一为：

- Codex skill: `github-pr-flow`
- Claude Code skill: `github-pr-flow`

两者都应优先调用仓库内 `scripts/pr_flow.py`，只有仓库缺失该脚本时，才回退到各自 skill 自带脚本。

### 9.3 CI Failure Repair Entry

当远端 PR 已经红灯时，当前认可的失败回流入口为：

- 读取失败 checks / actions log
- 在隔离 `worktree` 内修复
- 本地复现对应失败步骤
- 修复后重新通过 `scripts/pr_flow.py` 回到 PR 与 checks 链路

对 agent 来说，可使用：

- `gh-fix-ci` 负责读取失败检查与日志
- `github-pr-flow` 负责 push / PR / checks 收口

## 10. Standard SOP

当前仓库冻结以下标准操作流程，作为从本地改动进入 `dev` 的默认路径。

### 10.1 Start From A Clean Integration Baseline

1. 以 `origin/dev` 作为集成基线。
2. 通过 `git worktree` 创建隔离工作目录，不直接在脏的本地 `dev` 上堆改动。
3. 在 `worktree` 内新建短命分支，分支名必须清晰表达用途；agent 分支默认使用 `codex/` 前缀。

### 10.2 Fix And Validate In The Worktree

1. 只在该 `worktree` 分支内实现修复或功能。
2. 先跑与改动直接相关的最小验证，再跑与 CI 对齐的必要验证。
3. 不允许通过放宽断言、删测试、降阈值来制造绿灯。

### 10.3 Submit Through The PR Flow Script

1. 在 `worktree` 内整理 PR 标题与摘要。
2. 执行：

```bash
python scripts/pr_flow.py --base dev --body "本次改动摘要"
```

3. 让脚本完成以下动作：
   - `git push -u origin <branch>`
   - 创建或复用 `branch -> dev` 的 PR
   - 等待 checks 收敛

### 10.4 Handle CI Failures Through The Return Loop

1. 若 checks 失败，不直接手工在本地 `dev` 回拷代码。
2. 在同一 `worktree` 分支继续修复。
3. 先复现失败，再补修复和验证。
4. 再次执行 `scripts/pr_flow.py --base dev ...`，直到 PR checks 变为 clean。

### 10.5 Merge And Release Staging

1. 只有 `branch -> dev` PR clean 后，才进入 `dev`。
2. 阶段性集成完成后，再发起 `dev -> main` PR。
3. 只从 `main` merge commit 或 release tag 出包，不从临时分支或本地 `dev` 直接出包。

## 11. Explicitly Rejected Local Shortcuts

以下行为在当前仓库中不再被视为标准路径：

- 在本地长期脏 `dev` 上直接开发并手工回拷到集成分支
- 修完后不走 PR，直接把本地分支当作交付结论
- 使用 `--no-verify` 作为日常提交或推送路径
- 远端红灯后跳出当前 `worktree`，在其他目录另起一套修复实现
- 未验证 checks 结果就把 `dev` 视为阶段完成

## 12. Scope Clarification For This SOP

本节冻结的是“当前仓库的标准操作路径”，目的是让治理决策具备可执行入口。

它不额外改变本 ADR 第 6 节已经声明的边界：

- 远端失败回流的最终 workflow 设计仍可在后续 `EPIC / FEAT / TECH / TASK` 中继续演进
- `scripts/pr_flow.py` 与 skill 只是当前 canonical 操作入口，不代表未来不能被更强的一体化 workflow 替代
