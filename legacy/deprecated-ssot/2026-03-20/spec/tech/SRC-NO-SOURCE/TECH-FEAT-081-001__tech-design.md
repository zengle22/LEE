---
id: TECH-FEAT-081-001
ssot_type: tech
title: FEAT-081 Workflow-First CLI 技术架构
status: frozen
version: v1
parent_id: FEAT-081
derived_from_ids:
- ADR-006
source_refs:
- FEAT-081#scope
- FEAT-081#acceptance
- ADR-006
- UI-FEAT-081-001
- TASK-FEAT-081-001
- TASK-FEAT-081-002
owner: null
tags:
- cli
- workflow-first
- governance
- architecture
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

contract_type: frozen-technical-architecture
contract_version: '1.0'
metadata:
  contract_id: FTA-20260312-081
  title: FEAT-081 Workflow-First CLI 技术架构
  description: ADR/EPIC/FEAT Workflow-First 入口暴露的技术实现方案
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-12T00:00:00Z'
  feat_ref: FEAT-081
  ui_ref: UI-FEAT-081-001
  governing_adr: ADR-006
  designer: Architecture Designer
  reviewer: 待人类评审

# 1. 架构目标与约束

## 1.1 目标

实现 `lee adr new` / `lee epic new` / `lee feat new` 三条 CLI 命令，作为 ADR、EPIC、FEAT 三类正式对象的 workflow-first 高层入口，确保：
- 用户默认通过治理流程创建正式对象
- 阻止绕过 workflow 直接创建对象
- 命令帮助文案明确说明治理流程属性

## 1.2 约束来源 (Governing Constraints)

### 1.2.1 ADR-006 硬约束
- 面向用户的正式入口必须是高层命令或 workflow 命令
- `ssot create` 重新定位为调试/数据修复/补录/管理员命令
- 正式对象创建必须经由 workflow 或高层命令触发
- `ssot create` 和 `ArtifactManager.create_ssot()` 只负责最终物化
- 正式 SSOT ID 分配必须与治理链联动

### 1.2.2 UI-FEAT-081-001 交互约束
- 命令命名：`lee <object-type> <action>` 格式（即 `lee adr new`）
- 强制交互式 Workflow，不允许完全静默创建
- 帮助文案必须包含'通过治理流程'字样
- 响应时间：<100ms 响应确认，<1s 操作反馈，>1s 进度提示
- 创建前必须显式确认

### 1.2.3 FEAT-081 验收约束
- 命令必须出现在主 help 的 Workflow Commands 分组中
- 命令内部必须调用对应 workflow 模板启动流程
- 用户无法通过这些命令绕过 workflow 直接创建对象

# 2. 技术选型

## 2.1 核心技术栈

| 层级 | 技术选型 | 版本约束 | 选型理由 |
|------|----------|----------|----------|
| CLI 框架 | Click (Python) | >=8.0 | 项目现有 CLI 基于 Click 构建，保持一致性；支持命令分组、嵌套命令、帮助文本定制 |
| 交互式 UI | click.prompt + click.confirm | 内置 | 无需额外依赖，支持交互式 wizard 基础能力 |
| 富文本输出 | rich (可选) | >=13.0 | 增强视觉反馈（spinner、checkmark、进度条），提供优雅降级 |
| Workflow 调用 | pm_workflow API | current | 项目既有 workflow 编排 API，支持 instance 创建和状态管理 |
| 配置管理 | YAML + Python Dataclass | N/A | 与项目现有配置体系一致 |
| 模板引擎 | Jinja2 | >=3.0 | 与现有 workflow 模板系统一致 |

## 2.2 关键技术依赖

### 2.2.1 核心依赖 (不可替换)
- `lee.orchestrator.api.pm_workflow`: Workflow 实例创建和执行 API
- `lee.cli.commands.workflow_registry`: Workflow 模板注册和解析
- `lee.orchestrator.execution.artifacts.ArtifactManager`: SSOT 物化管理
- `click.Group`: CLI 命令分组管理

