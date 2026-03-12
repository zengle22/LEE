---
id: TECH-FEAT-012-001
ssot_type: tech
title: CLI 显式选择执行器能力技术方案
status: active
version: v1
parent_id: FEAT-012-001
derived_from_ids: []
source_refs:
- FEAT-012-001
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

# 技术架构方案：CLI 显式选择执行器能力

## 1. 架构概述

### 1.1 目标
实现 CLI 命令行参数 `--executor <name>` 的解析与路由能力，使用户能够显式指定使用 Kimi 或其他执行器。

### 1.2 核心设计原则
- **最小侵入性**：不修改现有 workflow 模板
- **优先级明确**：CLI 参数 > 默认配置 > 系统预设
- **一致性**：复用现有执行器路由逻辑，无代码重复
- **可扩展性**：支持未来新增执行器类型

## 2. 模块架构设计

### 2.1 模块划分

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLI 参数解析层 (CLI Layer)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  src/lee/cli/commands/run.py                                                │
│  ├── --executor 参数定义 (click.Choice)                                    │
│  └── 参数校验与错误处理                                                      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ executor_override
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          执行器路由决策层 (Routing Layer)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  src/lee/orchestrator/config_loader.py                                      │
│  ├── ExecutorConfig 扩展 (新增 cli_override 支持)                           │
│  └── 优先级决策: CLI > Config > Default                                     │
│                                                                              │
│  src/lee/orchestrator/execution/executors.py                                │
│  └── ExecutorFactory.create() 路由分发                                      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ executor_key
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          执行器实例化层 (Executor Layer)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  src/lee/orchestrator/execution/executors.py                                │
│  ├── KimiExecutor (已存在，复用 LLMExecutor)                               │
│  ├── QwenExecutor (已存在)                                                 │
│  └── 其他执行器 (llm, shell, claude_code, codex 等)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入: lee run <workflow> --executor kimi
                │
                ▼
┌──────────────────────────────┐
│  1. CLI 参数解析              │
│     click.Option --executor  │
│     choices=["llm", "qwen",   │
│              "kimi", ...]    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  2. 参数有效性校验            │
│     检查是否在已注册列表中     │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  3. 传递至 workflow_data      │
│     executor_override = name │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  4. 执行器决策               │
│   Priority:                  │
│   1. executor_override (CLI) │
│   2. config.executor.default │
│   3. "claude_code" (default) │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  5. ExecutorFactory 创建实例  │
│     executor = create(key)   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  6. 执行器执行               │
│     await executor.execute() │
└──────────────────────────────┘
```

## 3. 核心模块技术方案

### 3.1 CLI 参数解析模块

**位置**: `src/lee/cli/commands/run.py`

**现有状态**:
- 第 823 行已存在 `--executor` 参数定义
- 第 1019-1020 行已实现 `executor_override` 传递

**技术方案**:
- 复用现有的 click.Option 定义
- 扩展现有 choices 列表确保包含所有有效执行器
- 增强错误提示，列出可用执行器列表

```python
@click.option("--executor",
    default=None,  # 修改为 None 以支持优先级判断
    help="强制指定执行器类型（覆盖 spec 中的配置）",
    type=click.Choice([
        "llm", "qwen", "kimi", "shell",
        "claude_code", "codex", "langgraph"
    ])
)
```

### 3.2 执行器路由决策模块

**位置**:
- `src/lee/orchestrator/config_loader.py` (配置层)
- `src/lee/orchestrator/execution/executors.py` (工厂层)

**技术方案**:

**阶段 1 - 配置加载 (ConfigLoader)**:
```python
@dataclass
class ExecutorConfig:
    default_type: str = "claude_code"
    cli_override: Optional[str] = None  # 新增：CLI 显式指定

    def get_effective_executor(self) -> str:
        """按优先级返回最终执行器"""
        return self.cli_override or self.default_type
```

**阶段 2 - 工厂路由 (ExecutorFactory)**:
- 复用现有的 `_executors` 注册表
- 复用 `create()` 方法的分发逻辑
- KimiExecutor 已存在，无需新增

### 3.3 执行器实例化模块

**位置**: `src/lee/orchestrator/execution/executors.py`

**现有状态**:
```python
_executors = {
    "llm": LLMExecutor,
    "qwen": QwenExecutor,
    "kimi": KimiExecutor,  # 已存在
    "shell": ShellExecutor,
    "metagpt": MetaGPTExecutor,
    "claude_code": ClaudeCodeExecutor,
    "codex": CodexExecutor,
}
```

**技术方案**: 无需修改，KimiExecutor 已存在且正常工作

## 4. 核心依赖项

### 4.1 内部依赖

| 模块 | 路径 | 用途 | 版本约束 |
|------|------|------|----------|
| ExecutorFactory | `src/lee/orchestrator/execution/executors.py` | 执行器创建与路由 | 现有版本 |
| ExecutorConfig | `src/lee/orchestrator/config_loader.py` | 配置管理 | 需扩展 |
| CLI Run Command | `src/lee/cli/commands/run.py` | 参数解析入口 | 现有版本 |
| KimiExecutor | `src/lee/orchestrator/execution/executors.py` | 目标执行器 | 已存在 |

### 4.2 外部依赖

| 包名 | 用途 | 版本约束 |
|------|------|----------|
| click | CLI 参数解析 | >= 8.0.0 |
| PyYAML | 配置加载 | >= 6.0 |

## 5. 技术不确定性及备份方案

### 5.1 不确定性清单

| 序号 | 不确定性 | 风险等级 | 影响范围 | 备份方案 |
|------|----------|----------|----------|----------|
| UC-01 | CLI 参数与环境变量优先级冲突 | 低 | 配置解析 | 明确优先级文档：CLI > 环境变量 > 配置文件 |
| UC-02 | 无效执行器名称提示信息不完整 | 中 | 用户体验 | 扩展 click 错误处理，列出可用执行器 |
| UC-03 | 现有 Runner 层与 Executor 层命名混淆 | 低 | 代码理解 | 在文档中明确 Runner(kind) vs Executor(provider) 区别 |
| UC-04 | executor_override 传递链路中断 | 中 | 功能可用性 | 添加链路追踪日志，确保参数穿透 |

### 5.2 备份方案详情

**方案 B1 - 显式错误提示增强**:
当用户输入无效执行器时，返回清晰的错误提示：
```python
available = list(ExecutorFactory._executors.keys())
raise click.BadParameter(
    f"无效的执行器: {value}\n"
    f"可用执行器: {', '.join(sorted(available))}"
)
```

**方案 B2 - 降级机制**:
当指定执行器初始化失败时，自动降级至默认执行器：
```python
try:
    return executor_class(**kwargs)
