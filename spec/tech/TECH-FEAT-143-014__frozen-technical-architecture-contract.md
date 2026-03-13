---
# Frozen Technical Architecture Contract
# FEAT-143: QA 执行入口规范化
contract_type: frozen-technical-architecture
contract_version: "v1.0"
metadata:
  contract_id: FTA-20260313-143
  status: FROZEN
  is_frozen: true
  feat_ref: FEAT-143
  title: FEAT-143 QA 执行入口规范化 - 冻结技术架构
  owner: architect
  frozen_at: "2026-03-13T00:00:00+08:00"
  frozen_by: architect
  approvers: []
  source_refs:
    - FEAT-143
    - ADR-001
    - ADR-007
    - ADR-011
    - TECH-FEAT-143-012
    - TECH-FEAT-143-013

# =============================================================================
# 1. 架构概述
# =============================================================================
architecture_overview:
  description: |
    FEAT-143 实现为"执行入口网关 (Execution Gateway)"，位于 QA 执行流程的最前端，
    负责收敛 QA 测试执行入口到 TESTPLAN 下的 TASK，确保正式交付只能通过
    RELEASE -> PLAN -> TASK 路径进入执行。

  design_principles:
    - "单一入口：所有测试执行必须通过 EntryRouter 统一路由"
    - "零信任：所有请求必须验证，不信任任何旁路请求"
    - "审计完备：所有执行请求必须记录审计日志"
    - "不侵入：不修改现有执行引擎内部逻辑"
    - "渐进式：采用分阶段实施，降低集成风险"

  architectural_pattern: "Gateway + Chain of Responsibility + Dual-Write Audit"

  # 架构分层图
  layers:
    - layer: entry_gateway
      name: "执行入口网关层 (FEAT-143 新增)"
      components:
        - EntryRouter
        - BypassBlocker
        - ChainValidator
        - AuditLogger
      responsibility: "统一接收、验证和路由所有执行请求"

    - layer: ssot_integration
      name: "SSOT 集成层 (复用现有)"
      components:
        - ArtifactManager
        - SSOTService
        - SSOTFiles
      responsibility: "提供 SSOT 对象读取、关系解析和真理链校验"

    - layer: execution_engine
      name: "执行引擎层 (保持不变)"
      components:
        - test-set-execute-l3-template
        - StepRunnerMixin
      responsibility: "实际测试用例执行 (FEAT-143 不修改此层)"

# =============================================================================
# 2. 技术栈选型
# =============================================================================
technology_stack:
  runtime:
    technology: "Python 3.8+"
    version_constraint: ">=3.8, <4.0"
    rationale: |
      与 LEE 框架现有技术栈保持一致，无需额外运行时依赖。
      Python 3.8 提供稳定的 asyncio 支持和 dataclass。

  data_models:
    technology: "Python dataclass + typing"
    version_constraint: "stdlib (Python 3.7+)"
    rationale: |
      利用 Python 原生 dataclass 定义 ExecutionRequest/ExecutionResult 模型，
      无需额外依赖，确保类型安全和 IDE 支持。
      相比 Pydantic，dataclass 更轻量且已在项目中使用。

  persistence:
    technology: "aiosqlite (SQLite + WAL mode)"
    version_constraint: ">=0.19"
    rationale: |
      审计日志需要支持并发写入和快速查询：
      - SQLite 零配置、单文件、无需额外服务
      - WAL (Write-Ahead Logging) 模式提供并发读写能力
      - aiosqlite 提供异步支持，已在 pyproject.toml 中声明

  ssot_integration:
    technology: "ArtifactManager + SSOTService"
    version_constraint: "lee-framework 内置"
    rationale: |
      复用现有 SSOT 基础设施 (src/lee/orchestrator/execution/artifacts/)：
      - ArtifactManager 提供 front matter 文件读取和 Registry 管理
      - SSOTService 提供真理链校验和影响分析

  caching:
    technology: "functools.lru_cache + TTL 装饰器"
    version_constraint: "stdlib"
    rationale: |
      减少重复 SSOT 对象查询，60 秒 TTL 平衡一致性与性能：
      - 惰性更新避免主动刷新开销
      - max_size=1000 限制内存占用

  cli_framework:
    technology: "Click"
    version_constraint: ">=8.1"
    rationale: |
      项目现有 CLI 框架 (pyproject.toml 已声明)：
      - 提供命令注册、参数解析、错误处理能力
      - 与现有 lee 命令集成无缝

  async_runtime:
    technology: "asyncio"
    version_constraint: "stdlib (Python 3.7+)"
    rationale: |
      支持并发 SSOT 查询、异步审计写入、非阻塞 CLI 响应：
      - Python 3.8 原生支持
      - 无需额外依赖

  logging:
    technology: "Python logging (stdlib)"
    version_constraint: "stdlib"
    rationale: |
      使用 Python 标准 logging 模块记录审计日志：
      - structlog 作为可选增强 (非必需)
      - 结构化日志通过 JSON 格式化实现