### 2.2.2 可选依赖 (有降级方案)
- `rich.console.Console`: 富文本输出，降级为 `click.echo`
- `rich.prompt.Prompt`: 交互式提示，降级为 `click.prompt`
- `rich.status.Status`: 进度 spinner，降级为文本输出

# 3. 架构设计

## 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User-Facing Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ lee adr new  │  │ lee epic new │  │ lee feat new │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
└─────────┼─────────────────┼─────────────────┼───────────────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Workflow Command Module                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              SSOTCreateCommands (Click Group)                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │  │
│  │  │  adr()       │  │  epic()      │  │  feat()      │             │  │
│  │  │  (group)     │  │  (group)     │  │  (group)     │             │  │
│  │  │    └── new() │  │    └── new() │  │    └── new() │             │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interactive Wizard Layer                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              WorkflowWizard                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │  │
│  │  │ Step 1:      │  │ Step 2:      │  │ Step 3:      │             │  │
│  │  │ 收集标题     │  │ 收集描述     │  │ 确认创建     │             │  │
│  │  │ (必填)       │  │ (可选)       │  │ (预览+确认)  │             │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐                               │  │
│  │  │ Validation   │  │ Confirmation │                               │  │
│  │  │ (字段级验证) │  │ (Y/n/Edit)   │                               │  │
│  │  └──────────────┘  └──────────────┘                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Workflow Integration Layer                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              WorkflowLauncher                                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │  │
│  │  │ Template Path   │  │ Render Params   │  │ pm_workflow()   │    │  │
│  │  │ Resolution      │──│ (Jinja2)        │──│ API Call        │    │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘    │  │
│  │                                                                   │  │
│  │  Workflow Templates:                                              │  │
│  │  - governance.adr-create → spec-global/.../adr-create/v1/        │  │
│  │  - product.epic-create   → spec-global/.../epic-create/v1/        │  │
│  │  - product.feat-create   → spec-global/.../feat-create/v1/        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Governance & Safety Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │ DirectCreation   │  │ Git Pre-commit   │  │ CI Validation    │       │
│  │ Blocker          │  │ Hook             │  │ (GitHub Actions) │       │
│  │                  │  │                  │  │                  │       │
│  │ front_matter     │  │ workflow_instance│  │ validate_ssot_   │       │
│  │ validation       │  │ _id check        │  │ creation.py      │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3.2 核心组件设计

### 3.2.1 SSOTCreateCommands (CLI 命令组)

**职责**: 定义和管理 `lee adr/epic/feat` 命令组及其子命令

**实现要点**:
```python
# src/lee/cli/commands/ssot_create.py

import click
from typing import Optional

@click.group()
def adr():
    """ADR 决策记录管理 (通过治理流程)"""
    pass

@click.group()
def epic():
    """EPIC 需求管理 (通过治理流程)"""
    pass

@click.group()
def feat():
    """FEAT 特性管理 (通过治理流程)"""
    pass

@adr.command('new')
@click.option('--title', '-t', required=True, help='ADR 标题')
@click.option('--context', '-c', help='决策上下文/背景')
@click.option('--dry-run', is_flag=True, help='预览创建结果，不实际执行')
def adr_new(title: str, context: Optional[str], dry_run: bool):
    """通过治理流程创建新的 ADR 决策记录

    此命令将启动 ADR 创建 workflow，通过交互式向导收集信息，
    并在冻结前提供确认步骤。创建的对象将自动进入治理流程。
    """
    pass  # 实现见 WorkflowWizard

@epic.command('new')
@click.option('--title', '-t', required=True, help='EPIC 标题')
@click.option('--goal', '-g', help='EPIC 目标')
@click.option('--dry-run', is_flag=True, help='预览创建结果，不实际执行')
def epic_new(title: str, goal: Optional[str], dry_run: bool):
    """通过治理流程创建新的 EPIC 需求

    此命令将启动 EPIC 创建 workflow，通过交互式向导收集信息，
    并在冻结前提供确认步骤。创建的对象将自动进入治理流程。
    """
    pass

@feat.command('new')
@click.option('--title', '-t', required=True, help='FEAT 标题')
@click.option('--parent', '-p', help='父 EPIC ID (可选)')
@click.option('--dry-run', is_flag=True, help='预览创建结果，不实际执行')
def feat_new(title: str, parent: Optional[str], dry_run: bool):
    """通过治理流程创建新的 FEAT 特性

    此命令将启动 FEAT 创建 workflow，通过交互式向导收集信息，
    并在冻结前提供确认步骤。创建的对象将自动进入治理流程。
    """
    pass
```

