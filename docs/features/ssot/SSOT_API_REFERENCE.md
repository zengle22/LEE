# SSOT 真理链管理系统 - API 参考文档

## 1. 模块结构

```
src/lee/orchestrator/execution/artifacts/
├── __init__.py          # 公共导出
├── manager.py           # ArtifactManager - 产出物管理核心
├── registry.py          # ArtifactRegistry - 产出物注册表
├── manifest.py          # ManifestManager - Manifest 文件管理
├── models.py            # 数据模型 (ArtifactMetadata, RunManifest)
├── types.py             # 类型定义 (ArtifactType, ArtifactStatus, etc.)
├── context.py           # ContextBuilder - Context Bundle 构建器
├── task_brief.py        # TaskBriefGenerator - Task Brief 生成器
├── ssot_service.py      # SSOTService - SSOT 真理链服务
├── integration.py       # GateArtifactHandler - Gate 集成
└── cli/
    ├── ssot.py          # SSOT CLI 命令
    ├── context.py       # Context CLI 命令
    └── task_brief.py    # Task Brief CLI 命令
```

---

## 2. 核心类 API

### 2.1 ArtifactManager

产出物管理核心类，提供创建、adopt、freeze 等操作。

```python
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind

# 初始化
manager = ArtifactManager(root_path: Optional[Path] = None)

# 创建产出物
artifact = manager.create(
    artifact_type: ArtifactType,
    category: str,
    content: Union[str, bytes, Path],
    run_id: str,
    governance_kind: GovernanceKind,
    workflow_id: Optional[str] = None,
    department: Optional[str] = None,
    derived_from: Optional[str] = None,
    implements: Optional[List[str]] = None,
    verifies: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    title: str = "",
    description: str = "",
) -> ArtifactMetadata

# 冻结产出物
frozen = manager.freeze(artifact_id: str) -> ArtifactMetadata

# Adopt 现有产出物
adopted = manager.adopt(
    artifact_type: ArtifactType,
    category: str,
    path: Path,
    run_id: str,
    mode: AdoptMode = AdoptMode.COPY,
) -> ArtifactMetadata
```

### 2.2 ArtifactRegistry

产出物注册表，维护所有产出物的索引。

```python
from lee.orchestrator.execution.artifacts import ArtifactRegistry

# 初始化
registry = ArtifactRegistry(root_path: Optional[Path] = None)

# 重建注册表（从所有 manifest.yaml）
registry.rebuild() -> None

# 按 run_id 查询
artifacts = registry.get_by_run(run_id: str) -> List[ArtifactMetadata]

# 按类型查询
artifacts = registry.get_by_type(artifact_type: str) -> List[ArtifactMetadata]

# 按类别查询
artifacts = registry.get_by_category(category: str) -> List[ArtifactMetadata]

# 按状态查询
artifacts = registry.get_by_status(status: str) -> List[ArtifactMetadata]

# 按 ID 查询
artifact = registry.get_by_id(artifact_id: str) -> Optional[ArtifactMetadata]
```

### 2.3 ManifestManager

Manifest 文件管理器。

```python
from lee.orchestrator.execution.artifacts import ManifestManager

# 初始化
manifest_mgr = ManifestManager(
    root_path: Path,
    registry: ArtifactRegistry,
)

# 获取 manifest
manifest = manifest_mgr.get(
    run_id: str,
    department: Optional[str] = None,
) -> Optional[RunManifest]

# 保存 manifest
manifest_mgr.save(manifest: RunManifest) -> None

# 创建 manifest
manifest = manifest_mgr.create(
    run_id: str,
    department: Optional[str] = None,
) -> RunManifest
```

---

## 3. SSOT 服务 API

### 3.1 SSOTService

SSOT 真理链服务层。

```python
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService

# 初始化
service = SSOTService(artifact_manager: ArtifactManager)

# 校验真理链完整性
valid: bool
errors: List[str]
valid, errors = service.validate(
    run_id: Optional[str] = None,
    release: Optional[str] = None,
) -> Tuple[bool, List[str]]

# 影响范围分析
impact = service.impact(artifact_id: str) -> Dict[str, List[str]]
# 返回:
# {
#     "direct_dependents": [...],
#     "indirect_dependents": [...],
#     "verifiers": [...]
# }

# 真理链路径展示
chain = service.show_chain(artifact_id: str) -> List[Dict[str, Any]]
# 返回:
# [
#     {"id": "ART-001", "type": "CONTRACT", "category": "api_contract", "relation": ""},
#     {"id": "ART-002", "type": "CONTRACT", "category": "prd_contract", "relation": "derived_from"}
# ]
```

### 3.2 SSOT 校验规则

**v1.0 核心规则**:

