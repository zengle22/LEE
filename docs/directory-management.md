# LEE 项目文件产物目录管理机制

## 1. 目录分类

### 1.1 工具目录（LEE 元数据）

| 目录 | 说明 | 策略 |
|------|------|------|
| `.project/` | 项目配置和元数据 | 冻结 |
| `.workflow/` | 工作流运行时状态 | 允许写入 |
| `.artifacts/` | 产出物管理 | 允许写入 |

### 1.2 内容目录（业务输出）

| 目录 | 说明 | 策略 |
|------|------|------|
| `contracts/` | 冻结的分析结果和正式契约 | 冻结 |
| `docs/` | 生成的文档和报告 | 冻结 |
| `src/` | 生成的源代码 | 冻结 |
| `outputs/` | 中间产物和制品 | 允许写入 |
| `tests/` | 生成的测试文件 | 冻结 |
| `specs/` | 生成的规格文档 | 冻结 |

---

## 2. 核心机制

### 2.1 路径策略定义 (SSOT)

所有目录策略定义在 `src/lee/orchestrator/core/path_policy.py`：

```python
# 工具目录
TOOL_DIRECTORIES = {".artifacts", ".workflow", ".project"}

# 允许写入前缀
ALLOWED_WRITE_PREFIXES = {".artifacts/", ".workflow/", "outputs/"}

# 冻结目录前缀
FROZEN_PREFIXES = {"contracts/", "src/", "specs/"}
```

### 2.2 子目录定义

```python
WORKFLOW_SUBDIRS = {
    "traces": ".workflow/traces",
    "evidence": ".workflow/evidence",
    "tokens": ".workflow/tokens",
    "compliance": ".workflow/compliance",
    "env_check": ".workflow/env-check",
    "workspace_cleanup": ".workflow/workspace-cleanup",
    "events": ".workflow/events.jsonl",
    "db": ".workflow/orchestrator.db",
    "instances": ".workflow/instances",
    "approvals": ".workflow/approvals",
}

ARTIFACTS_SUBDIRS = {
    "active": ".artifacts/active",
}
```

### 2.3 路径配置服务

使用 `PathConfig` 获取路径：

```python
from src.lee.orchestrator.core.path_config import PathConfig

config = PathConfig(".")
artifacts_dir = config.artifacts_dir    # -> Path(".artifacts")
workflow_dir = config.workflow_dir      # -> Path(".workflow")
outputs_dir = config.outputs_dir        # -> Path("outputs")

# 检查写入权限
config.is_allowed_write("outputs/file.txt")  # -> True
config.is_allowed_write("src/file.py")       # -> False
```

### 2.4 运行时守卫 (PathGuard)

在 dev/CI 模式下启用运行时拦截：

```python
from src.lee.orchestrator.core.io_guard import init_path_guard

# 在 CLI worker 入口调用
init_path_guard(project_root=".")
```

---

## 3. 目录结构详情

### 3.1 由 `lee init` 创建

运行 `lee init` 命令时自动创建以下目录：

```
# 工具目录（LEE 元数据）
.project/          # 项目配置和元数据
.workflow/         # 工作流运行时状态
.artifacts/        # 产出物管理

# 内容目录（业务输出）
contracts/         # 冻结的分析结果
contracts/input/   # 契约输入
contracts/output/  # 契约输出

docs/             # 生成的文档
docs/spec/         # 规格文档
docs/reports/      # 报告文档
docs/guides/       # 指南文档
docs/archive/      # 归档文档

src/               # 源代码
src/components/    # 组件代码
src/services/      # 服务代码
src/utils/         # 工具代码
src/types/         # 类型定义

outputs/           # 中间产物
outputs/build/     # 构建产物
outputs/test/      # 测试输出
outputs/analysis/  # 分析结果
outputs/temp/      # 临时文件

tests/             # 测试文件
tests/unit/        # 单元测试
tests/integration/ # 集成测试
tests/e2e/         # 端到端测试

specs/             # 规格文档
specs/requirements/ # 需求规格
specs/api/         # API 规格
specs/database/    # 数据库规格
specs/ui/          # UI 规格

# 兼容旧版
spec/dev/          # 开发规格
spec/qa/           # 测试规格
spec/devops/       # 运维规格
evidence/          # 证据数据
env/               # 环境配置
```

### 3.2 .artifacts/

```
.artifacts/
└── active/
    ├── {department}/
    │   └── {run_id}/
    │       ├── manifest.yaml
    │       └── ...
    └── {run_id}/
        ├── manifest.yaml
        └── ...
```

### 3.2 .workflow/

```
.workflow/
├── traces/           # 执行追踪
├── evidence/         # 证据数据
├── tokens/           # 令牌文件
├── compliance/       # 合规检查结果
├── env-check/        # 环境检查结果
├── workspace-cleanup/ # 工作空间清理
├── events.jsonl      # 事件日志
├── orchestrator.db   # 状态数据库
├── instances/        # 工作流实例
│   └── l3/
└── approvals/        # 审批记录
```

### 3.3 outputs/

```
outputs/
├── build/           # 构建产物
├── test/            # 测试输出
├── analysis/        # 分析结果
└── temp/            # 临时文件
```

---

## 4. CI 门禁

### 4.1 本地 pre-push hook

安装后每次 `git push` 自动检测硬编码：

```bash
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 4.2 检测脚本

```bash
python scripts/detect-hardcoded-paths.py src
```

---

## 5. 约束规则

| 规则 | 说明 |
|------|------|
| 禁止写入项目外部 | 相对路径必须解析到 project_root 下 |
| 允许目录 | `.artifacts/`, `.workflow/`, `outputs/` |
| 冻结目录 | `contracts/`, `src/`, `specs/` |
| 项目根目录 | 禁止写入 |

---

## 6. 快速参考

### 获取路径

```python
from src.lee.orchestrator.core.path_config import PathConfig

config = PathConfig(project_root=".")

# 常用目录
config.artifacts_dir      # .artifacts/
config.workflow_dir       # .workflow/
config.outputs_dir        # outputs/

# 子目录
config.get_artifacts_subpath("active", "run123")
config.get_workflow_subpath("traces")
```

### 路径检查

```python
config.is_allowed_write("outputs/file.txt")  # True
config.is_allowed_write("src/file.py")        # False

config.is_frozen("src/file.py")               # True
config.is_frozen("outputs/file.txt")          # False
```

### 启用运行时守卫

```python
import os
os.environ["LEE_DEV_MODE"] = "1"

from src.lee.orchestrator.core.io_guard import init_path_guard
init_path_guard(project_root=".")
```

---

## 7. 相关文件

| 文件 | 说明 |
|------|------|
| `src/lee/orchestrator/core/path_policy.py` | 策略定义 (SSOT) |
| `src/lee/orchestrator/core/path_config.py` | 路径配置服务 |
| `src/lee/orchestrator/core/io_guard.py` | 运行时守卫 |
| `.project/dirs.yaml` | 项目目录配置 |
| `scripts/detect-hardcoded-paths.py` | CI 检测脚本 |
| `.githooks/pre-push` | 本地 CI hook |