**设计决策**:
- 采用 `lee <object> <action>` 命名模式（DD-001）
- 每个命令组独立定义，便于后续扩展子命令（如 `lee adr list`）
- 帮助文案强制包含"通过治理流程"字样（DD-003）

### 3.2.2 WorkflowWizard (交互向导)

**职责**: 管理交互式 workflow 启动流程，收集用户输入，执行验证，显示进度

**核心流程**:
```
[开始] → [显示工作流标识] → [步骤1:收集必填字段] → [实时验证]
  ↓
[步骤N:收集选填字段] → [预览汇总] → [确认对话框 Y/n/Edit]
  ↓
[调用 pm_workflow] → [显示进度] → [成功/失败反馈] → [结束]
```

**状态机设计**:
- `STATE-001 MAIN_HELP`: 主帮助展示，Workflow Commands 分组置顶
- `STATE-002 COMMAND_HELP`: 命令帮助，醒目标题框强调治理流程
- `STATE-003 WORKFLOW_RUNNING`: 工作流执行中，进度指示 (Step X/Y)
- `STATE-004 VALIDATION_FEEDBACK`: 字段级验证反馈
- `STATE-005 CONFIRMATION_DIALOG`: 创建前确认，支持 Y/n/Edit
- `STATE-006 SUCCESS`: 成功反馈，显示引用 ID 和下一步指引
- `STATE-007 ERROR`: 错误处理，分类说明和解决方案

**交互时序**:
| 阶段 | 目标响应时间 | 视觉反馈 |
|------|-------------|----------|
| 命令确认 | <100ms | 立即显示 [WORKFLOW] 标识 |
| 步骤切换 | <1s | spinner + 步骤指示 |
| 长操作 | >1s | 进度条 + 预计时间 |
| 成功 | - | checkmark + 结果卡片 |
| 错误 | - | cross + 诊断信息 |

### 3.2.3 WorkflowLauncher (Workflow 启动器)

**职责**: 封装 workflow 模板渲染和 pm_workflow API 调用

**核心方法**:
```python
class WorkflowLauncher:
    """Workflow 启动器，负责模板渲染和实例创建"""

    WORKFLOW_MAP = {
        'adr': 'governance.adr-create',
        'epic': 'product.epic-create',
        'feat': 'product.feat-create',
    }

    def launch(self, object_type: str, params: dict, dry_run: bool = False) -> WorkflowResult:
        """
        启动指定类型的 workflow

        Args:
            object_type: 'adr', 'epic', 或 'feat'
            params: 用户收集的参数
            dry_run: 是否为预览模式

        Returns:
            WorkflowResult: 包含 workflow_id、status、输出路径
        """
        workflow_key = self.WORKFLOW_MAP[object_type]
        template_path = self._resolve_template(workflow_key)

        # 渲染模板参数
        rendered = self._render_template(template_path, params)

        if dry_run:
            return WorkflowResult.preview(rendered)

        # 调用 pm_workflow API 创建实例
        result = pm_workflow(
            'create',
            template_id=str(rendered),
            data={'params': params, 'workflow_key': workflow_key}
        )

        return WorkflowResult.from_api(result)
```

