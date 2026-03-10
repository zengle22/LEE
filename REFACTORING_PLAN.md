# LEE 框架整改详细方案

**版本**: v1.0  
**日期**: 2026-03-04  
**范围**: 问题1 (flowcore包)、问题2 (TemplateManager重复)

---

## 第一部分：问题1 - flowcore 包整改

### 1.1 现状分析

```
src/flowcore/
├── __init__.py        # 仅包含兼容性注释和版本号
└── cli/
    ├── __init__.py    # 空文件
    └── main.py        # 仅6行代码，转发到 lee.cli.main

src/lee/
├── cli/
│   ├── main.py        # 完整的 CLI 实现 (227行)
│   └── commands/      # 所有命令实现
├── orchestrator/      # 200+ 文件，核心编排逻辑
└── ...
```

**核心问题**:
- `pyproject.toml` 入口点: `lee = "lee.cli.main:main"` (正确)
- README 文档声称存在 `flowcore.orchestrator.*` 等模块 (不存在)
- `flowcore` 实际只是一个空壳兼容性包

### 1.2 整改目标

将 `flowcore` 改造为**兼容性重定向包**，确保：
1. 旧代码 `from flowcore.xxx import yyy` 仍然可用
2. 实际调用转发到 `lee.xxx`
3. 添加 DeprecationWarning 提示迁移

### 1.3 具体实施步骤

#### 步骤 1: 重构 `src/flowcore/__init__.py`

```python
"""
flowcore - 兼容性重定向包

⚠️ 警告: flowcore 包已被弃用，将在 v0.3.0 中移除
请迁移到 lee 包:
  - from flowcore.orchestrator.runner import run_workflow
  + from lee.orchestrator.execution import run_workflow

本包提供向后兼容的重定向，会触发 DeprecationWarning
"""

import warnings
from importlib.metadata import PackageNotFoundError, version

# 版本号保持同步
try:
    __version__ = version("lee-framework")
except PackageNotFoundError:
    __version__ = "0.1.0"

# 弃用警告
warnings.warn(
    "flowcore 包已被弃用，将在 v0.3.0 中移除。"
    "请使用 lee 包替代。",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["__version__"]
```

#### 步骤 2: 删除 `src/flowcore/cli/` 目录

```bash
# 删除转发用的 cli 目录
rm -rf src/flowcore/cli/
```

**理由**:
- `pyproject.toml` 入口点直接指向 `lee.cli.main:main`
- `flowcore.cli` 没有被任何地方使用
- 删除可减少混淆

#### 步骤 3: 创建兼容性重定向模块

创建 `src/flowcore/orchestrator.py`:
```python
"""兼容性重定向: flowcore.orchestrator -> lee.orchestrator.execution"""
import warnings

warnings.warn(
    "flowcore.orchestrator 已被弃用，请使用 lee.orchestrator.execution",
    DeprecationWarning,
    stacklevel=2,
)

# 重定向所有导出
from lee.orchestrator.execution import (
    Orchestrator,
    WorkflowStateMachine,
    TemplateManager,
    run_workflow,
    WorkflowRunner,
    # ... 其他常用接口
)

__all__ = [
    "Orchestrator",
    "WorkflowStateMachine", 
    "TemplateManager",
    "run_workflow",
    "WorkflowRunner",
]
```

创建 `src/flowcore/engines.py`:
```python
"""兼容性重定向: flowcore.engines -> lee.orchestrator.execution"""
import warnings

warnings.warn(
    "flowcore.engines 已被弃用，请使用 lee.orchestrator.execution",
    DeprecationWarning,
    stacklevel=2,
)

from lee.orchestrator.execution import (
    ExecutorFactory,
    BaseExecutor,
    LangGraphExecutor,
    ClaudeCodeExecutor,
)

__all__ = [
    "ExecutorFactory",
    "BaseExecutor",
    "LangGraphExecutor",
    "ClaudeCodeExecutor",
]
```

创建 `src/flowcore/utils.py`:
```python
"""兼容性重定向: flowcore.utils -> lee.orchestrator.utils"""
import warnings

warnings.warn(
    "flowcore.utils 已被弃用，请使用 lee.orchestrator.utils",
    DeprecationWarning,
    stacklevel=2,
)

from lee.orchestrator.utils import (
    sanitization,
)

__all__ = ["sanitization"]
```

### 1.4 最终 flowcore 结构

```
src/flowcore/
├── __init__.py        # 版本号 + 弃用警告
├── orchestrator.py    # 重定向到 lee.orchestrator.execution
├── engines.py         # 重定向到 lee.orchestrator.execution
└── utils.py           # 重定向到 lee.orchestrator.utils
```

### 1.5 验证命令

```bash
# 验证旧导入仍然可用（但会触发警告）
python -c "from flowcore.orchestrator import Orchestrator"  # 应显示 DeprecationWarning

# 验证新导入方式
python -c "from lee.orchestrator.execution import Orchestrator; print('OK')"

# 验证 CLI 入口
lee --version
```

---

## 第二部分：问题2 - TemplateManager 合并

### 2.1 现状分析

**两个 TemplateManager 对比**:

| 特性 | core/template_manager.py | execution/template_manager.py |
|------|-------------------------|------------------------------|
| 行数 | 115 | 1000+ |
| WorkflowTemplate | 使用 SimpleNamespace | 使用正式 dataclass |
| 缓存机制 | Dict[str, Dict] | Dict[str, WorkflowTemplate] |
| spec-global 支持 | ❌ | ✅ |
| L2/L3 模板解析 | ❌ | ✅ |
| 拓扑排序 | ❌ | ✅ |
| 依赖验证 | ❌ | ✅ |
| 是否被使用 | ❌ 无任何导入 | ✅ 7个文件导入 |

