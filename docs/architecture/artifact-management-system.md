# LEE 产出物管理系统设计方案

> 版本: v2.0 (收缩版)
> 创建日期: 2026-02-26
> 状态: 设计评审通过，待实施

---

## 目录

1. [问题诊断](#1-问题诊断)
2. [设计原则](#2-设计原则)
3. [目录结构设计](#3-目录结构设计)
4. [数据模型](#4-数据模型)
5. [核心模块设计](#5-核心模块设计)
6. [Run 级 Manifest 机制](#6-run-级-manifest-机制)
7. [与 LEE 现有系统的集成](#7-与-lee-现有系统的集成)
8. [CLI 命令设计](#8-cli-命令设计)
9. [配置管理](#9-配置管理)
10. [实施路线](#10-实施路线)

---

## 1. 问题诊断

### 1.1 当前存在的核心问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **产出物散落** | 散布在 `.workflow/`、`output/`、各部门 `output/` 等多处 | 难以查找和管理 |
| **类型混杂** | 日志、证据、文档、代码、测试用例、脚本混在一起 | 无法区分优先级和用途 |
| **版本管理缺失** | 没有统一的版本控制和冻结机制 | 难以追溯和回滚 |
| **流转关系不清** | 产出物之间的依赖关系没有明确记录 | 影响问题排查 |
| **清理机制缺失** | 临时文件和历史积累无自动清理 | 占用空间 |
| **平行目录问题** | Agent 可能在多个位置创建同名文件 | 导致"平行世界"问题 |

### 1.2 设计目标

1. **统一存储**：所有产出物集中在 `.artifacts/` 目录下管理
2. **清晰分类**：按类型和部门双重索引
3. **状态管理**：草稿 → 活跃 → 冻结 → 归档的清晰生命周期
4. **关系追踪**：记录产出物之间的依赖和派生关系
5. **自动清理**：按保留策略自动清理过期文件
6. **可追溯**：完整的历史记录和版本管理
7. **紧贴 LEE**：作为 LEE 核心执行流程的内嵌骨架，而非独立平台

---

## 2. 设计原则

### 2.1 核心原则

1. **内嵌而非独立**：Artifact Manager 紧紧挂在 `run_id/workflow_id` 上，不是独立宇宙
2. **先收后放**：优先实现最关键的 20% 功能，其余作为演进路线
3. **强制入口**：所有产出物必须通过 ArtifactManager.create/adopt 进入系统
4. **单一事实源**：每个 run 有一个 manifest.yaml 作为状态根
5. **代码引用原则**：源代码/配置只存引用（git SHA），不复制内容

### 2.2 架构定位

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEE Core System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐       │
│  │   Orchestrator   │   │   Gate       │    │  Executor   │       │
│  └──────┬──────┘    └──────┬───────┘    └──────┬──────┘       │
│         │                   │                    │             │
│         └───────────────────┼────────────────────┘             │
│                             ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   Artifact Manager                       │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │ │
│  │  │ Registry│ │ Manifest│ │ Validator│ │ Lifecycle│        │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                   ▲                    │            │
│         ▼                   │                    ▼            │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    │
│  │   .artifacts/active/{run_id}/   │    │ .artifacts/frozen/ ││
│  └─────────────────────────────────────────────────────────┘ │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  .workflow/           (仅作 runtime scratch，不作为长期存储)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构设计

### 3.1 完整目录结构

```
.artifacts/                              # 产出物根目录
│
├── config.yaml                          # 配置文件
│
├── active/                              # 活跃运行产出物
│   ├── {run_id}/                        # 按 run_id 组织
│   │   ├── manifest.yaml                # 【关键】run 级 manifest
│   │   │
│   │   ├── inputs/                      # 输入文件
│   │   │   ├── requirements/            # 需求文档
│   │   │   ├── contracts/               # 契约引用
│   │   │   └── handovers/               # 接收的交接文档
│   │   │
│   │   ├── outputs/                     # 输出文件
│   │   │   ├── contracts/               # 契约产出
│   │   │   │   ├── prd/
│   │   │   │   ├── dev/
│   │   │   │   ├── qa/
│   │   │   │   └── ...
│   │   │   ├── documents/               # 文档产出
│   │   │   │   ├── design/
│   │   │   │   ├── review/
│   │   │   │   └── analysis/
│   │   │   ├── code/                    # 代码产出（主要是 patch）
│   │   │   │   └── patches/
│   │   │   ├── tests/                   # 测试产出
│   │   │   │   ├── test_cases/
│   │   │   │   ├── test_reports/
│   │   │   │   └── coverage/
│   │   │   └── scripts/                 # 生成的脚本
│   │   │
│   │   ├── intermediate/                # 中间产物
│   │   │   ├── drafts/                  # 草稿
│   │   │   ├── partials/                # 部分结果
│   │   │   └── cache/                   # 临时缓存
│   │   │
│   │   └── handover/                    # 交接文档
│   │       ├── to-{dept}/               # 交接给某部门
│   │       └── from-{dept}/             # 从某部门接收
│   │
│   └── current/                         # 当前活跃项目（符号链接）
│
├── frozen/                              # 冻结的产出物（不可变）
│   ├── contracts/                       # 冻结契约
│   │   ├── prd/
│   │   │   └── FDPRD-{YYYY}-{NNN}.yaml
│   │   ├── dev/
│   │   │   ├── FPKG-{YYYY}-{NNN}.yaml   # Frozen Package
│   │   │   ├── FTA-{YYYY}-{NNN}.yaml    # Frozen Technical Arch
│   │   │   └── API-{YYYY}-{NNN}.yaml    # API Contract
│   │   ├── qa/
│   │   │   └── FTEST-{YYYY}-{NNN}.yaml  # Frozen Test Plan
│   │   └── ...
│   │
│   └── baselines/                       # 基线版本
│       └── BL-{YYYY}-W{NN}.yaml
│
├── archive/                             # 归档产出物
│   ├── by-date/                         # 按日期归档
│   │   └── {YYYY}/{MM}/{DD}/
│   └── by-project/                      # 按项目归档
│       └── {project_name}/
│
├── logs/                                # 执行日志（独立存储）
│   ├── workflows/                       # 工作流日志
│   │   └── {run_id}.log
│   ├── agents/                          # Agent 日志
│   └── system/                          # 系统日志
│
└── registry/                            # 注册表（元数据索引）
    ├── index.json                       # 全局索引
    ├── by-type/                         # 按类型索引
    ├── by-department/                   # 按部门索引
    └── by-workflow/                     # 按工作流索引
```

### 3.2 关键设计决策

1. **run_id 作为一级组织单位**
   - 每个 run 都有自己的目录空间
   - 便于整包清理、归档、追溯

2. **manifest.yaml 作为单一事实源**
   - 记录该 run 的所有产出物信息
   - 即使 registry 异步更新，仍可从磁盘重建状态

3. **frozen/ 存放不可变产出物**
   - 冻结后的产出物物理移动到此目录
   - 作为下游工作的权威事实基线

4. **.workflow/ 角色重新定位**
   - 仅作为 executor runtime 临时目录
   - 真正要留存的一律通过 ArtifactManager 挂到 `.artifacts/active` 下

### 3.3 与代码仓库的关系

```
代码仓库 vs .artifacts 存储原则：

┌─────────────────────┬─────────────────────────────────────────┐
│      类型           │                    处理方式               │
├─────────────────────┼─────────────────────────────────────────┤
│ source_code         │ 只存引用：repo + git SHA + file path    │
│ test_code           │ 只存引用：repo + git SHA + file path    │
│ config              │ 只存引用：repo + git SHA + file path    │
│ patch               │ 存文件：.artifacts/active/{run_id}/...  │
│ script              │ 存文件：.artifacts/active/{run_id}/...  │
│ contracts           │ 存文件：.artifacts/frozen/contracts/    │
│ documents           │ 存文件：.artifacts/active/{run_id}/...  │
│ tests               │ 存文件：.artifacts/active/{run_id}/...  │
└─────────────────────┴─────────────────────────────────────────┘
```

---

## 4. 数据模型

### 4.1 ArtifactType 枚举

```python
class ArtifactType(Enum):
    """产出物类型 - 大类"""
    CONTRACT = "contract"       # 契约类（核心数据结构）
    DOCUMENT = "document"       # 文档类（说明和指导）
    CODE_REF = "code_ref"       # 代码引用（git SHA，不存内容）
    PATCH = "patch"             # 补丁文件（存内容）
    TEST = "test"               # 测试类（测试用例/报告）
    HANDOVER = "handover"       # 交接文档
    LOG = "log"                 # 日志类
    INTERMEDIATE = "intermediate"  # 中间产物
```

### 4.2 ArtifactCategory 枚举（从配置生成）

```python
# 从 config.yaml 的 categories 生成，避免模型-配置双写
class ArtifactCategory(Enum):
    """产出物分类 - 具体分类（配置驱动）"""

    # 契约类
    FROZEN_PRD = "frozen_prd"
    FROZEN_DEV_PACKAGE = "frozen_dev_package"
    FROZEN_UI_PROTOTYPE = "frozen_ui_prototype"
    FROZEN_TECH_ARCH = "frozen_tech_arch"
    API_CONTRACT = "api_contract"
    TEST_PLAN = "test_plan"
    DEPLOY_CONFIG = "deploy_config"

    # 文档类
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    DESIGN_DOC = "design_doc"
    REVIEW_REPORT = "review_report"
    TECHNICAL_DOC = "technical_doc"

    # 代码引用
    SOURCE_CODE = "source_code"
    TEST_CODE_REF = "test_code_ref"
    CONFIG_REF = "config_ref"

    # 补丁和脚本
    CODE_PATCH = "code_patch"
    BUILD_SCRIPT = "build_script"
    DEPLOY_SCRIPT = "deploy_script"

    # 测试类
    TEST_CASE = "test_case"
    TEST_REPORT = "test_report"
    COVERAGE_REPORT = "coverage_report"
    E2E_RESULT = "e2e_result"
    BUG_REPORT = "bug_report"

    # 交接
    DEPT_HANDOVER = "dept_handover"

    # 日志
    EXECUTION_LOG = "execution_log"
    TRACE_LOG = "trace_log"
```

### 4.3 ArtifactStatus 枚举

```python
class ArtifactStatus(Enum):
    """产出物状态"""
    DRAFT = "draft"              # 草稿（在 intermediate/）
    ACTIVE = "active"            # 活跃（在 outputs/）
    FROZEN = "frozen"            # 冻结（不可变，在 frozen/）
    ARCHIVED = "archived"        # 已归档（在 archive/）
    DEPRECATED = "deprecated"    # 已废弃（逻辑上不推荐，但仍可引用）
```

### 4.4 ArtifactMetadata 数据模型

```python
@dataclass
class ArtifactMetadata:
    """产出物元数据"""

    # === 标识信息 ===
    id: str                      # 唯一标识，格式：{category}-{timestamp}-{short_id}
    type: ArtifactType           # 大类
    category: ArtifactCategory   # 具体分类（强类型，从配置生成）
    status: ArtifactStatus       # 状态

    # === 路径信息 ===
    path: str                    # 文件路径（相对路径，相对于 .artifacts/）
    absolute_path: str           # 绝对路径（运行时计算）

    # === 对于代码引用类型 ===
    ref_type: Optional[str] = None  # "git" | "file" | None
    repo_name: Optional[str] = None
    git_commit: Optional[str] = None
    git_path: Optional[str] = None

    # === 所属信息 ===
    run_id: str                  # 所属运行 ID（必填）
    workflow_id: Optional[str] = None  # 所属工作流 ID
    project: Optional[str] = None      # 所属项目
    department: Optional[str] = None   # 所属部门

    # === 关系信息（全部基于 artifact id） ===
    depends_on: List[str] = field(default_factory_list)  # 依赖的产出物 ID
    derived_from: Optional[str] = None  # 源产出物 ID
    consumed_by: List[str] = field(default_factory_list)  # 被哪些产出物消费
    handover_refs: List[str] = field(default_factory_list)  # 关联的交接文档 ID

    # === 版本信息 ===
    version: str = "1.0.0"
    frozen_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    # === 验证信息 ===
    contract_schema: Optional[str] = None  # 遵循的契约 schema 路径
    validation_status: str = "pending"     # pending | passed | failed
    validation_errors: List[str] = field(default_factory_list)

    # === 时间信息 ===
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # 创建者（agent/executor 名称）

    # === 其他属性 ===
    size: int = 0                 # 文件大小（字节）
    hash: Optional[str] = None    # 内容哈希（SHA256）
    tags: List[str] = field(default_factory_list)
    attributes: Dict[str, Any] = field(default_factory_dict)
```

### 4.5 RunManifest 数据模型

```python
@dataclass
class RunManifest:
    """Run 级 Manifest - 单一事实源"""

    # === Run 信息 ===
    run_id: str
    workflow_id: str
    workflow_name: str
    project: str
    iteration: Optional[str] = None

    # === 时间信息 ===
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running | completed | failed | cancelled

    # === 产出物清单 ===
    artifacts: Dict[str, ArtifactMetadata] = field(default_factory_dict)
    # 按 artifact id 索引的元数据

    # === 输入引用 ===
    inputs: Dict[str, List[str]] = field(default_factory_dict)
    # {
    #   "contracts": ["FDPRD-2026-001", "FPKG-2026-001"],
    #   "handovers": ["HANDOVER-2026-001"],
    # }

    # === 交接信息 ===
    handovers: Dict[str, HandoverInfo] = field(default_factory_dict)
    # {
    #   "to-dev": HandoverInfo(...),
    #   "from-qa": HandoverInfo(...),
    # }

    # === Gate 引用 ===
    gates: List[str] = field(default_factory_list)
    # 此 run 相关的 gate ID

    # === 统计信息 ===
    stats: Dict[str, Any] = field(default_factory_dict)
    # {
    #   "total_artifacts": 10,
    #   "frozen_artifacts": 3,
    #   "validation_failed": 0,
    # }

    def save(self, path: str):
        """保存 manifest 到文件"""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path: str) -> "RunManifest":
        """从文件加载 manifest"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
```

### 4.6 HandoverInfo 数据模型

```python
@dataclass
class HandoverInfo:
    """交接文档信息"""

    id: str                      # 交接文档 ID
    from_dept: str               # 交出部门
    to_dept: str                 # 接收部门

    artifacts: List[str]         # 涉及的 artifact ID

    context: Dict[str, str] = field(default_factory_dict)
    # {
    #   "project": "ai-marathon-coach",
    #   "iteration": "2026-W08",
    #   "goal": "实现用户登录功能",
    # }

    checklist: List[Dict[str, Any]] = field(default_factory_list)
    # [
    #   {"item": "PRD已冻结", "status": True},
    #   {"item": "UI原型已确认", "status": True},
    # ]

    notes: List[str] = field(default_factory_list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
```

---

## 5. 核心模块设计

### 5.1 模块结构

```
src/lee/artifacts/
├── __init__.py
├── models.py                   # 数据模型
├── manager.py                  # 核心管理器
├── manifest.py                 # Manifest 管理
├── registry.py                 # 注册表管理
├── validator.py                # 验证器
├── lifecycle.py                # 生命周期管理
├── storage/                    # 存储后端
│   ├── __init__.py
│   ├── base.py                 # 抽象基类
│   └── local.py                # 本地存储实现
├── commands/                   # CLI 命令
│   ├── __init__.py
│   ├── list.py                 # 列表命令
│   ├── show.py                 # 显示命令
│   ├── adopt.py                # 认领命令
│   ├── freeze.py               # 冻结命令
│   ├── validate.py             # 验证命令
│   ├── clean.py                # 清理命令
│   └── rebuild_index.py        # 重建索引命令
└── config.py                   # 配置管理
```

### 5.2 ArtifactManager 核心接口

```python
class ArtifactManager:
    """产出物管理器 - 核心入口"""

    def __init__(self, root_dir: str, config_path: str = None):
        self.root_dir = Path(root_dir)
        self.config = self._load_config(config_path)
        self.registry = ArtifactRegistry(self.root_dir / "registry")
        self.storage = LocalStorageBackend(self.root_dir)
        self.validator = ArtifactValidator(self.root_dir / "contracts")
        self._load_categories()

    def _load_categories(self):
        """从配置加载 categories，强校验"""
        # 从 config.yaml 读取 categories
        # 动态生成 ArtifactCategory 枚举
        # 确保 create() 时强校验 category 是否合法

    # === 核心 CRUD ===

    async def create(
        self,
        content: str,
        category: ArtifactCategory,
        run_id: str,
        metadata: dict = None,
    ) -> ArtifactMetadata:
        """
        创建新产出物

        强制校验：
        - category 必须在配置中定义
        - run_id 必须存在且有效
        - 如果有 contract_schema，自动验证
        """

    async def adopt(
        self,
        path: str,
        category: ArtifactCategory,
        run_id: str,
        metadata: dict = None,
    ) -> ArtifactMetadata:
        """
        认领现有文件

        用途：
        - 迁移老数据
        - 注册 runtime 生成的文件
        - 不移动原文件，只生成元数据 + 索引
        """

    async def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """获取产出物"""

    async def find(
        self,
        type: ArtifactType = None,
        category: ArtifactCategory = None,
        status: ArtifactStatus = None,
        run_id: str = None,
        workflow_id: str = None,
        department: str = None,
        project: str = None,
        tags: List[str] = None,
    ) -> List[ArtifactMetadata]:
        """查找产出物"""

    # === 生命周期 ===

    async def freeze(
        self,
        artifact_id: str,
        reason: str = None,
    ) -> ArtifactMetadata:
        """
        冻结产出物

        操作：
        1. 验证产出物（如果有 contract_schema）
        2. 物理移动到 .artifacts/frozen/
        3. 更新 status = FROZEN
        4. 记录 frozen_at 和原因
        5. 更新 registry
        6. 更新 manifest
        """

    async def archive(
        self,
        artifact_id: str,
    ) -> ArtifactMetadata:
        """
        归档产出物

        操作：
        1. 物理移动到 .artifacts/archive/
        2. 更新 status = ARCHIVED
        3. 记录 archived_at
        4. 更新 registry
        """

    # === 关系管理 ===

    async def link(
        self,
        from_id: str,
        to_id: str,
        link_type: str = "dependency",
    ):
        """
        建立产出物之间的关联

        link_type:
        - dependency: from_id 依赖 to_id
        - derived: from_id 派生自 to_id
        - consumed: from_id 被 to_id 消费
        """

    async def create_handover(
        self,
        from_dept: str,
        to_dept: str,
        artifacts: List[str],
        context: dict = None,
        run_id: str = None,
    ) -> HandoverInfo:
        """
        创建交接文档
        """

    # === 验证 ===

    async def validate(
        self,
        artifact_id: str,
        schema_path: str = None,
    ) -> ValidationResult:
        """
        验证产出物

        根据 contract_schema 验证内容和格式
        """

    # === Run 级操作 ===

    async def get_run_manifest(self, run_id: str) -> RunManifest:
        """获取 run 的 manifest"""

    async def create_run(
        self,
        run_id: str,
        workflow_id: str,
        project: str,
    ) -> RunManifest:
        """
        创建新 run

        操作：
        1. 创建 .artifacts/active/{run_id}/ 目录
        2. 初始化 manifest.yaml
        3. 注册到 registry
        """

    async def complete_run(
        self,
        run_id: str,
        status: str = "completed",
    ):
        """
        完成 run

        操作：
        1. 更新 manifest 状态
        2. 计算统计信息
        3. 可选：自动清理 intermediate/
        """

    # === 清理 ===

    async def clean(
        self,
        before_date: datetime = None,
        status: ArtifactStatus = None,
        dry_run: bool = False,
    ) -> List[str]:
        """
        清理过期产出物

        根据 retention 配置清理
        """
```

### 5.3 ArtifactRegistry 接口

```python
class ArtifactRegistry:
    """产出物注册表"""

    def __init__(self, registry_dir: str):
        self.dir = Path(registry_dir)
        self.index_file = self.dir / "index.json"
        self._load_index()

    async def register(self, artifact: ArtifactMetadata):
        """注册产出物"""

    async def update(self, artifact: ArtifactMetadata):
        """更新产出物注册信息"""

    async def unregister(self, artifact_id: str):
        """注销产出物"""

    async def find(self, **filters) -> List[ArtifactMetadata]:
        """查找产出物"""

    async def rebuild_index(self) -> int:
        """
        重建索引

        从磁盘扫描 .artifacts/，重建 registry/index.json
        是一种"救命/修复"工具
        """

    def _update_by_type_index(self, artifact: ArtifactMetadata):
        """更新按类型索引"""

    def _update_by_dept_index(self, artifact: ArtifactMetadata):
        """更新按部门索引"""

    def _update_by_workflow_index(self, artifact: ArtifactMetadata):
        """更新按工作流索引"""
```

---

## 6. Run 级 Manifest 机制

### 6.1 Manifest 结构

```yaml
# .artifacts/active/{run_id}/manifest.yaml

version: "1.0"

# Run 信息
run_id: "RUN-20260226-abc123"
workflow_id: "wf_department_dev_123"
workflow_name: "dept_development"
project: "ai-marathon-coach"
iteration: "2026-W08"

# 时间
started_at: "2026-02-26T10:00:00Z"
completed_at: "2026-02-26T12:30:00Z"
status: "completed"

# 产出物清单（按类别组织）
artifacts:
  contracts:
    - id: "FPKG-2026-001"
      category: "frozen_dev_package"
      path: "frozen/contracts/dev/FPKG-2026-001.yaml"
      status: "frozen"
      frozen_at: "2026-02-26T12:00:00Z"

    - id: "API-2026-001"
      category: "api_contract"
      path: "active/RUN-20260226-abc123/outputs/contracts/dev/api.yaml"
      status: "active"

  documents:
    - id: "DOC-2026-001"
      category: "design_doc"
      path: "active/RUN-20260226-abc123/outputs/documents/design/arch.yaml"
      status: "active"

  code_refs:
    - id: "CODE-2026-001"
      category: "source_code"
      ref_type: "git"
      repo_name: "running-master"
      git_commit: "abc123def456"
      git_path: "backend/service/user.py"

  patches:
    - id: "PATCH-2026-001"
      category: "code_patch"
      path: "active/RUN-20260226-abc123/outputs/code/patches/user-service.patch"
      status: "active"

  tests:
    - id: "TEST-2026-001"
      category: "test_report"
      path: "active/RUN-20260226-abc123/outputs/tests/reports/unit.json"
      status: "active"

# 输入引用
inputs:
  contracts:
    - "FDPRD-2026-001"
    - "FUIP-2026-001"

  handovers:
    - "HANDOVER-2026-001"

# 交接信息
handovers:
  to-qa:
    id: "HANDOVER-2026-002"
    to_dept: "qa"
    artifacts:
      - "API-2026-001"
      - "PATCH-2026-001"
    checklist:
      - item: "API 契约已定义"
        status: true
      - item: "代码已通过测试"
        status: true

# Gate 引用
gates:
  - "GATE-2026-001"

# 统计
stats:
  total_artifacts: 5
  frozen_artifacts: 1
  code_refs: 1
  patches: 1
  validation_failed: 0
```

### 6.2 Manifest 操作

```python
# manifest.py

class ManifestManager:
    """Manifest 管理器"""

    def __init__(self, artifacts_root: str):
        self.root_dir = Path(artifacts_root)

    async def create(
        self,
        run_id: str,
        workflow_id: str,
        project: str,
    ) -> RunManifest:
        """创建新 run 的 manifest"""

    async def load(self, run_id: str) -> RunManifest:
        """加载 run 的 manifest"""

    async def save(self, manifest: RunManifest):
        """保存 manifest 到文件"""

    async def add_artifact(
        self,
        run_id: str,
        artifact: ArtifactMetadata,
    ):
        """添加产出物到 manifest"""

    async def update_status(
        self,
        run_id: str,
        status: str,
    ):
        """更新 run 状态"""

    async def get_stats(
        self,
        run_id: str,
    ) -> Dict[str, Any]:
        """获取 run 统计信息"""
```

---

## 7. 与 LEE 现有系统的集成

### 7.1 三个关键入口

```
┌─────────────────────────────────────────────────────────────┐
│                     LEE 执行流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Workflow Run 创建                                       │
│     │                                                        │
│     ├─> Orchestrator 创建 run_id                            │
│     │                                                        │
│     └─> 调用 ArtifactManager.create_run()                    │
│         ├─ 创建 .artifacts/active/{run_id}/                 │
│         └─ 初始化 manifest.yaml                              │
│                                                               │
│  2. Step 执行（FileOutputHandler 集成）                      │
│     │                                                        │
│     ├─ Agent 产出内容                                        │
│     │                                                        │
│     ├─ FileOutputHandler 解析输出                           │
│     │                                                        │
│     └─> 调用 ArtifactManager.create()/adopt()                │
│         ├─ 根据 category 确定存储位置                        │
│         ├─ 代码引用类型：只存 git SHA                        │
│         ├─ patch/script：存到 active/{run_id}/outputs/      │
│         └─ 更新 manifest + registry                         │
│                                                               │
│  3. Gate 验收                                                │
│     │                                                        │
│     ├─ Gate 检查所需证据                                     │
│     │                                                        │
│     ├─> 调用 ArtifactManager.find() 查找产出物              │
│         │                                                    │
│         ├─ 按 category 查找（如 frozen_prd, test_report）   │
│         └─ 验证产出物状态（必须是 frozen）                   │
│     │                                                        │
│     ├─ 验证通过                                              │
│     │                                                        │
│     └─> 调用 ArtifactManager.freeze()                        │
│         ├─ 移动到 .artifacts/frozen/                         │
│         └─ 更新 manifest + registry                         │
│                                                               │
│  4. Run 完成                                                │
│     │                                                        │
│     └─> 调用 ArtifactManager.complete_run()                  │
│         ├─ 更新 manifest 状态                                │
│         └─ 可选：清理 intermediate/                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 FileOutputHandler 集成

```python
# 修改后的 FileOutputHandler

class FileOutputHandler:
    """文件输出处理器 - 集成 ArtifactManager"""

    def __init__(self, artifact_manager: ArtifactManager):
        self.am = artifact_manager

    async def handle(
        self,
        llm_output: str,
        outputs_spec: List[Any],
        run_id: str,
    ) -> List[str]:
        """
        处理 LLM 输出，保存文件

        集成 ArtifactManager：
        1. 解析输出
        2. 根据 outputs_spec 确定 category
        3. 调用 artifact_manager.create()
        4. 自动更新 manifest
        """
        parsed_outputs = self._parse_llm_output(llm_output)

        artifact_ids = []

        for spec in outputs_spec:
            # 确定输出类型和分类
            category = self._determine_category(spec)
            artifact_type = self._determine_type(spec)

            # 获取内容
            content = self._find_content(spec, parsed_outputs)

            # 决定处理方式
            if artifact_type == ArtifactType.CODE_REF:
                # 代码引用：从 git repo 获取信息
                metadata = self._extract_git_metadata(content)
                artifact = await self.am.adopt(
                    path=metadata["git_path"],
                    category=category,
                    run_id=run_id,
                    metadata=metadata,
                )
            else:
                # 其他类型：创建新产出物
                artifact = await self.am.create(
                    content=content,
                    category=category,
                    run_id=run_id,
                )

            artifact_ids.append(artifact.id)

        return artifact_ids
```

### 7.3 Gate 集成

```python
# Gate 验证配置

gate:
  id: "GATE-2026-001"
  name: "开发完成验收"

  # 所需证据（按 category）
  required_artifacts:
    - category: "frozen_dev_package"
      status: "frozen"
      required: true

    - category: "test_report"
      min_count: 1
      validation_status: "passed"

    - category: "api_contract"
      required: true

  # 验证逻辑
  validation:
    - check: "all_required_artifacts_present"
    - check: "all_frozen_artifacts_valid"
    - check: "test_reports_passed"

  # 通过后的操作
  on_pass:
    - freeze: ["frozen_dev_package"]
    - create_handover:
        to_dept: "qa"
        artifacts: "all_outputs"

# Gate 验证器

class GateValidator:
    """Gate 验证器 - 集成 ArtifactManager"""

    def __init__(self, artifact_manager: ArtifactManager):
        self.am = artifact_manager

    async def validate(
        self,
        gate_config: dict,
        run_id: str,
    ) -> ValidationResult:
        """验证 gate 是否通过"""

        results = []

        for requirement in gate_config["required_artifacts"]:
            # 查找产出物
            artifacts = await self.am.find(
                category=requirement["category"],
                run_id=run_id,
                status=requirement.get("status"),
            )

            # 验证数量
            if requirement.get("required") and not artifacts:
                results.append(ValidationResult(
                    field=requirement["category"],
                    passed=False,
                    message=f"缺少必需的产出物: {requirement['category']}",
                ))
                continue

            # 验证状态
            for artifact in artifacts:
                if artifact.status != requirement.get("status"):
                    results.append(ValidationResult(
                        field=artifact.id,
                        passed=False,
                        message=f"产出物状态不符: 期望 {requirement.get('status')}, 实际 {artifact.status}",
                    ))

        return ValidationResult(results)
```

### 7.4 交接流程集成

```python
# QA → Dev 交接流程示例

# 1. QA 完成 L2，生成交接文档
qa_run_id = "RUN-20260226-qa-001"
handover = await am.create_handover(
    from_dept="qa",
    to_dept="dev",
    artifacts=[
        "FDPRD-2026-001",  # 冻结的 PRD
        "BUGSET-2026-001", # Bug 集
        "TEST-2026-001",   # 测试报告
    ],
    context={
        "project": "ai-marathon-coach",
        "iteration": "2026-W08",
        "goal": "修复用户登录 Bug",
    },
    run_id=qa_run_id,
)

# 2. Dev 启动 L2，接收交接
dev_run_id = "RUN-20260226-dev-001"

# 获取交接文档
handover_info = await am.find(handover_id=handover.id)

# 加载所有相关的输入
input_artifacts = []
for artifact_id in handover_info.artifacts:
    artifact = await am.get(artifact_id)
    input_artifacts.append(artifact)

# 3. Dev L2 执行...
# ... 使用 input_artifacts 作为输入

# 4. Dev 完成，创建新的交接给 QA
dev_handover = await am.create_handover(
    from_dept="dev",
    to_dept="qa",
    artifacts=[...],  # Dev 的产出物
    run_id=dev_run_id,
)
```

---

## 8. CLI 命令设计

### 8.1 核心命令

```bash
# === 查找 ===
# 列出产出物
lee artifacts list \
  [--type TYPE] \
  [--category CATEGORY] \
  [--status STATUS] \
  [--dept DEPT] \
  [--run RUN_ID] \
  [--project PROJECT]

# 按run查找
lee artifacts list --run RUN-20260226-abc123

# 按类型查找
lee artifacts list --type contract --status frozen

# === 显示 ===
# 查看产出物详情
lee artifacts show ARTIFACT_ID

# 查看产出物内容
lee artifacts cat ARTIFACT_ID

# 查看run的manifest
lee artifacts manifest RUN_ID

# === 管理 ===
# 认领现有文件（迁移用）
lee artifacts adopt PATH \
  --category CATEGORY \
  --run RUN_ID \
  [--metadata KEY=VALUE]

# 批量认领
lee artifacts adopt "outputs/**/*.yaml" \
  --category api_contract \
  --run RUN-20260226-abc123

# === 生命周期 ===
# 冻结产出物
lee artifacts freeze ARTIFACT_ID [--reason REASON]

# 批量冻结
lee artifacts freeze --run RUN_ID --category frozen_dev_package

# 归档产出物
lee artifacts archive ARTIFACT_ID

# 归档整个run
lee artifacts archive-run RUN_ID

# === 验证 ===
# 验证产出物
lee artifacts validate ARTIFACT_ID [--schema SCHEMA_PATH]

# 验证整个run
lee artifacts validate-run RUN_ID

# === 清理 ===
# 清理过期产出物
lee artifacts clean \
  [--before DATE] \
  [--status STATUS] \
  [--dry-run]

# 清理指定run的中间产物
lee artifacts clean-intermediate RUN_ID

# === 索引 ===
# 重建索引（救命工具）
lee artifacts rebuild-index

# === 交接 ===
# 查看交接文档
lee artifacts handover show HANDOVER_ID

# 列出交接
lee artifacts handover list \
  [--from DEPT] \
  [--to DEPT] \
  [--run RUN_ID]

# 确认接收交接
lee artifacts handover acknowledge HANDOVER_ID
```

### 8.2 命令输出示例

```bash
$ lee artifacts list --run RUN-20260226-abc123

Run: RUN-20260226-abc123
Workflow: dept_development
Project: ai-marathon-coach
Status: completed

Artifacts (5):
┌─────────────────────┬─────────────────┬─────────┬─────────────┐
│ ID                  │ Category        │ Status  │ Path        │
├─────────────────────┼─────────────────┼─────────┼─────────────┤
│ FPKG-2026-001       │ frozen_dev_pkg  │ frozen  │ frozen/con… │
│ API-2026-001        │ api_contract    │ active  │ active/RUN… │
│ DOC-2026-001        │ design_doc      │ active  │ active/RUN… │
│ CODE-2026-001       │ source_code     │ active  │ git:abc123… │
│ PATCH-2026-001      │ code_patch      │ active  │ active/RUN… │
└─────────────────────┴─────────────────┴─────────┴─────────────┘

Handovers:
  → to-qa: HANDOVER-2026-002
  ← from-prd: HANDOVER-2026-001

Gates:
  ✓ GATE-2026-001 (passed)
```

---

## 9. 配置管理

### 9.1 主配置文件

```yaml
# .artifacts/config.yaml

version: "1.0"

# === 目录配置 ===
directories:
  root: ".artifacts"
  active: ".artifacts/active"
  frozen: ".artifacts/frozen"
  archive: ".artifacts/archive"
  logs: ".artifacts/logs"
  cache: ".artifacts/cache"
  registry: ".artifacts/registry"

# === 产出物分类定义 ===
# （强校验，代码从这里生成 Enum）
categories:
  # 契约类
  frozen_prd:
    type: "contract"
    dept: "prd"
    schema: "spec-global/departments/prd/contracts/frozen-detailed-prd-contract/v1/schema.json"
    output_dir: "contracts/prd"

  frozen_dev_package:
    type: "contract"
    dept: "dev"
    schema: "spec-global/departments/dev/contracts/frozen-dev-package-contract/v1/schema.json"
    output_dir: "contracts/dev"
    freeze_on_create: true  # 创建后自动冻结

  frozen_ui_prototype:
    type: "contract"
    dept: "ui"
    schema: "spec-global/departments/ui/contracts/frozen-ui-prototype-contract/v1/schema.json"
    output_dir: "contracts/ui"

  api_contract:
    type: "contract"
    dept: "dev"
    schema: "spec-global/departments/dev/contracts/api-contract/v1/schema.json"
    output_dir: "contracts/dev"

  test_plan:
    type: "contract"
    dept: "qa"
    schema: "spec-global/departments/qa/contracts/test-plan/v1/schema.json"
    output_dir: "contracts/qa"

  # 文档类
  requirement_analysis:
    type: "document"
    dept: "prd"
    output_dir: "documents/analysis"

  design_doc:
    type: "document"
    dept: "dev"
    output_dir: "documents/design"

  review_report:
    type: "document"
    dept: "*"
    output_dir: "documents/review"

  # 代码引用
  source_code:
    type: "code_ref"
    storage: "reference"  # 不存内容，只存引用

  test_code_ref:
    type: "code_ref"
    storage: "reference"

  config_ref:
    type: "code_ref"
    storage: "reference"

  # 补丁和脚本
  code_patch:
    type: "patch"
    output_dir: "code/patches"
    content_type: "text/plain"

  build_script:
    type: "patch"
    output_dir: "scripts/build"
    content_type: "text/x-shellscript"

  deploy_script:
    type: "patch"
    output_dir: "scripts/deploy"
    content_type: "text/x-shellscript"

  # 测试类
  test_case:
    type: "test"
    dept: "qa"
    schema: "spec-global/departments/qa/contracts/test-case-contract/v1/schema.json"
    output_dir: "tests/cases"

  test_report:
    type: "test"
    dept: "qa"
    schema: "spec-global/departments/qa/contracts/e2e-report/v1/schema.json"
    output_dir: "tests/reports"

  coverage_report:
    type: "test"
    dept: "qa"
    output_dir: "tests/coverage"

  bug_report:
    type: "test"
    dept: "qa"
    schema: "spec-global/departments/qa/contracts/bug-contract/v1/schema.json"
    output_dir: "tests/bugs"

  # 交接
  dept_handover:
    type: "handover"
    output_dir: "handover"

  # 日志
  execution_log:
    type: "log"
    output_dir: "logs/execution"

# === 保留策略 ===
retention:
  drafts: 7              # 草稿保留7天
  active_runs: 30        # 活跃运行保留30天
  intermediate: 3        # 中间产物保留3天
  logs: 90               # 日志保留90天
  cache: 1               # 缓存保留1天
  frozen: -1             # 冻结文件永久保留
  handover: 90           # 交接文档保留90天

# === 自动归档规则 ===
# （使用结构化配置，避免 DSL）
auto_archive:
  enabled: true
  schedule: "0 2 * * *"  # 每天凌晨2点运行

  rules:
    - status: "active"
      max_age_days: 30
      action: "archive"

    - status: "draft"
      max_age_days: 7
      action: "delete"

    - status: "intermediate"
      max_age_days: 3
      action: "delete"

    - type: "handover"
      max_age_days: 90
      action: "archive"

# === 验证配置 ===
validation:
  enabled: true
  on_create: true        # 创建时验证
  on_freeze: true        # 冻结时验证
  strict: false          # 验证失败是否阻止
  auto_fix: false        # 是否尝试自动修复

# === ID 生成规则 ===
id_patterns:
  frozen_prd: "FDPRD-{YYYY}-{NNN}"
  frozen_dev_package: "FPKG-{YYYY}-{NNN}"
  frozen_ui_prototype: "FUIP-{YYYY}-{NNN}"
  api_contract: "API-{YYYY}-{NNN}"
  test_plan: "FTEST-{YYYY}-{NNN}"
  handover: "HANDOVER-{YYYYMMDD}-{NNN}"

# === 存储配置 ===
storage:
  default_backend: "local"
  local:
    base_path: ".artifacts"
  # 未来可扩展：
  # s3:
  #   bucket: "lee-artifacts"
  #   prefix: "artifacts/"
```

### 9.2 项目级配置覆盖

```yaml
# .artifacts/config.local.yaml （可选，项目级覆盖）

retention:
  active_runs: 60  # 本项目保留60天

categories:
  custom_contract:
    type: "contract"
    dept: "custom"
    output_dir: "contracts/custom"
```

---

## 10. 实施路线

### 10.1 Phase 1（第1周）：Run 级目录 + Manifest + Adopt

**目标**：建立基础结构，实现 run 级产出物管理

**任务**：

1. 创建目录结构
   - 创建 `.artifacts/` 及子目录
   - 创建 `config.yaml`

2. 实现数据模型
   - `ArtifactMetadata`
   - `RunManifest`
   - `ArtifactType`, `ArtifactStatus`
   - 从配置加载 `ArtifactCategory`

3. 实现简化版 Registry
   - 单个 `registry/index.json`
   - 基本注册/查找功能

4. 实现 `adopt()` 接口
   - 认领现有文件
   - 生成元数据
   - 更新索引

5. 实现 Manifest 管理
   - `create_run()`
   - `add_artifact()`
   - `save()` / `load()`

6. 基础 CLI
   - `lee artifacts list`
   - `lee artifacts show`
   - `lee artifacts adopt`

**验收标准**：
- 一条关键 L2 流程的所有产出物，都能从 `lee artifacts list --run RUN_ID` 找到
- 能用 `adopt` 命令认领现有文件

### 10.2 Phase 2（第2周）：Create + Freeze + Gate 集成

**目标**：实现产出物创建和冻结机制

**任务**：

1. 实现 `create()` 接口
   - 内容验证
   - 目录创建
   - ID 生成
   - Schema 验证

2. 实现 `freeze()` 接口
   - 验证产出物
   - 物理移动到 `frozen/`
   - 状态更新

3. 实现 `validate()` 接口
   - Schema 验证
   - 格式验证

4. 集成到 FileOutputHandler
   - 替换直接写文件为 `create()`
   - 自动更新 manifest

5. Gate 集成
   - Gate 按类别查找产出物
   - 验证产出物状态
   - 冻结通过 gate 的产出物

**验收标准**：
- 关键 step 使用 `create()` 创建产出物
- Gate 通过后自动冻结产出物
- 冻结的产出物物理在 `frozen/` 目录

### 10.3 Phase 3（第3周）：Handover + 交接

**目标**：实现部门间交接流程

**任务**：

1. 实现 `ArtifactType.HANDOVER`
   - `HandoverInfo` 模型
   - `create_handover()` 接口

2. Handover CLI
   - `lee artifacts handover list`
   - `lee artifacts handover show`
   - `lee artifacts handover acknowledge`

3. 交接流程集成
   - QA → Dev 交接
   - Dev → QA 交接
   - 自动填充输入

4. Manifest 集成
   - handovers 字段
   - 输入引用

**验收标准**：
- QA 完成 L2 后生成交接文档
- Dev 启动 L2 时通过 handover ID 获取所有输入
- 交接状态可追踪

### 10.4 Phase 4（第4周）：清理 + 工具完善

**目标**：实现自动清理和修复工具

**任务**：

1. 实现清理功能
   - `clean()` 接口
   - 按保留策略清理
   - `clean-intermediate` 命令

2. 实现修复工具
   - `rebuild-index` 命令
   - 磁盘扫描重建

3. 完善 CLI
   - 更好的输出格式
   - 表格视图
   - 详情视图

4. 自动归档
   - 定时任务
   - 归档规则执行

**验收标准**：
- 过期产出物自动清理
- 索引损坏可重建
- CLI 体验良好

### 10.5 Phase 5（第5周+）：演进功能（可选）

**目标**：增强功能，可作为 LEE 2.x 演进

**任务**：

1. 关系图可视化
   - 产出物依赖图
   - Run 流程图

2. 导入导出
   - 导出 run 包
   - 跨环境迁移

3. S3 后端
   - 云存储支持
   - 大文件处理

4. UI 集成
   - Web 查看界面
   - 可视化追溯

**说明**：这些功能对当前 LEE 稳定运行不是刚需，可作为长期演进路线。

---

## 附录

### A. 产出物 ID 命名规范

```
格式: {PREFIX}-{YYYY}-{NNN}

示例:
- FDPRD-2026-001    # Frozen PRD
- FPKG-2026-001     # Frozen Dev Package
- FUIP-2026-001     # Frozen UI Prototype
- API-2026-001      # API Contract
- FTEST-2026-001    # Frozen Test Plan
- HANDOVER-20260226-001  # Handover

运行时 ID:
- RUN-20260226-abc123def
```

### B. 目录迁移指南

从旧结构迁移到新结构：

```bash
# 1. 创建新目录
mkdir -p .artifacts/{active,frozen,archive,logs,registry}

# 2. 认领现有文件
lee artifacts adopt .workflow/outputs/**/*.yaml \
  --category frozen_dev_package \
  --run RUN-LEGACY-001

# 3. 冻结需要保留的产出物
lee artifacts freeze ARTIFACT_ID

# 4. 清理旧文件（确认无误后）
rm -rf .workflow/outputs/
```

### C. 故障排查

```bash
# 索引损坏，重建
lee artifacts rebuild-index

# 查找丢失的产出物
lee artifacts list --status all --include-archived

# 清理损坏的 manifest
rm .artifacts/active/RUN-XXX/manifest.yaml
lee artifacts rebuild-index
```

---

**文档变更历史**：

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-02-26 | 初版设计 |
| v2.0 | 2026-02-26 | 根据评审意见收缩，聚焦核心功能 |