### 3.2.4 DirectCreationBlocker (防绕过机制)

**职责**: 确保所有正式 SSOT 对象必须通过 workflow 创建，阻止直接创建

**三层防护架构**:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Front Matter Validation (SSOT 文件级)              │
│ ─────────────────────────────────────────────────────────   │
│ 检查所有新建的 SSOT 文件 front_matter 中是否包含            │
│ workflow_instance_id 字段                                  │
│                                                            │
│ 验证规则:                                                  │
│ - frozen 状态的 SSOT 必须有 workflow_instance_id          │
│ - 检查 parent_id 链的完整性                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Git Pre-commit Hook (版本控制级)                   │
│ ─────────────────────────────────────────────────────────   │
│ 在 commit 前拦截无 workflow_instance_id 的 SSOT 文件        │
│                                                            │
│ 实现: .githooks/pre-commit                                 │
│ - 扫描暂存区新增的 SSOT 文件                               │
│ - 验证 front_matter 完整性                                │
│ - 阻止不合规的 commit                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: CI Pipeline Validation (持续集成级)                │
│ ─────────────────────────────────────────────────────────   │
│ GitHub Actions 工作流在 PR 时执行验证                       │
│                                                            │
│ 实现: .github/workflows/ssot-governance-check.yml          │
│ - 调用 validate_ssot_creation.py                          │
│ - 检查 PR 中新增的 SSOT 文件                               │
│ - 失败时阻止 PR 合并                                       │
└─────────────────────────────────────────────────────────────┘
```

**验证规则**:
1. **ADR 创建**: 必须通过 `governance.adr-create` workflow
2. **EPIC 创建**: 必须通过 `product.epic-create` workflow
3. **FEAT 创建**: 必须通过 `product.feat-create` workflow

## 3.3 Workflow 模板设计

### 3.3.1 governance.adr-create Workflow

```yaml
kind: l3_workflow_template
version: "1.0"
id: workflow.governance.adr-create
name: ADR Create Workflow
description: 通过治理流程创建 ADR 决策记录

roles:
  agents:
    - agent.governance.adr_drafter
    - agent.governance.adr_reviewer
  gates:
    - gate.governance.adr_freeze

stages:
  - id: adr_creation_flow
    name: ADR Creation Flow
    steps:
      - id: draft_adr
        name: 起草 ADR
        kind: agent
        agent_id: agent.governance.adr_drafter
        inputs:
          - source: cli_params
            required: true
        outputs:
          - symbol: adr_draft
            freeze: false

      - id: review_adr
        name: ADR 评审
        kind: agent
        agent_id: agent.governance.adr_reviewer
        depends_on: [draft_adr]
        outputs:
          - symbol: adr_review_report
            freeze: false

      - id: adr_freeze
        name: ADR 冻结
        kind: gate
        depends_on: [review_adr]
        gate_rules:
          reviewers:
            - role: architect
          approval_criteria:
            - label: "决策完整性"
              criteria: "包含问题、决策、影响分析"
        outputs:
          - path: spec/adr/ADR-XXX.md
            freeze: true
            ssot:
              identity_kind: ssot
              ssot_type: ADR
              workflow_instance_id: "{{ workflow.id }}"  # 关键：绑定 workflow
```

### 3.3.2 product.epic-create Workflow

```yaml
kind: l3_workflow_template
version: "1.0"
id: workflow.product.epic-create
name: EPIC Create Workflow
description: 通过治理流程创建 EPIC 需求

roles:
  agents:
    - agent.product.epic_drafter
    - agent.product.epic_reviewer
  gates:
    - gate.product.epic_freeze

