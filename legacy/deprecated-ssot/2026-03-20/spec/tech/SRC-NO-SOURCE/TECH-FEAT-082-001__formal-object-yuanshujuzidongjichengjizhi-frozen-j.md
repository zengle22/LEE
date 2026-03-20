---
id: TECH-FEAT-082-001
ssot_type: tech
title: Formal Object 元数据自动继承机制 - Frozen 技术架构
status: frozen
version: v1
parent_id: FEAT-082
derived_from_ids:
- id: ADR-001
  version: v1
- id: ADR-003
  version: v1
- id: ADR-008
  version: v1
source_refs:
- FEAT-082#processing
- FEAT-082#acceptance
owner: dev
tags:
- tech
- metadata
- workflow
- inheritance
- ssot
- frozen
properties:
  tech_kind: frozen_architecture
  target_scope: workflow_runtime
  frozen_at: '2026-03-13T00:00:00'
workflow_instance_id: wf-tech-feat-082-001__formal-object-yuanshujuzidongjichengjizhi-frozen-j-20260316
  governing_adrs:
  - ADR-001
  - ADR-003
  - ADR-008
  decision_constraints:
  - 元数据继承以 FEAT 冻结文档为唯一真源
  - 不修改现有 SSOT Schema，仅扩展运行时注入能力
  - 单 Workspace 内元数据继承，不支持跨 Workspace 引用
  - 与现有 Workflow 模板保持向后兼容
  architecture_constraints:
  - MetadataInheritanceEngine 作为独立模块部署
  - FormalObjectRegistry 从 spec/目录扫描 SSOT 文件
  - WorkflowContextEnhancer 在 Agent Step 执行前注入元数据
---

# Formal Object 元数据自动继承机制 - Frozen 技术架构

## 架构冻结声明

本技术架构设计已经人类核准并冻结，版本 **v1**，冻结日期 **2026-03-13**。

后续实现必须严格遵守本架构定义，任何变更必须通过新版本 supersede 本版本。

**核准人**: [待填写]
**冻结日期**: 2026-03-13
**架构版本**: v1

---

## 1. 架构概述

### 1.1 设计目标

本技术方案旨在实现 Workflow 执行过程中 Formal Object（ADR/EPIC/FEAT）的元数据自动继承与绑定机制，确保：

- `source_refs` 自动追溯至原始需求源（SRC）
- `parent_id` 自动维护层级关系（FEAT→EPIC→ADR）
- `derived_from_ids` 自动构建派生链
- 所有元数据在 Workflow Runtime 中自动注入，无需人工干预

### 1.2 架构原则

| 原则 | 说明 | 合规验证 |
|------|------|----------|
| **Single Source of Truth** | 元数据继承逻辑以 FEAT 冻结文档为唯一真源 | 通过 `FormalObjectRegistry` 从 `spec/` 扫描 |
| **Non-Invasive** | 不修改现有 SSOT Schema，仅扩展运行时注入能力 | 通过 `WorkflowContextEnhancer` 实现 |
| **Transparent** | 继承逻辑对 Agent 透明，Agent 按常规方式消费元数据 | 元数据注入 `AgentContext` |
| **Traceable** | 所有自动注入操作生成审计日志，支持溯源 | `InheritanceContext` 包含审计信息 |
| **Fallback Ready** | 提供手动覆盖机制，应对边界场景 | 特性开关支持紧急关闭 |

### 1.3 架构边界

**In Scope**:
- FEAT/EPIC/SRC 元数据解析与索引
- 继承上下文构建与注入
- Workflow Runtime 元数据增强
- 循环依赖检测与防护

**Out of Scope**:
- 跨 Workspace 引用解析（由 ADR-001 明确排除）
- UI 层元数据展示（由 UI-FEAT-082-001 覆盖）
- 手动元数据编辑功能

---

