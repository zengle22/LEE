---
title: flowcore 兼容性包技术债务
date: 2026-03-04
version: 1.0.0
review_date: 2026-06-04
authors:
  - LEE Team
project: LEE Framework
---

# flowcore 兼容性包技术债务

**决策日期**: 2026-03-04  
**决策状态**: 已接受 (Accepted)  
**计划移除版本**: v0.3.0  

---

## 决策摘要

### 背景

在 LEE 框架架构整改过程中，发现 `src/flowcore/` 包名存实亡：
- 实际代码全部位于 `src/lee/` 目录
- `flowcore` 仅作为兼容性重定向包存在
- README 和所有文档示例仍使用 `flowcore` 导入

### 决策

**保留 `flowcore` 作为兼容性重定向包**，暂不删除。

### 理由

1. **大量外部依赖**
   - 10+ 个示例文件使用 `from flowcore.api import ...`
   - 30+ 处文档引用 `flowcore` 导入示例
   - 大量历史文档和指南依赖 `flowcore`

2. **维护成本极低**
   - 纯重定向，无实际业务逻辑
   - 代码量 < 100 行
   - 已添加 `DeprecationWarning` 提示迁移

3. **向后兼容性**
   - 避免破坏现有用户代码
   - 给用户充分的迁移时间

---

## 技术债务详情

### 债务 ID

`TECH-DEBT-2026-0304-001`

### 类别

兼容性技术债务 (Compatibility Technical Debt)

### 严重程度

🟡 Medium

### 影响范围

| 范围 | 状态 | 备注 |
|------|------|------|
| 生产代码 | ✅ 无影响 | `src/lee/` 完全独立 |
| CLI 入口 | ✅ 无影响 | 直接指向 `lee.cli.main:main` |
| 示例代码 | ⚠️ 依赖 | 10+ 文件使用 flowcore |
| 文档 | ⚠️ 依赖 | 30+ 处引用 |
| 测试 | ⚠️ 依赖 | `tests/test_flowcore_compat.py` |

### 当前实现

```
src/flowcore/
├── __init__.py        # 版本号 + DeprecationWarning
├── orchestrator.py    # 重定向到 lee.orchestrator.execution
├── engines.py         # 重定向到 lee.orchestrator.execution
└── utils.py           # 重定向到 lee.orchestrator.utils
```

### 重定向示例

```python
# src/flowcore/orchestrator.py
import warnings
warnings.warn(
    "flowcore.orchestrator 已弃用，请使用 from lee.orchestrator.execution import ...",
    DeprecationWarning,
    stacklevel=2,
)
from lee.orchestrator.execution import *
```

---

## 迁移路径

### 用户迁移指南

**旧导入方式** (仍然可用，但显示警告):
```python
from flowcore.orchestrator import Orchestrator
from flowcore.engines import ExecutorFactory
```

**新导入方式** (推荐):
```python
from lee.orchestrator.execution import Orchestrator, ExecutorFactory
```

### 移除计划

| 版本 | 行动 | 时间 |
|------|------|------|
| v0.1.x | 保留兼容，显示 DeprecationWarning | 当前 |
| v0.2.x | 继续保留，更新所有文档和示例 | 2026-Q2 |
| **v0.3.0** | **完全移除 flowcore 包** | **2026-Q3** |

---

## 需要更新的文件清单

### 示例代码 (examples/)

- [ ] `examples/human-gate-demo/test_human_gate.py`
- [ ] `examples/pm-agent-stg-workflow/quick_start.py`
- [ ] `examples/pm-agent-stg-workflow/run_stg_with_pm_agent.py`
- [ ] `examples/v2-demo/pm_agent_demo.py`
- [ ] `examples/v2-demo/run_demo.py`
- [ ] `examples/v2-demo/run_demo_simple.py`
- [ ] `examples/unified-engine-demo/test_mock.py`
- [ ] `examples/unified-engine-demo/test_local.py`
- [ ] `examples/unified-engine-demo/run_demo.py`
- [ ] `examples/pm-gate-integration-demo/test_pm_gate_integration.py`

### 文档 (docs/)

- [ ] `docs/guides/user/QUICKSTART.md`
- [ ] `docs/guides/user/GETTING_STARTED.md`
- [ ] `docs/guides/user/STG-WORKFLOW-REVIEW-GUIDE.md`
- [ ] `docs/guides/user/SLASH-COMMANDS-GUIDE.md`
- [ ] `docs/features/pm-agent/PM-AGENT-USER-GUIDE.md`
- [ ] `docs/features/human-gates/*.md` (多个文件)
- [ ] `docs/guides/installation/*.md` (多个文件)

### 测试

- [ ] `tests/test_flowcore_compat.py` (移除或更新)

### 工具脚本

- [ ] `tools/verify_env.py`
- [ ] `examples/simple_demo/verify_env.py`

---

## 相关文档

- [REFACTORING_COMPLETE.md](../REFACTORING_COMPLETE.md) - 架构整改完成报告
- [README.md](../README.md) - 已更新导入示例
- [WORKFLOW_MIGRATION_PLAN.md](../WORKFLOW_MIGRATION_PLAN.md) - 工作流格式迁移计划

---

## 决策记录

**决策**: 保留 flowcore 兼容性包  
**决策日期**: 2026-03-04  
**决策者**: AI Assistant + 项目负责人  
**计划移除**: v0.3.0  

**替代方案考虑**:
- ❌ 立即删除：会破坏大量示例和文档，用户体验差
- ✅ 保留兼容：给用户迁移时间，维护成本低
- ⏸️ 长期保留：不推荐，增加技术债务

---

## 检查清单

- [x] 创建兼容性重定向包
- [x] 添加 DeprecationWarning
- [x] 更新 README 导入示例
- [x] 创建技术债务文档
- [ ] 更新所有示例代码 (v0.2.x)
- [ ] 更新所有文档 (v0.2.x)
- [ ] 移除 flowcore 包 (v0.3.0)