stages:
  - id: epic_creation_flow
    name: EPIC Creation Flow
    steps:
      - id: draft_epic
        name: 起草 EPIC
        kind: agent
        agent_id: agent.product.epic_drafter
        outputs:
          - symbol: epic_draft
            freeze: false

      - id: epic_freeze
        name: EPIC 冻结
        kind: gate
        depends_on: [draft_epic]
        outputs:
          - path: spec/requirements/epics/EPIC-XXX.md
            freeze: true
            ssot:
              identity_kind: ssot
              ssot_type: EPIC
              workflow_instance_id: "{{ workflow.id }}"
```

### 3.3.3 product.feat-create Workflow

```yaml
kind: l3_workflow_template
version: "1.0"
id: workflow.product.feat-create
name: FEAT Create Workflow
description: 通过治理流程创建 FEAT 特性

roles:
  agents:
    - agent.product.feat_drafter
    - agent.product.feat_reviewer
  gates:
    - gate.product.feat_freeze

stages:
  - id: feat_creation_flow
    name: FEAT Creation Flow
    steps:
      - id: draft_feat
        name: 起草 FEAT
        kind: agent
        agent_id: agent.product.feat_drafter
        inputs:
          - source: parent_epic  # 可选的父 EPIC
            required: false
        outputs:
          - symbol: feat_draft
            freeze: false

      - id: feat_freeze
        name: FEAT 冻结
        kind: gate
        depends_on: [draft_feat]
        outputs:
          - path: spec/requirements/features/FEAT-XXX.md
            freeze: true
            ssot:
              identity_kind: ssot
              ssot_type: FEAT
              workflow_instance_id: "{{ workflow.id }}"
```

## 3.4 CLI 集成设计

### 3.4.1 命令注册

在 `src/lee/cli/main.py` 中注册 Workflow Commands 分组:

```python
def _register_commands() -> None:
    # ... 现有命令注册 ...

    from lee.cli.commands.ssot_create import adr, epic, feat

    # 注册到 Workflow Commands 分组
    cli.add_command(adr)
    cli.add_command(epic)
    cli.add_command(feat)
```

### 3.4.2 帮助分组配置

自定义 Click Group 实现 Workflow Commands 置顶:

```python
class WorkflowFirstGroup(click.Group):
    """自定义 Group，将 Workflow Commands 分组置顶"""

    WORKFLOW_COMMANDS = {'adr', 'epic', 'feat'}

    def format_commands(self, ctx, formatter):
        # 分离 workflow 命令和普通命令
        workflow_cmds = []
        other_cmds = []

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if subcommand in self.WORKFLOW_COMMANDS:
                workflow_cmds.append((subcommand, cmd))
            else:
                other_cmds.append((subcommand, cmd))

        # 先输出 Workflow Commands
        if workflow_cmds:
            with formatter.section('Workflow Commands (通过治理流程)'):
                formatter.write_dl([
                    (name, cmd.get_short_help_str())
                    for name, cmd in workflow_cmds
                ])

        # 再输出其他命令
        if other_cmds:
            with formatter.section('Commands'):
                formatter.write_dl([
                    (name, cmd.get_short_help_str())
                    for name, cmd in other_cmds
                ])
