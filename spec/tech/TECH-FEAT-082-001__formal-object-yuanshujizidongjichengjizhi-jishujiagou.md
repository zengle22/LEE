---
id: TECH-FEAT-082-001
ssot_type: tech
title: Formal Object 元数据自动继承机制 - 技术架构设计
status: draft
version: v1
parent_id: FEAT-082
derived_from_ids:
  - ADR-001
  - ADR-003
  - ADR-008
source_refs:
  - FEAT-082#processing
  - FEAT-082#acceptance
owner: dev
tags: [tech, metadata, workflow, inheritance, ssot]
properties:
  tech_kind: architecture_design
  target_scope: workflow_runtime
  frozen_at: null
---

# Formal Object 元数据自动继承机制 - 技术架构设计

## 1. 架构概述

### 1.1 设计目标

本技术方案旨在实现 Workflow 执行过程中 Formal Object（ADR/EPIC/FEAT）的元数据自动继承与绑定机制，确保：

- `source_refs` 自动追溯至原始需求源（SRC）
- `parent_id` 自动维护层级关系（FEAT→EPIC→ADR）
- `derived_from_ids` 自动构建派生链
- 所有元数据在 Workflow Runtime 中自动注入，无需人工干预

### 1.2 架构原则

| 原则 | 说明 |
|------|------|
| **Single Source of Truth** | 元数据继承逻辑以 FEAT 冻结文档为唯一真源 |
| **Non-Invasive** | 不修改现有 SSOT Schema，仅扩展运行时注入能力 |
| **Transparent** | 继承逻辑对 Agent 透明，Agent 按常规方式消费元数据 |
| **Traceable** | 所有自动注入操作生成审计日志，支持溯源 |
| **Fallback Ready** | 提供手动覆盖机制，应对边界场景 |

## 2. 技术实现方案

### 2.1 整体架构图

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

#### 2.2.1 Metadata Inheritance Engine（元数据继承引擎）

**职责**：
- 解析 Workflow 输入中的 `feat_ref`
- 从 FEAT 文档提取元数据关系链
- 构建完整的继承上下文
- 注入到 Agent 执行上下文

**核心接口**：

```python
class MetadataInheritanceEngine:
    """
    元数据自动继承引擎

    负责在 Workflow 运行时自动解析和维护 Formal Object 的元数据关系。
    """

    def resolve_inheritance_context(
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
        pass

    def inject_metadata(
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
        pass
```

**数据结构**：

```python
@dataclass
class InheritanceContext:
    """继承上下文 - 包含完整的元数据继承链"""

    # 当前对象信息
    current_feat: FeatMetadata

    # 自动继承的元数据
    source_refs: List[str]              # 追溯至 SRC
    parent_id: Optional[str]            # EPIC ID
    derived_from_ids: List[VersionedRef] # 派生链

    # 完整追溯链
    trace_chain: TraceChain

    # 审计信息
    resolved_at: datetime
    resolver_version: str

@dataclass
class TraceChain:
    """追溯链 - 从 SRC 到当前 FEAT 的完整路径"""
    src: SrcMetadata
    epic: EpicMetadata
    feat: FeatMetadata
    governing_adrs: List[str]
```

#### 2.2.2 Formal Object Registry（正式对象注册表）

**职责**：
- 管理 FEAT/EPIC/ADR 对象的元数据索引
- 提供高效的元数据查询接口
- 维护对象间关系图

**存储策略**：

```yaml
# 索引结构
formal_object_index:
  feat:
    FEAT-082:
      v1:
        path: "spec/requirements/features/FEAT-082__xxx.md"
        parent_id: "EPIC-003"
        source_refs:
          - "SRC-001"
        derived_from_ids: []
        frozen_at: "2026-03-11T15:17:41"

  epic:
    EPIC-003:
      v1:
        path: "spec/requirements/epics/EPIC-003__xxx.md"
        parent_id: null
        source_refs:
          - "SRC-001"
        frozen_at: "2026-03-10T10:00:00"

  src:
    SRC-001:
      v1:
        path: "spec/source/SRC-001__xxx.md"
        frozen_at: "2026-03-09T09:00:00"
```

#### 2.2.3 Workflow Context Enhancer（工作流上下文增强器）

**职责**：
- 在 Workflow 启动时自动加载元数据继承上下文
- 在每个 Step 执行前注入相关元数据
- 支持条件注入（按需加载）