except Exception:
    if executor_type != "claude_code":
        logger.warning(f"{executor_type} 初始化失败，降级至 claude_code")
        return self._executors["claude_code"](**kwargs)
    raise
```

**方案 B3 - 配置热加载**:
如 CLI 参数传递链路复杂，可通过环境变量中转：
```bash
LEE_EXECUTOR_OVERRIDE=kimi lee run <workflow>
```

## 6. Frozen 架构决策记录

### ADR-001: CLI 参数优先级高于配置文件
- **决策**: CLI `--executor` 参数优先级高于 `ExecutorConfig.default_type`
- **原因**: 符合用户直觉，临时切换不应修改配置文件
- **影响**: `run.py` 第 1019-1020 行已实现

### ADR-002: 复用现有 ExecutorFactory
- **决策**: 不复建路由层，复用 `ExecutorFactory._executors` 注册表
- **原因**: 满足 AC-012-001-04 要求，避免代码重复
- **影响**: 无需新增模块，降低维护成本

### ADR-003: 执行器名称校验在 CLI 层完成
- **决策**: 使用 click.Choice 在参数解析时完成校验
- **原因**: 早期失败原则，提供清晰的 CLI 错误提示
- **影响**: 错误在 CLI 层捕获，不进入 workflow 执行流程

### ADR-004: 最小化修改范围
- **决策**: 仅修改配置解析和 CLI 层，不修改 Runner 层和 Executor 层
- **原因**: 满足 Non Goals 要求，不修改现有 workflow 模板
- **影响**: 变更集中在 `config_loader.py` 和 `run.py`

## 7. 验收检查映射

| AC ID | 验收条件 | 技术实现 | 验证方式 |
|-------|----------|----------|----------|
| AC-012-001-01 | CLI 参数解析与传递 | `run.py` click.Option + workflow_data 传递 | 单元测试：模拟 CLI 输入 |
| AC-012-001-02 | 执行器优先级规则 | `ExecutorConfig.get_effective_executor()` | 集成测试：多配置场景 |
| AC-012-001-03 | 无效执行器错误处理 | click.Choice + 自定义错误消息 | 单元测试：无效输入测试 |
| AC-012-001-04 | 与现有实现一致性 | 复用 ExecutorFactory，无平行链路 | 代码审查 + 回归测试 |

## 8. 实施路径

### Phase 1: 配置层扩展 (1h)
- [ ] 修改 `ExecutorConfig`，添加 `cli_override` 字段
- [ ] 实现 `get_effective_executor()` 方法
- [ ] 添加单元测试

### Phase 2: CLI 层增强 (1h)
- [ ] 修改 `--executor` 参数默认值为 `None`
- [ ] 增强错误提示，列出可用执行器
- [ ] 确保 `executor_override` 正确传递至 workflow_data

### Phase 3: 集成验证 (1h)
- [ ] 端到端测试：`lee run --executor kimi`
- [ ] 优先级测试：CLI vs Config vs Default
- [ ] 错误处理测试：无效执行器名称

## 9. 附录

### 9.1 术语表

| 术语 | 定义 |
|------|------|
| Executor | 实际执行任务的组件（如 KimiExecutor, LLMExecutor） |
| Runner | 步骤级别的执行策略（如 LLMRunner, ClaudeCodeRunner） |
| executor_override | CLI 显式指定的执行器标识，覆盖配置 |
| executor_key | 执行器注册键名（如 "kimi", "qwen", "llm"） |

### 9.2 参考文档

- [FEAT-012-001] CLI 显式选择执行器能力
- [src/lee/cli/commands/run.py] CLI 命令实现
- [src/lee/orchestrator/execution/executors.py] 执行器工厂
- [src/lee/orchestrator/config_loader.py] 配置加载器

---

**架构冻结声明**: 本文档已经过技术评审，架构方案进入冻结状态。后续变更需经过变更控制流程。

**核准人**: ________________  **日期**: ________________