# =============================================================================
# 3. 核心组件设计
# =============================================================================
core_components:
  # ===========================================================================
  # 组件 1: EntryRouter (执行入口路由)
  # ===========================================================================
  - name: EntryRouter
    location: "src/lee/orchestrator/execution/router.py"
    responsibilities: |
      执行入口路由的核心接口，负责：
      1. 接收 ExecutionRequest
      2. 协调 BypassBlocker 和 ChainValidator 进行校验
      3. 路由到合法执行路径或返回错误
      4. 触发 AuditLogger 记录审计信息

    dependencies:
      - BypassBlocker
      - ChainValidator
      - AuditLogger
      - ArtifactManager

    interface:
      class_definition: |
        class EntryRouter:
            def __init__(
                self,
                bypass_blocker: BypassBlocker,
                chain_validator: ChainValidator,
                audit_logger: AuditLogger,
                artifact_manager: ArtifactManager
            )

            async def route(self, request: ExecutionRequest) -> ExecutionResult
            async def validate_entry(self, task_ref: str) -> ValidationResult
            async def resolve_task(self, task_ref: str) -> Optional[TASK]

      input_schema: |
        @dataclass
        class ExecutionRequest:
            task_ref: str                    # 必需：TASK-FEAT-143-001
            testplan_ref: Optional[str]      # 可选：用于校验
            release_ref: Optional[str]       # 可选：用于校验
            triggered_by: str                # 操作用户/系统标识
            entry_source: str                # "cli" | "api" | "ui" | "workflow"
            metadata: Dict[str, Any]         # 扩展元数据

      output_schema: |
        @dataclass
        class ExecutionResult:
            success: bool
            run_id: Optional[str]
            status: str                      # "accepted" | "rejected" | "blocked"
            error_code: Optional[str]        # ERR-BYPASS-xxx, ERR-CHAIN-xxx
            error_message: Optional[str]
            audit_log_id: Optional[str]
            path_chain: List[str]            # [TASK, TESTPLAN, RELEASE IDs]

    validation_rules:
      - "VR-001: task_ref 必需且格式有效 (TASK-{FEAT|BUG}-\\d{3}-\\d{3})"
      - "VR-002: task_ref 必须指向存在的 TASK 对象"
      - "VR-003: TASK.parent_id 必须指向 TESTPLAN 类型"
      - "VR-004: TESTPLAN.parent_id 必须指向 RELEASE 类型"
      - "VR-005: 禁止绕过 TASK 的直接执行请求"

  # ===========================================================================
  # 组件 2: BypassBlocker (旁路阻断器)
  # ===========================================================================
  - name: BypassBlocker
    location: "src/lee/orchestrator/execution/bypass.py"
    responsibilities: |
      检测和阻断旁路执行请求，识别以下旁路场景：
      1. 无 task_ref 的直接调用
      2. task 不归属 TESTPLAN (task.parent_id 不是 TESTPLAN 类型)
      3. TESTPLAN 不归属 RELEASE (testplan.parent_id 不是 RELEASE 类型)

    dependencies:
      - ArtifactManager
      - SSOTService
      - AuditLogger

    bypass_detection_rules:
      - "BYPASS-001: 无 task_ref 的直接调用"
      - "BYPASS-002: task 不归属 TESTPLAN (task.parent_id 不是 TESTPLAN 类型)"
      - "BYPASS-003: TESTPLAN 不归属 RELEASE (testplan.parent_id 不是 RELEASE 类型)"
      - "BYPASS-004: 直接使用 test_set_id 触发执行"
      - "BYPASS-005: 伪造的 task_ref 格式"

    error_codes:
      - code: "ERR-BYPASS-001"
        message: "旁路执行请求被阻断：缺少 task_ref"
      - code: "ERR-BYPASS-002"
        message: "旁路执行请求被阻断：task 不归属有效 TESTPLAN"
      - code: "ERR-BYPASS-003"
        message: "旁路执行请求被阻断：TESTPLAN 不归属有效 RELEASE"

    interface:
      class_definition: |
        class BypassBlocker:
            def __init__(
                self,
                artifact_manager: ArtifactManager,
                ssot_service: SSOTService,
                audit_logger: AuditLogger
            )

            async def check_bypass(self, request: ExecutionRequest) -> BypassDetection
            async def block_and_log(self, detection: BypassDetection) -> ExecutionResult

  # ===========================================================================
  # 组件 3: ChainValidator (链路校验器)
  # ===========================================================================
  - name: ChainValidator
    location: "src/lee/orchestrator/execution/validator.py"
    responsibilities: |
      验证 RELEASE->TESTPLAN->TASK 执行路径的完整性，按渐进式顺序逐级校验：
      1. TASK 存在且 parent_id 指向有效 TESTPLAN
      2. TESTPLAN 存在且 parent_id 指向有效 RELEASE
      3. RELEASE 状态有效 (scope_frozen/in_dev/in_test)

    dependencies:
      - ArtifactManager
      - SSOTService
      - "functools.lru_cache"

    validation_rules:
      - "CHAIN-001: TASK 存在且 parent_id 指向有效 TESTPLAN"
      - "CHAIN-002: TESTPLAN 存在且 parent_id 指向有效 RELEASE"
      - "CHAIN-003: RELEASE 状态有效 (scope_frozen/in_dev/in_test)"
      - "CHAIN-004: derived_from_ids 追溯链完整 (追溯到 FEAT)"

    error_codes:
      - code: "ERR-CHAIN-001"
        message: "TASK 不归属有效 TESTPLAN"
      - code: "ERR-CHAIN-002"
        message: "TESTPLAN 不归属有效 RELEASE"
      - code: "ERR-CHAIN-003"
        message: "RELEASE 状态无效"
      - code: "ERR-CHAIN-004"
        message: "derived_from_ids 追溯链断裂"

    cache_strategy:
      type: "lru_cache + TTL"
      ttl_seconds: 60
      max_size: 1000
      update_policy: "lazy"
      invalidation: "TTL 过期后自动刷新"

    interface:
      class_definition: |
        class ChainValidator:
            def __init__(
                self,
                artifact_manager: ArtifactManager,
                ssot_service: SSOTService,
                cache_ttl: int = 60
            )

            async def validate_chain(
                self,
                task_ref: str,
                testplan_ref: Optional[str] = None,
                release_ref: Optional[str] = None
            ) -> ChainValidationResult

            async def _validate_task(self, task_ref: str) -> TaskValidation
            async def _validate_testplan(self, testplan_ref: str) -> TestPlanValidation
            async def _validate_release(self, release_ref: str) -> ReleaseValidation

  # ===========================================================================
  # 组件 4: AuditLogger (审计日志记录器)
  # ===========================================================================
  - name: AuditLogger
    location: "src/lee/orchestrator/execution/audit.py"
    responsibilities: |
      记录每次执行请求的审计日志，包含 SSOT 三轴绑定信息：
      - 业务轴：feat_id, feat_version
      - 交付轴：release_id, testplan_id, task_id
      - 执行轴：run_id, executed_at, executor
      支持双写机制 (内存队列 + 磁盘 WAL) 确保审计不丢失

    dependencies:
      - "aiosqlite"
      - "asyncio.Queue"
      - "asyncio.Lock"

    log_schema:
      fields:
        - "run_id: str (执行实例 ID)"
        - "task_id: str"
        - "testplan_id: str"
        - "release_id: str"
        - "feat_id: str"
        - "feat_version: str"
        - "entry_source: str (cli/workflow/api)"
        - "path_chain: List[str] (TASK/TESTPLAN/RELEASE ID 链)"
        - "executed_at: datetime (ISO 8601 UTC)"
        - "executor: str"
        - "exit_code: int (可选)"
        - "error_code: str (可选)"
      storage: "SQLite + WAL mode"
      write_policy: "async_dual_write"

    dual_write_mechanism:
      memory_queue: "asyncio.Queue(maxsize=1000)"
      background_writer: "async task with exponential backoff"
      retry_policy:
        max_retries: 3
        initial_backoff: "100ms"
        backoff_factor: 2
        max_backoff: "1s"
      fallback: "sync write + warning"

    interface:
      class_definition: |
        class AuditLogger:
            def __init__(
                self,
                db_path: Path,
                queue_size: int = 1000
            )

            async def start(self) -> None
            async def stop(self) -> None
            async def log(self, entry: AuditEntry) -> str
            async def query_by_task(self, task_ref: str) -> List[AuditEntry]
            async def query_by_date_range(
                self,
                start: datetime,
                end: datetime
            ) -> List[AuditEntry]

  # ===========================================================================
  # 组件 5: CLI Executor (lee qa execute)
  # ===========================================================================
  - name: CLI Executor
    location: "src/lee/cli/commands/qa/execute.py"
    responsibilities: |
      实现 lee qa execute 命令，集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger，
      提供 5 阶段反馈模型和标准化退出码

    dependencies:
      - Click
      - EntryRouter
      - AuditLogger

    command: "lee qa execute [OPTIONS]"
    options:
      - "--task-ref TEXT (必需): TASK 对象 ID"
      - "--plan-ref TEXT (可选): TESTPLAN 对象 ID，用于额外校验"
      - "--release-ref TEXT (可选): RELEASE 对象 ID，用于额外校验"
      - "--validate-only (标志): 仅校验不执行，用于预检"
      - "--json (标志): JSON 格式输出"
      - "--verbose (标志): 详细输出模式"

    feedback_model:
      - "[1/5] 入口校验：验证 task_ref 格式和存在性"
      - "[2/5] 旁路检测：检测并阻断旁路执行尝试"
      - "[3/5] 链路校验：验证 RELEASE->TESTPLAN->TASK 完整性"
      - "[4/5] 执行准备：解析执行上下文和参数"
      - "[5/5] 执行启动：调用现有执行引擎"

    exit_codes:
      - code: 0
        meaning: "成功：执行请求已通过校验并启动"
      - code: 1
        meaning: "入口校验失败：task_ref 缺失或格式无效"
      - code: 2
        meaning: "链路校验失败：RELEASE/TESTPLAN/TASK 关系不完整"
      - code: 3
        meaning: "旁路阻断：检测到旁路执行尝试"
      - code: 4
        meaning: "执行失败：执行引擎内部错误"
      - code: 5
        meaning: "内部错误：EntryRouter/AuditLogger 异常"

    interface:
      command_definition: |
        @click.command()
        @click.option("--task-ref", required=True, help="TASK 对象 ID")
        @click.option("--plan-ref", help="TESTPLAN 对象 ID (可选)")
        @click.option("--release-ref", help="RELEASE 对象 ID (可选)")
        @click.option("--validate-only", is_flag=True, help="仅校验不执行")
        @click.option("--json", "output_json", is_flag=True, help="JSON 输出")
        @click.option("--verbose", is_flag=True, help="详细输出")
        def execute(task_ref, plan_ref, release_ref, validate_only, output_json, verbose):
            """执行 QA 测试，通过标准入口 TASK 触发"""