**注入点设计**：

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

        自动注入：
        1. source_refs - 来自 FEAT 的 source_refs
        2. parent_id - 来自 FEAT 的 parent_id
        3. derived_from_ids - 来自 FEAT 的 derived_from_ids
        4. governing_adrs - 来自追溯链的 ADR
        5. acceptance_criteria - FEAT 的验收标准
        """
        pass
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

## 3. 核心依赖项

### 3.1 内部依赖

| 依赖模块 | 路径 | 用途 | 版本约束 |
|----------|------|------|----------|
| Artifact Manager | `src/lee/orchestrator/execution/artifacts/manager.py` | SSOT 对象物化 | v1.3+ |
| SSOT Types | `src/lee/orchestrator/execution/artifacts/types.py` | 类型定义 | v1.3+ |
| Workflow Executor | `src/lee/orchestrator/execution/state_machine_executor.py` | Workflow 执行 | v3.5+ |
| Step Runners | `src/lee/orchestrator/execution/step_runners.py` | Step 分发 | v3.5+ |
| Agent Context | `src/lee/orchestrator/execution/agent_context.py` | Agent 上下文 | v2.0+ |

### 3.2 Schema 依赖

| Schema | 路径 | 用途 |
|--------|------|------|
| SSOT Agent Output | `spec-global/core/contracts/ssot-agent-output/v1/schema.json` | 输出契约 |
| FEAT Schema | `spec/contracts/frozen-requirement-contract/v1/schema.json` | FEAT 文档结构 |

### 3.3 外部依赖

| 依赖 | 用途 | 备份方案 |
|------|------|----------|
| PyYAML | FEAT 文档解析 | 内置 json 模块降级 |
| Markdown Frontmatter Parser | YAML Header 提取 | 正则表达式降级 |
| pydantic | 数据验证 | dataclasses + 手动验证 |

## 4. 技术不确定性及备份方案

### 4.1 风险矩阵

| 风险项 | 可能性 | 影响 | 风险等级 |
|--------|--------|------|----------|
| FEAT 文档解析性能瓶颈 | 中 | 高 | 🔴 高 |
| 循环依赖检测遗漏 | 低 | 高 | 🟡 中 |
| 元数据注入与现有逻辑冲突 | 中 | 中 | 🟡 中 |
| 跨 Workspace 引用处理 | 高 | 中 | 🟡 中 |
| 并发 Workflow 元数据一致性 | 低 | 高 | 🟡 中 |

### 4.2 备份方案

#### 风险 1: FEAT 文档解析性能瓶颈

**场景**：大量 FEAT 文档需要解析时，YAML Frontmatter 解析可能成为瓶颈

**备份方案**：
```python
# 方案 A: 缓存索引 (首选)
class CachedFormalObjectRegistry:
    """带缓存的 Formal Object 注册表"""

    def __init__(self):
        self._index_cache: Dict[str, Any] = {}
        self._cache_ttl: int = 300  # 5 分钟

    async def get_feat_metadata(self, feat_id: str) -> FeatMetadata:
        # 先查缓存
        if self._is_cache_valid(feat_id):
            return self._index_cache[feat_id]

        # 缓存未命中，解析文档
        metadata = await self._parse_feat_document(feat_id)
        self._index_cache[feat_id] = metadata
        return metadata

# 方案 B: 预构建索引 (备用)
class PrebuiltIndexRegistry:
    """预构建索引的注册表"""

    def rebuild_index(self):
        """后台任务定期重建索引"""
        for feat_file in self._scan_feat_files():
            metadata = self._parse_feat_document(feat_file)
            self._write_to_index_db(metadata)
```

#### 风险 2: 循环依赖检测遗漏

**场景**：错误的 FEAT 配置可能导致 parent_id 循环引用

**备份方案**：
```python
class CycleDetector:
    """循环依赖检测器"""

    def detect_cycle(self, start_id: str, get_parent_fn) -> Optional[List[str]]:
        """
        使用 Floyd's Cycle Detection 算法检测循环

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
            if len(path) > 100:
                raise InheritanceDepthExceeded()

        return None
```

#### 风险 3: 元数据注入与现有逻辑冲突

**场景**：自动注入的元数据可能与 Workflow/Agent 现有逻辑冲突

**备份方案**：
```yaml
# 方案: 特性开关 + 灰度发布
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

#### 风险 4: 跨 Workspace 引用处理

**场景**：FEAT-082 明确排除跨 Workspace 引用，但未来可能扩展

**备份方案**：
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
            logger.warning(f"Cross-workspace ref ignored: {ref}")
            return None

            # 未来：通过 SSOT Registry 解析
            # return self._registry_client.resolve(ref)

        return self._resolve_local_ref(ref)