## 2. 技术实现方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Workflow Runtime Layer                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐     │
│  │  Workflow L2    │───▶│  Metadata       │───▶│  Agent/Skill        │     │
│  │  Orchestrator   │    │  Injector       │    │  Execution          │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘     │
│           │                      │                       ▲                  │
│           │                      ▼                       │                  │
│           │           ┌─────────────────┐               │                  │
│           │           │  Formal Object  │───────────────┘                  │
│           │           │  Registry       │                                  │
│           │           └─────────────────┘                                  │
│           │                      ▲                                        │
│           ▼                      │                                        │
│  ┌─────────────────┐    ┌─────────────────┐                               │
│  │  FEAT Document  │◀───│  SSOT Resolver  │                               │
│  │  (Frozen)       │    │  (spec/)        │                               │
│  └─────────────────┘    └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SSOT Storage Layer                                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │   SRC   │──▶│  EPIC   │──▶│  FEAT   │──▶│  TECH   │──▶│  IMPL   │       │
│  │         │   │         │   │(frozen) │   │         │   │         │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘       │
│       │                           │                                       │
│       └───────────────────────────┘                                       │
│              source_refs (auto)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块设计

#### 2.2.1 MetadataInheritanceEngine（元数据继承引擎）

**部署位置**: `src/lee/orchestrator/metadata_inheritance/engine.py`

**职责**:
- 解析 Workflow 输入中的 `feat_ref`
- 从 FEAT 文档提取元数据关系链
- 构建完整的继承上下文
- 注入到 Agent 执行上下文

**核心接口**:

```python
class MetadataInheritanceEngine:
    """
    元数据自动继承引擎

    负责在 Workflow 运行时自动解析和维护 Formal Object 的元数据关系。
    """

    def __init__(
        self,
        registry: FormalObjectRegistry,
        cache: Optional[MetadataCache] = None,
    ):
        self._registry = registry
        self._cache = cache

    async def resolve_inheritance_context(
        self,
        feat_ref: str,
        workflow_context: WorkflowContext
    ) -> InheritanceContext:
        """
        解析继承上下文

        Args:
            feat_ref: FEAT 对象引用 (e.g., "FEAT-082@v1")
            workflow_context: 当前 Workflow 执行上下文

        Returns:
            InheritanceContext: 包含完整继承链的上下文对象
        """

    async def inject_metadata(
        self,
        agent_context: AgentContext,
        inheritance_context: InheritanceContext
    ) -> AgentContext:
        """
        将继承的元数据注入 Agent 上下文

        Args:
            agent_context: 原始 Agent 上下文
            inheritance_context: 继承上下文

        Returns:
            注入后的 Agent 上下文
        """
```

**数据结构**:

```python
@dataclass
class InheritanceContext:
    """继承上下文 - 包含完整的元数据继承链"""

    # 当前对象信息
    current_feat: FeatMetadata

    # 自动继承的元数据
    source_refs: List[str]              # 追溯至 SRC
    parent_id: Optional[str]            # EPIC ID
    derived_from_ids: List[Dict]        # 派生链 [{id, version}]

    # 完整追溯链
    trace_chain: TraceChain

    # 审计信息
    resolved_at: datetime
    resolver_version: str
    inheritance_log: List[InheritanceLogEntry]


@dataclass
class TraceChain:
    """追溯链 - 从 SRC 到当前 FEAT 的完整路径"""
    src: Optional[SrcMetadata]
    epic: Optional[EpicMetadata]
    feat: FeatMetadata
    governing_adrs: List[str]
```

#### 2.2.2 FormalObjectRegistry（正式对象注册表）

**部署位置**: `src/lee/orchestrator/metadata_inheritance/registry.py`

**职责**:
- 管理 FEAT/EPIC/ADR 对象的元数据索引
- 提供高效的元数据查询接口
- 维护对象间关系图

**索引策略**:

```yaml
# 索引结构（内存缓存）
formal_object_index:
  feat:
    FEAT-082:
      v1:
        path: "spec/requirements/features/FEAT-082__formal-object-yuanshujuzidongjichengjizhi.md"
        parent_id: "EPIC-003"
        source_refs: ["EPIC-003#scope"]
        derived_from_ids: []
        frozen_at: "2026-03-11T15:17:41"

  epic:
    EPIC-003:
      v1:
        path: "spec/requirements/epics/EPIC-003__xxx.md"
        parent_id: null
        source_refs: ["SRC-001"]
        frozen_at: "2026-03-10T10:00:00"

  src:
    SRC-001:
      v1:
        path: "spec/source/SRC-001__xxx.md"
        frozen_at: "2026-03-09T09:00:00"

  adr:
    ADR-001:
      v1:
        path: "spec/adr/ADR-001__ssot-delivery-chain-hard-governance.md"
        frozen_at: "2026-03-08T00:00:00"
```

