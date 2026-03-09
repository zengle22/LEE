# ADR-0020: lee init 命令与 project_config 模块整合重构

## 状态

**已实施** | 提案人: @dev | 实施日期: 2026-03-08 | 版本: v0.3.0

## 背景与问题

当前 LEE 框架存在两套项目初始化逻辑，导致维护困难和功能不一致：

### 问题 1: 两套并行的初始化逻辑

| 维度 | `init_project_structure()` (project_config.py) | `lee init` CLI (commands/init.py) |
|------|-----------------------------------------------|----------------------------------|
| **README 生成** | ✅ 每个目录 | ❌ 缺失 |
| **Git 仓库发现** | ❌ 无 | ✅ `.lee/repos.yaml` |
| **模板复制** | ❌ 无 | ✅ `templates/spec/` |
| **legacy 目录** | ❌ 无 | ✅ `legacy/` |
| **工具目录** | `.artifacts` → `contracts` | `.artifacts` ✅ |
| **spec 目录** | `specs/` (复数) | `spec/` (单数) ✅ |
| **dirs.yaml** | ✅ | ✅ |
| **.projectignore** | ✅ | ❌ |

### 问题 2: 目录定义分散

目录结构定义存在于多个地方：
1. `DEFAULT_DIRECTORY_SCHEMA` (project_config.py)
2. `_create_directory_structure()` 中的硬编码字典
3. `_create_dirs_yaml()` 中的 `DirectoryConfig` 对象
4. `path_policy.py` 中的常量定义

### 问题 3: 用户可见的问题

用户运行 `lee init` 后，`spec/`、`docs/`、`knowledge/` 等目录没有 README，新成员不知道这些目录的用途。

## 决策

**采用方案 B（修订版）：在 `project_config.py` 内统一初始化逻辑**

### 核心原则

1. **单一事实来源 (SSOT)**: 目录结构定义只存在一处
2. **向后兼容**: 保留现有 CLI 行为，增加功能而非改变行为
3. **模块内聚**: 不创建新模块，在现有 `project_config.py` 内重构
4. **类型安全**: 显式字段替代魔法字典

## 详细方案

### 1. 数据模型统一（显式字段替代 extras）

```python
@dataclass
class DirectoryConfig:
    """目录配置 - 替换原有的 DirectoryConfig，使用显式字段"""
    name: str
    path: str
    description: str
    subdirs: List[str] = field(default_factory=list)
    structure: str = "flat"           # flat, layered, module, hierarchical
    naming: str = "default"           # default, descriptive, timestamped
    cleanup: Optional[str] = None     # auto, manual, none
    
    # 显式定义特殊行为（替代 extras Dict）
    create_readme: bool = True                    # 是否生成 README
    readme_template: Optional[str] = None         # README 模板名称（None 用默认）
    copy_templates_from: Optional[str] = None     # 模板源路径（如 "templates/spec"）
    is_project_config: bool = False               # 是否为项目配置目录（创建 .project/README.md）


@dataclass
class DirectorySchema:
    """目录结构模式 - 统一 SSOT"""
    version: str
    description: str
    directories: Dict[str, DirectoryConfig]
    constraints: Constraints
    initialized_at: Optional[str] = None
    initialized_by: Optional[str] = None
    project_name: Optional[str] = None
```

### 2. 模块职责划分（不新建模块）

```
src/lee/orchestrator/core/
├── path_policy.py          # 保持不变（运行时策略）
└── project_config.py       # 【修改】统一数据模型 + 初始化逻辑
    ├── 数据模型
    │   ├── DirectoryConfig      # 显式字段版本
    │   ├── DirectorySchema      # 统一模式
    │   └── ProjectConfig        # 项目级配置（保留）
    ├── 配置加载/保存
    │   └── DirectorySchema.load/save()
    └── 初始化逻辑
        ├── initialize_project()       # 【新】统一初始化入口
        ├── _create_directories()      # 目录创建
        ├── _generate_readme()         # README 生成（简化版）
        ├── _discover_repos()          # Git 仓库发现（从 CLI 迁移）
        └── DEFAULT_SCHEMA: DirectorySchema  # 统一目录定义

src/lee/cli/commands/init.py  # CLI 入口
└── 调用 project_config.initialize_project()
```