```

#### 风险 5: 并发 Workflow 元数据一致性

**场景**：多个 Workflow 并发执行时，元数据索引可能不一致

**备份方案**：
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
                raise MetadataVersionMismatch()

            return metadata, version
```

## 5. 接口契约

### 5.1 输入契约

```yaml
metadata_inheritance_input:
  required:
    - feat_ref

  properties:
    feat_ref:
      type: string
      description: "FEAT 对象引用，格式: FEAT-{id}[@v{version}]"
      example: "FEAT-082@v1"

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
        properties:
          id: { type: string }
          version: { type: string }
      description: "自动维护的派生链"

    trace_chain:
      type: object
      description: "完整追溯链信息"

    inheritance_log:
      type: array
      description: "继承操作审计日志"
```

## 6. 验收验证方案

### 6.1 技术验收标准

| 验收项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| source_refs 自动绑定 | 单元测试 + 集成测试 | AC-003-001 通过 |
| parent_id 自动维护 | 单元测试 + 集成测试 | AC-003-002 通过 |
| 追溯信息展示 | E2E 测试 | AC-003-003 通过 |
| 性能 < 100ms | 压力测试 | 99th < 100ms |
| 并发安全 | 并发测试 | 无数据竞争 |

### 6.2 测试策略

```yaml
test_strategy:
  unit_tests:
    - "MetadataInheritanceEngine.resolve_inheritance_context"
    - "CycleDetector.detect_cycle"
    - "FormalObjectRegistry.get_metadata"

  integration_tests:
    - "Workflow 启动时元数据注入"
    - "Agent Step 元数据传递"
    - "Handover 元数据继承"

  e2e_tests:
    - "完整 FEAT→TECH 元数据链路"
    - "对象详情查询展示"
```

## 7. Frozen 架构声明

本技术架构设计经以下假设冻结：

1. **Schema 稳定性**：FEAT 文档 YAML Frontmatter 结构保持稳定
2. **Single Workspace**：当前版本仅支持单 Workspace 内元数据继承
3. **Non-Invasive**：不修改现有 SSOT Schema，仅扩展运行时
4. **Backward Compatible**：与现有 Workflow 模板保持向后兼容

**架构冻结版本**：v1
**冻结日期**：待人工核准后填充
**核准人**：待填充

---

## 附录 A: 关键代码结构

### A.1 目录结构

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
└── tests/
    ├── test_engine.py
    ├── test_registry.py
    └── test_integration.py
```

### A.2 配置示例

```yaml
# config/metadata_inheritance.yaml
metadata_inheritance:
  enabled: true

  cache:
    enabled: true
    ttl_seconds: 300
    max_entries: 1000

  indexing:
    mode: "lazy"  # lazy | eager
    rebuild_interval: 3600  # seconds

  limits:
    max_trace_depth: 100
    max_source_refs: 50
    max_derived_chain_length: 10

  conflict_resolution:
    strategy: "auto_override"
    log_level: "warning"
```

## 附录 B: 与其他系统的集成

### B.1 与 Workflow Orchestrator 集成

```python
# 在 Orchestrator 初始化时注入
class WorkflowOrchestrator:
    def __init__(self, ...):
        # ... 现有初始化 ...

        # 新增：元数据继承引擎
        self.metadata_engine = MetadataInheritanceEngine(
            registry=FormalObjectRegistry(),
            cache=MetadataCache(),
        )

    async def start_workflow(self, workflow_def, input_data):
        # 解析 feat_ref
        feat_ref = input_data.get("feat_ref")

        # 解析继承上下文
        if feat_ref:
            inheritance_ctx = await self.metadata_engine.resolve_inheritance_context(
                feat_ref=feat_ref,
                workflow_context=self.context
            )
            self.context.inheritance = inheritance_ctx

        # ... 继续执行 ...
```

### B.2 与 Agent Context 集成

```python
# 在构建 Agent Context 时注入
class AgentContextBuilder:
    def build(self, step, workflow_state):
        context = AgentContext()

        # 基础上下文
        context.step = step
        context.workflow = workflow_state

        # 新增：继承的元数据
        if workflow_state.inheritance:
            context.source_refs = workflow_state.inheritance.source_refs
            context.parent_id = workflow_state.inheritance.parent_id
            context.derived_from_ids = workflow_state.inheritance.derived_from_ids
            context.governing_adrs = workflow_state.inheritance.trace_chain.governing_adrs

        return context
```