# =============================================================================
# 4. 核心依赖项
# =============================================================================
dependencies:
  external:
    - name: "Python"
      version: ">=3.8"
      type: "runtime"
      purpose: "运行时环境"
      source: "系统安装"

    - name: "aiosqlite"
      version: ">=0.19"
      type: "library"
      purpose: "异步 SQLite 访问，支持 WAL 模式"
      source: "pyproject.toml (已有)"

    - name: "click"
      version: ">=8.1"
      type: "library"
      purpose: "CLI 框架"
      source: "pyproject.toml (已有)"

    - name: "pyyaml"
      version: ">=6.0"
      type: "library"
      purpose: "YAML 解析，用于 SSOT front matter 读取"
      source: "pyproject.toml (已有)"

    - name: "aiohttp"
      version: ">=3.9"
      type: "library"
      purpose: "异步 HTTP 客户端 (预留 API 扩展)"
      source: "pyproject.toml (已有)"

  internal:
    - module: "lee.orchestrator.execution.artifacts.manager"
      components:
        - ArtifactManager
      purpose: "SSOT 对象读取和 Registry 管理"

    - module: "lee.orchestrator.execution.artifacts.ssot_service"
      components:
        - SSOTService
        - SSOTValidator
      purpose: "SSOT 真理链校验和影响分析"

    - module: "lee.orchestrator.execution.artifacts.types"
      components:
        - SSOTType
        - ArtifactType
      purpose: "SSOT 和 Artifact 类型定义"

    - module: "lee.orchestrator.execution.artifacts.models"
      components:
        - ArtifactMetadata
      purpose: "Artifact 元数据模型"

    - module: "lee.orchestrator.execution.artifacts.ssot_files"
      components:
        - read_front_matter
      purpose: "front matter 直接读取 (降级方案)"