**核心方法**:

```python
class FormalObjectRegistry:
    """正式对象注册表 - 元数据索引缓存"""

    def __init__(self, project_root: Path):
        self._project_root = project_root
        self._index: Dict[str, Dict[str, Any]] = {}
        self._cache_valid_until: Optional[datetime] = None

    async def get_feat_metadata(self, feat_id: str, version: str = "v1") -> FeatMetadata:
        """获取 FEAT 元数据（带缓存）"""

    async def get_epic_metadata(self, epic_id: str) -> Optional[EpicMetadata]:
        """获取 EPIC 元数据"""

    async def get_src_metadata(self, src_id: str) -> Optional[SrcMetadata]:
        """获取 SRC 元数据"""

    async def get_governing_adrs(self, feat_id: str) -> List[str]:
        """获取治理当前 FEAT 的 ADR 列表"""

    async def rebuild_index(self) -> int:
        """从 spec/ 目录重建索引"""
```

#### 2.2.3 WorkflowContextEnhancer（工作流上下文增强器）

**部署位置**: `src/lee/orchestrator/metadata_inheritance/enhancer.py`

**职责**:
- 在 Workflow 启动时自动加载元数据继承上下文
- 在每个 Step 执行前注入相关元数据
- 支持条件注入（按需加载）

**注入点设计**:

```python
class WorkflowContextEnhancer:
    """
    Workflow 上下文增强器

    在 Workflow 执行的关键节点自动注入继承元数据。
    """

    INJECTION_POINTS = {
        "workflow_start": "Workflow 启动时",
        "before_agent_step": "Agent Step 执行前",
        "before_gate": "Gate 执行前",
        "on_handover": "Handover 发生时",
    }

    async def enhance_for_agent_step(
        self,
        step: AgentStep,
        workflow_state: WorkflowState
    ) -> EnhancedContext:
        """
        为 Agent Step 增强上下文

        自动注入:
        1. source_refs - 来自 FEAT 的 source_refs
        2. parent_id - 来自 FEAT 的 parent_id
        3. derived_from_ids - 来自 FEAT 的 derived_from_ids
        4. governing_adrs - 来自追溯链的 ADR
        5. acceptance_criteria - FEAT 的验收标准
        """
```

**注入内容**:

```python
@dataclass
class EnhancedContext:
    """增强后的上下文"""

    # 基础上下文（原有）
    step: AgentStep
    workflow: WorkflowState

    # 新增：继承的元数据
    inherited_metadata: Optional[InheritanceContext]

    @property
    def source_refs(self) -> List[str]:
        return self.inherited_metadata.source_refs if self.inherited_metadata else []

    @property
    def parent_id(self) -> Optional[str]:
        return self.inherited_metadata.parent_id if self.inherited_metadata else None

    @property
    def derived_from_ids(self) -> List[Dict]:
        return self.inherited_metadata.derived_from_ids if self.inherited_metadata else []

    @property
    def governing_adrs(self) -> List[str]:
        return self.inherited_metadata.trace_chain.governing_adrs if self.inherited_metadata else []
```

### 2.3 继承规则引擎

#### 2.3.1 元数据继承规则

```yaml
inheritance_rules:
  # 规则 1: source_refs 自动传递
  source_refs_propagation:
    description: "子对象自动继承父对象的 source_refs"
    from: ["EPIC", "SRC"]
    to: ["FEAT", "TECH", "UI", "TASK"]
    strategy: "merge_unique"
    override: "allowed_with_trace"

  # 规则 2: parent_id 自动绑定
  parent_id_binding:
    description: "创建 FEAT 时自动绑定到对应 EPIC"
    from: "EPIC"
    to: "FEAT"
    strategy: "explicit_reference"
    field: "parent_id"

  # 规则 3: derived_from_ids 链式维护
  derived_chain_maintenance:
    description: "维护派生链，新对象指向派生源"
    pattern: "SRC -> EPIC -> FEAT -> TECH"
    strategy: "append_only"

  # 规则 4: governing_adrs 自动收集
  adr_auto_collection:
    description: "自动收集影响当前对象的所有 ADR"
    scope: "从 SRC 到当前对象的完整链路"
    strategy: "cumulative_merge"
```

