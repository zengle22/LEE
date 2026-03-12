---
id: TECH-FEAT-012-002
ssot_type: tech
title: 默认执行器配置能力技术方案
status: active
version: v1
parent_id: FEAT-012-002
derived_from_ids: []
source_refs:
- FEAT-012-002
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

# Frozen Technical Architecture — 默认执行器配置能力

## Document Info
- **Feature**: FEAT-012-002
- **Title**: 默认执行器配置能力
- **Status**: Frozen (Pending Human Approval)
- **Version**: v1.0
- **Date**: 2026-03-12

---

## 1. 架构概览

### 1.1 目标
实现配置系统对默认 coding executor 的支持，允许用户通过配置文件设置默认执行器，简化日常使用流程。

### 1.2 架构原则
1. **向后兼容**：不破坏现有 CLI 行为，CLI 参数始终优先于配置
2. **渐进式加载**：配置在 CLI 启动时加载，变更在下次执行时生效
3. **优雅降级**：配置无效或缺失时，自动回退到系统预设默认值
4. **单一职责**：配置加载、验证、应用分层处理

---

## 2. 模块设计

### 2.1 模块结构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Entry (lee run)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Priority Resolution                                                │    │
│  │  1. CLI --executor parameter                                        │    │
│  │  2. Config default_coding_executor                                  │    │
│  │  3. System fallback (claude_code)                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Config Loader (Enhanced)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  ExecutorConfig (Extended)                                          │    │
│  │  - default_type: str              (现有)                            │    │
│  │  - coding_executor: str           (现有，内部使用)                   │    │
│  │  - coding_fallback: str           (现有)                            │    │
│  │  - default_coding_executor: str   (新增，用户配置)                   │    │
│  │  - llm_model: Optional[str]       (现有)                            │    │
│  │  - timeout_seconds: int           (现有)                            │    │
│  │  - VALID_EXECUTORS: ClassVar[List[str]]  (新增，有效值列表)          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Validation Layer                                                   │    │
│  │  - 配置值类型校验                                                   │    │
│  │  - 执行器有效性校验 (是否在 VALID_EXECUTORS 中)                      │    │
│  │  - 无效配置警告 + 降级处理                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Workflow Runner / Executor Router                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Executor Selection Logic                                           │    │
│  │  - resolve_executor(cli_override, config_value) -> str              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块说明

#### 2.2.1 Config Loader 扩展 (`lee/orchestrator/config_loader.py`)

**现状**：已有 `ExecutorConfig` dataclass，包含 `coding_executor` 字段（内部使用）

**变更**：
1. 新增 `default_coding_executor` 字段，用于用户配置
2. 新增 `VALID_EXECUTORS` 类变量，定义有效执行器列表
3. 增强 `from_dict` 方法，添加配置验证逻辑
4. 新增 `get_effective_coding_executor()` 方法，处理优先级逻辑

**优先级规则**：
```python
def resolve_coding_executor(cli_override: Optional[str],
                           config_default: Optional[str]) -> str:
    """
    执行器选择优先级：
    1. CLI --executor 参数（显式指定）
    2. Config default_coding_executor（用户偏好）
    3. 系统预设默认值 (claude_code)
    """
    if cli_override:
        return cli_override
    if config_default and _is_valid_executor(config_default):
        return config_default
    return "claude_code"  # 系统预设默认值
```

#### 2.2.2 CLI 层适配 (`lee/cli/commands/run.py`)

**现状**：`--executor` 参数默认值为 `"claude_code"`，通过 `executor_override` 传递给 workflow

**变更**：
1. 修改 `--executor` 参数默认值为 `None`（允许检测是否显式指定）
2. 在命令处理函数中，调用 `ConfigLoader` 获取配置
3. 使用 `resolve_coding_executor()` 解析最终执行器
4. 保持 `executor_override` 传递机制不变

**关键代码变更**：
```python
# 修改前
@click.option("--executor", default="claude_code", ...)

# 修改后
@click.option("--executor", default=None, ...)

def run(..., executor: Optional[str], ...):
    # 加载配置
    config = load_config(project_dir)

    # 解析最终执行器
    effective_executor = resolve_coding_executor(
        cli_override=executor,
        config_default=config.executor.default_coding_executor
    )

    # 传递给 workflow
    if effective_executor:
        workflow_data["executor_override"] = effective_executor
```