### 3. 统一目录结构定义 (DEFAULT_SCHEMA)

```python
DEFAULT_SCHEMA = DirectorySchema(
    version="2.0",
    description="LEE Standard Project Directory Topology",
    directories={
        # 工具目录（LEE 元数据）
        "config_dir": DirectoryConfig(
            name="config_dir",
            path=".project",
            description="LEE 项目配置，元数据（SSOT of project）",
            subdirs=["registry"],
            structure="flat",
            is_project_config=True,           # 显式字段：创建 .project/README.md
        ),
        "workflow_dir": DirectoryConfig(
            name="workflow_dir",
            path=".workflow",
            description="工作流运行态（可清理/可重建）",
            subdirs=["runs", "cache", "traces", "evidence", "tokens", "compliance", "env-check", "instances", "approvals"],
            structure="flat",
            cleanup="auto",
        ),
        "artifacts_dir": DirectoryConfig(
            name="artifacts_dir",
            path=".artifacts",
            description="产出物（需要长期保留/可追溯）",
            subdirs=["active", "frozen", "archive"],
            structure="layered",
        ),
        
        # 内容目录（业务输出）
        "spec_dir": DirectoryConfig(
            name="spec_dir",
            path="spec",
            description="规格 SSOT（可 gate、可冻结）",
            subdirs=["requirements", "api", "data", "ui", "adr"],
            structure="flat",
            copy_templates_from="templates/spec",   # 显式字段：模板复制来源
        ),
        "docs_dir": DirectoryConfig(
            name="docs_dir",
            path="docs",
            description="解释性文档（说明、指南、报告）",
            subdirs=["guides", "reports", "archive"],
            structure="flat",
            naming="descriptive",
        ),
        "knowledge_dir": DirectoryConfig(
            name="knowledge_dir",
            path="knowledge",
            description="知识沉淀（Agent 复盘、模式提炼、能力演进）",
            subdirs=["retrospectives", "patterns", "evolution"],
            structure="flat",
        ),
        "src_dir": DirectoryConfig(
            name="src_dir",
            path="src",
            description="源码（前后端分离建议明确边界）",
            subdirs=["backend", "frontend"],
            structure="module",
        ),
        "tests_dir": DirectoryConfig(
            name="tests_dir",
            path="tests",
            description="测试（镜像 src 结构）",
            subdirs=["unit", "integration", "e2e"],
            structure="hierarchical",
        ),
        "tools_dir": DirectoryConfig(
            name="tools_dir",
            path="tools",
            description="项目工具（代码生成、lint、自检脚本）",
            subdirs=[],
            structure="flat",
        ),
        "deploy_dir": DirectoryConfig(
            name="deploy_dir",
            path="deploy",
            description="部署（docker/helm/terraform）",
            subdirs=[],
            structure="flat",
        ),
        
        # 兼容旧版
        "legacy_dir": DirectoryConfig(
            name="legacy_dir",
            path="legacy",
            description="兼容旧版（默认只读）",
            subdirs=["spec", "evidence", "env"],
            structure="flat",
            cleanup=None,
        ),
    },
    constraints=Constraints(
        strict_path_validation=True,
        forbid_creation_outside_defined_dirs=True,
        require_initialization=True,
        allow_overrides=False,
    ),
)
```

### 4. 简化的 README 生成（单一函数替代注册表）