#### 2.3.2 规则优先级

```
优先级 (高 -> 低):
1. 显式覆盖 (Explicit Override) - 用户手动指定
2. 冻结文档 (Frozen Document) - FEAT 文档中的值
3. 自动继承 (Auto Inheritance) - 从父对象继承
4. 默认值 (Default) - 系统默认值
```

---

## 3. 核心依赖项

### 3.1 内部依赖（项目内模块）

| 依赖模块 | 路径 | 用途 | 版本约束 |
|----------|------|------|----------|
| Artifact Manager | `src/lee/orchestrator/execution/artifacts/manager.py` | SSOT 对象物化 | v1.3+ |
| SSOT Types | `src/lee/orchestrator/execution/artifacts/types.py` | 类型定义 | v1.3+ |
| Artifact Registry | `src/lee/orchestrator/execution/artifacts/registry.py` | SSOT 索引缓存 | v2.1+ |
| Workflow Executor | `src/lee/orchestrator/execution/state_machine_executor.py` | Workflow 执行 | v3.5+ |
| Step Runners | `src/lee/orchestrator/execution/step_runners.py` | Step 分发 | v3.5+ |
| Agent Context | `src/lee/orchestrator/execution/agent_context.py` | Agent 上下文 | v2.0+ |
| SSOT Contract | `src/lee/orchestrator/execution/artifacts/ssot_contract.py` | SSOT 输出契约 | v1.3+ |

### 3.2 Schema 依赖

| Schema | 路径 | 用途 |
|--------|------|------|
| SSOT Agent Output | `spec-global/core/contracts/ssot-agent-output/v1/schema.json` | 输出契约 |
| FEAT Schema | `spec/contracts/frozen-requirement-contract/v1/schema.json` | FEAT 文档结构 |
| SSOT Type Definitions | `src/lee/orchestrator/execution/artifacts/types.py::SSOTType` | 对象类型枚举 |

### 3.3 外部依赖（Python 库）

| 依赖 | 用途 | 版本约束 | 备份方案 |
|------|------|----------|----------|
| PyYAML | FEAT 文档 YAML Frontmatter 解析 | >=6.0 | 内置 json 模块降级 |
| pydantic | 数据验证 | >=2.0 | dataclasses + 手动验证 |
| frontmatter | Markdown Frontmatter 解析 | >=1.0 | 正则表达式降级 |

### 3.4 治理依赖（ADR）

| ADR | 标题 | 约束内容 |
|-----|------|----------|
| ADR-001 | SSOT delivery chain hard governance | 三轴模型、状态机、ID 规则 |
| ADR-003 | Product Department SSOT Design | FEAT 治理规则、Delivery Prep 规范 |
| ADR-008 | Dev department SSOT alignment | TECH 对象职责、证据轴收口 |

---

## 4. 技术不确定性及备份方案

### 4.1 风险矩阵

| 风险项 | 可能性 | 影响 | 风险等级 | 缓解措施 |
|--------|--------|------|----------|----------|
| FEAT 文档解析性能瓶颈 | 中 | 高 | 🔴 高 | 索引缓存 + 懒加载 |
| 循环依赖检测遗漏 | 低 | 高 | 🟡 中 | Floyd 环检测算法 |
| 元数据注入与现有逻辑冲突 | 中 | 中 | 🟡 中 | 特性开关 + 灰度发布 |
| 跨 Workspace 引用处理 | 高 | 中 | 🟡 中 | 明确排除 + 日志告警 |
| 并发 Workflow 元数据一致性 | 低 | 高 | 🟡 中 | 乐观锁 + 版本校验 |

### 4.2 备份方案详情

#### 风险 1: FEAT 文档解析性能瓶颈

**场景**: 大量 FEAT 文档需要解析时，YAML Frontmatter 解析可能成为瓶颈

**备份方案 A - 索引缓存（首选）**:

