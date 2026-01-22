# LEE 框架快速开始

> 快速开始使用 LEE 框架 v2

## 核心变化

### v2 主要更新

1. **核心代码包重命名**：`lee` → **`flowcore`**
2. **Spec 按部门组织**：采用 **core/departments/cross** 三层结构
3. **完善文档体系**：模块级文档 + 框架级文档 + 变更日志
4. **CLI 路径更新**：`python -m flowcore.cli.main`

## 生成的文件

### 核心文档

| 文件 | 说明 |
|------|------|
| `README.md` | LEE 框架总览 |
| `MIGRATION_PLAN.md` | 详细迁移计划（v2） |
| `GETTING_STARTED.md` | 本文件 |

### 配置模板

| 文件 | 说明 |
|------|------|
| `config/workspace.template.yaml` | Workspace 配置模板 |

### 工具脚本

| 文件 | 说明 | 使用方式 |
|------|------|----------|
| `tools/migrate.sh` | 自动化迁移脚本 | `bash tools/migrate.sh` |
| `tools/update_imports.py` | Python import 路径批量更新 | `python tools/update_imports.py` |

### 变更日志

| 文件 | 说明 |
|------|------|
| `changelogs/README.md` | 变更日志总览 |
| `changelogs/v0.1.0.md` | v0.1.0 版本变更 |
| `changelogs/unreleased.md` | 未发布变更 |

## 快速开始

### 1. 审核迁移计划

```bash
cat MIGRATION_PLAN.md
```

### 2. 创建备份

```bash
cp -r . ../LEE-backup-$(date +%Y%m%d)
```

### 3. 执行迁移

```bash
bash tools/migrate.sh
```

### 4. 更新 Import 路径

```bash
python tools/update_imports.py
```

### 5. 验证

```bash
python -m py_compile flowcore/**/*.py
```

### 6. 清理原始目录（确认无误后）

```bash
rm -rf orchestrator ai-spec MetaGPT/metagpt/lee
```

## 目标结构

```
LEE/                                    # ★ LEE 框架根目录（本项目）
├── flowcore/                           # ★ 核心代码包（改名）
│   ├── orchestrator/                   # 工作流编排器
│   │   ├── README.md                   # 使用文档
│   │   ├── ARCHITECTURE.md             # 架构文档
│   │   └── DESIGN.md                   # 设计文档
│   ├── engines/                        # 执行引擎
│   │   ├── README.md
│   │   ├── ARCHITECTURE.md
│   │   └── metagpt/                    # MetaGPT 适配层
│   ├── utils/                          # 工具模块
│   └── cli/                            # 命令行工具
├── spec-global/                        # ★ 全局规范模板（按部门组织）
│   ├── core/                           # 平台级基础规范
│   ├── departments/                    # 按部门组织
│   │   ├── pm/
│   │   ├── dev/
│   │   ├── qa/
│   │   └── ops/
│   └── cross/                          # 跨部门流程和接口
├── config/                             # 框架级配置
├── docs/                               # 框架文档
├── changelogs/                         # 变更日志
├── examples/                           # 框架使用示例
├── tools/                              # 工具脚本
└── tests/                              # 框架测试
```

## Import 路径变化

### 原始

```python
from orchestrator.core.state_machine import StateMachine
from metagpt.lee.protocol import LEERequest
```

### 目标（v2）

```python
from flowcore.orchestrator.state_machine import StateMachine
from flowcore.engines.metagpt.protocol import LEERequest
```

## 被其他产品项目引用

### 作为 Git Submodule（推荐）

在产品项目中：

```bash
cd running-coach
git submodule add https://github.com/your-org/LEE.git LEE
git submodule update --init --recursive
```

### 产品项目结构

```
running-coach/                          # 产品根目录
├── LEE/                                # ← git submodule 指向本框架
├── project/                            # 产品业务工程
│   ├── workspace.yaml                  # ← 复制自 config/workspace.template.yaml
│   ├── spec/                           # 产品专属 spec
│   └── repos/                          # 代码仓库
└── runtime/                            # 运行时目录
```

### 创建产品项目

1. **复制 workspace 配置**：

```bash
cd running-coach/project
cp ../LEE/config/workspace.template.yaml workspace.yaml
```

2. **修改 workspace.yaml**：

```yaml
spec:
  global_root: "../LEE/spec-global"  # 指向 LEE 框架
  project_root: "./spec"

repos:
  backend:
    path: "./repos/dev/backend"
    type: "git"
```

3. **运行工作流**：

```bash
cd running-coach/project
python ../LEE/flowcore/cli/main.py run workflows/my_workflow.yaml
```

## 常见问题

### Q: 为什么核心代码包叫 flowcore？

A: **flowcore** = flow（流程）+ core（核心）。这个名称：
- 简洁易记
- 语义清晰
- 符合技术命名惯例
- 易于扩展（可以有 flowcore-* 相关包）

### Q: spec-global 为什么要按部门组织？

A: 这符合"AI 一人公司"的组织思想：
- **core/**：平台级基础规范（不归任何部门）
- **departments/**：按部门垂直切分（pm/dev/qa/ops）
- **cross/**：跨部门流程和接口

既体现了组织结构，又为跨部门协作提供了专门的区域。

### Q: 迁移后原始目录还在吗？

A: 是的，迁移脚本使用 `cp` 而不是 `mv`，所以原始文件保留。确认无误后手动删除。

### Q: 如何恢复到迁移前的状态？

A: 删除新创建的目录，恢复备份：

```bash
rm -rf flowcore spec-global/config docs changelogs examples tools tests pyproject.toml
cp -r ../LEE-backup-YYYYMMDD/* .
```

### Q: 迁移后如何测试？

A: 运行以下命令验证：

```bash
# 检查 Python 语法
python -m py_compile flowcore/**/*.py

# 运行测试（如果有）
pytest tests/

# 测试 CLI
python -m flowcore.cli.main --help
```

## 下一步

迁移完成后：

1. **完善代码**：创建 `flowcore/engines/base.py` 等新文件
2. **创建模块文档**：每个模块的 README、ARCHITECTURE、DESIGN
3. **编写测试**：在 `tests/` 目录添加单元测试
4. **按部门重组 spec**：将现有 spec 分类到对应部门
5. **更新文档**：完善 `docs/` 下的文档
6. **配置 CI/CD**：添加 GitHub Actions

## 支持和文档

遇到问题？查看：

- **MIGRATION_PLAN.md** - 详细迁移计划（v2）
- **README.md** - 框架总览
- **changelogs/v0.1.0.md** - v0.1.0 版本变更
- **docs/** - 完整框架文档

## 版本历史

- **v0.1.0** (2026-01-22)：初始版本
  - 核心代码包：flowcore
  - Spec 按部门组织：core/departments/cross
  - 完善文档体系
