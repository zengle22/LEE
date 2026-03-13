---
id: TECH-FEAT-143-009
ssot_type: tech
title: FEAT-143 QA 执行入口规范化 - 冻结技术架构
status: frozen
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
---

# FEAT-143 QA 执行入口规范化 - 冻结技术架构

## 1. 架构概述

### 1.1 目标

收敛 QA 测试执行入口到 TESTPLAN 下的 TASK，确保正式交付只能通过 `RELEASE -> TESTPLAN -> TASK` 路径进入执行，消除分散执行入口导致的追溯断裂风险。

### 1.2 架构原则

1. **入口唯一性**：所有 QA 执行必须通过 `TASK-TESTPLAN-*` 触发
2. **链路完整性**：强制执行 `RELEASE -> TESTPLAN -> TASK` 三级引用校验
3. **旁路阻断**：识别并拒绝绕过标准入口的执行请求
4. **审计可追溯**：每次执行请求的 SSOT 三轴绑定信息完整记录

### 1.3 治理约束

本架构遵循以下 ADR 约束：

| ADR ID | 标题 | 约束要点 |
|--------|------|----------|
| ADR-001 | SSOT delivery chain hard governance | 三轴模型、交付链硬治理 |
| ADR-006 | CLI 命令分层与 SSOT 物化边界 | 用户命令 vs 系统命令分层 |
| ADR-007 | QA department SSOT alignment | TESTPLAN/TASK 作为执行入口 |

---

## 2. 模块技术实现方案

### 2.1 模块总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Layer (lee qa execute)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Entry Router  →  Bypass Blocker  →  Chain Validator  →  Audit Logger │
├─────────────────────────────────────────────────────────────────────┤
│                        SSOT Repository Layer                         │
│              (ArtifactManager / SSOTService / Registry)              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Entry Router 模块

**路径**: `src/lee/qa/entry/router.py`

**职责**: 接收所有执行请求，解析入口参数，路由到合法执行路径

**核心组件**:

```python
class EntryRouter:
    """执行入口路由器"""

    async def route(self, request: ExecutionRequest) -> ExecutionResult:
        """
        路由执行请求

        1. 解析 task_ref/plan_ref/release_ref 参数
        2. 调用 BypassBlocker 进行旁路检测
        3. 调用 ChainValidator 进行链路校验
        4. 路由到合法执行路径或返回错误
        """
        pass
```

**接口定义**:

| 方法 | 签名 | 返回值 | 职责 |
|------|------|--------|------|
| `route` | `async def route(request: ExecutionRequest) -> ExecutionResult` | `ExecutionResult` | 主路由入口 |
| `validate_entry` | `async def validate_entry(task_ref: str) -> ValidationResult` | `ValidationResult` | 入口合法性校验 |
| `resolve_task` | `async def resolve_task(task_ref: str) -> Optional[TASK]` | `Optional[TASK]` | 解析 TASK 对象 |

**错误代码**:

| 错误码 | 含义 | 触发条件 |
|--------|------|----------|
| `ERR-ENTRY-001` | 无效 task_ref | task_ref 不存在或格式错误 |
| `ERR-ENTRY-002` | task 不归属 testplan | task 的 parent_id 不是 TESTPLAN |

### 2.3 Bypass Blocker 模块

**路径**: `src/lee/qa/entry/bypass_blocker.py`

**职责**: 检测和阻断旁路执行请求

**核心组件**:

```python
class BypassBlocker:
    """旁路阻断器"""

    async def check(self, request: ExecutionRequest) -> BypassCheckResult:
        """
        旁路检测

        1. 检查是否存在 task_ref
        2. 检查 task_ref 是否归属有效 TESTPLAN
        3. 检查 TESTPLAN 是否归属有效 RELEASE
        4. 返回检测结果
        """
        pass

    async def block(self, request: ExecutionRequest, reason: str) -> BlockResult:
        """执行阻断并记录审计日志"""
        pass
```

**检测规则**:

| 规则 ID | 检测项 | 阻断条件 |
|--------|--------|----------|
| `BYPASS-001` | 无 task_ref 的直接调用 | `task_ref is None` |
| `BYPASS-002` | task 不归属 TESTPLAN | `task.parent_id` 不是 TESTPLAN 类型 |
| `BYPASS-003` | TESTPLAN 不归属 RELEASE | `testplan.parent_id` 不是 RELEASE 类型 |

**错误代码**:

| 错误码 | 含义 |
|--------|------|
| `ERR-BYPASS-001` | 旁路执行请求被阻断 |

### 2.4 Chain Validator 模块

**路径**: `src/lee/qa/entry/chain_validator.py`

**职责**: 验证 `RELEASE -> TESTPLAN -> TASK` 执行路径的完整性

**核心组件**:

```python
class ChainValidator:
    """链路校验器"""

    def __init__(self, cache_ttl: int = 60):
        self._cache = LRUCache(ttl_seconds=cache_ttl)

    async def validate(self, task_ref: str) -> ChainValidationResult:
        """
        链路完整性校验

        校验顺序：TASK -> TESTPLAN -> RELEASE
        渐进式提示：按 task->plan->release 顺序逐级反馈缺失环节
        """
        pass

    async def _validate_task(self, task: TASK) -> ValidationResult:
        """验证 TASK 归属 TESTPLAN"""
        pass

    async def _validate_testplan(self, testplan: TESTPLAN) -> ValidationResult:
        """验证 TESTPLAN 归属 RELEASE"""
        pass

    async def _validate_release(self, release: RELEASE) -> ValidationResult:
        """验证 RELEASE 状态有效"""
        pass
```

**缓存策略**:

| 缓存项 | TTL | 更新策略 |
|--------|-----|----------|
| TASK 对象 | 60 秒 | 惰性更新 |
| TESTPLAN 对象 | 60 秒 | 惰性更新 |
| RELEASE 对象 | 60 秒 | 惰性更新 |
| 链路校验结果 | 60 秒 | 惰性更新 |

**性能优化**:

1. **并行查询**: 同时获取 TASK/TESTPLAN/RELEASE 对象
2. **LRU 缓存**: 减少重复查询
3. **SSOT Registry 索引**: 利用 `.artifacts/.registry.json` 加速查找

**错误代码**:

| 错误码 | 含义 |
|--------|------|
| `ERR-CHAIN-001` | TASK 不归属有效 TESTPLAN |
| `ERR-CHAIN-002` | TESTPLAN 不归属有效 RELEASE |
| `ERR-CHAIN-003` | RELEASE 状态无效 (非 scope_frozen/in_dev/in_test) |

### 2.5 Audit Logger 模块

**路径**: `src/lee/qa/audit/logger.py`

**职责**: 记录每次执行请求的审计日志，确保可追溯

**核心组件**:

```python
class AuditLogger:
    """审计日志器"""

    def __init__(self, db_path: str, wal_enabled: bool = True):
        self.db_path = db_path
        self.wal_enabled = wal_enabled
        self._queue = asyncio.Queue(maxsize=1000)
        self._writer_task = None

    async def record(self, audit_entry: AuditEntry) -> None:
        """
        记录审计日志

        1. 写入内存队列 (快速路径)
        2. 后台异步写入 SQLite (持久化)
        3. 双写机制防止审计丢失
        """
        pass

    async def query(self, filters: AuditFilters) -> List[AuditEntry]:
        """查询审计日志"""
        pass

    async def _background_writer(self) -> None:
        """后台写入器，带指数退避重试"""
        pass
```

**SSOT 三轴绑定审计模型**:

```yaml
audit_entry:
  # 业务轴 (Business Axis)
  business_axis:
    feat_id: FEAT-143
    feat_version: v1
    testset_id: TESTSET-FEAT-143

  # 交付轴 (Delivery Axis)
  delivery_axis:
    release_id: REL-1.4.0
    testplan_id: TESTPLAN-REL-1.4.0
    task_id: TASK-TESTPLAN-REL-1.4.0-001

  # 执行轴 (Execution Axis)
  execution_axis:
    run_id: RUN-20260313-xxxx
    executed_at: 2026-03-13T10:00:00Z
    executor: cli / workflow / agent
    exit_code: 0
```