```python
class CachedFormalObjectRegistry:
    """带缓存的 Formal Object 注册表"""

    def __init__(self, project_root: Path, cache_ttl: int = 300):
        self._index_cache: Dict[str, Any] = {}
        self._cache_ttl: int = cache_ttl  # 5 分钟
        self._cache_timestamp: Dict[str, datetime] = {}

    async def get_feat_metadata(self, feat_id: str) -> FeatMetadata:
        # 先查缓存
        if self._is_cache_valid(feat_id):
            return self._index_cache[feat_id]

        # 缓存未命中，解析文档
        metadata = await self._parse_feat_document(feat_id)
        self._index_cache[feat_id] = metadata
        self._cache_timestamp[feat_id] = datetime.now()
        return metadata

    def _is_cache_valid(self, feat_id: str) -> bool:
        if feat_id not in self._index_cache:
            return False
        cached_at = self._cache_timestamp.get(feat_id)
        if not cached_at:
            return False
        return (datetime.now() - cached_at).total_seconds() < self._cache_ttl
```

**备份方案 B - 预构建索引（备用）**:

```python
class PrebuiltIndexRegistry:
    """预构建索引的注册表"""

    async def rebuild_index_async(self):
        """后台任务定期重建索引"""
        for feat_file in self._scan_feat_files():
            metadata = await self._parse_feat_document(feat_file)
            await self._write_to_index_db(metadata)
```

#### 风险 2: 循环依赖检测遗漏

**场景**: 错误的 FEAT 配置可能导致 parent_id 循环引用

**备份方案**:

```python
class CycleDetector:
    """循环依赖检测器"""

    MAX_TRACE_DEPTH = 100

    def detect_cycle(
        self,
        start_id: str,
        get_parent_fn: Callable[[str], Optional[str]]
    ) -> Optional[List[str]]:
        """
        使用路径追踪算法检测循环

        Returns:
            如果存在循环，返回循环路径；否则返回 None
        """
        visited = set()
        path = []
        current = start_id

        while current:
            if current in visited:
                cycle_start = path.index(current)
                return path[cycle_start:] + [current]

            visited.add(current)
            path.append(current)
            current = get_parent_fn(current)

            # 安全限制：最大追溯深度
            if len(path) > self.MAX_TRACE_DEPTH:
                raise InheritanceDepthExceeded(
                    f"Trace depth exceeded {self.MAX_TRACE_DEPTH} for {start_id}"
                )

        return None
```

#### 风险 3: 元数据注入与现有逻辑冲突

**场景**: 自动注入的元数据可能与 Workflow/Agent 现有逻辑冲突

**备份方案 - 特性开关**:

```yaml
# config/metadata_inheritance.yaml
metadata_inheritance:
  enabled: true

  # 灰度控制
  rollout:
    mode: "gradual"  # gradual | full | disabled
    target_workflows:
      - "template.dev.feature_delivery_l2"
    excluded_steps:
      - "legacy_step_id"

  # 冲突处理
  conflict_resolution:
    strategy: "auto_override"  # auto_override | preserve_existing | fail
    log_conflicts: true

  # 紧急开关
  emergency_kill_switch: false
```

**代码实现**:

```python
class MetadataInheritanceConfig:
    """配置管理"""

    def __init__(self, config_path: str):
        self._config = self._load_config(config_path)

    @property
    def enabled(self) -> bool:
        return self._config.get("enabled", False)

    @property
    def emergency_kill_switch(self) -> bool:
        return self._config.get("emergency_kill_switch", False)

    def should_inject(self, workflow_id: str, step_id: str) -> bool:
        if self.emergency_kill_switch:
            return False
        if not self.enabled:
            return False
        # 检查灰度配置
        return self._check_rollout(workflow_id, step_id)
```

#### 风险 4: 跨 Workspace 引用处理

**场景**: FEAT-082 明确排除跨 Workspace 引用，但未来可能扩展

**备份方案**:

```python
class CrossWorkspaceResolver:
    """跨 Workspace 引用解析器（预留接口）"""

    def resolve_external_ref(self, ref: str) -> Optional[Metadata]:
        """
        解析外部 Workspace 引用

        当前实现：返回 None（符合需求约束）
        未来扩展：通过注册中心解析
        """
        if self._is_external_ref(ref):
            # 当前：记录并跳过
            logger.warning(f"Cross-workspace ref ignored (not supported): {ref}")
            return None

            # 未来：通过 SSOT Registry 解析
            # return self._registry_client.resolve(ref)

        return self._resolve_local_ref(ref)

    def _is_external_ref(self, ref: str) -> bool:
        """判断是否为外部引用（未来扩展点）"""
        # 当前实现：所有引用都是本地的
        return False
```