| 规则 | 检查项 | 错误信息 |
|------|--------|----------|
| Rule 1 | `api_contract` 必须有 `derived_from` | `api_contract {id} missing derived_from` |
| Rule 2 | `implementation` 必须有 `implements` | `implementation {id} missing implements` |
| Rule 3 | `test_plan` 必须有 `verifies` | `test_plan {id} missing verifies` |
| Rule 4 | `derived_from` 必须指向存在的 artifact | `derived_from {id} points to non-existent artifact` |
| Rule 5 | `implements` 必须指向存在的 API | `implements {id} points to non-existent api_contract` |
| Rule 6 | `verifies` 必须指向存在的 PRD/API | `verifies {id} points to non-existent artifact` |

---

## 4. Context Builder API

### 4.1 ContextBuilder

Context Bundle 构建器。

```python
from lee.orchestrator.execution.artifacts.context import ContextBuilder

# 初始化
builder = ContextBuilder(artifact_manager: ArtifactManager)

# 记录 LLM 调用 (v1.0 完整版)
bundle = builder.record_llm_call_v1_0(
    run_id: str,
    step_id: str,
    prompt: PromptSnapshot,  # 或使用 prompt_text: str
    response: str,
    department: Optional[str] = None,
    artifacts: Optional[Dict[str, List[str]]] = None,
    config: Optional[LLMConfig] = None,
) -> TaskContextBundle

# 记录 LLM 调用 (v0.9 兼容版)
bundle = builder.record_llm_call_v0_9(
    run_id: str,
    step_id: str,
    prompt_text: str,
    response: str,
    department: Optional[str] = None,
    config: Optional[LLMConfig] = None,
) -> TaskContextBundle

# 保存 Bundle 为 artifact
artifact = builder.save_bundle(
    bundle: TaskContextBundle,
    workflow_id: Optional[str] = None,
) -> ArtifactMetadata

# 列出 Bundles
bundles = builder.list_bundles(
    run_id: Optional[str] = None,
    department: Optional[str] = None,
    order_by: str = "created_at",
) -> List[TaskContextBundle]

# 获取 Bundle
bundle = builder.get_bundle(bundle_id: str) -> Optional[TaskContextBundle]
```

### 4.2 数据模型

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional

@dataclass
class PromptSnapshot:
    """Prompt 快照"""
    system: str
    user: str
    history: List[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]: ...

@dataclass
class LLMConfig:
    """LLM 配置"""
    model: str = "claude-3-5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120

    def to_dict(self) -> Dict[str, Any]: ...

@dataclass
class TaskContextBundle:
    """任务上下文 Bundle"""
    id: str
    run_id: str
    step_id: str
    llm_call_id: str
    created_at: datetime
    artifacts: Optional[Dict[str, List[str]]] = None
    prompt_snapshot: Optional[PromptSnapshot] = None
    prompt_text: Optional[str] = None  # v0.9 兼容
    response: Optional[str] = None
    config: Optional[LLMConfig] = None

    def to_dict(self) -> Dict[str, Any]: ...
    def to_yaml(self) -> str: ...
```

---

## 5. Task Brief API

### 5.1 TaskBriefGenerator

Task Brief 生成器。

```python
from lee.orchestrator.execution.artifacts.task_brief import TaskBriefGenerator

# 初始化
generator = TaskBriefGenerator(artifact_manager: ArtifactManager)

# 手动创建 Task Brief
brief = generator.create_manual(
    run_id: str,
    department: str,
    title: str,
    description: str,
    task_type: str = "feature",  # feature, bugfix, incident, refactor
    related_ssot: Dict[str, str] = None,
    scope_include: List[str] = None,
    scope_exclude: List[str] = None,
    acceptance: List[str] = None,
    risks: List[str] = None,
) -> TaskBrief

# 从 PRD 创建
brief = generator.create_from_prd(
    run_id: str,
    department: str,
    prd_id: str,
    task_type: str = "feature",
) -> TaskBrief

# 从 Task Card 创建
brief = generator.create_from_task_card(
    run_id: str,
    department: str,
    task_card_id: str,
) -> TaskBrief

# 保存 Brief 为 artifact
artifact = generator.save_brief(
    brief: TaskBrief,
    workflow_id: Optional[str] = None,
) -> ArtifactMetadata

# 创建并保存（一步完成）
artifact, brief = generator.create_and_save(
    run_id: str,
    department: str,
    title: str,
    description: str,
    task_type: str = "feature",
    workflow_id: Optional[str] = None,
) -> Tuple[ArtifactMetadata, TaskBrief]
```

### 5.2 数据模型

```python
@dataclass
class TaskBrief:
    """任务简报"""
    id: str
    run_id: str
    department: str
    title: str
    description: str
    task_type: str  # feature, bugfix, incident, refactor
    related_ssot: Dict[str, str] = None
    scope: Dict[str, List[str]] = None
    acceptance: List[str] = None
    risks: List[str] = None
    body_markdown: str = ""
    created_at: datetime = None
    created_by: str = "user"
    status: str = "draft"  # draft, confirmed, completed

    def to_dict(self) -> Dict[str, Any]: ...
    def to_yaml(self) -> str: ...