#### 2.2.3 配置验证层

**验证规则**：
1. 类型校验：`default_coding_executor` 必须为字符串
2. 有效性校验：值必须在 `VALID_EXECUTORS` 列表中
3. 无效处理：记录警告日志，使用系统预设默认值

**有效执行器列表**：
```python
VALID_CODING_EXECUTORS = [
    "claude_code",  # 默认
    "kimi",
    "qwen",
    "llm",
    "shell",
    "codex",
    "langgraph"
]
```

---

## 3. 数据模型

### 3.1 配置文件 Schema

**文件位置**：`.lee/config.yaml`

**完整配置示例**：
```yaml
# 现有配置
spec_root: spec-global
demo_mode: false

# 执行器配置
executor:
  default_type: claude_code
  default_coding_executor: kimi      # 新增：用户默认编码执行器
  coding_executor: claude_code       # 内部使用（保持向后兼容）
  coding_fallback: llm_patch
  llm_model: gpt-4
  timeout_seconds: 600

# 其他配置
retry:
  max_retries: 3
  retry_delay_seconds: 2.0

tracing:
  enabled: true
  output_dir: .workflow/traces
```

**JSON 格式支持**（同 Schema）：
```json
{
  "executor": {
    "default_coding_executor": "kimi"
  }
}
```

### 3.2 配置类定义

```python
@dataclass
class ExecutorConfig:
    """执行器配置"""
    # 系统默认执行器类型
    default_type: str = "claude_code"

    # 用户配置的默认 coding 执行器（新增）
    default_coding_executor: Optional[str] = None

    # 编码步骤首选执行器（内部使用，向后兼容）
    coding_executor: str = "claude_code"

    # 编码步骤降级执行器
    coding_fallback: str = "llm_patch"

    # 其他配置
    llm_model: Optional[str] = None
    timeout_seconds: int = 600

    # 有效执行器列表（类变量）
    VALID_EXECUTORS: ClassVar[List[str]] = field(default_factory=lambda: [
        "claude_code", "kimi", "qwen", "llm", "shell", "codex", "langgraph"
    ])

    # 系统预设默认值（类变量）
    FALLBACK_EXECUTOR: ClassVar[str] = "claude_code"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutorConfig":
        # 基础字段解析
        config = cls(
            default_type=data.get("default_type", "claude_code"),
            default_coding_executor=data.get("default_coding_executor"),
            coding_executor=data.get("coding_executor", "claude_code"),
            coding_fallback=data.get("coding_fallback", "llm_patch"),
            llm_model=data.get("llm_model"),
            timeout_seconds=data.get("timeout_seconds", 600),
        )

        # 配置验证
        config._validate()
        return config

    def _validate(self) -> None:
        """验证配置有效性"""
        if self.default_coding_executor is None:
            return

        if not isinstance(self.default_coding_executor, str):
            logger.warning(
                f"Invalid default_coding_executor type: {type(self.default_coding_executor)}, "
                f"expected str. Using fallback."
            )
            self.default_coding_executor = None
            return

        if self.default_coding_executor not in self.VALID_EXECUTORS:
            logger.warning(
                f"Unknown executor '{self.default_coding_executor}'. "
                f"Valid options: {', '.join(self.VALID_EXECUTORS)}. "
                f"Using fallback '{self.FALLBACK_EXECUTOR}'."
            )
            # 保留原始值供用户查看，但标记为无效
            self._invalid_executor = self.default_coding_executor
            self.default_coding_executor = None

    def get_effective_executor(self, cli_override: Optional[str] = None) -> str:
        """
        获取最终生效的执行器

        优先级：
        1. CLI 显式指定
        2. 配置中的 default_coding_executor
        3. 系统预设默认值
        """
        if cli_override:
            return cli_override
        if self.default_coding_executor:
            return self.default_coding_executor
        return self.FALLBACK_EXECUTOR
```

---

## 4. 接口定义

### 4.1 内部接口

#### `resolve_coding_executor()`