#### 风险 5: 并发 Workflow 元数据一致性

**场景**: 多个 Workflow 并发执行时，元数据索引可能不一致

**备份方案**:

```python
class ConcurrentSafeRegistry:
    """并发安全的注册表"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._version_counter = 0

    async def get_metadata_with_version(
        self,
        feat_id: str,
        expected_version: Optional[int] = None
    ) -> Tuple[Metadata, int]:
        """
        获取带版本号的元数据

        用于乐观并发控制
        """
        async with self._lock:
            metadata = await self._get_metadata(feat_id)
            version = self._version_counter

            if expected_version and version != expected_version:
                raise MetadataVersionMismatch(
                    f"Expected version {expected_version}, got {version}"
                )

            return metadata, version

    async def increment_version(self):
        """递增版本号"""
        async with self._lock:
            self._version_counter += 1
            return self._version_counter
```

---

## 5. 接口契约

### 5.1 输入契约

```yaml
metadata_inheritance_input:
  required:
    - feat_ref

  properties:
    feat_ref:
      type: string
      description: "FEAT 对象引用，格式：FEAT-{id}[@v{version}]"
      example: "FEAT-082@v1"
      pattern: "^FEAT-[A-Z0-9]+(@v[0-9]+)?$"

    workflow_id:
      type: string
      description: "当前 Workflow ID"

    execution_context:
      type: object
      description: "执行上下文（可选）"
      properties:
        agent_type:
          type: string
          enum: ["llm", "skill", "claude_code"]
        step_id:
          type: string
```

### 5.2 输出契约

```yaml
metadata_inheritance_output:
  required:
    - source_refs
    - parent_id
    - derived_from_ids

  properties:
    source_refs:
      type: array
      items:
        type: string
      description: "自动继承的 source_refs"

    parent_id:
      type: string
      nullable: true
      description: "自动绑定的 parent_id"

    derived_from_ids:
      type: array
      items:
        type: object
        required: [id, version]
        properties:
          id: { type: string }
          version: { type: string }
          required: { type: boolean }
          slice_key: { type: string }
      description: "自动维护的派生链"

    trace_chain:
      type: object
      description: "完整追溯链信息"
      properties:
        src: { type: object, nullable: true }
        epic: { type: object, nullable: true }
        feat: { type: object }
        governing_adrs: { type: array, items: { type: string } }

    inheritance_log:
      type: array
      description: "继承操作审计日志"
      items:
        type: object
        properties:
          action: { type: string }
          source: { type: string }
          timestamp: { type: string }
```

---

## 6. 验收验证方案

### 6.1 技术验收标准

| 验收项 | 验证方法 | 通过标准 | 对应 AC |
|--------|----------|----------|---------|
| source_refs 自动绑定 | 单元测试 + 集成测试 | 从 EPIC 正确继承 source_refs | AC-FEAT-082-001 |
| parent_id 自动维护 | 单元测试 + 集成测试 | FEAT 的 parent_id 正确指向 EPIC | AC-FEAT-082-002 |
| derived_from_ids 链式维护 | 集成测试 | 派生链完整可追溯 | AC-FEAT-082-003 |
| 追溯信息展示 | E2E 测试 | 查询接口返回完整追溯链 | AC-FEAT-082-004 |
| 性能 < 100ms | 压力测试 | 99th percentile < 100ms | - |
| 并发安全 | 并发测试 | 无数据竞争、无死锁 | - |
| 循环依赖检测 | 单元测试 | 正确检测并拒绝循环引用 | - |

### 6.2 测试策略