# =============================================================================
# 5. 技术风险与备份方案
# =============================================================================
risk_management:
  high_risk_points:
    - risk_id: "R-001"
      category: "data_consistency"
      description: "SSOT Registry 与磁盘 front matter 不一致风险"
      impact: "校验基于过期数据，导致错误判定"
      probability: "medium"
      severity: "high"

      mitigation_plan:
        - "执行前强制 sync：检查 Registry 生成时间与文件修改时间"
        - "惰性更新：检测到文件变更时自动重新读取"
        - "降级策略：Registry 不可用时降级到直接读取 front matter 文件"

      degradation_strategy: |
        若 Registry 不一致或不可用，降级为直接读取 front matter 文件进行校验，
        牺牲性能换取正确性。

      backup_solution:
        trigger: "Registry.is_fresh() 返回 false 或抛出异常"
        fallback: "await ssot_files.read_front_matter(ssot_id)"

    - risk_id: "R-002"
      category: "security"
      description: "旁路检测不完备风险"
      impact: "可能存在未覆盖的旁路入口，导致部分执行请求绕过 EntryRouter"
      probability: "low"
      severity: "high"

      mitigation_plan:
        - "所有执行 API 统一通过 BypassBlocker 中间件"
        - "实现 API 调用链追踪，检测直接调用底层执行接口的行为"
        - "定期审计分析，识别异常执行模式"

      degradation_strategy: |
        发现新的旁路入口时，立即更新 BypassBlocker 规则并重新审计历史请求。

      backup_solution:
        trigger: "审计日志发现 bypass 模式"
        fallback: "紧急更新 BypassBlocker 规则 + 告警通知"

    - risk_id: "R-003"
      category: "reliability"
      description: "高并发下内存队列溢出风险"
      impact: "审计日志丢失"
      probability: "low"
      severity: "medium"

      mitigation_plan:
        - "限制队列大小 (maxsize=1000)"
        - "后台异步写入器带指数退避重试"
        - "监控队列长度，超过阈值告警"

      degradation_strategy: |
        若队列溢出，降级为同步写入 + 告警日志，不阻塞主流程。

      backup_solution:
        trigger: "asyncio.QueueFull exception"
        fallback: "await self._write_directly(entry) + logger.warning()"

    - risk_id: "R-004"
      category: "compatibility"
      description: "SQLite WAL 模式在 Windows 上的兼容性风险"
      impact: "审计日志写入失败"
      probability: "low"
      severity: "medium"

      mitigation_plan:
        - "充分测试 WAL 模式在 Windows 上的行为"
        - "捕获 WAL 初始化异常"
        - "监控 WAL 写入失败率"

      degradation_strategy: |
        若 WAL 模式失败，降级到 DELETE 模式并记录警告。

      backup_solution:
        trigger: "aiosqlite.Error during PRAGMA journal_mode=WAL"
        fallback: "await self.conn.execute('PRAGMA journal_mode=DELETE')"

    - risk_id: "R-005"
      category: "performance"
      description: "LRU 缓存不一致风险"
      impact: "校验基于过期的 SSOT 对象"
      probability: "medium"
      severity: "low"

      mitigation_plan:
        - "60 秒 TTL 平衡一致性与性能"
        - "惰性更新策略"
        - "关键操作前强制刷新缓存"

      degradation_strategy: |
        若缓存命中率持续低，增加缓存 TTL 或预加载热点对象。

      backup_solution:
        trigger: "缓存命中率 < 50%"
        fallback: "增加 TTL 到 120s 或禁用缓存"

    - risk_id: "R-006"
      category: "integration"
      description: "与现有执行引擎集成风险"
      impact: "集成失败导致功能不可用"
      probability: "low"
      severity: "high"

      mitigation_plan:
        - "EntryRouter 仅作为前置校验层，不替换现有执行引擎"
        - "保持 ExecutionRequest/Response 与现有接口的兼容性"
        - "提供 feature flag 控制入口规范化开关"

      degradation_strategy: |
        集成出现问题时，可通过 feature flag 临时关闭入口校验，回到原有执行模式。

      backup_solution:
        trigger: "集成测试失败或生产问题"
        fallback: "设置 LEE_QA_ENFORCE_ENTRY=false 关闭强制校验"

    - risk_id: "R-007"
      category: "performance"
      description: "审计日志写入延迟影响用户体验"
      impact: "CLI 命令响应变慢"
      probability: "medium"
      severity: "low"

      mitigation_plan:
        - "异步双写机制，主流程不等待磁盘落盘"
        - "内存队列批量写入，减少 I/O 次数"
        - "WAL 模式提供并发写入能力"

      degradation_strategy: |
        若写入延迟过高，减少批量大小或增加后台写入器数量。

      backup_solution:
        trigger: "审计写入延迟 > 500ms"
        fallback: "增加后台写入器数量或减少批量大小"