**数据库 Schema**:

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    testplan_id TEXT NOT NULL,
    release_id TEXT NOT NULL,
    feat_id TEXT NOT NULL,
    feat_version TEXT NOT NULL,
    entry_source TEXT NOT NULL,  -- cli / workflow / api
    path_chain TEXT NOT NULL,    -- JSON 数组
    executed_at TEXT NOT NULL,
    executor TEXT NOT NULL,
    exit_code INTEGER,
    error_code TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_run_id ON audit_log(run_id);
CREATE INDEX idx_audit_task_id ON audit_log(task_id);
CREATE INDEX idx_audit_release_id ON audit_log(release_id);
CREATE INDEX idx_audit_executed_at ON audit_log(executed_at);
```

**双写机制**:

1. **内存队列**: 快速写入，防止阻塞主流程
2. **SQLite WAL**: 异步持久化，Write-Ahead Logging 模式
3. **降级策略**: SQLite 写入失败时降级到文件日志

**重试策略**:

| 参数 | 值 |
|------|-----|
| 最大重试次数 | 3 |
| 初始退避 | 100ms |
| 退避因子 | 2x |
| 最大退避 | 1s |

### 2.6 CLI 集成模块

**路径**: `src/lee/cli/commands/qa/execute.py`

**职责**: 实现 `lee qa execute` 命令，集成所有核心组件

**命令接口**:

```bash
lee qa execute [OPTIONS]

Options:
  --task-ref TEXT       TASK 引用 (必需)
  --plan-ref TEXT       TESTPLAN 引用 (可选，用于校验)
  --release-ref TEXT    RELEASE 引用 (可选，用于校验)
  --validate-only       仅校验，不执行
  --json                JSON 格式输出
  --verbose             详细输出
```

**5 阶段反馈模型**:

```
[1/5] 入口校验 → Entry Router 检查
[2/5] 旁路检测 → Bypass Blocker 检查
[3/5] 链路校验 → Chain Validator 检查
[4/5] 执行准备 → 环境/上下文准备
[5/5] 执行启动 → 移交执行引擎
```

**Exit Codes**:

| Code | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 入口校验失败 (ERR-ENTRY-*) |
| 2 | 链路校验失败 (ERR-CHAIN-*) |
| 3 | 旁路阻断 (ERR-BYPASS-*) |
| 4 | 执行失败 |
| 5 | 内部错误 |

---

## 3. 核心依赖项

### 3.1 内部依赖

| 模块 | 路径 | 职责 | 风险等级 |
|------|------|------|----------|
| ArtifactManager | `src/lee/orchestrator/execution/artifacts/manager.py` | SSOT 对象物化 | 中 |
| SSOTService | `src/lee/orchestrator/execution/artifacts/ssot_service.py` | SSOT 校验与服务 | 中 |
| SSOTType | `src/lee/orchestrator/execution/artifacts/types.py` | SSOT 类型定义 | 低 |
| IDParser | `src/lee/orchestrator/execution/artifacts/id_parser.py` | ID 解析 | 低 |
| SSOT Registry | `.artifacts/.registry.json` | SSOT 索引缓存 | 中 |

### 3.2 外部依赖

| 库 | 版本 | 职责 | 风险等级 |
|----|------|------|----------|
| aiosqlite | >=0.19 | SQLite 异步驱动 (Audit Logger) | 低 |
| click | >=8.1 | CLI 框架 | 低 |
| pyyaml | >=6.0 | YAML 解析 (Front Matter) | 低 |
| jsonschema | >=4.0 | JSON Schema 校验 | 低 |

### 3.3 依赖关系图

```
lee.qa.entry.router
    ├── lee.qa.entry.bypass_blocker
    ├── lee.qa.entry.chain_validator
    ├── lee.qa.audit.logger
    └── lee.orchestrator.execution.artifacts
            ├── manager (ArtifactManager)
            ├── ssot_service (SSOTService)
            ├── types (SSOTType)
            └── id_parser (IDParser)

