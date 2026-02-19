---
title: RFC-001: Repository Registry - 仓库注册表
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# RFC-001: Repository Registry - 仓库注册表

## 问题背景

### 当前问题

1. **路径硬编码**: `development-plan.yaml` 和 `workflow.yaml` 中的输出路径是硬编码的
2. **规划与实际不一致**: 规划时假设 `frontend/`，实际代码在 `git/ai-marathon-coach-front/`
3. **跨项目不可复用**: 每个项目的仓库结构不同，无法复用 workflow 模板

### 根因分析

```
development-plan.yaml          实际项目结构
─────────────────────          ─────────────────
outputs:                       git/
  - path: "frontend/"            ├── ai-marathon-coach-front/  ← 实际前端
  - path: "backend/"             └── ai-marathon-coach-server/ ← 实际后端

                               project/AI跑步教练/
                                 ├── dev-plan/
                                 ├── dev/
                                 └── (没有 frontend/ 目录)
```

## 解决方案

### 核心概念: 仓库注册表 (Repository Registry)

在项目根目录引入 `project.yaml`，定义仓库映射关系：

```yaml
# project/AI跑步教练/project.yaml
kind: project
version: "1.0"

id: ai-running-coach
name: AI 跑步教练

# 仓库注册表
repositories:
  frontend:
    type: git
    path: "../../git/ai-marathon-coach-front"
    description: "UniApp 前端项目"
  backend:
    type: git
    path: "../../git/ai-marathon-coach-server"
    description: "Go 后端服务"

# 路径别名 (可选，简化引用)
path_aliases:
  "@frontend": "${repositories.frontend.path}"
  "@backend": "${repositories.backend.path}"
  "@openspec": "./dev/${current_phase}/openspec"
```

### 在 workflow 中使用

```yaml
# dev/phase7/workflow.yaml
outputs:
  # 方式1: 使用别名
  - path: "@frontend/src/styles/tokens.css"

  # 方式2: 使用变量
  - path: "${repositories.frontend}/src/components/"

  # 方式3: 相对于 openspec (本地文档)
  - path: "@openspec/04-implementation/summary.md"
```

### Orchestrator 路径解析流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Path Resolution                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 加载 project.yaml                                            │
│     ┌─────────────────┐                                          │
│     │ repositories:   │                                          │
│     │   frontend: ... │                                          │
│     │   backend: ...  │                                          │
│     └─────────────────┘                                          │
│              │                                                   │
│              ▼                                                   │
│  2. 解析 workflow.yaml 中的路径                                   │
│     ┌─────────────────────────────────────────┐                  │
│     │ path: "@frontend/src/components/"       │                  │
│     │       ↓                                 │                  │
│     │ resolved: "../../git/ai-marathon-coach- │                  │
│     │           front/src/components/"        │                  │
│     └─────────────────────────────────────────┘                  │
│              │                                                   │
│              ▼                                                   │
│  3. 验证时使用解析后的绝对路径                                     │
│     ┌─────────────────────────────────────────┐                  │
│     │ validate: E:/ai/ai-constitution/git/    │                  │
│     │           ai-marathon-coach-front/      │                  │
│     │           src/components/               │                  │
│     └─────────────────────────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 实现设计

### 1. 新增 ProjectConfig 类

```python
# orchestrator/core/project_config.py

@dataclass
class Repository:
    id: str
    type: str  # git | local | remote
    path: str
    description: str = ""
    branch: str = "main"

@dataclass
class ProjectConfig:
    id: str
    name: str
    repositories: Dict[str, Repository]
    path_aliases: Dict[str, str]
    base_path: Path

    @classmethod
    def load(cls, project_dir: str) -> "ProjectConfig":
        """从 project.yaml 加载配置"""
        project_yaml = Path(project_dir) / "project.yaml"
        if not project_yaml.exists():
            # 向上查找
            project_yaml = cls._find_project_yaml(project_dir)
        ...

    def resolve_path(self, path: str) -> str:
        """解析路径别名和变量"""
        # 处理 @alias
        for alias, target in self.path_aliases.items():
            if path.startswith(alias):
                path = path.replace(alias, target, 1)

        # 处理 ${repositories.xxx}
        path = self._resolve_variables(path)

        # 转为绝对路径
        return str((self.base_path / path).resolve())
```

### 2. 扩展 WorkflowParser

```python
# orchestrator/core/workflow_parser.py

class WorkflowParser:
    def __init__(self, workflow_path: str, project_config: ProjectConfig = None):
        ...
        self.project_config = project_config

    def _resolve_output_path(self, path: str) -> str:
        """解析输出路径"""
        if self.project_config:
            return self.project_config.resolve_path(path)
        return path
```

### 3. CLI 集成

```bash
# 初始化项目 (创建 project.yaml)
python -m orchestrator project init ./my-project

# 注册仓库
python -m orchestrator project add-repo frontend ../../git/my-frontend

# 验证路径解析
python -m orchestrator project resolve "@frontend/src/components"

# 状态检查时显示仓库信息
python -m orchestrator status ./project/AI跑步教练/dev/phase7
# Output:
# Repositories:
#   frontend: ../../git/ai-marathon-coach-front (exists ✓)
#   backend: ../../git/ai-marathon-coach-server (exists ✓)
```

## 迁移策略

### Phase 1: 兼容模式

- 如果没有 `project.yaml`，保持现有行为
- 路径不以 `@` 或 `${` 开头时，按原样处理

### Phase 2: 标准化现有项目

```bash
# 为 AI跑步教练 项目创建配置
python -m orchestrator project init ./project/AI跑步教练 \
  --add-repo frontend=../../git/ai-marathon-coach-front \
  --add-repo backend=../../git/ai-marathon-coach-server
```

### Phase 3: 更新规范模板

- 更新 `development-plan.yaml` 模板使用别名
- 更新 `workflow.yaml` 模板使用别名
- 文档更新

## 验证规则

### orchestrator validate 增强

```yaml
# 验证时检查
validation:
  repository_check:
    - id: frontend
      must_exist: true
      check_branch: main
    - id: backend
      must_exist: true
```

### 错误提示改进

```
❌ Validation failed for p07_04_implementation:
   - Repository 'frontend' not found at: ../../git/ai-marathon-coach-front

   Hint: Run 'orchestrator project add-repo frontend <path>' to configure
```

## 标准化收益

| 场景 | 之前 | 之后 |
|------|------|------|
| 新项目初始化 | 手动修改所有路径 | `orchestrator project init` |
| 仓库位置变更 | 修改所有 yaml 文件 | 只改 `project.yaml` |
| 跨项目复用 workflow | 不可能 | 使用别名，直接复用 |
| 路径验证失败 | "Output not found" | 显示仓库状态和修复建议 |

## 下一步

1. 实现 `ProjectConfig` 类
2. 扩展 `WorkflowParser` 支持路径解析
3. 添加 `project` 子命令到 CLI
4. 迁移 AI跑步教练 项目
5. 更新文档和模板