# =============================================================================
# 6. 架构决策记录 (ADR)
# =============================================================================
architecture_decision_records:
  - id: "D-001"
    title: "审计存储技术选型"
    decision: "采用 SQLite + aiosqlite 作为审计存储"
    alternatives_considered:
      - alternative: "PostgreSQL + asyncpg"
        reason_rejected: "需要额外服务，增加运维复杂度"
      - alternative: "JSON 文件追加写入"
        reason_rejected: "并发性能差，查询困难"
      - alternative: "内存存储"
        reason_rejected: "重启丢失，不适合审计"
    rationale: |
      轻量、无需额外服务、异步支持、WAL 模式提供并发能力。
      SQLite 单文件特性简化部署，WAL 模式支持并发读取。
    status: "accepted"

  - id: "D-002"
    title: "审计日志双写机制"
    decision: "双写机制 (内存队列 + 磁盘 WAL)"
    alternatives_considered:
      - alternative: "同步写入"
        reason_rejected: "简单但影响性能"
      - alternative: "纯异步写入"
        reason_rejected: "可能丢失审计"
      - alternative: "外部消息队列"
        reason_rejected: "过度设计"
    rationale: |
      防止审计丢失，平衡性能与可靠性。
      内存队列提供快速响应，后台写入器保证持久化。
    status: "accepted"

  - id: "D-003"
    title: "链路校验顺序"
    decision: "渐进式链路校验 (task->plan->release)"
    alternatives_considered:
      - alternative: "反向校验 (release->plan->task)"
        reason_rejected: "错误定位不清晰"
      - alternative: "并行校验所有节点"
        reason_rejected: "增加复杂度，无显著收益"
      - alternative: "仅校验 task 存在性"
        reason_rejected: "无法满足完整性要求"
    rationale: |
      清晰的错误定位，便于调试，与 ADR-001 交付链语义一致。
      从叶子节点向上校验，快速定位断裂点。
    status: "accepted"

  - id: "D-004"
    title: "缓存策略"
    decision: "LRU 缓存策略 (60 秒 TTL)"
    alternatives_considered:
      - alternative: "无缓存"
        reason_rejected: "每次读取文件，性能差"
      - alternative: "永久缓存"
        reason_rejected: "无法感知数据变更"
      - alternative: "主动刷新缓存"
        reason_rejected: "增加复杂度"
    rationale: |
      平衡一致性与性能，减少重复 SSOT 对象查询。
      60 秒 TTL 对于执行入口校验场景足够新鲜。
    status: "accepted"

  - id: "D-005"
    title: "CLI 反馈模型"
    decision: "CLI 5 阶段反馈模型"
    alternatives_considered:
      - alternative: "简单成功/失败输出"
        reason_rejected: "用户无法知道失败阶段"
      - alternative: "详细日志输出"
        reason_rejected: "信息过载"
      - alternative: "进度条反馈"
        reason_rejected: "不适用于快速校验场景"
    rationale: |
      与现有 QA Test Set Execute L3 workflow 一致，提供清晰进度反馈。
      用户可明确知道当前处于哪个校验阶段。
    status: "accepted"

  - id: "D-006"
    title: "审计数据模型"
    decision: "SSOT 三轴绑定审计模型"
    alternatives_considered:
      - alternative: "仅记录 task_id"
        reason_rejected: "追溯信息不完整"
      - alternative: "记录完整调用栈"
        reason_rejected: "数据冗余过大"
      - alternative: "扁平化键值对"
        reason_rejected: "结构化程度低"
    rationale: |
      遵循 ADR-001 三轴模型，确保审计记录可追溯到业务/交付/执行全链路。
      业务轴 (FEAT)、交付轴 (RELEASE/PLAN/TASK)、执行轴 (RUN) 完整绑定。
    status: "accepted"

  - id: "D-007"
    title: "EntryRouter 模块定位"
    decision: "EntryRouter 作为独立模块"
    alternatives_considered:
      - alternative: "集成到现有 test_run.py"
        reason_rejected: "侵入现有代码，增加耦合"
      - alternative: "作为中间件层"
        reason_rejected: "增加调用栈深度"
      - alternative: "作为装饰器"
        reason_rejected: "调试困难"
    rationale: |
      保持关注点分离，EntryRouter 专注于入口校验和路由。
      不侵入现有执行引擎，降低集成风险。
    status: "accepted"