lee.cli.commands.qa.execute
    └── lee.qa.entry.router
```

---

## 4. 技术不确定性及备份方案

### 4.1 已识别的技术不确定性

| ID | 不确定性 | 影响 | 概率 | 缓解措施 | 备份方案 |
|----|----------|------|------|----------|----------|
| UC-001 | SSOT Registry 与磁盘 front matter 不一致 | 中 | 中 | 执行前强制 sync | 降级到全量扫描 |
| UC-002 | SQLite WAL 模式在 Windows 上的兼容性 | 中 | 低 | 充分测试 WAL 模式 | 降级到 DELETE 模式 |
| UC-003 | 高并发下内存队列溢出 | 低 | 低 | 限制队列大小 (1000) | 同步写入 + 告警 |
| UC-004 | TASK 归属关系校验性能 | 中 | 中 | LRU 缓存 + 并行查询 | 增加缓存 TTL |

### 4.2 详细备份方案

#### UC-001: Registry 不一致

**触发条件**:
- `.artifacts/.registry.json` 与磁盘 front matter 不一致
- SSOT 对象被外部修改

**备份方案**:
```python
async def get_ssot_object(ssot_id: str) -> Optional[SSOTObject]:
    # 主路径：从 Registry 获取
    if registry.is_fresh(ssot_id):
        return registry.get(ssot_id)

    # 备份路径：从磁盘 front matter 直接读取
    return await ssot_files.read_front_matter(ssot_id)
```

#### UC-002: SQLite WAL 兼容性

**触发条件**:
- Windows 上 WAL 模式失败
- 文件锁定冲突

**备份方案**:
```python
async def init_database(self):
    try:
        await self.conn.execute("PRAGMA journal_mode=WAL")
    except aiosqlite.Error:
        # 降级到 DELETE 模式
        await self.conn.execute("PRAGMA journal_mode=DELETE")
        self.logger.warning("WAL mode failed, fallback to DELETE mode")
```

#### UC-003: 内存队列溢出

**触发条件**:
- 后台写入器阻塞
- 审计请求速率 > 写入速率

**备份方案**:
```python
async def record(self, entry: AuditEntry):
    try:
        self._queue.put_nowait(entry)
    except asyncio.QueueFull:
        # 降级：同步写入 + 告警
        await self._write_directly(entry)
        self.logger.warning("Queue full, writing directly")
```

#### UC-004: 校验性能

**触发条件**:
- 大量并发执行请求
- 缓存命中率低

**备份方案**:
```python
# 增加缓存层
@lru_cache(maxsize=1000)
def get_cached_validation_result(task_ref: str, cache_key: str):
    ...

# 批量预加载
async def preload_chain(task_refs: List[str]):
    await asyncio.gather(*[self._load_chain(t) for t in task_refs])
```

---

## 5. 冻结架构决策

### 5.1 架构决策记录

| ID | 决策内容 | 状态 | 理由 |
|----|----------|------|------|
| D-001 | 采用 SQLite + aiosqlite 作为审计存储 | frozen | 轻量、无需额外服务、异步支持 |
| D-002 | 双写机制 (内存队列 + 磁盘 WAL) | frozen | 防止审计丢失，平衡性能与可靠性 |
| D-003 | 渐进式链路校验 (task->plan->release) | frozen | 清晰的错误定位，便于调试 |
| D-004 | LRU 缓存策略 (60 秒 TTL) | frozen | 平衡一致性与性能 |
| D-005 | CLI 5 阶段反馈模型 | frozen | 与现有 QA 执行器反馈模型一致 |
| D-006 | SSOT 三轴绑定审计模型 | frozen | 遵循 ADR-001 三轴模型 |

### 5.2 决策详细说明

#### D-001: SQLite + aiosqlite

**理由**:
1. 项目已有 aiosqlite 依赖，无需新增外部库
2. SQLite 零配置，适合 CLI 工具
3. 支持 WAL 模式，提供并发写入能力
4. 单文件数据库，便于备份和迁移

**风险**:
- 高并发写入性能有限 (通过双写机制缓解)

#### D-002: 双写机制

**理由**:
1. 审计日志不可丢失，需要持久化保证
2. 同步写入会阻塞主流程，影响响应时间
3. 内存队列提供快速路径，后台异步写入保证持久化

**实现**:
- 内存队列：`asyncio.Queue(maxsize=1000)`
- 后台写入器：独立异步任务，带指数退避重试

#### D-003: 渐进式链路校验

**理由**:
1. 用户需要清晰的错误定位
2. 按依赖顺序逐级校验，便于理解问题根源
3. 与 ADR-001 的交付链语义一致

**顺序**:
```
TASK → 检查 parent_id 是否为 TESTPLAN
  ↓