```yaml
test_strategy:
  unit_tests:
    files:
      - "src/lee/orchestrator/metadata_inheritance/tests/test_engine.py"
      - "src/lee/orchestrator/metadata_inheritance/tests/test_registry.py"
      - "src/lee/orchestrator/metadata_inheritance/tests/test_cycle_detector.py"
    coverage_target: 80%

    test_cases:
      - "MetadataInheritanceEngine.resolve_inheritance_context"
      - "MetadataInheritanceEngine.inject_metadata"
      - "FormalObjectRegistry.get_feat_metadata"
      - "CycleDetector.detect_cycle"
      - "WorkflowContextEnhancer.enhance_for_agent_step"

  integration_tests:
    files:
      - "src/lee/orchestrator/metadata_inheritance/tests/test_integration.py"
    test_cases:
      - "Workflow 启动时元数据注入"
      - "Agent Step 元数据传递"
      - "Handover 元数据继承"
      - "多 FEAT 并发解析"

  e2e_tests:
    files:
      - "tests/e2e/test_metadata_inheritance.py"
    test_cases:
      - "完整 FEAT→TECH 元数据链路"
      - "对象详情查询展示"
      - "追溯链可视化验证"
```

---

## 7. 部署与配置

### 7.1 模块目录结构

```
src/lee/orchestrator/metadata_inheritance/
├── __init__.py
├── engine.py              # MetadataInheritanceEngine
├── registry.py            # FormalObjectRegistry
├── enhancer.py            # WorkflowContextEnhancer
├── resolver.py            # SSOTResolver
├── cycle_detector.py      # CycleDetector
├── models.py              # 数据模型
├── exceptions.py          # 异常定义
├── config.py              # 配置管理
├── __version__.py         # 版本信息
└── tests/
    ├── __init__.py
    ├── test_engine.py
    ├── test_registry.py
    ├── test_enhancer.py
    ├── test_cycle_detector.py
    └── test_integration.py
```

### 7.2 配置示例

```yaml
# config/metadata_inheritance.yaml
metadata_inheritance:
  enabled: true

  # 缓存配置
  cache:
    enabled: true
    ttl_seconds: 300
    max_entries: 1000
    preload_on_startup: false

  # 索引配置
  indexing:
    mode: "lazy"  # lazy | eager
    rebuild_interval_seconds: 3600
    scan_directories:
      - "spec/source"
      - "spec/requirements/epics"
      - "spec/requirements/features"
      - "spec/adr"

  # 限制配置
  limits:
    max_trace_depth: 100
    max_source_refs: 50
    max_derived_chain_length: 10
    max_governing_adrs: 20

  # 冲突处理
  conflict_resolution:
    strategy: "auto_override"  # auto_override | preserve_existing | fail
    log_level: "warning"
    log_conflicts: true

  # 灰度发布
  rollout:
    mode: "gradual"
    target_workflows:
      - "template.dev.feature_delivery_l2"
    excluded_steps: []

  # 紧急开关
  emergency_kill_switch: false
```

### 7.3 与现有系统集成

#### 与 Workflow Orchestrator 集成

```python
# src/lee/orchestrator/core/workflow_executor.py

from ..metadata_inheritance import MetadataInheritanceEngine, FormalObjectRegistry

class WorkflowExecutor:
    def __init__(self, ...):
        # ... 现有初始化 ...

        # 新增：元数据继承引擎
        self.metadata_engine = MetadataInheritanceEngine(
            registry=FormalObjectRegistry(project_root=self.project_root),
            cache=MetadataCache() if config.cache_enabled else None,
        )

    async def start_workflow(self, workflow_def, input_data):
        # 解析 feat_ref
        feat_ref = input_data.get("feat_ref")

        # 解析继承上下文
        if feat_ref and self.metadata_engine.config.enabled:
            inheritance_ctx = await self.metadata_engine.resolve_inheritance_context(
                feat_ref=feat_ref,
                workflow_context=self.context
            )
            self.context.inheritance = inheritance_ctx

        # ... 继续执行 ...
```

#### 与 Agent Context 集成

```python
# src/lee/orchestrator/execution/agent_context.py

from ..metadata_inheritance import InheritanceContext

class AgentContext:
    def __init__(
        self,
        step: AgentStep,
        workflow: WorkflowState,
        inheritance: Optional[InheritanceContext] = None,
    ):
        self.step = step
        self.workflow = workflow
        self.inheritance = inheritance

    @property
    def source_refs(self) -> List[str]:
        """获取继承的 source_refs"""
        return self.inheritance.source_refs if self.inheritance else []

    @property
    def parent_id(self) -> Optional[str]:
        """获取继承的 parent_id"""
        return self.inheritance.parent_id if self.inheritance else None

    @property
    def derived_from_ids(self) -> List[Dict]:
        """获取继承的 derived_from_ids"""
        return self.inheritance.derived_from_ids if self.inheritance else []

    @property
    def governing_adrs(self) -> List[str]:
        """获取治理 ADR 列表"""
        return self.inheritance.trace_chain.governing_adrs if self.inheritance else []
```