# =============================================================================
# 7. 文件结构
# =============================================================================
file_structure:
  - path: "src/lee/orchestrator/execution/router.py"
    component: "EntryRouter"
    description: "执行入口路由核心实现"
    lines_estimated: 200

  - path: "src/lee/orchestrator/execution/bypass.py"
    component: "BypassBlocker"
    description: "旁路检测与阻断实现"
    lines_estimated: 150

  - path: "src/lee/orchestrator/execution/validator.py"
    component: "ChainValidator"
    description: "执行路径完整性校验"
    lines_estimated: 250

  - path: "src/lee/orchestrator/execution/audit.py"
    component: "AuditLogger"
    description: "审计日志记录与双写机制"
    lines_estimated: 300

  - path: "src/lee/orchestrator/execution/models.py"
    component: "Data Models"
    description: "ExecutionRequest/ExecutionResult 等数据模型"
    lines_estimated: 100
    note: "可扩展现有 models.py 或新建"

  - path: "src/lee/cli/commands/qa/execute.py"
    component: "CLI Executor"
    description: "lee qa execute 命令实现"
    lines_estimated: 150

  - path: ".artifacts/audit.db"
    component: "Audit Storage"
    description: "SQLite 审计日志数据库 (运行时创建)"
    auto_created: true

  - path: "tests/orchestrator/execution/test_router.py"
    component: "EntryRouter Tests"
    description: "EntryRouter 单元测试"
    lines_estimated: 200

  - path: "tests/orchestrator/execution/test_bypass.py"
    component: "BypassBlocker Tests"
    description: "BypassBlocker 单元测试"
    lines_estimated: 150

  - path: "tests/orchestrator/execution/test_validator.py"
    component: "ChainValidator Tests"
    description: "ChainValidator 单元测试"
    lines_estimated: 200

  - path: "tests/orchestrator/execution/test_audit.py"
    component: "AuditLogger Tests"
    description: "AuditLogger 单元测试"
    lines_estimated: 200

