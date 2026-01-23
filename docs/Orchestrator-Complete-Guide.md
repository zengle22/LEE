# Orchestrator 完整使用指南

> **⚠️ ARCHITECTURE UPDATE NOTICE**
>
> **This document describes the v1.6 architecture, which has been superseded by v2.0.**
>
> The new architecture introduces:
> - **PM Agent Layer**: Decision-making AI that only orchestrates, doesn't execute
> - **Unified Engine Interface**: Standardized executors for LLM/MetaGPT/Shell/MCP
> - **Orchestrator Evolution**: Now controls execution through EngineRegistry, not external AI tools
>
> **For the latest architecture, see**: [architecture.md](./architecture.md)
> **For migration guidance, see**: [ARCHITECTURE-MIGRATION-GUIDE.md](./ARCHITECTURE-MIGRATION-GUIDE.md)
>
> ---
>
> This document is preserved for historical reference and for projects still using the v1.6 architecture.
>
> **Version**: v1.6
> **Status**: **LEGACY** - Superseded by v2.0
> **Last Updated**: 2025-01-22

---

## 目录

1. [简介](#1-简介)
2. [使用场景](#2-使用场景)
3. [安装与配置](#3-安装与配置)
4. [核心概念](#4-核心概念)
5. [完整命令参考](#5-完整命令参考)
6. [使用流程](#6-使用流程)
7. [完整示例](#7-完整示例)
8. [高级特性](#8-高级特性)
9. [故障排除](#9-故障排除)
10. [最佳实践](#10-最佳实践)

---

## 1. 简介

### 1.1 什么是 Orchestrator？

Orchestrator 是一个**通用的 AI 工作流编排器**，专门为解决 AI Agent 执行过程中的四个核心问题而设计：

| 问题 | 解决方案 |
|------|----------|
| Agent 编排可能被跳过 | 状态机 + 依赖检查 + Step Token |
| 人类门禁可能被忽略 | Gate 产物化 + 下游强依赖 |
| 产物验证可能被遗漏 | Artifact Gate + 强制验证 |
| 执行日志可能不完整 | 自动事件记录 + Span 追踪 |

### 1.2 核心价值

- **让规范从"建议"变成"协议"**：不再是 Agent 自觉遵守，而是强制执行
- **跨平台支持**：Claude Code, Codex CLI, Gemini Code, 任何 Custom Agent
- **完整审计追踪**：每个操作都有记录，可追溯、可回放
- **人类在环控制**：关键决策点强制人工审批

### 1.3 适用对象

- AI 工作流开发者
- DevOps 工程师
- QA 团队
- 需要控制 AI Agent 执行的管理者

---

## 2. 使用场景

### 2.1 软件开发流程

**场景**：自动化代码生成 + Code Review

```yaml
workflow:
  id: dev-flow
  name: 软件开发流程
  steps:
    - id: design
      name: 设计文档
      run: agent:architect
      human_gate: design_review

    - id: implement
      name: 代码实现
      run: agent:developer
      depends_on: [design]

    - id: review
      name: 代码审查
      run: agent:reviewer
      depends_on: [implement]
      human_gate: code_approval

    - id: deploy
      name: 部署
      run: agent:deployer
      depends_on: [review]
      human_gate: deploy_approval
```

**价值**：
- 强制每个步骤完成后才进入下一步
- 关键决策点（设计、代码、部署）必须人工审批
- 完整记录谁在何时做了什么

### 2.2 测试流程

**场景**：Bug 修复验证循环

```yaml
workflow:
  id: testing-flow
  name: 测试流程
  stages:
    - id: t5_bug_fix_cycle
      loop:
        condition: "open_bugs.count > 0"
        max_cycles: 5
      steps:
        - id: find_bugs
          name: 发现 Bug
          run: agent:tester

        - id: report_bug
          name: 报告 Bug
          run: agent:reporter
          depends_on: [find_bugs]

        - id: wait_fix
          name: 等待修复
          run: agent:waiter
          depends_on: [report_bug]
          # 等待外部事件：开发提交修复版本

        - id: verify_fix
          name: 验证修复
          run: agent:verifier
          depends_on: [wait_fix]

        - id: gate_check
          name: 出测门禁
          run: agent:gatekeeper
          depends_on: [verify_fix]
          human_gate: exit_approval  # 如果 bug 没了，批准退出循环
```

**价值**：
- 支持循环执行，直到所有 Bug 修复
- 可以等待外部事件（开发提交代码）
- 出测门禁确保质量达标

### 2.3 文档生成流程

**场景**：API 文档自动生成

```yaml
workflow:
  id: docs-flow
  name: 文档生成流程
  steps:
    - id: extract_api
      name: 提取 API 定义
      run: agent:extractor
      outputs:
        - path: output/api-spec.json
          required: true

    - id: generate_docs
      name: 生成文档
      run: agent:doc_generator
      depends_on: [extract_api]
      outputs:
        - path: output/api-reference.md
          required: true
        - path: output/api-guide.md
          required: true

    - id: review
      name: 文档审查
      run: agent:doc_reviewer
      depends_on: [generate_docs]
      human_gate: doc_approval
```

**价值**：
- Artifact Gate 确保所有必需文档都生成
- 强制人工审查文档质量

### 2.4 CI/CD 集成

**场景**：持续集成/部署流程

```yaml
workflow:
  id: cicd-flow
  name: CI/CD 流程
  steps:
    - id: test
      name: 运行测试
      run: agent:test_runner
      outputs:
        - path: output/test-report.xml
          required: true

    - id: build
      name: 构建
      run: agent:builder
      depends_on: [test]
      outputs:
        - path: output/artifact.jar
          required: true

    - id: deploy_staging
      name: 部署到测试环境
      run: agent:deployer
      depends_on: [build]
      human_gate: staging_approval

    - id: deploy_production
      name: 部署到生产环境
      run: agent:deployer
      depends_on: [deploy_staging]
      human_gate: production_approval  # 强制生产审批
```

---

## 3. 安装与配置

### 3.1 系统要求

- Python 3.10+
- 磁盘空间：> 100MB

### 3.2 安装

```bash
# 从源码安装
cd /path/to/LEE
pip install -e .

# 或使用 conda
conda env create -f environment.yml
conda activate lee-env
```

### 3.3 验证安装

```bash
python -m flowcore.orchestrator --help
```

应显示命令帮助信息。

---

## 4. 核心概念

### 4.1 工作流 (Workflow)

工作流是一个 YAML 文件，定义了一系列步骤及其依赖关系。

**基本结构**：

```yaml
id: my-workflow
name: 我的工作流
version: "1.0"

steps:
  - id: step1
    name: 第一步
    run: agent:my_agent
    depends_on: []
    outputs:
      - path: output/result.txt
        required: true

  - id: step2
    name: 第二步
    run: agent:another_agent
    depends_on: [step1]
    human_gate: step2_review
```

### 4.2 状态机 (State Machine)

Orchestrator 使用状态机管理工作流执行状态。

**步骤状态**：

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `blocked` | 被依赖阻断 |
| `ready` | 可以执行 |
| `in_progress` | 执行中 |
| `validating` | 验证中 |
| `gate_pending` | 等待门禁 |
| `completed` | 已完成 |
| `failed` | 失败 |

**运行状态**：

| 状态 | 说明 |
|------|------|
| `created` | 已创建 |
| `running` | 运行中 |
| `paused` | 暂停（等待门禁） |
| `completed` | 已完成 |
| `failed` | 失败 |

### 4.3 门禁 (Gate)

门禁是工作流中的控制点，用于强制人工审批或自动验证。

**类型**：

- `human_gate`：人工门禁，需要人手动审批
- `auto_gate`：自动门禁，基于条件自动通过

**示例**：

```yaml
steps:
  - id: deploy
    name: 部署
    human_gate: deploy_approval  # 需要人工审批
```

### 4.4 Step Token

Step Token 是步骤执行的授权令牌。

**作用**：
- 限制 Agent 只能执行授权的操作
- 与步骤绑定，过期自动失效
- 记录工具调用，可追溯

**生命周期**：
1. 签发：步骤开始时自动签发
2. 使用：Agent 携带 Token 调用工具
3. 验证：ToolGuard 检查权限
4. 过期：默认 4 小时后失效

### 4.5 Artifact Gate

Artifact Gate 确保步骤产出的所有必需文件都存在。

**规则**：
- 从 workflow 定义获取 `required_outputs`
- 检查所有必需文件是否存在
- 缺文件直接失败，不允许过门
- 生成 manifest 用于审计

**示例**：

```yaml
steps:
  - id: generate_docs
    name: 生成文档
    outputs:
      - path: output/api.md
        required: true      # 必需
      - path: output/guide.md
        required: true      # 必需
      - path: output/extra.md
        required: false     # 可选
```

### 4.6 事件日志 (Event Log)

事件日志自动记录所有工作流事件，不依赖 Agent 主动记录。

**事件类型**：
- `run_created`: 工作流创建
- `step_started`: 步骤开始
- `step_completed`: 步骤完成
- `gate_triggered`: 门禁触发
- `gate_approved`: 门禁通过
- `validation_failed`: 验证失败
- ...

**日志格式**：JSONL（每行一个 JSON 对象）

### 4.7 Agent Context

Agent Context 是步骤执行的完整上下文，包含：
- Agent 规范（persona, instructions, quality_bar）
- 步骤信息（inputs, outputs）
- 工作流状态（run_id, current_step）
- 契约（input_contract, output_contract）

**注入方式**：
- Claude Code: `.workflow/current-context.yaml`
- Codex CLI: 环境变量
- 其他: 自定义注入器

---

## 5. 完整命令参考

### 5.1 工作流管理

#### `generate-workflow` - 生成工作流

从模板和配置生成 workflow.yaml。

```bash
python -m flowcore.orchestrator generate-workflow \
  --template ai-spec/specs/.../phase-openspec-flow/v1/workflow.yaml \
  --config ./phase-config.yaml \
  --output ./workflow.yaml
```

**参数**：
- `--template, -t`: 工作流模板路径（必需）
- `--config, -c`: Phase 配置文件路径
- `--output, -o`: 输出路径（必需）
- `--phase-id`: Phase ID（替代配置文件）
- `--phase-name`: Phase 名称
- `--phase-dir`: Phase 目录路径
- `--change-id`: 变更 ID
- `--project-dir`: 项目目录

#### `init` - 初始化工作流运行

```bash
python -m flowcore.orchestrator init <project_dir> \
  --workflow <workflow.yaml> \
  [--template <template.yaml>] \
  [--skip-validation] \
  [--skip-workflow-validation]
```

**功能**：
- 解析 workflow.yaml
- 初始化状态机
- 创建 Phase 目录结构
- 验证项目配置（可选）
- 验证工作流结构（可选）

**示例**：

```bash
# 基本用法
python -m flowcore.orchestrator init ./my-phase \
  --workflow ./workflow.yaml

# 跳过验证（不推荐）
python -m flowcore.orchestrator init ./my-phase \
  --workflow ./workflow.yaml \
  --skip-validation
```

#### `status` - 查看当前状态

```bash
python -m flowcore.orchestrator status <project_dir>
```

**输出**：
```
═══════════════════════════════════════════════════════════
  Workflow Status
═══════════════════════════════════════════════════════════

  Run ID:       RUN-20250122-153045
  State:        running
  Current step: step2

  Step Progress:
    ● pending: 2
    ● in_progress: 1
    ● completed: 3
    ● failed: 0

  Gates:
    ● approved: 1
    ● pending: 1

  ⏳ Pending Gates (BLOCKING):
    - step2_review
      Approve: python -m flowcore.orchestrator approve ./my-phase step2_review --approver <name>

  Ready Steps:
    - step3

  Run-to-Gate Decision:
    next_step: step3
    next_step_human_gate: false
    action: continue

  ➡️  ACTION: Auto-continue to step3
```

### 5.2 步骤执行

#### `next` - 执行下一步

自动执行下一个就绪的步骤。

```bash
python -m flowcore.orchestrator next <project_dir>
```

**功能**：
- 自动选择下一个就绪步骤
- 检查门禁状态
- 签发 Step Token
- 注入 Agent Context
- 开始步骤执行

**示例**：

```bash
python -m flowcore.orchestrator next ./my-phase
```

#### `start` - 开始指定步骤

```bash
python -m flowcore.orchestrator start <project_dir> <step_id> \
  [--agent <agent_id>] \
  [--inject-context] \
  [--no-inject-context] \
  [--context-file <path>] \
  [--no-agent] \
  [--injector <claude_code|auto>]
```

**参数**：
- `project_dir`: 项目目录
- `step_id`: 步骤 ID（必需）
- `--agent`: Agent ID
- `--inject-context`: 注入 Agent 上下文（默认启用）
- `--no-inject-context`: 禁用上下文注入
- `--context-file`: 自定义上下文输出路径
- `--no-agent`: 跳过 Agent 加载（调试模式）
- `--injector`: 指定注入器（默认自动检测）

**示例**：

```bash
# 基本用法
python -m flowcore.orchestrator start ./my-phase step1

# 禁用上下文注入
python -m flowcore.orchestrator start ./my-phase step1 --no-inject-context

# 指定注入器
python -m flowcore.orchestrator start ./my-phase step1 --injector claude_code
```

#### `complete` - 完成步骤

```bash
python -m flowcore.orchestrator complete <project_dir> <step_id> \
  [--outputs <file1,file2,...>]
```

**功能**：
- 标记步骤为完成
- 进入验证阶段
- 记录输出文件

**示例**：

```bash
python -m flowcore.orchestrator complete ./my-phase step1 \
  --outputs output/result.txt,output/data.json
```

#### `validate` - 验证步骤产物

```bash
python -m flowcore.orchestrator validate <project_dir> <step_id>
```

**功能**：
- 检查所有必需输出是否存在
- 运行验证器（如果定义）
- 生成 manifest
- 如果有门禁，进入门禁状态

**示例**：

```bash
python -m flowcore.orchestrator validate ./my-phase step1
```

**输出**：

```
  --- Artifact Gate: Required Outputs Check ---

  Required outputs (2):
    - output/result.txt
    - output/data.json

  ✅ Found outputs (2):
    - output/result.txt
    - output/data.json

  Manifest: .workflow/manifests/step1.manifest.json

  ✅ Artifact Gate PASSED for step1
```

### 5.3 门禁管理

#### `approve` - 审批门禁

```bash
python -m flowcore.orchestrator approve <project_dir> <gate_id> \
  --approver <name> \
  [--comment <comment>]
```

**功能**：
- 审批通过门禁
- 生成 approval artifact
- 更新步骤状态为完成
- 解除阻断状态

**示例**：

```bash
python -m flowcore.orchestrator approve ./my-phase design_review \
  --approver "张三" \
  --comment "设计文档符合要求，可以继续"
```

#### `reject` - 拒绝门禁

```bash
python -m flowcore.orchestrator reject <project_dir> <gate_id> \
  --approver <name> \
  --reason <reason>
```

**功能**：
- 拒绝门禁
- 标记步骤为失败
- 记录拒绝原因

**示例**：

```bash
python -m flowcore.orchestrator reject ./my-phase design_review \
  --approver "张三" \
  --reason "设计不完整，需要补充"
```

### 5.4 令牌管理

#### `token` - 查看令牌

```bash
python -m flowcore.orchestrator token <project_dir> <step_id>
```

**功能**：
- 显示步骤的活跃令牌
- 显示令牌权限
- 显示上下文编码

**示例**：

```bash
python -m flowcore.orchestrator token ./my-phase step1
```

**输出**：

```
═══════════════════════════════════════════════════════════
  Active Tokens for step1
═══════════════════════════════════════════════════════════

  Token ID:    TKN-A1B2C3D4
  Expires:     2025-01-22T19:30:45
  Permissions: read, write, execute
  Context:     WORKFLOW_TOKEN:eyJ0IjoiVEstS...

```

#### `check` - 检查令牌

```bash
python -m flowcore.orchestrator check <project_dir> \
  --token <token_id> \
  [--tool <tool_name>]
```

**功能**：
- 验证令牌有效性
- 检查工具访问权限

**示例**：

```bash
# 检查令牌
python -m flowcore.orchestrator check ./my-phase \
  --token TKN-A1B2C3D4

# 检查特定工具权限
python -m flowcore.orchestrator check ./my-phase \
  --token TKN-A1B2C3D4 \
  --tool Bash
```

### 5.5 日志与追踪

#### `log` - 查看事件日志

```bash
python -m flowcore.orchestrator log <project_dir> \
  [--step <step_id>] \
  [--limit <n>] \
  [--stats]
```

**参数**：
- `--step`: 过滤特定步骤
- `--limit`: 限制事件数量
- `--stats`: 显示统计信息

**示例**：

```bash
# 查看所有事件
python -m flowcore.orchestrator log ./my-phase

# 查看特定步骤
python -m flowcore.orchestrator log ./my-phase --step step1

# 显示统计
python -m flowcore.orchestrator log ./my-phase --stats
```

**输出**：

```
═══════════════════════════════════════════════════════════
  Event Log (15 events)
═══════════════════════════════════════════════════════════

  2025-01-22 15:30:45 step_started            step1
  2025-01-22 15:35:22 step_completed          step1
  2025-01-22 15:35:23 validation_passed       step1
  2025-01-22 15:35:24 gate_triggered          step1
  2025-01-22 15:40:10 gate_approved           step1
  ...
```

#### `trace` - 查看执行追踪

```bash
python -m flowcore.orchestrator trace <project_dir> \
  [--format <markdown|yaml>] \
  [--output <path>] \
  [--limit <n>]
```

**功能**：
- 显示 Span-based 追踪
- 导出追踪报告
- 显示统计信息

**示例**：

```bash
# 显示追踪
python -m flowcore.orchestrator trace ./my-phase

# 导出为 Markdown
python -m flowcore.orchestrator trace ./my-phase \
  --format markdown \
  --output trace-report.md
```

**输出**：

```
═══════════════════════════════════════════════════════════
  Execution Trace
═══════════════════════════════════════════════════════════

  Run ID:          RUN-20250122-153045
  Total Spans:     25
  Total Duration:  45320ms
  Total Tokens:    12450
  Total Cost:      $0.0872
  Errors:          0

  By Type:
    - step: 5
    - validation: 5
    - gate: 3
    - tool_call: 12

  By Status:
    ● success: 25
    ● failed: 0
    ● running: 0
    ● timeout: 0

  Recent Spans:
    ✅ step1 (step) - 12450ms
    ✅ validation_step1 (validation) - 234ms
    ✅ gate_design_review (gate) - 287656ms
    ...
```

#### `detailed-log` - 生成详细执行日志

```bash
python -m flowcore.orchestrator detailed-log <project_dir> \
  [--session <session_id>] \
  [--source <auto|claude_code|codex|gemini|opencode>] \
  [--output <path>]
```

**功能**：
- 解析 AI 工具会话日志
- 生成详细执行报告
- 包含 AI 工作过程

**示例**：

```bash
# 自动检测并生成
python -m flowcore.orchestrator detailed-log ./my-phase

# 指定会话
python -m flowcore.orchestrator detailed-log ./my-phase \
  --session 2025-01-22-153045
```

#### `export` - 导出审计报告

```bash
python -m flowcore.orchestrator export <project_dir> \
  [--format <json|yaml>]
```

**功能**：
- 导出完整审计报告
- 包含所有事件和统计

**示例**：

```bash
python -m flowcore.orchestrator export ./my-phase --format json
```

### 5.6 高级操作

#### `reset` - 重置步骤

```bash
python -m flowcore.orchestrator reset <project_dir> <step_id> \
  [--reason <reason>]
```

**功能**：
- 重置步骤状态为 pending
- 允许重新执行
- 记录重置历史

**示例**：

```bash
python -m flowcore.orchestrator reset ./my-phase step1 \
  --reason "需要重新执行"
```

#### `context` - 查看 Agent 上下文

```bash
python -m flowcore.orchestrator context <project_dir> \
  [--clear] \
  [--injector <claude_code|auto>]
```

**功能**：
- 查看当前注入的 Agent 上下文
- 清除上下文

**示例**：

```bash
# 查看上下文
python -m flowcore.orchestrator context ./my-phase

# 清除上下文
python -m flowcore.orchestrator context ./my-phase --clear
```

#### `validate-project` - 验证项目配置

```bash
python -m flowcore.orchestrator validate-project <project_dir>
```

**功能**：
- 验证 project.yaml
- 检查仓库路径
- 验证路径别名

**示例**：

```bash
python -m flowcore.orchestrator validate-project ./my-phase
```

### 5.7 测试流程扩展命令

#### `loop-start` - 开始循环

```bash
python -m flowcore.orchestrator loop-start <project_dir> <loop_id>
```

**功能**：
- 开始循环执行
- 用于 bug 修复循环等场景

**示例**：

```bash
python -m flowcore.orchestrator loop-start ./my-phase t5_bug_fix_cycle
```

#### `loop-complete` - 完成循环迭代

```bash
python -m flowcore.orchestrator loop-complete <project_dir> <loop_id> \
  [--continue]
```

**参数**：
- `--continue`: 继续下一轮迭代

**示例**：

```bash
# 完成循环
python -m flowcore.orchestrator loop-complete ./my-phase t5_bug_fix_cycle

# 继续下一轮
python -m flowcore.orchestrator loop-complete ./my-phase t5_bug_fix_cycle --continue
```

#### `wait` - 开始外部等待

```bash
python -m flowcore.orchestrator wait <project_dir> <step_id> \
  --event <event_type> \
  [--timeout <48h>] \
  [--timeout-action <escalate|fail|skip>] \
  [--notify <channels>]
```

**功能**：
- 等待外部事件
- 用于等待开发修复等场景

**示例**：

```bash
python -m flowcore.orchestrator wait ./my-phase wait_fix \
  --event fix_version_submitted \
  --timeout 48h \
  --timeout-action escalate \
  --notify email,slack
```

#### `resolve` - 解决外部等待

```bash
python -m flowcore.orchestrator resolve <project_dir> <wait_id> \
  --resolver <name> \
  [--data <json>]
```

**示例**：

```bash
python -m flowcore.orchestrator resolve ./my-phase WAIT-step1-153045 \
  --resolver "李四" \
  --data '{"version": "1.2.3"}'
```

#### `loop-back` - 回退到之前步骤

```bash
python -m flowcore.orchestrator loop-back <project_dir> <from_step> <to_step> \
  [--reason <reason>]
```

**功能**：
- 回退到之前的步骤
- 用于出测门禁失败等场景

**示例**：

```bash
python -m flowcore.orchestrator loop-back ./my-phase gate_check find_bugs \
  --reason "发现新 Bug，需要重新修复"
```

---

## 6. 使用流程

### 6.1 基本流程

```
┌─────────────────────────────────────────────────────────────┐
│                      基本工作流                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 准备 workflow.yaml                                      │
│     └─ 定义步骤、依赖、门禁、输出                            │
│                                                             │
│  2. 初始化工作流                                             │
│     $ python -m orchestrator init <dir> --workflow workflow.yaml│
│     └─ 创建状态文件、目录结构                                │
│                                                             │
│  3. 执行步骤                                                 │
│     $ python -m orchestrator next <dir>                      │
│     └─ 自动执行下一个就绪步骤                                │
│                                                             │
│  4. 完成步骤                                                 │
│     $ python -m orchestrator complete <dir> <step_id>        │
│     └─ Agent 完成工作后调用                                  │
│                                                             │
│  5. 验证产物                                                 │
│     $ python -m orchestrator validate <dir> <step_id>        │
│     └─ 检查必需输出、运行验证器                              │
│                                                             │
│  6. 审批门禁（如果有）                                       │
│     $ python -m orchestrator approve <dir> <gate_id>         │
│     └─ 人工审批通过                                          │
│                                                             │
│  7. 重复 3-6 直到工作流完成                                  │
│                                                             │
│  8. 查看日志                                                 │
│     $ python -m orchestrator log <dir>                       │
│     └─ 审查完整执行记录                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 完整工作流程示例

#### Step 1: 创建 workflow.yaml

```yaml
id: simple-demo
name: 简单示例工作流
version: "1.0"

steps:
  - id: step1
    name: 生成报告
    run: agent:reporter
    outputs:
      - path: output/report.txt
        required: true

  - id: step2
    name: 审查报告
    run: agent:reviewer
    depends_on: [step1]
    human_gate: report_approval

  - id: step3
    name: 发布报告
    run: agent:publisher
    depends_on: [step2]
    outputs:
      - path: output/published.txt
        required: true
```

#### Step 2: 初始化工作流

```bash
$ python -m flowcore.orchestrator init ./demo --workflow workflow.yaml

═══════════════════════════════════════════════════════════
  Workflow Initialized
═══════════════════════════════════════════════════════════

  Run ID:      RUN-20250122-153045
  Workflow:    简单示例工作流
  Project:     ./demo
  State file:  .workflow/state.yaml

  Total steps: 3
  Human gates: 1

  ✅ Ready to start execution
```

#### Step 3: 执行第一步

```bash
$ python -m flowcore.orchestrator next ./demo

✅ Started step: step1
  Token: TKN-A1B2C3D4
  Expires: 2025-01-22T19:30:45

  --- Agent Context ---
  ✅ Context injected: claude_code
  📋 Agent: reporter
  📋 Name: 报告生成器
  📄 Context: .workflow/current-context.yaml

  ℹ️  When done, run: python -m flowcore.orchestrator complete ./demo step1
```

#### Step 4: Agent 工作（使用 AI 工具）

Agent 查看上下文：

```bash
# AI 工具会读取
$ cat .workflow/current-context.yaml
```

Agent 完成工作，生成报告：

```bash
# 创建输出文件
$ echo "这是一个报告" > output/report.txt
```

#### Step 5: 完成步骤

```bash
$ python -m flowcore.orchestrator complete ./demo step1 \
  --outputs output/report.txt

✅ Step step1 marked for validation
  ℹ️  Run: python -m flowcore.orchestrator validate ./demo step1
```

#### Step 6: 验证产物

```bash
$ python -m flowcore.orchestrator validate ./demo step1

  --- Artifact Gate: Required Outputs Check ---

  Required outputs (1):
    - output/report.txt

  ✅ Found outputs (1):
    - output/report.txt

  Manifest: .workflow/manifests/step1.manifest.json

  ✅ Artifact Gate PASSED for step1
```

#### Step 7: 审批门禁（第二步完成后）

```bash
# ... 执行 step2 ...

# 审批
$ python -m flowcore.orchestrator approve ./demo report_approval \
  --approver "张三" \
  --comment "报告质量良好，可以发布"

✅ Gate report_approval approved
  Approval ID: APPR-12345678
  Approver: 张三

  ℹ️  Ready to continue. Run: python -m flowcore.orchestrator next ./demo
```

#### Step 8: 继续执行

```bash
$ python -m flowcore.orchestrator next ./demo
# ... 重复执行
```

#### Step 9: 查看完整日志

```bash
$ python -m flowcore.orchestrator log ./demo

═══════════════════════════════════════════════════════════
  Event Log (12 events)
═══════════════════════════════════════════════════════════

  2025-01-22 15:30:45 run_created               -
  2025-01-22 15:30:46 step_started             step1
  2025-01-22 15:35:22 step_completed           step1
  2025-01-22 15:35:23 validation_passed        step1
  2025-01-22 15:40:10 gate_approved            report_approval
  ...
```

---

## 7. 完整示例

### 7.1 软件开发流程

**workflow.yaml**:

```yaml
id: dev-flow
name: 软件开发流程
version: "1.0"

steps:
  - id: design
    name: 设计文档
    run: agent:architect
    outputs:
      - path: output/design.md
        required: true
    human_gate: design_review

  - id: implement
    name: 代码实现
    run: agent:developer
    depends_on: [design]
    inputs:
      - source: design
        path: output/design.md
    outputs:
      - path: output/app.py
        required: true
      - path: output/test_app.py
        required: true

  - id: test
    name: 运行测试
    run: agent:test_runner
    depends_on: [implement]
    outputs:
      - path: output/test-results.xml
        required: true

  - id: review
    name: 代码审查
    run: agent:reviewer
    depends_on: [test]
    human_gate: code_approval

  - id: deploy
    name: 部署
    run: agent:deployer
    depends_on: [review]
    outputs:
      - path: output/deployment.log
        required: true
    human_gate: deploy_approval
```

**执行流程**:

```bash
# 1. 初始化
python -m flowcore.orchestrator init ./dev-project --workflow workflow.yaml

# 2. 执行设计步骤
python -m flowcore.orchestrator next ./dev-project
# Agent 生成设计文档
python -m flowcore.orchestrator complete ./dev-project design --outputs output/design.md
python -m flowcore.orchestrator validate ./dev-project design

# 3. 审批设计
python -m flowcore.orchestrator approve ./dev-project design_review --approver "架构师"

# 4. 继续后续步骤...
python -m flowcore.orchestrator next ./dev-project
```

### 7.2 测试流程（带循环）

**workflow.yaml**:

```yaml
id: testing-flow
name: 测试流程
version: "1.0"

stages:
  - id: t5_bug_fix_cycle
    loop:
      condition: "open_bugs.count > 0"
      max_cycles: 5
    steps:
      - id: find_bugs
        name: 发现 Bug
        run: agent:tester
        outputs:
          - path: output/bugs.json
            required: true

      - id: report_bug
        name: 报告 Bug
        run: agent:reporter
        depends_on: [find_bugs]
        outputs:
          - path: output/bug-report.md
            required: true

      - id: wait_fix
        name: 等待修复
        run: agent:waiter
        depends_on: [report_bug]
        # 外部等待

      - id: verify_fix
        name: 验证修复
        run: agent:verifier
        depends_on: [wait_fix]
        outputs:
          - path: output/verification.json
            required: true

      - id: gate_check
        name: 出测门禁
        run: agent:gatekeeper
        depends_on: [verify_fix]
        human_gate: exit_approval
```

**执行流程**:

```bash
# 1. 初始化
python -m flowcore.orchestrator init ./test-project --workflow workflow.yaml

# 2. 开始循环
python -m flowcore.orchestrator loop-start ./test-project t5_bug_fix_cycle

# 3. 执行循环体
python -m flowcore.orchestrator next ./test-project  # find_bugs
# ... Agent 发现 bug

# 4. 报告 bug
python -m flowcore.orchestrator next ./test-project  # report_bug

# 5. 等待外部修复
python -m flowcore.orchestrator wait ./test-project wait_fix \
  --event fix_version_submitted \
  --timeout 48h

# 6. 开发提交修复后，解决等待
python -m flowcore.orchestrator resolve ./test-project WAIT-wait_fix-XXX \
  --resolver "开发者" \
  --data '{"version": "1.2.3"}'

# 7. 验证修复
python -m flowcore.orchestrator next ./test-project  # verify_fix

# 8. 出测门禁 - 如果还有 bug，回退
python -m flowcore.orchestrator approve ./test-project exit_approval --approver "测试主管"
# 或如果还有 bug:
python -m flowcore.orchestrator loop-back ./test-project gate_check find_bugs \
  --reason "发现新 Bug"

# 9. 如果决定继续下一轮循环
python -m flowcore.orchestrator loop-complete ./test-project t5_bug_fix_cycle --continue
```

### 7.3 CI/CD 集成

**workflow.yaml**:

```yaml
id: cicd-flow
name: CI/CD 流程
version: "1.0"

steps:
  - id: test
    name: 运行测试
    run: agent:test_runner
    outputs:
      - path: output/test-report.xml
        required: true
      - path: output/coverage.xml
        required: true

  - id: build
    name: 构建
    run: agent:builder
    depends_on: [test]
    outputs:
      - path: output/artifact.jar
        required: true

  - id: deploy_staging
    name: 部署到测试环境
    run: agent:deployer
    depends_on: [build]
    outputs:
      - path: output/staging.log
        required: true
    human_gate: staging_approval

  - id: smoke_test
    name: 冒烟测试
    run: agent:tester
    depends_on: [deploy_staging]
    outputs:
      - path: output/smoke-test-results.json
        required: true

  - id: deploy_production
    name: 部署到生产环境
    run: agent:deployer
    depends_on: [smoke_test]
    outputs:
      - path: output/production.log
        required: true
    human_gate: production_approval
```

**CI 脚本**:

```bash
#!/bin/bash
set -e

PROJECT_DIR="./cicd-project"

# 1. 初始化
python -m flowcore.orchestrator init $PROJECT_DIR --workflow workflow.yaml

# 2. 自动执行到第一个门禁
while true; do
  python -m flowcore.orchestrator next $PROJECT_DIR

  # 检查是否有门禁
  STATUS=$(python -m flowcore.orchestrator status $PROJECT_DIR)
  if echo "$STATUS" | grep -q "Pending Gates"; then
    echo "遇到门禁，等待人工审批"
    break
  fi

  # 检查是否完成
  if echo "$STATUS" | grep -q "Workflow completed"; then
    echo "工作流完成"
    break
  fi
done

# 3. 显示状态
python -m flowcore.orchestrator status $PROJECT_DIR
```

---

## 8. 高级特性

### 8.1 Agent 上下文注入

Orchestrator 会自动为每个步骤注入 Agent 上下文。

**支持的注入器**：
- `claude_code`: Claude Code（.workflow/current-context.yaml）
- `codex_cli`: Codex CLI（环境变量）
- `auto`: 自动检测

**上下文内容**：
- Agent ID, Name, Version
- Persona, Instructions, Quality Bar
- Step 信息（inputs, outputs）
- Workflow 状态（run_id, current_step）
- 契约（input_contract, output_contract）

**禁用注入**：

```bash
python -m flowcore.orchestrator start ./project step1 --no-inject-context
```

### 8.2 Artifact Gate

Artifact Gate 确保所有必需输出都存在。

**配置**：

```yaml
steps:
  - id: generate
    name: 生成文档
    outputs:
      - path: output/api.md
        required: true      # 必需
      - path: output/guide.md
        required: true      # 必需
      - path: output/extra.md
        required: false     # 可选
```

**验证行为**：
- 缺少必需输出 → 验证失败
- 所有必需输出存在 → 验证通过
- 额外输出 → 警告但不失败

**Manifest**：

每次验证生成 manifest：

```json
{
  "step": "generate",
  "verified_at": "2025-01-22T15:30:45",
  "required": ["output/api.md", "output/guide.md"],
  "produced": ["output/api.md", "output/guide.md", "output/extra.md"],
  "missing": [],
  "extra": ["output/extra.md"],
  "status": "done"
}
```

### 8.3 Run-to-Gate 决策

Orchestrator 提供 Run-to-Gate 决策信息，用于 AI 自动执行。

**决策信息**：

```bash
$ python -m flowcore.orchestrator status ./project

  Run-to-Gate Decision:
    next_step: step2
    next_step_human_gate: false
    action: continue
```

**决策逻辑**：

| 条件 | action |
|------|--------|
| 有待审批门禁 | `wait_for_approval` |
| 有就绪步骤 | `continue` |
| 全部完成 | `workflow_done` |
| 被阻断 | `blocked` |

### 8.4 循环执行

支持测试流程中的循环场景（如 Bug 修复循环）。

**配置**：

```yaml
stages:
  - id: bug_fix_cycle
    loop:
      condition: "open_bugs.count > 0"
      max_cycles: 5
    steps:
      - id: find_bugs
        name: 发现 Bug
        run: agent:tester
      # ... 其他步骤
```

**命令**：

```bash
# 开始循环
python -m flowcore.orchestrator loop-start ./project bug_fix_cycle

# 完成当前迭代（继续下一轮）
python -m flowcore.orchestrator loop-complete ./project bug_fix_cycle --continue

# 完成循环（不再继续）
python -m flowcore.orchestrator loop-complete ./project bug_fix_cycle
```

### 8.5 外部等待

支持等待外部事件（如开发提交修复版本）。

**配置**：

```yaml
steps:
  - id: wait_fix
    name: 等待修复
    run: agent:waiter
```

**命令**：

```bash
# 开始等待
python -m flowcore.orchestrator wait ./project wait_fix \
  --event fix_version_submitted \
  --timeout 48h

# 解决等待
python -m flowcore.orchestrator resolve ./project WAIT-wait_fix-XXX \
  --resolver "开发者"
```

### 8.6 Loop Back

支持从失败的门禁回退到之前的步骤。

**使用场景**：
- 出测门禁失败 → 回到 Bug 修复循环
- 审查不通过 → 回到设计阶段

**命令**：

```bash
python -m flowcore.orchestrator loop-back ./project gate_check find_bugs \
  --reason "发现新 Bug，需要重新修复"
```

### 8.7 跨平台支持

Orchestrator 设计为平台无关，支持：

#### Claude Code

```yaml
# 在 CLAUDE.md 中添加

## 工作流执行规则

执行任何开发任务前，必须：

1. 运行 `python -m flowcore.orchestrator status .` 检查当前状态
2. 如果有待审批门禁，等待人类审批
3. 获取当前步骤的 token: `python -m flowcore.orchestrator token . <step_id>`
4. 完成后运行验证: `python -m flowcore.orchestrator validate . <step_id>`
```

#### Codex CLI

```bash
# 在 codex-constitution.yaml 中

pre_execute_hook: "python -m flowcore.orchestrator check . --token $STEP_TOKEN"
post_execute_hook: "python -m flowcore.orchestrator complete . --step $STEP_ID"
```

#### 通用方式

将 Orchestrator 状态注入到系统提示词：

```
当前工作流状态:
- 当前步骤: {current_step}
- 待审批门禁: {pending_gates}
- 可用令牌: {available_token}
- 必须产出: {required_outputs}
```

---

## 9. 故障排除

### 9.1 常见错误

#### 错误 1: No workflow state found

```
❌ No workflow state found in ./project
```

**原因**：工作流未初始化

**解决**：

```bash
python -m flowcore.orchestrator init ./project --workflow workflow.yaml
```

#### 错误 2: Step not in pending/ready state

```
❌ Cannot start step step1: Step step1 is not in pending/ready state (current: completed)
```

**原因**：步骤已完成或正在执行

**解决**：检查状态或重置步骤

```bash
# 查看状态
python -m flowcore.orchestrator status ./project

# 如果需要重新执行，重置步骤
python -m flowcore.orchestrator reset ./project step1
```

#### 错误 3: Blocked by pending gate

```
❌ Execution blocked by pending gates:
  - design_review
    Approve: python -m flowcore.orchestrator approve ./project design_review --approver <name>
```

**原因**：有待审批的门禁

**解决**：审批门禁或跳过（不推荐）

```bash
# 审批
python -m flowcore.orchestrator approve ./project design_review --approver "张三"
```

#### 错误 4: MISSING OUTPUTS

```
❌ MISSING OUTPUTS (2):
  - output/result.txt
  - output/data.json

Artifact Gate BLOCKED: 必须补齐所有必需输出后才能通过验证
```

**原因**：缺少必需的输出文件

**解决**：补齐缺失的文件

```bash
# Agent 创建缺失文件
echo "result" > output/result.txt
echo "data" > output/data.json

# 重新验证
python -m flowcore.orchestrator validate ./project step1
```

#### 错误 5: Token invalid

```
❌ Token invalid: Token has expired
```

**原因**：令牌已过期（默认 4 小时）

**解决**：重新开始步骤获取新令牌

```bash
python -m flowcore.orchestrator start ./project step1
```

### 9.2 调试技巧

#### 查看详细状态

```bash
# 查看完整状态
python -m flowcore.orchestrator status ./project

# 查看事件日志
python -m flowcore.orchestrator log ./project --stats

# 查看执行追踪
python -m flowcore.orchestrator trace ./project
```

#### 查看状态文件

```bash
# 查看原始状态
cat .workflow/state.yaml
```

#### 查看当前上下文

```bash
# Claude Code
cat .workflow/current-context.yaml

# 使用命令
python -m flowcore.orchestrator context ./project
```

#### 启用调试模式

```bash
# 设置环境变量
export ORCHESTRATOR_DEBUG=1
export ORCHESTRATOR_DEBUG_AGENT=1

# 运行命令
python -m flowcore.orchestrator status ./project
```

### 9.3 恢复策略

#### 重置步骤

```bash
python -m flowcore.orchestrator reset ./project step1 \
  --reason "需要重新执行"
```

#### 回退到之前步骤

```bash
python -m flowcore.orchestrator loop-back ./project step3 step1 \
  --reason "step2 有问题，需要重新执行"
```

#### 重新初始化

```bash
# 备份当前状态
cp -r .workflow .workflow.backup

# 重新初始化
python -m flowcore.orchestrator init ./project --workflow workflow.yaml
```

---

## 10. 最佳实践

### 10.1 工作流设计

#### 原则 1: 小步骤优先

将大任务拆分为小步骤，每个步骤只做一件事。

**❌ 不好的设计**：

```yaml
steps:
  - id: big_step
    name: 做所有事情
    run: agent:do_everything
    outputs:
      - path: output/everything.txt
        required: true
```

**✅ 好的设计**：

```yaml
steps:
  - id: step1
    name: 分析需求
    run: agent:analyzer
    outputs:
      - path: output/requirements.md
        required: true

  - id: step2
    name: 设计方案
    run: agent:designer
    depends_on: [step1]
    outputs:
      - path: output/design.md
        required: true

  - id: step3
    name: 实现代码
    run: agent:implementer
    depends_on: [step2]
    outputs:
      - path: output/code.py
        required: true
```

#### 原则 2: 明确输入输出

每个步骤都应该明确声明输入和输出。

```yaml
steps:
  - id: step2
    name: 第二步
    run: agent:worker
    inputs:
      - source: step1
        path: output/step1-result.txt
    outputs:
      - path: output/step2-result.txt
        required: true
```

#### 原则 3: 关键决策点设置门禁

在关键决策点设置人工门禁，不要让 AI 自动做所有决策。

```yaml
steps:
  - id: deploy_production
    name: 部署到生产环境
    run: agent:deployer
    human_gate: production_approval  # 强制人工审批
```

#### 原则 4: 使用 Artifact Gate

利用 Artifact Gate 确保所有必需输出都生成。

```yaml
steps:
  - id: generate_docs
    name: 生成文档
    outputs:
      - path: output/api.md
        required: true      # 必需
      - path: output/guide.md
        required: true      # 必需
```

### 10.2 Agent 规范设计

#### 原则 1: 明确 Persona

为每个 Agent 定义清晰的 persona。

```yaml
agent:reviewer
persona:
  role: "代码审查专家"
  expertise: ["代码质量", "安全性", "性能"]
  tone: "专业、严谨"
```

#### 原则 2: 设置 Quality Bar

定义清晰的质量标准。

```yaml
agent:reviewer
quality_bar:
  - "代码必须通过所有测试"
  - "代码覆盖率必须 > 80%"
  - "不能有安全漏洞"
```

#### 原则 3: 禁止行为

明确列出禁止的行为。

```yaml
agent:developer
forbidden_behaviors:
  - id: "skip_tests"
    name: "跳过测试"
    description: "不允许跳过任何测试"
  - id: "hardcode_secrets"
    name: "硬编码密钥"
    description: "不允许在代码中硬编码密钥"
```

### 10.3 安全实践

#### 原则 1: 使用 Token 控制权限

不要给 Agent 过高的权限。

```bash
# 默认权限
permissions: ["read", "write", "execute"]

# 生产部署需要额外权限
permissions: ["read", "write", "execute", "deploy"]
```

#### 原则 2: 审计所有操作

定期查看审计日志。

```bash
# 导出审计报告
python -m flowcore.orchestrator export ./project --format json

# 查看详细日志
python -m flowcore.orchestrator detailed-log ./project
```

#### 原则 3: 验证项目配置

在初始化时验证项目配置。

```bash
python -m flowcore.orchestrator validate-project ./project
```

### 10.4 性能优化

#### 原则 1: 并行执行独立步骤

Orchestrator 会自动并行执行独立的步骤。

```yaml
steps:
  - id: unit_test
    name: 单元测试
    run: agent:test_runner
    outputs:
      - path: output/unit-test.xml
        required: true

  - id: integration_test
    name: 集成测试
    run: agent:test_runner
    outputs:
      - path: output/integration-test.xml
        required: true

  # 这两个测试可以并行执行
```

#### 原则 2: 减少门禁阻塞

只在必要时设置门禁。

```yaml
steps:
  - id: auto_check
    name: 自动检查
    run: agent:checker
    # 不需要门禁，让 AI 自动执行

  - id: deploy_production
    name: 部署到生产
    run: agent:deployer
    human_gate: production_approval  # 只有生产部署需要门禁
```

### 10.5 团队协作

#### 原则 1: 使用清晰的命名

使用清晰、一致的命名规范。

```yaml
steps:
  - id: design_review
    # 清晰的步骤 ID

gates:
  - design_review
  # 步骤 ID 和门禁 ID 一致
```

#### 原则 2: 记录审批原因

审批时记录原因，便于追溯。

```bash
python -m flowcore.orchestrator approve ./project design_review \
  --approver "张三" \
  --comment "设计文档符合要求，架构合理，可以继续"
```

#### 原则 3: 定期审查日志

定期审查工作流执行日志，找出改进点。

```bash
# 每周审查
python -m flowcore.orchestrator log ./project --stats
```

---

## 附录

### A. 状态文件格式

`.workflow/state.yaml` 格式：

```yaml
version: "1.1"
run_id: "RUN-20250122-153045"
workflow_id: "my-workflow"
workflow_name: "我的工作流"
run_state: "running"
created_at: "2025-01-22T15:30:45"
updated_at: "2025-01-22T15:40:10"
current_step: "step2"

steps:
  step1:
    step_id: "step1"
    state: "completed"
    agent_id: "agent:worker"
    started_at: "2025-01-22T15:30:50"
    completed_at: "2025-01-22T15:35:22"
    token: "TKN-A1B2C3D4"
    outputs:
      - "output/result.txt"
    outputs_hash: "abc123"
    validation_result:
      passed: true
      validated_at: "2025-01-22T15:35:23"
    gate_id: "step1_review"
    gate_status: "approved"
    required_outputs:
      - "output/result.txt"

  step2:
    step_id: "step2"
    state: "in_progress"
    agent_id: "agent:worker2"
    started_at: "2025-01-22T15:40:10"
    token: "TKN-E5F6G7H8"
    required_outputs:
      - "output/step2-result.txt"

_deps:
  step2: ["step1"]

gates:
  step1_review:
    gate_id: "step1_review"
    step_id: "step1"
    type: "human"
    status: "approved"
    blocking: true
    triggered_at: "2025-01-22T15:35:23"
    approved_at: "2025-01-22T15:40:00"
    approver: "张三"
    approval_artifact: ".workflow/approvals/step1_review.json"
    comment: "质量良好"

artifacts: {}
metadata: {}

loops: {}
external_waits: {}
loop_back_targets: {}
```

### B. 事件日志格式

`.workflow/events.jsonl` 格式（每行一个 JSON）：

```json
{"event_id":"EVT-20250122153045001-0001","event_type":"run_created","timestamp":"2025-01-22T15:30:45","run_id":"RUN-20250122-153045","step_id":null,"agent_id":null,"actor":"system","data":{"workflow_id":"my-workflow","workflow_name":"我的工作流"}}
{"event_id":"EVT-20250122153050002-0002","event_type":"step_started","timestamp":"2025-01-22T15:30:50","run_id":"RUN-20250122-153045","step_id":"step1","agent_id":"agent:worker","actor":"agent","data":{"token":"TKN-A1B2C3D4"}}
{"event_id":"EVT-20250122153522003-0003","event_type":"step_completed","timestamp":"2025-01-22T15:35:22","run_id":"RUN-20250122-153045","step_id":"step1","agent_id":"agent:worker","actor":"agent","outputs_hash":"abc123","data":{"outputs":["output/result.txt"]}}
```

### C. Manifest 格式

`.workflow/manifests/step1.manifest.json` 格式：

```json
{
  "step": "step1",
  "verified_at": "2025-01-22T15:35:23",
  "required": ["output/result.txt"],
  "produced": ["output/result.txt"],
  "missing": [],
  "extra": [],
  "status": "done"
}
```

### D. Approval Artifact 格式

`.workflow/approvals/gate_id.json` 格式：

```json
{
  "gate_id": "step1_review",
  "step_id": "step1",
  "run_id": "RUN-20250122-153045",
  "approver": "张三",
  "approved_at": "2025-01-22T15:40:00",
  "comment": "质量良好",
  "artifacts_hash": "abc123",
  "approval_id": "APPR-12345678",
  "signature": null
}
```

### E. 命令速查表

| 命令 | 说明 |
|------|------|
| `generate-workflow` | 从模板生成 workflow.yaml |
| `init` | 初始化工作流运行 |
| `status` | 查看当前状态 |
| `next` | 执行下一步 |
| `start` | 开始指定步骤 |
| `complete` | 完成步骤 |
| `validate` | 验证步骤产物 |
| `approve` | 审批门禁 |
| `reject` | 拒绝门禁 |
| `token` | 查看令牌 |
| `check` | 检查令牌 |
| `log` | 查看事件日志 |
| `trace` | 查看执行追踪 |
| `detailed-log` | 生成详细执行日志 |
| `export` | 导出审计报告 |
| `reset` | 重置步骤 |
| `context` | 查看/清除 Agent 上下文 |
| `validate-project` | 验证项目配置 |
| `loop-start` | 开始循环 |
| `loop-complete` | 完成循环迭代 |
| `wait` | 开始外部等待 |
| `resolve` | 解决外部等待 |
| `loop-back` | 回退到之前步骤 |

---

**文档版本**: v1.6
**最后更新**: 2025-01-22
**维护者**: LEE 框架团队