---

## 8. 治理约束合规性

### 8.1 ADR-001 合规性

| ADR-001 约束 | 本架构实现 | 验证方式 |
|-------------|-----------|----------|
| 需求轴/交付轴/证据轴三轴模型 | 元数据继承从需求轴流向交付轴 | `InheritanceContext.trace_chain` |
| `derived_from_ids` 结构化 | 使用`[{id, version}]`格式 | Schema 验证 |
| 状态机约束 | 冻结 FEAT 不可修改 | `FormalObjectRegistry` 只读 |
| Registry 作为缓存 | 索引从 spec/文件投影 | `rebuild_index()` 方法 |

### 8.2 ADR-003 合规性

| ADR-003 约束 | 本架构实现 | 验证方式 |
|-------------|-----------|----------|
| FEAT 是最小可独立验收单元 | 元数据继承以 FEAT 为锚点 | `feat_ref` 输入 |
| `parent_id` 层级关系 | FEAT→EPIC 自动绑定 | `InheritanceContext.parent_id` |
| `source_refs` 追溯 | 从 EPIC/SRC 自动继承 | `InheritanceContext.source_refs` |
| ADR 作为治理约束 | `governing_adrs` 自动收集 | `TraceChain.governing_adrs` |

### 8.3 ADR-008 合规性

| ADR-008 约束 | 本架构实现 | 验证方式 |
|-------------|-----------|----------|
| TECH 是 Dev 交付翻译层 | TECH 从 FEAT 派生元数据 | `derived_from_ids` |
| 正式 SSOT 引用 | 元数据来自冻结 FEAT 文档 | `FormalObjectRegistry` |
| `governing_adrs` 注入 | 执行上下文显式传入 | `AgentContext.governing_adrs` |

---

## 9. 冻结附录

### 9.1 关键决策记录

| 决策项 | 决策内容 | 理由 |
|--------|----------|------|
| 索引策略 | 内存缓存 + 懒加载 | 平衡性能与实现复杂度 |
| 继承注入点 | Workflow 启动 + Agent Step 前 | 确保所有执行点都能获得元数据 |
| 循环检测算法 | 路径追踪 + 深度限制 | 简单可靠，避免栈溢出 |
| 跨 Workspace | 当前版本明确排除 | 符合 FEAT-082 范围约束 |
| 并发控制 | 乐观锁 + 版本校验 | 避免过度工程化 |

### 9.2 技术债务

| 债务项 | 描述 | 优先级 | 预计偿还时间 |
|--------|------|--------|-------------|
| 索引持久化 | 当前使用内存缓存，重启后重建 | P2 | v2.0 |
| 增量索引更新 | 当前全量重建，支持文件监听增量更新 | P2 | v2.0 |
| 跨 Workspace 扩展 | 预留接口但未实现 | P3 | TBD |
| 图数据库索引 | 当前使用内存字典，可迁移到 Neo4j | P3 | TBD |

### 9.3 未来扩展点

```python
# 预留接口：跨 Workspace 引用
class CrossWorkspaceResolver:
    def resolve_external_ref(self, ref: str) -> Optional[Metadata]:
        # TODO: 实现 SSOT Registry 远程解析
        pass

# 预留接口：增量索引更新
class IncrementalIndexUpdater:
    async def watch_and_update(self):
        # TODO: 使用 watchdog 监听文件变化
        pass

# 预留接口：图数据库索引
class GraphDatabaseRegistry:
    async def store_relationships(self, trace_chain: TraceChain):
        # TODO: 使用 Neo4j 存储关系图
        pass
```

---

## 10. 签署

**架构师**: [待填写]
**核准日期**: 2026-03-13
**版本**: v1
**状态**: frozen

本架构文档冻结后，任何修改必须通过新版本号 supersede，禁止原地修改已冻结版本。