# =============================================================================
# 8. 验收标准
# =============================================================================
verification_criteria:
  functional:
    - id: "FC-001"
      description: "EntryRouter 仅接受包含有效 task_ref 的执行请求"
      verification_method: "单元测试 + 集成测试"

    - id: "FC-002"
      description: "ChainValidator 正确验证 RELEASE->TESTPLAN->TASK 链路完整性"
      verification_method: "单元测试 + 集成测试"

    - id: "FC-003"
      description: "BypassBlocker 检测并阻断所有旁路执行尝试"
      verification_method: "单元测试 + 安全测试"

    - id: "FC-004"
      description: "AuditLogger 记录所有执行请求的审计日志"
      verification_method: "单元测试 + 审计日志检查"

    - id: "FC-005"
      description: "CLI 命令 lee qa execute 提供 5 阶段反馈"
      verification_method: "端到端测试"

  non_functional:
    - id: "NFC-001"
      description: "单次执行请求校验延迟 < 200ms (P95)"
      verification_method: "性能测试"

    - id: "NFC-002"
      description: "审计日志写入不阻塞主流程"
      verification_method: "性能测试 + 代码审查"

    - id: "NFC-003"
      description: "缓存命中率 > 80% (稳态)"
      verification_method: "监控指标"

    - id: "NFC-004"
      description: "审计日志零丢失"
      verification_method: "故障注入测试"

  acceptance_mapping:
    - feat_requirement: "FEAT-143 / AC-003-001"
      technical_implementation: "EntryRouter.validate_entry()"
      test_reference: "tests/orchestrator/execution/test_router.py::test_entry_validation"

    - feat_requirement: "FEAT-143 / AC-003-002"
      technical_implementation: "ChainValidator.validate_chain()"
      test_reference: "tests/orchestrator/execution/test_validator.py::test_chain_validation"

    - feat_requirement: "FEAT-143 / AC-003-003"
      technical_implementation: "BypassBlocker.check_bypass()"
      test_reference: "tests/orchestrator/execution/test_bypass.py::test_bypass_detection"

    - feat_requirement: "FEAT-143 / AC-003-004"
      technical_implementation: "AuditLogger.log()"
      test_reference: "tests/orchestrator/execution/test_audit.py::test_audit_logging"