TESTPLAN → 检查 parent_id 是否为 RELEASE
  ↓
RELEASE → 检查状态是否有效 (scope_frozen/in_dev/in_test)
```

#### D-004: LRU 缓存策略

**理由**:
1. 减少重复 SSOT 对象查询
2. 60 秒 TTL 平衡一致性与性能
3. 惰性更新策略，避免主动刷新开销

#### D-005: CLI 5 阶段反馈模型

**理由**:
1. 与现有 QA Test Set Execute L3 workflow 一致
2. 提供清晰的执行进度反馈
3. 便于问题定位和调试

#### D-006: SSOT 三轴绑定审计模型

**理由**:
1. 遵循 ADR-001 定义的三轴模型
2. 确保审计记录可追溯到业务/交付/执行全链路
3. 为后续分析和报表提供结构化数据基础

---

## 6. 目录结构

```
src/lee/
├── qa/
│   ├── __init__.py
│   ├── entry/
│   │   ├── __init__.py
│   │   ├── router.py           # Entry Router
│   │   ├── bypass_blocker.py   # Bypass Blocker
│   │   └── chain_validator.py  # Chain Validator
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── logger.py           # Audit Logger
│   │   ├── models.py           # 审计数据模型
│   │   └── storage.py          # 存储层抽象
│   └── utils/
│       ├── __init__.py
│       ├── errors.py           # 错误代码定义
│       └── validators.py       # 通用校验器
├── cli/
│   └── commands/
│       └── qa/
│           ├── __init__.py
│           └── execute.py      # lee qa execute 命令
└── orchestrator/
    └── execution/
        └── artifacts/          # 现有 SSOT 基础设施
            ├── manager.py
            ├── ssot_service.py
            ├── types.py
            └── id_parser.py
```

---

## 7. 接口契约

### 7.1 ExecutionRequest

```python
@dataclass
class ExecutionRequest:
    """执行请求"""
    task_ref: Optional[str]      # TASK 引用
    plan_ref: Optional[str]      # TESTPLAN 引用 (可选)
    release_ref: Optional[str]   # RELEASE 引用 (可选)
    entry_source: str            # 入口来源：cli / workflow / api
    executor: str                # 执行者标识
    validate_only: bool = False  # 仅校验模式
    json_output: bool = False    # JSON 输出模式
```

### 7.2 ExecutionResult

```python
@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    exit_code: int
    error_code: Optional[str]
    error_message: Optional[str]
    task_id: Optional[str]
    testplan_id: Optional[str]
    release_id: Optional[str]
    audit_log_id: Optional[int]
```

### 7.3 ValidationResult

```python
@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool
    errors: List[ValidationError]
    warnings: List[str]

@dataclass
class ValidationError:
    """校验错误"""
    code: str          # ERR-ENTRY-*, ERR-CHAIN-*, ERR-BYPASS-*
    message: str
    field: Optional[str]
```

### 7.4 AuditEntry

```python
@dataclass
class AuditEntry:
    """审计日志条目"""
    run_id: str
    task_id: str
    testplan_id: str
    release_id: str
    feat_id: str
    feat_version: str
    entry_source: str
    path_chain: List[str]  # [TASK, TESTPLAN, RELEASE]
    executed_at: datetime
    executor: str
    exit_code: Optional[int]
    error_code: Optional[str]