```python
def resolve_coding_executor(
    cli_override: Optional[str],
    config_value: Optional[str],
    valid_executors: Optional[List[str]] = None,
    fallback: str = "claude_code"
) -> Tuple[str, Optional[str]]:
    """
    解析最终生效的 coding executor

    Args:
        cli_override: CLI 显式指定的执行器
        config_value: 配置文件中指定的默认执行器
        valid_executors: 有效执行器列表（可选，使用默认值）
        fallback: 降级使用的默认执行器

    Returns:
        Tuple[生效的执行器, 警告信息（如有）]
    """
```

#### `ExecutorConfig.get_effective_executor()`

```python
def get_effective_executor(self, cli_override: Optional[str] = None) -> str:
    """获取最终生效的执行器，处理优先级逻辑"""
```

### 4.2 配置加载接口（现有，保持不变）

```python
def load_config(
    project_root: Optional[str] = None,
    config_path: Optional[str] = None
) -> LeeConfig:
    """加载项目配置"""
```

---

## 5. 核心依赖项

### 5.1 内部依赖

| 模块 | 路径 | 用途 |
|------|------|------|
| ConfigLoader | `lee/orchestrator/config_loader.py` | 配置加载与解析 |
| LeeConfig | `lee/orchestrator/config_loader.py` | 主配置数据类 |
| ExecutorConfig | `lee/orchestrator/config_loader.py` | 执行器配置数据类 |
| CLI run command | `lee/cli/commands/run.py` | CLI 入口与参数处理 |

### 5.2 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| PyYAML | >=6.0 | YAML 配置文件解析 |
| click | >=8.0 | CLI 框架 |
| pydantic (可选) | >=2.0 | 配置验证增强（备选方案） |

---

## 6. 技术风险与备份方案

### 6.1 风险识别

| 风险项 | 严重程度 | 描述 |
|--------|----------|------|
| R1 - 命名冲突 | 中 | 现有 `coding_executor` 与新增 `default_coding_executor` 语义区分不清 |
| R2 - 向后兼容 | 高 | CLI `--executor` 默认值变更可能影响现有脚本 |
| R3 - 配置格式扩展 | 低 | JSON 格式支持需要额外测试 |
| R4 - 验证逻辑复杂度 | 低 | 多层验证可能导致代码复杂 |

### 6.2 风险缓解方案

#### R1 - 命名冲突

**问题**：现有 `ExecutorConfig.coding_executor` 用于内部执行器选择，新增 `default_coding_executor` 用于用户配置，两者语义相近。

**解决方案**：
1. **文档澄清**：
   - `coding_executor`：内部运行时使用的执行器（工作流内部使用）
   - `default_coding_executor`：用户偏好设置的默认执行器（CLI 使用）

2. **代码注释**：在配置类中添加详细注释说明用途差异

3. **备选方案**（如混淆严重）：
   - 将 `default_coding_executor` 重命名为 `user_preferred_executor`
   - 或在配置文件中简化为 `default_executor`（需要确认是否有歧义）

#### R2 - 向后兼容

**问题**：`--executor` 默认值从 `"claude_code"` 改为 `None`，可能影响依赖默认值的脚本。

**解决方案**：
1. **行为保持**：
   - 即使默认值为 `None`，解析后的 `effective_executor` 仍为 `"claude_code"`
   - 仅改变检测是否显式指定的能力，不改变最终行为

2. **测试覆盖**：
   - 现有测试 `test_run_uses_template_default_params` 验证默认值行为
   - 新增测试验证无配置时的降级行为

3. **降级方案**（如出现问题）：
   - 保留 `--executor` 默认值为 `"claude_code"`
   - 添加 `--use-config-executor` 标志位显式启用配置读取

#### R3 - JSON 格式支持

**问题**：需求要求支持 JSON 格式，但现有配置系统主要使用 YAML。

**解决方案**：
1. **最小实现**：
   - JSON 解析在 `ConfigLoader._load_yaml()` 中通过 `yaml.safe_load()` 隐式支持
   - YAML 是 JSON 的超集，无需额外代码

2. **显式支持**（如需要）：
   - 添加 `_load_json()` 方法处理 `.json` 文件
   - 使用标准库 `json` 模块解析