```

# 4. 核心依赖清单

## 4.1 运行时依赖

| 依赖名 | 类型 | 版本 | 用途 | 风险等级 |
|--------|------|------|------|----------|
| click | runtime | >=8.0 | CLI 框架基础 | 低 |
| pyyaml | runtime | >=6.0 | YAML 解析 | 低 |
| jinja2 | runtime | >=3.0 | 模板渲染 | 低 |
| rich | runtime (optional) | >=13.0 | 富文本输出 | 低 |

## 4.2 内部依赖

| 依赖名 | 类型 | 用途 | 风险等级 |
|--------|------|------|----------|
| lee.orchestrator.api.pm_workflow | internal | Workflow API | 中 |
| lee.cli.commands.workflow_registry | internal | Workflow 注册表 | 中 |
| lee.orchestrator.execution.artifacts | internal | SSOT 物化 | 低 |
| lee.cli.main | internal | CLI 主入口 | 中 |

## 4.3 外部工具依赖

| 工具 | 用途 | 必需 |
|------|------|------|
| Git | Pre-commit hook | 是 |
| GitHub Actions | CI 验证 | 是 (对于协作) |

# 5. 技术风险与备份方案

## 5.1 高风险点

### R-001: Workflow 引擎依赖风险

**风险描述**: `pm_workflow` API 的行为变更可能导致命令无法正常启动 workflow

**影响**: 高 - 核心功能不可用
**概率**: 中

**缓解措施**:
1. 封装 WorkflowLauncher 层，隔离 API 变化
2. 实现降级路径：当 API 不可用时，提示用户使用 `lee run` 手动启动
3. 增加 API 响应验证，提供清晰的错误信息

**降级策略**:
```python
def launch_with_fallback(object_type: str, params: dict):
    try:
        return self.launch(object_type, params)
    except WorkflowAPIError as e:
        click.echo(f"⚠️  Workflow API 暂时不可用: {e}")
        click.echo("请使用以下命令手动启动 workflow:")
        click.echo(f"  lee run {WORKFLOW_MAP[object_type]} --spec <params_file>")
        raise click.ClickException("自动启动失败，请手动执行")
```

### R-002: 交互式体验阻塞风险

**风险描述**: 强制交互式 wizard 在 CI/CD 或脚本环境中无法使用

**影响**: 中 - 自动化场景受阻
**概率**: 高

**缓解措施**:
1. 保留 `--spec` 参数支持，允许从文件加载参数
2. 检测非交互式环境（`stdin.isatty()`），自动切换到批处理模式
3. 提供 `--yes` / `-y` 参数跳过确认步骤

**降级策略**:
```python
if not click.get_text_stream('stdin').isatty():
    # 非交互模式：要求提供 --spec 或所有必需参数
    if not spec_file:
        raise click.ClickException("非交互模式需要提供 --spec 参数")
    return self._batch_mode_launch(spec_file)
```

### R-003: Workflow 模板缺失风险

**风险描述**: `adr-create` / `epic-create` / `feat-create` workflow 模板可能未部署

**影响**: 高 - 命令无法执行
**概率**: 中

**缓解措施**:
1. 命令启动前检查模板存在性
2. 提供清晰的模板缺失错误信息
3. 引导用户使用 `lee workflow list` 查看可用模板

**降级策略**:
```python
def _ensure_template_exists(workflow_key: str):
    registry = load_workflow_registry()
    if workflow_key not in registry.get('workflows', {}):
        click.echo(f"❌ Workflow 模板 '{workflow_key}' 未找到")
        click.echo("可用 workflow 列表:")
        # 显示相似模板建议
        suggestions = fuzzy_search(registry['workflows'].keys(), workflow_key)
        for s in suggestions:
            click.echo(f"  - {s}")
        raise click.ClickException("模板缺失")