**结论**: `core/template_manager.py` 是完全废弃的代码

### 2.2 整改步骤

#### 步骤 1: 删除废弃文件

```bash
# 删除废弃的 template_manager.py
rm src/lee/orchestrator/core/template_manager.py
```

#### 步骤 2: 验证无残留引用

```bash
# 全局搜索确保没有遗漏引用
grep -r "from.*core.*template_manager" src/
grep -r "lee\.orchestrator\.core\.template_manager" src/
```

预期结果: 无匹配

#### 步骤 3: 清理 core/__init__.py

检查并移除可能的相关导出:

```python
# src/lee/orchestrator/core/__init__.py
# 确认没有导入 TemplateManager，无需修改
```

### 2.3 验证合并结果

```bash
# 验证所有 TemplateManager 导入都指向 execution
grep -r "from.*template_manager import" src/ | grep -v execution
# 预期: 无输出

# 验证运行正常
python -c "
from lee.orchestrator.execution import TemplateManager
from lee.orchestrator.execution.template_manager import WorkflowTemplate
print('TemplateManager:', TemplateManager)
print('WorkflowTemplate:', WorkflowTemplate)
print('OK')
"
```

---

## 第三部分：执行检查清单

### 3.1 文件操作清单

| 操作 | 文件/目录 | 状态 |
|------|----------|------|
| 修改 | `src/flowcore/__init__.py` | ⬜ |
| 删除 | `src/flowcore/cli/` 目录 | ⬜ |
| 创建 | `src/flowcore/orchestrator.py` | ⬜ |
| 创建 | `src/flowcore/engines.py` | ⬜ |
| 创建 | `src/flowcore/utils.py` | ⬜ |
| 删除 | `src/lee/orchestrator/core/template_manager.py` | ⬜ |
| 删除 | `src/config/` 目录 (空目录) | ⬜ |

### 3.2 代码验证清单

- [ ] `python -c "from flowcore import __version__"` 显示警告
- [ ] `python -c "from flowcore.orchestrator import TemplateManager"` 显示警告且可用
- [ ] `python -c "from lee.orchestrator.execution import TemplateManager"` 正常工作
- [ ] `lee --version` 正常输出
- [ ] `pytest tests/` 无导入错误

---

## 第四部分：文档更新

### 4.1 README.md 更新

**当前错误描述** (需要删除):
```python
from flowcore.orchestrator.runner import run_workflow  # 不存在
from flowcore.engines.legacy_executor.adapter import run_lee_unit  # 不存在
```

**正确描述**:
```python
# 核心模块
from lee.orchestrator.execution import (
    Orchestrator,
    TemplateManager,
    run_workflow,
    WorkflowRunner,
)

# 执行引擎
from lee.orchestrator.execution import (
    ExecutorFactory,
    LangGraphExecutor,
    ClaudeCodeExecutor,
)
```

### 4.2 添加迁移指南

创建 `docs/MIGRATION-v0.1-to-v0.2.md`:

```markdown
# v0.1 到 v0.2 迁移指南

## flowcore 包弃用

flowcore 包已被弃用，将在 v0.3.0 中移除。

### 迁移前
```python
from flowcore.orchestrator.runner import run_workflow
from flowcore.engines.base import LEERequest, LEEResult
```

### 迁移后
```python
from lee.orchestrator.execution import run_workflow
# LEERequest, LEEResult 已合并到统一接口
```
```

---

## 附录：详细命令脚本

### 一键执行脚本

```bash
#!/bin/bash
# refactor-phase1.sh

echo "=== Phase 1: Cleanup flowcore and TemplateManager ==="

# 1. 删除废弃文件
echo "Removing deprecated files..."
rm -f src/lee/orchestrator/core/template_manager.py
rm -rf src/flowcore/cli/
rm -rf src/config/  # empty directory

# 2. 更新 flowcore/__init__.py
echo "Updating flowcore/__init__.py..."
cat > src/flowcore/__init__.py << 'EOF'
"""flowcore - 兼容性重定向包 (已弃用)"""
import warnings
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lee-framework")
except PackageNotFoundError:
    __version__ = "0.1.0"

warnings.warn(
    "flowcore 包已被弃用，将在 v0.3.0 中移除。请使用 lee 包替代。",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["__version__"]
EOF

# 3. 创建兼容性重定向模块
echo "Creating compatibility shims..."

# orchestrator.py shim
cat > src/flowcore/orchestrator.py << 'EOF'
"""兼容性重定向: flowcore.orchestrator -> lee.orchestrator.execution"""
import warnings
warnings.warn("flowcore.orchestrator 已弃用，请使用 lee.orchestrator.execution", DeprecationWarning, stacklevel=2)
from lee.orchestrator.execution import *
EOF

# engines.py shim  
cat > src/flowcore/engines.py << 'EOF'
"""兼容性重定向: flowcore.engines -> lee.orchestrator.execution"""
import warnings
warnings.warn("flowcore.engines 已弃用，请使用 lee.orchestrator.execution", DeprecationWarning, stacklevel=2)
from lee.orchestrator.execution import ExecutorFactory, BaseExecutor, LangGraphExecutor, ClaudeCodeExecutor
EOF

# utils.py shim
cat > src/flowcore/utils.py << 'EOF'
"""兼容性重定向: flowcore.utils -> lee.orchestrator.utils"""
import warnings
warnings.warn("flowcore.utils 已弃用，请使用 lee.orchestrator.utils", DeprecationWarning, stacklevel=2)
from lee.orchestrator.utils import *
EOF

echo "=== Phase 1 Complete ==="
echo "Run tests: pytest tests/ -xvs"
```

---

**下一步**: 执行上述脚本后，进入 "第三部分：Workflow 格式迁移计划"