3. **测试覆盖**：
   - 添加 `test_load_from_json()` 测试用例

#### R4 - 验证逻辑复杂度

**问题**：配置验证涉及类型检查、有效性检查、降级处理，可能导致代码复杂。

**解决方案**：
1. **分层验证**：
   - 第一层：类型校验（字段级）
   - 第二层：有效性校验（业务级）
   - 第三层：应用时校验（运行时）

2. **备选方案**（如需要更严格验证）：
   - 引入 `pydantic` 进行声明式验证
   - 使用 JSON Schema 定义配置格式

---

## 7. 测试策略

### 7.1 单元测试

| 测试用例 | 描述 | 期望结果 |
|----------|------|----------|
| `test_default_coding_executor_from_config` | 从配置文件加载 default_coding_executor | 配置正确解析 |
| `test_invalid_executor_warning` | 配置无效执行器时发出警告 | 记录警告日志，使用默认值 |
| `test_resolve_executor_priority_cli` | CLI 参数优先级高于配置 | 使用 CLI 指定的执行器 |
| `test_resolve_executor_priority_config` | 配置值在无 CLI 参数时生效 | 使用配置指定的执行器 |
| `test_resolve_executor_fallback` | 无配置时使用系统默认值 | 使用 claude_code |
| `test_config_validation_type_error` | 配置值类型错误时降级 | 忽略无效配置，使用默认值 |

### 7.2 集成测试

| 测试用例 | 描述 | 期望结果 |
|----------|------|----------|
| `test_run_with_configured_executor` | 使用配置文件中的执行器运行工作流 | 正确调用指定执行器 |
| `test_run_cli_override_config` | CLI 参数覆盖配置文件 | 使用 CLI 指定的执行器 |
| `test_run_invalid_config_graceful` | 无效配置时优雅降级 | 完成执行并提示配置问题 |

---

## 8. 实现计划

### 8.1 变更文件清单

| 文件 | 变更类型 | 描述 |
|------|----------|------|
| `lee/orchestrator/config_loader.py` | 修改 | 添加 `default_coding_executor` 字段和验证逻辑 |
| `lee/cli/commands/run.py` | 修改 | 修改 `--executor` 默认值，添加配置解析逻辑 |
| `tests/test_config_loader.py` | 新增测试 | 添加配置加载和验证测试 |
| `tests/test_run_command_defaults.py` | 修改 | 更新现有测试，添加新场景测试 |

### 8.2 配置迁移指南

**用户配置示例**（`.lee/config.yaml`）：

```yaml
# 基础配置
executor:
  default_coding_executor: kimi    # 设置默认编码执行器为 Kimi
```

**有效值列表**：
- `claude_code` (默认)
- `kimi`
- `qwen`
- `llm`
- `shell`
- `codex`
- `langgraph`

---

## 9. Frozen 架构审批

### 9.1 审批检查清单

- [ ] 技术方案满足所有 Acceptance Criteria
- [ ] 向后兼容性得到保证
- [ ] 风险识别完整且有缓解方案
- [ ] 核心依赖项明确
- [ ] 接口定义清晰

### 9.2 审批人

- 架构审批：_________________
- 日期：_________________

### 9.3 批准后状态

本架构文档批准后，状态将变更为 **Frozen**，作为开发阶段的输入。

---

## 附录 A：与需求追踪矩阵

| 需求 ID | 需求描述 | 架构实现 |
|---------|----------|----------|
| AC-012-002-01 | 配置项读取与生效 | `ExecutorConfig.default_coding_executor` + `from_dict()` |
| AC-012-002-02 | 配置与 CLI 参数优先级 | `resolve_coding_executor()` 优先级逻辑 |
| AC-012-002-03 | 配置变更后生效 | CLI 启动时加载配置（每次执行重新加载） |
| AC-012-002-04 | 无效配置降级策略 | `ExecutorConfig._validate()` 验证 + 降级逻辑 |
| AC-012-002-05 | 配置缺失处理 | `FALLBACK_EXECUTOR` 默认值 |

## 附录 B：变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-12 | 初始架构设计 | Architecture Agent |