```python
def _generate_readme(config: DirectoryConfig, project_name: Optional[str] = None) -> str:
    """
    生成目录 README 内容 - 简化版，单一函数处理所有情况
    """
    # 特殊处理：项目配置目录
    if config.is_project_config:
        return _generate_project_readme(project_name)
    
    # 默认 README 模板
    content = f"""# {config.description}

**Config Key**: `{config.name}`  
**Structure**: `{config.structure}`  
**Naming**: `{config.naming}`

"""
    if config.subdirs:
        content += "## Subdirectories\n\n"
        for subdir in config.subdirs:
            content += f"- `{subdir}/`\n"
        content += "\n"
    
    if config.cleanup == "auto":
        content += "**Note**: This directory is automatically cleaned up.\n"
    
    # 为 spec 目录添加额外说明
    if config.name == "spec_dir":
        content += """
## Gate Workflow

本目录下的规格文档需要经过 gate 流程才能冻结：
1. 创建规格草稿
2. 提交 gate 审查
3. 冻结后变为只读
"""
    
    return content


def _generate_project_readme(project_name: Optional[str]) -> str:
    """生成 .project/README.md 内容"""
    return f"""# LEE Project Configuration

**Project**: {project_name or "Unnamed Project"}

This directory contains the LEE orchestrator configuration for this project.

## Files

- `dirs.yaml`: Directory structure configuration (SSOT)
- `registry/`: Registry definitions

## Directory Structure

See `dirs.yaml` for the complete directory topology.
"""
```

### 5. 统一初始化函数

```python
def initialize_project(
    project_dir: Path,
    *,
    project_name: Optional[str] = None,
    auto_discover_repos: bool = True,
    copy_templates: bool = True,
    generate_readme: bool = True,
    max_depth: int = 4,
    force: bool = False,
) -> DirectorySchema:
    """
    【新】统一项目初始化入口
    
    整合了原 init_project_structure() 和 lee init CLI 的所有功能：
    - 目录结构创建
    - README 生成
    - Git 仓库发现
    - 模板复制
    - 配置文件创建
    """
    # 1. 检查现有配置
    config_file = project_dir / ".project" / "dirs.yaml"
    if config_file.exists() and not force:
        existing = DirectorySchema.load(project_dir)
        print(f"[INFO] Project already initialized at: {existing.initialized_at}")
        return existing
    
    # 2. 使用默认 schema
    schema = DEFAULT_SCHEMA
    schema.project_name = project_name or project_dir.name
    schema.initialized_at = datetime.now().isoformat()
    schema.initialized_by = "lee-init"
    
    # 3. 创建目录结构
    for dir_name, dir_config in schema.directories.items():
        dir_path = project_dir / dir_config.path
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        for subdir in dir_config.subdirs:
            (dir_path / subdir).mkdir(parents=True, exist_ok=True)
        
        # 4. 生成 README
        if generate_readme and dir_config.create_readme:
            readme_path = dir_path / "README.md"
            if not readme_path.exists() or force:
                readme_content = _generate_readme(dir_config, schema.project_name)
                readme_path.write_text(readme_content, encoding='utf-8')
        
        # 5. 复制模板
        if copy_templates and dir_config.copy_templates_from:
            _copy_template_tree(
                src=Path(dir_config.copy_templates_from),
                dst=dir_path
            )
    
    # 6. 创建 .project/README.md
    if generate_readme:
        project_readme = project_dir / ".project" / "README.md"
        if not project_readme.exists() or force:
            project_readme.write_text(
                _generate_project_readme(schema.project_name),
                encoding='utf-8'
            )
    
    # 7. Git 仓库发现
    if auto_discover_repos:
        _create_repo_registry(project_dir, max_depth=max_depth, force=force)
    
    # 8. 创建 .lee/config.yaml
    _create_lee_config(project_dir, force=force)
    
    # 9. 创建 .projectignore
    _create_projectignore(project_dir, force=force)
    
    # 10. 保存 schema
    schema.save()
    
    print(f"[✓] Project initialized successfully")
    return schema


# 废弃的兼容性入口
def init_project_structure(*args, **kwargs):
    """
    【废弃】请使用 initialize_project() 替代
    
    此函数保留用于向后兼容，将在 v3.0 移除。
    """
    import warnings
    warnings.warn(
        "init_project_structure() is deprecated, use initialize_project()",
        DeprecationWarning,
        stacklevel=2
    )
    return initialize_project(*args, **kwargs)
```

### 6. dirs.yaml 版本升级策略