```

---

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试文件 | 覆盖率目标 |
|------|----------|------------|
| Entry Router | `tests/unit/qa/entry/test_router.py` | 90% |
| Bypass Blocker | `tests/unit/qa/entry/test_bypass_blocker.py` | 90% |
| Chain Validator | `tests/unit/qa/entry/test_chain_validator.py` | 90% |
| Audit Logger | `tests/unit/qa/audit/test_logger.py` | 85% |

### 8.2 集成测试

| 测试场景 | 测试文件 |
|----------|----------|
| 完整执行流程 | `tests/integration/qa/test_execute_flow.py` |
| 旁路阻断场景 | `tests/integration/qa/test_bypass_blocking.py` |
| 链路断裂场景 | `tests/integration/qa/test_chain_validation.py` |
| 审计记录验证 | `tests/integration/qa/test_audit_logging.py` |

### 8.3 端到端测试

| 测试场景 | 测试文件 |
|----------|----------|
| CLI 命令执行 | `tests/e2e/cli/test_qa_execute.py` |
| 错误代码验证 | `tests/e2e/cli/test_error_codes.py` |
| 5 阶段反馈 | `tests/e2e/cli/test_feedback_model.py` |

---

## 9. 验收标准映射

| AC | 验收标准 | 实现模块 | 测试文件 |
|----|----------|----------|----------|
| AC-003-001 | 执行入口唯一性验证 | Entry Router | `test_router.py::test_entry_uniqueness` |
| AC-003-002 | 执行路径完整性校验 | Chain Validator | `test_chain_validator.py::test_chain_integrity` |
| AC-003-003 | 旁路执行入口阻断 | Bypass Blocker | `test_bypass_blocker.py::test_bypass_blocking` |
| AC-003-004 | 执行入口审计 | Audit Logger | `test_logger.py::test_audit_recording` |

---

## 10. 回滚策略

### 10.1 回滚目标

| 组件 | 回滚路径 |
|------|----------|
| Entry Router | `src/lee/qa/entry/` |
| Chain Validator | `src/lee/qa/entry/` |
| Bypass Blocker | `src/lee/qa/entry/` |
| Audit Logger | `src/lee/qa/audit/` |
| CLI 集成 | `src/lee/cli/commands/qa/execute.py` |

### 10.2 回滚模式

**模式**: `revert`

回滚到上一已知良好版本，不影响现有 SSOT 数据和审计日志。

---

## 11. 观察性

### 11.1 日志范围

| 日志域 | Scope | 级别 |
|--------|-------|------|
| Entry Router | `task-execution.entry` | INFO |
| Chain Validator | `task-execution.chain` | DEBUG |
| Bypass Blocker | `task-execution.bypass` | WARNING |
| Audit Logger | `task-execution.audit` | INFO |

### 11.2 关键指标

| 指标 | 描述 | 采集点 |
|------|------|--------|
| `entry_requests_total` | 入口请求总数 | Entry Router |
| `bypass_blocked_total` | 旁路阻断总数 | Bypass Blocker |
| `chain_validation_failures_total` | 链路校验失败数 | Chain Validator |
| `audit_write_latency_seconds` | 审计写入延迟 | Audit Logger |

### 11.3 审计字段

```yaml
audit_fields:
  - run_id
  - changed_files
  - test_results
  - audit_log_samples
```

---

## 12. 参考文献

| 文档 | 引用点 |
|------|--------|
| ADR-001 | 三轴模型、交付链硬治理规则 |
| ADR-006 | CLI 分层原则 |
| ADR-007 | QA 部门 SSOT 对齐、TESTPLAN/TASK 执行入口 |
| FEAT-143 | 冻结需求文档 |
| TECH-FEAT-169-003 | Frozen Technical Architecture Contract Schema |

---

## 13. 冻结确认

本架构文档已于 `2026-03-13` 冻结，后续实现必须严格遵循本架构定义。

任何架构变更必须通过新版本号 (`v2`, `v3`, ...) 进行，并保留本冻结版本作为历史记录。

**冻结签字**:

- 架构设计师：AI Architect
- 冻结时间：2026-03-13
- 评审状态：待人类核准