```

### R-004: 防绕过机制绕过风险

**风险描述**: 技术熟练用户可能通过修改 front_matter 或 hook 绕过防护

**影响**: 中 - 治理流程被绕过
**概率**: 低

**缓解措施**:
1. 三层防护（front_matter + pre-commit + CI）提高绕过成本
2. 在 CI 中进行深度验证，检查 workflow_instance_id 的真实性
3. 审计日志记录所有 SSOT 创建操作
4. 定期扫描 registry 中异常对象

**降级策略**:
- 发现绕过行为时，触发治理流程审查
- 异常对象标记为 `suspicious` 状态，人工确认

## 5.2 技术不确定性

### U-001: 参数传递机制

**不确定性**: CLI 收集的参数如何高效传递给 workflow 模板
**当前假设**: 通过 Jinja2 模板渲染注入
**验证方法**: 原型实现验证参数传递完整性

**备份方案**:
- 如模板渲染复杂，改用 YAML 合并方式生成 workflow instance
- 或直接通过 pm_workflow data 字段传递完整参数对象

### U-002: Workflow 实例状态跟踪

**不确定性**: CLI 如何实时获取 workflow 执行状态和结果
**当前假设**: 轮询 pm_workflow API 获取状态更新
**验证方法**: 验证长流程（>30s）的状态跟踪稳定性

**备份方案**:
- 如轮询不稳定，改用事件驱动架构（SQLite trigger + callback）
- 或改为异步模式：启动 workflow 后返回 instance_id，用户自行查询

### U-003: 父子关系自动建立

**不确定性**: FEAT 如何自动关联到正确的父 EPIC
**当前假设**: 用户通过 `--parent` 参数指定，或从 workflow 上下文推断
**验证方法**: 验证 parent_id 在 SSOT 文件中的正确写入

**备份方案**:
- 如自动推断不可靠，改为强制要求 `--parent` 参数
- 或在 workflow 中增加 parent 选择步骤

# 6. 验收映射

| AC ID | 技术组件 | 验证方法 |
|-------|----------|----------|
| AC-002-001 | WorkflowFirstGroup.format_commands | `lee --help` 输出中 Workflow Commands 分组置顶，包含 adr/epic/feat |
| AC-002-002 | WorkflowLauncher.launch | `lee adr new` 执行后启动对应 workflow，返回 workflow_id |
| AC-002-003 | click.Command.help | `lee adr new --help` 输出包含"通过治理流程"字样 |
| AC-002-004 | DirectCreationBlocker | 无 workflow_instance_id 的 SSOT 文件被 pre-commit hook 阻止 |

# 7. 测试策略

## 7.1 单元测试

- `WorkflowLauncher` 参数渲染逻辑
- `DirectCreationBlocker` front_matter 验证逻辑
- `WorkflowWizard` 状态机转换
- `WorkflowFirstGroup` 命令分组逻辑

## 7.2 集成测试

- `lee adr new --dry-run` → 预览模式正确渲染
- `lee adr new --title "Test"` → 交互式 wizard 启动
- `lee adr new --spec params.yaml` → 批处理模式正确执行
- 无 workflow_instance_id 的文件提交 → pre-commit 拦截

## 7.3 E2E 测试

- 完整 workflow 执行：命令 → wizard → workflow 启动 → SSOT 创建
- 防绕过验证：直接修改文件 → commit 被阻止 → 通过 workflow 创建成功

# 8. 交付物清单

| 交付物 | 路径 | 类型 |
|--------|------|------|
| CLI 命令模块 | src/lee/cli/commands/ssot_create.py | 代码 |
| CLI 主入口更新 | src/lee/cli/main.py | 代码修改 |
| ADR Create Workflow | spec-global/core/workflows/adr-create/v1/workflow.yaml | 配置 |
| EPIC Create Workflow | spec-global/departments/product/workflows/templates/epic-create/v1/workflow.yaml | 配置 |
| FEAT Create Workflow | spec-global/departments/product/workflows/templates/feat-create/v1/workflow.yaml | 配置 |
| Pre-commit Hook | .githooks/pre-commit | 脚本 |
| CI Workflow | .github/workflows/ssot-governance-check.yml | 配置 |
| 防绕过验证模块 | src/lee/governance/ci/validate_ssot_creation.py | 代码 |

# 9. SSOT 输出合约

```yaml
contract_version: '1.0'
run_id: tech-arch-fe-081
outputs:
  - key: tech_architecture
    identity_kind: ssot
    ssot_type: tech
    title: FEAT-081 Frozen Technical Architecture
    parent: FEAT-081
    implements:
      - FEAT-081
    trace_to:
      - ADR-006
      - UI-FEAT-081-001
```

---

**状态**: FROZEN
**冻结时间**: 2026-03-12T00:00:00Z
**核准人**: 待人类评审