```python
@classmethod
def load(cls, project_dir: Path) -> 'DirectorySchema':
    """加载配置，自动处理版本迁移"""
    config_file = project_dir / ".project" / "dirs.yaml"
    
    if not config_file.exists():
        raise FileNotFoundError(f"Directory structure not initialized: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    version = data.get("version", "1.0")
    
    # 版本迁移链
    if version == "1.0":
        data = cls._migrate_v1_0_to_v1_1(data)
        version = "1.1"
    
    if version == "1.1":
        # v1.1 和 v2.0 格式兼容，只需更新 version 字段
        data["version"] = "2.0"
        version = "2.0"
    
    # 解析 directories
    directories = {}
    for name, config in data.get("directories", {}).items():
        # 处理旧格式（可能没有新字段）
        config.setdefault("create_readme", True)
        config.setdefault("readme_template", None)
        config.setdefault("copy_templates_from", None)
        config.setdefault("is_project_config", name == "config_dir")
        directories[name] = DirectoryConfig(name=name, **config)
    
    return cls(
        version=version,
        description=data.get("description", ""),
        directories=directories,
        constraints=Constraints(**data.get("constraints", {})),
        initialized_at=data.get("initialized_at"),
        initialized_by=data.get("initialized_by"),
        project_name=data.get("project_name"),
    )


@staticmethod
def _migrate_v1_0_to_v1_1(data: dict) -> dict:
    """v1.0 到 v1.1 的迁移逻辑"""
    # v1.0 到 v1.1 的变更...
    data["version"] = "1.1"
    return data
```

### 7. 向后兼容策略

| 现有功能 | 兼容策略 |
|---------|---------|
| `init_project_structure()` | 保留函数，内部调用 `initialize_project()`，添加 `DeprecationWarning` |
| `DirectoryConfig` 类 | 保持同名，字段扩展（新增字段有默认值） |
| `DEFAULT_DIRECTORY_SCHEMA` | 保持变量名，指向新的 `DEFAULT_SCHEMA` |
| `dirs.yaml` v1.1 | 自动升级到 v2.0，无需用户干预 |
| CLI 参数 | 完全保留现有参数，新增可选参数 |

### 8. CLI 集成（commands/init.py）

```python
# src/lee/cli/commands/init.py
from lee.orchestrator.core.project_config import initialize_project

@click.command()
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--no-discover", is_flag=True, help="禁用自动发现 git 仓库")
@click.option("--depth", default=4, help="搜索 git 仓库的最大深度")
@click.option("--force", is_flag=True, help="强制重新生成")
@click.option("--no-readme", is_flag=True, help="不生成 README 文件 [新增]")
@click.option("--no-templates", is_flag=True, help="不复制模板文件 [新增]")
def init(project_dir, no_discover, depth, force, no_readme, no_templates):
    """初始化项目目录结构"""
    project_root = Path(project_dir).resolve()
    
    # 调用统一的初始化函数
    schema = initialize_project(
        project_dir=project_root,
        auto_discover_repos=not no_discover,
        copy_templates=not no_templates,
        generate_readme=not no_readme,
        max_depth=depth,
        force=force,
    )
    
    # CLI 特定的输出格式化...
    click.echo(click.style("✅ Project initialized successfully!", fg="green"))
```

## 实施计划（修订版）

### Phase 1: 数据模型重构（低风险）
- [ ] 在 `project_config.py` 中修改 `DirectoryConfig`，添加显式字段
- [ ] 创建新的 `DirectorySchema` 类（兼容旧 `DirectoryStructureConfig`）
- [ ] 迁移 `DEFAULT_DIRECTORY_SCHEMA` 到 `DEFAULT_SCHEMA`
- [ ] 添加版本迁移逻辑
- [ ] **测试**：单元测试数据模型加载/保存

### Phase 2: 初始化逻辑重构（中风险）
- [ ] 实现 `initialize_project()` 函数
- [ ] 实现 `_generate_readme()` 简化版
- [ ] 从 CLI 迁移 Git 仓库发现和模板复制逻辑到 `project_config.py`
- [ ] **测试**：在临时目录测试完整初始化流程

### Phase 3: CLI 迁移（低风险）
- [ ] 修改 `commands/init.py` 调用 `initialize_project()`
- [ ] 添加 `--no-readme` 和 `--no-templates` 参数
- [ ] **测试**：CLI 行为与之前一致

