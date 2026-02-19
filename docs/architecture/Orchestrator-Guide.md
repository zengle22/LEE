---
title: Workflow Orchestrator
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Workflow Orchestrator

**通用的 AI 工作流编排器 - 让规范从"建议"变成"协议"**

## 核心理念

```
┌─────────────────────────────────────────────────────────────────────┐
│                        传统方式 vs 编排器方式                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  传统方式 (依赖 LLM 自觉):                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                         │
│  │ Step 1  │───▶│ Step 2  │───▶│ Step 3  │   LLM 可以随意跳步      │
│  └─────────┘    └─────────┘    └─────────┘                         │
│       ↓              ↓              ↓                              │
│  (可能跳过)     (可能跳过)     (可能跳过)                           │
│                                                                     │
│  编排器方式 (强制执行):                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Step 1  │───▶│  Gate   │───▶│ Step 2  │───▶│  Gate   │───▶...   │
│  └─────────┘    │ Token ✓ │    └─────────┘    │ Token ✓ │         │
│       │         │ Valid ✓ │         │         │ Valid ✓ │         │
│       │         │ Human ✓ │         │         │ Human ✓ │         │
│       │         └─────────┘         │         └─────────┘         │
│       │              │              │              │               │
│       ▼              ▼              ▼              ▼               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Event Log (自动记录)                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 四个核心问题的解决方案

| 问题 | 解决机制 |
|------|----------|
| Agent 编排可能被跳过 | 状态机 + deps + step token |
| 人类门禁可能被忽略 | gate 产物化 (approval artifact) + 下游强依赖 |
| 产物验证可能被遗漏 | validators 变成 step 必选项，fail-fast |
| 执行日志可能不完整 | 编排器自动记事件流，不依赖 agent |

## 快速开始

```bash
# 1. 初始化工作流运行
python -m orchestrator init ./my-project --workflow workflow.yaml

# 2. 查看当前状态
python -m orchestrator status ./my-project

# 3. 执行下一步 (自动检查门禁)
python -m orchestrator next ./my-project

# 4. 人工审批门禁
python -m orchestrator approve ./my-project h1_plan_review --approver "张三"

# 5. 获取步骤令牌 (用于授权工具调用)
python -m orchestrator token ./my-project step_2

# 6. 验证产物
python -m orchestrator validate ./my-project step_1

# 7. 查看事件日志
python -m orchestrator log ./my-project
```

## 目录结构

```
orchestrator/
├── core/
│   ├── __init__.py
│   ├── state_machine.py    # 状态机实现
│   ├── event_log.py        # 事件溯源日志
│   ├── token_manager.py    # Step Token 管理
│   └── workflow_parser.py  # Workflow 解析器
├── validators/
│   ├── __init__.py
│   ├── schema_validator.py # JSON Schema 验证
│   ├── file_validator.py   # 文件存在性验证
│   └── coverage_validator.py # 覆盖率验证
├── gates/
│   ├── __init__.py
│   ├── human_gate.py       # 人工门禁
│   ├── auto_gate.py        # 自动门禁
│   └── approval_artifact.py # 审批产物
├── adapters/
│   ├── __init__.py
│   ├── claude_adapter.py   # Claude Code 适配器
│   ├── codex_adapter.py    # Codex 适配器
│   └── gemini_adapter.py   # Gemini 适配器
├── cli.py                  # 命令行入口
└── README.md
```

## 跨平台支持

编排器设计为平台无关，通过以下方式实现：

1. **状态文件** - 所有状态存储在文件系统，任何 LLM 都能读取
2. **CLI 接口** - 通过命令行调用，不依赖特定 IDE
3. **适配器模式** - 为不同平台提供适配器
4. **标准协议** - 使用 JSON/YAML 作为数据交换格式

```
┌─────────────────────────────────────────────────────────────────┐
│                        跨平台架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│  │ Claude    │  │ Codex     │  │ Gemini    │  │ Custom    │   │
│  │ Code      │  │ CLI       │  │ Code      │  │ Agent     │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │
│        │              │              │              │          │
│        ▼              ▼              ▼              ▼          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Adapter Layer                         │  │
│  │  (hooks, tool permissions, context injection)            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Orchestrator Core                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │  │
│  │  │ State      │  │ Validator  │  │ Token      │        │  │
│  │  │ Machine    │  │ Engine     │  │ Manager    │        │  │
│  │  └────────────┘  └────────────┘  └────────────┘        │  │
│  │  ┌────────────┐  ┌────────────┐                        │  │
│  │  │ Gate       │  │ Event      │                        │  │
│  │  │ Manager    │  │ Logger     │                        │  │
│  │  └────────────┘  └────────────┘                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   File System                            │  │
│  │  state.yaml | events.jsonl | tokens/ | approvals/        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 与 LLM 的集成方式

### Claude Code

```markdown
<!-- 在 CLAUDE.md 中添加 -->

## 工作流执行规则

执行任何开发任务前，必须：

1. 运行 `python -m orchestrator status .` 检查当前状态
2. 如果有待审批门禁，等待人类审批
3. 获取当前步骤的 token: `python -m orchestrator token . <step_id>`
4. 完成后运行验证: `python -m orchestrator validate . <step_id>`
5. 提交前确认: `python -m orchestrator can-commit .`

违反上述规则的操作将被拒绝。
```

### Codex CLI

```bash
# 在 codex-constitution.yaml 中
pre_execute_hook: "python -m orchestrator check . --token $STEP_TOKEN"
post_execute_hook: "python -m orchestrator complete . --step $STEP_ID"
```

### 通用方式 (任何 LLM)

将编排器状态注入到系统提示词：

```
当前工作流状态:
- 当前步骤: {current_step}
- 待审批门禁: {pending_gates}
- 可用令牌: {available_token}
- 必须产出: {required_outputs}

在开始任何操作前，请确认你有有效的步骤令牌。
```