```

---

## 6. Gate 集成 API

### 6.1 GateArtifactHandler

Gate 门禁处理器。

```python
from lee.orchestrator.execution.artifacts.integration import GateArtifactHandler

# 初始化
handler = GateArtifactHandler(project_root: Optional[Path] = None)

# 冻结 run 的所有 artifacts
frozen = handler.freeze_run_artifacts(
    run_id: str,
    department: Optional[str] = None,
) -> List[ArtifactMetadata]

# Gate 审批（含 SSOT 校验）
result = handler.approve_gate_artifacts(
    run_id: str,
    gate_id: str,
    department: Optional[str] = None,
    enforce: bool = True,  # True=强制模式，False=警告模式
) -> Dict[str, Any]
# 返回:
# {
#     "frozen_count": 5,
#     "frozen_artifacts": ["ART-001", "ART-002", ...],
#     "ssot_validated": True,
#     "ssot_errors": None  # or List[str] if failed
# }
```

---

## 7. CLI 命令 API

### 7.1 SSOT CLI

```python
from lee.cli.commands.ssot import ssot

# 校验
@click.command()
@click.option("--run-id", help="按 run ID 校验")
@click.option("--release", help="按 release tag 校验")
@click.option("--enforce", is_flag=True, help="强制模式")
def validate(run_id, release, enforce): ...

# 构建索引
@click.command()
@click.option("--output", "-o", help="输出文件路径")
@click.option("--release", help="仅构建指定 release")
def build_index(output, release): ...

# 影响分析
@click.command()
@click.argument("artifact_id")
@click.option("--format", type=click.Choice(["table", "json"]))
def impact(artifact_id, format): ...

# 真理链展示
@click.command()
@click.argument("artifact_id")
@click.option("--format", type=click.Choice(["table", "json"]))
def show_chain(artifact_id, format): ...
```

### 7.2 Context CLI

```python
from lee.cli.commands.context import context

# 列出 Bundles
@click.command()
@click.option("--run-id", help="按 run ID 过滤")
@click.option("--department", help="按部门过滤")
@click.option("--format", type=click.Choice(["table", "json", "yaml"]))
@click.option("--order-by", default="created_at")
def list_bundles(run_id, department, format, order_by): ...

# 查看 Bundle 详情
@click.command()
@click.argument("bundle_id")
@click.option("--format", type=click.Choice(["yaml", "json", "text"]))
def show(bundle_id, format): ...
```

### 7.3 Task Brief CLI

```python
from lee.cli.commands.task_brief import task_brief

# 列出 Briefs
@click.command()
@click.option("--run-id", help="按 run ID 过滤")
@click.option("--department", help="按部门过滤")
@click.option("--format", type=click.Choice(["table", "json", "yaml"]))
def list_briefs(run_id, department, format): ...

# 查看 Brief 详情
@click.command()
@click.argument("brief_id")
@click.option("--format", type=click.Choice(["yaml", "json", "text"]))
def show(brief_id, format): ...

# 创建 Brief
@click.command()
@click.option("--run-id", required=True)
@click.option("--department", required=True)
@click.option("--title", required=True)
@click.option("--description", required=True)
@click.option("--task-type", default="feature")
@click.option("--scope-include", multiple=True)
@click.option("--scope-exclude", multiple=True)
@click.option("--acceptance", multiple=True)
@click.option("--risks", multiple=True)
def create(run_id, department, title, description, task_type,
           scope_include, scope_exclude, acceptance, risks): ...
```

---

## 8. 类型定义

### 8.1 ArtifactType

```python
class ArtifactType(str, Enum):
    CONTRACT = "CONTRACT"      # 契约类
    DOCUMENT = "DOCUMENT"      # 文档类
    CODE_REF = "CODE_REF"      # 代码引用
    PATCH = "PATCH"            # 补丁类
    TEST = "TEST"              # 测试类
    HANDOVER = "HANDOVER"      # 移交类
    LOG = "LOG"                # 日志类
    INTERMEDIATE = "INTERMEDIATE"  # 中间产物
```

### 8.2 ArtifactStatus

```python
class ArtifactStatus(str, Enum):
    ACTIVE = "ACTIVE"      # 活跃
    FROZEN = "FROZEN"      # 已冻结
    ARCHIVED = "ARCHIVED"  # 已归档
```

### 8.3 GovernanceKind

```python
class GovernanceKind(str, Enum):
    TRANSFER = "transfer"      # 部门间移交
    DELIVERABLE = "deliverable"  # 交付物
    EVIDENCE = "evidence"      # 证据
```

---

## 9. 参考文档

- [SSOT 用户指南](SSOT_USER_GUIDE.md)
- [SSOT 最佳实践](SSOT_BEST_PRACTICES.md)
- [产出物管理系统架构](../../architecture/artifact-management-system.md)