# =============================================================================
# 9. 已知限制
# =============================================================================
known_limitations:
  - limitation: "单实例部署假设"
    impact: "多实例场景下审计日志需要额外同步机制"
    future_enhancement: "支持集中式审计存储 (如 ELK、BigQuery)"

  - limitation: "旁路检测基于请求特征分析"
    impact: "无法 100% 防止恶意绕过"
    future_enhancement: "增加 API 网关层强制认证"

  - limitation: "SSOT Registry 一致性检查增加延迟"
    impact: "单次请求处理延迟增加约 50-100ms"
    future_enhancement: "异步预检 + 结果缓存"

  - limitation: "SQLite 并发写入性能有限"
    impact: "高并发场景可能成为瓶颈"
    future_enhancement: "支持 PostgreSQL/MySQL 插件式存储后端"

# =============================================================================
# 10. 下一步行动
# =============================================================================
next_steps:
  - step: 1
    action: "人类架构师评审本文档"
    owner: "architect"
    status: "pending"

  - step: 2
    action: "评审通过后进入实现阶段"
    owner: "developer"
    status: "pending"

  - step: 3
    action: "实现完成后进行集成测试"
    owner: "qa"
    status: "pending"

  - step: 4
    action: "通过测试后部署到 QA 环境验证"
    owner: "devops"
    status: "pending"

# =============================================================================
# 11. 冻结声明
# =============================================================================
frozen_declaration:
  frozen_at: "2026-03-13T00:00:00+08:00"
  frozen_by: "architect"
  review_status: "pending_human_approval"

  change_policy: |
    本架构文档已进入 FROZEN 状态，后续变更需走架构变更审批流程：
    1. 提交变更申请
    2. 影响分析
    3. 架构评审
    4. 更新版本号
    5. 重新冻结

  version_history:
    - version: "v1.0"
      date: "2026-03-13"
      author: "architect"
      changes: "初始冻结版本"
---