### Phase 4: 废弃旧 API（需要通知）
- [ ] 修改 `init_project_structure()` 添加废弃警告
- [ ] 确保旧函数内部调用新函数
- [ ] 更新文档，标注废弃计划

### Phase 5: 验证与测试
- [ ] 在现有项目上测试 `lee init --force`
- [ ] 在新项目上测试完整初始化
- [ ] 测试 dirs.yaml v1.1 自动升级
- [ ] 测试调用旧 API 的代码是否正常工作

## 测试策略

### 必须覆盖的测试场景

| 测试场景 | 验证点 |
|---------|-------|
| 全新项目初始化 | 所有目录、README、配置文件正确创建 |
| `lee init --force` 在已有项目上 | 保留用户数据，更新配置和 README |
| 读取 v1.1 的 dirs.yaml | 自动升级到 v2.0，无错误 |
| 调用废弃的 `init_project_structure()` | 正常工作，发出 DeprecationWarning |
| `--no-readme` 参数 | 不创建任何 README |
| `--no-templates` 参数 | 不复制模板文件 |
| 目录已存在但无 README | 补充创建 README（不覆盖现有文件）|

### 建议测试命令

```bash
# 单元测试
pytest tests/orchestrator/core/test_project_config.py -v

# 集成测试（临时目录）
python -c "
import tempfile
from pathlib import Path
from lee.orchestrator.core.project_config import initialize_project

with tempfile.TemporaryDirectory() as tmp:
    initialize_project(Path(tmp), project_name='test-project')
    # 验证目录结构...
"

# CLI 测试
lee init --project-dir /tmp/test-init --no-discover
```

## 影响分析

### 对用户的影响
- ✅ 新初始化的项目会有完整的 README 文档
- ✅ CLI 行为保持不变
- ✅ 新增 `--no-readme`、`--no-templates` 参数

### 对开发者的影响
- ✅ 目录结构定义只需修改 `DEFAULT_SCHEMA` 一处
- ✅ `project_config.py` 模块职责更清晰

### 对现有代码的影响
- ✅ 现有 `dirs.yaml` 文件自动升级，无需修改
- ✅ 现有调用 `init_project_structure()` 的代码仍然工作（带废弃警告）

## 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|-------|------|---------|
| 初始化逻辑 bug 导致数据丢失 | 低 | 高 | 1. 充分单元测试 2. 集成测试 3. 保留 `--force` 备份 |
| 向后兼容性问题 | 中 | 中 | 1. 旧函数保留 2. 废弃警告 3. 自动版本迁移 |
| 性能下降 | 低 | 低 | 1. 性能测试 2. 优化文件操作 |

## 决策记录

| 日期 | 决策者 | 决策 |
|------|-------|------|
| 2026-03-08 | @dev | 提出方案 B |
| 2026-03-08 | 架构师 | 评审通过（修订版）- 要求：1) 不新建模块 2) 显式字段替代 extras 3) 简化 README 模板 |
| 2026-03-08 | @dev | 实施完成 - v0.3.0 发布 |

## 相关链接

- 问题来源：`lee init` 没有为 `spec/` 目录生成 README
- 相关代码：
  - `src/lee/cli/commands/init.py`
  - `src/lee/orchestrator/core/project_config.py`
  - `src/lee/orchestrator/core/path_policy.py`

---

**评审意见区**

<!-- 架构师评审已通过，见决策记录 -->

**修订说明（v2）**:
1. ❌ 移除了新建 `project_initializer.py` 模块的计划，改为在 `project_config.py` 内重构
2. ❌ 移除了 `extras: Dict` 设计，改用显式字段（`create_readme`, `copy_templates_from`, `is_project_config`）
3. ❌ 简化了 README 模板系统，由注册表模式改为单一函数 + 条件分支
4. ✅ 细化了向后兼容策略，明确废弃警告和迁移路径
5. ✅ 添加了 dirs.yaml 版本升级策略（v1.1 → v2.0 自动迁移）
6. ✅ 补充了具体测试策略和测试命令

