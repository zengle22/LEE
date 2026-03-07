# LEE Project Configuration

This directory contains the LEE orchestrator configuration for this project.

## Files

- `dirs.yaml`: Directory structure configuration (DO NOT edit manually)
- `schema/`: Schema definitions for validation
- `governance/`: Temporary governance shell for tasks not yet promoted into formal SSOT
  - `governance/SPEC_GOVERNANCE_L3_USAGE.md`: How to run the governed spec-maintenance workflow with writeback, review gate, and revise loop

## Directory Structure

`dirs.yaml` is the SSOT for directory topology and placement only.
Artifact identity, filename, and reference rules are owned by the SSOT identity layer.

LEE 项目采用**分层目录结构**，将工具元数据与业务内容分离：

### 根目录级（工具配置）

| 目录 | 说明 |
|------|------|
| `.project/` | 项目元数据和配置 |
| `.workflow/` | 工作流运行时状态（执行状态、实例、缓存等） |

**特点**：这些目录属于 LEE 工具的元数据，不属于业务输出内容。

### 内容目录级（业务输出）

| 目录 | 说明 |
|------|------|
| `contracts/` | 冻结的分析结果和正式契约 |
| `docs/` | 生成的文档和报告 |
| `knowledge/` | Agent 复盘、模式沉淀、能力演进 |
| `src/` | 生成的源代码 |
| `outputs/` | 中间产物和制品 |
| `tests/` | 生成的测试文件 |
| `specs/` | 生成的规格文档 |

**特点**：这些目录属于业务输出内容，可能需要版本化管理。

### 目录位置规则

目录的实际位置取决于是否设置了 `project_name`：

```
project_name = "LEE" 时：
  .project/           → {project_root}/.project/
  .workflow/          → {project_root}/.workflow/
  contracts/          → {project_root}/LEE/contracts/
  docs/               → {project_root}/LEE/docs/
  ...

project_name = None 时：
  所有目录直接在 {project_root}/ 下
```

## 设计思路

### 为什么分离两类目录？

1. **关注点分离**
   - `.project/` 和 `.workflow/` 是工具配置/运行时状态
   - `contracts/`, `docs/`, `src/` 等是业务输出内容

2. **多项目管理支持**
   - 多个项目可以共享同一套工具配置
   - 通过 `project_name` 隔离不同项目的内容

3. **版本化管理便利**
   - 业务输出可以独立版本化
   - 工具配置与内容分离，便于迁移和共享

### 使用场景

**单项目场景**（project_name = None）：
```
/my-project/
  .project/
  .workflow/
  contracts/
  docs/
  src/
```

**多项目场景**（project_name = "app1"）：
```
/workspace/
  .project/           # 共享配置
  .workflow/          # 共享运行时
  app1/               # 项目A内容
    contracts/
    docs/
  app2/               # 项目B内容
    contracts/
    docs/
```

## Constraints

- ✅ Strict path validation enabled
- ✅ File creation outside defined directories is forbidden
- ✅ Project initialization is required

## Getting Output Paths

When creating outputs in your workflow, use the configured directory structure:

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(".")
path = config.get_output_path("doc", category="reports", title="My Report")
# Returns: docs/reports/2025-01-25-my-report.md
```

For governed SSOT artifacts:
- `dirs.yaml` decides the directory family
- the SSOT identity layer decides the object ID and filename

## Re-initializing

To re-initialize the project structure (e.g., after updating the schema):

```bash
python -m flowcore.orchestrator init . --force
```
